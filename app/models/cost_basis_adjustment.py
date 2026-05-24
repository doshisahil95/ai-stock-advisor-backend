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
  "related_isins": ["INE155A01022"],             # other ISINs touched (e.g.
parent)
  "amount": Decimal128("-24244.83"),             # signed: our_invested - broker_invested
  "it_act_section": "Section 49(2C)",
  "effective_date": ISODate("2025-10-01"),
  "calculation": "TMPV original cost ₹81,337 split: 68.85% to TMPV (kept) + 31.15% to TMCV (new).
ICICI didn't apply this split, so their 'invested' over-counts by ₹24,244.83.",
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

from pydantic import BaseModel, ConfigDict, Field

from app.models._common import Money, PyObjectId


class CostBasisAdjustment(BaseModel):
    """One IT-Act-driven cost basis divergence vs broker.

    Chat 5.5+:
      F18: amount uses Money alias so Decimal128 round-trips via model_validate.
      F19: schema_version uses BaseDoc-style alias so it actually persists.
      Also added id/_id alias defensively (model previously had no _id field).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    id: PyObjectId | None = Field(default=None, alias="_id")

    name: str  # "TMPV/TMCV demerger Oct 2025"
    isin: str | None = None  # primary ISIN affected
    related_isins: list[str] = Field(default_factory=list)
    # F18 fix (Chat 5.5+): Money alias coerces Decimal128 -> Decimal on model_validate.
    # Pre-fix bare Decimal would TypeError on Mongo round-trip. No current consumer
    # triggers this (cost_basis_service uses raw find/dicts), but the model was
    # structurally broken for any future user.
    amount: Money  # signed: our_invested - broker_invested
    it_act_section: str  # "Section 49(2C)"
    effective_date: datetime
    calculation: str  # plain-English math
    broker_treatment: str  # what the broker shows
    our_treatment: str  # what we do
    rationale: str  # why our way is correct
    source_documents: list[str] = Field(default_factory=list)
    active: bool = True

    # F19 fix (Chat 5.5+): _schema_version with leading underscore was silently
    # treated as private attribute in Pydantic v2 — never written via model_dump.
    # BaseDoc pattern: regular field with alias.
    schema_version: int = Field(default=1, alias="_schema_version")
