"""Daily cron — snapshot prices for open suggestion outcomes."""

from __future__ import annotations

import logging
import sys

from app.services.cron_heartbeat_service import cron_run
from app.services.outcome_tracker import snapshot_open_outcomes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def main() -> int:
    print("=" * 70)
    print(" Suggestion outcome tracking")
    print("=" * 70)

    with cron_run("track_suggestion_outcomes") as hb:
        stats = snapshot_open_outcomes()

        hb.metadata.update(
            {
                # #47/TD22: service returns "active_outcomes" (renamed in
                # Commit A.5 when selection broadened from "open" to all
                # non-expired). Reading the stale "open_outcomes" key raised
                # KeyError every run -> 1 failure/0 success daily -> F4 email.
                "active_outcomes": stats["active_outcomes"],
                "snapshots_30d": stats["snapshots_30d"],
                "snapshots_60d": stats["snapshots_60d"],
                "snapshots_90d": stats["snapshots_90d"],
                "snapshots_180d": stats["snapshots_180d"],
                "expired": stats["expired"],
            }
        )

        print()
        print(f"  Active outcomes:   {stats['active_outcomes']}")
        print(f"  Snapshots 30d:     {stats['snapshots_30d']}")
        print(f"  Snapshots 60d:     {stats['snapshots_60d']}")
        print(f"  Snapshots 90d:     {stats['snapshots_90d']}")
        print(f"  Snapshots 180d:    {stats['snapshots_180d']}")
        print(f"  Expired (>180d):   {stats['expired']}")
        print()
        return 0


if __name__ == "__main__":
    sys.exit(main())
