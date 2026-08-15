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
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from app.db.client import Collections
from app.services.fundamentals_service import get_dividend_announcements_for_isin
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


# ─────────────────────────────────────────────────────────────────────
# #65: Dividend-drift matrix (announced vs received vs booked)
#
# A dividend is a real gain (feeds total_dividends_* via #63/#64) even though
# it is not a taxable capital gain. If a payout is announced (captured from
# yfinance into dividend_announcements by refresh_fundamentals) and its ex-date
# passes while we hold the stock, but no DIVIDEND transaction is ever recorded,
# our realised-gain figure is silently understated. This matrix flags that so
# the user can record the missing DIVIDEND row.
#
# Design (mirrors take_auto_snapshot's compute/alert split):
#   - compute_dividend_drift() is a PURE read (no writes, no alerts) so it is
#     hermetically testable and safe to call from the endpoint on every render.
#   - evaluate_dividend_drift_alerts() is the separate ntfy-only nudge, rising-
#     edge deduped via a marker doc in reconciliation_snapshots (mirrors
#     _send_auto_drift_alert: ntfy-only on the price channel, no alerts_log
#     Alert, no new AlertType).
#
# "Held on ex-date" heuristic: currently held (holdings deleted_at=None,
# quantity>0) AND first_purchased_at <= ex_date. Precise point-in-time FIFO
# reconstruction is deliberately out of scope for round 1 — the case that
# matters is a missed dividend on a stock we still own. Fully-exited positions
# are historical and not a live decision.
#
# NOT a tax artifact: dividends stay out of /tax capital-gains (compliance).
# ─────────────────────────────────────────────────────────────────────

# A recorded DIVIDEND transaction is matched to an announced ex-date if its
# trade_date falls within this many days of the ex_date. In India a dividend is
# typically credited 2-6 weeks after the ex-date and the user records it on the
# credit/record date, not the ex-date — so we match on a generous date window,
# not an exact timestamp.
_DIVIDEND_MATCH_WINDOW_DAYS = 21

# #80 L5: a recorded DIVIDEND may sit at most this many days BEFORE the ex-date
# and still match (pure data-entry slack). Beyond this, a pre-ex-date txn belongs
# to an earlier announcement and must NOT satisfy this ex-date. Small on purpose.
_DIVIDEND_MATCH_BACKDATE_TOLERANCE_DAYS = 2

# An announced ex-date must be older than this before a missing receipt is
# treated as "you likely received a payout you haven't booked" (rather than
# "announced, too soon to expect the credit"). Covers the settle/credit lag.
_DIVIDEND_SETTLE_MARGIN_DAYS = 21


def _naive_date_floor(dt: datetime) -> datetime:
    """Strip tz + time-of-day → midnight naive datetime (Mongo compare-safe)."""
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _held_names() -> list[dict]:
    """Currently-held names with the fields the drift matrix needs.

    #74 U3-b: filter quantity > 0 (not just deleted_at=None). A position that
    is fully exited but not yet soft-deleted (qty 0) with first_purchased_at <=
    an ex-date would otherwise classify as missing_receipt and fire a spurious
    "unrecorded dividend" nudge — the docstring claimed quantity>0 but the query
    didn't enforce it.
    """
    return list(
        Collections.holdings().find(
            {"deleted_at": None, "quantity": {"$gt": 0}},
            {
                "_id": 0,
                "isin": 1,
                "symbol": 1,
                "quantity": 1,
                "first_purchased_at": 1,
                # #74 U3-e: project booked dividends here so the matrix loop
                # doesn't issue a redundant per-name find_one for it (N+1).
                "total_dividends_received": 1,
            },
        )
    )


def _dividend_txns_for_isin(isin: str) -> list[dict]:
    """Recorded DIVIDEND transactions for one ISIN (trade_date ascending).

    price = per-share payout (see holdings_service._fifo_replay DIVIDEND branch).
    """
    return list(
        Collections.transactions()
        .find(
            {"isin": isin, "type": "DIVIDEND", "deleted_at": None},
            {"_id": 0, "trade_date": 1, "price": 1},
        )
        .sort("trade_date", 1)
    )


def _corporate_action_news_isins(
    isins: list[str], window_days: int = 120
) -> set[str]:
    """#74 U3-e: corporate-action-news corroboration for many ISINs at once.

    ONE query returns the set of ISINs (from `isins`) that have a classified
    corporate_action-themed article within the window, instead of a per-name
    find_one (N queries -> 1). Reads the entity-accurate (#50) entities_isins
    tag so it never corroborates on wrong-company news.
    """
    if not isins:
        return set()
    cutoff = utcnow() - timedelta(days=window_days)
    found: set[str] = set()
    for art in Collections.news_articles().find(
        {
            "entities_isins": {"$in": isins},
            "classified": True,
            "themes": "corporate_action",  # membership on the multikey list
            "fetched_at": {"$gte": cutoff},
        },
        {"_id": 0, "entities_isins": 1},
    ):
        for i in art.get("entities_isins", []) or []:
            if i in isins:
                found.add(i)
    return found


def compute_dividend_drift() -> list[dict]:
    """Announced vs received vs booked per held name (PURE read).

    For each currently-held ISIN, join the captured yfinance announcements
    (dividend_announcements) against the recorded DIVIDEND transactions and the
    booked total_dividends_received, and classify each announced ex-date:

      - "matched":         a DIVIDEND row exists within the match window.
      - "missing_receipt": ex-date passed by >= the settle margin, we held the
                           stock across it, and NO DIVIDEND row was recorded ->
                           realised gain is likely understated.
      - "pending":         ex-date is in the future or within the settle margin
                           (announced, too soon to expect the credit).

    Returns one row per held name:
      {isin, symbol, quantity, booked_dividends, has_corporate_action_news,
       announcements: [{ex_date, amount_per_share, expected_amount, status,
                        matched_trade_date}], missing_count}
    Names with no announcements are still returned (announcements=[], so the UI
    can show "no announcements captured") — the caller can filter.
    """
    today = _naive_date_floor(utcnow())
    settle_cutoff = today - timedelta(days=_DIVIDEND_SETTLE_MARGIN_DAYS)

    held = _held_names()
    # #74 U3-e: resolve corporate-action-news corroboration for ALL held names
    # in ONE query instead of a per-name find_one inside the loop.
    ca_news_isins = _corporate_action_news_isins(
        [h["isin"] for h in held if h.get("isin")]
    )

    rows: list[dict] = []
    for h in held:
        isin = h.get("isin")
        if not isin:
            continue
        symbol = h.get("symbol") or isin
        quantity = _to_dec(h.get("quantity"))
        first_purchased_at = h.get("first_purchased_at")
        first_floor = (
            _naive_date_floor(first_purchased_at) if first_purchased_at else None
        )

        announcements = get_dividend_announcements_for_isin(isin)
        div_txns = _dividend_txns_for_isin(isin)

        # #74 U3-e: booked lifetime dividends come from the _held_names
        # projection now (no redundant per-name find_one).
        booked = _to_dec(h.get("total_dividends_received"))

        matrix: list[dict] = []
        missing_count = 0
        for a in announcements:
            ex_date = a.get("ex_date")
            if ex_date is None:
                continue
            ex_floor = _naive_date_floor(ex_date)
            amount_per_share = _to_dec(a.get("amount_per_share"))

            # Held across this ex-date? (round-1 heuristic)
            held_then = first_floor is not None and first_floor <= ex_floor

            # Look for a recorded DIVIDEND within the match window of the ex-date.
            # #80 L5: the window is DIRECTIONAL — a payout physically cannot
            # settle BEFORE its own ex-date (India credits 2-6 weeks AFTER), so
            # only a trade_date on/after the ex-date can match. A small negative
            # tolerance (_DIVIDEND_MATCH_BACKDATE_TOLERANCE_DAYS) absorbs manual
            # data-entry slack. The old symmetric abs(...)≤21 let a DIVIDEND up
            # to 21 days BEFORE the ex-date (i.e. a prior interim payout) satisfy
            # this ex-date, mislabeling a genuine miss as "matched".
            matched_trade_date = None
            for t in div_txns:
                td = t.get("trade_date")
                if td is None:
                    continue
                td_floor = _naive_date_floor(td)
                delta_days = (td_floor - ex_floor).days
                if (
                    -_DIVIDEND_MATCH_BACKDATE_TOLERANCE_DAYS
                    <= delta_days
                    <= _DIVIDEND_MATCH_WINDOW_DAYS
                ):
                    matched_trade_date = td_floor
                    break

            if matched_trade_date is not None:
                status = "matched"
            elif ex_floor > settle_cutoff:
                # Future ex-date, or passed but still within the credit lag.
                status = "pending"
            elif held_then:
                status = "missing_receipt"
                missing_count += 1
            else:
                # Ex-date passed but we were not holding across it (bought later);
                # no receipt is expected. Surface as pending (informational).
                status = "pending"

            matrix.append(
                {
                    "ex_date": ex_floor,
                    "amount_per_share": amount_per_share,
                    # #74 U3-c: this is an ESTIMATE from the CURRENT quantity, not
                    # the ex-date quantity (precise point-in-time FIFO
                    # reconstruction is deliberately out of scope for round 1 —
                    # see the module note). It is exact only if the position size
                    # is unchanged since the ex-date; flagged so the UI/nudge can
                    # present it as an estimate rather than an authoritative
                    # figure.
                    "expected_amount": (amount_per_share * quantity)
                    if quantity > 0
                    else Decimal("0"),
                    "expected_basis": "current_quantity",
                    "status": status,
                    "matched_trade_date": matched_trade_date,
                }
            )

        rows.append(
            {
                "isin": isin,
                "symbol": symbol,
                "quantity": quantity,
                "booked_dividends": booked,
                "has_corporate_action_news": isin in ca_news_isins,
                "announcements": matrix,
                "missing_count": missing_count,
            }
        )

    return rows


def _dividend_drift_marker_id(isin: str, ex_floor: datetime) -> str:
    """Stable rising-edge dedup key for a missing-receipt nudge."""
    return f"dividend_missing:{isin}:{ex_floor.date().isoformat()}"


# Cap individual per-dividend nudges per run; beyond this, roll the rest into
# one summary push. Prevents a first-run flood (a fresh install legitimately has
# a large backlog of never-recorded historical dividends) from firing dozens of
# separate notifications while still surfacing the full count and never hiding a
# real unbooked payout. Kin to #67's "don't blast on a pre-existing backlog".
_DIVIDEND_NUDGE_INDIVIDUAL_CAP = 3


def _write_dividend_drift_marker(snapshots, item: dict) -> bool:
    """Persist the rising-edge dedup marker for one missing receipt.

    Written only after the corresponding push succeeded (success-gated), so a
    transient ntfy outage retries the whole batch on the next run.

    #73 U2-d: guarded. A bare insert_one here used to be able to abort the whole
    nudge cron mid-batch if it threw (and the already-pushed dividend would then
    have no marker AND the remaining nudges never ran). We now swallow+log a
    marker-write failure and return False; the dividend simply re-nudges next
    run (the safe direction — we never silently drop a real unbooked payout).
    Returns True if the marker landed.
    """
    try:
        snapshots.insert_one(
            _convert_decimals_to_decimal128(
                {
                    "taken_at": utcnow(),
                    "type": "dividend_drift_marker",
                    "marker_id": item["marker_id"],
                    "isin": item["isin"],
                    "symbol": item["symbol"],
                    "ex_date": item["ex_floor"],
                    "amount_per_share": item["amount_per_share"],
                    "expected_amount": item["expected"],
                    "_schema_version": 1,
                }
            )
        )
        return True
    except Exception as exc:
        log.error(
            "dividend-drift marker write failed for %s (%s): %s — will re-nudge next run",
            item.get("isin"),
            item.get("marker_id"),
            exc,
        )
        return False


def evaluate_dividend_drift_alerts() -> int:
    """Nudge on NEW missing dividend receipts (rising-edge deduped, flood-capped).

    Mirrors _send_auto_drift_alert: ntfy-only on the price channel, best-effort
    (push_public raises on transport failure -> guarded, logged, not
    propagated). Dedup is a marker doc in reconciliation_snapshots keyed by
    (isin, ex_date) so each missed dividend nudges at most once; a marker is
    written ONLY after a successful push (success-gated -> a transient ntfy
    outage retries the batch next run; mirrors #41/#56/#57).

    Flood control: at most _DIVIDEND_NUDGE_INDIVIDUAL_CAP dividends are pushed
    as individual nudges per run. If more are newly missing, the first few are
    pushed individually and the remainder are rolled into ONE summary push (a
    fresh install has a legitimate backlog of never-recorded historical
    dividends). Markers are written for every newly-missing dividend either way,
    so the count stays exact and it never re-floods.

    Returns the number of newly-missing dividends handled (individual + rolled
    into the summary) that were durably marked this run.
    """
    drift = compute_dividend_drift()
    snapshots = Collections.reconciliation_snapshots()

    # Collect every NEW missing receipt (no existing marker), newest ex-date
    # first so the individual nudges surface the most recent (most actionable).
    new_missing: list[dict] = []
    for row in drift:
        isin = row["isin"]
        symbol = row["symbol"]
        for a in row["announcements"]:
            if a["status"] != "missing_receipt":
                continue
            ex_floor = a["ex_date"]
            marker_id = _dividend_drift_marker_id(isin, ex_floor)
            if snapshots.find_one(
                {"type": "dividend_drift_marker", "marker_id": marker_id}
            ):
                continue  # already nudged for this (isin, ex_date)
            new_missing.append(
                {
                    "isin": isin,
                    "symbol": symbol,
                    "ex_floor": ex_floor,
                    "marker_id": marker_id,
                    "amount_per_share": a["amount_per_share"],
                    "expected": a["expected_amount"],
                }
            )

    if not new_missing:
        return 0

    new_missing.sort(key=lambda x: x["ex_floor"], reverse=True)

    individual = new_missing[:_DIVIDEND_NUDGE_INDIVIDUAL_CAP]
    overflow = new_missing[_DIVIDEND_NUDGE_INDIVIDUAL_CAP:]
    handled = 0

    # Individual nudges — each success-gates its own marker.
    for item in individual:
        body_text = (
            f"{item['symbol']}: a dividend of ₹{item['amount_per_share']}/share "
            f"went ex on {item['ex_floor'].date().isoformat()} but no payout is "
            f"recorded. You likely received ~₹{item['expected']} — record it so "
            f"your realised gain is not understated. "
            f"Reconciliation page → Dividend drift."
        )
        try:
            push_public(
                channel="price",  # portfolio-impact = price channel (mirrors auto-drift)
                title="Unrecorded dividend",
                message=body_text,
                priority="default",
                tags=["money_with_wings"],
            )
        except Exception as exc:
            log.error(
                "dividend-drift ntfy nudge failed for %s: %s", item["isin"], exc
            )
            continue  # no marker -> retries next run
        if _write_dividend_drift_marker(snapshots, item):
            handled += 1

    # Overflow — ONE summary push gates ALL rolled-in markers together.
    if overflow:
        names = sorted({o["symbol"] for o in overflow})
        preview = ", ".join(names[:6]) + ("…" if len(names) > 6 else "")
        body_text = (
            f"{len(overflow)} more unrecorded dividends across {len(names)} "
            f"holdings ({preview}). Record them so your realised gain is not "
            f"understated. Reconciliation page → Dividend drift."
        )
        try:
            push_public(
                channel="price",
                title=f"{len(overflow)} more unrecorded dividends",
                message=body_text,
                priority="default",
                tags=["money_with_wings"],
            )
        except Exception as exc:
            log.error("dividend-drift summary ntfy nudge failed: %s", exc)
        else:
            for item in overflow:
                if _write_dividend_drift_marker(snapshots, item):
                    handled += 1

    if handled:
        log.info(
            "Dividend-drift: %d newly-missing handled (%d individual, %d summarised)",
            handled,
            len(individual),
            len(overflow),
        )
    return handled
