"""Price service — fetch OHLCV from yfinance, store in `prices_daily`.

Two responsibilities:
  1. Bulk fetch from yfinance (handles batching, retries, BSE fallback)
  2. Read latest / historical prices from Mongo

The daily refresh script (scripts/refresh_prices.py) is the cron entry point.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Iterable

from bson import Decimal128
import pandas as pd
import yfinance as yf
from pymongo import ASCENDING, DESCENDING, UpdateOne

from app.db.client import Collections
from app.models._common import _convert_decimals_to_decimal128

log = logging.getLogger(__name__)

# ── Yahoo ticker conversion ──────────────────────────────────────────────────


def to_yahoo_ticker(symbol: str, exchange: str = "NSE") -> str:
    """NSE: INFY → INFY.NS  ;  BSE: PATELSAI → PATELSAI.BO"""
    suffix = ".BO" if exchange.upper() == "BSE" else ".NS"
    s = symbol.upper()
    return s if s.endswith(suffix) else f"{s}{suffix}"


# ── Fetch from yfinance ──────────────────────────────────────────────────────


def fetch_eod_prices(
    holdings_meta: list[dict],
    days_back: int = 7,
) -> list[dict]:
    """Fetch OHLCV for a list of (isin, symbol, exchange) over `days_back` days.

    Args:
        holdings_meta: list of dicts each with keys 'isin', 'symbol', 'exchange'
        days_back: how many calendar days of history to fetch (yfinance returns
                   only trading days within this window)

    Returns:
        list of price-doc dicts ready to upsert into `prices_daily`.
        On per-symbol failure, that symbol is skipped (logged) — partial success
        is fine; we'd rather have most prices than fail the whole batch.
    """
    if not holdings_meta:
        return []

    # yfinance accepts space-separated tickers; download in batches of ~50
    # to avoid rate-limit issues
    BATCH_SIZE = 50
    all_rows: list[dict] = []

    # Map yahoo_ticker → (isin, symbol, exchange) for re-association after fetch
    ticker_meta: dict[str, dict] = {}
    for h in holdings_meta:
        yt = to_yahoo_ticker(h["symbol"], h.get("exchange", "NSE"))
        ticker_meta[yt] = h

    end_date = datetime.now(timezone.utc).date() + timedelta(
        days=1
    )  # yfinance is exclusive on end
    start_date = end_date - timedelta(days=days_back)

    tickers_list = list(ticker_meta.keys())
    log.info(
        "Fetching prices for %d tickers (%d days back)", len(tickers_list), days_back
    )

    for i in range(0, len(tickers_list), BATCH_SIZE):
        batch = tickers_list[i : i + BATCH_SIZE]
        log.info("  Batch %d: %d tickers", i // BATCH_SIZE + 1, len(batch))

        try:
            # auto_adjust=False: keep raw close + adj close separate
            # group_by='ticker': nested DataFrame keyed by ticker
            df = yf.download(
                tickers=" ".join(batch),
                start=start_date,
                end=end_date,
                auto_adjust=False,
                group_by="ticker",
                progress=False,
                threads=True,
            )
        except Exception as exc:
            log.error("Batch fetch failed: %s — falling back to per-ticker", exc)
            df = None

        if df is None or df.empty:
            log.warning("Batch returned empty df — skipping")
            continue

        # When only one ticker is in the batch, df has flat columns (no MultiIndex)
        # yfinance 1.3+ returns MultiIndex columns as (metric, ticker) regardless of group_by.
        # Normalize: if MultiIndex, swap to (ticker, metric) so we can do df[ticker].
        if hasattr(df.columns, "levels") and len(df.columns.levels) == 2:
            # If outer level looks like metrics ('Open','Close',...), swap.
            outer_values = set(df.columns.get_level_values(0))
            if outer_values & {"Open", "Close", "High", "Low", "Volume", "Adj Close"}:
                df = df.swaplevel(axis=1)
                df = df.sort_index(axis=1)

        if len(batch) == 1 and not hasattr(df.columns, "levels"):
            # Single-ticker, flat columns — direct
            yt = batch[0]
            rows = _df_to_rows(df, yt, ticker_meta[yt])
            all_rows.extend(rows)
        else:
            available_tickers = (
                set(df.columns.get_level_values(0))
                if hasattr(df.columns, "levels")
                else {batch[0]}
            )
            for yt in batch:
                if yt not in available_tickers:
                    log.warning("Ticker %s not returned by yfinance", yt)
                    continue
                ticker_df = df[yt].dropna(how="all")
                if ticker_df.empty:
                    log.warning("Ticker %s returned empty data", yt)
                    continue
                rows = _df_to_rows(ticker_df, yt, ticker_meta[yt])
                all_rows.extend(rows)

        # Be polite to yfinance
        if i + BATCH_SIZE < len(tickers_list):
            time.sleep(0.5)

    log.info("Fetched %d total OHLCV rows", len(all_rows))
    return all_rows


def _df_to_rows(ticker_df, yahoo_ticker: str, meta: dict) -> list[dict]:
    """Convert a yfinance OHLCV dataframe to our price-doc format."""
    rows = []
    for date_idx, row in ticker_df.iterrows():
        # Skip rows with all NaN (non-trading days, IPO pre-listing, etc.)
        if row.isna().all():
            continue
        try:
            open_p = row.get("Open")
            high = row.get("High")
            low = row.get("Low")
            close = row.get("Close")
            volume = row.get("Volume")
            adj_close = row.get("Adj Close")

            # Skip if any OHLC is missing/NaN.
            # F7 fix (Chat 5.5+): pre-fix this branch was dead — hasattr(p, "isnan")
            # is False for numpy scalars (the method is "isnan" not "isna"), AND
            # the second clause then called the wrong method name anyway. NaN
            # values flowed through to Decimal('NaN') and poisoned downstream P&L.
            # pd.isna handles None, NaN, NaT, pd.NA correctly.
            if any(p is None or pd.isna(p) for p in (open_p, high, low, close)):
                continue

            # Cast pandas Timestamp -> UTC datetime
            ts = date_idx.to_pydatetime()
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            else:
                ts = ts.astimezone(timezone.utc)

            rows.append(
                {
                    "isin": meta["isin"],
                    "symbol": meta["symbol"],
                    "exchange": meta.get("exchange", "NSE"),
                    "date": ts.replace(hour=0, minute=0, second=0, microsecond=0),
                    "open": Decimal(str(round(float(open_p), 4))),
                    "high": Decimal(str(round(float(high), 4))),
                    "low": Decimal(str(round(float(low), 4))),
                    "close": Decimal(str(round(float(close), 4))),
                    "volume": int(volume or 0),
                    "adj_close": Decimal(str(round(float(adj_close), 4)))
                    if adj_close is not None
                    else None,
                    "source": "yfinance",
                    "fetched_at": datetime.now(timezone.utc),
                    "_schema_version": 1,
                }
            )
        except (TypeError, ValueError) as exc:
            log.debug("Skipping row %s for %s: %s", date_idx, yahoo_ticker, exc)
            continue
    return rows


# ── Upsert into Mongo ────────────────────────────────────────────────────────


def upsert_prices(rows: list[dict]) -> dict:
    """Bulk-upsert price rows into `prices_daily`. Returns counts."""
    if not rows:
        return {"upserted": 0, "modified": 0, "total": 0}

    coll = Collections.prices_daily()

    operations = [
        UpdateOne(
            {"isin": r["isin"], "date": r["date"]},
            {"$set": _convert_decimals_to_decimal128(r)},
            upsert=True,
        )
        for r in rows
    ]

    chunk_size = 1000
    upserted = modified = 0
    for i in range(0, len(operations), chunk_size):
        result = coll.bulk_write(operations[i : i + chunk_size], ordered=False)
        upserted += result.upserted_count
        modified += result.modified_count

    return {
        "upserted": upserted,
        "modified": modified,
        "total": coll.estimated_document_count(),
    }


# ── Read from Mongo ──────────────────────────────────────────────────────────


def get_latest_price(isin: str) -> dict | None:
    """Get the most recent price row for one ISIN."""
    return Collections.prices_daily().find_one(
        {"isin": isin},
        sort=[("date", DESCENDING)],
    )


def bulk_get_latest_prices(isins: list[str]) -> dict[str, dict]:
    """Get the most recent price row for each ISIN. Returns {isin: doc}.

    Preference order:
      1. Today's most recent intraday quote (from prices_intraday) — if available
      2. Most recent EOD bar (from prices_daily)

    Intraday docs are normalized into the same shape as EOD docs:
      - 'close' field is set to the intraday 'price' so callers don't care which source
      - 'date' is set to captured_at (so price_as_of stays meaningful)
    """
    if not isins:
        return {}

    intraday = bulk_get_latest_intraday(isins)

    # Always fetch EOD too — used as fallback and for ISINs with no intraday
    pipeline = [
        {"$match": {"isin": {"$in": isins}}},
        {"$sort": {"isin": 1, "date": -1}},
        {
            "$group": {
                "_id": "$isin",
                "latest": {"$first": "$$ROOT"},
            }
        },
    ]
    eod = {
        doc["_id"]: doc["latest"]
        for doc in Collections.prices_daily().aggregate(pipeline)
    }

    merged: dict[str, dict] = {}
    for isin in isins:
        if isin in intraday:
            i = intraday[isin]
            # Normalize to the shape annotate_with_current_price expects
            merged[isin] = {
                **i,
                "close": i["price"],
                "date": i["captured_at"],
            }
        elif isin in eod:
            merged[isin] = eod[isin]

    return merged


def get_price_history(isin: str, days: int = 30) -> list[dict]:
    """Get the last N trading days of OHLCV for one ISIN. Newest first."""
    cursor = (
        Collections.prices_daily()
        .find({"isin": isin})
        .sort("date", DESCENDING)
        .limit(days)
    )
    return list(cursor)


def bulk_get_previous_closes(
    isin_to_latest_date: dict[str, datetime],
) -> dict[str, Decimal | None]:
    """For each ISIN, get the close from the most recent trading day BEFORE
    that ISIN's latest_date.

    Returns {isin: previous_close_decimal_or_None}.
    Used to compute day gain — paired with bulk_get_latest_prices.

    P2-13 / master_todo #11: pushes the per-ISIN ``date < latest_date`` filter
    into Mongo via one indexed find_one per ISIN (the (isin, date) index makes
    each a single-doc point-query). The previous shape $push-ed every price doc
    for every ISIN into an in-memory array and filtered in Python, pulling ~34k
    docs per dashboard request. Delegates to the single-ISIN get_previous_close
    so the Decimal128/Decimal normalization lives in exactly one place.
    """
    if not isin_to_latest_date:
        return {}

    return {
        isin: get_previous_close(isin, latest_date)
        for isin, latest_date in isin_to_latest_date.items()
    }


def get_previous_close(isin: str, before_date: datetime) -> Decimal | None:
    """Get the close from the most recent trading day BEFORE `before_date`.

    Single-ISIN version of bulk_get_previous_closes. Use this for endpoints
    that work on one holding at a time.
    """
    doc = Collections.prices_daily().find_one(
        {"isin": isin, "date": {"$lt": before_date}},
        sort=[("date", -1)],
        projection={"close": 1, "_id": 0},
    )
    if not doc:
        return None
    v = doc["close"]
    if isinstance(v, Decimal128):
        return v.to_decimal()
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def annotate_with_current_price(
    holding_doc: dict,
    latest_price_doc: dict | None,
    previous_close: Decimal | None = None,
) -> dict:
    """Compute live P&L fields and add them to a holding doc.

    Adds:
      - current_price (Decimal)
      - current_value (Decimal) = qty * current_price
      - unrealized_pnl (Decimal) = current_value - invested_amount
      - unrealized_pnl_pct (float) = unrealized_pnl / invested_amount * 100
      - day_gain (Decimal) = qty * (current_price - previous_close)
      - day_gain_pct (float) = (current_price / previous_close - 1) * 100
      - price_as_of (datetime) = the date of the latest price used
      - price_stale (bool) = true if latest price is more than 6 calendar days old

    If no price is available, sets all the above to None / 0.
    Day gain fields are only populated if `previous_close` is provided.
    """
    from datetime import datetime, timezone, timedelta

    def _to_dec(v):
        if isinstance(v, Decimal128):
            return v.to_decimal()
        if isinstance(v, Decimal):
            return v
        return Decimal(str(v))

    if not latest_price_doc:
        holding_doc["current_price"] = None
        holding_doc["current_value"] = None
        holding_doc["unrealized_pnl"] = None
        holding_doc["unrealized_pnl_pct"] = None
        holding_doc["day_gain"] = None
        holding_doc["day_gain_pct"] = None
        holding_doc["price_as_of"] = None
        holding_doc["price_stale"] = True
        return holding_doc

    qty = _to_dec(holding_doc["quantity"])
    invested = _to_dec(holding_doc["invested_amount"])
    current_price = _to_dec(latest_price_doc["close"])
    current_value = (qty * current_price).quantize(Decimal("0.01"))
    unrealized_pnl = (current_value - invested).quantize(Decimal("0.01"))
    pnl_pct = float((unrealized_pnl / invested) * 100) if invested > 0 else None

    # Day's gain (if we have yesterday's close)
    if previous_close is not None and previous_close > 0:
        prev_value = (qty * previous_close).quantize(Decimal("0.01"))
        day_gain = (current_value - prev_value).quantize(Decimal("0.01"))
        day_gain_pct = float(((current_price / previous_close) - 1) * 100)
    else:
        day_gain = None
        day_gain_pct = None

    price_date = latest_price_doc["date"]
    if price_date.tzinfo is None:
        price_date = price_date.replace(tzinfo=timezone.utc)
    # 6 calendar days (~4 NSE trading days across a weekend) is the canonical
    # threshold (P2-14 / master_todo #10: code is canonical, docstring aligned).
    is_stale = (datetime.now(timezone.utc) - price_date) > timedelta(days=6)

    holding_doc["current_price"] = current_price
    holding_doc["current_value"] = current_value
    holding_doc["unrealized_pnl"] = unrealized_pnl
    holding_doc["unrealized_pnl_pct"] = (
        round(pnl_pct, 2) if pnl_pct is not None else None
    )
    holding_doc["day_gain"] = day_gain
    holding_doc["day_gain_pct"] = (
        round(day_gain_pct, 2) if day_gain_pct is not None else None
    )
    holding_doc["price_as_of"] = price_date
    holding_doc["price_stale"] = is_stale

    return holding_doc


# ── Intraday fetch & storage ─────────────────────────────────────────────────


def fetch_intraday_quotes(holdings_meta: list[dict]) -> list[dict]:
    """Fetch the latest intraday quote per holding via yfinance 5-min bars.

    Args:
        holdings_meta: list of dicts each with keys 'isin', 'symbol', 'exchange'

    Returns:
        list of intraday-quote dicts ready for insert into prices_intraday.
        Empty list if market closed / yfinance returns nothing.
    """
    if not holdings_meta:
        return []

    BATCH_SIZE = 50
    all_rows: list[dict] = []
    now_utc = datetime.now(timezone.utc)

    ticker_meta: dict[str, dict] = {}
    for h in holdings_meta:
        yt = to_yahoo_ticker(h["symbol"], h.get("exchange", "NSE"))
        ticker_meta[yt] = h

    tickers_list = list(ticker_meta.keys())
    log.info("Intraday fetch: %d tickers (5m bars, period=1d)", len(tickers_list))

    for i in range(0, len(tickers_list), BATCH_SIZE):
        batch = tickers_list[i : i + BATCH_SIZE]
        try:
            df = yf.download(
                tickers=" ".join(batch),
                period="1d",
                interval="5m",
                auto_adjust=False,
                group_by="ticker",
                progress=False,
                threads=True,
            )
        except Exception as exc:
            log.error("Intraday batch fetch failed: %s", exc)
            continue

        if df is None or df.empty:
            log.warning("Intraday batch returned empty df — market closed?")
            continue

        # Same column normalization as fetch_eod_prices
        if hasattr(df.columns, "levels") and len(df.columns.levels) == 2:
            outer_values = set(df.columns.get_level_values(0))
            if outer_values & {"Open", "Close", "High", "Low", "Volume", "Adj Close"}:
                df = df.swaplevel(axis=1)
                df = df.sort_index(axis=1)

        # Per-ticker extraction
        if len(batch) == 1 and not hasattr(df.columns, "levels"):
            yt = batch[0]
            row = _intraday_row_from_df(df, yt, ticker_meta[yt], now_utc)
            if row:
                all_rows.append(row)
        else:
            available_tickers = (
                set(df.columns.get_level_values(0))
                if hasattr(df.columns, "levels")
                else {batch[0]}
            )
            for yt in batch:
                if yt not in available_tickers:
                    continue
                ticker_df = df[yt].dropna(how="all")
                if ticker_df.empty:
                    continue
                row = _intraday_row_from_df(ticker_df, yt, ticker_meta[yt], now_utc)
                if row:
                    all_rows.append(row)

        if i + BATCH_SIZE < len(tickers_list):
            time.sleep(0.3)

    log.info("Intraday fetch: got %d quotes", len(all_rows))
    return all_rows


# ── IST helpers (P1-4 / master_todo #9) ──────────────────────────────────────
IST = timezone(timedelta(hours=5, minutes=30))  # fixed UTC+5:30; India has no DST


def _to_ist(ts) -> datetime:
    """Convert a datetime / pandas Timestamp to IST.

    tz-aware inputs are converted; tz-naive inputs are treated as UTC first,
    matching the naive->UTC convention used elsewhere in this module
    (see _df_to_rows and annotate_with_current_price).
    """
    if hasattr(ts, "to_pydatetime"):
        ts = ts.to_pydatetime()
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(IST)


def _intraday_row_from_df(
    ticker_df, yahoo_ticker: str, meta: dict, captured_at: datetime
) -> dict | None:
    """Reduce an intraday OHLCV DF into a single 'latest quote' row.

    F8 fix (Chat 5.5+): pre-fix only dropped NaN on Close, so Open/High/Low
    could still be NaN on a partial 5m bar and flow through to Decimal('NaN'),
    poisoning every downstream live P&L during market hours. We now drop NaN
    across OHL+Close, and guard Volume sum against NaN since pandas .sum()
    returns NaN when all values are NaN (then `NaN or 0` evaluates to NaN
    because NaN is truthy in Python, breaking int() conversion).
    """
    try:
        clean = ticker_df.dropna(subset=["Open", "High", "Low", "Close"])
        if clean.empty:
            return None
        last = clean.iloc[-1]
        # P1-4 / master_todo #9 (holiday guard): yfinance period="1d" can
        # return the prior trading day's bars on an NSE holiday (a stale bar).
        # If the latest bar's IST date != today's IST date, treat it as "no
        # quote" so a holiday-stale row never lands in prices_intraday (and
        # never becomes a bogus "current price" via bulk_get_latest_intraday).
        bar_ist_date = _to_ist(clean.index[-1]).date()
        today_ist_date = _to_ist(captured_at).date()
        if bar_ist_date != today_ist_date:
            log.info(
                "Intraday bar for %s dated %s IST != today %s IST - stale "
                "(market holiday?); skipping",
                yahoo_ticker,
                bar_ist_date,
                today_ist_date,
            )
            return None

        # pandas .max()/.min() ignore NaN by default (skipna=True), but
        # return NaN if EVERY value is NaN — defensive check.
        high_max = clean["High"].max()
        low_min = clean["Low"].min()
        vol_sum = clean["Volume"].sum()
        if pd.isna(high_max) or pd.isna(low_min):
            return None
        return {
            "isin": meta["isin"],
            "symbol": meta["symbol"],
            "exchange": meta.get("exchange", "NSE"),
            "captured_at": captured_at,
            "price": Decimal(str(round(float(last["Close"]), 4))),
            "open_today": Decimal(str(round(float(clean.iloc[0]["Open"]), 4))),
            "day_high": Decimal(str(round(float(high_max), 4))),
            "day_low": Decimal(str(round(float(low_min), 4))),
            "volume_today": int(vol_sum) if not pd.isna(vol_sum) else 0,
            "source": "yfinance_intraday",
            "_schema_version": 1,
        }
    except Exception as exc:
        log.warning("Skipping intraday row for %s: %s", yahoo_ticker, exc)
        return None


def insert_intraday_quotes(rows: list[dict]) -> int:
    """Insert (not upsert) intraday quotes — each cron run is its own snapshot.

    Returns count inserted.
    """
    if not rows:
        return 0
    docs = [_convert_decimals_to_decimal128(r) for r in rows]
    Collections.prices_intraday().insert_many(docs, ordered=False)
    return len(docs)


def bulk_get_latest_intraday(isins: list[str]) -> dict[str, dict]:
    """For each ISIN, return the most recent intraday quote captured TODAY (UTC).

    Returns {} for ISINs without an intraday quote today (e.g. weekends, off hours).
    """
    if not isins:
        return {}

    now_utc = datetime.now(timezone.utc)
    today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)

    pipeline = [
        {
            "$match": {
                "isin": {"$in": isins},
                "captured_at": {"$gte": today_start},
            }
        },
        {"$sort": {"isin": 1, "captured_at": -1}},
        {
            "$group": {
                "_id": "$isin",
                "doc": {"$first": "$$ROOT"},
            }
        },
    ]

    return {
        r["_id"]: r["doc"] for r in Collections.prices_intraday().aggregate(pipeline)
    }
