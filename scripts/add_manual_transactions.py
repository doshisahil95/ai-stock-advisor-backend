"""Add manual transactions to transactions_staging.

For things that don't appear in ICICI Order Book exports:
- IPO allotments
- Demerger cost basis adjustments
- Off-market transfers
- Bonuses, splits, etc.

Each transaction is explicitly defined below with full context. Re-run
import_orderbooks.py BEFORE this script to wipe staging and reload Order
Books, then this appends manual entries on top.

Usage:
    PYTHONPATH=. uv run python scripts/add_manual_transactions.py
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal

from app.db.client import Collections
from app.models._common import _convert_decimals_to_decimal128, utcnow
from app.services.holdings_service import validate_replay

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# ── Manual transactions to add ───────────────────────────────────────────────
# Each dict represents one transaction. ISINs verified against NSE master.

MANUAL_TRANSACTIONS = [
    # ── IPO Allotments ───────────────────────────────────────────────────────
    {
        "isin": "INE0J1Y01017",  # LIC India
        "symbol": "LICI",
        "exchange": "NSE",
        "type": "BUY",
        "quantity": Decimal("39"),
        "price": Decimal(
            "904.00"
        ),  # Retail discount price (₹949 - ₹45 retail discount)
        "trade_date": datetime(2022, 5, 13, tzinfo=timezone.utc),
        "total_fees": Decimal("0"),
        "source": "manual_ipo_allotment",
        "source_ref": "IPO_LIC_2022:90_applied_39_allotted",
        "notes": "LIC IPO allotment — applied for 90 shares at ₹904, allotted 39 shares (partial). Refund of ₹46,104 for unallotted 51 shares.",
    },
    {
        "isin": "INE0LXG01040",  # Ola Electric Mobility
        "symbol": "OLAELEC",
        "exchange": "NSE",
        "type": "BUY",
        "quantity": Decimal("195"),
        "price": Decimal("76.00"),
        "trade_date": datetime(2024, 8, 6, tzinfo=timezone.utc),
        "total_fees": Decimal("0"),
        "source": "manual_ipo_allotment",
        "source_ref": "IPO_OLAELEC_2024",
        "notes": "Ola Electric IPO allotment — 195 shares (5 lots of 39) at upper band ₹76",
    },
    {
        "isin": "INE0ONG01011",  # NTPC Green Energy
        "symbol": "NTPCGREEN",
        "exchange": "NSE",
        "type": "BUY",
        "quantity": Decimal("138"),
        "price": Decimal("108.00"),
        "trade_date": datetime(2024, 11, 19, tzinfo=timezone.utc),
        "total_fees": Decimal("0"),
        "source": "manual_ipo_allotment",
        "source_ref": "IPO_NTPCGREEN_2024",
        "notes": "NTPC Green Energy IPO allotment — 138 shares (1 lot) at upper band ₹108",
    },
    # ── Demerger: Tata Motors → TMPV (kept) + TMCV (new) ─────────────────────
    # Effective date: 01-Oct-2025
    # Ratio: 1:1 (1 TMCV for every 1 TMPV held)
    # Cost basis split (per Tata Motors): TMPV 68.85%, TMCV 31.15%
    #
    # Original TMPV: 100 shares @ ₹813.37 avg cost = ₹81,337 total cost
    # Post-demerger:
    #   TMPV: 100 shares @ ₹559.99 (68.85% of cost) = ₹55,999.96
    #   TMCV: 100 shares @ ₹253.36 (31.15% of cost) = ₹25,336.47
    #   Total preserved: ₹81,336.43 ✅
    {
        "isin": "INE1TAE01010",  # TMCV new ISIN (post-demerger)
        "symbol": "TMCV",
        "exchange": "NSE",
        "type": "BUY",
        "quantity": Decimal("100"),
        "price": Decimal("253.3647"),  # 31.15% of ₹813.37
        "trade_date": datetime(2025, 10, 1, tzinfo=timezone.utc),
        # #53/#70: demerger receipts INHERIT the parent's original acquisition
        # date for the STCG/LTCG holding-period test (IT Act). This is the
        # earliest TMPV (INE155A01022) BUY date, from the ICICI order book:
        # 18-Oct-2023 (5 sh @ ₹661.95). NOTE (#70): the 100 TMPV parent block
        # was bought across THREE lots (5 sh 18-Oct-2023 + 22 sh 05-Jun-2024 +
        # 73 sh 02-Dec-2024); the single acquired_date carries the EARLIEST
        # (LTCG-favourable) date onto the whole 100-sh TMCV receipt — an
        # accepted approximation for the multi-lot block (exact per-lot
        # inheritance is the deferred Option B). Cost basis stays the
        # apportioned §49(2C) price above; only the holding period moves.
        "acquired_date": datetime(2023, 10, 18, tzinfo=timezone.utc),
        "total_fees": Decimal("0"),
        "source": "manual_demerger",
        "source_ref": "DEMERGER_TATAMOTORS_2025:31.15pct_to_TMCV",
        "notes": "Tata Motors demerger effective 01-Oct-2025. 1:1 ratio. Cost basis = 31.15% of original TMPV cost (₹813.37/sh × 100 sh × 31.15% / 100 sh = ₹253.36/sh). Holding period inherits the original TMPV acquisition date (#53).",
    },
    # ── Reliance Industries 1:1 Bonus (Oct/Nov 2024) ────────────────────────
    # 1 bonus share for every 1 share held. You held 5 RELIANCE shares → 5 bonus shares.
    # Zero-cost addition; FIFO will dilute avg cost from ₹2432.87 to ₹1216.43.
    {
        "isin": "INE002A01018",  # RELIANCE
        "symbol": "RELIANCE",
        "exchange": "NSE",
        "type": "BUY",
        "quantity": Decimal("5"),
        "price": Decimal("0"),
        "trade_date": datetime(2024, 11, 1, tzinfo=timezone.utc),  # Bonus record date
        "total_fees": Decimal("0"),
        "source": "manual_corporate_action",
        "source_ref": "BONUS_RELIANCE_2024:1to1_5_bonus_on_5_held",
        "notes": "Reliance Industries 1:1 bonus issue — 5 bonus shares for 5 shares held. Zero cost. Avg cost dilutes from ₹2432.87 to ₹1216.43.",
    },
    # ── Ashok Leyland 1:1 Bonus (Jul 2025) ──────────────────────────────────
    # 1 bonus share for every 1 share held. You held 150 ASHOKLEY → 150 bonus.
    {
        "isin": "INE208A01029",  # ASHOKLEY
        "symbol": "ASHOKLEY",
        "exchange": "NSE",
        "type": "BUY",
        "quantity": Decimal("150"),
        "price": Decimal("0"),
        "trade_date": datetime(2025, 7, 18, tzinfo=timezone.utc),
        "total_fees": Decimal("0"),
        "source": "manual_corporate_action",
        "source_ref": "BONUS_ASHOKLEY_2025:1to1_150_bonus_on_150_held",
        "notes": "Ashok Leyland 1:1 bonus issue — 150 bonus shares for 150 held. Zero cost. Avg cost dilutes from ₹210.90 to ₹105.45.",
    },
    # ── Container Corporation 1:1 Bonus (Jul 2025) ──────────────────────────
    # 1 bonus share for every 1 share held. You held 6 CONCOR → 6 bonus.
    # NOTE: ICICI master shows 7 shares (6 + 1 bonus). Discrepancy from 1:6 ratio?
    # Check: was it actually a 1:6 ratio (1 bonus per 6 held)? That would explain
    # 6 + 1 = 7. The script below assumes 1:1 (6 bonus). UPDATE if needed.
    {
        "isin": "INE111A01025",  # CONCOR
        "symbol": "CONCOR",
        "exchange": "NSE",
        "type": "BUY",
        "quantity": Decimal(
            "1"
        ),  # ICICI master showed 7 final shares from 6, so 1 bonus
        "price": Decimal("0"),
        "trade_date": datetime(2025, 7, 8, tzinfo=timezone.utc),
        "total_fees": Decimal("0"),
        "source": "manual_corporate_action",
        "source_ref": "BONUS_CONCOR_2025:1_bonus_on_6_held",
        "notes": "Container Corporation bonus issue — 1 bonus share for 6 held. Final qty: 7. Avg cost dilutes from ₹687.31 to ~₹589.12.",
    },
    # ── Jio Financial demerger (Jul 2023) ───────────────────────────────────
    # When Jio Financial demerged from Reliance on 20-Jul-2023:
    #   - Each RELIANCE shareholder got 1 JIOFIN share for every 1 RELIANCE held
    #   - You held 5 RELIANCE → got 5 JIOFIN at demerger
    # Per ICICI: cost basis transferred at ₹113.43/share
    # NOTE: Should also reduce RELIANCE cost basis. Pending — see RELIANCE adjustment below.
    {
        "isin": "INE758E01017",  # JIOFIN
        "symbol": "JIOFIN",
        "exchange": "NSE",
        "type": "BUY",
        "quantity": Decimal("5"),
        "price": Decimal("113.43"),
        "trade_date": datetime(
            2023, 7, 20, tzinfo=timezone.utc
        ),  # Jio Financial demerger record date
        # #53/#70: JIOFIN inherits the parent RELIANCE (INE002A01018) original
        # acquisition date for the holding-period test. This is the earliest
        # RELIANCE BUY date, from the ICICI order book: 25-Jul-2022 (5 sh @
        # ₹2423.70). Single-block parent (all 5 JIOFIN came from that one 5-sh
        # RELIANCE buy; the 01-Nov-2024 1:1 bonus post-dates the 20-Jul-2023
        # demerger and is NOT the parent), so this inherited date is EXACT.
        # Cost basis stays ₹113.43 (ICICI demat allocation); only the holding
        # period is measured from this date.
        "acquired_date": datetime(2022, 7, 25, tzinfo=timezone.utc),
        "total_fees": Decimal("0"),
        "source": "manual_demerger",
        "source_ref": "DEMERGER_JIOFIN_2023:1to1_from_RELIANCE",
        "notes": "Jio Financial demerger from Reliance — 5 shares received (1:1 ratio for 5 RELIANCE held). Cost basis ₹113.43/share per ICICI demat allocation. Holding period inherits the original RELIANCE acquisition date (#53).",
    },
    # ── Tata Steel 1:10 stock split (28-Jul-2022) ───────────────────────────
    # Each share split into 10 (face value reduced from ₹10 to ₹1).
    # You held 10 shares pre-split → 100 shares post-split.
    # Avg cost: ₹1,170.27 → ₹117.027 per share. Total invested unchanged.
    {
        "isin": "INE081A01020",  # TATASTEEL
        "symbol": "TATASTEEL",
        "exchange": "NSE",
        "type": "SPLIT",
        "quantity": Decimal("0"),  # SPLIT type uses ratios in corporate_action, not qty
        "price": Decimal("0"),
        "trade_date": datetime(
            2022, 7, 28, tzinfo=timezone.utc
        ),  # Tata Steel split record date
        "total_fees": Decimal("0"),
        "corporate_action": {
            "ratio_from": 1,
            "ratio_to": 10,
            "notes": "Tata Steel 1:10 sub-division (face value ₹10 → ₹1) effective 28-Jul-2022",
        },
        "source": "manual_corporate_action",
        "source_ref": "SPLIT_TATASTEEL_2022:1to10",
        "notes": "1:10 stock split. Held 10 shares pre-split → 100 shares post-split. Avg cost dilutes from ₹1170.27 to ₹117.03.",
    },  # ── BPCL 1:1 Bonus (Sep 2024) ───────────────────────────────────────────
    # 1 bonus share for every 1 share held. You held 46 BPCL → 46 bonus.
    # Avg cost dilutes from ~₹522 to ~₹261. All 92 sold Feb 2025.
    {
        "isin": "INE029A01011",  # BPCL
        "symbol": "BPCL",
        "exchange": "NSE",
        "type": "BUY",
        "quantity": Decimal("46"),
        "price": Decimal("0"),
        "trade_date": datetime(2024, 9, 18, tzinfo=timezone.utc),
        "total_fees": Decimal("0"),
        "source": "manual_corporate_action",
        "source_ref": "BONUS_BPCL_2024:1to1_46_bonus_on_46_held",
        "notes": "BPCL 1:1 bonus issue — 46 bonus shares for 46 held. Zero cost. Avg cost dilutes from ~₹522 to ~₹261 before subsequent Feb 2025 sale.",
    },
    # ── LIC 1:1 Bonus (record date 02-Jun-2026) ─────────────────────────────
    # 1 bonus share for every 1 share held. You held 39 LICI (IPO allotment)
    # → 39 bonus shares. Zero-cost; FIFO dilutes avg cost ₹904 → ₹452.
    # Confirmed via ICICI demat statement: "LIC ... Buy 39 @ ₹0.00 STT Not Paid
    # ... 02-Jun-2026" (39 + 39 = 78 held, matches ICICI holdings snapshot).
    {
        "isin": "INE0J1Y01017",  # LICI
        "symbol": "LICI",
        "exchange": "NSE",
        "type": "BUY",
        "quantity": Decimal("39"),
        "price": Decimal("0"),
        "trade_date": datetime(2026, 6, 2, tzinfo=timezone.utc),
        "total_fees": Decimal("0"),
        "source": "manual_corporate_action",
        "source_ref": "BONUS_LICI_2026:1to1_39_bonus_on_39_held",
        "notes": "LIC 1:1 bonus issue — 39 bonus shares for 39 held. Zero cost. Avg cost dilutes from ₹904 to ₹452. Record date 02-Jun-2026 per ICICI demat statement.",
    },
    # ── Trent 17-share bonus (record date 08-Jun-2026) ──────────────────────
    # You held 35 TRENT (all via order-book buys Jul-2024 → Feb-2025) → 17
    # zero-cost bonus shares credited 08-Jun-2026 (35 + 17 = 52 held, matches
    # ICICI holdings snapshot). Confirmed via ICICI demat statement: "TRENT ...
    # Buy 17 @ ₹0.00 STT Not Paid ... 08-Jun-2026". Recorded as the exact
    # broker-allotted zero-cost quantity (mirrors the CONCOR odd-lot pattern);
    # FIFO dilutes avg cost ₹5,737 → ₹3,858.
    {
        "isin": "INE849A01020",  # TRENT
        "symbol": "TRENT",
        "exchange": "NSE",
        "type": "BUY",
        "quantity": Decimal("17"),
        "price": Decimal("0"),
        "trade_date": datetime(2026, 6, 8, tzinfo=timezone.utc),
        "total_fees": Decimal("0"),
        "source": "manual_corporate_action",
        "source_ref": "BONUS_TRENT_2026:17_bonus_on_35_held",
        "notes": "Trent bonus issue — 17 bonus shares credited on 35 held. Zero cost. Avg cost dilutes from ₹5,737 to ₹3,858. Record date 08-Jun-2026 per ICICI demat statement.",
    },
]

# ── TMPV cost basis adjustment ───────────────────────────────────────────────
# Special case: we don't add a new transaction for TMPV. Instead we update
# the existing TMPV BUY transactions in staging to reflect the post-demerger
# cost basis (68.85% of original). This is cleaner than adding synthetic
# SELL transactions and keeps FIFO logic clean.

TMPV_COST_BASIS_FACTOR = Decimal("0.6885")  # 68.85%
TMPV_ISIN = "INE155A01022"


def adjust_tmpv_cost_basis() -> int:
    """Multiply price field on all TMPV BUY transactions by 0.6885.

    Skips if already adjusted (idempotency check via notes field).
    Returns number of transactions adjusted.
    """
    staging = Collections.transactions_staging()

    # Find all non-adjusted TMPV BUYs
    cursor = staging.find(
        {
            "isin": TMPV_ISIN,
            "type": "BUY",
            "notes": {"$not": {"$regex": "DEMERGER_ADJUSTED"}},
        }
    )

    adjusted = 0
    for tx in cursor:
        old_price = Decimal(str(tx["price"]))
        new_price = (old_price * TMPV_COST_BASIS_FACTOR).quantize(Decimal("0.0001"))
        old_fees = Decimal(str(tx.get("total_fees", 0)))
        new_fees = (old_fees * TMPV_COST_BASIS_FACTOR).quantize(Decimal("0.01"))

        existing_notes = tx.get("notes", "")
        new_notes = (
            f"{existing_notes} | DEMERGER_ADJUSTED 01-Oct-2025: "
            f"price {old_price} → {new_price} (×{TMPV_COST_BASIS_FACTOR}); "
            f"fees {old_fees} → {new_fees}"
        ).strip(" |")

        update = _convert_decimals_to_decimal128(
            {
                "price": new_price,
                "total_fees": new_fees,
                "notes": new_notes,
                "updated_at": utcnow(),
            }
        )

        staging.update_one({"_id": tx["_id"]}, {"$set": update})
        adjusted += 1
        log.info(
            "Adjusted TMPV transaction (date %s): price %s → %s",
            tx["trade_date"].date(),
            old_price,
            new_price,
        )

    return adjusted


# ── Insert manual transactions ───────────────────────────────────────────────


def insert_manual_transactions() -> dict:
    """Insert MANUAL_TRANSACTIONS into staging.

    Skips inserts where source_ref already exists (idempotency).
    """
    staging = Collections.transactions_staging()
    inserted = 0
    skipped_existing = 0

    for tx in MANUAL_TRANSACTIONS:
        existing = staging.find_one({"source_ref": tx["source_ref"]})
        if existing:
            log.info(
                "Skipping (already exists): %s — %s", tx["symbol"], tx["source_ref"]
            )
            skipped_existing += 1
            continue

        doc = dict(tx)
        doc["_schema_version"] = 1
        doc["created_at"] = utcnow()
        doc["updated_at"] = utcnow()
        doc["deleted_at"] = None
        if doc["type"] == "BUY":
            doc["remaining_quantity"] = doc["quantity"]
        # TD17: a backdated manual SELL must not drive quantity negative at any
        # point in the FIFO timeline. Replay the full per-ISIN timeline
        # (order-book staging + manual entries inserted so far this run + this
        # SELL) and ABORT rather than silently inserting a tx that recompute
        # would later only log as an oversell. Gated on SELL so benign
        # BUY/SPLIT/BONUS inserts are never blocked by unrelated staging data.
        if doc["type"] == "SELL":
            timeline = list(staging.find({"isin": doc["isin"], "deleted_at": None})) + [
                doc
            ]
            ok, reason = validate_replay(timeline)
            if not ok:
                raise RuntimeError(
                    f"Manual SELL rejected for {doc['symbol']} "
                    f"({doc['source_ref']}): {reason}"
                )
        staging.insert_one(_convert_decimals_to_decimal128(doc))
        inserted += 1
        log.info(
            "Inserted: %s %s × %s @ ₹%s on %s",
            doc["type"],
            doc["quantity"],
            doc["symbol"],
            doc["price"],
            doc["trade_date"].date(),
        )

    return {"inserted": inserted, "skipped_existing": skipped_existing}


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    print("=" * 70)
    print("  Adding manual transactions to staging")
    print("=" * 70)
    print()

    staging = Collections.transactions_staging()
    initial_count = staging.estimated_document_count()
    print(f"Staging currently has: {initial_count} transactions")
    print()

    # Step 1: insert manual transactions
    print("Step 1: Inserting manual IPO + demerger transactions...")
    result = insert_manual_transactions()
    print(f"  ✓ Inserted: {result['inserted']}")
    print(f"  ⏭  Skipped (already exists): {result['skipped_existing']}")
    print()

    # Step 2: adjust TMPV cost basis for demerger
    print("Step 2: Adjusting TMPV cost basis for Tata Motors demerger...")
    print("        (multiplying TMPV BUY prices by 0.6885 = 68.85%)")
    adjusted = adjust_tmpv_cost_basis()
    print(f"  ✓ Adjusted: {adjusted} TMPV transactions")
    print()

    final_count = staging.estimated_document_count()
    print(
        f"Staging now has: {final_count} transactions ({final_count - initial_count} new)"
    )
    print()
    print("Next steps:")
    print(
        "  1. Run reconciliation: PYTHONPATH=. uv run python scripts/reconcile_staging.py"
    )
    print("  2. Cross-check totals against ICICI")
    print(
        "  3. If matches: PYTHONPATH=. uv run python scripts/promote_staging.py --confirm --wipe-live"
    )
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
