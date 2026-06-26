"""Admin / ops endpoints (Tailscale-only).

These endpoints exist for operator recovery, not for the dashboard. The whole
app sits behind Tailscale (no public ingress, no middleware -- Tailscale IS the
auth perimeter; see PROJECT_STATE Section 3), so "Tailscale-only" here is the
deployment perimeter, not an in-app auth gate.

POST /admin/recompute/{isin} is the HTTP replacement for the SSH-shell recovery
of a stuck holding -- the fallback the TD19 buy/sell warning path tells the
operator to run ("re-run recompute for this ISIN to refresh"). It delegates to
the existing holdings_service.recompute_holding, which is the ONE authoritative
holdings writer and is serialized per-ISIN via the TD20 advisory lock, so this
endpoint can never interleave with a concurrent buy/sell recompute. We do NOT
add a parallel recompute path.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from bson import Decimal128, ObjectId
from fastapi import APIRouter, HTTPException, Path

from app.db.client import Collections
from app.services.holdings_service import recompute_holding

log = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

_ISIN = Path(..., min_length=12, max_length=12, pattern=r"^[A-Z0-9]{12}$")


def _jsonable(v: Any) -> Any:
    """Recursively convert Mongo/Decimal types to JSON-friendly values.

    Mirrors watchlist.py:_jsonable / suggestions.py:_decimal_to_jsonable. Kept
    router-local (not shared) so this router doesn't reach into another router's
    private helper -- the project keeps a per-router copy of this small serializer.
    """
    if isinstance(v, Decimal128):
        return str(v.to_decimal())
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, list):
        return [_jsonable(x) for x in v]
    if isinstance(v, dict):
        return {k: _jsonable(val) for k, val in v.items()}
    return v


@router.post(
    "/recompute/{isin}",
    summary="Recompute a holding from its ledger (Tailscale-only ops recovery)",
)
def recompute_holding_admin(isin: str = _ISIN) -> dict:
    """Force a FIFO recompute of the holding for `isin` from its transactions.

    HTTP replacement for SSH-shell recovery of a stuck holding (the TD19
    buy/sell `recorded_with_warning` fallback). Delegates to the existing
    holdings_service.recompute_holding -- the only authoritative holdings writer,
    per-ISIN advisory-locked (TD20), idempotent, FIFO-from-scratch. No parallel
    recompute path.

    Returns one of:
      - {"status": "recomputed", "isin", "holding": {...}}
            active holding rebuilt and read back.
      - {"status": "no_active_holding", "isin", "holding": None, "message"}
            recompute_holding returned None (fully exited, or no transactions
            exist for this ISIN). The recompute itself succeeded, so this is a
            200, not a 404 -- mirrors the /sell "exited" envelope.

    Raises:
      - 409 if another recompute for this ISIN is already in progress (TD20
        advisory-lock contention / wait timeout).
      - 500 on any other unexpected failure (logged with a traceback).
    """
    try:
        holding = recompute_holding(isin)
    except RuntimeError as exc:
        # TD20 advisory-lock contention: another recompute for this ISIN is
        # mid-flight and we timed out waiting for the lock.
        log.warning("Admin recompute lock contention for %s: %s", isin, exc)
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:  # surface a clean ops error; the trace is logged
        log.exception("Admin recompute failed for %s", isin)
        raise HTTPException(
            status_code=500,
            detail=f"Recompute failed for {isin}: {exc}",
        )

    if holding is None:
        return {
            "status": "no_active_holding",
            "isin": isin,
            "holding": None,
            "message": (
                "Recompute completed; no active holding remains "
                "(fully exited, or no transactions exist for this ISIN)."
            ),
        }

    # Read the rebuilt active doc back and serialize it (same pattern as the
    # holdings router: recompute, then find_one + serialize for the response).
    doc = Collections.holdings().find_one({"isin": isin, "deleted_at": None})
    return {
        "status": "recomputed",
        "isin": isin,
        "holding": _jsonable(doc) if doc else None,
    }
