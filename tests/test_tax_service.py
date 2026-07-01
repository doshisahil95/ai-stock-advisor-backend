"""Tests for the capital-gains service (F11 / #39).

Hermetic: uses the #33 fake_db fixture (in-memory transactions/holdings/instruments)
and the tx() factory. No Atlas, no network. Run via `uv run python -m pytest`.
"""

from datetime import datetime
from decimal import Decimal

import pytest

from app.services import tax_service
from app.services.tax_service import (
    FyParseError,
    _add_months,
    _classify,
    parse_fy,
)
from tests._fakes import tx

from datetime import date


# ── FY parsing ────────────────────────────────────────────────────────────────
def test_parse_fy_valid():
    start, fy_start, fy_end = parse_fy("2025-26")
    assert start == 2025
    assert fy_start == date(2025, 4, 1)
    assert fy_end == date(2026, 3, 31)


@pytest.mark.parametrize(
    "bad", ["2025-27", "2025-2026", "25-26", "2025_26", "abcd-ef", ""]
)
def test_parse_fy_rejects_bad(bad):
    with pytest.raises(FyParseError):
        parse_fy(bad)


def test_parse_fy_century_rollover():
    start, fy_start, fy_end = parse_fy("2099-00")
    assert start == 2099
    assert fy_end == date(2100, 3, 31)


# ── holding-period classification (strict > 12 calendar months) ─────────────────
def test_add_months_clamps_day():
    assert _add_months(date(2024, 2, 29), 12) == date(2025, 2, 28)


def test_exactly_12_months_is_stcg():
    assert _classify(date(2023, 6, 15), date(2024, 6, 15)) == "STCG"


def test_one_day_past_12_months_is_ltcg():
    assert _classify(date(2023, 6, 15), date(2024, 6, 16)) == "LTCG"


# ── end-to-end capital-gains over the ledger ────────────────────────────────────
def test_short_term_gain(fake_db):
    fake_db["transactions"].seed(
        tx("BUY", 100, 10, trade_date=datetime(2024, 5, 1)),
        tx("SELL", 100, 15, trade_date=datetime(2024, 9, 1)),
    )
    r = tax_service.compute_capital_gains("2024-25")
    assert len(r["lots"]) == 1
    lot = r["lots"][0]
    assert lot["gain_type"] == "STCG"
    assert lot["gain"] == Decimal("500.00")
    assert lot["buy_cost"] == Decimal("1000.00")
    assert lot["sell_proceeds"] == Decimal("1500.00")
    assert r["summary"]["stcg"]["realized_gain"] == Decimal("500.00")
    assert r["summary"]["ltcg"]["lot_count"] == 0
    assert r["summary"]["total"]["realized_gain"] == Decimal("500.00")


def test_long_term_gain(fake_db):
    fake_db["transactions"].seed(
        tx("BUY", 100, 10, trade_date=datetime(2023, 1, 1)),
        tx("SELL", 100, 20, trade_date=datetime(2024, 6, 1)),
    )
    r = tax_service.compute_capital_gains("2024-25")
    assert len(r["lots"]) == 1
    assert r["lots"][0]["gain_type"] == "LTCG"
    assert r["summary"]["ltcg"]["realized_gain"] == Decimal("1000.00")
    assert r["summary"]["stcg"]["lot_count"] == 0


def test_fees_normalize_into_cost_and_proceeds(fake_db):
    fake_db["transactions"].seed(
        tx("BUY", 100, 10, fees=50, trade_date=datetime(2024, 5, 1)),
        tx("SELL", 100, 20, fees=100, trade_date=datetime(2024, 9, 1)),
    )
    r = tax_service.compute_capital_gains("2024-25")
    lot = r["lots"][0]
    assert lot["buy_cost"] == Decimal("1050.00")
    assert lot["sell_proceeds"] == Decimal("1900.00")
    assert lot["gain"] == Decimal("850.00")


def test_fy_boundary_inclusive_edges(fake_db):
    # SELL on the first and last IST day of FY 2024-25 both count.
    fake_db["transactions"].seed(
        tx("BUY", 10, 10, trade_date=datetime(2023, 1, 1), _id=None),
        tx("SELL", 10, 12, trade_date=datetime(2024, 4, 1)),
        tx("BUY", 10, 10, trade_date=datetime(2023, 1, 2)),
        tx("SELL", 10, 12, trade_date=datetime(2025, 3, 31)),
    )
    r = tax_service.compute_capital_gains("2024-25")
    assert len(r["lots"]) == 2


def test_fy_boundary_excludes_other_years(fake_db):
    fake_db["transactions"].seed(
        tx("BUY", 10, 10, trade_date=datetime(2023, 1, 1)),
        tx("SELL", 10, 12, trade_date=datetime(2023, 8, 1)),  # FY 2023-24, not 2024-25
    )
    r = tax_service.compute_capital_gains("2024-25")
    assert r["lots"] == []
    assert r["summary"]["total"]["lot_count"] == 0


def test_single_sell_spans_two_buy_lots_splits_rows(fake_db):
    # 60 sh bought long ago (LTCG) + 40 sh bought recently (STCG), sold together.
    fake_db["transactions"].seed(
        tx("BUY", 60, 10, trade_date=datetime(2023, 1, 1)),
        tx("BUY", 40, 10, trade_date=datetime(2024, 6, 1)),
        tx("SELL", 100, 20, trade_date=datetime(2024, 9, 1)),
    )
    r = tax_service.compute_capital_gains("2024-25")
    assert len(r["lots"]) == 2
    assert r["summary"]["ltcg"]["lot_count"] == 1
    assert r["summary"]["stcg"]["lot_count"] == 1
    assert r["summary"]["ltcg"]["realized_gain"] == Decimal("600.00")  # 60 * (20-10)
    assert r["summary"]["stcg"]["realized_gain"] == Decimal("400.00")  # 40 * (20-10)
    assert r["summary"]["total"]["realized_gain"] == Decimal("1000.00")


def test_partial_sell_single_row(fake_db):
    fake_db["transactions"].seed(
        tx("BUY", 100, 10, trade_date=datetime(2024, 5, 1)),
        tx("SELL", 40, 15, trade_date=datetime(2024, 9, 1)),
    )
    r = tax_service.compute_capital_gains("2024-25")
    assert len(r["lots"]) == 1
    assert r["lots"][0]["quantity"] == Decimal("40")
    assert r["lots"][0]["gain"] == Decimal("200.00")


def test_demerger_cost_basis_is_read_from_ledger_not_double_counted(fake_db):
    # A manual_demerger receipt is a BUY carrying the apportioned (49(2C)) cost.
    # Capital gains must use THAT cost, with no cost_basis_adjustments re-application.
    fake_db["transactions"].seed(
        {
            **tx("BUY", 100, 25, trade_date=datetime(2024, 5, 1)),
            "source": "manual_demerger",
        },
        tx("SELL", 100, 40, trade_date=datetime(2024, 9, 1)),
    )
    r = tax_service.compute_capital_gains("2024-25")
    lot = r["lots"][0]
    assert lot["buy_cost"] == Decimal("2500.00")
    assert lot["sell_proceeds"] == Decimal("4000.00")
    assert lot["gain"] == Decimal("1500.00")


def test_no_transactions_returns_empty(fake_db):
    r = tax_service.compute_capital_gains("2024-25")
    assert r["fy"] == "2024-25"
    assert r["fy_start"] == "2024-04-01"
    assert r["fy_end"] == "2025-03-31"
    assert r["lots"] == []
    assert r["summary"]["total"] == {
        "realized_gain": Decimal("0.00"),
        "proceeds": Decimal("0.00"),
        "cost": Decimal("0.00"),
        "lot_count": 0,
    }


def test_default_fy_used_when_omitted(fake_db):
    r = tax_service.compute_capital_gains()
    assert r["fy"] == tax_service.current_fy()
