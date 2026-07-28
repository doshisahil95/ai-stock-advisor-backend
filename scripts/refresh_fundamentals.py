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
from app.services.fundamentals_service import (
    refresh_dividends_universe,
    refresh_earnings_universe,
    refresh_universe,
)
from app.services.cron_heartbeat_service import cron_run
from app.services.suggestion_engine import get_watchlist_isins

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


def get_watchlist_instruments() -> list[dict]:
    """Watchlisted ISINs resolved to instrument dicts (F13).

    Reuses suggestion_engine.get_watchlist_isins() -- the single source of
    truth for watchlist membership (status=="watchlist") -- and resolves to
    {isin, symbol, exchange} from instruments. Watchlist names are typically
    outside NIFTY 100, so without this they would never get weekly
    fundamentals/earnings. This is part of the F13 data-volume multiplier.
    """
    isins = get_watchlist_isins()
    if not isins:
        return []
    return list(
        Collections.instruments().find(
            {"isin": {"$in": list(isins)}},
            {"_id": 0, "isin": 1, "symbol": 1, "exchange": 1},
        )
    )


def get_nifty100_union_holdings() -> list[dict]:
    """Default universe for the weekly refresh: NIFTY 100 ∪ active holdings.

    Held stocks may be outside NIFTY 100 (e.g. midcaps). They still need
    fresh fundamentals + earnings for F2 sell-side scoring.

    F13: watchlisted ISINs (status=="watchlist") are also folded in here --
    they are typically outside NIFTY 100 and would otherwise never receive
    weekly fundamentals/earnings. Part of the data-volume multiplier.
    """
    seen: set[str] = set()
    targets: list[dict] = []
    for inst in get_nifty100() + get_active_holdings() + get_watchlist_instruments():
        isin = inst["isin"]
        if isin in seen:
            continue
        seen.add(isin)
        targets.append(inst)
    return targets


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

    # #75 U4-a: the ENTIRE refresh runs INSIDE the cron_run block. Previously the
    # `with` closed after only the three metadata assignments, so refresh_universe
    # / refresh_earnings_universe / refresh_dividends_universe (and the exit code)
    # ran OUTSIDE it — the heartbeat was written "success" immediately and any
    # Sunday fundamentals/earnings/dividends failure was invisible to F4. Now a
    # crash anywhere below is caught by cron_run and recorded as a failure
    # heartbeat, and the per-step stats persist to hb.metadata for forensics.
    with cron_run("refresh_fundamentals") as hb:
        hb.metadata["holdings_only"] = args.holdings_only
        hb.metadata["explicit_symbols"] = args.symbols
        hb.metadata["limit"] = args.limit

        if args.symbols:
            symbol_list = [s.strip() for s in args.symbols.split(",") if s.strip()]
            targets = get_specific(symbol_list)
            if not targets:
                print(f" None of the symbols found in instruments: {symbol_list}")
                hb.mark_skipped("no_matching_symbols")
                return 1
            mode = f"specific symbols ({len(targets)})"
        elif args.holdings_only:
            targets = get_active_holdings()
            mode = f"active holdings ({len(targets)})"
        else:
            targets = get_nifty100_union_holdings()
            mode = f"NIFTY 100  active holdings ({len(targets)})"

        if args.limit:
            targets = targets[: args.limit]
            mode += f"  LIMITED to {len(targets)}"

        hb.metadata["mode"] = mode
        hb.metadata["targets"] = len(targets)
        print(f"Fundamentals refresh  target: {mode}")
        print()

        stats = refresh_universe(targets, throttle_sec=args.throttle)
        hb.metadata["fundamentals"] = {
            "attempted": stats["attempted"],
            "succeeded": stats["succeeded"],
            "failed": stats["failed"],
        }

        print()
        print("=" * 60)
        print("Fundamentals refresh:")
        print(f"  Attempted: {stats['attempted']}")
        print(f"  Succeeded: {stats['succeeded']}")
        print(f"  Failed:    {stats['failed']}")
        if stats["failed_isins"]:
            print(f"  Failed ISINs (first 10): {stats['failed_isins'][:10]}")
        print("=" * 60)

        # F14: earnings calendar refresh for the same universe.
        # Shares the yfinance round-trip with fundamentals (same Ticker object
        # produced upstream) but is logically separate so its stats are visible.
        print()
        print(f"Earnings calendar refresh  target: same {len(targets)} instruments")
        print()
        earnings_stats = refresh_earnings_universe(targets, throttle_sec=args.throttle)
        hb.metadata["earnings"] = {
            "attempted": earnings_stats["attempted"],
            "succeeded_with_events": earnings_stats["succeeded_with_events"],
            "succeeded_no_events": earnings_stats["succeeded_no_events"],
            "failed": earnings_stats["failed"],
            "total_events_inserted": earnings_stats["total_events_inserted"],
        }

        print()
        print("=" * 60)
        print("Earnings calendar refresh:")
        print(f"  Attempted:               {earnings_stats['attempted']}")
        print(f"  Succeeded with events:   {earnings_stats['succeeded_with_events']}")
        print(f"  Succeeded with NO events:{earnings_stats['succeeded_no_events']}")
        print(f"  Failed:                  {earnings_stats['failed']}")
        print(f"  Total events stored:     {earnings_stats['total_events_inserted']}")
        if earnings_stats["failed_isins"]:
            print(f"  Failed ISINs (first 10): {earnings_stats['failed_isins'][:10]}")
        print("=" * 60)

        # #65: dividend-announcement capture for the SAME universe. Guarded so a
        # yfinance dividends hiccup can never fail the fundamentals/earnings run
        # (mirrors the guarded-caller pattern used for the alert evaluators). This
        # is the "announced" leg of the dividend-drift matrix; a dividend is a real
        # gain (feeds total_dividends_* via #63/#64) so a missed payout understates
        # realised gain — the reconciliation matrix flags that.
        dividend_stats = None
        try:
            print()
            print(f"Dividend announcements refresh  target: same {len(targets)} instruments")
            print()
            dividend_stats = refresh_dividends_universe(targets, throttle_sec=args.throttle)
            hb.metadata["dividends"] = {
                "attempted": dividend_stats["attempted"],
                "succeeded_with_dividends": dividend_stats["succeeded_with_dividends"],
                "succeeded_no_dividends": dividend_stats["succeeded_no_dividends"],
                "failed": dividend_stats["failed"],
                "total_announcements_inserted": dividend_stats[
                    "total_announcements_inserted"
                ],
            }

            print()
            print("=" * 60)
            print("Dividend announcements refresh:")
            print(f"  Attempted:                  {dividend_stats['attempted']}")
            print(f"  Succeeded with dividends:   {dividend_stats['succeeded_with_dividends']}")
            print(f"  Succeeded with NO dividends:{dividend_stats['succeeded_no_dividends']}")
            print(f"  Failed:                     {dividend_stats['failed']}")
            print(f"  Total announcements stored: {dividend_stats['total_announcements_inserted']}")
            if dividend_stats["failed_isins"]:
                print(f"  Failed ISINs (first 10): {dividend_stats['failed_isins'][:10]}")
            print("=" * 60)
        except Exception:
            log.exception("Dividend-announcement refresh failed (non-fatal)")
            hb.metadata["dividends_error"] = True

        # Exit non-zero only if BOTH primary steps mostly failed. The dividend
        # leg is best-effort and never affects the exit code.
        fundamentals_ok = stats["failed"] < stats["attempted"]
        earnings_ok = earnings_stats["failed"] < earnings_stats["attempted"]
        exit_code = 0 if (fundamentals_ok or earnings_ok) else 1
        # #75 U4-a: if both primary steps mostly failed, mark the heartbeat a
        # failure so F4 alerts (cron_run only auto-fails on an exception; a
        # "mostly failed but no raise" run would otherwise look healthy).
        if exit_code != 0:
            hb.status = "failure"
            hb.error = (
                f"fundamentals failed={stats['failed']}/{stats['attempted']}, "
                f"earnings failed={earnings_stats['failed']}/"
                f"{earnings_stats['attempted']}"
            )
        return exit_code


if __name__ == "__main__":
    sys.exit(main())
