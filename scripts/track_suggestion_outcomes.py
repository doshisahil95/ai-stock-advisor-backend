"""Daily cron — snapshot prices for open suggestion outcomes."""

from __future__ import annotations

import logging
import sys

from app.services.outcome_tracker import snapshot_open_outcomes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def main() -> int:
    print("=" * 70)
    print(" Suggestion outcome tracking")
    print("=" * 70)

    stats = snapshot_open_outcomes()

    print()
    print(f"  Open outcomes:     {stats['open_outcomes']}")
    print(f"  Snapshots 30d:     {stats['snapshots_30d']}")
    print(f"  Snapshots 60d:     {stats['snapshots_60d']}")
    print(f"  Snapshots 90d:     {stats['snapshots_90d']}")
    print(f"  Snapshots 180d:    {stats['snapshots_180d']}")
    print(f"  Expired (>180d):   {stats['expired']}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
