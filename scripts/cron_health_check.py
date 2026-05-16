"""F4: Daily cron health check (runs 21:00 IST).

Reads the cron registry (app.services.cron_heartbeat_service.CRON_REGISTRY),
compares against today's heartbeats in MongoDB, and fires a single batched
ntfy alert via push_public("errors", ...) if any expected cron:
  - did not run today, OR
  - ran but its latest run today was a failure, OR
  - ran fewer times today than min_runs_per_day.

The check itself writes a heartbeat (recursive — intentional).
If everything is healthy, no alert is sent. Silent success.

Usage (cron):
  0 21 * * * cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. \\
      /home/ubuntu/.local/bin/uv run python scripts/cron_health_check.py \\
      >> /home/ubuntu/cron-health.log 2>&1
"""

from __future__ import annotations

import logging
import sys

from app.services.cron_heartbeat_service import (
    count_today_heartbeats,
    cron_run,
    get_registry,
    is_expected_today,
    ist_today_window_utc,
)
from app.services.notify import push_public

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


def main() -> int:
    with cron_run("cron_health_check") as hb:
        today_start, tomorrow_start = ist_today_window_utc()
        anomalies: list[str] = []
        per_cron_status: list[dict] = []

        for spec in get_registry():
            # Skip ourselves — we're literally running right now, so a count
            # of 0 success would be a false alarm. Future runs see this one
            # via get_latest_per_cron.
            if spec.cron_name == "cron_health_check":
                continue

            expected = is_expected_today(spec)
            counts = count_today_heartbeats(
                spec.cron_name,
                ist_today_utc_start=today_start,
                ist_tomorrow_utc_start=tomorrow_start,
            )

            per_cron_status.append(
                {
                    "cron_name": spec.cron_name,
                    "expected": expected,
                    "counts": counts,
                }
            )

            if not expected:
                continue

            ran_ok = counts["success"] + counts["skipped"]
            if ran_ok < spec.min_runs_per_day:
                anomalies.append(
                    f"MISSING: {spec.cron_name} "
                    f"(expected {spec.min_runs_per_day}+ runs today, "
                    f"got {counts['success']} success + {counts['skipped']} skipped)"
                )
            if counts["failure"] > 0:
                anomalies.append(
                    f"FAILED: {spec.cron_name} ({counts['failure']} failure(s) today)"
                )

        hb.metadata["per_cron_status"] = per_cron_status
        hb.metadata["anomaly_count"] = len(anomalies)
        hb.metadata["anomalies"] = anomalies

        print("=" * 70)
        print(" Cron health check")
        print("=" * 70)
        for entry in per_cron_status:
            print(
                f"  {entry['cron_name']:32s} expected={entry['expected']} "
                f"counts={entry['counts']}"
            )
        print()

        if not anomalies:
            print("✓ All expected crons healthy.")
            return 0

        print(f"⚠ {len(anomalies)} anomaly/anomalies detected:")
        for a in anomalies:
            print(f"  - {a}")

        try:
            push_public(
                channel="errors",
                title=f"⚠ Cron health: {len(anomalies)} issue(s)",
                message="\n".join(anomalies),
                priority="high",
                tags=["warning", "cron"],
            )
            print("✓ Alert published to ntfy (errors channel)")
        except Exception:
            # If the alert itself fails, let cron_run record this run as a
            # failure so tomorrow's check surfaces it.
            log.exception("Failed to publish health alert")
            raise

        # Return 0 even on anomalies — the alert IS the signal. Returning
        # non-zero would itself mark this run as failed and double-count noise.
        return 0


if __name__ == "__main__":
    sys.exit(main())
