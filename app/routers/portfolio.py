"""Portfolio summary API."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from bson import Decimal128, ObjectId
from fastapi import APIRouter, Query

from app.db.client import Collections
from app.services.portfolio_service import (
    _to_dec,
    compute_risk_summary,
    compute_summary,
)
from app.services.price_service import (
    annotate_with_current_price,
    bulk_get_latest_prices,
    bulk_get_previous_closes,
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def _serialize(value: Any) -> Any:
    """Recursive JSON-serializer: Decimal/Decimal128 → str, ObjectId → str, datetime → ISO."""
    if isinstance(value, Decimal128):
        return str(value.to_decimal())
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialize(v) for v in value]
    return value


@router.get(
    "/summary",
    summary="Full portfolio summary with totals, movers, and sector breakdown",
)
def portfolio_summary() -> dict:
    """Returns top-level totals, top movers (by pct + by value), day's gainers/losers,
    concentration (top 5 holdings by value), and sector breakdown.

    All amounts in INR. Decimal values returned as strings to preserve precision.
    """
    holdings = list(
        Collections.holdings().find({"deleted_at": None}).sort("invested_amount", -1)
    )

    if not holdings:
        return _serialize(
            {
                "as_of": datetime.utcnow(),
                "totals": {
                    "invested": Decimal("0"),
                    "current_value": Decimal("0"),
                    "unrealized_pnl": Decimal("0"),
                    "unrealized_pnl_pct": 0.0,
                    "day_gain": Decimal("0"),
                    "day_gain_pct": 0.0,
                    "realized_pnl_lifetime": Decimal("0"),
                    "total_holdings": 0,
                    "fully_exited_lifetime": 0,
                },
                "top_gainers_by_pct": [],
                "top_losers_by_pct": [],
                "top_gainers_by_value": [],
                "top_losers_by_value": [],
                "day_gainers": [],
                "day_losers": [],
                "concentration": [],
                "sector_breakdown": [],
            }
        )

    # Bulk-fetch latest prices in one Mongo aggregation
    isins = [h["isin"] for h in holdings]
    latest_prices = bulk_get_latest_prices(isins)

    summary = compute_summary(holdings, latest_prices)
    return _serialize(summary)


@router.get(
    "/risk-summary",
    summary="Concentration & risk alerts over current holdings (read-only)",
)
def portfolio_risk_summary() -> dict:
    """F12 (#28). Concentration by holding and by sector, plus threshold-based
    risk alerts, over the active holdings.

    Read-only. Reuses the same annotation path as /portfolio/summary, so the
    concentration figures match. All amounts in INR; Decimals as strings.
    """
    holdings = list(
        Collections.holdings().find({"deleted_at": None}).sort("invested_amount", -1)
    )
    isins = [h["isin"] for h in holdings]
    latest_prices = bulk_get_latest_prices(isins) if isins else {}
    return _serialize(compute_risk_summary(holdings, latest_prices))


@router.get(
    "/by-tag",
    summary="Active holdings filtered by tag, with live P&L + tag-scoped totals (read-only)",
)
def portfolio_by_tag(
    tag: str = Query(
        ...,
        min_length=1,
        description="Tag to filter holdings.tags on (exact, case-sensitive).",
    ),
) -> dict:
    """F15 (#28). Return active holdings whose `tags` array contains `tag`, each
    annotated with live P&L (same shape and code path as GET /portfolio/holdings),
    plus a tag-scoped totals block.

    Read-only. Tag match is exact and case-sensitive (Mongo array-membership).
    A missing or empty `tag` → 422. An unknown tag → empty holdings + zeroed
    totals (200, not 404).
    """
    docs = list(
        Collections.holdings()
        .find({"deleted_at": None, "tags": tag})
        .sort("invested_amount", -1)
    )

    # Same annotate path as holdings.list_holdings (one pattern, not parallel).
    isins = [d["isin"] for d in docs]
    price_map = bulk_get_latest_prices(isins) if isins else {}
    isin_to_date = {
        d["isin"]: price_map[d["isin"]]["date"] for d in docs if d["isin"] in price_map
    }
    prev_close_map = bulk_get_previous_closes(isin_to_date)
    annotated = [
        annotate_with_current_price(
            d,
            price_map.get(d["isin"]),
            prev_close_map.get(d["isin"]),
        )
        for d in docs
    ]

    # Tag-scoped totals. invested counts every matched holding; current/unrealized
    # only count priced holdings (an unpriced holding has current_value=None), so
    # the totals reconcile with what the table can actually show.
    total_invested = Decimal("0")
    total_current = Decimal("0")
    for d in annotated:
        total_invested += _to_dec(d.get("invested_amount"))
        cv = d.get("current_value")
        if cv is not None:
            total_current += _to_dec(cv)
    total_unrealized = total_current - total_invested
    total_unrealized_pct = (
        float((total_unrealized / total_invested) * 100) if total_invested > 0 else 0.0
    )

    totals = {
        "count": len(annotated),
        "invested": total_invested.quantize(Decimal("0.01")),
        "current_value": total_current.quantize(Decimal("0.01")),
        "unrealized_pnl": total_unrealized.quantize(Decimal("0.01")),
        "unrealized_pnl_pct": round(total_unrealized_pct, 2),
    }

    return _serialize(
        {
            "tag": tag,
            "holdings": annotated,
            "totals": totals,
        }
    )
