"""Digest — generated pre-market / post-market briefings. Retained forever."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models._common import BaseDoc, Money, PyObjectId, utcnow

DigestType = Literal["pre_market", "post_market"]
SuggestedAction = Literal["HOLD", "TRIM", "ADD", "EXIT", "WATCH"]


class HoldingDigestEntry(BaseModel):
    """Per-holding section in a digest."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    isin: str
    symbol: str
    catalysts_today: list[str] = Field(default_factory=list)
    risks_today: list[str] = Field(default_factory=list)
    suggested_action: SuggestedAction = "HOLD"
    reasoning: str = ""
    confidence: float = Field(default=0.5, ge=0, le=1)
    cited_news_ids: list[PyObjectId] = Field(default_factory=list)


class WatchlistDigestEntry(BaseModel):
    """Per-monitored-stock section in a digest."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    isin: str
    symbol: str
    update: str = ""
    approaching_trigger: bool = False
    suggested_action: SuggestedAction = "WATCH"


class Digest(BaseDoc):
    """A pre-market or post-market briefing. Stored forever."""

    id: PyObjectId | None = Field(default=None, alias="_id")

    # What & when
    digest_type: DigestType
    for_date: datetime = Field(..., description="The trading day this digest is FOR")
    generated_at: datetime = Field(default_factory=utcnow)

    # Generation context
    model_used: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: Money = Field(default=Decimal("0"))
    generation_duration_ms: int = 0

    # Structured content
    market_summary: str = ""
    per_holding: list[HoldingDigestEntry] = Field(default_factory=list)
    watchlist_updates: list[WatchlistDigestEntry] = Field(default_factory=list)
    top_3_focus: list[str] = Field(default_factory=list)
    contrarian_insight: str = ""

    # User interest reminders ("you asked about X recently")
    recent_user_interest: list[dict] = Field(default_factory=list)

    # Sources
    cited_news_ids: list[PyObjectId] = Field(default_factory=list)
    cited_macro_signal_ids: list[PyObjectId] = Field(default_factory=list)

    # Delivery
    email_sent_at: datetime | None = None
    email_message_id: str = ""
    ntfy_sent_at: datetime | None = None
    ntfy_message_id: str = ""

    # Feedback (Phase 4 effectiveness review)
    user_rating: int | None = Field(default=None, ge=1, le=5)
    user_feedback_notes: str = ""

    # Audit
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
