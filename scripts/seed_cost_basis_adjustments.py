"""Seed the cost_basis_adjustments collection with the known adjustments.

Idempotent: skips inserts where (name, effective_date) already exists.

Run once to bootstrap. Re-run safely whenever you add new adjustments here.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal

from app.db.client import Collections
from app.models._common import _convert_decimals_to_decimal128, utcnow

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# Currently-known divergences, derived from add_manual_transactions.py.
# Add more entries here as new corporate actions create tax-basis vs broker-basis gaps.
ADJUSTMENTS = [
    {
        "name": "Tata Motors demerger — TMPV/TMCV cost split",
        "isin": "INE1TAE01010",  # TMCV
        "related_isins": ["INE155A01022"],  # TMPV
        "amount": Decimal("-24244.83"),
        "it_act_section": "Section 49(2C) of the Income Tax Act, 1961",
        "effective_date": datetime(2025, 10, 1, tzinfo=timezone.utc),
        "calculation": (
            "Pre-demerger: 100 TMPV held at ₹813.37 avg cost = ₹81,337 invested.\n"
            "Section 49(2C) requires the original cost to be apportioned between the "
            "resulting and demerged companies in proportion to their net book values "
            "at the date of demerger.\n"
            "Tata Motors' apportionment: 68.85% to TMPV (kept), 31.15% to TMCV (new).\n"
            "Post-demerger:\n"
            "  TMPV: 100 × ₹813.37 × 68.85% = ₹55,999.96 (avg cost ₹559.99)\n"
            "  TMCV: 100 × ₹813.37 × 31.15% = ₹25,336.47 (avg cost ₹253.36)\n"
            "  Total preserved: ₹81,336.43 (rounding ₹0.57)"
        ),
        "broker_treatment": (
            "ICICI continues to show the original ₹81,337 against TMPV alone "
            "and ₹0 against TMCV. This over-counts 'invested' by ₹24,244.83 "
            "(the portion that should have been allocated to TMCV)."
        ),
        "our_treatment": (
            "All TMPV BUY transactions in our database have their price field "
            "multiplied by 0.6885 (idempotent, marked with DEMERGER_ADJUSTED tag). "
            "A new BUY transaction was created for TMCV at ₹253.36/share, "
            "100 shares, dated 01-Oct-2025."
        ),
        "rationale": (
            "When the user eventually sells TMPV or TMCV, the capital-gains "
            "computation MUST use the apportioned cost basis (Section 49(2C)). "
            "Using the broker's unapportioned figure would over-state cost on "
            "TMPV (under-counting tax) and under-state cost on TMCV (over-counting tax). "
            "Both errors are scrutinable by an AO during assessment."
        ),
        "source_documents": [
            "Tata Motors PIB notice on demerger record date (Sep 2025)",
            "Section 49(2C), Income Tax Act 1961",
            "ICICI demat statement — TMCV credit on 02-Oct-2025",
        ],
        "active": True,
    },
]


def main() -> int:
    coll = Collections.cost_basis_adjustments()
    inserted = 0
    skipped = 0

    for adj in ADJUSTMENTS:
        existing = coll.find_one(
            {
                "name": adj["name"],
                "effective_date": adj["effective_date"],
            }
        )
        if existing:
            log.info("Skipping (already exists): %s", adj["name"])
            skipped += 1
            continue

        doc = dict(adj)
        doc["_schema_version"] = 1
        doc["created_at"] = utcnow()
        doc["updated_at"] = utcnow()
        coll.insert_one(_convert_decimals_to_decimal128(doc))
        log.info("Inserted: %s (₹%s)", adj["name"], adj["amount"])
        inserted += 1

    log.info("Done — %d inserted, %d skipped", inserted, skipped)
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
