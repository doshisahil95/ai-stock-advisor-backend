from datetime import datetime

from app.services.holdings_service import validate_replay
from tests._fakes import tx


def test_valid_buy_then_sell():
    ok, reason = validate_replay(
        [
            tx("BUY", 100, 10, trade_date=datetime(2024, 1, 1)),
            tx("SELL", 50, 15, trade_date=datetime(2024, 1, 2)),
        ]
    )
    assert ok is True
    assert reason is None


def test_oversell_rejected():
    ok, reason = validate_replay(
        [
            tx("BUY", 50, 10, trade_date=datetime(2024, 1, 1)),
            tx("SELL", 100, 15, trade_date=datetime(2024, 1, 2)),
        ]
    )
    assert ok is False
    assert "available" in reason


def test_chronology_enforced_not_input_order():
    # SELL is dated earlier than the BUY; replay sorts by trade_date, so the
    # SELL is evaluated first against an empty book -> oversell.
    ok, reason = validate_replay(
        [
            tx("SELL", 50, 15, trade_date=datetime(2024, 1, 2)),
            tx("BUY", 100, 10, trade_date=datetime(2024, 1, 5)),
        ]
    )
    assert ok is False


def test_split_enables_post_split_sell():
    ok, reason = validate_replay(
        [
            tx("BUY", 100, 10, trade_date=datetime(2024, 1, 1)),
            tx(
                "SPLIT",
                trade_date=datetime(2024, 1, 2),
                corporate_action={"ratio_from": 1, "ratio_to": 2},
            ),
            tx("SELL", 150, 8, trade_date=datetime(2024, 1, 3)),
        ]
    )
    assert ok is True
    assert reason is None


def test_deleted_transactions_skipped():
    ok, reason = validate_replay(
        [
            tx("BUY", 100, 10, trade_date=datetime(2024, 1, 1)),
            tx(
                "SELL",
                200,
                15,
                trade_date=datetime(2024, 1, 2),
                deleted_at=datetime(2024, 1, 3),
            ),
        ]
    )
    assert ok is True
