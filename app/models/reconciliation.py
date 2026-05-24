"""Pydantic model for reconciliation snapshots.

Each snapshot captures both 'our' system numbers and (optionally) ICICI
broker numbers at the same point in time.

Manual snapshots include ICICI
data; automatic daily snapshots include only our data.

Drift = (our_X - icici_X) - expected_delta_X
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models._common import Money, PyObjectId


class ExpectedDelta(BaseModel):
    """A known/expected difference between our system and ICICI.

    NOTE (Chat 5.5+): This class is currently NOT referenced from
    `ReconciliationSnapshot` (it's effectively dead code as of HEAD).
    Fixing the Money/schema_version pattern here regardless so that
    if/when a future caller wires it in, it can round-trip cleanly
    against Mongo. Removal is a separate cleanup decision.
    """

    # F16 fix (Chat 5.5+): Money alias coerces Decimal128 -> Decimal on
    # model_validate(mongo_doc). Pre-fix bare Decimal would TypeError.
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    field: Literal["invested", "current_value", "day_gain"]
    amount: Money  # signed: -24244.83 means our_invested = icici_invested - 24244.83
    reason: str  # "TMPV/TMCV demerger Oct 2025 — Section 49(2C) split"
    set_at: datetime


class ReconciliationSnapshot(BaseModel):
    """One reconciliation comparison snapshot.

    Two flavors:
      - type="auto": daily cron, our-side only (icici_* and delta_* are None)
      - type="manual": user-triggered, includes ICICI numbers + delta + drift

    Document shape evolved (Chat 5.5+):
      F16: All money fields now use `Money` alias for Decimal128<->Decimal coercion.
      F17: schema_version uses the BaseDoc-style alias so it actually persists.
      Also added id/_id alias defensively so a future model_validate(mongo_doc)
        round-trips cleanly. populate_by_name=True so construction with either
        `schema_version=` or `_schema_version=` works.

    Pre-fix bugs (now fixed):
      - bare Decimal field types meant model_validate(mongo_doc) raised on
        every historical row (Decimal128 doesn't auto-coerce to Decimal in
        Pydantic v2). No current consumer triggers this — read paths bypass
        via _serialize(dict) — but the model was structurally broken for any
        future use.
      - `_schema_version: int = 1` was silently treated as a private attribute
        in Pydantic v2 (leading underscore on a regular field). model_dump
        never emitted it, so every persisted reconciliation_snapshots doc
        lacks the version marker; future schema migrations had nothing to key
        off of. Switched to the BaseDoc pattern.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    id: PyObjectId | None = Field(default=None, alias="_id")

    taken_at: datetime
    type: Literal["manual", "auto"]  # manual = user entered ICICI numbers; auto = cron

    # Our system's numbers (always present)
    our_invested: Money
    our_current_value: Money
    our_day_gain: Money | None = None
    our_unrealized_pnl: Money | None = None

    # ICICI numbers (only present on manual snapshots)
    icici_invested: Money | None = None
    icici_current_value: Money | None = None
    icici_day_gain: Money | None = None

    # Computed deltas (our - icici); only present when both sides are set
    delta_invested: Money | None = None
    delta_current_value: Money | None = None
    delta_day_gain: Money | None = None

    # Drift = abs(actual_delta - expected_delta); the alert trigger
    drift_invested: Money | None = None
    drift_current_value: Money | None = None
    drift_day_gain: Money | None = None

    # Status
    has_drift: bool = False  # convenience flag for queries
    alerts_sent: list[str] = Field(default_factory=list)  # ["ntfy", "email", "badge"]
    notes: str | None = None

    schema_version: int = Field(default=1, alias="_schema_version")
