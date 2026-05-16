"""Refresh daily OHLCV prices from yfinance into MongoDB.

By default, refreshes the last 7 days of data for:
  - All currently-held stocks
  - All monitored stocks (Phase 2+)
  - NIFTY 100 universe (if loaded)

Usage:
    # Daily incremental refresh (cron entry point)
    PYTHONPATH=. uv run python scripts/refresh_prices.py

    # Initial 5-year backfill
    PYTHONPATH=. uv run python scripts/refresh_prices.py --backfill-years 5

    # Refresh specific symbols only
    PYTHONPATH=. uv run python scripts/refresh_prices.py --symbols INFY,TCS

    # Just fetch prices for currently-held stocks (skip NIFTY 100)
    PYTHONPATH=. uv run python scripts/refresh_prices.py --holdings-only
"""

from __future__ import annotations

import argparse
import logging
import sys

from app.db.client import Collections
from app.services.cron_heartbeat_service import cron_run
from app.services.price_service import fetch_eod_prices, upsert_prices

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


def get_active_holdings() -> list[dict]:
    """All currently-held stocks (deleted_at = null)."""
    return list(
        Collections.holdings().find(
            {"deleted_at": None},
            {"_id": 0, "isin": 1, "symbol": 1, "exchange": 1},
        )
    )


def get_monitored() -> list[dict]:
    """All monitored stocks (status = 'tracking')."""
    return list(
        Collections.monitored_stocks().find(
            {"status": "tracking"},
            {"_id": 0, "isin": 1, "symbol": 1, "exchange": 1},
        )
    )


def get_nifty100() -> list[dict]:
    """All NIFTY 100 instruments (loaded by seed_nifty100.py)."""
    return list(
        Collections.instruments().find(
            {"in_nifty100": True},
            {"_id": 0, "isin": 1, "symbol": 1, "exchange": 1},
        )
    )


def get_specific_symbols(symbols: list[str]) -> list[dict]:
    """Look up metadata for specific symbols (NSE only — for ad-hoc use)."""
    return list(
        Collections.instruments().find(
            {"exchange": "NSE", "symbol": {"$in": [s.upper() for s in symbols]}},
            {"_id": 0, "isin": 1, "symbol": 1, "exchange": 1},
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh prices from yfinance")
    parser.add_argument(
        "--backfill-years",
        type=int,
        default=None,
        help="One-time backfill: fetch this many years of history (e.g., 5)",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Comma-separated list of NSE symbols (overrides default targets)",
    )
    parser.add_argument(
        "--holdings-only",
        action="store_true",
        help="Only refresh currently-held stocks (skip monitored + NIFTY 100)",
    )
    args = parser.parse_args()

    with cron_run("refresh_prices") as hb:
        hb.metadata["backfill_years"] = args.backfill_years
        hb.metadata["holdings_only"] = args.holdings_only
        hb.metadata["explicit_symbols"] = args.symbols

        # Determine target stocks
        if args.symbols:
            symbols_list = [s.strip() for s in args.symbols.split(",") if s.strip()]
            targets = get_specific_symbols(symbols_list)
            if not targets:
                print(f"⚠ None of the symbols found in instruments: {symbols_list}")
                hb.status = "failure"
                hb.error = f"No matching instruments for {symbols_list}"
                return 1
        else:
            targets = get_active_holdings()
            if not args.holdings_only:
                seen = {h["isin"] for h in targets}
                for m in get_monitored():
                    if m["isin"] not in seen:
                        targets.append(m)
                        seen.add(m["isin"])
                for n in get_nifty100():
                    if n["isin"] not in seen:
                        targets.append(n)
                        seen.add(n["isin"])

        hb.metadata["targets"] = len(targets)
        print(f"Fetching prices for {len(targets)} stocks")

        # Determine days to fetch
        if args.backfill_years:
            days_back = args.backfill_years * 365
            print(
                f"BACKFILL mode: {args.backfill_years} years (~{days_back} calendar days)"
            )
        else:
            days_back = 7  # Daily refresh — small overlap to handle weekends/holidays
            print(f"INCREMENTAL mode: last {days_back} days")

        # Fetch
        rows = fetch_eod_prices(targets, days_back=days_back)

        if not rows:
            print("⚠  No price rows fetched. Yahoo may be having issues.")
            hb.status = "failure"
            hb.error = "No price rows fetched from yfinance"
            return 1

        print(f"\nFetched {len(rows)} OHLCV rows. Upserting...")
        result = upsert_prices(rows)
        hb.metadata["rows_fetched"] = len(rows)
        hb.metadata["upserted"] = result["upserted"]
        hb.metadata["modified"] = result["modified"]
        hb.metadata["total"] = result["total"]
        print(f"   Upserted: {result['upserted']}")
        print(f"   Modified: {result['modified']}")
        print(f"   Total in prices_daily: {result['total']}")
        print()
        print("✓ Price refresh complete")
        return 0


if __name__ == "__main__":
    sys.exit(main())
