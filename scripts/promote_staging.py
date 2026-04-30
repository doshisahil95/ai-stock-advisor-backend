"""Promote transactions_staging to live transactions + recompute holdings.

Copies all docs from transactions_staging into the real transactions collection,
then runs recompute_holding(isin) for every distinct ISIN to rebuild holdings.

Idempotent-ish: requires --confirm to actually run, and you can specify --wipe-live
to clear existing transactions/holdings before promoting (recommended on first import).

Usage:
    PYTHONPATH=. uv run python scripts/promote_staging.py --confirm
    PYTHONPATH=. uv run python scripts/promote_staging.py --confirm --wipe-live
"""

from __future__ import annotations

import argparse
import logging
import sys

from app.db.client import Collections
from app.services.holdings_service import recompute_holding

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote staging → live transactions")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually perform the promotion (otherwise just dry-run)",
    )
    parser.add_argument(
        "--wipe-live",
        action="store_true",
        help="Wipe live transactions/holdings before promote (use on first import)",
    )
    args = parser.parse_args()

    staging = Collections.transactions_staging()
    transactions = Collections.transactions()
    holdings = Collections.holdings()

    staging_count = staging.estimated_document_count()
    if staging_count == 0:
        print("⚠️  transactions_staging is empty. Nothing to promote.")
        return 1

    print(f"Staging: {staging_count} transactions ready to promote")
    print(
        f"Live:    {transactions.estimated_document_count()} transactions, "
        f"{holdings.count_documents({'deleted_at': None})} active holdings"
    )

    if not args.confirm:
        print()
        print("DRY RUN — no changes made. Re-run with --confirm to actually promote.")
        if args.wipe_live:
            print("(Would also wipe live transactions and holdings before promote.)")
        return 0

    if args.wipe_live:
        d1 = transactions.delete_many({}).deleted_count
        d2 = holdings.delete_many({}).deleted_count
        print(f"Wiped live: {d1} transactions, {d2} holdings")

    # Copy staging → live
    staging_docs = list(staging.find({}))
    # Strip the _id from staging so Mongo generates fresh ones for live
    for doc in staging_docs:
        doc.pop("_id", None)

    if staging_docs:
        result = transactions.insert_many(staging_docs, ordered=False)
        print(
            f"✓ Inserted {len(result.inserted_ids)} transactions into live collection"
        )

    # Recompute every distinct ISIN
    distinct_isins = transactions.distinct("isin")
    print(f"\nRecomputing {len(distinct_isins)} holdings...")
    success = failed = 0
    for isin in distinct_isins:
        try:
            holding = recompute_holding(isin)
            success += 1
            if holding:
                log.info(
                    "  ✓ %s (%s): qty=%s avg=%s",
                    holding.symbol,
                    isin,
                    holding.quantity,
                    holding.avg_cost,
                )
        except Exception as exc:
            failed += 1
            log.error("  ✗ %s: %s", isin, exc)

    print(f"\nRecompute complete: {success} succeeded, {failed} failed")
    print()
    print(
        f"Live now: {transactions.estimated_document_count()} transactions, "
        f"{holdings.count_documents({'deleted_at': None})} active holdings"
    )
    print()
    print("✅ Promotion complete. Verify via:")
    print("   curl http://127.0.0.1:8000/portfolio/holdings | python3 -m json.tool")
    print()
    print("If something looks wrong, you can wipe and re-import:")
    print("   PYTHONPATH=. uv run python scripts/import_orderbooks.py --wipe")
    print(
        "   PYTHONPATH=. uv run python scripts/promote_staging.py --confirm --wipe-live"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
