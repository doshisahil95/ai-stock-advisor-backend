"""Suggestion run + outcome tracking models.

A `SuggestionRun` is one full execution of the weekly cron. It contains:
  - The full universe considered
  - Per-stock gate results (which gates passed/failed)
  - Per-stock scoring breakdown (raw signals, normalized scores, composite)
  - The top-K candidates with full per-signal context

A `SuggestionOutcome` is created when a suggestion is acted on or expires
(180d after suggestion). Tracks price-at-suggestion vs price-now and the
spread vs Nifty over 30/60/90/180-day windows.

These collections are append-only. Re-running the same week's cron creates
a new SuggestionRun rather than updating the existing one (so we never
lose history of what was suggested and why).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models._common import BaseDoc, Money, PyObjectId, utcnow

SuggestionRunStatus = Literal["running", "success", "partial", "failed"]
SuggestionTrackingStatus = Literal["open", "acted", "passed", "expired"]


class GateResult(BaseModel):
    """Result of one quality gate for one candidate."""

    model_config = ConfigDict(extra="forbid")

    gate_name: str
    passed: bool
    threshold: str = ""  # e.g. "ROE >= 10%"
    actual_value: str = ""  # e.g. "ROE = 14.2%"
    skipped: bool = False  # True if input data was missing
    skip_reason: str = ""


class SignalScore(BaseModel):
    """One signal's contribution to the composite score."""

    model_config = ConfigDict(extra="forbid")

    signal_name: str
    raw_value: str = ""  # Stringified for safety (Money/None/etc.)
    normalized_score: float  # 0-100, post-normalization
    weight: float  # Group weight contribution (0-1)
    available: bool = True  # False if input data was missing


class CandidateScore(BaseModel):
    """A candidate's full scoring breakdown.

    This is what the dossier (Unit 2) and the UI (Unit 3) read from.
    """

    model_config = ConfigDict(extra="forbid")

    isin: str
    symbol: str
    name: str
    sector: str

    # Final score
    composite_score: float  # 0-100
    rank: int  # Within this run, 1 = best

    # Confidence (deterministic, not LLM-derived)
    confidence_score: float  # 0-100
    confidence_deductions: list[str] = Field(
        default_factory=list,
        description="Reasons the confidence score was below 100",
    )

    # Per-group breakdown
    quality_score: float = 0.0
    valuation_score: float = 0.0
    momentum_score: float = 0.0
    news_score: float = 0.0  # Always 0 in Unit 1 (no news yet)

    # Per-signal breakdown
    signals: list[SignalScore] = Field(default_factory=list)

    # Gates
    gates: list[GateResult] = Field(default_factory=list)
    gates_passed: int = 0
    gates_failed: int = 0
    gates_skipped: int = 0

    # Snapshot of inputs at scoring time
    fundamentals_fetched_at: datetime | None = None
    price_as_of: datetime | None = None
    current_price: Money | None = None


class SuggestionRun(BaseDoc):
    """One full execution of the weekly suggestions cron."""

    id: PyObjectId | None = Field(default=None, alias="_id")

    # Run identity
    run_date: datetime = Field(default_factory=utcnow, description="UTC start time")
    run_date_ist: str = Field(..., description="YYYY-MM-DD in IST, used for de-dup")
    run_type: Literal["scheduled", "manual", "dry_run"] = "manual"

    # Status
    status: SuggestionRunStatus = "running"
    started_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime | None = None
    error: str = ""

    # Universe + filtering
    universe_size: int = 0  # NIFTY 100 count
    excluded_held: int = 0  # Stocks dropped because already held
    excluded_rejected: int = 0  # Stocks dropped because user-rejected (90d)
    excluded_acted: int = 0  # F5b: acted-but-not-held soft-exclude (30d)
    excluded_stale_data: int = 0  # Dropped because fundamentals/prices stale
    candidates_considered: int = 0  # Universe - all exclusions
    candidates_post_gates: int = 0  # Survivors after quality gates

    # Configuration snapshot (so re-runs are reproducible)
    config: dict = Field(
        default_factory=dict,
        description="Frozen scoring config (weights, thresholds) for this run",
    )

    # Results
    top_candidates: list[CandidateScore] = Field(default_factory=list)
    all_candidates: list[CandidateScore] = Field(
        default_factory=list,
        description="Full ranked list including those below top-K cutoff",
    )

    # Run-level metadata
    top_k: int = 10
    notes: str = ""


class SuggestionOutcome(BaseDoc):
    """Tracking record for one suggestion across its lifecycle."""

    id: PyObjectId | None = Field(default=None, alias="_id")

    # Identity
    isin: str = Field(..., min_length=12, max_length=12)
    symbol: str
    suggestion_run_id: PyObjectId
    suggested_at: datetime
    suggested_at_price: Money
    suggested_rank: int
    suggested_composite_score: float

    # User action
    tracking_status: SuggestionTrackingStatus = "open"
    user_action_at: datetime | None = None
    user_action_note: str = ""

    # Outcome snapshots (filled by daily outcome cron)
    price_at_30d: Money | None = None
    price_at_60d: Money | None = None
    price_at_90d: Money | None = None
    price_at_180d: Money | None = None

    # Comparison vs Nifty 50
    nifty_at_suggestion: Money | None = None
    nifty_at_30d: Money | None = None
    nifty_at_60d: Money | None = None
    nifty_at_90d: Money | None = None
    nifty_at_180d: Money | None = None

    # Computed return (stock - Nifty) at each window — convenience fields
    excess_return_30d: float | None = None
    excess_return_60d: float | None = None
    excess_return_90d: float | None = None
    excess_return_180d: float | None = None

    # Audit
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
