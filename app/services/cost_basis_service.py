"""Cost-basis adjustments service.

Reads from the cost_basis_adjustments collection.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from bson import Decimal128

from app.db.client import Collections


def _to_dec(v: Any) -> Decimal:
    if v is None:
        return Decimal("0")
    if isinstance(v, Decimal128):
        return v.to_decimal()
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def get_active_adjustments() -> list[dict]:
    """Return all active cost-basis adjustments, oldest first by effective_date."""
    return list(
        Collections.cost_basis_adjustments()
        .find({"active": True})
        .sort("effective_date", 1)
    )


def total_adjustment_amount() -> Decimal:
    """Sum of all active adjustments. Signed: negative means our_invested < broker_invested."""
    return sum(
        (_to_dec(adj.get("amount")) for adj in get_active_adjustments()),
        start=Decimal("0"),
    )
