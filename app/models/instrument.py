"""Tradable equity instrument from NSE.

Sourced from NSE EQUITY_L.csv and refreshed daily by cron.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models._common import utcnow


class Instrument(BaseModel):
    """One instrument per (exchange, symbol)."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    exchange: str = Field(..., pattern=r"^(NSE|BSE)$")
    symbol: str = Field(..., description="Trading symbol (e.g., 'INFY')")
    isin: str = Field(..., min_length=12, max_length=12, pattern=r"^[A-Z0-9]{12}$")
    name: str = Field(default="", description="Company name")

    instrument_type: str = Field(default="EQ")
    segment: str = Field(default="")
    lot_size: int = Field(default=1, ge=1)
    tick_size: float = Field(default=0.05, ge=0)

    source: str = Field(default="nse_official")
    last_seen_at: datetime = Field(
        default_factory=utcnow,
        description="Last refresh that confirmed this instrument exists",
    )
    last_changed_at: datetime = Field(
        default_factory=utcnow,
        description="Last refresh where any field actually changed",
    )
