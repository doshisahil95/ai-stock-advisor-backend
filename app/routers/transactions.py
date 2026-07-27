"""Portfolio-wide transactions: search, edit, delete.

Per-stock transactions live on the holdings router (/portfolio/holdings/{isin}/transactions).
This router is for cross-portfolio queries and for editing/deleting individual transactions
with full audit-log support.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Literal

from bson import Decimal128, ObjectId
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
import re

from app.db.client import Collections
from app.models._common import _convert_decimals_to_decimal128, utcnow
from app.models.cost_basis_adjustment import CostBasisAdjustment
from app.models.transaction import Transaction
from app.services import corporate_action_service
from app.services.holdings_service import recompute_holding
from app.services.transactions_audit_service import log_change
from app.services.holdings_service import recompute_holding, validate_replay


router = APIRouter(prefix="/transactions", tags=["transactions"])

# ── Helpers ──────────────────────────────────────────────────────────────────

Money = Decimal


def _serialize(value: Any) -> Any:
    if isinstance(value, Decimal128):
        return str(value.to_decimal())
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialize(v) for v in value]
    return value


# ── Request models ───────────────────────────────────────────────────────────


class EditTransactionRequest(BaseModel):
    """Editable fields on a transaction.
    All optional; missing fields are unchanged.
    Reason is required per audit invariant (Project_State §11)."""

    model_config = ConfigDict(extra="forbid")
    quantity: Money | None = None
    price: Money | None = None
    trade_date: datetime | None = None
    total_fees: Money | None = None
    notes: str | None = None
    # F21 fix (Chat 5.5+): reason is REQUIRED. Pre-fix it was optional, so
    # callers could mutate the immutable ledger with no audit justification,
    # producing audit entries with reason=None and breaking the documented
    # audit guarantee used for tax review. Frontend (transaction-edit-sheet.tsx
    # zod schema and transactions page delete dialog) already enforces a 3-char
    # minimum; backend now matches.
    reason: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Why this is being edited (audit). Required.",
    )


class DeleteTransactionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # F21 fix (Chat 5.5+): reason is REQUIRED. See EditTransactionRequest.
    reason: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Why this is being deleted (audit). Required.",
    )


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/search", summary="Search/list transactions across the portfolio")
def search_transactions(
    symbol: str | None = Query(
        None, description="Exact symbol match (case-insensitive)"
    ),
    type: Literal["BUY", "SELL", "SPLIT", "BONUS", "DIVIDEND"] | None = Query(None),
    from_date: str | None = Query(
        None, description="Inclusive lower bound, YYYY-MM-DD"
    ),
    to_date: str | None = Query(None, description="Inclusive upper bound, YYYY-MM-DD"),
    include_deleted: bool = Query(False),
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
) -> dict:
    """Filterable list of transactions, sorted newest first."""
    query: dict = {}

    if symbol:
        # Prefix match — input is uppercased and symbols are stored uppercase, so
        # this stays case-sensitive on purpose; an "i" flag disables the
        # (symbol, trade_date) index. Supports partial typing like "TR" → TRENT.
        escaped = re.escape(symbol.upper())
        query["symbol"] = {"$regex": f"^{escaped}"}
    if type:
        query["type"] = type

    date_filter: dict = {}
    parsed_from: datetime | None = None
    parsed_to: datetime | None = None

    if from_date:
        try:
            parsed_from = datetime.fromisoformat(from_date)
        except ValueError:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"Invalid from_date: {from_date}"
            )
        date_filter["$gte"] = parsed_from
    if to_date:
        try:
            d = datetime.fromisoformat(to_date)
        except ValueError:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"Invalid to_date: {to_date}"
            )
        parsed_to = d.replace(hour=23, minute=59, second=59)
        date_filter["$lte"] = parsed_to

    # Cross-field validation
    if parsed_from and parsed_to and parsed_from > parsed_to:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"from_date ({from_date}) cannot be after to_date ({to_date})",
        )
    today_eod_naive = datetime.now(
        timezone.utc
    ).replace(  # tz-ok: future-date validation bound, made naive inline below
        hour=23, minute=59, second=59, tzinfo=None
    )
    if parsed_to and parsed_to.replace(tzinfo=None) > today_eod_naive:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"to_date ({to_date}) cannot be in the future",
        )

    if date_filter:
        query["trade_date"] = date_filter

    if not include_deleted:
        query["deleted_at"] = None

    coll = Collections.transactions()
    total = coll.count_documents(query)
    cursor = coll.find(query).sort("trade_date", -1).skip(skip).limit(limit)

    return {
        "transactions": _serialize(list(cursor)),
        "total": total,
        "limit": limit,
        "skip": skip,
    }


@router.get("/{tx_id}", summary="Get one transaction by id")
def get_transaction(tx_id: str) -> dict:
    try:
        oid = ObjectId(tx_id)
    except Exception:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Invalid transaction id: {tx_id}"
        )

    tx = Collections.transactions().find_one({"_id": oid})
    if not tx:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Transaction not found: {tx_id}"
        )
    return _serialize(tx)


@router.patch("/{tx_id}", summary="Edit a transaction (with audit log + recompute)")
def edit_transaction(tx_id: str, payload: EditTransactionRequest) -> dict:
    """Update a transaction's editable fields, log to audit, recompute the holding.

    Editing quantity/price/date materially changes realized P&L history.
    The `reason` field is captured in the audit log.
    """
    try:
        oid = ObjectId(tx_id)
    except Exception:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Invalid transaction id: {tx_id}"
        )

    before = Collections.transactions().find_one({"_id": oid})
    if not before:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Transaction not found: {tx_id}"
        )
    if before.get("deleted_at"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Cannot edit a deleted transaction"
        )

    update_fields: dict = {}
    for field in ("quantity", "price", "trade_date", "total_fees", "notes"):
        value = getattr(payload, field, None)
        if value is not None:
            update_fields[field] = value

    if not update_fields:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields to update")

    # ── Validation: simulate the new state to catch impossible edits ────────
    # Build the would-be transaction list with this edit applied
    all_txs = list(
        Collections.transactions().find({"isin": before["isin"], "deleted_at": None})
    )
    simulated_txs = []
    for tx in all_txs:
        if tx["_id"] == oid:
            sim = {**tx, **update_fields}
            simulated_txs.append(sim)
        else:
            simulated_txs.append(tx)

    is_valid, error_msg = validate_replay(simulated_txs)
    if not is_valid:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, error_msg)

    # ── Apply the edit ──────────────────────────────────────────────────────
    # TD16 (write-before-apply): build the would-be after-state and write the
    # audit row BEFORE mutating the ledger. If the audit insert fails, the
    # update_one never runs -- same invariant as the F10 feedback handler and
    # the transactions_audit guarantee in Project_State Section 11.
    update_fields["updated_at"] = utcnow()
    after_preview = {**before, **update_fields}
    log_change(
        transaction_id=str(oid),
        isin=before["isin"],
        action="edit",
        before=_serialize(before),
        after=_serialize(after_preview),
        reason=payload.reason,
    )
    Collections.transactions().update_one(
        {"_id": oid},
        {"$set": _convert_decimals_to_decimal128(update_fields)},
    )
    after = Collections.transactions().find_one({"_id": oid})
    recompute_holding(before["isin"])
    return _serialize(after)


@router.delete(
    "/{tx_id}", summary="Soft-delete a transaction (with audit log + recompute)"
)
def delete_transaction(tx_id: str, payload: DeleteTransactionRequest) -> dict:
    try:
        oid = ObjectId(tx_id)
    except Exception:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Invalid transaction id: {tx_id}"
        )

    before = Collections.transactions().find_one({"_id": oid})
    if not before:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Transaction not found: {tx_id}"
        )
    if before.get("deleted_at"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Already deleted")

    # ── Validation: simulate without this transaction ───────────────────────
    all_txs = list(
        Collections.transactions().find({"isin": before["isin"], "deleted_at": None})
    )
    simulated_txs = [tx for tx in all_txs if tx["_id"] != oid]

    is_valid, error_msg = validate_replay(simulated_txs)
    if not is_valid:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Deleting this transaction would create an impossible state: {error_msg}",
        )

    # ── Apply the soft-delete ───────────────────────────────────────────────
    # TD16 (write-before-apply): write the audit row BEFORE the soft-delete.
    # If the audit insert fails, the ledger mutation never happens -- same
    # invariant as the F10 feedback handler and Project_State Section 11.
    log_change(
        transaction_id=str(oid),
        isin=before["isin"],
        action="delete",
        before=_serialize(before),
        after=None,
        reason=payload.reason,
    )
    now = utcnow()
    Collections.transactions().update_one(
        {"_id": oid},
        {"$set": {"deleted_at": now, "updated_at": now}},
    )
    recompute_holding(before["isin"])

    return {
        "message": f"Transaction {tx_id} soft-deleted",
        "isin": before["isin"],
        "symbol": before.get("symbol"),
    }


@router.get("/audit/recent", summary="Recent edits/deletes across all transactions")
def get_recent_audit(limit: int = Query(50, ge=1, le=500)) -> list[dict]:
    """Read-only audit log — append-only, immutable from the API.

    Used to explain retroactive changes to realized P&L (e.g. for tax review).
    """
    from app.services.transactions_audit_service import get_recent_audit as _get_recent

    return _serialize(_get_recent(limit=limit))


@router.get("/{tx_id}/audit", summary="Audit history for one transaction")
def get_transaction_audit(tx_id: str) -> list[dict]:
    """All audit entries for a specific transaction, newest first."""
    from app.services.transactions_audit_service import get_audit_for_transaction

    try:
        ObjectId(tx_id)
    except Exception:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Invalid transaction id: {tx_id}"
        )
    return _serialize(get_audit_for_transaction(tx_id))


# ── #68: corporate-action data-entry front-end ──────────────────────────────


def _to_dec(value: Any) -> Decimal:
    """Coerce a Mongo-stored numeric (Decimal128/Decimal/str/int) to Decimal."""
    if isinstance(value, Decimal128):
        return value.to_decimal()
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class RecordCorporateActionRequest(BaseModel):
    """Record a SPLIT / BONUS / demerger in one shot (#68).

    The FIFO cost math is already correct at the single source of truth
    (`_fifo_replay`); this is the data-entry front-end that produces the same
    ledger row(s) the manual `add_manual_transactions.py` script produces, then
    recomputes. Fields are validated per `action_type` in the handler (kept as
    explicit HTTPExceptions to match this router's style rather than a nest of
    per-branch models).
    """

    model_config = ConfigDict(extra="forbid")

    action_type: Literal["split", "bonus", "demerger"]
    # Affected (parent) instrument. For split/bonus this IS the security whose
    # lots change; for demerger it's the parent that spun off the child.
    isin: str = Field(..., min_length=12, max_length=12, pattern=r"^[A-Z0-9]{12}$")
    symbol: str = Field(..., min_length=1)
    exchange: str = Field(default="NSE", pattern=r"^(NSE|BSE)$")
    trade_date: datetime
    notes: str = ""
    source_ref: str = Field(
        default="",
        description="Stable idempotency key, e.g. 'SPLIT_TATASTEEL_2022:1to10'. "
        "A repeat call with the same source_ref is a no-op.",
    )

    # SPLIT / BONUS ratios (ratio_to per ratio_from held).
    ratio_from: int | None = Field(default=None, gt=0)
    ratio_to: int | None = Field(default=None, gt=0)
    # BONUS: optional explicit share count when the broker's allotment doesn't
    # equal ratio*held (e.g. CONCOR showed 1 bonus for 6 held). Overrides the
    # computed ratio*held quantity when supplied.
    bonus_quantity: Money | None = Field(default=None, gt=0)

    # DEMERGER child (new) instrument + §49(2C) cost apportionment.
    child_isin: str | None = Field(
        default=None, min_length=12, max_length=12, pattern=r"^[A-Z0-9]{12}$"
    )
    child_symbol: str | None = Field(default=None, min_length=1)
    child_quantity: Money | None = Field(default=None, gt=0)
    child_cost_pct: Money | None = Field(
        default=None,
        gt=0,
        lt=1,
        description="Fraction of the parent's original cost apportioned to the "
        "child, e.g. 0.3115 for 31.15% (§49(2C) net-book-value proportion).",
    )
    parent_total_cost: Money | None = Field(
        default=None,
        gt=0,
        description="The parent block's total original cost being apportioned "
        "(e.g. ₹81,337 for 100 TMPV @ ₹813.37).",
    )
    # Holding-period inheritance date for the child receipt (#53). Parent's
    # earliest acquisition date; absent -> receipt date is used downstream.
    acquired_date: datetime | None = None
    it_act_section: str = Field(default="Section 49(2C) of the Income Tax Act, 1961")


def _corp_action_exists(source_ref: str) -> bool:
    """Idempotency: has a non-deleted ledger row with this source_ref landed?"""
    if not source_ref:
        return False
    return (
        Collections.transactions().find_one(
            {"source_ref": source_ref, "deleted_at": None}
        )
        is not None
    )


@router.post(
    "/corporate-action",
    summary="Record a SPLIT / BONUS / demerger and auto-map it onto holdings (#68)",
    status_code=201,
)
def record_corporate_action(req: RecordCorporateActionRequest) -> dict:
    """Record a corporate action ONCE; the ledger row(s) + recompute do the rest.

    SPLIT  -> one type="SPLIT" row (ratios drive _fifo_replay lot scaling).
    BONUS  -> one zero-cost type="BUY" price=0 row (the real-ledger pattern;
              _fifo_replay dilutes avg cost, holding period runs from allotment).
    DEMERGER -> a source="manual_demerger" child BUY carrying the apportioned
                §49(2C) cost + inherited acquired_date, PLUS an auto-created
                cost_basis_adjustments doc. The parent-cost reduction is
                returned as an AUDITED follow-up (apply via PATCH /transactions/
                {id}) — we never silently bulk-mutate immutable BUY rows.

    Idempotent on source_ref: a repeat call returns {"status": "already_recorded"}.
    """
    isin = req.isin.strip().upper()
    symbol = req.symbol.strip().upper()
    exchange = req.exchange.strip().upper()

    if _corp_action_exists(req.source_ref):
        return {
            "status": "already_recorded",
            "isin": isin,
            "source_ref": req.source_ref,
            "message": "A transaction with this source_ref already exists.",
        }

    # ── SPLIT ────────────────────────────────────────────────────────────────
    if req.action_type == "split":
        if req.ratio_from is None or req.ratio_to is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "split requires ratio_from and ratio_to",
            )
        row = corporate_action_service.build_split_row(
            isin=isin,
            symbol=symbol,
            exchange=exchange,
            ratio_from=req.ratio_from,
            ratio_to=req.ratio_to,
            trade_date=req.trade_date,
            notes=req.notes,
            source_ref=req.source_ref,
        )
        # Guard: a SPLIT before any BUY (or otherwise impossible) is rejected,
        # mirroring the validate_replay guard on the sell/edit/delete paths.
        existing_txs = list(
            Collections.transactions().find({"isin": isin, "deleted_at": None})
        )
        ok, reason = validate_replay(existing_txs + [row])
        if not ok:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, reason)
        tx = Transaction(**row)
        Collections.transactions().insert_one(tx.to_mongo())
        return _finish_corp_action(isin, symbol, "SPLIT recorded")

    # ── BONUS ──────────────────────────────────────────────────────────────
    if req.action_type == "bonus":
        if req.ratio_from is None or req.ratio_to is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "bonus requires ratio_from and ratio_to",
            )
        if req.bonus_quantity is not None:
            bonus_qty = req.bonus_quantity
        else:
            holding = Collections.holdings().find_one(
                {"isin": isin, "deleted_at": None}
            )
            if not holding:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"No active holding for {isin}; supply bonus_quantity "
                    f"explicitly to record a bonus on a non-held/closed position.",
                )
            held_qty = _to_dec(holding.get("quantity"))
            bonus_qty = corporate_action_service.compute_bonus_quantity(
                held_qty, req.ratio_from, req.ratio_to
            )
        row = corporate_action_service.build_bonus_row(
            isin=isin,
            symbol=symbol,
            exchange=exchange,
            bonus_quantity=bonus_qty,
            trade_date=req.trade_date,
            notes=req.notes,
            source_ref=req.source_ref,
        )
        tx = Transaction(**row)
        Collections.transactions().insert_one(tx.to_mongo())
        result = _finish_corp_action(isin, symbol, "BONUS recorded")
        result["bonus_quantity"] = str(bonus_qty)
        return result

    # ── DEMERGER ─────────────────────────────────────────────────────────────
    # req.action_type == "demerger"
    missing = [
        name
        for name, val in (
            ("child_isin", req.child_isin),
            ("child_symbol", req.child_symbol),
            ("child_quantity", req.child_quantity),
            ("child_cost_pct", req.child_cost_pct),
            ("parent_total_cost", req.parent_total_cost),
        )
        if val is None
    ]
    if missing:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"demerger requires: {', '.join(missing)}",
        )
    child_isin = req.child_isin.strip().upper()
    child_symbol = req.child_symbol.strip().upper()

    split_math = corporate_action_service.compute_demerger_cost_split(
        parent_total_cost=req.parent_total_cost,
        parent_quantity=req.child_quantity,  # 1:1 receipt: child qty == parent qty apportioned
        child_cost_pct=req.child_cost_pct,
    )

    child_row = corporate_action_service.build_demerger_child_row(
        child_isin=child_isin,
        child_symbol=child_symbol,
        exchange=exchange,
        quantity=req.child_quantity,
        cost_per_share=split_math["child_cost_per_share"],
        trade_date=req.trade_date,
        acquired_date=req.acquired_date,
        notes=req.notes,
        source_ref=req.source_ref,
    )
    child_tx = Transaction(**child_row)
    Collections.transactions().insert_one(child_tx.to_mongo())

    # Auto-create the §49(2C) cost_basis_adjustments doc (the row said this
    # endpoint should). Mirrors seed_cost_basis_adjustments.py's shape.
    adj = CostBasisAdjustment(
        name=f"{symbol} demerger — {symbol}/{child_symbol} cost split",
        isin=child_isin,
        related_isins=[isin],
        amount=split_math["adjustment_amount"],
        it_act_section=req.it_act_section,
        effective_date=req.trade_date,
        calculation=(
            f"Parent {symbol}: {req.child_quantity} sh, total cost "
            f"₹{req.parent_total_cost}. §49(2C) apportions "
            f"{req.child_cost_pct} to {child_symbol}: "
            f"child total ₹{split_math['child_total_cost']} "
            f"(₹{split_math['child_cost_per_share']}/sh); parent retains "
            f"×{split_math['parent_retained_factor']}."
        ),
        broker_treatment=(
            f"Broker keeps the full ₹{req.parent_total_cost} on {symbol} and "
            f"₹0 on {child_symbol}, over-counting parent 'invested'."
        ),
        our_treatment=(
            f"{child_symbol} BUY created at "
            f"₹{split_math['child_cost_per_share']}/sh; {symbol} BUY rows to be "
            f"repriced ×{split_math['parent_retained_factor']} via the audited "
            f"edit path (see parent_reprice in this response)."
        ),
        rationale=(
            "§49(2C) requires the original cost to be apportioned between the "
            "resulting and demerged companies in proportion to their net book "
            "values at the date of demerger."
        ),
        source_documents=[req.it_act_section],
    )
    # CostBasisAdjustment is a plain BaseModel (no BaseDoc.to_mongo); persist it
    # the same way seed_cost_basis_adjustments.py does — by_alias dump + audit
    # timestamps + Decimal->Decimal128.
    adj_doc = adj.model_dump(by_alias=True, exclude_none=True)
    adj_doc["created_at"] = utcnow()
    adj_doc["updated_at"] = utcnow()
    Collections.cost_basis_adjustments().insert_one(
        _convert_decimals_to_decimal128(adj_doc)
    )

    # Recompute the CHILD holding so it appears immediately.
    _finish_corp_action(child_isin, child_symbol, "demerger child recorded")

    # Compute (do NOT apply) the parent BUY-row reprice. The caller applies it
    # via PATCH /transactions/{id} so every parent-cost change is audited.
    parent_rows = list(
        Collections.transactions().find({"isin": isin, "deleted_at": None})
    )
    reprice = corporate_action_service.compute_parent_reprice(
        parent_rows, split_math["parent_retained_factor"]
    )

    return {
        "status": "recorded",
        "isin": isin,
        "child_isin": child_isin,
        "child_cost_per_share": str(split_math["child_cost_per_share"]),
        "adjustment_amount": str(split_math["adjustment_amount"]),
        "parent_retained_factor": str(split_math["parent_retained_factor"]),
        "cost_basis_adjustment_created": True,
        "parent_reprice": _serialize(reprice),
        "message": (
            "Demerger child recorded + §49(2C) adjustment created. Apply the "
            "parent_reprice entries via PATCH /transactions/{id} (audited) to "
            "reduce the parent's cost basis."
        ),
    }


def _finish_corp_action(isin: str, symbol: str, what: str) -> dict:
    """Recompute the affected holding after a corp-action insert, mirroring the
    add_buy/sell TD19 recorded_with_warning contract (a persisted ledger row +
    a recompute that may fail independently must not 500)."""
    try:
        recompute_holding(isin)
    except Exception:  # pragma: no cover - defensive, mirrors add_buy
        return {
            "status": "recorded_with_warning",
            "isin": isin,
            "symbol": symbol,
            "warning": (
                f"{what}, but the holding aggregate could not be recomputed and "
                f"may be stale. Re-run recompute for this ISIN to refresh."
            ),
        }
    return {"status": "recorded", "isin": isin, "symbol": symbol, "message": what}
