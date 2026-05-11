"""Fundamentals snapshot per instrument.

One doc per ISIN per refresh. Fundamentals refresh runs weekly (separate cron
from the suggestions run). Stored as a snapshot so we can audit what data the
scoring engine saw at the time of any past suggestion run.

Source: yfinance for v1. Designed behind a provider interface so we can swap
to Tijori or another paid source later without changing the consumer code.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.models._common import BaseDoc, Money, PyObjectId, utcnow


class InstrumentFundamentals(BaseDoc):
    """Fundamentals snapshot for one instrument.

    All numeric fields are optional because yfinance coverage is patchy.
    The scoring engine handles missing fields by skipping the dependent
    signal and logging it (visible in confidence_score deductions).
    """

    id: PyObjectId | None = Field(default=None, alias="_id")

    # Identity
    isin: str = Field(..., min_length=12, max_length=12, pattern=r"^[A-Z0-9]{12}$")
    symbol: str
    exchange: str = "NSE"

    # Identity / classification
    name: str = Field(default="")
    sector: str = Field(default="")  # yfinance "sector" (broad, e.g. "Technology")
    industry: str = Field(default="")  # yfinance "industry" (narrower)

    # Valuation
    market_cap: Money | None = Field(
        default=None, description="In INR (rupees, not crores)"
    )
    pe_ratio: Money | None = Field(default=None, description="Trailing P/E")
    pe_forward: Money | None = Field(default=None, description="Forward P/E")
    pb_ratio: Money | None = Field(default=None, description="Price/Book")
    peg_ratio: Money | None = Field(default=None, description="P/E to growth")
    dividend_yield: Money | None = Field(
        default=None, description="As decimal e.g. 0.025 = 2.5%"
    )

    # Quality
    return_on_equity: Money | None = Field(
        default=None, description="As decimal e.g. 0.18 = 18%"
    )
    return_on_assets: Money | None = Field(default=None, description="As decimal")
    debt_to_equity: Money | None = Field(default=None, description="Total D/E ratio")
    profit_margin: Money | None = Field(
        default=None, description="Net margin as decimal"
    )
    operating_margin: Money | None = Field(
        default=None, description="Op margin as decimal"
    )

    # Growth
    earnings_growth_yoy: Money | None = Field(default=None, description="As decimal")
    revenue_growth_yoy: Money | None = Field(default=None, description="As decimal")

    # Risk
    beta: Money | None = Field(default=None, description="vs market index")

    # Price context (snapshot at fetch time)
    current_price: Money | None = None
    fifty_two_week_high: Money | None = None
    fifty_two_week_low: Money | None = None

    # Provenance
    source: str = Field(
        default="yfinance", description="Which provider returned this snapshot"
    )
    source_raw: dict = Field(
        default_factory=dict, description="Raw provider response, for debugging"
    )
    fields_present: list[str] = Field(
        default_factory=list, description="Names of fields that had values"
    )
    fields_missing: list[str] = Field(
        default_factory=list, description="Names of fields that were None/missing"
    )

    # Audit
    fetched_at: datetime = Field(default_factory=utcnow)
    created_at: datetime = Field(default_factory=utcnow)
