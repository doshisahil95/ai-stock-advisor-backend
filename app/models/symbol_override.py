"""Maps non-standard broker symbols (e.g., ICICI internal codes) to NSE/BSE symbols."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models._common import PyObjectId, utcnow

BrokerSource = Literal["ICICI", "ZERODHA", "OTHER"]


class SymbolOverride(BaseModel):
    """Maps source_broker:source_symbol to a canonical (target_exchange, target_symbol)."""

    # F79 fix (Chat 5.5+): populate_by_name=True so model_validate accepts
    # the '_id' alias. Kept extra='forbid' for tight schema validation.
    model_config = ConfigDict(
        extra="forbid",
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    # F79 fix (Chat 5.5+): _id alias. Pre-fix extra='forbid' rejected _id
    # on any Mongo round-trip via model_validate.
    id: PyObjectId | None = Field(default=None, alias="_id")
    source_broker: BrokerSource = "ICICI"
    source_symbol: str = Field(..., description="Symbol as it appears in the source")
    target_exchange: str = Field(..., pattern=r"^(NSE|BSE)$")
    target_symbol: str = Field(..., description="Canonical NSE/BSE symbol")

    notes: str = ""
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
