"""Holding — derived current position per stock (recomputed from transactions)."""

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.models._common import BaseDoc, Money, PyObjectId, utcnow


class Holding(BaseDoc):
    """Current position in a single stock. Refreshed from transactions on demand."""

    id: PyObjectId | None = Field(default=None, alias="_id")

    # Identity (unique key: isin)
    isin: str = Field(..., min_length=12, max_length=12, pattern=r"^[A-Z0-9]{12}$")
    symbol: str
    exchange: str = "NSE"
    name: str = Field(default="")
    sector: str = Field(default="")
    industry: str = Field(default="")

    # Current position
    quantity: Money = Field(default=Decimal("0"))
    avg_cost: Money = Field(default=Decimal("0"))
    invested_amount: Money = Field(default=Decimal("0"))

    # Realized
    realized_pnl: Money = Field(default=Decimal("0"))
    total_dividends_received: Money = Field(default=Decimal("0"))

    # Personal metadata
    user_notes: str = ""
    thesis: str = ""
    tags: list[str] = Field(default_factory=list)

    # Risk parameters
    stop_loss: Money | None = None
    target_price: Money | None = None
    alert_on: list[str] = Field(
        default_factory=lambda: ["stop_loss", "target", "earnings", "news", "52w_high"]
    )

    # Recompute tracking
    last_recomputed_at: datetime = Field(default_factory=utcnow)
    first_purchased_at: datetime | None = None
    last_traded_at: datetime | None = None

    # Audit
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    deleted_at: datetime | None = None
