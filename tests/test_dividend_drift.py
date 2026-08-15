"""Hermetic tests for reconciliation.compute_dividend_drift (#65).

compute_dividend_drift is a PURE read over dividend_announcements x holdings x
transactions (DIVIDEND rows) x holdings.total_dividends_received, with a
news_articles corroboration column. It classifies each announced ex-date as
matched / missing_receipt / pending. These tests drive that classification via
the hermetic fake_db (no Atlas, no yfinance, no ntfy).

"now" is pinned by monkeypatching reconciliation.utcnow so the settle-margin /
future-ex-date branches are deterministic.
"""

from datetime import datetime
from decimal import Decimal

import pytest

from app.services import reconciliation
from app.services.reconciliation import (
    _DIVIDEND_MATCH_WINDOW_DAYS,
    _DIVIDEND_SETTLE_MARGIN_DAYS,
    compute_dividend_drift,
)

ISIN = "INE787D01026"
NOW = datetime(2026, 6, 1)  # fixed reference "today"


@pytest.fixture
def frozen_now(monkeypatch):
    monkeypatch.setattr(reconciliation, "utcnow", lambda: NOW)
    return NOW


def _hold(qty="100", first=datetime(2020, 1, 1), booked="0"):
    return {
        "isin": ISIN,
        "symbol": "BALKRISIND",
        "quantity": Decimal(qty),
        "first_purchased_at": first,
        "total_dividends_received": Decimal(booked),
        "deleted_at": None,
    }


def _ann(ex_date, amount="4.0"):
    return {
        "isin": ISIN,
        "symbol": "BALKRISIND",
        "exchange": "NSE",
        "ex_date": ex_date,
        "amount_per_share": Decimal(amount),
        "source": "yfinance",
    }


def _div_txn(trade_date, price="4.0"):
    return {
        "isin": ISIN,
        "type": "DIVIDEND",
        "trade_date": trade_date,
        "price": Decimal(price),
        "deleted_at": None,
    }


def _row(drift):
    """Single-name convenience: the one row for ISIN."""
    rows = [r for r in drift if r["isin"] == ISIN]
    assert len(rows) == 1
    return rows[0]


def test_missing_receipt_when_held_and_ex_date_passed(fake_db, frozen_now):
    # Ex-date well past the settle margin, held across it, no DIVIDEND row.
    ex = datetime(2026, 1, 10)  # ~140 days before NOW
    fake_db["holdings"].seed(_hold(qty="700"))
    fake_db["dividend_announcements"].seed(_ann(ex, "4.0"))

    row = _row(compute_dividend_drift())

    assert row["missing_count"] == 1
    a = row["announcements"][0]
    assert a["status"] == "missing_receipt"
    # expected_amount = per-share * quantity
    assert a["expected_amount"] == Decimal("4.0") * Decimal("700")


def test_matched_when_dividend_recorded_in_window(fake_db, frozen_now):
    ex = datetime(2026, 1, 10)
    # A DIVIDEND recorded 15 days after ex-date -> within the +/-21d match window.
    recorded = datetime(2026, 1, 25)
    assert abs((recorded - ex).days) <= _DIVIDEND_MATCH_WINDOW_DAYS
    fake_db["holdings"].seed(_hold(qty="700"))
    fake_db["dividend_announcements"].seed(_ann(ex, "4.0"))
    fake_db["transactions"].seed(_div_txn(recorded, "4.0"))

    row = _row(compute_dividend_drift())

    assert row["missing_count"] == 0
    a = row["announcements"][0]
    assert a["status"] == "matched"
    assert a["matched_trade_date"] == datetime(2026, 1, 25)


def test_recorded_outside_window_is_still_missing(fake_db, frozen_now):
    ex = datetime(2026, 1, 10)
    # A DIVIDEND 60 days later is NOT this ex-date's payout (outside +/-21d).
    recorded = datetime(2026, 3, 11)
    assert abs((recorded - ex).days) > _DIVIDEND_MATCH_WINDOW_DAYS
    fake_db["holdings"].seed(_hold(qty="700"))
    fake_db["dividend_announcements"].seed(_ann(ex, "4.0"))
    fake_db["transactions"].seed(_div_txn(recorded, "4.0"))

    row = _row(compute_dividend_drift())

    assert row["missing_count"] == 1
    assert row["announcements"][0]["status"] == "missing_receipt"


def test_pre_ex_date_dividend_does_not_match(fake_db, frozen_now):
    # #80 L5: a DIVIDEND dated well BEFORE the ex-date belongs to an earlier
    # announcement — a payout cannot settle before its own ex-date. The old
    # symmetric abs(...)<=21 window WOULD have matched this (18 days before);
    # the directional window must reject it, so the ex-date stays missing.
    ex = datetime(2026, 1, 10)
    recorded = datetime(2025, 12, 23)  # 18 days BEFORE ex → prior payout
    assert 0 < (ex - recorded).days <= _DIVIDEND_MATCH_WINDOW_DAYS
    fake_db["holdings"].seed(_hold(qty="700"))
    fake_db["dividend_announcements"].seed(_ann(ex, "4.0"))
    fake_db["transactions"].seed(_div_txn(recorded, "4.0"))

    row = _row(compute_dividend_drift())

    assert row["missing_count"] == 1
    assert row["announcements"][0]["status"] == "missing_receipt"


def test_small_backdate_tolerance_still_matches(fake_db, frozen_now):
    # #80 L5: a 1-day pre-ex-date txn is data-entry slack, within the small
    # backdate tolerance, and should still match.
    ex = datetime(2026, 1, 10)
    recorded = datetime(2026, 1, 9)  # 1 day before ex → within tolerance
    fake_db["holdings"].seed(_hold(qty="700"))
    fake_db["dividend_announcements"].seed(_ann(ex, "4.0"))
    fake_db["transactions"].seed(_div_txn(recorded, "4.0"))

    row = _row(compute_dividend_drift())

    assert row["missing_count"] == 0
    assert row["announcements"][0]["status"] == "matched"


def test_future_ex_date_is_pending(fake_db, frozen_now):
    ex = datetime(2026, 9, 1)  # after NOW
    fake_db["holdings"].seed(_hold(qty="700"))
    fake_db["dividend_announcements"].seed(_ann(ex, "4.0"))

    row = _row(compute_dividend_drift())

    assert row["missing_count"] == 0
    assert row["announcements"][0]["status"] == "pending"


def test_within_settle_margin_is_pending(fake_db, frozen_now):
    # Ex-date passed but still within the settle margin -> too soon to expect
    # the credit -> pending, not missing.
    ex = datetime(2026, 5, 25)  # 7 days before NOW, < settle margin (21d)
    assert 0 < (NOW - ex).days < _DIVIDEND_SETTLE_MARGIN_DAYS
    fake_db["holdings"].seed(_hold(qty="700"))
    fake_db["dividend_announcements"].seed(_ann(ex, "4.0"))

    row = _row(compute_dividend_drift())

    assert row["missing_count"] == 0
    assert row["announcements"][0]["status"] == "pending"


def test_not_held_across_ex_date_is_pending_not_missing(fake_db, frozen_now):
    # Bought AFTER the ex-date -> no receipt expected -> pending (informational),
    # never a missing_receipt nudge.
    ex = datetime(2026, 1, 10)
    fake_db["holdings"].seed(_hold(qty="700", first=datetime(2026, 3, 1)))
    fake_db["dividend_announcements"].seed(_ann(ex, "4.0"))

    row = _row(compute_dividend_drift())

    assert row["missing_count"] == 0
    assert row["announcements"][0]["status"] == "pending"


def test_news_corroboration_flag(fake_db, frozen_now):
    ex = datetime(2026, 1, 10)
    fake_db["holdings"].seed(_hold(qty="700"))
    fake_db["dividend_announcements"].seed(_ann(ex, "4.0"))
    # A classified corporate_action article entity-tagged to this ISIN, recent.
    fake_db["news_articles"].seed(
        {
            "entities_isins": [ISIN],
            "classified": True,
            "themes": ["corporate_action", "earnings"],
            "fetched_at": datetime(2026, 5, 20),
        }
    )

    row = _row(compute_dividend_drift())
    assert row["has_corporate_action_news"] is True


def test_news_corroboration_false_when_no_corporate_action(fake_db, frozen_now):
    ex = datetime(2026, 1, 10)
    fake_db["holdings"].seed(_hold(qty="700"))
    fake_db["dividend_announcements"].seed(_ann(ex, "4.0"))
    # Article exists but NOT corporate_action themed -> no corroboration.
    fake_db["news_articles"].seed(
        {
            "entities_isins": [ISIN],
            "classified": True,
            "themes": ["earnings"],
            "fetched_at": datetime(2026, 5, 20),
        }
    )

    row = _row(compute_dividend_drift())
    assert row["has_corporate_action_news"] is False


def test_multiple_announcements_mixed_statuses(fake_db, frozen_now):
    fake_db["holdings"].seed(_hold(qty="700"))
    fake_db["dividend_announcements"].seed(
        _ann(datetime(2026, 1, 10), "4.0"),  # missing (past, held, no txn)
        _ann(datetime(2025, 11, 7), "4.0"),  # missing
        _ann(datetime(2026, 9, 1), "4.0"),   # pending (future)
    )
    # Record the payout for the Jan ex-date only.
    fake_db["transactions"].seed(_div_txn(datetime(2026, 1, 20), "4.0"))

    row = _row(compute_dividend_drift())

    statuses = sorted(a["status"] for a in row["announcements"])
    assert statuses == ["matched", "missing_receipt", "pending"]
    assert row["missing_count"] == 1


def test_booked_dividends_surfaced(fake_db, frozen_now):
    fake_db["holdings"].seed(_hold(qty="700", booked="2800.00"))
    fake_db["dividend_announcements"].seed(_ann(datetime(2026, 1, 10), "4.0"))

    row = _row(compute_dividend_drift())
    assert row["booked_dividends"] == Decimal("2800.00")


def test_name_with_no_announcements_still_returned(fake_db, frozen_now):
    fake_db["holdings"].seed(_hold(qty="700"))
    # no announcements seeded

    row = _row(compute_dividend_drift())
    assert row["announcements"] == []


def test_zero_quantity_holding_excluded(fake_db, frozen_now):
    """#74 U3-b: a fully-exited-but-not-soft-deleted position (qty 0) must NOT
    appear in the drift matrix, so it can't fire a spurious missing-receipt
    nudge on a stock we no longer hold."""
    fake_db["holdings"].seed(_hold(qty="0"))
    fake_db["dividend_announcements"].seed(_ann(datetime(2026, 1, 10), "4.0"))

    drift = compute_dividend_drift()
    assert [r for r in drift if r["isin"] == ISIN] == []


def test_refresh_dividends_for_preserves_window_on_fetch_failure(fake_db, monkeypatch):
    """#74 U3-a: a transient yfinance failure (fetch returns None) must NOT wipe
    the recent announcement window — otherwise a genuinely-missed dividend stops
    being flagged. A successful empty fetch ([]) still replaces the window."""
    from app.services import fundamentals_service as fs

    # Seed an existing recent announcement.
    fake_db["dividend_announcements"].seed(_ann(datetime(2026, 1, 10), "4.0"))
    assert fake_db["dividend_announcements"].count_documents({"isin": ISIN}) == 1

    # Simulate a transient fetch failure.
    monkeypatch.setattr(fs, "fetch_dividends_yfinance", lambda *a, **k: None)
    res = fs.refresh_dividends_for(ISIN, "BALKRISIND")

    assert res.get("fetch_failed") is True
    assert res["window_deleted"] == 0
    # The pre-existing announcement is preserved (window NOT wiped).
    assert fake_db["dividend_announcements"].count_documents({"isin": ISIN}) == 1
