"""Reconciliation API."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from bson import Decimal128, ObjectId
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.services.reconciliation import (
    compute_dividend_drift,
    get_latest_snapshot,
    get_snapshot_history,
    take_auto_snapshot,
    take_manual_snapshot,
)

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])


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


class ManualSnapshotPayload(BaseModel):
    icici_invested: float
    icici_current_value: float
    icici_day_gain: float | None = None
    notes: str | None = None
    set_as_baseline: bool = False


@router.get("/latest", summary="Get the most recent snapshot")
def get_latest(snapshot_type: str | None = None) -> dict | None:
    snap = get_latest_snapshot(snapshot_type=snapshot_type)
    return _serialize(snap) if snap else None


@router.get("/history", summary="Get snapshot history (newest first)")
def get_history(limit: int = 30) -> list[dict]:
    limit = max(1, min(limit, 365))
    snapshots = get_snapshot_history(limit=limit)
    return _serialize(snapshots)


@router.get(
    "/dividend-drift",
    summary="Dividend-drift matrix: announced vs received vs booked (#65)",
)
def get_dividend_drift() -> list[dict]:
    """Per held name, announced dividends (yfinance) vs recorded DIVIDEND rows
    vs booked total. Flags a missing_receipt where a payout went ex while held
    but was never recorded (which understates realised gain). Read-only; NOT a
    tax view (dividends are income, not capital gains)."""
    return _serialize(compute_dividend_drift())


@router.post("/snapshot", summary="Record a manual snapshot with ICICI numbers")
def post_snapshot(payload: ManualSnapshotPayload) -> dict:
    try:
        snap = take_manual_snapshot(
            icici_invested=Decimal(str(payload.icici_invested)),
            icici_current_value=Decimal(str(payload.icici_current_value)),
            icici_day_gain=(
                Decimal(str(payload.icici_day_gain))
                if payload.icici_day_gain is not None
                else None
            ),
            notes=payload.notes,
            set_as_baseline=payload.set_as_baseline,
        )
        return _serialize(snap)
    except Exception as exc:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Reconciliation snapshot failed: {exc}",
        )


@router.post("/auto-snapshot", summary="Trigger an automatic snapshot (cron use)")
def post_auto_snapshot() -> dict:
    """Endpoint for the daily cron to call. Captures our-side numbers only."""
    snap = take_auto_snapshot()
    return _serialize(snap)
