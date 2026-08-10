"""Holdings API — read holdings, add via BUY transactions, edit metadata."""

from __future__ import annotations
import logging
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from bson import Decimal128, ObjectId
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.db.client import Collections
from app.models._common import Money, _convert_decimals_to_decimal128, utcnow
from app.models.holding import Holding
from app.models.transaction import Transaction
from app.services.holdings_service import (
    per_isin_write_lock,
    recompute_holding,
    recompute_holding_locked,
    preview_sell,
    validate_replay,
)
from app.services.instrument_service import lookup_isin
from app.services.price_service import (
    annotate_with_current_price,
    bulk_get_latest_prices,
    bulk_get_previous_closes,
    get_latest_price,
    get_previous_close,
    get_price_history,
)
from app.services.yfinance_lookup import fetch_metadata

router = APIRouter(prefix="/portfolio/holdings", tags=["portfolio"])
log = logging.getLogger(__name__)

# ── Request models ───────────────────────────────────────────────────────────


class AddBuyRequest(BaseModel):
    """Record a buy.
    ISIN is auto-resolved via the `instruments` collection
    (NSE master), or you can supply it explicitly to override."""

    model_config = ConfigDict(extra="forbid")
    symbol: str = Field(..., description="e.g., 'INFY'")
    exchange: str = Field(default="NSE", pattern=r"^(NSE|BSE)$")
    # F14 fix (Chat 5.5+): positivity validators so malformed payloads 422
    # before writing a broken transaction to the immutable ledger.
    quantity: Money = Field(..., gt=0)
    price: Money = Field(..., gt=0, description="Per-share price in INR")
    trade_date: datetime
    total_fees: Money = Field(default=Decimal("0"), ge=0)
    notes: str = ""
    isin: str | None = Field(
        default=None,
        description="Optional override. By default, ISIN is looked up from the "
        "instruments collection. Supply this only if the symbol isn't in the "
        "master or you want to override the lookup.",
    )


class SellRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # F14 fix (Chat 5.5+): positivity validators.
    quantity: Money = Field(..., gt=0)
    price: Money = Field(..., gt=0)
    trade_date: datetime
    total_fees: Money = Field(default=Decimal("0"), ge=0)
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


def _serialize_for_response(value):
    """Recursive JSON-serializer for Mongo docs: Decimal128 → str, ObjectId → str, datetime → ISO."""
    from datetime import datetime
    from decimal import Decimal
    from bson import Decimal128, ObjectId

    if isinstance(value, Decimal128):
        return str(value.to_decimal())
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _serialize_for_response(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialize_for_response(v) for v in value]
    return value


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


@router.get("", summary="List all active holdings (with live P&L)")
def list_holdings() -> list[dict]:
    """Return all currently held positions, annotated with live P&L from latest prices."""
    docs = list(
        Collections.holdings().find({"deleted_at": None}).sort("invested_amount", -1)
    )
    if not docs:
        return []

    # Bulk-fetch latest prices for all ISINs in one query
    isins = [d["isin"] for d in docs]
    price_map = bulk_get_latest_prices(isins)

    # Annotate each holding with live P&L
    # Bulk-fetch previous trading day's close for day gain computation
    isin_to_date = {
        d["isin"]: price_map[d["isin"]]["date"] for d in docs if d["isin"] in price_map
    }
    prev_close_map = bulk_get_previous_closes(isin_to_date)

    annotated = [
        annotate_with_current_price(
            d,
            price_map.get(d["isin"]),
            prev_close_map.get(d["isin"]),
        )
        for d in docs
    ]
    return [_doc_to_response(d) for d in annotated]


@router.get("/{isin}", summary="Get a single holding by ISIN (with live P&L)")
def get_holding(isin: str) -> dict:
    doc = Collections.holdings().find_one({"isin": isin, "deleted_at": None})
    if not doc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"No active holding for ISIN {isin}"
        )
    latest = get_latest_price(isin)
    prev_close = get_previous_close(isin, latest["date"]) if latest else None
    annotated = annotate_with_current_price(doc, latest, prev_close)
    return _doc_to_response(annotated)


@router.get(
    "/{isin}/history",
    summary="Get price history (OHLCV) for a holding",
)
def get_holding_history(isin: str, days: int = 90) -> list[dict]:
    """Return the last N trading days of OHLCV for this ISIN.

    Args:
        isin: instrument ISIN
        days: number of trading days to return (default 90, max 2000)

    Returns:
        List of {date, open, high, low, close, volume} sorted oldest → newest.
        Empty list if no price data available.
    """
    days = max(1, min(days, 2000))
    rows = get_price_history(isin, days=days)
    # get_price_history returns newest-first; reverse for chart consumption
    rows.reverse()
    return _serialize_for_response(rows)


@router.get(
    "/{isin}/transactions",
    summary="Get all transactions for a holding (chronological)",
)
def get_holding_transactions(isin: str) -> list[dict]:
    """Return all BUY/SELL/SPLIT/BONUS transactions for this ISIN, oldest → newest.

    Includes corporate actions (splits, bonuses) so the UI can show the full
    audit trail. Excludes only soft-deleted transactions.
    """
    docs = list(
        Collections.transactions()
        .find({"isin": isin, "deleted_at": None})
        .sort("trade_date", 1)
    )
    return _serialize_for_response(docs)


@router.post("", summary="Record a BUY (creates or adds to a holding)", status_code=201)
def add_buy(req: AddBuyRequest) -> dict:
    """Record a BUY transaction. Holding is recomputed and returned.

    Symbol+exchange is resolved to ISIN via yfinance. If the holding already
    exists, this just adds another lot (FIFO).
    """
    # Resolve ISIN
    # Resolve ISIN: prefer explicit, fall back to yfinance lookup
    # Resolve ISIN: prefer explicit, fall back to instruments collection
    isin = (req.isin or "").strip().upper()
    if not isin:
        looked_up = lookup_isin(req.symbol, req.exchange, broker="ICICI")
        isin = (looked_up or "").upper()
    if not isin or len(isin) != 12 or not isin.isalnum():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Could not resolve ISIN for {req.symbol} on {req.exchange}. "
            f"Either supply 'isin' explicitly in the request body, or add a "
            f"symbol_overrides entry if this is an ICICI internal code.",
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
    # TD19: the BUY is now persisted to the immutable ledger (source of truth).
    # recompute_holding rebuilds the *derived* holding aggregate and can fail
    # independently (yfinance metadata fetch, transient Mongo error). Previously
    # such a failure 500'd even though the ledger write had already succeeded,
    # leaving the caller unsure whether the BUY landed. Wrap the recompute so a
    # failure returns success-with-warning instead of masking a persisted write.
    try:
        holding = recompute_holding(isin)
    except Exception:
        log.exception("recompute_holding failed after BUY insert for %s", isin)
        return {
            "status": "recorded_with_warning",
            "isin": isin,
            "warning": (
                "BUY recorded, but the holding aggregate could not be "
                "recomputed and may be stale. Retry, or re-run recompute "
                "for this ISIN to refresh."
            ),
        }
    if not holding:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Holding recompute returned None unexpectedly",
        )

    doc = Collections.holdings().find_one({"isin": isin, "deleted_at": None})
    latest = get_latest_price(isin)
    prev_close = get_previous_close(isin, latest["date"]) if latest else None
    annotated = annotate_with_current_price(doc, latest, prev_close)
    return _doc_to_response(annotated)


@router.post(
    "/{isin}/preview-sell",
    summary="Preview a SELL (no DB writes) — shows realized P&L",
)
def preview_sell_endpoint(isin: str, payload: SellRequest) -> dict:
    """Read-only simulation of a SELL — used by the UI to show preview values
    before the user confirms.

    Same payload shape as the real /sell endpoint, but doesn't write anything.
    """
    # F5 fix (Chat 5.5+): pass total_fees through so preview math matches
    # the persisted realized_pnl on submit (both sides do fee normalization).
    result = preview_sell(
        isin=isin,
        sell_quantity=payload.quantity,
        sell_price=payload.price,
        sell_fees=payload.total_fees,
    )
    return _serialize_for_response(result)


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
    # TD17: the held_qty check above only guards the current total. A BACKDATED
    # SELL can pass it yet drive quantity negative at an intermediate point in
    # the timeline -- which _fifo_replay would only log as an oversell warning,
    # never reject. Replay the full per-ISIN timeline (existing non-deleted
    # transactions + this proposed SELL) and 400 BEFORE writing to the ledger.
    # #80 H1: hold the per-ISIN write lock across read->validate->insert->
    # recompute so two concurrent SELLs can't each pass validate_replay against
    # a stale read and both insert (a combined oversell _fifo_replay only logs).
    # trade_value/created_at are stamped so validate_replay's (trade_date,
    # created_at) tie-break matches the real recompute ordering (#77 U6-c).
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
    tx_doc = tx.to_mongo()
    try:
        with per_isin_write_lock(isin):
            existing_txs = list(
                Collections.transactions().find({"isin": isin, "deleted_at": None})
            )
            proposed_sell = {
                "type": "SELL",
                "quantity": req.quantity,
                "price": req.price,
                "trade_date": req.trade_date,
                "created_at": tx_doc.get("created_at"),
            }
            ok, reason = validate_replay(existing_txs + [proposed_sell])
            if not ok:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, reason)
            Collections.transactions().insert_one(tx_doc)
            # TD19: the SELL is now persisted. recompute rebuilds the derived
            # holding and can fail independently; a failure must not 500 and
            # mask the persisted write (handled below). recompute_holding_locked
            # runs the impl WITHOUT re-acquiring the lock we already hold.
            new_holding = recompute_holding_locked(isin)
    except HTTPException:
        raise
    except RuntimeError as exc:
        # per_isin_write_lock acquire timeout -> another write is in flight.
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    except Exception:
        log.exception("recompute_holding failed after SELL insert for %s", isin)
        return {
            "status": "recorded_with_warning",
            "isin": isin,
            "warning": (
                "SELL recorded, but the holding aggregate could not be "
                "recomputed and may be stale. Retry, or re-run recompute "
                "for this ISIN to refresh."
            ),
        }
    if not new_holding:
        # Fully exited — F12 fix (Chat 5.5+): include realized_total so the
        # frontend's SellSheet onSuccess toast can show 'realized ₹X'
        # instead of 'realized undefined'. Realized total is the lifetime
        # realized P&L on this ISIN (post-recompute), read off the now-
        # soft-deleted doc. Pre-fix the response shape was
        # {status, isin, message} — kept for any non-FE consumer; the
        # frontend discriminator is the absence of '_id', so adding fields
        # is non-breaking.
        final_doc = Collections.holdings().find_one({"isin": isin})
        realized_total = "0"
        if final_doc is not None:
            rv = final_doc.get("realized_pnl")
            if isinstance(rv, Decimal128):
                realized_total = str(rv.to_decimal())
            elif rv is not None:
                realized_total = str(rv)
        return {
            "status": "exited",
            "isin": isin,
            "message": "Position fully closed",
            "realized_total": realized_total,
        }

    doc = Collections.holdings().find_one({"isin": isin, "deleted_at": None})
    latest = get_latest_price(isin)
    prev_close = get_previous_close(isin, latest["date"]) if latest else None
    annotated = annotate_with_current_price(doc, latest, prev_close)
    return _doc_to_response(annotated)


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
