"""Portfolio aggregation service.

Pure functions that take active holdings + price data and return summary
aggregates. Called by the GET /portfolio/summary endpoint.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from bson import Decimal128

from app.db.client import Collections

log = logging.getLogger(__name__)

# How many top movers to return in each category
TOP_MOVERS_LIMIT = 5
CONCENTRATION_LIMIT = 5


def _to_dec(v: Any) -> Decimal:
    if isinstance(v, Decimal128):
        return v.to_decimal()
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v)) if v is not None else Decimal("0")


def _previous_trading_day_close(isin: str, latest_date: datetime) -> Decimal | None:
    """Get the close from the trading day before `latest_date`.

    Used for day's gain calculation.
    """
    doc = Collections.prices_daily().find_one(
        {"isin": isin, "date": {"$lt": latest_date}},
        sort=[("date", -1)],
        projection={"close": 1, "_id": 0},
    )
    return _to_dec(doc["close"]) if doc else None


def _bulk_previous_closes(
    isin_to_latest_date: dict[str, datetime],
) -> dict[str, Decimal | None]:
    """Bulk-fetch previous trading day's close for many ISINs.

    Uses one aggregation: for each ISIN, find the most recent price strictly
    before the latest_date.
    """
    if not isin_to_latest_date:
        return {}

    # Build $facet — one branch per ISIN. For ~32 holdings this is fine;
    # for 100s of holdings we'd switch to a per-ISIN find.
    # Simpler approach: do one aggregation across all relevant ISINs at once.
    pipeline = [
        {"$match": {"isin": {"$in": list(isin_to_latest_date.keys())}}},
        # Keep only docs strictly before each ISIN's latest date.
        # We can't do per-ISIN "$lt" easily; instead, take all docs and filter in the next stage.
        {"$sort": {"isin": 1, "date": -1}},
        {
            "$group": {
                "_id": "$isin",
                "all_dates": {"$push": {"date": "$date", "close": "$close"}},
            }
        },
    ]

    result: dict[str, Decimal | None] = {}
    for group in Collections.prices_daily().aggregate(pipeline):
        isin = group["_id"]
        latest_date = isin_to_latest_date[isin]
        # Find the first entry whose date < latest_date (already sorted desc)
        prev_close = None
        for entry in group["all_dates"]:
            if entry["date"] < latest_date:
                prev_close = _to_dec(entry["close"])
                break
        result[isin] = prev_close

    return result


def compute_summary(holdings: list[dict], latest_prices: dict[str, dict]) -> dict:
    """Compute the full portfolio summary.

    Args:
        holdings: list of active holding docs (from holdings collection)
        latest_prices: {isin: latest_price_doc} from prices_daily

    Returns:
        Dict matching the GET /portfolio/summary response shape.
    """
    now = datetime.now(timezone.utc)

    # ── Per-holding annotation ──────────────────────────────────────────────
    isin_to_latest_date = {
        h["isin"]: latest_prices[h["isin"]]["date"]
        for h in holdings
        if h["isin"] in latest_prices
    }
    prev_closes = _bulk_previous_closes(isin_to_latest_date)

    annotated: list[dict] = []
    total_invested = Decimal("0")
    total_current = Decimal("0")
    total_day_gain = Decimal("0")
    total_prev_value = Decimal("0")

    for h in holdings:
        isin = h["isin"]
        qty = _to_dec(h["quantity"])
        avg_cost = _to_dec(h["avg_cost"])
        invested = _to_dec(h["invested_amount"])

        latest = latest_prices.get(isin)
        if not latest:
            # No price data — skip from gain/loss math but include placeholder
            annotated.append(
                {
                    "isin": isin,
                    "symbol": h["symbol"],
                    "sector": h.get("sector", "Unknown"),
                    "quantity": qty,
                    "avg_cost": avg_cost,
                    "invested": invested,
                    "current_price": None,
                    "current_value": None,
                    "unrealized_pnl": None,
                    "unrealized_pnl_pct": None,
                    "day_gain": None,
                    "day_gain_pct": None,
                    "price_stale": True,
                    "price_as_of": None,
                }
            )
            total_invested += invested
            continue

        cur_price = _to_dec(latest["close"])
        cur_value = (qty * cur_price).quantize(Decimal("0.01"))
        unrealized_pnl = (cur_value - invested).quantize(Decimal("0.01"))
        unrealized_pct = (
            float((unrealized_pnl / invested) * 100) if invested > 0 else None
        )

        prev_close = prev_closes.get(isin)
        if prev_close is not None and prev_close > 0:
            prev_value = (qty * prev_close).quantize(Decimal("0.01"))
            day_gain = (cur_value - prev_value).quantize(Decimal("0.01"))
            day_gain_pct = float(((cur_price / prev_close) - 1) * 100)
            total_prev_value += prev_value
            total_day_gain += day_gain
        else:
            day_gain = None
            day_gain_pct = None

        # Mark stale if price is more than 6 calendar days old
        from datetime import timedelta

        price_date = latest["date"]
        if price_date.tzinfo is None:
            price_date = price_date.replace(tzinfo=timezone.utc)
        is_stale = (now - price_date) > timedelta(days=6)

        annotated.append(
            {
                "isin": isin,
                "symbol": h["symbol"],
                "sector": h.get("sector") or "Unknown",
                "quantity": qty,
                "avg_cost": avg_cost,
                "invested": invested,
                "current_price": cur_price,
                "current_value": cur_value,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_pct": round(unrealized_pct, 2)
                if unrealized_pct is not None
                else None,
                "day_gain": day_gain,
                "day_gain_pct": round(day_gain_pct, 2)
                if day_gain_pct is not None
                else None,
                "price_stale": is_stale,
                "price_as_of": price_date,
            }
        )
        total_invested += invested
        total_current += cur_value

    # ── Top-level totals ────────────────────────────────────────────────────
    total_unrealized = total_current - total_invested
    total_unrealized_pct = (
        float((total_unrealized / total_invested) * 100) if total_invested > 0 else 0.0
    )
    total_day_gain_pct = (
        float((total_day_gain / total_prev_value) * 100)
        if total_prev_value > 0
        else 0.0
    )

    # Realized P&L lifetime (across all soft-deleted exits)
    realized_lifetime = Decimal("0")
    fully_exited_count = 0
    for h in Collections.holdings().find(
        {"deleted_at": {"$ne": None}},
        {"realized_pnl": 1, "_id": 0},
    ):
        realized_lifetime += _to_dec(h.get("realized_pnl", 0))
        fully_exited_count += 1

    totals = {
        "invested": total_invested.quantize(Decimal("0.01")),
        "current_value": total_current.quantize(Decimal("0.01")),
        "unrealized_pnl": total_unrealized.quantize(Decimal("0.01")),
        "unrealized_pnl_pct": round(total_unrealized_pct, 2),
        "day_gain": total_day_gain.quantize(Decimal("0.01")),
        "day_gain_pct": round(total_day_gain_pct, 2),
        "realized_pnl_lifetime": realized_lifetime.quantize(Decimal("0.01")),
        "total_holdings": len(holdings),
        "fully_exited_lifetime": fully_exited_count,
    }

    # ── Movers ──────────────────────────────────────────────────────────────
    with_pnl = [h for h in annotated if h["unrealized_pnl"] is not None]

    top_gainers_pct = sorted(
        with_pnl, key=lambda h: h["unrealized_pnl_pct"] or 0, reverse=True
    )[:TOP_MOVERS_LIMIT]
    top_losers_pct = sorted(with_pnl, key=lambda h: h["unrealized_pnl_pct"] or 0)[
        :TOP_MOVERS_LIMIT
    ]
    top_gainers_value = sorted(
        with_pnl, key=lambda h: float(h["unrealized_pnl"] or 0), reverse=True
    )[:TOP_MOVERS_LIMIT]
    top_losers_value = sorted(with_pnl, key=lambda h: float(h["unrealized_pnl"] or 0))[
        :TOP_MOVERS_LIMIT
    ]

    def _mover_brief(h: dict) -> dict:
        return {
            "symbol": h["symbol"],
            "isin": h["isin"],
            "current_value": h["current_value"],
            "unrealized_pnl": h["unrealized_pnl"],
            "unrealized_pnl_pct": h["unrealized_pnl_pct"],
        }

    # ── Day's biggest movers (today's gain/loss) ────────────────────────────
    with_day = [h for h in annotated if h["day_gain"] is not None]
    day_gainers = sorted(with_day, key=lambda h: h["day_gain_pct"] or 0, reverse=True)[
        :TOP_MOVERS_LIMIT
    ]
    day_losers = sorted(with_day, key=lambda h: h["day_gain_pct"] or 0)[
        :TOP_MOVERS_LIMIT
    ]

    def _day_mover_brief(h: dict) -> dict:
        return {
            "symbol": h["symbol"],
            "isin": h["isin"],
            "current_price": h["current_price"],
            "day_gain": h["day_gain"],
            "day_gain_pct": h["day_gain_pct"],
        }

    # ── Concentration ──────────────────────────────────────────────────────
    if total_current > 0:
        concentration = sorted(
            [h for h in annotated if h["current_value"]],
            key=lambda h: float(h["current_value"]),
            reverse=True,
        )[:CONCENTRATION_LIMIT]
        concentration_brief = [
            {
                "symbol": h["symbol"],
                "isin": h["isin"],
                "current_value": h["current_value"],
                "pct_of_portfolio": round(
                    float((h["current_value"] / total_current) * 100), 2
                ),
            }
            for h in concentration
        ]
    else:
        concentration_brief = []

    # ── Sector breakdown ───────────────────────────────────────────────────
    sector_invested: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    sector_current: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    sector_count: dict[str, int] = defaultdict(int)

    for h in annotated:
        sector = h["sector"] or "Unknown"
        sector_invested[sector] += h["invested"]
        if h["current_value"]:
            sector_current[sector] += h["current_value"]
        sector_count[sector] += 1

    sector_breakdown = []
    for sector in sorted(
        sector_invested.keys(),
        key=lambda s: -float(sector_current.get(s, sector_invested[s])),
    ):
        inv = sector_invested[sector]
        cur = sector_current[sector]
        pnl = (cur - inv).quantize(Decimal("0.01"))
        pnl_pct = float((pnl / inv) * 100) if inv > 0 else 0.0
        pct_of_portfolio = (
            float((cur / total_current) * 100) if total_current > 0 else 0.0
        )
        sector_breakdown.append(
            {
                "sector": sector,
                "stock_count": sector_count[sector],
                "invested": inv.quantize(Decimal("0.01")),
                "current_value": cur.quantize(Decimal("0.01")),
                "unrealized_pnl": pnl,
                "unrealized_pnl_pct": round(pnl_pct, 2),
                "pct_of_portfolio": round(pct_of_portfolio, 2),
            }
        )

    return {
        "as_of": now,
        "totals": totals,
        "top_gainers_by_pct": [_mover_brief(h) for h in top_gainers_pct],
        "top_losers_by_pct": [_mover_brief(h) for h in top_losers_pct],
        "top_gainers_by_value": [_mover_brief(h) for h in top_gainers_value],
        "top_losers_by_value": [_mover_brief(h) for h in top_losers_value],
        "day_gainers": [_day_mover_brief(h) for h in day_gainers],
        "day_losers": [_day_mover_brief(h) for h in day_losers],
        "concentration": concentration_brief,
        "sector_breakdown": sector_breakdown,
    }
