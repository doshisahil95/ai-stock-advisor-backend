"""User profile — your investing context that the agent uses."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models._common import BaseDoc, utcnow

AlertPriority = Literal["min", "low", "default", "high", "urgent"]


class ConcentrationAwareness(BaseModel):
    """Thresholds at which agent must explicitly reason about concentration risk.

    NOT hard limits — they trigger explicit reasoning in recommendations.
    """

    model_config = ConfigDict(extra="forbid")

    reasoning_required_above_pct: float = Field(default=15.0, ge=0, le=100)
    sector_reasoning_required_above_pct: float = Field(default=30.0, ge=0, le=100)


class AlertPriorities(BaseModel):
    """Per-alert-type default priority for ntfy delivery."""

    model_config = ConfigDict(extra="forbid")

    stop_loss: AlertPriority = "high"
    target_hit: AlertPriority = "high"
    news: AlertPriority = "default"
    earnings: AlertPriority = "default"
    macro: AlertPriority = "default"


class UserProfile(BaseDoc):
    """Single-user investing context. There is exactly one of these documents."""

    id: str = Field(default="sahil", alias="_id")

    # Basic
    display_name: str
    email: EmailStr
    timezone: str = "Asia/Kolkata"

    # Long-term context (free text, edit anytime)
    investing_philosophy: str = Field(default="")
    risk_narrative: str = Field(default="")

    # Tax
    tax_bracket_pct: float = Field(default=30.0, ge=0, le=100)

    # Concentration awareness (prompt triggers, NOT limits)
    concentration_awareness: ConcentrationAwareness = Field(
        default_factory=ConcentrationAwareness
    )

    # Notification scheduling
    digest_time_pre_market: str = Field(default="08:45", pattern=r"^\d{2}:\d{2}$")
    digest_time_post_market: str = Field(default="16:00", pattern=r"^\d{2}:\d{2}$")
    alert_priorities: AlertPriorities = Field(default_factory=AlertPriorities)

    # Audit
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
