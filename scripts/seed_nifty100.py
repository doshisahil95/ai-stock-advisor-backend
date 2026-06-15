"""Seed the NIFTY 100 universe — mark NSE instruments as `in_nifty100: true`.

Source: NIFTY 100 constituent list. We fetch the official CSV from NSE archives.
NSE blocks generic UAs, so we send a browser User-Agent.

After running this, the price-refresh script will include NIFTY 100 in its
default targets. This expands the agent's "scanning universe" beyond just
your holdings.

Usage:
    PYTHONPATH=. uv run python scripts/seed_nifty100.py
"""

from __future__ import annotations

import csv
import io
import logging
import sys
from datetime import datetime, timezone

import requests
from pymongo import UpdateOne

from app.db.client import Collections
from app.services.price_service import fetch_eod_prices, upsert_prices
from app.models._common import utcnow

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger(__name__)

NIFTY100_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty100list.csv"

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/csv,application/csv,*/*",
}


def fetch_nifty100_symbols() -> list[str]:
    """Fetch NIFTY 100 constituent list from NSE."""
    log.info("Downloading NIFTY 100 constituent list from %s", NIFTY100_URL)
    response = requests.get(NIFTY100_URL, headers=_BROWSER_HEADERS, timeout=30)
    response.raise_for_status()
    log.info("Downloaded %d bytes", len(response.content))

    reader = csv.DictReader(io.StringIO(response.text))
    symbols: list[str] = []
    for raw_row in reader:
        row = {k.strip(): (v.strip() if v else "") for k, v in raw_row.items()}
        symbol = row.get("Symbol", "").upper()
        if symbol:
            symbols.append(symbol)

    log.info("Parsed %d NIFTY 100 symbols", len(symbols))
    return symbols


def mark_nifty100_in_instruments(symbols: list[str]) -> dict:
    """Set `in_nifty100: true` on matched NSE instruments."""
    if not symbols:
        return {"matched": 0, "modified": 0}

    coll = Collections.instruments()
    now = utcnow()

    # Find which symbols actually exist in our instruments
    matched_docs = list(
        coll.find(
            {"exchange": "NSE", "symbol": {"$in": symbols}},
            {"_id": 0, "isin": 1, "symbol": 1, "exchange": 1},
        )
    )
    matched_symbols = {d["symbol"] for d in matched_docs}
    not_matched = set(symbols) - matched_symbols
    if not_matched:
        log.warning(
            "Symbols in NIFTY 100 list but not in instruments: %s", sorted(not_matched)
        )

    # Set the flag
    operations = [
        UpdateOne(
            {"exchange": "NSE", "symbol": sym},
            {"$set": {"in_nifty100": True, "nifty100_marked_at": now}},
        )
        for sym in matched_symbols
    ]
    if operations:
        result = coll.bulk_write(operations, ordered=False)
        return {
            "matched_in_instruments": len(matched_symbols),
            "modified": result.modified_count,
            "not_matched": sorted(not_matched),
            "stocks_to_backfill": matched_docs,
        }
    return {
        "matched_in_instruments": 0,
        "modified": 0,
        "not_matched": list(not_matched),
        "stocks_to_backfill": [],
    }


def main() -> int:
    print("=" * 70)
    print("  Seeding NIFTY 100 universe")
    print("=" * 70)
    print()

    # Step 1: fetch list
    print("Step 1: Fetching NIFTY 100 constituent list...")
    try:
        symbols = fetch_nifty100_symbols()
        print(f"  ✓ {len(symbols)} symbols in NIFTY 100")
    except Exception as exc:
        print(f"  ✗ Failed: {exc}")
        return 1

    # Step 2: mark in instruments collection
    print()
    print("Step 2: Marking NIFTY 100 in instruments collection...")
    result = mark_nifty100_in_instruments(symbols)
    print(f"  ✓ Matched: {result['matched_in_instruments']}")
    print(f"  ✓ Modified: {result['modified']}")
    if result.get("not_matched"):
        print(
            f"  ⚠️  Not in instruments ({len(result['not_matched'])}): "
            f"{', '.join(result['not_matched'][:10])}"
            + ("..." if len(result["not_matched"]) > 10 else "")
        )

    # Step 3: backfill 5y price history for these stocks
    backfill_targets = result.get("stocks_to_backfill", [])
    if not backfill_targets:
        print("\nNo stocks to backfill.")
        return 0

    print(
        f"\nStep 3: Backfilling 5-year price history for {len(backfill_targets)} NIFTY 100 stocks..."
    )
    print("        (This will take a few minutes — be patient)")
    rows = fetch_eod_prices(backfill_targets, days_back=5 * 365)
    print(f"  ✓ Fetched {len(rows)} price rows")

    if rows:
        upsert_result = upsert_prices(rows)
        print(f"  ✓ Upserted: {upsert_result['upserted']}")
        print(f"  ✓ Modified: {upsert_result['modified']}")
        print(f"  ✓ Total prices_daily docs: {upsert_result['total']}")

    print()
    print("✅ NIFTY 100 seeding complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
