"""Outcome tracking for past suggestions.

Daily cron snapshots prices for all open suggestions and computes excess
return vs an equal-weighted NIFTY 100 benchmark at 30/60/90/180-day windows.

Note: the SuggestionOutcome.nifty_at_* fields hold the EW NIFTY 100 RETURN
(percent) for the matching window, not a price. We treat the synthetic
benchmark as a single number per window per outcome.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any

from bson import Decimal128, ObjectId

from app.db.client import Collections
from app.models._common import utcnow
from app.models.suggestion import SuggestionOutcome

log = logging.getLogger(__name__)

WINDOWS_DAYS = [30, 60, 90, 180]
EXPIRY_DAYS = 180


def _dec(v: Any) -> Decimal | None:
    if v is None:
        return None
    if isinstance(v, Decimal128):
        return v.to_decimal()
    if isinstance(v, Decimal):
        return v
    try:
        return Decimal(str(v))
    except Exception:
        return None


def _flt(v: Any) -> float | None:
    d = _dec(v)
    return float(d) if d is not None else None


def create_outcomes_for_run(
    run_id: ObjectId, run_date: datetime, top_candidates: list
) -> int:
    """Create SuggestionOutcome records for each top-K candidate at run time.

    Idempotent: skips if an outcome already exists for this (isin, run_id).
    """
    coll = Collections.suggestion_outcomes()
    now = utcnow()
    created = 0

    for c in top_candidates:
        if coll.find_one({"isin": c.isin, "suggestion_run_id": run_id}):
            continue

        suggested_price = (
            c.current_price if c.current_price is not None else Decimal("0")
        )
        outcome = SuggestionOutcome(
            isin=c.isin,
            symbol=c.symbol,
            suggestion_run_id=run_id,
            suggested_at=run_date,
            suggested_at_price=suggested_price,
            suggested_rank=c.rank,
            suggested_composite_score=c.composite_score,
            tracking_status="open",
            created_at=now,
            updated_at=now,
        )
        doc = outcome.to_mongo()
        doc["suggestion_run_id"] = run_id  # ensure it's not coerced to None
        coll.insert_one(doc)
        created += 1

    log.info("Created %d new outcome records for run", created)
    return created


def _compute_nifty100_ew_return(
    isins: list[str],
    from_date: datetime,
    to_date: datetime,
) -> float | None:
    """Equal-weighted NIFTY 100 return between two dates (percent)."""
    returns: list[float] = []
    for isin in isins:
        history_from = list(
            Collections.prices_daily()
            .find(
                {"isin": isin, "date": {"$lte": from_date}},
                {"close": 1, "date": 1},
            )
            .sort("date", -1)
            .limit(1)
        )
        history_to = list(
            Collections.prices_daily()
            .find(
                {"isin": isin, "date": {"$lte": to_date}},
                {"close": 1, "date": 1},
            )
            .sort("date", -1)
            .limit(1)
        )

        if not history_from or not history_to:
            continue

        p_from = _flt(history_from[0]["close"])
        p_to = _flt(history_to[0]["close"])
        if p_from is None or p_to is None or p_from <= 0:
            continue

        returns.append((p_to / p_from - 1) * 100)

    if not returns:
        return None
    return sum(returns) / len(returns)


def snapshot_open_outcomes() -> dict:
    """Daily cron: for each open outcome, snapshot prices at the relevant windows."""
    now = datetime.now(timezone.utc)
    coll = Collections.suggestion_outcomes()

    open_outcomes = list(coll.find({"tracking_status": "open"}))

    nifty100_isins = [
        d["isin"]
        for d in Collections.instruments().find(
            {"in_nifty100": True},
            {"_id": 0, "isin": 1},
        )
    ]

    stats = {
        "open_outcomes": len(open_outcomes),
        "snapshots_30d": 0,
        "snapshots_60d": 0,
        "snapshots_90d": 0,
        "snapshots_180d": 0,
        "expired": 0,
    }

    for outcome in open_outcomes:
        suggested_at = outcome["suggested_at"]
        if suggested_at.tzinfo is None:
            suggested_at = suggested_at.replace(tzinfo=timezone.utc)

        days_since = (now - suggested_at).days
        updates: dict[str, Any] = {"updated_at": utcnow()}

        for window_days in WINDOWS_DAYS:
            field_name = f"price_at_{window_days}d"
            nifty_field = f"nifty_at_{window_days}d"
            excess_field = f"excess_return_{window_days}d"

            if outcome.get(field_name) is not None:
                continue
            if days_since < window_days:
                continue

            target_date = suggested_at + timedelta(days=window_days)
            price_at = list(
                Collections.prices_daily()
                .find(
                    {"isin": outcome["isin"], "date": {"$lte": target_date}},
                    {"close": 1, "date": 1},
                )
                .sort("date", -1)
                .limit(1)
            )
            if not price_at:
                continue
            stock_price = _dec(price_at[0]["close"])
            if stock_price is None:
                continue
            updates[field_name] = Decimal128(str(stock_price))

            nifty_ret = _compute_nifty100_ew_return(
                nifty100_isins,
                suggested_at,
                target_date,
            )
            if nifty_ret is not None:
                updates[nifty_field] = Decimal128(str(round(nifty_ret, 4)))

            suggested_price = _flt(outcome.get("suggested_at_price"))
            if suggested_price and suggested_price > 0:
                stock_ret = (float(stock_price) / suggested_price - 1) * 100
                if nifty_ret is not None:
                    updates[excess_field] = round(stock_ret - nifty_ret, 4)

            stats[f"snapshots_{window_days}d"] += 1

        if days_since >= EXPIRY_DAYS and outcome["tracking_status"] == "open":
            updates["tracking_status"] = "expired"
            stats["expired"] += 1

        if len(updates) > 1:
            coll.update_one({"_id": outcome["_id"]}, {"$set": updates})

    log.info(
        "Outcome snapshot complete: %d open, snapshots 30d=%d 60d=%d 90d=%d 180d=%d, expired=%d",
        stats["open_outcomes"],
        stats["snapshots_30d"],
        stats["snapshots_60d"],
        stats["snapshots_90d"],
        stats["snapshots_180d"],
        stats["expired"],
    )
    return stats


def compute_system_performance() -> dict:
    """Aggregate performance metrics across all tracked outcomes."""
    coll = Collections.suggestion_outcomes()

    result: dict[str, Any] = {
        "windows": {},
        "total_outcomes_tracked": coll.count_documents({}),
        "open": coll.count_documents({"tracking_status": "open"}),
        "acted": coll.count_documents({"tracking_status": "acted"}),
        "passed": coll.count_documents({"tracking_status": "passed"}),
        "expired": coll.count_documents({"tracking_status": "expired"}),
    }

    for window_days in WINDOWS_DAYS:
        excess_field = f"excess_return_{window_days}d"
        nifty_field = f"nifty_at_{window_days}d"
        price_field = f"price_at_{window_days}d"

        cursor = coll.find(
            {excess_field: {"$exists": True, "$ne": None}},
            {
                "suggested_at_price": 1,
                price_field: 1,
                nifty_field: 1,
                excess_field: 1,
                "symbol": 1,
            },
        )
        excess_returns: list[float] = []
        stock_returns: list[float] = []
        nifty_returns: list[float] = []

        for o in cursor:
            ex = _flt(o.get(excess_field))
            if ex is not None:
                excess_returns.append(ex)
            sp = _flt(o.get("suggested_at_price"))
            pp = _flt(o.get(price_field))
            if sp and pp and sp > 0:
                stock_returns.append((pp / sp - 1) * 100)
            nr = _flt(o.get(nifty_field))
            if nr is not None:
                nifty_returns.append(nr)

        n = len(excess_returns)
        result["windows"][f"{window_days}d"] = {
            "samples": n,
            "avg_excess_return_pct": round(sum(excess_returns) / n, 2) if n else None,
            "avg_stock_return_pct": round(sum(stock_returns) / len(stock_returns), 2)
            if stock_returns
            else None,
            "avg_nifty_return_pct": round(sum(nifty_returns) / len(nifty_returns), 2)
            if nifty_returns
            else None,
            "win_rate_pct": round(sum(1 for r in excess_returns if r > 0) / n * 100, 1)
            if n
            else None,
        }

    return result
