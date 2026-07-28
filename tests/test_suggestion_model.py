"""Hermetic tests for suggestion model invariants (#76 U5-a).

Pure Pydantic validation — no Atlas, no network.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from bson import ObjectId

from app.models.suggestion import SuggestionOutcome


def _outcome_doc(tracking_status: str) -> dict:
    return {
        "isin": "INE002A01018",
        "symbol": "RELIANCE",
        "suggestion_run_id": ObjectId(),
        "suggested_at": datetime(2026, 1, 1),
        "suggested_at_price": Decimal("2400.00"),
        "suggested_rank": 1,
        "suggested_composite_score": 88.0,
        "tracking_status": tracking_status,
    }


def test_suggestion_outcome_hydrates_rejected():
    """#76 U5-a: submit_feedback stamps tracking_status='rejected' and
    outcome_tracker counts a 'rejected' bucket, so the Literal MUST accept it.
    Pre-fix, SuggestionOutcome(**doc) on a rejected row raised ValidationError."""
    out = SuggestionOutcome(**_outcome_doc("rejected"))
    assert out.tracking_status == "rejected"


def test_suggestion_outcome_hydrates_all_feedback_statuses():
    for status in ("open", "acted", "passed", "rejected", "expired"):
        out = SuggestionOutcome(**_outcome_doc(status))
        assert out.tracking_status == status
