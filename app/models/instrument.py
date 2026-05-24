"""Tradable equity instrument from NSE.

Sourced from NSE EQUITY_L.csv and refreshed daily by cron.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models._common import PyObjectId, utcnow


class Instrument(BaseModel):
    """One instrument per (exchange, symbol)."""

    # F20 fix (Chat 5.5+): populate_by_name=True so model_validate(mongo_doc)
    # accepts the '_id' alias. Kept extra='forbid' so future stray fields
    # still raise (good guard for the daily NSE refresh diff).
    model_config = ConfigDict(
        extra="forbid",
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    # F20 fix (Chat 5.5+): _id alias. Pre-fix extra='forbid' rejected the
    # _id key on any Mongo round-trip through model_validate. No current
    # consumer triggers it (instrument_service uses raw dicts) but the model
    # was structurally broken for any future model_validate user.
    id: PyObjectId | None = Field(default=None, alias="_id")
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
