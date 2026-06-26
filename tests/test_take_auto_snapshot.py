from datetime import datetime
from decimal import Decimal

from app.services import reconciliation
from app.services.reconciliation import (
    DRIFT_ALERT_THRESHOLD_INVESTED,
    take_auto_snapshot,
)


def _our(invested):
    return {
        "our_invested": Decimal(invested),
        "our_current_value": Decimal("0"),
        "our_day_gain": Decimal("0"),
        "our_unrealized_pnl": Decimal("0"),
    }


def test_no_manual_baseline_skips_drift_block(fake_db, monkeypatch):
    monkeypatch.setattr(reconciliation, "_get_our_numbers", lambda: _our("100000"))
    snap = take_auto_snapshot()
    assert snap["type"] == "auto"
    assert "has_drift" not in snap  # no manual baseline -> drift block skipped


def test_no_drift_when_invested_matches(fake_db, monkeypatch):
    monkeypatch.setattr(reconciliation, "_get_our_numbers", lambda: _our("100000"))
    fake_db["reconciliation_snapshots"].seed(
        {
            "type": "manual",
            "our_invested": Decimal("100000"),
            "taken_at": datetime(2024, 1, 1),
        }
    )
    fired = []
    monkeypatch.setattr(
        reconciliation,
        "_send_auto_drift_alert",
        lambda **k: fired.append(k) or ["ntfy"],
    )

    snap = take_auto_snapshot()

    assert snap["drift_invested"] == Decimal("0")
    assert snap["has_drift"] is False
    assert snap["alerts_sent"] == []
    assert fired == []


def test_drift_above_threshold_fires_alert(fake_db, monkeypatch):
    monkeypatch.setattr(reconciliation, "_get_our_numbers", lambda: _our("105000"))
    fake_db["reconciliation_snapshots"].seed(
        {
            "type": "manual",
            "our_invested": Decimal("100000"),
            "taken_at": datetime(2024, 1, 1),
        }
    )
    fired = []
    monkeypatch.setattr(
        reconciliation,
        "_send_auto_drift_alert",
        lambda **k: fired.append(k) or ["ntfy"],
    )

    snap = take_auto_snapshot()

    assert snap["drift_invested"] == Decimal("5000")
    assert snap["has_drift"] is True
    assert snap["alerts_sent"] == ["ntfy"]
    assert len(fired) == 1


def test_rising_edge_suppresses_repeat_alert(fake_db, monkeypatch):
    monkeypatch.setattr(reconciliation, "_get_our_numbers", lambda: _our("105000"))
    fake_db["reconciliation_snapshots"].seed(
        {
            "type": "manual",
            "our_invested": Decimal("100000"),
            "taken_at": datetime(2024, 1, 1),
        },
        {
            "type": "auto",
            "our_invested": Decimal("105000"),
            "taken_at": datetime(2024, 1, 10),
            "has_drift": True,
        },
    )
    fired = []
    monkeypatch.setattr(
        reconciliation,
        "_send_auto_drift_alert",
        lambda **k: fired.append(k) or ["ntfy"],
    )

    snap = take_auto_snapshot()

    assert snap["has_drift"] is True
    # prior auto snapshot already had drift -> rising-edge dedupe, no re-alert.
    assert snap["alerts_sent"] == []
    assert fired == []


def test_drift_exactly_at_threshold_is_not_drift(fake_db, monkeypatch):
    # has_drift uses a strict ">", so exactly the threshold is NOT drift.
    monkeypatch.setattr(
        reconciliation,
        "_get_our_numbers",
        lambda: _our(Decimal("100000") + DRIFT_ALERT_THRESHOLD_INVESTED),
    )
    fake_db["reconciliation_snapshots"].seed(
        {
            "type": "manual",
            "our_invested": Decimal("100000"),
            "taken_at": datetime(2024, 1, 1),
        }
    )

    snap = take_auto_snapshot()

    assert snap["drift_invested"] == DRIFT_ALERT_THRESHOLD_INVESTED
    assert snap["has_drift"] is False
