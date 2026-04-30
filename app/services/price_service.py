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

            # Skip if all OHLC are missing
            if any(
                p is None or (hasattr(p, "isnan") and p.isna())
                for p in (open_p, high, low, close)
            ):
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
    """Get the most recent price row for each ISIN. Returns {isin: doc}."""
    if not isins:
        return {}

    # Aggregation: group by isin, take the doc with max date per group
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
    return {
        doc["_id"]: doc["latest"]
        for doc in Collections.prices_daily().aggregate(pipeline)
    }


def get_price_history(isin: str, days: int = 30) -> list[dict]:
    """Get the last N trading days of OHLCV for one ISIN. Newest first."""
    cursor = (
        Collections.prices_daily()
        .find({"isin": isin})
        .sort("date", DESCENDING)
        .limit(days)
    )
    return list(cursor)


def annotate_with_current_price(
    holding_doc: dict, latest_price_doc: dict | None
) -> dict:
    """Compute live P&L fields and add them to a holding doc.

    Adds:
      - current_price (Decimal)
      - current_value (Decimal) = qty * current_price
      - unrealized_pnl (Decimal) = current_value - invested_amount
      - unrealized_pnl_pct (float) = unrealized_pnl / invested_amount * 100
      - price_as_of (datetime) = the date of the latest price used
      - price_stale (bool) = true if latest price is more than 4 trading days old

    If no price is available, sets all the above to None / 0.
    """
    from datetime import datetime, timezone, timedelta
    from bson import Decimal128

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
        holding_doc["price_as_of"] = None
        holding_doc["price_stale"] = True
        return holding_doc

    qty = _to_dec(holding_doc["quantity"])
    avg_cost = _to_dec(holding_doc["avg_cost"])
    invested = _to_dec(holding_doc["invested_amount"])
    current_price = _to_dec(latest_price_doc["close"])
    current_value = (qty * current_price).quantize(Decimal("0.01"))
    unrealized_pnl = (current_value - invested).quantize(Decimal("0.01"))
    pnl_pct = float((unrealized_pnl / invested) * 100) if invested > 0 else None

    price_date = latest_price_doc["date"]
    if price_date.tzinfo is None:
        price_date = price_date.replace(tzinfo=timezone.utc)
    is_stale = (datetime.now(timezone.utc) - price_date) > timedelta(
        days=6
    )  # 4 trading days ≈ 6 calendar

    holding_doc["current_price"] = current_price
    holding_doc["current_value"] = current_value
    holding_doc["unrealized_pnl"] = unrealized_pnl
    holding_doc["unrealized_pnl_pct"] = (
        round(pnl_pct, 2) if pnl_pct is not None else None
    )
    holding_doc["price_as_of"] = price_date
    holding_doc["price_stale"] = is_stale

    return holding_doc
