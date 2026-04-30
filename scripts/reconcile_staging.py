"""Reconciliation report for transactions_staging.

Generates totals, per-FY breakdowns, and per-stock current quantity (FIFO net)
so you can cross-check against ICICI's reports BEFORE promoting to live.

Usage:
    PYTHONPATH=. uv run python scripts/reconcile_staging.py
"""

from __future__ import annotations

import sys
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Iterator

from bson import Decimal128

from app.db.client import Collections

# ── Helpers ──────────────────────────────────────────────────────────────────


def _to_dec(v) -> Decimal:
    if isinstance(v, Decimal128):
        return v.to_decimal()
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def _fy_label(d: datetime) -> str:
    """Indian FY: April 1 to March 31. So 2024-04-15 → 'FY 2024-25'."""
    if d.month >= 4:
        start = d.year
    else:
        start = d.year - 1
    return f"FY {start}-{str(start + 1)[-2:]}"


def _money(d: Decimal) -> str:
    """₹X,XX,XXX.XX (Indian comma style: lakh)."""
    s = f"{d:,.2f}"
    # Convert US-style 1,234,567.89 to Indian-style 12,34,567.89
    if "." in s:
        int_part, dec_part = s.split(".")
    else:
        int_part, dec_part = s, "00"
    int_part = int_part.replace(",", "")
    neg = int_part.startswith("-")
    if neg:
        int_part = int_part[1:]
    if len(int_part) > 3:
        last3 = int_part[-3:]
        rest = int_part[:-3]
        rest_groups = []
        while len(rest) > 2:
            rest_groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            rest_groups.insert(0, rest)
        int_part = ",".join(rest_groups) + "," + last3
    sign = "-" if neg else ""
    return f"₹{sign}{int_part}.{dec_part}"


@dataclass
class FifoLot:
    qty: Decimal
    price: Decimal
    fees: Decimal
    trade_date: datetime


@dataclass
class StockState:
    symbol: str
    isin: str
    lots: deque[FifoLot] = field(default_factory=deque)
    realized_pnl: Decimal = Decimal("0")
    first_buy: datetime | None = None
    last_traded: datetime | None = None

    @property
    def current_qty(self) -> Decimal:
        return sum((lot.qty for lot in self.lots), Decimal("0"))

    @property
    def invested(self) -> Decimal:
        return sum((lot.qty * lot.price + lot.fees for lot in self.lots), Decimal("0"))

    @property
    def avg_cost(self) -> Decimal:
        q = self.current_qty
        return (self.invested / q) if q > 0 else Decimal("0")


def _fifo_apply(state: StockState, txn: dict) -> None:
    qty = _to_dec(txn["quantity"])
    price = _to_dec(txn["price"])
    fees = _to_dec(txn.get("total_fees", 0))
    trade_date = txn["trade_date"]
    state.last_traded = trade_date

    if txn["type"] == "BUY":
        if state.first_buy is None:
            state.first_buy = trade_date
        state.lots.append(
            FifoLot(qty=qty, price=price, fees=fees, trade_date=trade_date)
        )

    elif txn["type"] == "SELL":
        proceeds_per_share = price - (fees / qty if qty > 0 else Decimal("0"))
        remaining = qty
        while remaining > 0 and state.lots:
            lot = state.lots[0]
            take = min(remaining, lot.qty)
            cost_per_share = lot.price + (
                lot.fees / lot.qty if lot.qty > 0 else Decimal("0")
            )
            state.realized_pnl += take * (proceeds_per_share - cost_per_share)
            if lot.qty > 0:
                lot.fees -= lot.fees * take / lot.qty
            lot.qty -= take
            remaining -= take
            if lot.qty == 0:
                state.lots.popleft()


def _iter_staging() -> Iterator[dict]:
    return Collections.transactions_staging().find({}).sort("trade_date", 1)


# ── Report ───────────────────────────────────────────────────────────────────


def main() -> int:
    staging = Collections.transactions_staging()
    total_rows = staging.estimated_document_count()
    if total_rows == 0:
        print("⚠️  transactions_staging is empty. Run import_orderbooks.py first.")
        return 1

    print("=" * 70)
    print("  ICICI Order Book Import — Reconciliation Report")
    print("=" * 70)
    print()

    # ── Aggregate stats ─────────────────────────────────────────────────────
    buy_count = sell_count = 0
    total_invested = Decimal("0")  # sum of buy values + fees
    total_realized = Decimal("0")  # sum of sell proceeds (gross)
    total_fees = Decimal("0")
    total_realized_pnl = Decimal("0")  # FIFO P&L

    fy_stats: dict[str, dict] = defaultdict(
        lambda: {
            "buys": 0,
            "sells": 0,
            "invested": Decimal("0"),
            "realized": Decimal("0"),
            "fees": Decimal("0"),
            "realized_pnl": Decimal("0"),
        }
    )

    states: dict[str, StockState] = {}

    for txn in _iter_staging():
        sym = txn["symbol"]
        isin = txn.get("isin", "?")
        state = states.setdefault(sym, StockState(symbol=sym, isin=isin))

        prev_pnl = state.realized_pnl
        _fifo_apply(state, txn)
        delta_pnl = state.realized_pnl - prev_pnl

        qty = _to_dec(txn["quantity"])
        price = _to_dec(txn["price"])
        fees = _to_dec(txn.get("total_fees", 0))
        value = qty * price
        fy = _fy_label(txn["trade_date"])

        total_fees += fees
        fy_stats[fy]["fees"] += fees

        if txn["type"] == "BUY":
            buy_count += 1
            total_invested += value + fees
            fy_stats[fy]["buys"] += 1
            fy_stats[fy]["invested"] += value + fees
        elif txn["type"] == "SELL":
            sell_count += 1
            total_realized += value
            total_realized_pnl += delta_pnl
            fy_stats[fy]["sells"] += 1
            fy_stats[fy]["realized"] += value
            fy_stats[fy]["realized_pnl"] += delta_pnl

    # ── Print: Overall ──────────────────────────────────────────────────────
    print("OVERALL TOTALS")
    print("─" * 70)
    print(f"Total BUY transactions:           {buy_count:>10,}")
    print(f"Total SELL transactions:          {sell_count:>10,}")
    print(f"Total invested (BUY+fees):        {_money(total_invested):>20}")
    print(f"Total realized from sells (gross):{_money(total_realized):>20}")
    print(f"Total fees paid:                  {_money(total_fees):>20}")
    print(f"Total realized P&L (FIFO):        {_money(total_realized_pnl):>20}")
    print()

    # ── Print: Per-FY ───────────────────────────────────────────────────────
    print("PER-FY BREAKDOWN")
    print("─" * 70)
    print(
        f"{'FY':<12}{'Buys':>7}{'Sells':>7}  {'Invested':>17}  {'Realized':>17}  {'Fees':>11}  {'Realized P&L':>14}"
    )
    for fy in sorted(fy_stats.keys()):
        s = fy_stats[fy]
        print(
            f"{fy:<12}{s['buys']:>7}{s['sells']:>7}  "
            f"{_money(s['invested']):>17}  {_money(s['realized']):>17}  "
            f"{_money(s['fees']):>11}  {_money(s['realized_pnl']):>14}"
        )
    print()

    # ── Print: Currently held ───────────────────────────────────────────────
    held = [s for s in states.values() if s.current_qty > 0]
    held.sort(key=lambda x: -x.invested)

    print(f"CURRENTLY HELD ({len(held)} stocks)")
    print("─" * 70)
    print(
        f"{'Symbol':<14}{'Qty':>10}  {'Avg Cost':>14}  {'Invested':>17}  {'First Buy':>12}  {'ISIN':<14}"
    )
    total_currently_invested = Decimal("0")
    for s in held:
        first_buy = s.first_buy.strftime("%Y-%m-%d") if s.first_buy else "?"
        print(
            f"{s.symbol:<14}{float(s.current_qty):>10,.0f}  "
            f"{_money(s.avg_cost):>14}  {_money(s.invested):>17}  "
            f"{first_buy:>12}  {s.isin:<14}"
        )
        total_currently_invested += s.invested
    print()
    print(f"Total currently invested:         {_money(total_currently_invested):>20}")
    print()

    # ── Fully exited stocks ────────────────────────────────────────────────
    exited = [s for s in states.values() if s.current_qty == 0]
    if exited:
        print(f"FULLY EXITED ({len(exited)} stocks — no longer held)")
        print("─" * 70)
        for s in sorted(exited, key=lambda x: -x.realized_pnl):
            print(
                f"  {s.symbol:<14}  Realized P&L: {_money(s.realized_pnl):>14}  "
                f"(last traded: {s.last_traded.strftime('%Y-%m-%d') if s.last_traded else '?'})"
            )
        print()

    # ── Next steps ─────────────────────────────────────────────────────────
    print("STAGING SUMMARY")
    print("─" * 70)
    print(f"Rows in transactions_staging:     {total_rows:>10,}")
    print()
    print("NEXT STEPS")
    print("─" * 70)
    print("1. Cross-check OVERALL TOTALS and PER-FY against ICICI:")
    print("   - Reports → Profit & Loss")
    print("   - AnnualGlobalTransactionStatement.pdf")
    print("2. Cross-check CURRENTLY HELD against ICICI Holdings snapshot")
    print("3. If anything looks wrong:")
    print("   - Inspect rows: db.transactions_staging.find({symbol: 'XXX'}) in Atlas")
    print(
        "   - Re-run import: PYTHONPATH=. uv run python scripts/import_orderbooks.py --wipe"
    )
    print("4. When numbers match, promote:")
    print("   PYTHONPATH=. uv run python scripts/promote_staging.py")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
