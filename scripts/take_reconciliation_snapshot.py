"""Cron entry: take an auto reconciliation snapshot daily."""

from __future__ import annotations

import logging
import sys

from app.services.cron_heartbeat_service import cron_run
from app.services.reconciliation import take_auto_snapshot

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def main() -> int:
    with cron_run("take_reconciliation_snapshot") as hb:
        snap = take_auto_snapshot()
        hb.metadata["our_invested"] = str(snap["our_invested"])
        hb.metadata["our_current_value"] = str(snap["our_current_value"])
        hb.metadata["our_day_gain"] = str(snap["our_day_gain"])
        log.info(
            "Auto snapshot taken: invested=%s, current=%s, day_gain=%s",
            snap["our_invested"],
            snap["our_current_value"],
            snap["our_day_gain"],
        )
        if snap.get("notes"):
            log.warning("Snapshot note: %s", snap["notes"])
            hb.metadata["notes"] = snap["notes"]
        return 0


if __name__ == "__main__":
    sys.exit(main())
