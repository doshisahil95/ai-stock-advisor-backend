from datetime import datetime
from decimal import Decimal

from app.services.holdings_service import _fifo_replay
from tests._fakes import tx


def test_single_buy():
    r = _fifo_replay([tx("BUY", 100, 10, trade_date=datetime(2024, 1, 1))])
    assert r["quantity"] == Decimal("100")
    assert r["avg_cost"] == Decimal("10")
    assert r["invested_amount"] == Decimal("1000")
    assert r["realized_pnl"] == Decimal("0")
    assert r["first_purchased_at"] == datetime(2024, 1, 1)
    assert r["last_traded_at"] == datetime(2024, 1, 1)


def test_buy_then_partial_sell_realizes_pnl():
    r = _fifo_replay(
        [
            tx("BUY", 100, 10, trade_date=datetime(2024, 1, 1)),
            tx("SELL", 40, 15, trade_date=datetime(2024, 1, 2)),
        ]
    )
    assert r["quantity"] == Decimal("60")
    assert r["invested_amount"] == Decimal("600")
    assert r["avg_cost"] == Decimal("10")
    assert r["realized_pnl"] == Decimal("200")


def test_full_exit_zeroes_position():
    r = _fifo_replay(
        [
            tx("BUY", 100, 10, trade_date=datetime(2024, 1, 1)),
            tx("SELL", 100, 20, trade_date=datetime(2024, 1, 2)),
        ]
    )
    assert r["quantity"] == Decimal("0")
    assert r["invested_amount"] == Decimal("0")
    assert r["avg_cost"] == Decimal("0")
    assert r["realized_pnl"] == Decimal("1000")


def test_buy_fees_fold_into_invested():
    r = _fifo_replay([tx("BUY", 100, 10, fees=50, trade_date=datetime(2024, 1, 1))])
    assert r["invested_amount"] == Decimal("1050")
    assert r["avg_cost"] == Decimal("10.5")


def test_dividend_accrues_without_touching_position():
    r = _fifo_replay(
        [
            tx("BUY", 100, 10, trade_date=datetime(2024, 1, 1)),
            tx("DIVIDEND", 0, 2, trade_date=datetime(2024, 1, 5)),
        ]
    )
    assert r["quantity"] == Decimal("100")
    assert r["invested_amount"] == Decimal("1000")
    assert r["total_dividends_received"] == Decimal("200")


def test_split_scales_qty_and_price():
    r = _fifo_replay(
        [
            tx("BUY", 100, 10, trade_date=datetime(2024, 1, 1)),
            tx(
                "SPLIT",
                trade_date=datetime(2024, 1, 2),
                corporate_action={"ratio_from": 1, "ratio_to": 2},
            ),
        ]
    )
    assert r["quantity"] == Decimal("200")
    assert r["avg_cost"] == Decimal("5")
    assert r["invested_amount"] == Decimal("1000")


def test_bonus_dilutes_cost():
    r = _fifo_replay(
        [
            tx("BUY", 100, 10, trade_date=datetime(2024, 1, 1)),
            tx(
                "BONUS",
                trade_date=datetime(2024, 1, 2),
                corporate_action={"ratio_from": 1, "ratio_to": 1},
            ),
        ]
    )
    assert r["quantity"] == Decimal("200")
    assert r["avg_cost"] == Decimal("5")
    assert r["invested_amount"] == Decimal("1000")
