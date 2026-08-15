"""Hermetic tests for explainability._build_user_action direction scoping.

#80 badge leak (sibling of #43): a stale user_action badge derived from
monitored_stocks feedback must be scoped to the run's direction. A sell-context
"acted"/"passed" must not collapse the buy card for the same ISIN, and vice
versa. A legacy doc with no feedback_direction matches any direction.

_build_user_action is a pure function (no DB), so these drive it directly.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.services.explainability import _build_user_action

RUN_START = datetime(2026, 6, 1, tzinfo=timezone.utc)
AFTER = datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc)  # at/after run start
BEFORE = datetime(2026, 5, 30, tzinfo=timezone.utc)  # stale, prior run


def _doc(action="acted", at=AFTER, direction=None):
    d = {"last_feedback_action": action, "last_feedback_at": at}
    if direction is not None:
        d["feedback_direction"] = direction
    return d


def test_none_doc_returns_none():
    assert _build_user_action(None, RUN_START, direction="buy") is None


def test_legacy_no_direction_matches_any_direction():
    # No feedback_direction (pre-#43) → badge surfaces regardless of direction.
    doc = _doc(direction=None)
    assert _build_user_action(doc, RUN_START, direction="buy")["action"] == "acted"
    assert _build_user_action(doc, RUN_START, direction="sell")["action"] == "acted"


def test_matching_direction_surfaces_badge():
    doc = _doc(direction="buy")
    got = _build_user_action(doc, RUN_START, direction="buy")
    assert got is not None and got["action"] == "acted"


def test_cross_direction_badge_is_suppressed():
    # THE LEAK: a sell-context feedback must NOT collapse the buy card.
    doc = _doc(direction="sell")
    assert _build_user_action(doc, RUN_START, direction="buy") is None
    # ...and symmetrically.
    doc_buy = _doc(direction="buy")
    assert _build_user_action(doc_buy, RUN_START, direction="sell") is None


def test_stale_feedback_before_run_start_suppressed():
    # Direction matches but the feedback predates this run → still stale → None.
    doc = _doc(at=BEFORE, direction="buy")
    assert _build_user_action(doc, RUN_START, direction="buy") is None


def test_missing_action_returns_none():
    doc = {"last_feedback_at": AFTER, "feedback_direction": "buy"}
    assert _build_user_action(doc, RUN_START, direction="buy") is None
