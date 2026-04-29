"""Conversations — log of ad-hoc Q&A with the agent."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from app.models._common import BaseDoc, Money, PyObjectId, utcnow

QueryIntent = Literal[
    "should_i_buy",
    "should_i_sell",
    "price_target_request",
    "allocation_request",
    "news_question",
    "general_market",
    "thesis_check",
    "educational",
    "other",
]
SentimentOverlay = Literal["cautious", "neutral", "aggressive"]


class Conversation(BaseDoc):
    """A single ad-hoc Q&A exchange. Stored for history & effectiveness review."""

    id: PyObjectId | None = Field(default=None, alias="_id")

    # The exchange
    query: str
    response: str
    intent: QueryIntent = "other"

    # User-stated sentiment for this query (e.g., "I'm feeling cautious today")
    sentiment_overlay: SentimentOverlay | None = None

    # Linked entities
    related_entities_isins: list[str] = Field(default_factory=list)
    related_holding_id: PyObjectId | None = Field(
        default=None,
        description="If query is about a current position, link to its holding",
    )
    related_monitored_id: PyObjectId | None = None

    # Citations
    cited_news_ids: list[PyObjectId] = Field(default_factory=list)
    cited_macro_signal_ids: list[PyObjectId] = Field(default_factory=list)
    cited_digest_ids: list[PyObjectId] = Field(default_factory=list)
    cited_transaction_ids: list[PyObjectId] = Field(default_factory=list)

    # LLM metadata
    model_used: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: Money = Field(default=Decimal("0"))
    duration_ms: int = 0

    # Outcomes (populated when you act on advice)
    user_action: str = Field(default="", description="Free text: what you did after")
    user_action_at: datetime | None = None
    follow_up_conversation_ids: list[PyObjectId] = Field(default_factory=list)

    # Audit
    created_at: datetime = Field(default_factory=utcnow)
