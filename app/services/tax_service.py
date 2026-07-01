"""Capital-gains service (F11 / #39).

Read-only tax view over the Phase-1 transaction ledger: an STCG/LTCG per-lot
breakdown for an Indian financial year (1 Apr -> 31 Mar, IST).

Design invariants (see PROJECT_STATE Section 11/12 + master_todo #39):
  * READ-ONLY on Phase 1. This service never writes. It replays transactions
    through holdings_service._fifo_replay -- the SINGLE FIFO source of truth --
    and reads the per-disposal `_realized_lots` that replay emits. There is NO
    parallel FIFO path here (importing the one FIFO function, not re-implementing).
  * Section 49(2C) demerger cost basis is honored automatically: the apportioned
    cost is already baked into the `manual_demerger` BUY rows in `transactions`
    (e.g. TMCV at 31.15% of the original cost), so replaying the ledger yields the
    tax-correct cost. We do NOT re-apply cost_basis_adjustments amounts here --
    that collection is a pure audit/display surface (cost_basis_service only reads
    and sums it); feeding it into FIFO would double-count.
  * Listed-equity holding period: LTCG when held strictly MORE than 12 calendar
    months; otherwise STCG. holding_period_days is reported for display.

Known limitation (to be filed as a NEW-ITEMS row): Phase-1 FIFO models BONUS by
diluting existing lots in place (keeping their original buy trade_date) and
demerger receipts as manual BUY rows, so the buy_date / cost for bonus & demerger
lots reflect the ledger encoding rather than the strict IT-Act treatment (bonus =
zero cost + holding period from allotment; demerger = inherit original holding
period). #39 is read-only on Phase 1 and does not re-architect FIFO.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from bson import Decimal128

from app.db.client import Collections
from app.services.holdings_service import _fifo_replay

# India has no DST; IST is a fixed offset (mirrors price_service's IST convention).
IST = timezone(timedelta(hours=5, minutes=30))
_TWO_DP = Decimal("0.01")


class FyParseError(ValueError):
    """Raised when the fy string is malformed or not a consecutive-year FY."""


def parse_fy(fy: str) -> tuple[int, date, date]:
    """Parse 'YYYY-YY' -> (start_year, fy_start_date, fy_end_date), IST calendar.

    e.g. '2025-26' -> (2025, date(2025, 4, 1), date(2026, 3, 31)).
    Rejects a non-consecutive pair ('2025-27') and any non-YYYY-YY shape.
    """
    if not isinstance(fy, str) or not re.fullmatch(r"\d{4}-\d{2}", fy):
        raise FyParseError(f"fy must look like YYYY-YY (e.g. 2025-26); got {fy!r}")
    start_year = int(fy[:4])
    end_yy = int(fy[5:])
    if (start_year + 1) % 100 != end_yy:
        raise FyParseError(
            f"fy {fy!r} is not a consecutive financial year "
            f"(expected {start_year}-{(start_year + 1) % 100:02d})"
        )
    return start_year, date(start_year, 4, 1), date(start_year + 1, 3, 31)


def current_fy() -> str:
    """The Indian FY containing 'now' (IST), as 'YYYY-YY'."""
    now_ist = datetime.now(timezone.utc).astimezone(IST)  # tz-ok: FY is IST-relative
    y = now_ist.year if now_ist.month >= 4 else now_ist.year - 1
    return f"{y}-{(y + 1) % 100:02d}"


def _to_dec(v: Any) -> Decimal:
    if v is None:
        return Decimal("0")
    if isinstance(v, Decimal128):
        return v.to_decimal()
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def _ist_date(dt: datetime) -> date:
    """Interpret a Mongo naive-UTC datetime as an IST calendar date."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST).date()


def _add_months(d: date, months: int) -> date:
    """`d` shifted forward by `months` calendar months (clamps day-of-month)."""
    m0 = d.month - 1 + months
    year = d.year + m0 // 12
    month = m0 % 12 + 1
    next_first = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    last_day = (next_first - timedelta(days=1)).day
    return date(year, month, min(d.day, last_day))


def _classify(buy_d: date, sell_d: date) -> str:
    """LTCG iff listed-equity holding period is strictly > 12 months, else STCG."""
    return "LTCG" if sell_d > _add_months(buy_d, 12) else "STCG"


def _name_for(isin: str) -> str:
    """Display name: prefer the holdings doc, fall back to the instruments master."""
    h = Collections.holdings().find_one({"isin": isin}, {"_id": 0, "name": 1})
    if h and h.get("name"):
        return h["name"]
    inst = Collections.instruments().find_one({"isin": isin}, {"_id": 0, "name": 1})
    return (inst or {}).get("name", "")


def _summarize(lots: list[dict]) -> dict:
    def agg(rows: list[dict]) -> dict:
        gain = sum((r["gain"] for r in rows), Decimal("0"))
        proceeds = sum((r["sell_proceeds"] for r in rows), Decimal("0"))
        cost = sum((r["buy_cost"] for r in rows), Decimal("0"))
        return {
            "realized_gain": gain.quantize(_TWO_DP, ROUND_HALF_UP),
            "proceeds": proceeds.quantize(_TWO_DP, ROUND_HALF_UP),
            "cost": cost.quantize(_TWO_DP, ROUND_HALF_UP),
            "lot_count": len(rows),
        }

    stcg = [r for r in lots if r["gain_type"] == "STCG"]
    ltcg = [r for r in lots if r["gain_type"] == "LTCG"]
    return {"stcg": agg(stcg), "ltcg": agg(ltcg), "total": agg(lots)}


def compute_capital_gains(fy: str | None = None) -> dict:
    """STCG/LTCG per-lot breakdown + aggregates for `fy` (default: current IST FY).

    Replays each ISIN's ledger through _fifo_replay, keeps only disposals whose
    SELL date (IST) falls inside the FY, classifies each buy-lot consumption
    STCG/LTCG, and aggregates. Pure read; no writes.
    """
    fy = fy or current_fy()
    _start_year, fy_start, fy_end = parse_fy(fy)

    txns = list(Collections.transactions().find({"deleted_at": None}))
    by_isin: dict[str, list[dict]] = defaultdict(list)
    for t in txns:
        by_isin[t["isin"]].append(t)

    lots: list[dict] = []
    for isin, group in by_isin.items():
        group.sort(key=lambda t: t.get("trade_date") or datetime.min)
        realized = _fifo_replay(group).get("_realized_lots", [])
        if not realized:
            continue
        symbol = group[0].get("symbol", "")
        name = _name_for(isin)
        for disp in realized:
            sell_d = _ist_date(disp["sell_trade_date"])
            if not (fy_start <= sell_d <= fy_end):
                continue
            buy_d = _ist_date(disp["buy_trade_date"])
            qty = _to_dec(disp["quantity"])
            buy_cost = (qty * disp["buy_cost_per_share"]).quantize(
                _TWO_DP, ROUND_HALF_UP
            )
            proceeds = (qty * disp["sell_proceeds_per_share"]).quantize(
                _TWO_DP, ROUND_HALF_UP
            )
            gain = (proceeds - buy_cost).quantize(_TWO_DP, ROUND_HALF_UP)
            lots.append(
                {
                    "isin": isin,
                    "symbol": symbol,
                    "name": name,
                    "buy_date": buy_d.isoformat(),
                    "sell_date": sell_d.isoformat(),
                    "quantity": qty,
                    "buy_cost": buy_cost,
                    "sell_proceeds": proceeds,
                    "gain": gain,
                    "holding_period_days": (sell_d - buy_d).days,
                    "gain_type": _classify(buy_d, sell_d),
                }
            )

    lots.sort(key=lambda r: (r["sell_date"], r["isin"], r["buy_date"]))
    return {
        "fy": fy,
        "fy_start": fy_start.isoformat(),
        "fy_end": fy_end.isoformat(),
        "summary": _summarize(lots),
        "lots": lots,
    }
