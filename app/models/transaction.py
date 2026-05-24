"""Transaction — source of truth for all trades, dividends, and corporate actions."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    # F29 fix (Chat 5.5+): money fields ge=0 catches negatives (the actually
    # dangerous case — flips realized P&L sign in FIFO). Zero is allowed at the
    # field level because legitimate use cases exist:
    #   - BUY at price=0: bonus-share receipts (user's existing pattern; e.g.
    #     RELIANCE 1:1 bonus modeled as BUY qty=5 price=0)
    #   - SPLIT/BONUS/DEMERGER with qty=0 + price=0: corporate-action rows
    #     where meaning lives in `corporate_action.ratio_from/ratio_to`
    #     (e.g. TATASTEEL 1:10 split)
    #   - DIVIDEND with qty=0: _fifo_replay ignores tx.quantity for DIVIDEND
    #     (per-share payout × current_qty derived from lots)
    # The type-aware validator below additionally requires qty > 0 on BUY/SELL
    # so genuinely nonsense rows are still caught.
    quantity: Money = Field(..., ge=0, description="Always positive, even for SELL")
    price: Money = Field(..., ge=0)
    trade_date: datetime
    settlement_date: datetime | None = None
    # Costs (just total — no breakdown per our agreement)
    total_fees: Money = Field(default=Decimal("0"), ge=0)
    # Optional: for BONUS / SPLIT
    corporate_action: CorporateAction | None = None
    # Provenance
    source: Source = "manual"
    source_ref: str = Field(default="")
    notes: str = ""
    # FIFO accounting helper (only meaningful for BUY rows)
    remaining_quantity: Money | None = Field(
        default=None,
        ge=0,
        description="For BUY only: shares from this lot not yet sold (FIFO)",
    )
    # Audit
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    deleted_at: datetime | None = None

    @model_validator(mode="after")
    def _validate_trade_qty(self):
        """F29 (Chat 5.5+): zero-quantity BUY/SELL is nonsense and must reject.

        Why type-aware instead of a blanket `gt=0` on the field?
            BUY    — must have qty > 0 (real trade or bonus-share receipt).
                     Price may be 0 (bonus receipts).
            SELL   — must have qty > 0 (can't sell nothing).
            SPLIT  — qty/price ignored by _fifo_replay; meaning lives in
                     corporate_action.ratio_from/ratio_to.
            BONUS  — same as SPLIT (qty/price ignored; ratios drive replay).
            DEMERGER — qty/price unused.
            DIVIDEND — qty ignored; price = per-share payout × current_qty.

        Defense-in-depth: the API edge (AddBuyRequest, SellRequest) ALREADY
        enforces strict gt=0 on quantity/price (F14, shipped commit 4).
        The model-level rule here protects against future internal call
        sites that bypass the request models (e.g. background workers,
        scripts that go through Pydantic rather than raw insert_many).
        """
        if self.type in ("BUY", "SELL") and self.quantity == 0:
            raise ValueError(
                f"{self.type} must have quantity > 0 (got 0). "
                f"For corporate-action rows use SPLIT/BONUS/DEMERGER types "
                f"(those carry meaning in corporate_action ratios, not in qty)."
            )
        return self
