"""Monitored stocks — agent-tracked candidates (formerly 'watchlist').

Mostly populated by the agent. User can also explicitly add via API or via
ad-hoc queries ('what about TATAMOTORS?').
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from app.models._common import BaseDoc, Money, PyObjectId, utcnow

AddedBy = Literal["agent", "user_query", "user_explicit"]
MonitoringStatus = Literal["tracking", "promoted_to_holding", "dropped"]
AlertOn = Literal[
    "price_target", "earnings", "news", "52w_high", "52w_low", "volume_spike"
]


class MonitoredStock(BaseDoc):
    """A stock the agent is actively analyzing across digest runs."""

    id: PyObjectId | None = Field(default=None, alias="_id")

    # Identity
    isin: str = Field(..., min_length=12, max_length=12, pattern=r"^[A-Z0-9]{12}$")
    symbol: str
    exchange: str = "NSE"
    name: str = Field(default="")
    sector: str = Field(default="")
    industry: str = Field(default="")

    # Provenance
    added_by: AddedBy
    added_reason: str = Field(default="", description="Why this is being monitored")
    added_at: datetime = Field(default_factory=utcnow)

    # Evolving thesis (agent updates this over time)
    thesis: str = ""
    conviction: float = Field(
        default=0.5,
        ge=0,
        le=1,
        description="Agent's evolving confidence in this opportunity (0-1)",
    )
    conviction_history: list[dict] = Field(
        default_factory=list,
        description="[{date, score, reason}] — track how conviction evolved",
    )

    # Action triggers
    target_buy_price: Money | None = None
    alert_above: Money | None = None
    alert_below: Money | None = None
    alert_on: list[AlertOn] = Field(
        default_factory=lambda: ["price_target", "earnings", "news"]
    )

    # Tags & notes
    tags: list[str] = Field(default_factory=list)
    user_notes: str = ""

    # Lifecycle
    status: MonitoringStatus = "tracking"
    last_reviewed_at: datetime = Field(default_factory=utcnow)
    last_user_interest_at: datetime | None = Field(
        default=None,
        description="When you last asked about it — used in digest 'stocks you've shown interest in'",
    )
    promoted_to_holding_at: datetime | None = None
    dropped_at: datetime | None = None
    dropped_reason: str = ""

    # Audit
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
