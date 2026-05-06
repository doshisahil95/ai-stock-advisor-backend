"""Cost-basis adjustment model.

Each document represents one IT-Act-driven divergence between the broker's
nominal cost basis (what ICICI/Zerodha shows as "invested") and our tax-correct
cost basis (what your CA needs for capital-gains computation).

Examples:
- Section 49(2C): cost basis split on demerger (TMPV → TMPV + TMCV)
- Section 55(2)(b)(v): cost basis on bonus shares (zero, by IT Act)
- Section 47(vid): cost preservation on spin-offs

Storage shape:
{
    "_id": ObjectId,
    "name": "TMPV/TMCV demerger Oct 2025",        # human-readable label
    "isin": "INE1TAE01010",                        # primary ISIN affected (optional)
    "related_isins": ["INE155A01022"],             # other ISINs touched (e.g. parent)
    "amount": Decimal128("-24244.83"),             # signed: our_invested - broker_invested
    "it_act_section": "Section 49(2C)",
    "effective_date": ISODate("2025-10-01"),
    "calculation": "TMPV original cost ₹81,337 split: 68.85% to TMPV (kept) + 31.15% to TMCV (new). ICICI didn't apply this split, so their 'invested' over-counts by ₹24,244.83.",
    "broker_treatment": "ICICI continues to show ₹81,337 against TMPV alone, ignoring TMCV.",
    "our_treatment": "TMPV transactions adjusted by ×0.6885; TMCV created with cost basis 31.15% of original.",
    "rationale": "Section 49(2C) requires cost apportionment in proportion to net book value at the date of demerger.",
    "source_documents": ["Tata Motors PIB notice 12-Sep-2025", "ICICI demat statement 02-Oct-2025"],
    "active": true,
    "created_at": ISODate(...),
    "updated_at": ISODate(...),
}
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CostBasisAdjustment(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str  # "TMPV/TMCV demerger Oct 2025"
    isin: str | None = None  # primary ISIN affected
    related_isins: list[str] = Field(default_factory=list)
    amount: Decimal  # signed: our_invested - broker_invested
    it_act_section: str  # "Section 49(2C)"
    effective_date: datetime
    calculation: str  # plain-English math
    broker_treatment: str  # what the broker shows
    our_treatment: str  # what we do
    rationale: str  # why our way is correct
    source_documents: list[str] = Field(default_factory=list)
    active: bool = True

    _schema_version: int = 1
