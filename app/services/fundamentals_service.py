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
from datetime import datetime, timezone, timedelta
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
