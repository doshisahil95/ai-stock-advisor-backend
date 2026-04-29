"""Alert log — audit trail of every alert sent."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.models._common import BaseDoc, Money, PyObjectId, utcnow

AlertType = Literal[
    "stop_loss_hit",
    "target_hit",
    "52w_high",
    "52w_low",
    "volume_spike",
    "gap_up",
    "gap_down",
    "news_event",
    "earnings_reminder",
    "macro_event",
    "concentration_warning",
    "digest_pre_market",
    "digest_post_market",
    "system_error",
]
Severity = Literal["low", "medium", "high", "critical"]
DeliveryChannel = Literal[
    "ntfy_public_price",
    "ntfy_public_news",
    "ntfy_private_digests",
    "ntfy_private_errors",
    "email",
]
DeliveryStatus = Literal["sent", "failed", "retried"]
UserAction = Literal["trimmed", "added", "exited", "ignored", "noted"]


class TriggerData(BaseDoc):
    """Snapshot of relevant numbers at time of alert."""

    current_price: Money | None = None
    stop_loss: Money | None = None
    target_price: Money | None = None
    avg_cost: Money | None = None
    quantity: Money | None = None
    pct_change: float | None = None
    extras: dict = Field(
        default_factory=dict, description="Type-specific extra context"
    )


class Alert(BaseDoc):
    """A single alert ever sent. Retained forever."""

    id: PyObjectId | None = Field(default=None, alias="_id")

    # What
    alert_type: AlertType
    severity: Severity
    channel: DeliveryChannel

    # Subject
    isin: str | None = Field(default=None, min_length=12, max_length=12)
    symbol: str | None = None

    # Content as delivered
    title: str
    body: str

    # LLM reasoning (for news/digest-driven alerts)
    llm_reasoning: str = ""
    cited_news_ids: list[PyObjectId] = Field(default_factory=list)
    cited_transaction_ids: list[PyObjectId] = Field(default_factory=list)

    # Trigger snapshot
    trigger_data: TriggerData = Field(default_factory=TriggerData)

    # Delivery
    ntfy_message_id: str = ""
    email_message_id: str = ""
    sent_at: datetime = Field(default_factory=utcnow)
    delivery_status: DeliveryStatus = "sent"
    delivery_error: str = ""

    # User interaction (Phase 3+ — for effectiveness review)
    acknowledged_at: datetime | None = None
    user_action: UserAction | None = None
    user_action_notes: str = ""

    # Audit
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
