"""Hermetic tests for suggestion model invariants (#76 U5-a).

Pure Pydantic validation — no Atlas, no network.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from bson import ObjectId

from app.models.suggestion import CandidateScore, SuggestionOutcome


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


# ── TD7/#45: sell group scores are first-class CandidateScore fields ──


def _candidate_kwargs(**overrides) -> dict:
    base = {
        "isin": "INE002A01018",
        "symbol": "RELIANCE",
        "name": "Reliance Industries",
        "sector": "Energy",
        "composite_score": 72.5,
        "rank": 1,
        "confidence_score": 90.0,
    }
    base.update(overrides)
    return base


def test_candidate_score_carries_sell_group_fields():
    """#45: a sell candidate persists booking_opportunity/valuation_stretch/
    risk/tax_concentration as first-class fields (previously dropped, leaving
    only 0.0 buy-named fields and empty group_meta)."""
    c = CandidateScore(
        **_candidate_kwargs(
            booking_opportunity_score=81.0,
            valuation_stretch_score=64.0,
            risk_score=55.0,
            tax_concentration_score=48.0,
        )
    )
    assert c.booking_opportunity_score == 81.0
    assert c.valuation_stretch_score == 64.0
    assert c.risk_score == 55.0
    assert c.tax_concentration_score == 48.0
    # Buy-named fields stay 0.0 on a sell candidate — direction disambiguates.
    assert c.quality_score == 0.0
    assert c.valuation_score == 0.0
    assert c.momentum_score == 0.0
    assert c.news_score == 0.0


def test_candidate_score_sell_fields_default_zero_for_legacy_and_buy():
    """#45: pre-#45 persisted docs (and every buy candidate) never carried the
    sell fields; extra='forbid' means they must be declared, and they must
    default to 0.0 so historical rows hydrate cleanly without a backfill."""
    # A buy candidate populates only the buy quartet.
    buy = CandidateScore(
        **_candidate_kwargs(
            quality_score=70.0,
            valuation_score=60.0,
            momentum_score=65.0,
            news_score=50.0,
        )
    )
    assert buy.quality_score == 70.0
    assert buy.booking_opportunity_score == 0.0
    assert buy.valuation_stretch_score == 0.0
    assert buy.risk_score == 0.0
    assert buy.tax_concentration_score == 0.0

    # A legacy doc with none of the group fields still hydrates (all default 0).
    legacy = CandidateScore(**_candidate_kwargs())
    assert legacy.booking_opportunity_score == 0.0
    assert legacy.risk_score == 0.0
