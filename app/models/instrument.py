"""Tradable equity instrument from NSE or BSE.

Sourced from Zerodha Kite's public instruments dump and refreshed daily by cron.
This is reference data, not user data — no schema versioning needed.
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

    source: str = Field(default="kite")
    refreshed_at: datetime = Field(default_factory=utcnow)
