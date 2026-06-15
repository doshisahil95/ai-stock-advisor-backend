"""CRUD endpoints for the user's watchlist (F13).

A "watchlist" entry is a monitored_stocks doc with status=="watchlist". We do
NOT add a parallel collection -- the MonitoredStock model already declares the
"watchlist" status and the F13 fields (target_buy_price / alert_* / tags /
user_notes / thesis / conviction). See PROJECT_STATE Section 7 + Section 8.

How this coexists with the feedback path (POST /suggestions/{isin}/feedback):
- monitored_stocks is one-doc-per-ISIN (both writers upsert on {isin}). status
  is a single field, so an ISIN is EITHER a feedback state (tracking/passed/
  rejected) OR watchlist -- never two rows. PUT here flips status to
  "watchlist"; a previously-rejected/acted ISIN is thereby un-excluded
  (get_excluded_isins only scans rejected/tracking -- see suggestion_engine).
- The isin_unique_active partial index (partialFilterExpression status:
  "tracking") is untouched: it only constrains tracking docs, so a watchlist
  doc is outside it. Single-doc-per-ISIN is upheld by the upsert-on-{isin}.

Write-before-apply (F10 INVARIANT): every mutation logs to
monitored_stocks_audit via log_change BEFORE the monitored_stocks write, the
same order submit_feedback uses (see PROJECT_STATE Section 11 + Section 14).

Universe wiring: build_universe() = NIFTY 100 UNION watchlist (Unit 1), and the
weekly fundamentals + news crons fold in watchlist ISINs (Unit 3) -- that is
the F13 data-volume multiplier (TD33 Tavily daily quota).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from bson import Decimal128, ObjectId
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, ConfigDict, Field

from app.db.client import Collections
from app.models._common import Money, _convert_decimals_to_decimal128, utcnow
from app.models.monitored_stock import AlertOn, MonitoredStockWatchlistPatch
from app.services import monitored_stocks_audit_service
from app.services.price_service import bulk_get_latest_prices

log = logging.getLogger(__name__)

router = APIRouter(prefix="/watchlist", tags=["watchlist"])

_ISIN = Path(..., min_length=12, max_length=12, pattern=r"^[A-Z0-9]{12}$")


def _jsonable(v: Any) -> Any:
    """Recursively convert Mongo/Decimal types to JSON-friendly values.

    Mirrors suggestions.py:_decimal_to_jsonable. Kept local (not shared) so
    this router doesn't reach into another router's private helper; the
    project already keeps a per-router copy of this small serializer.
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


def _serialize_row(row: dict, price_doc: dict | None) -> dict:
    """Serialize a watchlist monitored_stocks doc + latest price for the API.

    Price enrichment is price-only (latest close + as-of date) via
    bulk_get_latest_prices, which already prefers today's intraday quote over
    the latest EOD bar. Fundamentals/news are intentionally NOT folded in here
    (kept cheap; the heavier data lives behind the existing dossier surfaces).
    """
    out = _jsonable(dict(row))
    out["_id"] = str(row["_id"])
    if price_doc:
        out["current_price"] = _jsonable(price_doc.get("close"))
        out["price_as_of"] = _jsonable(price_doc.get("date"))
    else:
        out["current_price"] = None
        out["price_as_of"] = None
    return out


class WatchlistUpsert(BaseModel):
    """Request body for PUT /watchlist/{isin} (create or update).

    extra="forbid" so a typo'd field is a 422, not a silent no-op. All fields
    optional: a bare {} PUT just (re)asserts watchlist membership. note is the
    audit-trail note and is NOT persisted onto the monitored_stocks doc.
    """

    model_config = ConfigDict(extra="forbid")

    target_buy_price: Money | None = None
    alert_above: Money | None = None
    alert_below: Money | None = None
    alert_on: list[AlertOn] | None = None
    tags: list[str] | None = None
    user_notes: str | None = Field(default=None, max_length=2000)
    thesis: str | None = Field(default=None, max_length=2000)
    conviction: float | None = Field(default=None, ge=0, le=1)
    symbol: str | None = None
    name: str | None = None
    note: str = Field(default="", max_length=500)


@router.get("")
def list_watchlist() -> list[dict]:
    """All watchlist entries, newest-interest first, price-enriched."""
    rows = list(
        Collections.monitored_stocks()
        .find({"status": "watchlist"})
        .sort("last_user_interest_at", -1)
    )
    isins = [r["isin"] for r in rows]
    prices = bulk_get_latest_prices(isins) if isins else {}
    return [_serialize_row(r, prices.get(r["isin"])) for r in rows]


@router.get("/{isin}")
def get_watchlist_entry(isin: str = _ISIN) -> dict:
    """One watchlist entry (404 if the ISIN isn't currently watchlisted)."""
    row = Collections.monitored_stocks().find_one({"isin": isin, "status": "watchlist"})
    if not row:
        raise HTTPException(status_code=404, detail=f"{isin} is not on the watchlist")
    prices = bulk_get_latest_prices([isin])
    return _serialize_row(row, prices.get(isin))


@router.put("/{isin}")
def upsert_watchlist_entry(payload: WatchlistUpsert, isin: str = _ISIN) -> dict:
    """Create or update a watchlist entry (idempotent).

    Order of operations (write-before-apply, mirrors submit_feedback):
      1. Validate the ISIN is a known instrument (404 otherwise).
      2. Read previous status -> decide add-vs-update audit action.
      3. Write monitored_stocks_audit row BEFORE the apply (F10 INVARIANT).
      4. Upsert monitored_stocks via the typed MonitoredStockWatchlistPatch.

    Flipping status to "watchlist" un-excludes an ISIN that was previously
    rejected/acted (get_excluded_isins only scans rejected/tracking).
    """
    now = utcnow()

    # 1. Unknown-ISIN guard. build_universe + price/news/fundamentals all
    #    resolve symbol/exchange from instruments; a watchlist row with no
    #    instrument is inert, so reject it loudly instead of storing dead data.
    instrument = Collections.instruments().find_one(
        {"isin": isin},
        {"_id": 0, "symbol": 1, "name": 1, "exchange": 1, "sector": 1, "industry": 1},
    )
    if not instrument:
        raise HTTPException(
            status_code=404,
            detail=f"{isin} not found in instruments; cannot watchlist an unknown security",
        )

    # 2. Previous status drives the audit action and tells us whether this PUT
    #    is un-excluding a rejected/acted ISIN.
    existing = Collections.monitored_stocks().find_one(
        {"isin": isin}, {"_id": 0, "status": 1}
    )
    previous_status = existing.get("status") if existing else None
    audit_action = (
        "watchlist_update" if previous_status == "watchlist" else "watchlist_add"
    )

    # 3. Audit BEFORE apply (F10 invariant; same order as submit_feedback).
    monitored_stocks_audit_service.log_change(
        isin=isin,
        action=audit_action,
        previous_status=previous_status,
        new_status="watchlist",
        note=payload.note,
        performed_at=now,
    )

    # 4. Apply. Construct the typed patch (catches Literal drift on status /
    #    alert_on). exclude_none keeps unspecified optional fields untouched on
    #    a re-PUT. Money fields -> Decimal128 before they hit Mongo (raw
    #    Decimal is not BSON-encodable).
    patch = MonitoredStockWatchlistPatch(
        isin=isin,
        target_buy_price=payload.target_buy_price,
        alert_above=payload.alert_above,
        alert_below=payload.alert_below,
        alert_on=payload.alert_on,
        tags=payload.tags,
        user_notes=payload.user_notes,
        thesis=payload.thesis,
        conviction=payload.conviction,
        last_user_interest_at=now,
        updated_at=now,
    )
    set_doc = _convert_decimals_to_decimal128(patch.model_dump(exclude_none=True))

    result = Collections.monitored_stocks().update_one(
        {"isin": isin},
        {
            "$set": set_doc,
            "$setOnInsert": {
                "created_at": now,
                "added_at": now,
                "added_by": "user_explicit",
                "added_reason": "watchlist",
                "symbol": payload.symbol or instrument.get("symbol", ""),
                "name": payload.name or instrument.get("name", ""),
                "exchange": instrument.get("exchange", "NSE"),
                "sector": instrument.get("sector", ""),
                "industry": instrument.get("industry", ""),
                "_schema_version": 1,
            },
        },
        upsert=True,
    )

    log.info(
        "Watchlist upsert %s: action=%s prev_status=%s inserted=%s",
        isin,
        audit_action,
        previous_status,
        result.upserted_id is not None,
    )

    row = Collections.monitored_stocks().find_one({"isin": isin})
    prices = bulk_get_latest_prices([isin])
    return _serialize_row(row, prices.get(isin))


@router.delete("/{isin}")
def delete_watchlist_entry(isin: str = _ISIN) -> dict:
    """Hard-delete a watchlist entry.

    Only deletes when the doc is currently status=="watchlist": a
    tracking/passed/rejected doc carries feedback history (F6/F5b) and must
    never be nuked via the watchlist path -- those 404 here. The audit row
    (written before the delete) preserves the record of the removal.
    """
    existing = Collections.monitored_stocks().find_one(
        {"isin": isin}, {"_id": 0, "status": 1}
    )
    if not existing or existing.get("status") != "watchlist":
        raise HTTPException(status_code=404, detail=f"{isin} is not on the watchlist")

    now = utcnow()
    monitored_stocks_audit_service.log_change(
        isin=isin,
        action="watchlist_remove",
        previous_status="watchlist",
        new_status="removed",
        note="",
        performed_at=now,
    )
    result = Collections.monitored_stocks().delete_one(
        {"isin": isin, "status": "watchlist"}
    )
    log.info("Watchlist remove %s: deleted=%d", isin, result.deleted_count)
    return {"isin": isin, "deleted": result.deleted_count == 1}
