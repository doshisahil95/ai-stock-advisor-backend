"""Capital-gains tax view API (F11 / #39).

GET /tax/capital-gains?fy=YYYY-YY  ->  STCG/LTCG per-lot breakdown + aggregates
for an Indian financial year (1 Apr -> 31 Mar, IST). Read-only over the Phase-1
ledger; the FIFO / 49(2C) / holding-period invariants live in
app/services/tax_service.py.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from bson import Decimal128, ObjectId
from fastapi import APIRouter, HTTPException, Query

from app.services import tax_service

router = APIRouter(prefix="/tax", tags=["tax"])

# fy is optional; omitted -> current IST financial year (tax_service.current_fy()).
# Charset is guarded here; the consecutive-year rule lives in tax_service.parse_fy.
_FY = Query(
    default=None, pattern=r"^\d{4}-\d{2}$", description="Financial year, e.g. 2025-26"
)


def _jsonable(v: Any) -> Any:
    """Recursively convert Mongo/Decimal types to JSON-friendly values.

    Mirrors watchlist.py / cost_basis.py: a per-router copy of the small
    serializer so this router doesn't reach into another router's private helper.
    """
    if isinstance(v, Decimal128):
        return str(v.to_decimal())
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, datetime):
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()
    if isinstance(v, list):
        return [_jsonable(x) for x in v]
    if isinstance(v, dict):
        return {k: _jsonable(val) for k, val in v.items()}
    return v


@router.get("/capital-gains")
def capital_gains(fy: str | None = _FY) -> dict:
    """STCG/LTCG per-lot capital-gains breakdown for the financial year.

    `fy` defaults to the current IST FY when omitted. A malformed shape is a 422
    at the Query boundary; a well-formed but non-consecutive fy (e.g. 2025-27)
    raises FyParseError, surfaced here as a 422.
    """
    try:
        result = tax_service.compute_capital_gains(fy)
    except tax_service.FyParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _jsonable(result)
