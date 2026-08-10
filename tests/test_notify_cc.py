"""Hermetic tests for the #83 (#60 Part A) RESEND_CC BCC parser.

Pure string parsing over settings.RESEND_CC — no Atlas, no network, no Resend
call. Exercises app.services.notify._parse_cc_recipients directly so the
merge/de-dupe/primary-exclusion contract is locked down without hitting the
email transport. The email() payload-shaping (bcc key only when non-empty AND
include_cc=True) is asserted via a monkeypatched resend.Emails.send below.
"""

from __future__ import annotations

import pytest

from app.services import notify


def test_parse_cc_empty_returns_empty(monkeypatch):
    """Unset RESEND_CC -> no BCC (byte-identical to pre-#83)."""
    monkeypatch.setattr(notify.settings, "RESEND_CC", "")
    assert notify._parse_cc_recipients("sahil@example.com") == []


def test_parse_cc_splits_strips_and_orders(monkeypatch):
    monkeypatch.setattr(
        notify.settings, "RESEND_CC", " advisor@example.com , spouse@example.com "
    )
    assert notify._parse_cc_recipients("sahil@example.com") == [
        "advisor@example.com",
        "spouse@example.com",
    ]


def test_parse_cc_drops_empty_entries(monkeypatch):
    monkeypatch.setattr(
        notify.settings, "RESEND_CC", "advisor@example.com,, ,spouse@example.com,"
    )
    assert notify._parse_cc_recipients("sahil@example.com") == [
        "advisor@example.com",
        "spouse@example.com",
    ]


def test_parse_cc_dedupes_case_insensitively(monkeypatch):
    monkeypatch.setattr(
        notify.settings,
        "RESEND_CC",
        "advisor@example.com,ADVISOR@example.com,advisor@example.com",
    )
    assert notify._parse_cc_recipients("sahil@example.com") == ["advisor@example.com"]


def test_parse_cc_excludes_primary(monkeypatch):
    """The primary recipient is never also BCC'd (case-insensitive)."""
    monkeypatch.setattr(
        notify.settings, "RESEND_CC", "SAHIL@example.com,advisor@example.com"
    )
    assert notify._parse_cc_recipients("sahil@example.com") == ["advisor@example.com"]


def _capture_send(monkeypatch) -> dict:
    """Swap resend.Emails.send for a capture that records the payload and
    returns a success-shaped response, so email() runs end-to-end without a
    real network call."""
    captured: dict = {}

    def _fake_send(payload):
        captured["payload"] = payload
        return {"id": "test-msg-id"}

    monkeypatch.setattr(notify.resend.Emails, "send", staticmethod(_fake_send))
    return captured


def test_email_adds_bcc_when_cc_set_and_included(monkeypatch):
    monkeypatch.setattr(notify.settings, "RESEND_TO", "sahil@example.com")
    monkeypatch.setattr(notify.settings, "RESEND_CC", "advisor@example.com")
    captured = _capture_send(monkeypatch)

    res = notify.email(subject="s", html="<p>h</p>")

    assert res["ok"] is True
    assert captured["payload"]["to"] == "sahil@example.com"
    assert captured["payload"]["bcc"] == ["advisor@example.com"]


def test_email_omits_bcc_when_include_cc_false(monkeypatch):
    """cron-health path: include_cc=False keeps mail author-only even when
    RESEND_CC is populated."""
    monkeypatch.setattr(notify.settings, "RESEND_TO", "sahil@example.com")
    monkeypatch.setattr(notify.settings, "RESEND_CC", "advisor@example.com")
    captured = _capture_send(monkeypatch)

    res = notify.email(subject="s", html="<p>h</p>", include_cc=False)

    assert res["ok"] is True
    assert "bcc" not in captured["payload"]


def test_email_omits_bcc_when_cc_unset(monkeypatch):
    """Byte-identical to pre-#83: no bcc key added at all when RESEND_CC=''."""
    monkeypatch.setattr(notify.settings, "RESEND_TO", "sahil@example.com")
    monkeypatch.setattr(notify.settings, "RESEND_CC", "")
    captured = _capture_send(monkeypatch)

    res = notify.email(subject="s", html="<p>h</p>")

    assert res["ok"] is True
    assert "bcc" not in captured["payload"]
