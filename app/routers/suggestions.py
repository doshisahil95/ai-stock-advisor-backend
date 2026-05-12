"""Read endpoints for the suggestions engine + feedback writes."""

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


def _serialize_run(run: dict, include_dossiers: bool = True) -> dict:
    """Serialize a SuggestionRun doc for the API response."""
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

    return out


@router.get("/latest")
def get_latest_suggestion_run() -> dict:
    """Most recent successful suggestion run with full dossiers."""
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
    """Get one specific suggestion run with full dossiers."""
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

    Updates monitored_stocks (creates if absent). The "rejected" action drives
    the 90-day rejection window in suggestion_engine.get_rejected_isins().
    """
    now = utcnow()

    set_doc: dict[str, Any] = {
        "isin": isin,
        "last_feedback_at": now,
        "last_feedback_action": payload.action,
        "last_feedback_note": payload.note,
        "updated_at": now,
    }

    if payload.action == "acted":
        set_doc["status"] = "tracking"
        set_doc["acted_at"] = now
    elif payload.action == "passed":
        set_doc["status"] = "passed"
        set_doc["passed_at"] = now
    elif payload.action == "rejected":
        set_doc["status"] = "rejected"
        set_doc["rejected_at"] = now

    result = Collections.monitored_stocks().update_one(
        {"isin": isin},
        {
            "$set": set_doc,
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    if payload.action in ("acted", "passed"):
        Collections.suggestion_outcomes().update_many(
            {"isin": isin, "tracking_status": "open"},
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
        "Feedback for %s: action=%s, upserted=%s",
        isin,
        payload.action,
        result.upserted_id is not None,
    )
    return {
        "isin": isin,
        "action": payload.action,
        "status": set_doc.get("status"),
    }
