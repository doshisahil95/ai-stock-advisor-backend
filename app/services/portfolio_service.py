"""Portfolio aggregation service.

Pure functions that take active holdings + price data and return summary
aggregates. Called by the GET /portfolio/summary endpoint.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from bson import Decimal128

from app.db.client import Collections

log = logging.getLogger(__name__)

# How many top movers to return in each category
TOP_MOVERS_LIMIT = 5
CONCENTRATION_LIMIT = 5

# F12 (#28): concentration risk-alert thresholds (% of portfolio current value).
# Two-tier severity: cross the WARN bound -> "warn"; cross the HIGH bound -> "high".
# Operational constants live in code (project convention), not env/settings.
SINGLE_HOLDING_CONCENTRATION_WARN_PCT = 10.0
SINGLE_HOLDING_CONCENTRATION_HIGH_PCT = 20.0
SECTOR_CONCENTRATION_WARN_PCT = 30.0
SECTOR_CONCENTRATION_HIGH_PCT = 50.0


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

    pipeline = [
        {"$match": {"isin": {"$in": list(isin_to_latest_date.keys())}}},
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
        prev_close = None
        for entry in group["all_dates"]:
            if entry["date"] < latest_date:
                prev_close = _to_dec(entry["close"])
                break
        result[isin] = prev_close
    return result


def _annotate_holdings(
    holdings: list[dict], latest_prices: dict[str, dict]
) -> tuple[list[dict], dict]:
    """Annotate each holding with live value/P&L and accumulate portfolio totals.

    Extracted from compute_summary so the summary and risk-summary endpoints
    share ONE annotation path (no parallel aggregation). Behaviour-preserving:
    the per-holding dicts and running totals are exactly what compute_summary
    built inline before.

    Returns:
        (annotated, accum) where `annotated` is the per-holding list and
        `accum` carries running Decimal totals used by callers:
        {total_invested, total_current, total_day_gain, total_prev_value}.
    """
    isin_to_latest_date = {
        h["isin"]: latest_prices[h["isin"]]["date"]
        for h in holdings
        if h["isin"] in latest_prices
    }
    prev_closes = _bulk_previous_closes(isin_to_latest_date)

    now = datetime.now(timezone.utc)

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
                    "sector": h.get("sector") or "Unknown",
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

    accum = {
        "total_invested": total_invested,
        "total_current": total_current,
        "total_day_gain": total_day_gain,
        "total_prev_value": total_prev_value,
    }
    return annotated, accum


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
    # Shared with compute_risk_summary via _annotate_holdings (one path).
    annotated, _accum = _annotate_holdings(holdings, latest_prices)
    total_invested = _accum["total_invested"]
    total_current = _accum["total_current"]
    total_day_gain = _accum["total_day_gain"]
    total_prev_value = _accum["total_prev_value"]

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

    # Realized P&L lifetime — sum across ALL holdings (active + soft-deleted).
    #
    # F2 companion fix (Chat 5.5+): Pre-F2, this iterated soft-deleted only,
    # which UNDERCOUNTED lifetime realized for any active position that had
    # prior partial sells. Post-F2 (holdings reactivate on multi-cycle re-entry
    # rather than spawning parallel docs), the active doc carries cumulative
    # realized_pnl from FIFO replay across all cycles — so summing only
    # soft-deleted misses that. Sum across all docs to capture both.
    #
    # fully_exited_count stays soft-deleted-only because it semantically
    # counts positions no longer held.
    realized_lifetime = Decimal("0")
    fully_exited_count = 0
    for h in Collections.holdings().find(
        {},
        {"realized_pnl": 1, "deleted_at": 1, "_id": 0},
    ):
        realized_lifetime += _to_dec(h.get("realized_pnl", 0))
        if h.get("deleted_at") is not None:
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

    # ── Broker view (vs tax-correct) ─────────────────────────────────────────
    # ICICI/Zerodha display "invested" using nominal cost (no IT Act adjustments).
    # Our cost basis applies adjustments per Section 49(2C) etc.
    # If adjustments exist, expose what the broker would show alongside.
    from app.services.cost_basis_service import total_adjustment_amount

    adjustment_total = total_adjustment_amount()
    if adjustment_total != Decimal("0"):
        # adjustment_total is signed: (our_invested - broker_invested)
        # so broker_invested = our_invested - adjustment_total
        broker_invested = total_invested - adjustment_total
        broker_unrealized_pnl = (total_current - broker_invested).quantize(
            Decimal("0.01")
        )
        broker_unrealized_pnl_pct = (
            float((broker_unrealized_pnl / broker_invested) * 100)
            if broker_invested > 0
            else None
        )
        totals["broker_invested"] = broker_invested.quantize(Decimal("0.01"))
        totals["broker_unrealized_pnl"] = broker_unrealized_pnl
        totals["broker_unrealized_pnl_pct"] = (
            round(broker_unrealized_pnl_pct, 2)
            if broker_unrealized_pnl_pct is not None
            else None
        )
    else:
        totals["broker_invested"] = None
        totals["broker_unrealized_pnl"] = None
        totals["broker_unrealized_pnl_pct"] = None

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


def compute_risk_summary(holdings: list[dict], latest_prices: dict[str, dict]) -> dict:
    """Compute concentration & risk alerts over the active holdings (read-only).

    F12 (#28). Reuses _annotate_holdings (the SAME path compute_summary uses)
    so the concentration figures here are identical to /portfolio/summary's —
    no parallel aggregation. Produces:
      - concentration_by_holding: every priced holding, desc by % of portfolio
      - concentration_by_sector:  per-sector % of portfolio
      - alerts: two-tier (warn/high) single-holding + sector concentration
                breaches, plus a low-severity stale/missing-price data note.

    Thresholds are the module constants above (not env-configurable).
    Empty/unpriced portfolios return zeros and empty arrays.
    """
    now = datetime.now(timezone.utc)
    annotated, accum = _annotate_holdings(holdings, latest_prices)
    total_current = accum["total_current"]

    # ── Concentration by holding (priced holdings only) ─────────────────────
    priced = [h for h in annotated if h["current_value"] is not None]
    concentration_by_holding = []
    for h in sorted(priced, key=lambda x: float(x["current_value"]), reverse=True):
        pct = (
            float((h["current_value"] / total_current) * 100)
            if total_current > 0
            else 0.0
        )
        concentration_by_holding.append(
            {
                "isin": h["isin"],
                "symbol": h["symbol"],
                "sector": h["sector"] or "Unknown",
                "current_value": h["current_value"],
                "pct_of_portfolio": round(pct, 2),
            }
        )

    # ── Concentration by sector ─────────────────────────────────────────────
    sector_current: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    sector_count: dict[str, int] = defaultdict(int)
    for h in annotated:
        sector = h["sector"] or "Unknown"
        if h["current_value"]:
            sector_current[sector] += h["current_value"]
        sector_count[sector] += 1

    concentration_by_sector = []
    for sector in sorted(
        sector_current.keys(), key=lambda s: -float(sector_current[s])
    ):
        cur = sector_current[sector]
        pct = float((cur / total_current) * 100) if total_current > 0 else 0.0
        concentration_by_sector.append(
            {
                "sector": sector,
                "stock_count": sector_count[sector],
                "current_value": cur.quantize(Decimal("0.01")),
                "pct_of_portfolio": round(pct, 2),
            }
        )

    # ── Alerts ──────────────────────────────────────────────────────────────
    alerts: list[dict] = []

    for h in concentration_by_holding:
        pct = h["pct_of_portfolio"]
        if pct > SINGLE_HOLDING_CONCENTRATION_HIGH_PCT:
            severity, threshold = "high", SINGLE_HOLDING_CONCENTRATION_HIGH_PCT
        elif pct > SINGLE_HOLDING_CONCENTRATION_WARN_PCT:
            severity, threshold = "warn", SINGLE_HOLDING_CONCENTRATION_WARN_PCT
        else:
            continue
        alerts.append(
            {
                "type": "single_holding_concentration",
                "severity": severity,
                "isin": h["isin"],
                "symbol": h["symbol"],
                "pct_of_portfolio": pct,
                "threshold": threshold,
                "message": (
                    f"{h['symbol']} is {pct:.2f}% of the portfolio "
                    f"(over the {threshold:.0f}% {severity} threshold)."
                ),
            }
        )

    for s in concentration_by_sector:
        pct = s["pct_of_portfolio"]
        if pct > SECTOR_CONCENTRATION_HIGH_PCT:
            severity, threshold = "high", SECTOR_CONCENTRATION_HIGH_PCT
        elif pct > SECTOR_CONCENTRATION_WARN_PCT:
            severity, threshold = "warn", SECTOR_CONCENTRATION_WARN_PCT
        else:
            continue
        alerts.append(
            {
                "type": "sector_concentration",
                "severity": severity,
                "sector": s["sector"],
                "pct_of_portfolio": pct,
                "threshold": threshold,
                "message": (
                    f"The {s['sector']} sector is {pct:.2f}% of the portfolio "
                    f"(over the {threshold:.0f}% {severity} threshold)."
                ),
            }
        )

    # Stale / missing price data: annotated holdings flagged price_stale=True
    # (covers both >6-day-old prices and holdings with no price at all — the
    # latter are excluded from total_current, so their weight is understated).
    stale = [h for h in annotated if h.get("price_stale")]
    if stale:
        alerts.append(
            {
                "type": "stale_price",
                "severity": "info",
                "count": len(stale),
                "isins": [h["isin"] for h in stale],
                "symbols": [h["symbol"] for h in stale],
                "message": (
                    f"{len(stale)} holding(s) have stale (>6 days old) or missing "
                    "price data; concentration figures may be understated."
                ),
            }
        )

    return {
        "as_of": now,
        "total_current_value": total_current.quantize(Decimal("0.01")),
        "concentration_by_holding": concentration_by_holding,
        "concentration_by_sector": concentration_by_sector,
        "alerts": alerts,
    }
