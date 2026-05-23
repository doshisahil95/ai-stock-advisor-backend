from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models._common import BaseDoc, Money, PyObjectId, utcnow

AddedBy = Literal["agent", "user_query", "user_explicit"]
MonitoringStatus = Literal["tracking", "passed", "rejected", "watchlist"]
FeedbackAction = Literal["acted", "passed", "rejected"]
AlertOn = Literal[
    "price_target", "earnings", "news", "52w_high", "52w_low", "volume_spike"
]


class MonitoredStock(BaseDoc):
    """A stock the agent / user is actively monitoring across digest runs."""


id: PyObjectId | None = Field(default=None, alias="_id")

# Identity
isin: str = Field(..., min_length=12, max_length=12, pattern=r"^[A-Z0-9]{12}$")
symbol: str = Field(default="")
exchange: str = "NSE"
name: str = Field(default="")
sector: str = Field(default="")
industry: str = Field(default="")

# Provenance
added_by: AddedBy
added_reason: str = Field(default="", description="Why this is being monitored")
added_at: datetime = Field(default_factory=utcnow)

# Evolving thesis (agent updates this over time — F1/F3 future use)
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

# Action triggers (F13 watchlist + future intraday alert paths)
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

# Feedback fields (written by POST /suggestions/{isin}/feedback via
# MonitoredStockFeedbackPatch). See PROJECT_STATE Section 12 / F6 + F5b.
acted_at: datetime | None = None
passed_at: datetime | None = None
rejected_at: datetime | None = None
last_feedback_action: FeedbackAction | None = None
last_feedback_at: datetime | None = None
last_feedback_note: str = ""

# Audit
created_at: datetime = Field(default_factory=utcnow)
updated_at: datetime = Field(default_factory=utcnow)


class MonitoredStockFeedbackPatch(BaseModel):
    """Typed shape of the $set patch written by /suggestions/{isin}/feedback.

    Constructing this model at write time catches Literal drift (status,
    action) loudly instead of letting the schema silently rot. The field
    set MUST match what submit_feedback's $set block writes — if you add
    a field there, add it here too, and vice versa.

    Caller pattern:
        patch = MonitoredStockFeedbackPatch(...)
        set_doc = patch.model_dump(exclude_none=True)
        Collections.monitored_stocks().update_one(
            {"isin": isin},
            {"$set": set_doc, "$setOnInsert": {...identity seeds...}},
            upsert=True,
        )

    The exclude_none=True is intentional — acted_at / passed_at /
    rejected_at are mutually exclusive per call (only one is set per
    feedback action), and we want $set to leave the other two
    untouched on existing docs so prior feedback timestamps are
    preserved across status flips.
    """


model_config = ConfigDict(extra="forbid")

isin: str = Field(..., min_length=12, max_length=12, pattern=r"^[A-Z0-9]{12}$")
status: MonitoringStatus
last_feedback_action: FeedbackAction
last_feedback_at: datetime
last_feedback_note: str = ""
updated_at: datetime
acted_at: datetime | None = None
passed_at: datetime | None = None
rejected_at: datetime | None = None
