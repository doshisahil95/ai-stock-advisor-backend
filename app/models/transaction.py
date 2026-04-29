"""Transaction — source of truth for all trades, dividends, and corporate actions."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models._common import BaseDoc, Money, PyObjectId, utcnow

TransactionType = Literal["BUY", "SELL", "DIVIDEND", "BONUS", "SPLIT"]
Exchange = Literal["NSE", "BSE"]
Source = Literal["manual", "csv_import", "yfinance_corporate_action", "breeze_api"]


class CorporateAction(BaseModel):
    """Details for BONUS / SPLIT transactions."""

    model_config = ConfigDict(extra="forbid")

    ratio_from: int = Field(..., gt=0)
    ratio_to: int = Field(..., gt=0)
    notes: str = ""


class Transaction(BaseDoc):
    """A single trade, dividend payout, or corporate action.

    Holdings are derived from this collection; never edit holdings directly.
    """

    id: PyObjectId | None = Field(default=None, alias="_id")

    # Identity
    isin: str = Field(..., min_length=12, max_length=12, pattern=r"^[A-Z0-9]{12}$")
    symbol: str
    exchange: Exchange = "NSE"

    # Transaction details
    type: TransactionType
    quantity: Money = Field(..., description="Always positive, even for SELL")
    price: Money
    trade_date: datetime
    settlement_date: datetime | None = None

    # Costs (just total — no breakdown per our agreement)
    total_fees: Money = Field(default=Decimal("0"))

    # Optional: for BONUS / SPLIT
    corporate_action: CorporateAction | None = None

    # Provenance
    source: Source = "manual"
    source_ref: str = Field(default="")
    notes: str = ""

    # FIFO accounting helper (only meaningful for BUY rows)
    remaining_quantity: Money | None = Field(
        default=None,
        description="For BUY only: shares from this lot not yet sold (FIFO)",
    )

    # Audit
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    deleted_at: datetime | None = None
