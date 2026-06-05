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
from app.models._common import _convert_decimals_to_decimal128
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
        # Prefix match (case-insensitive) — supports partial typing like "TR" → TRENT
        escaped = re.escape(symbol.upper())
        query["symbol"] = {"$regex": f"^{escaped}", "$options": "i"}
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
    today_eod_naive = datetime.now(timezone.utc).replace(
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
    update_fields["updated_at"] = datetime.now(timezone.utc)
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
    now = datetime.now(timezone.utc)
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
