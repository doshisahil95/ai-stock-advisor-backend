"""Portfolio summary API."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from bson import Decimal128, ObjectId
from fastapi import APIRouter

from app.db.client import Collections
from app.services.portfolio_service import compute_summary
from app.services.price_service import bulk_get_latest_prices

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
