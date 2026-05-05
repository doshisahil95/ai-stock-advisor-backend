"""Pydantic model for reconciliation snapshots.

Each snapshot captures both 'our' system numbers and (optionally) ICICI
broker numbers at the same point in time. Manual snapshots include ICICI
data; automatic daily snapshots include only our data.

Drift = (our_X - icici_X) - expected_delta_X
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExpectedDelta(BaseModel):
    """A known/expected difference between our system and ICICI."""

    field: Literal["invested", "current_value", "day_gain"]
    amount: Decimal  # signed: -24244.83 means our_invested = icici_invested - 24244.83
    reason: str  # "TMPV/TMCV demerger Oct 2025 — Section 49(2C) split"
    set_at: datetime


class ReconciliationSnapshot(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    taken_at: datetime
    type: Literal[
        "manual", "auto"
    ]  # manual = user entered ICICI numbers; auto = cron, our-side only

    # Our system's numbers (always present)
    our_invested: Decimal
    our_current_value: Decimal
    our_day_gain: Decimal | None = None
    our_unrealized_pnl: Decimal | None = None

    # ICICI numbers (only present on manual snapshots)
    icici_invested: Decimal | None = None
    icici_current_value: Decimal | None = None
    icici_day_gain: Decimal | None = None

    # Computed deltas (our - icici); only present when both sides are set
    delta_invested: Decimal | None = None
    delta_current_value: Decimal | None = None
    delta_day_gain: Decimal | None = None

    # Drift = abs(actual_delta - expected_delta); the alert trigger
    drift_invested: Decimal | None = None
    drift_current_value: Decimal | None = None
    drift_day_gain: Decimal | None = None

    # Status
    has_drift: bool = False  # convenience flag for queries
    alerts_sent: list[str] = Field(default_factory=list)  # ["ntfy", "email", "badge"]
    notes: str | None = None

    _schema_version: int = 1
