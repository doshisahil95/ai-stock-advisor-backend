"""Instruments & symbol overrides API.

Read-only on instruments (refreshed by cron).
Full CRUD on symbol overrides for ICICI/Zerodha/etc internal codes.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.db.client import Collections
from app.services.instrument_service import (
    add_override,
    delete_override,
    list_overrides,
    lookup_metadata,
)

router = APIRouter(prefix="/instruments", tags=["instruments"])

# ── Instruments (read-only) ──────────────────────────────────────────────────


# NOTE: the static "/search/..." route MUST be declared before the dynamic
# "/{exchange}/{symbol}" route. FastAPI matches in registration order, so if the
# dynamic route comes first it captures "/instruments/search/INFY" as
# exchange="search", symbol="INFY" and the search endpoint becomes unreachable.
@router.get("/search/{symbol_prefix}", summary="Search instruments by symbol prefix")
def search_instruments(symbol_prefix: str, limit: int = 20) -> list[dict]:
    """Find instruments whose symbol starts with the given prefix.

    Useful for confirming an ICICI symbol exists in the NSE master before
    creating an override.
    """
    cursor = (
        Collections.instruments()
        .find(
            {"symbol": {"$regex": f"^{symbol_prefix.upper()}", "$options": ""}},
            {"_id": 0, "exchange": 1, "symbol": 1, "isin": 1, "name": 1},
        )
        .limit(limit)
    )
    return list(cursor)


@router.get(
    "/{exchange}/{symbol}", summary="Look up an instrument by exchange and symbol"
)
def get_instrument(exchange: str, symbol: str) -> dict:
    """Returns full metadata for an instrument, or 404 if not found."""
    meta = lookup_metadata(symbol, exchange, broker="ICICI")
    if not meta:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"No instrument found for {exchange}:{symbol}",
        )
    # Convert datetime to ISO strings for JSON
    return {
        k: (v.isoformat() if hasattr(v, "isoformat") else v)
        for k, v in meta.items()
        if k != "_id"
    }


# ── Overrides ────────────────────────────────────────────────────────────────

BrokerType = Literal["ICICI", "ZERODHA", "OTHER"]


class CreateOverrideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_broker: BrokerType = "ICICI"
    source_symbol: str = Field(
        ..., description="Symbol as the broker shows it (e.g., 'SHK')"
    )
    target_exchange: str = Field(default="NSE", pattern=r"^(NSE|BSE)$")
    target_symbol: str = Field(
        ..., description="Canonical NSE symbol (e.g., 'SUDARSCHEM')"
    )
    notes: str = Field(default="", description="Optional context")


@router.post("/overrides", summary="Add or update a symbol override", status_code=200)
def create_override(req: CreateOverrideRequest) -> dict:
    """Map a broker's internal symbol to its canonical NSE/BSE symbol.

    Validates that the target symbol exists in the instruments collection.
    """
    try:
        result = add_override(
            source_symbol=req.source_symbol,
            target_symbol=req.target_symbol,
            target_exchange=req.target_exchange,
            source_broker=req.source_broker,
            notes=req.notes,
        )
        return {"status": "ok", **result}
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


@router.get("/overrides", summary="List all symbol overrides")
def get_overrides(source_broker: BrokerType | None = None) -> list[dict]:
    """List overrides. Optionally filter by broker."""
    overrides = list_overrides(source_broker=source_broker)
    # Convert datetime fields to ISO strings
    for o in overrides:
        for k in ("created_at", "updated_at"):
            if k in o and hasattr(o[k], "isoformat"):
                o[k] = o[k].isoformat()
    return overrides


@router.delete(
    "/overrides/{source_broker}/{source_symbol}", summary="Remove a symbol override"
)
def remove_override(source_broker: BrokerType, source_symbol: str) -> dict:
    deleted = delete_override(source_broker, source_symbol)
    if not deleted:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"No override found for {source_broker}:{source_symbol.upper()}",
        )
    return {
        "status": "deleted",
        "source_broker": source_broker,
        "source_symbol": source_symbol.upper(),
    }
