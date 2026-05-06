"""Cost-basis adjustments API."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from bson import Decimal128, ObjectId
from fastapi import APIRouter

from app.services.cost_basis_service import get_active_adjustments

router = APIRouter(prefix="/cost-basis", tags=["cost-basis"])


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


@router.get(
    "/adjustments", summary="List all active cost-basis adjustments (audit trail)"
)
def list_adjustments() -> list[dict]:
    return _serialize(get_active_adjustments())
