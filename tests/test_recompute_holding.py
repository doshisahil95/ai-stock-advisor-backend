from datetime import datetime
from decimal import Decimal

from app.services import holdings_service
from app.services.holdings_service import recompute_holding
from tests._fakes import oid, tx

ISIN = "INE000A01001"


def _stub_metadata(monkeypatch):
    monkeypatch.setattr(
        holdings_service,
        "fetch_metadata",
        lambda symbol, exchange: {
            "name": "Test Co",
            "sector": "Tech",
            "industry": "SW",
        },
    )


def test_recompute_is_idempotent(fake_db, monkeypatch):
    _stub_metadata(monkeypatch)
    fake_db["transactions"].seed(
        tx("BUY", 100, 10, trade_date=datetime(2024, 1, 1), isin=ISIN, _id=oid()),
        tx("SELL", 40, 15, trade_date=datetime(2024, 1, 2), isin=ISIN, _id=oid()),
    )

    h1 = recompute_holding(ISIN)
    h2 = recompute_holding(ISIN)

    assert h1 is not None and h2 is not None
    assert h2.quantity == Decimal("60")
    assert h2.invested_amount == Decimal("600")
    assert h2.avg_cost == Decimal("10")
    assert h2.realized_pnl == Decimal("200")
    assert h2.deleted_at is None

    # Running twice produces identical aggregates and preserves created_at.
    assert h1.quantity == h2.quantity
    assert h1.invested_amount == h2.invested_amount
    assert h1.realized_pnl == h2.realized_pnl
    assert h1.created_at == h2.created_at

    # Exactly one active holding doc — no parallel/duplicate row on re-run.
    active = [d for d in fake_db["holdings"]._docs if d.get("deleted_at") is None]
    assert len(active) == 1


def test_recompute_full_exit_soft_deletes(fake_db, monkeypatch):
    _stub_metadata(monkeypatch)
    fake_db["transactions"].seed(
        tx("BUY", 100, 10, trade_date=datetime(2024, 1, 1), isin=ISIN, _id=oid()),
        tx("SELL", 100, 20, trade_date=datetime(2024, 1, 2), isin=ISIN, _id=oid()),
    )

    result = recompute_holding(ISIN)

    assert result is None  # fully exited -> soft-deleted, returns None
    active = [d for d in fake_db["holdings"]._docs if d.get("deleted_at") is None]
    assert active == []
