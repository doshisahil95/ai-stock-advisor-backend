"""Cron entry: refresh intraday quotes for active holdings.

Runs every 15 min during NSE market hours (Mon-Fri 09:15-15:45 IST).
Inserts new docs into prices_intraday — no upsert (we want history).
"""

from __future__ import annotations

import logging
import sys

from app.db.client import Collections
from app.services.cron_heartbeat_service import cron_run
from app.services.price_service import (
    fetch_intraday_quotes,
    insert_intraday_quotes,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def main() -> int:
    with cron_run("refresh_prices_intraday") as hb:
        holdings = list(
            Collections.holdings().find(
                {"deleted_at": None},
                {"isin": 1, "symbol": 1, "exchange": 1},
            )
        )
        if not holdings:
            log.info("No active holdings — nothing to refresh")
            hb.mark_skipped("no_active_holdings")
            return 0

        hb.metadata["holdings"] = len(holdings)
        log.info("Intraday refresh for %d active holdings", len(holdings))
        rows = fetch_intraday_quotes(holdings)

        if not rows:
            log.info("No intraday data returned (market closed?)")
            hb.mark_skipped("market_closed_or_no_data")
            return 0

        inserted = insert_intraday_quotes(rows)
        hb.metadata["rows_fetched"] = len(rows)
        hb.metadata["rows_inserted"] = inserted
        log.info("Intraday refresh complete: %d inserted", inserted)
        return 0


if __name__ == "__main__":
    sys.exit(main())
