"""Fundamentals service — fetch and persist per-stock fundamentals.

Provider abstraction so we can swap yfinance for Tijori (or anything else)
later without touching the consumer code (suggestion_engine).

v1 implementation: yfinance. Coverage is patchy for some Indian stocks;
missing fields are stored as None and surfaced in the scoring engine via
the confidence_score deduction mechanism.

Read patterns:
  - get_latest_for_isin(isin)               — single-stock read
  - get_latest_bulk(isins)                  — bulk read for scoring
  - is_fresh(fundamentals, max_age_days)    — staleness check

Write patterns:
  - refresh_one(isin, symbol, exchange)     — fetch + upsert one stock
  - refresh_universe(instruments)           — bulk refresh (called by cron)

The fetch is rate-limited (yfinance batch size + small sleep) to avoid
Yahoo throttling. For NIFTY 100 it takes ~60-90s end-to-end.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from typing import Any, Iterable

from bson import Decimal128
from pymongo import UpdateOne

import yfinance as yf

from app.db.client import Collections
from app.models._common import _convert_decimals_to_decimal128, utcnow
from app.services.price_service import to_yahoo_ticker

log = logging.getLogger(__name__)

# How long fundamentals are considered "fresh" by the scoring engine.
# Anything older than this gets the candidate dropped from a run with a
# logged warning.
DEFAULT_FRESHNESS_DAYS = 14

# Field map: our model field name -> yfinance info key
# yfinance keys are camelCase. We document expected types/units in comments.
_YF_FIELD_MAP = {
    # Identity / classification
    "name": "longName",
    "sector": "sector",
    "industry": "industry",
    # Valuation
    "market_cap": "marketCap",  # int, INR
    "pe_ratio": "trailingPE",  # float
    "pe_forward": "forwardPE",  # float
    "pb_ratio": "priceToBook",  # float
    "peg_ratio": "pegRatio",  # float
    "dividend_yield": "dividendYield",  # float, decimal (0.025 = 2.5%)
    # Quality
    "return_on_equity": "returnOnEquity",  # float, decimal
    "return_on_assets": "returnOnAssets",  # float, decimal
    "debt_to_equity": "debtToEquity",  # float (often given as % e.g. 47.5 meaning 0.475)
    "profit_margin": "profitMargins",  # float, decimal
    "operating_margin": "operatingMargins",  # float, decimal
    # Growth
    "earnings_growth_yoy": "earningsGrowth",  # float, decimal
    "revenue_growth_yoy": "revenueGrowth",  # float, decimal
    # Risk
    "beta": "beta",  # float
    # Price context
    "current_price": "currentPrice",  # float, INR (fallback: regularMarketPrice)
    "fifty_two_week_high": "fiftyTwoWeekHigh",  # float, INR
    "fifty_two_week_low": "fiftyTwoWeekLow",  # float, INR
}

# String-typed fields (don't try to Decimal-ify these)
_STRING_FIELDS = {"name", "sector", "industry"}


def _to_decimal_or_none(v: Any) -> Decimal | None:
    """Coerce a yfinance value to Decimal. Return None for missing/invalid."""
    if v is None:
        return None
    if isinstance(v, str):
        # yfinance uses "-" or "N/A" sometimes
        if v.strip() in ("", "-", "N/A", "None", "nan"):
            return None
        try:
            return Decimal(v.strip())
        except Exception:
            return None
    if isinstance(v, (int, float)):
        # NaN check
        if v != v:  # NaN != NaN
            return None
        try:
            return Decimal(str(v))
        except Exception:
            return None
    if isinstance(v, Decimal):
        return v
    if isinstance(v, Decimal128):
        return v.to_decimal()
    return None


def _normalize_debt_to_equity(v: Decimal | None) -> Decimal | None:
    """yfinance returns debtToEquity in two possible scales:
      - As a ratio (e.g., 0.47 = 47% debt-to-equity), or
      - As a percentage (e.g., 47.5)
    Indian stocks tend to come back in percentage form. Normalize to ratio
    (always < ~10 for practical companies) so downstream gates compare cleanly.
    """
    if v is None:
        return None
    # Heuristic: if value > 5, it's almost certainly in percentage form.
    # Real D/E ratios above 5 are extreme outliers.
    if v > Decimal("5"):
        return v / Decimal("100")
    return v


def _normalize_dividend_yield(v: Decimal | None) -> Decimal | None:
    """Same scale issue — yfinance sometimes returns 2.5 instead of 0.025.
    Normalize to decimal form (0.025 = 2.5%).
    """
    if v is None:
        return None
    # If value > 1, it's in percentage form
    if v > Decimal("1"):
        return v / Decimal("100")
    return v


def _build_fundamentals_doc(
    isin: str,
    symbol: str,
    exchange: str,
    info: dict,
) -> dict:
    """Map yfinance `info` dict -> our InstrumentFundamentals doc shape."""
    doc: dict = {
        "isin": isin,
        "symbol": symbol.upper(),
        "exchange": exchange.upper(),
        "source": "yfinance",
        "source_raw": info,  # store raw for debugging; ~5KB per stock
        "fetched_at": utcnow(),
        "created_at": utcnow(),
        "_schema_version": 1,
    }
    fields_present: list[str] = []
    fields_missing: list[str] = []

    for our_field, yf_key in _YF_FIELD_MAP.items():
        raw = info.get(yf_key)
        if our_field in _STRING_FIELDS:
            if raw and isinstance(raw, str) and raw.strip():
                doc[our_field] = raw.strip()
                fields_present.append(our_field)
            else:
                doc[our_field] = ""
                fields_missing.append(our_field)
            continue

        value = _to_decimal_or_none(raw)
        if value is None:
            doc[our_field] = None
            fields_missing.append(our_field)
            continue

        # Per-field normalization
        if our_field == "debt_to_equity":
            value = _normalize_debt_to_equity(value)
        elif our_field == "dividend_yield":
            value = _normalize_dividend_yield(value)

        doc[our_field] = value
        fields_present.append(our_field)

    # current_price fallback
    if doc.get("current_price") is None:
        fallback = _to_decimal_or_none(info.get("regularMarketPrice"))
        if fallback is not None:
            doc["current_price"] = fallback
            if "current_price" in fields_missing:
                fields_missing.remove("current_price")
            fields_present.append("current_price")

    doc["fields_present"] = fields_present
    doc["fields_missing"] = fields_missing
    return doc


# ── Provider: yfinance ───────────────────────────────────────────────────────


def fetch_one_yfinance(symbol: str, exchange: str = "NSE") -> dict | None:
    """Fetch raw `info` dict from yfinance for one stock.
    Returns None on failure (logged, not raised).
    """
    yt = to_yahoo_ticker(symbol, exchange)
    try:
        ticker = yf.Ticker(yt)
        info = ticker.info or {}
        if not info or len(info) < 5:  # near-empty response = failed lookup
            log.warning("yfinance returned near-empty info for %s", yt)
            return None
        return info
    except Exception as exc:
        log.warning("yfinance fetch_one failed for %s: %s", yt, exc)
        return None


# ── Public API ───────────────────────────────────────────────────────────────


def refresh_one(isin: str, symbol: str, exchange: str = "NSE") -> dict | None:
    """Fetch fundamentals for one stock and upsert into the collection.
    Returns the persisted doc, or None on fetch failure.
    """
    info = fetch_one_yfinance(symbol, exchange)
    if info is None:
        return None
    doc = _build_fundamentals_doc(isin, symbol, exchange, info)

    Collections.instruments_fundamentals().update_one(
        {"isin": isin},
        {"$set": _convert_decimals_to_decimal128(doc)},
        upsert=True,
    )
    return doc


def refresh_universe(instruments: list[dict], throttle_sec: float = 0.3) -> dict:
    """Refresh fundamentals for a list of instruments.

    Args:
        instruments: list of dicts with at least {isin, symbol, exchange}.
        throttle_sec: sleep between fetches to be nice to yfinance.

    Returns:
        Stats dict: {attempted, succeeded, failed, failed_isins}.
    """
    stats = {
        "attempted": len(instruments),
        "succeeded": 0,
        "failed": 0,
        "failed_isins": [],
    }
    log.info("Refreshing fundamentals for %d instruments", len(instruments))
    for i, inst in enumerate(instruments):
        isin = inst["isin"]
        symbol = inst["symbol"]
        exchange = inst.get("exchange", "NSE")

        result = refresh_one(isin, symbol, exchange)
        if result is None:
            stats["failed"] += 1
            stats["failed_isins"].append(isin)
            log.warning("  [%d/%d] FAIL %s (%s)", i + 1, len(instruments), symbol, isin)
        else:
            stats["succeeded"] += 1
            present = len(result["fields_present"])
            missing = len(result["fields_missing"])
            log.info(
                "  [%d/%d] OK   %s (%s) — %d/%d fields present",
                i + 1,
                len(instruments),
                symbol,
                isin,
                present,
                present + missing,
            )

        if throttle_sec > 0 and i < len(instruments) - 1:
            time.sleep(throttle_sec)

    log.info(
        "Fundamentals refresh complete: %d/%d succeeded",
        stats["succeeded"],
        stats["attempted"],
    )
    return stats


def get_latest_for_isin(isin: str) -> dict | None:
    """Read the latest fundamentals snapshot for one ISIN. None if missing."""
    return Collections.instruments_fundamentals().find_one({"isin": isin})


def get_latest_bulk(isins: list[str]) -> dict[str, dict]:
    """Read latest fundamentals for many ISINs. Returns {isin: doc} (only present)."""
    if not isins:
        return {}
    cursor = Collections.instruments_fundamentals().find({"isin": {"$in": isins}})
    return {doc["isin"]: doc for doc in cursor}


def is_fresh(
    fundamentals_doc: dict | None, max_age_days: int = DEFAULT_FRESHNESS_DAYS
) -> bool:
    """True if fundamentals were fetched within max_age_days."""
    if not fundamentals_doc:
        return False
    fetched_at = fundamentals_doc.get("fetched_at")
    if not fetched_at:
        return False
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - fetched_at
    return age <= timedelta(days=max_age_days)


# ─────────────────────────────────────────────────────────────────────
# F14: Earnings calendar
# ─────────────────────────────────────────────────────────────────────
#
# yfinance Ticker.calendar returns a dict with an 'Earnings Date' key
# whose value is one date or a list of dates (sometimes a 1-2 element
# range when the date is unconfirmed). We persist each date as a
# separate doc keyed by (isin, earnings_date).
#
# Refresh semantics: future events (>= today) are REPLACED on each
# refresh — we delete then re-insert. Past events are immutable history.


def _coerce_naive_datetime(d: Any) -> datetime | None:
    """Coerce yfinance date-ish value to a tz-naive datetime.

    Handles pandas Timestamp, datetime (tz-aware or naive), date.
    Returns None if it can't be parsed.
    """
    if d is None:
        return None
    if hasattr(d, "to_pydatetime"):
        try:
            d = d.to_pydatetime()
        except Exception:
            return None
    if isinstance(d, datetime):
        if d.tzinfo is not None:
            d = d.replace(tzinfo=None)
        return d
    if isinstance(d, date):
        return datetime(d.year, d.month, d.day)
    return None


def _sanitize_for_bson(value: Any) -> Any:
    """Coerce arbitrary yfinance values into BSON-encodable shapes.

    yfinance Ticker.calendar can contain datetime.date (BSON can't encode it,
    only datetime is allowed), pandas Timestamps, numpy scalars, and lists
    thereof. Walks dicts/lists/tuples and converts:
      - date / Timestamp / tz-aware datetime → tz-naive datetime
      - numpy scalars → native Python via .item()
      - other primitives → unchanged
      - unknown types → str(value) as a last resort
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo is not None else value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if hasattr(value, "to_pydatetime"):
        try:
            return _sanitize_for_bson(value.to_pydatetime())
        except Exception:
            return str(value)
    if hasattr(value, "item"):  # numpy scalar
        try:
            return _sanitize_for_bson(value.item())
        except Exception:
            return str(value)
    if isinstance(value, dict):
        return {str(k): _sanitize_for_bson(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize_for_bson(v) for v in value]
    return str(value)


def fetch_earnings_calendar_yfinance(
    symbol: str, exchange: str = "NSE"
) -> tuple[list[datetime], dict | None]:
    """Fetch upcoming earnings dates from yfinance Ticker.calendar.

    Returns (sorted_dates, raw_calendar_dict). Empty list + None on
    failure or no events (logged, not raised).
    """
    yt = to_yahoo_ticker(symbol, exchange)
    try:
        ticker = yf.Ticker(yt)
        cal = ticker.calendar
        if not cal or not isinstance(cal, dict):
            return [], None

        raw_dates = cal.get("Earnings Date", [])
        if raw_dates is None:
            return [], cal
        if not isinstance(raw_dates, (list, tuple)):
            raw_dates = [raw_dates]

        out: list[datetime] = []
        for raw in raw_dates:
            parsed = _coerce_naive_datetime(raw)
            if parsed is not None:
                out.append(parsed)

        return sorted(set(out)), cal
    except Exception as exc:
        log.warning("yfinance earnings calendar fetch failed for %s: %s", yt, exc)
        return [], None


def refresh_earnings_for(isin: str, symbol: str, exchange: str = "NSE") -> dict:
    """Refresh earnings calendar for one ISIN.

    Returns stats dict: {events_fetched, events_inserted, future_deleted, source_raw}.
    """
    dates, raw_cal = fetch_earnings_calendar_yfinance(symbol, exchange)
    now_naive = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Replace-future semantics: drop all future events for this ISIN
    # then insert the freshly-fetched list. Past events untouched.
    delete_result = Collections.earnings_calendar().delete_many(
        {"isin": isin, "earnings_date": {"$gte": now_naive}}
    )

    inserted = 0
    if dates:
        # yfinance Ticker.calendar contains datetime.date values
        # (e.g. 'Ex-Dividend Date') that BSON cannot encode. Sanitize once
        # before reuse across all docs for this ISIN.
        raw_cal_safe = _sanitize_for_bson(raw_cal) if raw_cal else None
        docs = [
            {
                "isin": isin,
                "symbol": symbol.upper(),
                "exchange": exchange.upper(),
                "earnings_date": d,
                "source": "yfinance",
                "source_raw": raw_cal_safe,
                "fetched_at": utcnow(),
                "created_at": utcnow(),
            }
            for d in dates
        ]
        # use upsert by unique key to be defensive against a race
        ops = [
            UpdateOne(
                {"isin": doc["isin"], "earnings_date": doc["earnings_date"]},
                {"$set": doc},
                upsert=True,
            )
            for doc in docs
        ]
        result = Collections.earnings_calendar().bulk_write(ops, ordered=False)
        inserted = (result.upserted_count or 0) + (result.modified_count or 0)

    return {
        "events_fetched": len(dates),
        "events_inserted": inserted,
        "future_deleted": delete_result.deleted_count,
    }


def refresh_earnings_universe(
    instruments: list[dict], throttle_sec: float = 0.3
) -> dict:
    """Refresh earnings calendar for a list of instruments.

    Args:
        instruments: list of dicts with at least {isin, symbol, exchange}.
        throttle_sec: sleep between fetches.

    Returns stats dict.
    """
    stats = {
        "attempted": len(instruments),
        "succeeded_with_events": 0,
        "succeeded_no_events": 0,
        "failed": 0,
        "failed_isins": [],
        "total_events_inserted": 0,
    }

    log.info("Refreshing earnings calendar for %d instruments", len(instruments))
    for i, inst in enumerate(instruments):
        isin = inst["isin"]
        symbol = inst["symbol"]
        exchange = inst.get("exchange", "NSE")

        try:
            r = refresh_earnings_for(isin, symbol, exchange)
            if r["events_fetched"] > 0:
                stats["succeeded_with_events"] += 1
                stats["total_events_inserted"] += r["events_inserted"]
                log.info(
                    "  [%d/%d] OK   %s (%s)  %d events",
                    i + 1,
                    len(instruments),
                    symbol,
                    isin,
                    r["events_fetched"],
                )
            else:
                stats["succeeded_no_events"] += 1
                log.info(
                    "  [%d/%d] OK   %s (%s)  no upcoming events",
                    i + 1,
                    len(instruments),
                    symbol,
                    isin,
                )
        except Exception as exc:
            stats["failed"] += 1
            stats["failed_isins"].append(isin)
            log.warning(
                "  [%d/%d] FAIL %s (%s): %s",
                i + 1,
                len(instruments),
                symbol,
                isin,
                exc,
            )

        if throttle_sec > 0 and i < len(instruments) - 1:
            time.sleep(throttle_sec)

    log.info(
        "Earnings refresh complete: %d with events, %d without, %d failed",
        stats["succeeded_with_events"],
        stats["succeeded_no_events"],
        stats["failed"],
    )
    return stats


def get_next_earnings_for_isin(
    isin: str, as_of: datetime | None = None
) -> datetime | None:
    """Return the next earnings_date >= as_of for one ISIN, or None.

    Consumer helper for the suggestion engine gates/signals.
    """
    if as_of is None:
        as_of = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    elif as_of.tzinfo is not None:
        as_of = as_of.replace(tzinfo=None)

    doc = Collections.earnings_calendar().find_one(
        {"isin": isin, "earnings_date": {"$gte": as_of}},
        sort=[("earnings_date", 1)],
        projection={"earnings_date": 1, "_id": 0},
    )
    if doc is None:
        return None
    return doc["earnings_date"]


def get_next_earnings_bulk(
    isins: list[str], as_of: datetime | None = None
) -> dict[str, datetime]:
    """Bulk variant of get_next_earnings_for_isin.

    Returns {isin: next_earnings_date}; ISINs with no upcoming event omitted.
    """
    if not isins:
        return {}
    if as_of is None:
        as_of = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    elif as_of.tzinfo is not None:
        as_of = as_of.replace(tzinfo=None)

    cursor = Collections.earnings_calendar().find(
        {"isin": {"$in": isins}, "earnings_date": {"$gte": as_of}},
        projection={"isin": 1, "earnings_date": 1, "_id": 0},
        sort=[("earnings_date", 1)],
    )
    out: dict[str, datetime] = {}
    for doc in cursor:
        # First (earliest) per isin wins because of the asc sort
        isin = doc["isin"]
        if isin not in out:
            out[isin] = doc["earnings_date"]
    return out
