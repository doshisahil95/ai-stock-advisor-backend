"""Cron health API (F4)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from bson import Decimal128, ObjectId
from fastapi import APIRouter

from app.services.cron_heartbeat_service import (
    count_today_heartbeats,
    get_latest_per_cron,
    get_recent_heartbeats,
    get_registry,
    is_expected_today,
    ist_today_window_utc,
)

router = APIRouter(prefix="/cron", tags=["cron"])


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
    "/heartbeats",
    summary="Recent cron heartbeats + per-cron health summary",
)
def get_heartbeats(limit: int = 200) -> dict:
    """Returns recent heartbeats plus a per-cron health summary for today.

    Response shape:
      {
        "heartbeats": [...],          # newest first, capped at `limit`
        "health_summary": [
          {
            "cron_name", "description", "schedule",
            "expected_today", "min_runs_per_day",
            "last_run_at", "last_status", "last_error",
            "today_total", "today_success", "today_failure", "today_skipped",
            "healthy"
          }, ...
        ]
      }

    `healthy` is True when either (a) the cron is not expected today, or
    (b) today_success + today_skipped >= min_runs_per_day AND today_failure == 0.
    """
    today_start, tomorrow_start = ist_today_window_utc()
    latest = get_latest_per_cron()

    summary: list[dict] = []
    for spec in get_registry():
        expected = is_expected_today(spec)
        last = latest.get(spec.cron_name)
        today_counts = count_today_heartbeats(
            spec.cron_name,
            ist_today_utc_start=today_start,
            ist_tomorrow_utc_start=tomorrow_start,
        )

        if not expected:
            healthy = True
        else:
            ran_ok = today_counts["success"] + today_counts["skipped"]
            healthy = ran_ok >= spec.min_runs_per_day and today_counts["failure"] == 0

        summary.append(
            {
                "cron_name": spec.cron_name,
                "description": spec.description,
                "schedule": spec.schedule_human,
                "expected_today": expected,
                "min_runs_per_day": spec.min_runs_per_day,
                "last_run_at": last["started_at"] if last else None,
                "last_status": last["status"] if last else None,
                "last_error": last.get("error") if last else None,
                "today_total": today_counts["total"],
                "today_success": today_counts["success"],
                "today_failure": today_counts["failure"],
                "today_skipped": today_counts["skipped"],
                "healthy": healthy,
            }
        )

    heartbeats = get_recent_heartbeats(limit=limit)

    return _serialize(
        {
            "heartbeats": heartbeats,
            "health_summary": summary,
        }
    )
