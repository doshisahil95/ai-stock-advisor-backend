"""Transaction — source of truth for all trades, dividends, and corporate actions."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models._common import BaseDoc, Money, PyObjectId, utcnow

TransactionType = Literal["BUY", "SELL", "DIVIDEND", "BONUS", "SPLIT"]
Exchange = Literal["NSE", "BSE"]
# F80 fix (Chat 5.5+): added the three manual-prefixed source values that
# already exist in production data (per `db.transactions.distinct('source')`):
#   manual_corporate_action (5 rows): hand-recorded bonus/split events
#   manual_ipo_allotment    (3 rows): hand-recorded IPO allotment BUYs
#   manual_demerger         (2 rows): hand-recorded demerger receipt BUYs
#                                     (cost-basis transfer; type=BUY at price=0
#                                      or computed split-cost — see TMCV, JIOFIN)
# Pre-fix Transaction.model_validate(...) on any of these rows would
# raise on the Source literal. Read paths bypass via _serialize, so no
# active code path was crashing, but the model was structurally broken
# for any future model_validate consumer (and F29's validator test
# surfaced the gap during Batch 1 closure).
Source = Literal[
    "manual",
    "csv_import",
    "manual_corporate_action",
    "manual_ipo_allotment",
    "manual_demerger",
    "yfinance_corporate_action",
    "breeze_api",
]


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
    #   - SPLIT/BONUS with qty=0 + price=0: corporate-action rows where meaning
    #     lives in `corporate_action.ratio_from/ratio_to` (e.g. TATASTEEL 1:10).
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
    # F82 fix (Chat 5.5+): legitimate ICICI/broker reference fields written by
    # scripts/import_orderbooks.py but never declared on the model — caused
    # Transaction.model_validate(mongo_doc) to fail with extra_forbidden on
    # 72 / 108 historical csv_import rows. No live caller did model_validate
    # (read paths use _serialize), so this was latent, not a crash. Declared
    # here so model_validate now round-trips and API responses serialized via
    # the model expose these audit fields.
    settlement_ref: str = Field(
        default="",
        description="ICICI ZIP order/settlement reference (broker-side trace id)",
    )
    trade_value: Money | None = Field(
        default=None,
        ge=0,
        description="Broker-reported trade value (audit cache; may differ from "
        "qty*price by rounding/disclosure conventions). "
        "Not authoritative — FIFO uses qty + price + fees.",
    )
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
