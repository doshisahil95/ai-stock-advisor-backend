from datetime import datetime
from decimal import Decimal

import app.db.client as db_client
from app.services.holdings_service import preview_sell
from tests._fakes import FakeCollection, tx

ISIN = "INE000A01001"


def _install_txns(monkeypatch, docs):
    fake = FakeCollection().seed(*docs)
    monkeypatch.setattr(
        db_client.Collections, "transactions", staticmethod(lambda: fake), raising=False
    )
    return fake


def test_partial_sell_preview(monkeypatch):
    _install_txns(
        monkeypatch, [tx("BUY", 100, 10, trade_date=datetime(2024, 1, 1), isin=ISIN)]
    )
    r = preview_sell(ISIN, Decimal("40"), Decimal("15"))
    assert r["valid"] is True
    assert r["realized_pnl"] == Decimal("200.00")
    assert r["remaining_qty"] == Decimal("60")
    assert r["fully_exits"] is False


def test_full_exit_preview(monkeypatch):
    _install_txns(
        monkeypatch, [tx("BUY", 100, 10, trade_date=datetime(2024, 1, 1), isin=ISIN)]
    )
    r = preview_sell(ISIN, Decimal("100"), Decimal("20"))
    assert r["valid"] is True
    assert r["fully_exits"] is True
    assert r["realized_pnl"] == Decimal("1000.00")


def test_oversell_rejected(monkeypatch):
    _install_txns(
        monkeypatch, [tx("BUY", 10, 10, trade_date=datetime(2024, 1, 1), isin=ISIN)]
    )
    r = preview_sell(ISIN, Decimal("50"), Decimal("15"))
    assert r["valid"] is False
    assert "Not enough quantity" in r["error"]


def test_nonpositive_qty_rejected(monkeypatch):
    _install_txns(
        monkeypatch, [tx("BUY", 10, 10, trade_date=datetime(2024, 1, 1), isin=ISIN)]
    )
    r = preview_sell(ISIN, Decimal("0"), Decimal("15"))
    assert r["valid"] is False


def test_no_transactions_rejected(monkeypatch):
    _install_txns(monkeypatch, [])
    r = preview_sell(ISIN, Decimal("1"), Decimal("15"))
    assert r["valid"] is False


def test_split_aware_preview(monkeypatch):
    _install_txns(
        monkeypatch,
        [
            tx("BUY", 100, 10, trade_date=datetime(2024, 1, 1), isin=ISIN),
            tx(
                "SPLIT",
                trade_date=datetime(2024, 1, 2),
                isin=ISIN,
                corporate_action={"ratio_from": 1, "ratio_to": 2},
            ),
        ],
    )
    r = preview_sell(ISIN, Decimal("50"), Decimal("8"))
    assert r["valid"] is True
    assert r["realized_pnl"] == Decimal("150.00")
    assert r["remaining_qty"] == Decimal("150")


def test_remaining_invested_includes_residual_fees(monkeypatch):
    """#77 U6-b: remaining_invested must include residual per-lot fees (mirrors
    _fifo_replay invested = Σqty*price + Σfees). BUY 100 @ ₹10 + ₹50 fees;
    sell 40 -> 60 remain; residual fees = 50 * 60/100 = 30, so
    remaining_invested = 600 + 30 = 630 (was 600 pre-fix)."""
    _install_txns(
        monkeypatch,
        [tx("BUY", 100, 10, fees=50, trade_date=datetime(2024, 1, 1), isin=ISIN)],
    )
    r = preview_sell(ISIN, Decimal("40"), Decimal("15"))
    assert r["valid"] is True
    assert r["remaining_qty"] == Decimal("60")
    assert r["remaining_invested"] == Decimal("630.00")
