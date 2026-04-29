"""Daily OHLCV — for holdings, monitored stocks, and NIFTY 100 universe."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from app.models._common import BaseDoc, Money, PyObjectId, utcnow

PriceSource = Literal["yfinance", "nse_official", "manual"]


class PriceDaily(BaseDoc):
    """One OHLCV bar for one stock for one trading day."""

    id: PyObjectId | None = Field(default=None, alias="_id")

    # Identity
    isin: str = Field(..., min_length=12, max_length=12, pattern=r"^[A-Z0-9]{12}$")
    symbol: str
    exchange: str = "NSE"

    # Time
    date: datetime = Field(..., description="Trading date (UTC midnight)")

    # OHLCV
    open: Money
    high: Money
    low: Money
    close: Money
    volume: int = Field(..., ge=0)
    value_inr: Money | None = None

    # Adjusted (post-split/bonus)
    adj_close: Money | None = None

    # Provenance
    source: PriceSource = "yfinance"
    fetched_at: datetime = Field(default_factory=utcnow)
