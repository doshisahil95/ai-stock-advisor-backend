"""Audit log for transaction edits / deletes.

Append-only. Each edit or delete writes a doc capturing: which transaction,
when, the before-state, the after-state (or "deleted"), and the user's reason.

Used for:
- CA-facing audit trail (explains retroactive changes to realized P&L)
- Post-mortem when something looks off ("why did Apr-2024 realized P&L change?")
- Future regulatory / tax-time export
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from app.db.client import Collections
from app.models._common import _convert_decimals_to_decimal128, utcnow

AuditAction = Literal["edit", "delete"]


def log_change(
    transaction_id: str,
    isin: str,
    action: AuditAction,
    before: dict,
    after: dict | None,  # None for deletes
    reason: str | None = None,
) -> None:
    """Append a single audit entry. Caller is responsible for providing the
    pre-mutation `before` snapshot."""
    Collections.transactions_audit().insert_one(
        _convert_decimals_to_decimal128(
            {
                "transaction_id": transaction_id,
                "isin": isin,
                "action": action,
                "before": before,
                "after": after,
                "reason": reason or "",
                "changed_at": utcnow(),
                "_schema_version": 1,
            }
        )
    )


def get_audit_for_transaction(transaction_id: str) -> list[dict]:
    """All audit entries for one transaction, newest first."""
    return list(
        Collections.transactions_audit()
        .find({"transaction_id": transaction_id})
        .sort("changed_at", -1)
    )


def get_recent_audit(limit: int = 50) -> list[dict]:
    """Latest audit entries across the whole portfolio."""
    return list(
        Collections.transactions_audit().find({}).sort("changed_at", -1).limit(limit)
    )
