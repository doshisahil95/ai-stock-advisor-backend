"""Cron entry: take an auto reconciliation snapshot daily."""

from __future__ import annotations

import logging
import sys

from app.services.cron_heartbeat_service import cron_run
from app.services.reconciliation import (
    evaluate_dividend_drift_alerts,
    take_auto_snapshot,
)

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

        # #65: nudge on any NEW unrecorded dividend (announced ex-date passed
        # while held, no DIVIDEND row). Guarded so a dividend-drift failure can
        # never fail the primary reconciliation snapshot (mirrors the guarded
        # alert-evaluator callers). Rising-edge deduped inside the evaluator.
        try:
            nudges = evaluate_dividend_drift_alerts()
            hb.metadata["dividend_drift_nudges"] = nudges
            if nudges:
                log.info("Dividend-drift nudges fired: %d", nudges)
        except Exception:
            log.exception("evaluate_dividend_drift_alerts failed (non-fatal)")
            hb.metadata["dividend_drift_error"] = True

        return 0


if __name__ == "__main__":
    sys.exit(main())
