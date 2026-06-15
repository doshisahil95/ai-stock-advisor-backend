"""Shared model helpers: Decimal128 bridging, base config, common fields."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Any

from bson import Decimal128, ObjectId
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, PlainSerializer


# ── Decimal128 ↔ Decimal bridge ─────────────────────────────────────────────
def _to_decimal(v: Any) -> Decimal:
    if isinstance(v, Decimal):
        return v
    if isinstance(v, Decimal128):
        return v.to_decimal()
    if isinstance(v, (str, int)):
        return Decimal(v)
    if isinstance(v, float):
        if v != v:  # NaN is the only float not equal to itself
            raise ValueError("NaN not allowed")
        return Decimal(str(v))

    raise TypeError(f"Cannot convert {type(v).__name__} to Decimal")


Money = Annotated[
    Decimal,
    BeforeValidator(_to_decimal),
]


# ── ObjectId helper ──────────────────────────────────────────────────────────
def _to_object_id(v: Any) -> ObjectId:
    if isinstance(v, ObjectId):
        return v
    if isinstance(v, str) and ObjectId.is_valid(v):
        return ObjectId(v)
    raise TypeError(f"Invalid ObjectId: {v!r}")


PyObjectId = Annotated[
    ObjectId,
    BeforeValidator(_to_object_id),
    PlainSerializer(lambda v: str(v), when_used="json"),
]


# ── Base model ───────────────────────────────────────────────────────────────
class BaseDoc(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
        extra="forbid",
    )

    schema_version: int = Field(default=1, alias="_schema_version")

    def to_mongo(self) -> dict:
        data = self.model_dump(by_alias=True, exclude_none=True)
        return _convert_decimals_to_decimal128(data)


def _convert_decimals_to_decimal128(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return Decimal128(obj)
    if isinstance(obj, dict):
        return {k: _convert_decimals_to_decimal128(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_decimals_to_decimal128(item) for item in obj]
    return obj


def utcnow() -> datetime:
    """UTC-naive datetime. Project invariant: Mongo stores naive UTC; Python uses naive UTC.
    pymongo strips tzinfo on write by default, so legacy callers that passed
    tz-aware values silently got naive in storage — fixing here so in-memory
    comparisons against Mongo reads (naive) don't TypeError.
    """
    return datetime.now(timezone.utc).replace(
        tzinfo=None
    )  # tz-ok: canonical naive-UTC helper (the one sanctioned aware-now source)
