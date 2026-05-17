"""Append-only audit log for monitored_stocks feedback writes (F10).

Mirrors transactions_audit_service.py. One doc per
/suggestions/{isin}/feedback call. log_change() is invoked BEFORE the
corresponding monitored_stocks update_one apply, so intent survives even
if the apply step crashes. This is the same write-before-apply pattern
used for transactions_audit (see PROJECT_STATE Section 11 + Section 7).

The collection accessor and indexes already exist:
  - Collections.monitored_stocks_audit() in app/db/client.py
  - Indexes (performed_at desc) and (isin, performed_at desc) in
    app/db/indexes.py

Read endpoints that consume this service live in app/routers/suggestions.py:
  - GET /suggestions/{isin}/audit            -> get_audit_for_isin
  - GET /suggestions/feedback/audit/recent   -> get_recent_audit
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Literal

from bson import ObjectId

from app.db.client import Collections

log = logging.getLogger(__name__)

FeedbackAction = Literal["acted", "passed", "rejected"]

# Bump when the audit doc shape changes incompatibly. Read endpoints can
# branch on this field to handle older rows. Mirrors how _schema_version
# is used on cron_heartbeats and suggestion_runs.
SCHEMA_VERSION = 1


def log_change(
    *,
    isin: str,
    action: FeedbackAction,
    previous_status: str | None,
    new_status: str,
    note: str,
    performed_at: datetime,
) -> ObjectId:
    """Append one audit row. Returns the inserted _id.

    INVARIANT: caller must invoke this BEFORE applying the corresponding
    monitored_stocks update, so that even if the update_one crashes the
    intent is preserved. Mirrors transactions_audit_service.log_change
    relative to transactions PATCH/DELETE.

    `performed_at` is a UTC-naive datetime per the project-wide Mongo
    datetime convention (see PROJECT_STATE Section 14, "Datetimes: UTC-naive
    in Mongo"). Caller passes utcnow() from app.models._common.
    """
    doc = {
        "isin": isin,
        "action": action,
        "previous_status": previous_status,
        "new_status": new_status,
        "note": note or "",
        "performed_at": performed_at,
        "_schema_version": SCHEMA_VERSION,
    }
    result = Collections.monitored_stocks_audit().insert_one(doc)
    log.info(
        "monitored_stocks_audit: isin=%s action=%s prev=%s new=%s id=%s",
        isin,
        action,
        previous_status,
        new_status,
        result.inserted_id,
    )
    return result.inserted_id


def get_audit_for_isin(isin: str, limit: int = 50) -> list[dict]:
    """Newest-first feedback audit history for one ISIN.

    Used by GET /suggestions/{isin}/audit. Backed by the
    (isin, performed_at desc) compound index.
    """
    cursor = (
        Collections.monitored_stocks_audit()
        .find({"isin": isin})
        .sort("performed_at", -1)
        .limit(limit)
    )
    return list(cursor)


def get_recent_audit(limit: int = 50) -> list[dict]:
    """Newest-first feedback audit rows across all ISINs.

    Used by GET /suggestions/feedback/audit/recent. Backed by the
    (performed_at desc) index.
    """
    cursor = (
        Collections.monitored_stocks_audit()
        .find({})
        .sort("performed_at", -1)
        .limit(limit)
    )
    return list(cursor)
