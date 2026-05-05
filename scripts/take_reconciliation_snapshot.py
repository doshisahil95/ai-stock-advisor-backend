"""Cron entry: take an auto reconciliation snapshot daily."""

from __future__ import annotations

import logging
import sys

from app.services.reconciliation import take_auto_snapshot

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def main() -> int:
    snap = take_auto_snapshot()
    log.info(
        "Auto snapshot taken: invested=₹%s, current=₹%s, day_gain=₹%s",
        snap["our_invested"],
        snap["our_current_value"],
        snap["our_day_gain"],
    )
    if snap.get("notes"):
        log.warning("Snapshot note: %s", snap["notes"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
