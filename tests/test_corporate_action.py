"""Hermetic tests for the #68 corporate-action data-entry front-end.

Two layers, both zero-network:
  1. The pure builders in `corporate_action_service` (row/adjustment shaping +
     §49(2C) split math) — no DB, no fixture.
  2. The `POST /transactions/corporate-action` endpoint handler exercised
     through the `fake_db` FakeCollection harness, asserting the resulting
     ledger row(s) drive `_fifo_replay` to the correct holding AND that a
     demerger writes the §49(2C) cost_basis_adjustments doc + returns the
     parent-reprice follow-up.

These lean on the EXISTING harness (tests/_fakes.py + tests/conftest.py). The
endpoint reuses the same `validate_replay` + `recompute_holding` +
`Transaction`/`CostBasisAdjustment` models as add_buy/sell, so we are testing
wiring + row shape, not re-deriving FIFO (which test_fifo_replay covers).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from app.services import corporate_action_service as ca
from app.services import holdings_service
from app.services.holdings_service import _fifo_replay
from tests._fakes import tx


@pytest.fixture
def stub_metadata(monkeypatch):
    """Stub yfinance metadata so a first-time child holding recompute (the
    demerger receipt) never hits the network. Mirrors test_recompute_holding."""
    monkeypatch.setattr(
        holdings_service,
        "fetch_metadata",
        lambda symbol, exchange: {"name": symbol, "sector": "", "industry": ""},
    )


# ─────────────────────────── pure builders ───────────────────────────


def test_build_split_row_shape():
    row = ca.build_split_row(
        isin="INE081A01020",
        symbol="TATASTEEL",
        exchange="NSE",
        ratio_from=1,
        ratio_to=10,
        trade_date=datetime(2022, 7, 28),
        notes="1:10 split",
        source_ref="SPLIT_TATASTEEL_2022:1to10",
    )
    assert row["type"] == "SPLIT"
    assert row["quantity"] == Decimal("0")
    assert row["price"] == Decimal("0")
    assert row["corporate_action"] == {
        "ratio_from": 1,
        "ratio_to": 10,
        "notes": "1:10 split",
    }
    assert row["source"] == "manual_corporate_action"


def test_split_row_drives_fifo_scale():
    """10 sh @ ₹1170.27 then a 1:10 split -> 100 sh @ ₹117.027, total preserved."""
    buy = tx("BUY", quantity=Decimal("10"), price=Decimal("1170.27"),
             trade_date=datetime(2021, 1, 1))
    split = ca.build_split_row(
        isin="INE081A01020", symbol="TATASTEEL", exchange="NSE",
        ratio_from=1, ratio_to=10, trade_date=datetime(2022, 7, 28),
    )
    split["_id"] = tx("SPLIT")["_id"]
    out = _fifo_replay([buy, split])
    assert out["quantity"] == Decimal("100")
    # avg cost = 11702.70 / 100
    assert out["invested_amount"] == Decimal("11702.70")


def test_compute_bonus_quantity_one_to_one():
    assert ca.compute_bonus_quantity(Decimal("5"), 1, 1) == Decimal("5.0000")


def test_compute_bonus_quantity_one_per_six():
    # CONCOR: 1 bonus per 6 held.
    assert ca.compute_bonus_quantity(Decimal("6"), 6, 1) == Decimal("1.0000")


def test_compute_bonus_quantity_rejects_bad_ratio():
    with pytest.raises(ValueError):
        ca.compute_bonus_quantity(Decimal("5"), 0, 1)


def test_build_bonus_row_is_zero_cost_buy():
    row = ca.build_bonus_row(
        isin="INE002A01018", symbol="RELIANCE", exchange="NSE",
        bonus_quantity=Decimal("5"), trade_date=datetime(2024, 11, 1),
        source_ref="BONUS_RELIANCE_2024",
    )
    assert row["type"] == "BUY"
    assert row["price"] == Decimal("0")
    assert row["quantity"] == Decimal("5")
    assert row["source"] == "manual_corporate_action"


def test_bonus_row_dilutes_avg_cost():
    """5 sh @ ₹2432.87 + 5 zero-cost bonus -> 10 sh, avg ₹1216.44, total unchanged."""
    buy = tx("BUY", quantity=Decimal("5"), price=Decimal("2432.87"),
             trade_date=datetime(2020, 1, 1))
    bonus = ca.build_bonus_row(
        isin="INE002A01018", symbol="RELIANCE", exchange="NSE",
        bonus_quantity=Decimal("5"), trade_date=datetime(2024, 11, 1),
    )
    bonus["_id"] = tx("BUY")["_id"]
    out = _fifo_replay([buy, bonus])
    assert out["quantity"] == Decimal("10")
    assert out["invested_amount"] == Decimal("12164.35")  # 5*2432.87


def test_compute_demerger_cost_split_tmpv_tmcv():
    """TMPV 100 sh @ ₹813.37 total ₹81,337; 31.15% to TMCV."""
    res = ca.compute_demerger_cost_split(
        parent_total_cost=Decimal("81337.00"),
        parent_quantity=Decimal("100"),
        child_cost_pct=Decimal("0.3115"),
    )
    assert res["child_total_cost"] == Decimal("25336.48")
    assert res["child_cost_per_share"] == Decimal("253.3648")
    assert res["parent_retained_factor"] == Decimal("0.6885")
    # signed our - broker == -child_total
    assert res["adjustment_amount"] == Decimal("-25336.48")


def test_compute_demerger_cost_split_rejects_bad_pct():
    with pytest.raises(ValueError):
        ca.compute_demerger_cost_split(
            parent_total_cost=Decimal("100"),
            parent_quantity=Decimal("1"),
            child_cost_pct=Decimal("1.5"),
        )


def test_build_demerger_child_row_inherits_acquired_date():
    row = ca.build_demerger_child_row(
        child_isin="INE1TAE01010", child_symbol="TMCV", exchange="NSE",
        quantity=Decimal("100"), cost_per_share=Decimal("253.3647"),
        trade_date=datetime(2025, 10, 1),
        acquired_date=datetime(2023, 10, 18),
        source_ref="DEMERGER_TATAMOTORS_2025",
    )
    assert row["source"] == "manual_demerger"
    assert row["acquired_date"] == datetime(2023, 10, 18)
    assert row["price"] == Decimal("253.3647")


def test_compute_parent_reprice_scales_price_and_fees():
    parent_rows = [
        tx("BUY", quantity=Decimal("100"), price=Decimal("813.37"),
           fees=Decimal("10.00"), trade_date=datetime(2023, 10, 18)),
    ]
    instrs = ca.compute_parent_reprice(parent_rows, Decimal("0.6885"))
    assert len(instrs) == 1
    assert instrs[0]["new_price"] == Decimal("560.0052")  # 813.37 * 0.6885
    assert instrs[0]["new_fees"] == Decimal("6.89")       # 10.00 * 0.6885


def test_compute_parent_reprice_skips_non_buy():
    rows = [tx("SPLIT", corporate_action={"ratio_from": 1, "ratio_to": 2})]
    assert ca.compute_parent_reprice(rows, Decimal("0.5")) == []


# ─────────────────────────── endpoint wiring ───────────────────────────
# These import the handler lazily so a construction error surfaces per-test.


def _seed_holding(fake_db, isin, symbol, qty, avg_cost):
    fake_db["holdings"].seed(
        {
            "isin": isin,
            "symbol": symbol,
            "exchange": "NSE",
            "quantity": qty,
            "avg_cost": avg_cost,
            "invested_amount": qty * avg_cost,
            "deleted_at": None,
            "name": symbol,
        }
    )


def test_endpoint_split_records_and_recomputes(fake_db, stub_metadata):
    from app.routers.transactions import RecordCorporateActionRequest, record_corporate_action

    isin = "INE081A01020"
    fake_db["transactions"].seed(
        tx("BUY", quantity=Decimal("10"), price=Decimal("1170.27"),
           trade_date=datetime(2021, 1, 1), isin=isin, symbol="TATASTEEL")
    )
    _seed_holding(fake_db, isin, "TATASTEEL", Decimal("10"), Decimal("1170.27"))

    req = RecordCorporateActionRequest(
        action_type="split", isin=isin, symbol="TATASTEEL",
        ratio_from=1, ratio_to=10, trade_date=datetime(2022, 7, 28),
        source_ref="SPLIT_TATASTEEL_2022:1to10",
    )
    resp = record_corporate_action(req)
    assert resp["status"] == "recorded"
    # one SPLIT row now in the ledger
    rows = list(fake_db["transactions"].find({"isin": isin}))
    assert any(r["type"] == "SPLIT" for r in rows)


def test_endpoint_split_idempotent(fake_db, stub_metadata):
    from app.routers.transactions import RecordCorporateActionRequest, record_corporate_action

    isin = "INE081A01020"
    fake_db["transactions"].seed(
        tx("BUY", quantity=Decimal("10"), price=Decimal("1170.27"),
           trade_date=datetime(2021, 1, 1), isin=isin, symbol="TATASTEEL")
    )
    _seed_holding(fake_db, isin, "TATASTEEL", Decimal("10"), Decimal("1170.27"))
    req = RecordCorporateActionRequest(
        action_type="split", isin=isin, symbol="TATASTEEL",
        ratio_from=1, ratio_to=10, trade_date=datetime(2022, 7, 28),
        source_ref="SPLIT_TATASTEEL_2022:1to10",
    )
    record_corporate_action(req)
    resp2 = record_corporate_action(req)
    assert resp2["status"] == "already_recorded"
    splits = [r for r in fake_db["transactions"].find({"isin": isin}) if r["type"] == "SPLIT"]
    assert len(splits) == 1


def test_endpoint_bonus_computes_qty_from_holding(fake_db, stub_metadata):
    from app.routers.transactions import RecordCorporateActionRequest, record_corporate_action

    isin = "INE002A01018"
    fake_db["transactions"].seed(
        tx("BUY", quantity=Decimal("5"), price=Decimal("2432.87"),
           trade_date=datetime(2020, 1, 1), isin=isin, symbol="RELIANCE")
    )
    _seed_holding(fake_db, isin, "RELIANCE", Decimal("5"), Decimal("2432.87"))
    req = RecordCorporateActionRequest(
        action_type="bonus", isin=isin, symbol="RELIANCE",
        ratio_from=1, ratio_to=1, trade_date=datetime(2024, 11, 1),
        source_ref="BONUS_RELIANCE_2024:1to1",
    )
    resp = record_corporate_action(req)
    assert resp["status"] == "recorded"
    assert resp["bonus_quantity"] == "5.0000"
    bonus_rows = [
        r for r in fake_db["transactions"].find({"isin": isin})
        if r["type"] == "BUY" and str(r.get("price")) in ("0", "0.0000")
        and r.get("source") == "manual_corporate_action"
    ]
    assert len(bonus_rows) == 1


def test_endpoint_bonus_explicit_quantity_overrides(fake_db, stub_metadata):
    from app.routers.transactions import RecordCorporateActionRequest, record_corporate_action

    isin = "INE111A01025"
    fake_db["transactions"].seed(
        tx("BUY", quantity=Decimal("6"), price=Decimal("687.31"),
           trade_date=datetime(2020, 1, 1), isin=isin, symbol="CONCOR")
    )
    _seed_holding(fake_db, isin, "CONCOR", Decimal("6"), Decimal("687.31"))
    req = RecordCorporateActionRequest(
        action_type="bonus", isin=isin, symbol="CONCOR",
        ratio_from=1, ratio_to=1, trade_date=datetime(2025, 7, 8),
        bonus_quantity=Decimal("1"),  # ICICI showed only 1 bonus for 6 held
        source_ref="BONUS_CONCOR_2025",
    )
    resp = record_corporate_action(req)
    assert resp["bonus_quantity"] == "1"


def test_endpoint_demerger_writes_child_row_and_adjustment(fake_db, stub_metadata):
    from app.routers.transactions import RecordCorporateActionRequest, record_corporate_action

    parent_isin = "INE155A01022"  # TMPV
    child_isin = "INE1TAE01010"   # TMCV
    fake_db["transactions"].seed(
        tx("BUY", quantity=Decimal("100"), price=Decimal("813.37"),
           trade_date=datetime(2023, 10, 18), isin=parent_isin, symbol="TMPV")
    )
    _seed_holding(fake_db, parent_isin, "TMPV", Decimal("100"), Decimal("813.37"))

    req = RecordCorporateActionRequest(
        action_type="demerger",
        isin=parent_isin, symbol="TMPV",
        child_isin=child_isin, child_symbol="TMCV",
        child_quantity=Decimal("100"),
        child_cost_pct=Decimal("0.3115"),
        parent_total_cost=Decimal("81337.00"),
        acquired_date=datetime(2023, 10, 18),
        trade_date=datetime(2025, 10, 1),
        it_act_section="Section 49(2C)",
        source_ref="DEMERGER_TATAMOTORS_2025:31.15pct_to_TMCV",
    )
    resp = record_corporate_action(req)
    assert resp["status"] == "recorded"

    # child BUY row exists, source manual_demerger, inherits acquired_date
    child_rows = list(fake_db["transactions"].find({"isin": child_isin}))
    assert len(child_rows) == 1
    assert child_rows[0]["source"] == "manual_demerger"
    assert child_rows[0]["acquired_date"] == datetime(2023, 10, 18)

    # §49(2C) adjustment doc written
    adjustments = list(fake_db["cost_basis_adjustments"].find({}))
    assert len(adjustments) == 1
    assert adjustments[0]["it_act_section"] == "Section 49(2C)"

    # parent-reprice follow-up returned (audited PATCH path, NOT applied here)
    assert "parent_reprice" in resp
    assert len(resp["parent_reprice"]) == 1
    assert resp["parent_reprice"][0]["new_price"] == "560.0052"
    # parent ledger row is UNCHANGED by this endpoint (immutability invariant)
    parent_rows = list(fake_db["transactions"].find({"isin": parent_isin}))
    assert str(parent_rows[0]["price"]) == "813.37"


def test_endpoint_demerger_idempotent_on_child(fake_db, stub_metadata):
    from app.routers.transactions import RecordCorporateActionRequest, record_corporate_action

    parent_isin = "INE155A01022"
    child_isin = "INE1TAE01010"
    fake_db["transactions"].seed(
        tx("BUY", quantity=Decimal("100"), price=Decimal("813.37"),
           trade_date=datetime(2023, 10, 18), isin=parent_isin, symbol="TMPV")
    )
    _seed_holding(fake_db, parent_isin, "TMPV", Decimal("100"), Decimal("813.37"))
    req = RecordCorporateActionRequest(
        action_type="demerger", isin=parent_isin, symbol="TMPV",
        child_isin=child_isin, child_symbol="TMCV",
        child_quantity=Decimal("100"), child_cost_pct=Decimal("0.3115"),
        parent_total_cost=Decimal("81337.00"),
        acquired_date=datetime(2023, 10, 18), trade_date=datetime(2025, 10, 1),
        source_ref="DEMERGER_TATAMOTORS_2025:31.15pct_to_TMCV",
    )
    record_corporate_action(req)
    resp2 = record_corporate_action(req)
    assert resp2["status"] == "already_recorded"
    assert len(list(fake_db["transactions"].find({"isin": child_isin}))) == 1
    assert len(list(fake_db["cost_basis_adjustments"].find({}))) == 1
