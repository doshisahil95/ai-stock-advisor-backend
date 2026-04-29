"""Daily macro indicators — drives sector rotation and concentration reasoning."""

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.models._common import BaseDoc, Money, PyObjectId, utcnow


class MacroSignal(BaseDoc):
    """Snapshot of macro indicators for a single date.

    All optional — fetcher fills what's available; agent handles missing values.
    """

    id: PyObjectId | None = Field(default=None, alias="_id")

    date: datetime = Field(..., description="Reading date (UTC midnight)")

    # FX
    usd_inr: Money | None = None
    dxy: Money | None = Field(default=None, description="US Dollar Index")

    # Commodities
    brent_usd: Money | None = None
    gold_inr_per_10g: Money | None = None
    copper_usd_per_lb: Money | None = None

    # Yields & rates
    india_10y_yield: Money | None = Field(default=None, description="In percent")
    us_10y_yield: Money | None = Field(default=None, description="In percent")
    rbi_repo: Money | None = Field(default=None, description="In percent")

    # Flows (₹ crores; negative = outflow)
    fii_equity_inr_cr: Money | None = None
    dii_equity_inr_cr: Money | None = None

    # Volatility
    india_vix: Money | None = None
    cboe_vix: Money | None = None

    # Sources
    sources: list[str] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=utcnow)
