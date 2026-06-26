from bson import ObjectId

from app.routers.suggestions import SuggestionFeedback, submit_feedback
from app.services import monitored_stocks_audit_service

ISIN = "INE000A01001"


def test_audit_written_before_apply(fake_db, monkeypatch):
    order: list[str] = []
    captured: dict = {}

    def rec_log(**kwargs):
        order.append("audit")
        captured.update(kwargs)
        return ObjectId()

    monkeypatch.setattr(monitored_stocks_audit_service, "log_change", rec_log)

    ms = fake_db["monitored_stocks"]
    orig_update = ms.update_one

    def rec_update(*args, **kwargs):
        order.append("apply")
        return orig_update(*args, **kwargs)

    monkeypatch.setattr(ms, "update_one", rec_update)

    out = submit_feedback(SuggestionFeedback(action="acted"), isin=ISIN)

    # F10 write-before-apply: the audit row lands BEFORE the state mutation.
    assert order == ["audit", "apply"]
    assert captured["previous_status"] is None
    assert captured["new_status"] == "tracking"
    assert captured["action"] == "acted"
    assert out["status"] == "tracking"
    assert out["previous_status"] is None


def test_previous_status_captured(fake_db, monkeypatch):
    monkeypatch.setattr(
        monitored_stocks_audit_service, "log_change", lambda **k: ObjectId()
    )
    fake_db["monitored_stocks"].seed(
        {"isin": ISIN, "status": "rejected", "added_by": "user_explicit"}
    )

    out = submit_feedback(SuggestionFeedback(action="acted"), isin=ISIN)

    assert out["previous_status"] == "rejected"
    assert out["status"] == "tracking"


def test_action_status_mapping(fake_db, monkeypatch):
    monkeypatch.setattr(
        monitored_stocks_audit_service, "log_change", lambda **k: ObjectId()
    )
    for action, expected in [("passed", "passed"), ("rejected", "rejected")]:
        fake_db["monitored_stocks"]._docs.clear()
        out = submit_feedback(SuggestionFeedback(action=action), isin=ISIN)
        assert out["status"] == expected
