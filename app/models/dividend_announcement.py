"""Dividend announcement captured from yfinance corporate actions (master_todo #65).

One doc per (isin, ex_date). Source = yfinance Ticker.dividends, refreshed
weekly alongside fundamentals + earnings (same universe, same cron). Mirrors
the earnings_calendar model/refresh pattern exactly (see earnings_event.py) —
this is the "announced" leg of the #65 dividend-drift matrix (announced vs
received vs booked).

Purpose: a dividend is a real gain even though it is not taxable as a capital
gain (it feeds totals.total_dividends_lifetime / total_realized_with_dividends
via #63/#64). If a payout is announced and its ex-date passes while we hold the
stock but no DIVIDEND transaction is ever recorded, our realised-gain figure is
silently understated. This collection is the automated "announced" truth the
reconciliation drift matrix (#65) compares the recorded DIVIDEND rows against.

NOT a tax artifact: dividends stay out of /tax capital-gains (compliance,
mirrors the #63/#64 decision). This is decision-support / reconciliation only.

Refresh semantics (see refresh_dividends_for in fundamentals_service):
  - Each weekly refresh REPLACES the recent-window announcements for the ISIN
    (delete ex_date >= a lookback floor, then upsert the fresh list) so a
    corrected/withdrawn dividend does not linger. Older history is kept.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models._common import Money, utcnow


class DividendAnnouncement(BaseModel):
    """One announced cash dividend for one ISIN, keyed by ex-date."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    isin: str = Field(..., min_length=12, max_length=12, pattern=r"^[A-Z0-9]{12}$")
    symbol: str = Field(..., description="Trading symbol (e.g., 'INFY')")
    exchange: str = Field(default="NSE", pattern=r"^(NSE|BSE)$")

    ex_date: datetime = Field(
        ...,
        description=(
            "Ex-dividend date from yfinance Ticker.dividends index. Stored "
            "tz-naive (Mongo invariant); yfinance returns a Timestamp we coerce "
            "to a naive datetime. This is the key axis for the drift match: a "
            "holder on the ex-date is entitled to the payout."
        ),
    )
    amount_per_share: Money = Field(
        ...,
        description="Announced cash dividend per share (INR), from yfinance.",
    )

    source: str = Field(default="yfinance")
    fetched_at: datetime = Field(
        default_factory=utcnow,
        description="When this row was last (re-)fetched from the provider.",
    )
    created_at: datetime = Field(default_factory=utcnow)
