"""Monitored stocks — agent-tracked candidates (formerly 'watchlist').

Populated today by the feedback writer at POST /suggestions/{isin}/feedback.
Future populated by agent / user_query / user_explicit code paths (F1, F3,
F13) — fields for those paths exist on the model but are not written yet.

Schema notes (Chat 5, A1 — 2026-05-20):
- `MonitoringStatus` Literal aligned with writer-produced values:
  "tracking" / "passed" / "rejected" plus future-use "watchlist" (F13).
  Previous values "promoted_to_holding" / "dropped" REMOVED — no code in
  the current tree writes them; they were aspirational lifecycle states
  from the original scaffold. The matching `promoted_to_holding_at` /
  `dropped_at` / `dropped_reason` lifecycle fields are removed for the
  same reason. If F1/F3/F13 needs any of these back, re-add them then.
- Feedback fields (`acted_at` / `passed_at` / `rejected_at`,
  `last_feedback_action` / `last_feedback_at` / `last_feedback_note`)
  ADDED to match writer reality. Previously the writer wrote them via
  raw `update_one` and the model didn't declare them, which meant any
  future `MonitoredStock(**doc)` round-trip would crash.
- `symbol` downgraded to optional (default ""). The feedback writer
  doesn't have it; rich-entry paths (agent, watchlist seed) will
  populate it when they ship. Strict re-tightening can wait until
  those paths exist.
- `MonitoredStockFeedbackPatch` below is the typed shape the feedback
  writer uses to build its $set patch. Constructing it catches Literal
  drift (status, action) at write time. Its field set MUST match what
  `submit_feedback`'s $set block writes — if you add a field there,
  add it here too, and vice versa. This is the load-bearing schema
  for the feedback path (Chat 5 / A1).

See also:
- PROJECT_STATE Section 7 (collection schema), Section 12 (F6 + F5b
  invariants), Section 14 (write-before-apply via
  monitored_stocks_audit_service.log_change).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models._common import BaseDoc, Money, PyObjectId, utcnow

AddedBy = Literal["agent", "user_query", "user_explicit"]
MonitoringStatus = Literal["tracking", "passed", "rejected", "watchlist"]
FeedbackAction = Literal["acted", "passed", "rejected"]
# TD1/#43: which side of the book a feedback action targets. Mirrors
# SuggestionDirection in models/suggestion.py; kept local to avoid a cross-
# model import. Used by MonitoredStockFeedbackPatch + the MonitoredStock
# feedback_direction field so exclusion can be direction-scoped.
FeedbackDirection = Literal["buy", "sell"]
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

    # TD1/#43: which side of the book the LAST feedback action was for. Lets
    # get_excluded_isins suppress an ISIN only on the direction the user gave
    # feedback on (a sell-side "rejected" no longer also suppresses the buy
    # side for 90d, and vice versa). Optional + default None so the two live
    # pre-#43 docs (and every legacy doc) coerce cleanly; None is treated as
    # "applies to the requested direction" so exclusion behavior is BYTE-
    # IDENTICAL to today until direction-tagged feedback is written. This is
    # the schema-light alternative to the full "dual rows per ISIN" TD1 design
    # (which would break the single-doc-per-ISIN invariant + the partial
    # unique index + the watchlist upsert-on-{isin}). Watchlist writes never
    # touch this field (a watchlist entry is not a buy/sell decision). NOTE:
    # the sibling cosmetic leak in explainability._build_user_action (a stale
    # user_action badge can show on both a buy and a sell card for the same
    # ISIN) is KNOWINGLY left unfixed here — it is gated to feedback at/after
    # run start and the current UI does not send feedback direction, so it
    # cannot manifest in practice today.
    feedback_direction: FeedbackDirection | None = None

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
    # TD1/#43: the side of the book this feedback is for (from the feedback
    # request's `direction`, default "buy"). Always set by submit_feedback so
    # future exclusions are direction-scoped; kept as a plain str field here
    # (not optional) because the writer always supplies it going forward.
    feedback_direction: FeedbackDirection = "buy"


class MonitoredStockWatchlistPatch(BaseModel):
    """Typed shape of the $set patch written by the /watchlist CRUD path (F13).

    Mirrors MonitoredStockFeedbackPatch: constructing this model at write
    time catches Literal drift (status, alert_on) loudly instead of letting
    the schema silently rot. The field set MUST match what the /watchlist
    router's $set block writes -- if you add a field there, add it here too,
    and vice versa.

    status is pinned to "watchlist". The router upserts on {isin} with the
    identity seeds (added_by / added_at / created_at / symbol / name) in
    $setOnInsert, so this patch carries only the mutable watchlist fields.

    Caller pattern:
        patch = MonitoredStockWatchlistPatch(...)
        set_doc = patch.model_dump(exclude_none=True)
        Collections.monitored_stocks().update_one(
            {"isin": isin},
            {"$set": set_doc, "$setOnInsert": {...identity seeds...}},
            upsert=True,
        )

    exclude_none=True is intentional: optional price/alert/tag fields left
    unset by the caller must not overwrite existing values on a re-PUT. The
    router passes through only the fields the client actually supplied.
    """

    model_config = ConfigDict(extra="forbid")

    isin: str = Field(..., min_length=12, max_length=12, pattern=r"^[A-Z0-9]{12}$")
    status: Literal["watchlist"] = "watchlist"
    target_buy_price: Money | None = None
    alert_above: Money | None = None
    alert_below: Money | None = None
    alert_on: list[AlertOn] | None = None
    tags: list[str] | None = None
    user_notes: str | None = None
    thesis: str | None = None
    conviction: float | None = Field(default=None, ge=0, le=1)
    last_user_interest_at: datetime | None = None
    updated_at: datetime
