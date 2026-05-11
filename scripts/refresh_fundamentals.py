"""Refresh fundamentals for the NIFTY 100 universe (or specific symbols).

Designed to run weekly via cron. yfinance throttles aggressive callers, so
we sleep ~0.3s between calls. Total runtime for NIFTY 100 ≈ 60-90s.

Usage:
  # Refresh entire NIFTY 100 universe (cron entry point)
  PYTHONPATH=. uv run python scripts/refresh_fundamentals.py

  # Refresh specific symbols only
  PYTHONPATH=. uv run python scripts/refresh_fundamentals.py --symbols INFY,TCS

  # Refresh held stocks only (smaller, faster)
  PYTHONPATH=. uv run python scripts/refresh_fundamentals.py --holdings-only

  # Diagnostic: refresh just first N from universe
  PYTHONPATH=. uv run python scripts/refresh_fundamentals.py --limit 5
"""

from __future__ import annotations

import argparse
import logging
import sys

from app.db.client import Collections
from app.services.fundamentals_service import refresh_universe

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


def get_nifty100() -> list[dict]:
    return list(
        Collections.instruments().find(
            {"in_nifty100": True},
            {"_id": 0, "isin": 1, "symbol": 1, "exchange": 1},
        )
    )


def get_active_holdings() -> list[dict]:
    return list(
        Collections.holdings().find(
            {"deleted_at": None},
            {"_id": 0, "isin": 1, "symbol": 1, "exchange": 1},
        )
    )


def get_specific(symbols: list[str]) -> list[dict]:
    return list(
        Collections.instruments().find(
            {"exchange": "NSE", "symbol": {"$in": [s.upper() for s in symbols]}},
            {"_id": 0, "isin": 1, "symbol": 1, "exchange": 1},
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh fundamentals via yfinance")
    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Comma-separated NSE symbols (overrides default NIFTY 100 target)",
    )
    parser.add_argument(
        "--holdings-only",
        action="store_true",
        help="Refresh fundamentals for currently-held stocks only",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Diagnostic: process only the first N stocks",
    )
    parser.add_argument(
        "--throttle",
        type=float,
        default=0.3,
        help="Seconds to sleep between yfinance calls (default 0.3)",
    )
    args = parser.parse_args()

    if args.symbols:
        symbol_list = [s.strip() for s in args.symbols.split(",") if s.strip()]
        targets = get_specific(symbol_list)
        if not targets:
            print(f"❌ None of the symbols found in instruments: {symbol_list}")
            return 1
        mode = f"specific symbols ({len(targets)})"
    elif args.holdings_only:
        targets = get_active_holdings()
        mode = f"active holdings ({len(targets)})"
    else:
        targets = get_nifty100()
        mode = f"NIFTY 100 universe ({len(targets)})"

    if args.limit:
        targets = targets[: args.limit]
        mode += f" — LIMITED to {len(targets)}"

    print(f"Fundamentals refresh — target: {mode}")
    print()

    stats = refresh_universe(targets, throttle_sec=args.throttle)

    print()
    print("=" * 60)
    print(f"  Attempted: {stats['attempted']}")
    print(f"  Succeeded: {stats['succeeded']}")
    print(f"  Failed:    {stats['failed']}")
    if stats["failed_isins"]:
        print(f"  Failed ISINs (first 10): {stats['failed_isins'][:10]}")
    print("=" * 60)

    return 0 if stats["failed"] < stats["attempted"] else 1


if __name__ == "__main__":
    sys.exit(main())
