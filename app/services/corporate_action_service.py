"""Corporate-action data-entry helpers (#68).

The FIFO cost math for SPLIT / BONUS / demerger is ALREADY correct at the
single source of truth (`holdings_service._fifo_replay`); #53 added
holding-period inheritance via `Transaction.acquired_date`. #68 is purely the
DATA-ENTRY / automation front-end for that math: it turns the hand-edited
`scripts/add_manual_transactions.py` dicts into a runtime endpoint that records
a corporate action ONCE and produces exactly the same ledger row(s) the script
produces, then lets the caller `recompute_holding`.

This module is intentionally DB-free and side-effect-free — every function is a
pure builder returning plain dicts. The router (`app/routers/transactions.py`)
owns the DB reads (current held qty, parent BUY rows) and the writes
(`insert_one`, `recompute_holding`, the §49(2C) adjustment). Keeping the math
pure makes it hermetically testable via the existing FakeCollection harness and
mirrors the split between `preview_sell` (pure) and the sell endpoint (I/O).

Nothing here invents a parallel FIFO path: SPLIT is a `type="SPLIT"` row whose
meaning lives in `corporate_action.ratio_from/ratio_to` (exactly what
_fifo_replay consumes); BONUS is a zero-cost `type="BUY" price=0` row (the
pattern the REAL ledger uses — RELIANCE/ASHOKLEY/CONCOR/BPCL — NOT the dead
`type="BONUS"` branch); a demerger receipt is a `source="manual_demerger"` BUY
carrying the apportioned §49(2C) cost as `price` + the inherited `acquired_date`.
"""

from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal


def build_split_row(
    *,
    isin: str,
    symbol: str,
    exchange: str,
    ratio_from: int,
    ratio_to: int,
    trade_date: datetime,
    notes: str = "",
    source_ref: str = "",
) -> dict:
    """A SPLIT ledger row. Meaning lives in corporate_action ratios; qty/price
    are 0 and ignored by _fifo_replay (which scales existing lots by the ratio,
    preserving total cost). Mirrors the TATASTEEL 1:10 row in the manual script.
    """
    return {
        "isin": isin,
        "symbol": symbol,
        "exchange": exchange,
        "type": "SPLIT",
        "quantity": Decimal("0"),
        "price": Decimal("0"),
        "trade_date": trade_date,
        "total_fees": Decimal("0"),
        "corporate_action": {
            "ratio_from": int(ratio_from),
            "ratio_to": int(ratio_to),
            "notes": notes,
        },
        "source": "manual_corporate_action",
        "source_ref": source_ref,
        "notes": notes,
    }


def compute_bonus_quantity(
    held_qty: Decimal, ratio_from: int, ratio_to: int
) -> Decimal:
    """Bonus shares received = held_qty * ratio_to / ratio_from.

    E.g. a 1:1 bonus (ratio_from=1, ratio_to=1) on 5 held -> 5 bonus. A 1:6
    bonus (ratio_from=6, ratio_to=1) on 6 held -> 1 bonus (the CONCOR case).
    """
    rf = Decimal(str(ratio_from))
    rt = Decimal(str(ratio_to))
    if rf <= 0 or rt <= 0:
        raise ValueError("bonus ratios must be positive")
    return (held_qty * rt / rf).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def build_bonus_row(
    *,
    isin: str,
    symbol: str,
    exchange: str,
    bonus_quantity: Decimal,
    trade_date: datetime,
    notes: str = "",
    source_ref: str = "",
) -> dict:
    """A BONUS as a zero-cost BUY lot (the real-ledger pattern).

    We DELIBERATELY record bonus shares as `type="BUY" price=0` rather than
    `type="BONUS"`: the actual production data (RELIANCE/ASHOKLEY/CONCOR/BPCL)
    uses zero-cost BUY rows, `_fifo_replay` dilutes avg cost correctly across
    the enlarged lot set, and the holding period on bonus shares correctly runs
    from allotment (the IT-Act treatment). The `type="BONUS"` ratio branch is
    dead for real data; we do not resurrect it.
    """
    return {
        "isin": isin,
        "symbol": symbol,
        "exchange": exchange,
        "type": "BUY",
        "quantity": bonus_quantity,
        "price": Decimal("0"),
        "trade_date": trade_date,
        "total_fees": Decimal("0"),
        "source": "manual_corporate_action",
        "source_ref": source_ref,
        "notes": notes,
    }


def build_demerger_child_row(
    *,
    child_isin: str,
    child_symbol: str,
    exchange: str,
    quantity: Decimal,
    cost_per_share: Decimal,
    trade_date: datetime,
    acquired_date: datetime | None,
    notes: str = "",
    source_ref: str = "",
) -> dict:
    """The demerger RECEIPT row: a BUY of the child (new) ISIN carrying the
    apportioned §49(2C) cost as `price` and the parent's original acquisition
    date as `acquired_date` (holding-period inheritance, #53). Mirrors the
    TMCV / JIOFIN rows in the manual script.
    """
    row = {
        "isin": child_isin,
        "symbol": child_symbol,
        "exchange": exchange,
        "type": "BUY",
        "quantity": quantity,
        "price": cost_per_share,
        "trade_date": trade_date,
        "total_fees": Decimal("0"),
        "source": "manual_demerger",
        "source_ref": source_ref,
        "notes": notes,
    }
    if acquired_date is not None:
        row["acquired_date"] = acquired_date
    return row


def compute_demerger_cost_split(
    *,
    parent_total_cost: Decimal,
    parent_quantity: Decimal,
    child_cost_pct: Decimal,
) -> dict:
    """Split a parent block's total cost per §49(2C).

    Returns the per-share child cost, the retained parent factor, and the
    signed adjustment amount (our_invested - broker_invested), which is
    NEGATIVE because the broker keeps the full cost on the parent and shows 0
    on the child, so our apportioned total under-counts the parent by the child
    slice. This mirrors the -₹24,244.83 TMPV/TMCV figure in
    seed_cost_basis_adjustments.py.

    child_cost_pct is a fraction in (0, 1), e.g. Decimal("0.3115") for 31.15%.
    """
    if parent_quantity <= 0:
        raise ValueError("parent_quantity must be positive")
    if not (Decimal("0") < child_cost_pct < Decimal("1")):
        raise ValueError("child_cost_pct must be a fraction strictly in (0, 1)")

    child_total = (parent_total_cost * child_cost_pct).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    child_cost_per_share = (child_total / parent_quantity).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )
    parent_retained_factor = (Decimal("1") - child_cost_pct).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )
    # Signed: our_invested - broker_invested. Broker keeps parent_total_cost on
    # the parent + 0 on the child; we now carry (parent*retained) + child_total.
    # our - broker = -child_total (the slice moved onto the child that the
    # broker never credited).
    adjustment_amount = (-child_total).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return {
        "child_total_cost": child_total,
        "child_cost_per_share": child_cost_per_share,
        "parent_retained_factor": parent_retained_factor,
        "adjustment_amount": adjustment_amount,
    }


def compute_parent_reprice(
    parent_buy_rows: list[dict],
    parent_retained_factor: Decimal,
) -> list[dict]:
    """Compute (but do NOT apply) the retained new price/fees for each parent
    BUY row after a demerger.

    Returns one instruction per non-deleted parent BUY row:
        {transaction_id, old_price, new_price, old_fees, new_fees, reason}

    The caller applies these through the EXISTING audited PATCH path
    (`PATCH /transactions/{id}`) so the immutable-ledger invariant holds — we
    never bulk-mutate BUY rows silently (unlike the one-off script). This keeps
    a full audit trail on every parent-cost change.
    """
    from app.services.holdings_service import _to_decimal

    factor = Decimal(str(parent_retained_factor))
    instructions: list[dict] = []
    for row in parent_buy_rows:
        if row.get("type") != "BUY":
            continue
        old_price = _to_decimal(row.get("price"))
        old_fees = _to_decimal(row.get("total_fees", 0))
        new_price = (old_price * factor).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
        new_fees = (old_fees * factor).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        instructions.append(
            {
                "transaction_id": str(row.get("_id")),
                "trade_date": row.get("trade_date"),
                "old_price": old_price,
                "new_price": new_price,
                "old_fees": old_fees,
                "new_fees": new_fees,
            }
        )
    return instructions
