"""Reconciliation service.

Two flows:
1. Manual snapshot: user enters ICICI numbers via UI/API → service computes
   deltas vs our system, compares to expected deltas, alerts if drift.
2. Automatic snapshot: daily cron captures our-side numbers only. Compares
   against the last manual snapshot to detect "we changed but ICICI didn't"
   (or vice-versa) drift over time.

Expected deltas are stored in user_profile.reconciliation_baseline; when the
user enters a manual snapshot that has zero drift, the deltas become the new
baseline.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.db.client import Collections
from app.services.notify import push_public, email
from app.services.portfolio_service import compute_summary
from app.services.price_service import bulk_get_latest_prices
from app.models._common import _convert_decimals_to_decimal128, utcnow

log = logging.getLogger(__name__)

# Drift over this absolute amount triggers an alert
# Invested is stable through the day — small threshold catches real drift
DRIFT_ALERT_THRESHOLD_INVESTED = Decimal("1000.00")
# Current value depends on live prices — only flag truly large deltas
# (e.g. missed corporate action causing wrong quantity)
DRIFT_ALERT_THRESHOLD_CURRENT_VALUE = Decimal("15000.00")


def _to_dec(v: Any) -> Decimal:
    if v is None:
        return Decimal("0")
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def _get_our_numbers() -> dict:
    """Snapshot our system's current invested / current / day_gain."""
    holdings = list(Collections.holdings().find({"deleted_at": None}))
    if not holdings:
        return {
            "our_invested": Decimal("0"),
            "our_current_value": Decimal("0"),
            "our_day_gain": Decimal("0"),
            "our_unrealized_pnl": Decimal("0"),
        }
    isins = [h["isin"] for h in holdings]
    latest_prices = bulk_get_latest_prices(isins)
    summary = compute_summary(holdings, latest_prices)
    totals = summary["totals"]
    return {
        "our_invested": _to_dec(totals["invested"]),
        "our_current_value": _to_dec(totals["current_value"]),
        "our_day_gain": _to_dec(totals["day_gain"]),
        "our_unrealized_pnl": _to_dec(totals["unrealized_pnl"]),
    }


def _get_expected_deltas() -> dict:
    """Read expected deltas from user_profile."""
    profile = Collections.user_profile().find_one({})
    if not profile:
        return {}
    baseline = profile.get("reconciliation_baseline") or {}
    return {
        "invested": _to_dec(baseline.get("expected_delta_invested", 0)),
        "current_value": _to_dec(baseline.get("expected_delta_current_value", 0)),
        "day_gain": _to_dec(baseline.get("expected_delta_day_gain", 0)),
        "explanation": baseline.get("explanation", ""),
        "set_at": baseline.get("set_at"),
    }


def take_auto_snapshot() -> dict:
    """Daily cron-driven snapshot: our-side only, no ICICI input.

    Compares against the last manual snapshot to detect drift. When our
    invested base has moved away from the last manual reconciliation point by
    more than DRIFT_ALERT_THRESHOLD_INVESTED, fire an ntfy push
    (master_todo #25).

    ntfy ONLY — email is intentionally skipped on this path. The manual
    snapshot path (_send_drift_alerts) keeps the dual ntfy+email transport
    because it is user-triggered and point-in-time; this auto snapshot runs
    every day, so an email on every drift day would be noise.

    Rising-edge: the push fires only when this snapshot has drift AND the most
    recent prior auto snapshot did not, so a standing divergence does not
    re-push on every daily run. Taking a fresh manual snapshot resets the
    comparison baseline, which re-arms the alert.

    Current-value drift is deliberately NOT alerted on the auto path: over a
    multi-day gap it is dominated by live-price movement (the same reason the
    manual path only treats a huge current-value delta as a wrong-quantity
    signal), so it would fire constantly.
    """
    our = _get_our_numbers()
    snapshot = {
        "taken_at": utcnow(),
        "type": "auto",
        **our,
        "_schema_version": 1,
    }

    # Compare to last manual snapshot
    last_manual = Collections.reconciliation_snapshots().find_one(
        {"type": "manual"}, sort=[("taken_at", -1)]
    )
    if last_manual:
        # Did our numbers change in a way that should also have changed ICICI?
        delta_invested_change = _to_dec(our["our_invested"]) - _to_dec(
            last_manual.get("our_invested")
        )
        drift_invested = abs(delta_invested_change)

        # Mongo strips tzinfo; restore it for safe subtraction.
        last_taken_at = last_manual["taken_at"]
        if last_taken_at.tzinfo is None:
            last_taken_at = last_taken_at.replace(tzinfo=timezone.utc)
        days_since = (
            datetime.now(timezone.utc) - last_taken_at
        ).days  # tz-ok: aware diff vs last_taken_at (coerced aware above)

        if drift_invested > Decimal("100") and days_since >= 14:
            snapshot["notes"] = (
                f"Auto snapshot: our_invested changed by ₹{delta_invested_change} "
                f"since last manual reconciliation {days_since} days ago. "
                f"Consider entering current ICICI numbers."
            )

        # master_todo #25: ntfy-only drift alert on the daily auto path.
        # Record the same drift/status fields the manual snapshot uses so the
        # reconciliation_snapshots collection stays consistent across flavors.
        has_drift = drift_invested > DRIFT_ALERT_THRESHOLD_INVESTED
        snapshot["drift_invested"] = drift_invested
        snapshot["has_drift"] = has_drift
        snapshot["alerts_sent"] = []

        # Rising-edge dedupe: only alert when drift NEWLY appears. The prior
        # auto snapshot's has_drift tells us whether we already alerted for
        # this episode; legacy auto docs lack the field (-> falsy -> first
        # post-deploy drift still alerts once).
        last_auto = Collections.reconciliation_snapshots().find_one(
            {"type": "auto"}, sort=[("taken_at", -1)]
        )
        already_alerting = bool(last_auto and last_auto.get("has_drift"))

        if has_drift and not already_alerting:
            snapshot["alerts_sent"] = _send_auto_drift_alert(
                drift_invested=drift_invested,
                delta_invested_change=delta_invested_change,
                days_since=days_since,
            )

    Collections.reconciliation_snapshots().insert_one(
        _convert_decimals_to_decimal128(snapshot)
    )
    return snapshot


def take_manual_snapshot(
    icici_invested: Decimal,
    icici_current_value: Decimal,
    icici_day_gain: Decimal | None = None,
    notes: str | None = None,
    set_as_baseline: bool = False,
) -> dict:
    """User-driven snapshot: capture both our + ICICI numbers, compute drift.

    If set_as_baseline=True, the computed deltas become the new expected baseline.
    Useful when you've manually reconciled and confirmed the difference is
    explained (e.g., a known corporate action mismatch).
    """
    our = _get_our_numbers()
    expected = _get_expected_deltas()

    # Compute actual deltas (our - icici)
    delta_invested = our["our_invested"] - _to_dec(icici_invested)
    delta_current = our["our_current_value"] - _to_dec(icici_current_value)
    delta_day_gain = (
        our["our_day_gain"] - _to_dec(icici_day_gain)
        if icici_day_gain is not None
        else None
    )

    # Compute drift (actual delta vs expected)
    # Drift detection — different rules per field:
    # - invested: stable through the day, baseline meaningful, low threshold
    # - current_value: live prices make baseline noisy; only alert on huge deltas
    #   (which would indicate a wrong quantity, e.g. missed corporate action)
    # - day_gain: intra-day timing noise dominates; never alert
    drift_invested = abs(delta_invested - expected.get("invested", Decimal("0")))
    drift_current = abs(delta_current)  # NO baseline subtraction — just absolute delta
    drift_day_gain = (
        abs(delta_day_gain - expected.get("day_gain", Decimal("0")))
        if delta_day_gain is not None
        else None
    )

    has_drift = (
        drift_invested > DRIFT_ALERT_THRESHOLD_INVESTED
        or drift_current > DRIFT_ALERT_THRESHOLD_CURRENT_VALUE
    )

    snapshot = {
        "taken_at": utcnow(),
        "type": "manual",
        **our,
        "icici_invested": _to_dec(icici_invested),
        "icici_current_value": _to_dec(icici_current_value),
        "icici_day_gain": _to_dec(icici_day_gain)
        if icici_day_gain is not None
        else None,
        "delta_invested": delta_invested,
        "delta_current_value": delta_current,
        "delta_day_gain": delta_day_gain,
        "drift_invested": drift_invested,
        "drift_current_value": drift_current,
        "drift_day_gain": drift_day_gain,
        "has_drift": has_drift,
        "notes": notes,
        "alerts_sent": [],
        "_schema_version": 1,
    }

    # If user wants to bake in this delta as the new baseline
    if set_as_baseline:
        # F23 fix (Chat 5.5+): pre-fix wrote float(delta_invested) into Mongo,
        # baking in IEEE-754 precision loss permanently. Every subsequent
        # reconciliation read it back via _to_dec(str(float)) and computed
        # drift = abs(delta - expected) — always paise-off on a rupee field,
        # producing spurious or suppressed drift alerts. Now wrap the whole
        # payload in _convert_decimals_to_decimal128 so the Decimal precision
        # round-trips exactly. Also switched datetime.now(timezone.utc) to
        # the project utcnow() helper (post-F1 returns tz-naive UTC, matching
        # the storage invariant).
        Collections.user_profile().update_one(
            {},
            {
                "$set": _convert_decimals_to_decimal128(
                    {
                        "reconciliation_baseline": {
                            "expected_delta_invested": delta_invested,
                            "explanation": notes or "Baseline accepted by user",
                            "set_at": utcnow(),
                        }
                    }
                )
            },
            upsert=True,
        )
        log.info(
            "Reconciliation baseline updated: invested=%s, current=%s",
            delta_invested,
            delta_current,
        )

    # Send alerts if there's drift
    if has_drift:
        alerts_sent = _send_drift_alerts(snapshot)
        snapshot["alerts_sent"] = alerts_sent

    Collections.reconciliation_snapshots().insert_one(
        _convert_decimals_to_decimal128(snapshot)
    )
    return snapshot


def _send_drift_alerts(snapshot: dict) -> list[str]:
    """Fire ntfy + email when drift is detected.

    Returns which channels succeeded."""
    sent = []
    drift_lines = []
    if snapshot.get("drift_invested", 0) > DRIFT_ALERT_THRESHOLD_INVESTED:
        drift_lines.append(
            f"Invested drift: ₹{snapshot['drift_invested']:,.2f} "
            f"(actual delta {snapshot['delta_invested']:+,.2f} vs expected baseline)"
        )
    if snapshot.get("drift_current_value", 0) > DRIFT_ALERT_THRESHOLD_CURRENT_VALUE:
        drift_lines.append(
            f"Current value off by ₹{snapshot['drift_current_value']:,.2f} "
            f"(may indicate wrong quantity from a missed corporate action)"
        )

    if not drift_lines:
        return sent

    body_text = (
        "Portfolio Advisor: reconciliation drift detected\n\n"
        + "\n".join(drift_lines)
        + "\n\nThis usually means a corporate action was applied on one side but not the other."
        + "\nReview at the dashboard's Reconciliation page."
    )
    body_html = (
        "<h3>Portfolio Advisor: reconciliation drift detected</h3>"
        + "<ul>"
        + "".join(f"<li>{line}</li>" for line in drift_lines)
        + "</ul>"
        + "<p>This usually means a corporate action was applied on one side but not the other.</p>"
        + "<p><a href='http://100.112.20.41:3000/reconciliation'>Review on dashboard</a></p>"
    )

    try:
        push_public(
            channel="price",  # reconciliation drift = portfolio impact = price channel
            title="Portfolio reconciliation drift",
            message=body_text,
            priority="high",
            tags=["warning", "money_with_wings"],
        )
        sent.append("ntfy")
    except Exception as exc:
        log.error("ntfy alert failed: %s", exc)

    # A2 part 2 (Chat 5): notify.email() swallows Resend exceptions and
    # returns {"ok": bool, "id": str|None, "error": str|None}. The old
    # raise-based try/except never fires after A2 part 1, so we must
    # branch on result["ok"] before appending to `sent`.
    # body_text (defined above for ntfy) doubles as the multipart/alternative
    # plain-text body so non-HTML mail clients render the alert too.
    result = email(
        subject="Portfolio reconciliation drift detected",
        html=body_html,
        text=body_text,
    )
    if result.get("ok"):
        sent.append("email")
        log.info("reconciliation drift email sent: id=%s", result.get("id"))
    else:
        log.error("email alert failed: %s", result.get("error"))

    return sent


def _send_auto_drift_alert(
    drift_invested: Decimal,
    delta_invested_change: Decimal,
    days_since: int,
) -> list[str]:
    """Fire an ntfy-only drift alert for the daily auto snapshot (master_todo #25).

    Mirrors the ntfy half of _send_drift_alerts but deliberately omits the
    email leg: the auto snapshot runs daily and email would be noise. Uses the
    same push_public("price") transport (reconciliation drift = portfolio
    impact = price channel). push_public raises on transport failure, so the
    call is guarded and the failure is logged, never propagated into the cron.

    Returns which channels succeeded (["ntfy"] or []), stored on the snapshot's
    alerts_sent field for parity with the manual path.
    """
    sent: list[str] = []
    body_text = (
        "Portfolio Advisor: reconciliation drift detected (auto snapshot)\n\n"
        f"Our invested base has moved ₹{delta_invested_change:+,.2f} "
        f"(|drift| ₹{drift_invested:,.2f}) since the last manual reconciliation "
        f"{days_since} days ago.\n\n"
        "This usually means a corporate action was applied on one side but not "
        "the other.\nRe-enter current ICICI numbers on the dashboard's "
        "Reconciliation page."
    )

    try:
        push_public(
            channel="price",  # reconciliation drift = portfolio impact = price channel
            title="Portfolio reconciliation drift (auto)",
            message=body_text,
            priority="high",
            tags=["warning", "money_with_wings"],
        )
        sent.append("ntfy")
    except Exception as exc:
        log.error("auto-snapshot drift ntfy alert failed: %s", exc)

    return sent


def get_latest_snapshot(snapshot_type: str | None = None) -> dict | None:
    """Get the most recent snapshot, optionally filtered by type ('manual' or 'auto')."""
    query = {}
    if snapshot_type:
        query["type"] = snapshot_type
    return Collections.reconciliation_snapshots().find_one(
        query, sort=[("taken_at", -1)]
    )


def get_snapshot_history(limit: int = 30) -> list[dict]:
    """Get last N snapshots, newest first."""
    return list(
        Collections.reconciliation_snapshots()
        .find({})
        .sort("taken_at", -1)
        .limit(limit)
    )
