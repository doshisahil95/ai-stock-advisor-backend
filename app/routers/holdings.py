"""Holdings API — read holdings, add via BUY transactions, edit metadata."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from bson import ObjectId
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.db.client import Collections
from app.models._common import Money, _convert_decimals_to_decimal128, utcnow
from app.models.holding import Holding
from app.models.transaction import Transaction
from app.services.holdings_service import recompute_holding
from app.services.yfinance_lookup import fetch_metadata

router = APIRouter(prefix="/portfolio/holdings", tags=["portfolio"])

# ── Request models ───────────────────────────────────────────────────────────


class AddBuyRequest(BaseModel):
    """Record a buy. ISIN is auto-resolved from symbol+exchange via yfinance,
    or you can supply it explicitly if the lookup fails."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(..., description="e.g., 'INFY'")
    exchange: str = Field(default="NSE", pattern=r"^(NSE|BSE)$")
    quantity: Money
    price: Money = Field(..., description="Per-share price in INR")
    trade_date: datetime
    total_fees: Money = Field(default=Decimal("0"))
    notes: str = ""
    isin: str | None = Field(
        default=None,
        description="Optional. If yfinance can't resolve the ISIN, supply it here.",
    )


class SellRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity: Money
    price: Money
    trade_date: datetime
    total_fees: Money = Field(default=Decimal("0"))
    notes: str = ""


class HoldingMetadataPatch(BaseModel):
    """Editable fields on a holding (NOT quantity / cost — those are derived)."""

    model_config = ConfigDict(extra="forbid")

    user_notes: str | None = None
    thesis: str | None = None
    tags: list[str] | None = None
    stop_loss: Money | None = None
    target_price: Money | None = None
    alert_on: list[str] | None = None


# ── Response helpers ─────────────────────────────────────────────────────────


def _doc_to_response(doc: dict) -> dict:
    """Convert a Mongo doc to a JSON-serializable response.

    Decimal128 -> string, ObjectId -> string, datetime -> ISO format.
    """
    from bson import Decimal128

    def convert(value: Any) -> Any:
        if isinstance(value, Decimal128):
            return str(value.to_decimal())
        if isinstance(value, ObjectId):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, dict):
            return {k: convert(v) for k, v in value.items()}
        if isinstance(value, list):
            return [convert(v) for v in value]
        return value

    return convert(doc)


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("", summary="List all active holdings")
def list_holdings() -> list[dict]:
    """Return all currently held positions (excludes soft-deleted exits)."""
    docs = list(
        Collections.holdings().find({"deleted_at": None}).sort("invested_amount", -1)
    )
    return [_doc_to_response(d) for d in docs]


@router.get("/{isin}", summary="Get a single holding by ISIN")
def get_holding(isin: str) -> dict:
    doc = Collections.holdings().find_one({"isin": isin, "deleted_at": None})
    if not doc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"No active holding for ISIN {isin}"
        )
    return _doc_to_response(doc)


@router.post("", summary="Record a BUY (creates or adds to a holding)", status_code=201)
def add_buy(req: AddBuyRequest) -> dict:
    """Record a BUY transaction. Holding is recomputed and returned.

    Symbol+exchange is resolved to ISIN via yfinance. If the holding already
    exists, this just adds another lot (FIFO).
    """
    # Resolve ISIN
    # Resolve ISIN: prefer explicit, fall back to yfinance lookup
    meta = fetch_metadata(req.symbol, req.exchange)
    isin = (req.isin or meta["isin"] or "").strip().upper()
    if not isin or len(isin) != 12 or not isin.isalnum():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Could not resolve ISIN for {req.symbol} on {req.exchange} "
            f"(yfinance returned '{meta['isin']}'). "
            f"Please supply isin explicitly in the request body.",
        )

    # Build the transaction
    tx = Transaction(
        isin=isin,
        symbol=req.symbol.upper(),
        exchange=req.exchange.upper(),
        type="BUY",
        quantity=req.quantity,
        price=req.price,
        trade_date=req.trade_date,
        total_fees=req.total_fees,
        notes=req.notes,
        source="manual",
        remaining_quantity=req.quantity,  # initially all of it
    )
    Collections.transactions().insert_one(tx.to_mongo())

    # Recompute holding from full transaction history
    holding = recompute_holding(isin)
    if not holding:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Holding recompute returned None unexpectedly",
        )

    doc = Collections.holdings().find_one({"isin": isin, "deleted_at": None})
    return _doc_to_response(doc)


@router.post("/{isin}/sell", summary="Record a SELL (FIFO depletion)")
def sell(isin: str, req: SellRequest) -> dict:
    """Record a SELL. FIFO depletion happens during recompute. If quantity goes to 0,
    the holding is soft-deleted and 204 is returned."""
    holding = Collections.holdings().find_one({"isin": isin, "deleted_at": None})
    if not holding:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"No active holding for ISIN {isin}"
        )

    held_qty = Decimal(str(holding["quantity"]))
    if Decimal(str(req.quantity)) > held_qty:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Cannot sell {req.quantity}: only {held_qty} held",
        )

    tx = Transaction(
        isin=isin,
        symbol=holding["symbol"],
        exchange=holding.get("exchange", "NSE"),
        type="SELL",
        quantity=req.quantity,
        price=req.price,
        trade_date=req.trade_date,
        total_fees=req.total_fees,
        notes=req.notes,
        source="manual",
    )
    Collections.transactions().insert_one(tx.to_mongo())

    new_holding = recompute_holding(isin)
    if not new_holding:
        # Fully exited
        return {"status": "exited", "isin": isin, "message": "Position fully closed"}

    doc = Collections.holdings().find_one({"isin": isin, "deleted_at": None})
    return _doc_to_response(doc)


@router.patch(
    "/{isin}", summary="Edit holding metadata (notes, thesis, alerts) — NOT quantity"
)
def patch_holding(isin: str, patch: HoldingMetadataPatch) -> dict:
    """Update editable metadata. Quantity & cost are derived; not editable here."""
    doc = Collections.holdings().find_one({"isin": isin, "deleted_at": None})
    if not doc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"No active holding for ISIN {isin}"
        )

    update = patch.model_dump(exclude_none=True)
    if not update:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields to update")

    update["updated_at"] = utcnow()
    Collections.holdings().update_one(
        {"isin": isin, "deleted_at": None},
        {"$set": _convert_decimals_to_decimal128(update)},
    )

    new_doc = Collections.holdings().find_one({"isin": isin, "deleted_at": None})
    return _doc_to_response(new_doc)


@router.get("/{isin}/transactions", summary="List all transactions for a stock")
def list_transactions(isin: str) -> list[dict]:
    """Return all transactions (BUY/SELL/DIVIDEND/etc.) for one stock, oldest first."""
    txs = list(
        Collections.transactions()
        .find({"isin": isin, "deleted_at": None})
        .sort("trade_date", 1)
    )
    return [_doc_to_response(t) for t in txs]
