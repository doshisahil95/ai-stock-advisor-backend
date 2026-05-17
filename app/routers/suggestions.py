"""Read endpoints for the suggestions engine + feedback writes.

F6 (stateful feedback) + F5b (acted soft-exclude) are wired through
suggestion_engine.get_excluded_isins (run-build time) and
explainability.enrich_run -> _build_user_action (serialization time).
See PROJECT_STATE Section 14 for the two-mechanism rationale.

F10 (feedback audit trail) is wired here via
monitored_stocks_audit_service.log_change, which is invoked BEFORE the
monitored_stocks update_one in submit_feedback (write-before-apply
invariant, same pattern as transactions_audit). The two read endpoints
GET /{isin}/audit and GET /feedback/audit/recent expose the audit data
to the UI and to ops debugging.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Literal

from bson import Decimal128, ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Path, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.db.client import Collections
from app.models._common import utcnow
from app.services import monitored_stocks_audit_service
from app.services.explainability import enrich_run
from app.services.outcome_tracker import compute_system_performance

log = logging.getLogger(__name__)

router = APIRouter(prefix="/suggestions", tags=["suggestions"])


def _decimal_to_jsonable(v: Any) -> Any:
    """Recursively convert Mongo/Decimal types to JSON-friendly values."""
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
        return [_decimal_to_jsonable(x) for x in v]
    if isinstance(v, dict):
        return {k: _decimal_to_jsonable(val) for k, val in v.items()}
    return v


def _serialize_audit(row: dict) -> dict:
    """Serialize a monitored_stocks_audit doc for the API response."""
    out = _decimal_to_jsonable(dict(row))
    out["_id"] = str(row["_id"])
    return out


def _serialize_run(run: dict, include_dossiers: bool = True) -> dict:
    """Serialize a SuggestionRun doc for the API response.

    Calls `enrich_run` at the end so each top candidate carries plain-English
    metadata (signal_meta, group_meta, gate_meta, confidence_meta) and the run
    carries feedback_meta + page_intro.
    """
    out = _decimal_to_jsonable(dict(run))
    out["_id"] = str(run["_id"])

    if include_dossiers and out.get("notes"):
        try:
            out["dossiers"] = json.loads(out["notes"]).get("dossiers", [])
        except (json.JSONDecodeError, TypeError):
            out["dossiers"] = []
    else:
        out["dossiers"] = []

    out.pop("notes", None)
    out.pop("all_candidates", None)  # keep response light

    # Additive enrichment -- never mutates underlying doc, only the response.
    return enrich_run(out)


@router.get("/latest")
def get_latest_suggestion_run() -> dict:
    """Most recent successful suggestion run with full dossiers + explainability."""
    run = Collections.suggestion_runs().find_one(
        {"status": {"$in": ["success", "partial"]}},
        sort=[("run_date", -1)],
    )
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No suggestion runs available yet. Run scripts/run_weekly_suggestions.py first.",
        )
    return _serialize_run(run, include_dossiers=True)


@router.get("/runs")
def list_suggestion_runs(
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
) -> dict:
    """Paginated list of past suggestion runs (no dossiers, just metadata)."""
    cursor = (
        Collections.suggestion_runs()
        .find(
            {"status": {"$in": ["success", "partial"]}},
            {
                "_id": 1,
                "run_date": 1,
                "run_date_ist": 1,
                "run_type": 1,
                "status": 1,
                "universe_size": 1,
                "candidates_post_gates": 1,
                "top_k": 1,
            },
        )
        .sort("run_date", -1)
        .skip(skip)
        .limit(limit)
    )
    runs = [_decimal_to_jsonable(r) for r in cursor]
    for r in runs:
        r["_id"] = str(r["_id"])
    total = Collections.suggestion_runs().count_documents(
        {"status": {"$in": ["success", "partial"]}}
    )
    return {"runs": runs, "total": total, "limit": limit, "skip": skip}


@router.get("/runs/{run_id}")
def get_suggestion_run(run_id: str = Path(...)) -> dict:
    """Get one specific suggestion run with full dossiers + explainability."""
    try:
        oid = ObjectId(run_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail=f"Invalid run id: {run_id}")
    run = Collections.suggestion_runs().find_one({"_id": oid})
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return _serialize_run(run, include_dossiers=True)


@router.get("/performance")
def get_performance() -> dict:
    """Aggregate system-vs-benchmark performance for tracked outcomes."""
    return compute_system_performance()


# F10: static-path audit endpoint declared BEFORE /{isin}/audit so the
# literal "feedback/audit/recent" segment is matched first regardless of
# route-ordering quirks. ISIN is min_length=12 so "feedback" would not match
# the dynamic param anyway, but declaring statically-pathed routes first
# is the safer convention.
@router.get("/feedback/audit/recent")
def get_recent_feedback_audit(
    limit: int = Query(50, ge=1, le=500),
) -> list[dict]:
    """Newest-first feedback audit rows across all monitored stocks (F10).

    Mirrors GET /transactions/audit/recent. Used by ops/debug surfaces and
    by the frontend audit-trail view.
    """
    rows = monitored_stocks_audit_service.get_recent_audit(limit=limit)
    return [_serialize_audit(r) for r in rows]


@router.get("/{isin}/audit")
def get_feedback_audit_for_isin(
    isin: str = Path(..., min_length=12, max_length=12),
    limit: int = Query(50, ge=1, le=500),
) -> list[dict]:
    """Newest-first feedback audit history for one ISIN (F10).

    Mirrors GET /transactions/{id}/audit.
    """
    rows = monitored_stocks_audit_service.get_audit_for_isin(isin, limit=limit)
    return [_serialize_audit(r) for r in rows]


class SuggestionFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["acted", "passed", "rejected"]
    note: str = Field(default="", max_length=500)


@router.post("/{isin}/feedback")
def submit_feedback(
    payload: SuggestionFeedback,
    isin: str = Path(..., min_length=12, max_length=12),
) -> dict:
    """Record user feedback on a suggested candidate.

    Order of operations (matters for crash-safety; mirrors the transactions
    PATCH/DELETE pattern documented in PROJECT_STATE Section 11):
      1. Read existing monitored_stocks doc to capture previous_status.
      2. Write monitored_stocks_audit row BEFORE the update_one apply
         (F10 INVARIANT: append-only, write-before-apply, so intent
         survives even if the apply step crashes).
      3. Apply the monitored_stocks update_one (last-write-wins, upsert).
      4. Re-label the MOST RECENT non-expired outcome for this ISIN. We do
         not update older outcomes -- those represent decisions the user
         made on past suggestions, and re-clicking on a current suggestion
         shouldn't rewrite history. We do not gate on the outcome's
         existing status, so a user changing their mind (e.g. acted ->
         rejected) is reflected on the current outcome.

    The outcome label is metadata only; the daily snapshot job continues
    collecting 30/60/90/180d price points for every non-expired outcome
    regardless of label (see outcome_tracker.snapshot_open_outcomes).
    """
    now = utcnow()

    # 1. Capture previous status BEFORE we mutate.
    existing = Collections.monitored_stocks().find_one(
        {"isin": isin},
        {"_id": 0, "status": 1},
    )
    previous_status: str | None = existing.get("status") if existing else None

    # 2. Resolve new status from the action (last-write-wins; passed/rejected
    #    overwrite even if the prior state was "tracking" because the user is
    #    actively changing their mind).
    if payload.action == "acted":
        new_status = "tracking"
    elif payload.action == "passed":
        new_status = "passed"
    else:  # rejected
        new_status = "rejected"

    # 3. Write the audit row BEFORE applying the update_one. If Mongo
    #    accepts this insert but the update_one below crashes, we still
    #    have the intent on record. Same invariant as transactions_audit.
    monitored_stocks_audit_service.log_change(
        isin=isin,
        action=payload.action,
        previous_status=previous_status,
        new_status=new_status,
        note=payload.note,
        performed_at=now,
    )

    # 4. Apply the monitored_stocks update.
    set_doc: dict[str, Any] = {
        "isin": isin,
        "status": new_status,
        "last_feedback_at": now,
        "last_feedback_action": payload.action,
        "last_feedback_note": payload.note,
        "updated_at": now,
    }
    if payload.action == "acted":
        set_doc["acted_at"] = now
    elif payload.action == "passed":
        set_doc["passed_at"] = now
    elif payload.action == "rejected":
        set_doc["rejected_at"] = now

    result = Collections.monitored_stocks().update_one(
        {"isin": isin},
        {
            "$set": set_doc,
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    # 5. Re-label the most recent non-expired outcome for this ISIN.
    #    Sort by suggested_at desc, take the first one. This is the
    #    suggestion the user is actually looking at on the page.
    latest_outcome = Collections.suggestion_outcomes().find_one(
        {"isin": isin, "tracking_status": {"$ne": "expired"}},
        sort=[("suggested_at", -1)],
        projection={"_id": 1, "tracking_status": 1},
    )
    if latest_outcome:
        Collections.suggestion_outcomes().update_one(
            {"_id": latest_outcome["_id"]},
            {
                "$set": {
                    "tracking_status": payload.action,
                    "user_action_at": now,
                    "user_action_note": payload.note,
                    "updated_at": now,
                }
            },
        )
        log.info(
            "Feedback for %s: action=%s prev_status=%s (relabeled outcome %s from %s); upserted_monitored=%s",
            isin,
            payload.action,
            previous_status,
            latest_outcome["_id"],
            latest_outcome.get("tracking_status"),
            result.upserted_id is not None,
        )
    else:
        log.info(
            "Feedback for %s: action=%s prev_status=%s (no active outcome to relabel); upserted_monitored=%s",
            isin,
            payload.action,
            previous_status,
            result.upserted_id is not None,
        )

    return {
        "isin": isin,
        "action": payload.action,
        "status": new_status,
        "previous_status": previous_status,
    }
