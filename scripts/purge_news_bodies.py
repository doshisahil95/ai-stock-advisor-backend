"""Cron entry: purge stale news article bodies (storage hygiene).

Runs daily at 02:30 IST. For every classified news_articles doc older than the
retention window (by fetched_at), $unset the bulky body_text field and stamp
body_purged_at. The classification fields (sentiment / themes / severity /
classifier_summary) are kept — only the raw body, which has already served the
Haiku classifier, is reclaimed.

P2-4 / master_todo #13 / TD27.

Age is keyed on fetched_at (always present via default_factory=utcnow);
published_at is nullable so it is deliberately NOT used. Idempotent: docs already
purged (body_purged_at set) are excluded, so re-runs are no-ops. --dry-run
reports the candidate count without writing.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import timedelta

from app.db.client import Collections
from app.models._common import utcnow
from app.services.cron_heartbeat_service import cron_run

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# Bodies are only needed until the classifier has run; 30 days leaves a generous
# window for re-classification / debugging before the space is reclaimed.
RETENTION_DAYS = 30


def main() -> int:
    parser = argparse.ArgumentParser(description="Purge stale news article bodies.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report how many bodies would be purged without writing.",
    )
    args = parser.parse_args()

    with cron_run("purge_news_bodies") as hb:
        now = utcnow()
        cutoff = now - timedelta(days=RETENTION_DAYS)
        hb.metadata["retention_days"] = RETENTION_DAYS
        hb.metadata["cutoff"] = cutoff.isoformat()
        hb.metadata["dry_run"] = args.dry_run

        # Classified, older than the window, not already purged, still carrying a
        # body. fetched_at (not published_at) defines age — see master_todo #13.
        query = {
            "classified": True,
            "fetched_at": {"$lt": cutoff},
            "body_purged_at": None,
            "body_text": {"$nin": ["", None]},
        }
        coll = Collections.news_articles()

        candidates = coll.count_documents(query)
        hb.metadata["candidates"] = candidates

        if candidates == 0:
            log.info("No stale news bodies to purge (cutoff %s)", cutoff.isoformat())
            hb.mark_skipped("no_expired_bodies")
            return 0

        if args.dry_run:
            log.info(
                "[dry-run] would purge %d news bodies (cutoff %s)",
                candidates,
                cutoff.isoformat(),
            )
            return 0

        result = coll.update_many(
            query,
            {"$unset": {"body_text": ""}, "$set": {"body_purged_at": now}},
        )
        hb.metadata["purged"] = result.modified_count
        log.info(
            "Purged %d news bodies (cutoff %s)",
            result.modified_count,
            cutoff.isoformat(),
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
