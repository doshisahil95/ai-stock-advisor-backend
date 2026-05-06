"""Cron entry: refresh intraday quotes for active holdings.

Runs every 15 min during NSE market hours (Mon-Fri 09:15-15:45 IST).
Inserts new docs into prices_intraday — no upsert (we want history).
"""

from __future__ import annotations

import logging
import sys

from app.db.client import Collections
from app.services.price_service import (
    fetch_intraday_quotes,
    insert_intraday_quotes,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def main() -> int:
    holdings = list(
        Collections.holdings().find(
            {"deleted_at": None},
            {"isin": 1, "symbol": 1, "exchange": 1},
        )
    )
    if not holdings:
        log.info("No active holdings — nothing to refresh")
        return 0

    log.info("Intraday refresh for %d active holdings", len(holdings))
    rows = fetch_intraday_quotes(holdings)

    if not rows:
        log.info("No intraday data returned (market closed?)")
        return 0

    inserted = insert_intraday_quotes(rows)
    log.info("Intraday refresh complete: %d inserted", inserted)
    return 0


if __name__ == "__main__":
    sys.exit(main())
