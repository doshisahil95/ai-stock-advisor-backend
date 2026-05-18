"""Earnings event for one (ISIN, earnings_date) tuple (F14).

One doc per upcoming or historical earnings event. Source = yfinance
(Ticker.calendar) refreshed weekly alongside fundamentals.

Consumed by:
  - Buy-side scoring: gate to skip suggesting buys within 5 days
    of an earnings event.
  - Sell-side scoring (F2): signal/penalty for 'within 5 days of
    earnings' (too noisy to suggest selling through earnings).

Refresh semantics (see refresh_earnings_for in fundamentals_service):
  - Each weekly refresh DELETES all future (>= today) events for the
    ISIN and inserts the fresh list from yfinance.
  - Past events are never deleted; we keep history for audit.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models._common import utcnow


class EarningsEvent(BaseModel):
    """One upcoming or historical earnings event for one ISIN."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    isin: str = Field(..., min_length=12, max_length=12, pattern=r"^[A-Z0-9]{12}$")
    symbol: str = Field(..., description="Trading symbol (e.g., 'INFY')")
    exchange: str = Field(default="NSE", pattern=r"^(NSE|BSE)$")

    earnings_date: datetime = Field(
        ...,
        description=(
            "Date of the earnings event. Stored tz-naive (Mongo invariant). "
            "yfinance returns this as a Timestamp; we coerce to naive datetime."
        ),
    )

    source: str = Field(default="yfinance")
    source_raw: dict[str, Any] | None = Field(
        default=None,
        description="Raw yfinance Ticker.calendar dict for debugging. May be omitted to save space.",
    )

    fetched_at: datetime = Field(
        default_factory=utcnow,
        description="When this row was last (re-)fetched from the provider.",
    )
    created_at: datetime = Field(default_factory=utcnow)