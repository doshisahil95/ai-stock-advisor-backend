"""Send the weekly suggestions digest via Resend (email) and ntfy (push).

Unit 3 polish:
  - Top 10 in email (was 5)
  - "Did you get the push?" banner in email
  - Per-delivery audit log in `digest_deliveries` collection
  - Sends digest even when zero candidates (so user knows the system ran)

F2b: ntfy moved from self-hosted Tailscale Funnel to public ntfy.sh
because iOS delivery on the private path was poll-based and dropped
digests silently. push_private remains in notify.py for future
genuinely-sensitive content.

F2 chunk 6: send_combined_digest(buy_run, sell_run) emits ONE email +
ONE ntfy push covering both sides. Used by the --direction=both cron
path in run_weekly_suggestions.py.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from app.config.settings import settings
from app.db.client import Collections
from app.models._common import utcnow
from app.models.suggestion import SuggestionRun
from app.services.notify import email as notify_email, push_public

log = logging.getLogger(__name__)

DEFAULT_DASHBOARD_URL = f"http://{settings.TAILSCALE_IP}:3000/suggestions"
TOP_K_FOR_EMAIL = 10  # was 5


# ─────────────────────────────────────────────────────────────────────
# Subject + priority helpers (shared by single + combined digests)
# ─────────────────────────────────────────────────────────────────────


def _priority_label(top_composite: float) -> str:
    if top_composite >= 70:
        return "HIGH"
    if top_composite >= 55:
        return "MED"
    return "----"


def _format_subject(run: SuggestionRun) -> str:
    top = run.top_candidates[:5]
    if not top:
        return (
            f"[----] Weekly suggestions - {run.run_date_ist} - no candidates this week"
        )
    top_composite = top[0].composite_score
    priority = _priority_label(top_composite)
    symbols = ", ".join(c.symbol for c in top)
    return f"[{priority}] Weekly suggestions - {run.run_date_ist} - top: {symbols}"


def _format_score_breakdown(run: SuggestionRun, candidate: Any) -> str:
    if run.direction == "sell":
        return (
            "Book="
            f"{getattr(candidate, 'booking_opportunity_score', 0.0):.0f} "
            "Stretch="
            f"{getattr(candidate, 'valuation_stretch_score', 0.0):.0f} "
            "Risk="
            f"{getattr(candidate, 'risk_score', 0.0):.0f} "
            "Tax/Conc="
            f"{getattr(candidate, 'tax_concentration_score', 0.0):.0f}"
        )
    return (
        f"Q={candidate.quality_score:.0f} "
        f"V={candidate.valuation_score:.0f} "
        f"M={candidate.momentum_score:.0f} "
        f"N={candidate.news_score:.0f}"
    )


def _format_score_breakdown_html(run: SuggestionRun, candidate: Any) -> str:
    return (
        '<p style="margin: 4px 0; font-family: monospace; font-size: 11px; color: #888;">'
        f"{_format_score_breakdown(run, candidate)}"
        "</p>"
    )


# ─────────────────────────────────────────────────────────────────────
# Single-direction (buy or sell) digest formatters
# ─────────────────────────────────────────────────────────────────────


def _format_no_candidates_html(run: SuggestionRun) -> str:
    """Email body when zero candidates were eligible."""
    return (
        '<div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 700px; margin: 0 auto; padding: 16px; color: #1a1a1a;">'
        f'<h1 style="font-size: 22px; margin-bottom: 4px;">Weekly Suggestions - {run.run_date_ist}</h1>'
        '<p style="color: #666; margin-top: 0; font-size: 14px;">No eligible candidates this week.</p>'
        '<hr style="border: none; border-top: 1px solid #e5e5e5; margin: 16px 0;">'
        '<p style="font-size: 14px;">The system ran successfully but no NIFTY 100 stocks passed all quality gates. Possible reasons:</p>'
        '<ul style="font-size: 14px; line-height: 1.6;">'
        f"<li>Universe: {run.universe_size} | excluded held: {run.excluded_held} | excluded rejected: {run.excluded_rejected} | stale data: {run.excluded_stale_data}</li>"
        f"<li>Considered after exclusions: {run.candidates_considered}</li>"
        f"<li>Passed gates: {run.candidates_post_gates}</li>"
        "</ul>"
        f'<p style="font-size: 14px;"><a href="{DEFAULT_DASHBOARD_URL}" style="color: #2563eb;">Open dashboard</a> for details.</p>'
        "</div>"
    )


def _format_email_html(run: SuggestionRun, dossiers: list[dict]) -> str:
    if not run.top_candidates:
        return _format_no_candidates_html(run)

    dossier_by_isin = {d.get("isin"): d for d in dossiers}

    html_parts = [
        '<div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 700px; margin: 0 auto; padding: 16px; color: #1a1a1a;">',
        f'<h1 style="font-size: 22px; margin-bottom: 4px;">Weekly Suggestions - {run.run_date_ist}</h1>',
        f'<p style="color: #666; margin-top: 0; font-size: 14px;">Universe: {run.universe_size} | Eligible: {run.candidates_post_gates} | Top: {len(run.top_candidates[:TOP_K_FOR_EMAIL])}</p>',
        '<hr style="border: none; border-top: 1px solid #e5e5e5; margin: 16px 0;">',
    ]

    for c in run.top_candidates[:TOP_K_FOR_EMAIL]:
        dossier = dossier_by_isin.get(c.isin, {})
        plain_english = dossier.get("plain_english_summary") or dossier.get(
            "one_line_thesis", "(no summary)"
        )
        verdict = dossier.get("valuation_verdict", "(no verdict)")

        html_parts.append(
            '<div style="margin-bottom: 20px; padding: 12px; background: #f9f9f9; border-radius: 6px; border-left: 4px solid #2563eb;">'
            '<div style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 8px;">'
            f'<h2 style="font-size: 18px; margin: 0;">#{c.rank} {c.symbol}</h2>'
            f'<span style="font-family: monospace; font-size: 13px; color: #666;">composite {c.composite_score:.1f} | confidence {c.confidence_score:.0f}</span>'
            "</div>"
            f'<p style="margin: 8px 0; font-size: 14px; color: #333; line-height: 1.5;">{plain_english}</p>'
            f"{_format_score_breakdown_html(run, c)}"
            f'<p style="margin: 6px 0 0; font-size: 12px; color: #555; font-style: italic;">Valuation: {verdict}</p>'
            "</div>"
        )

    html_parts.append(
        '<hr style="border: none; border-top: 1px solid #e5e5e5; margin: 16px 0;">'
        f'<p style="font-size: 14px;"><a href="{DEFAULT_DASHBOARD_URL}" style="color: #2563eb; text-decoration: none; font-weight: 500;">Open full dashboard</a> for analyst details, action buttons, and history.</p>'
        '<hr style="border: none; border-top: 1px solid #e5e5e5; margin: 16px 0;">'
        '<p style="font-size: 11px; color: #999; margin-top: 16px;">'
        "You decide. The system synthesizes; it does not advise. Buy or skip via ICICI Direct as usual."
        "</p>"
        '<p style="font-size: 11px; color: #999; margin-top: 8px;">'
        "Did not get the ntfy push? Confirm your iPhone ntfy app is subscribed to your configured digests topic on <code>https://ntfy.sh</code> (no credentials required for public topics)."
        "</p>"
        "</div>"
    )
    return "\n".join(html_parts)


def _format_email_text(run: SuggestionRun, dossiers: list[dict]) -> str:
    if not run.top_candidates:
        return f"Weekly Suggestions - {run.run_date_ist}\n\nNo eligible candidates this week.\n\nUniverse: {run.universe_size} | Considered: {run.candidates_considered} | Post-gates: {run.candidates_post_gates}\n\nOpen: {DEFAULT_DASHBOARD_URL}"

    dossier_by_isin = {d.get("isin"): d for d in dossiers}
    lines = [
        f"Weekly Suggestions - {run.run_date_ist}",
        f"Universe: {run.universe_size} | Eligible: {run.candidates_post_gates} | Top: {len(run.top_candidates[:TOP_K_FOR_EMAIL])}",
        "=" * 70,
        "",
    ]
    for c in run.top_candidates[:TOP_K_FOR_EMAIL]:
        dossier = dossier_by_isin.get(c.isin, {})
        summary = dossier.get("plain_english_summary") or dossier.get(
            "one_line_thesis", "(none)"
        )
        lines.append(
            f"#{c.rank} {c.symbol}  composite={c.composite_score:.1f}  conf={c.confidence_score:.0f}"
        )
        lines.append(f"  {_format_score_breakdown(run, c)}")
        lines.append(f"  {summary}")
        lines.append(f"  Valuation: {dossier.get('valuation_verdict', '(none)')}")
        lines.append("")
    lines.append(f"Open: {DEFAULT_DASHBOARD_URL}")
    return "\n".join(lines)


def _format_ntfy_body(run: SuggestionRun) -> str:
    if not run.top_candidates:
        return f"No eligible candidates for {run.run_date_ist}. The system ran successfully."
    lines = [
        f"**Top {min(len(run.top_candidates), TOP_K_FOR_EMAIL)}** ({run.run_date_ist}):",
        "",
    ]
    for c in run.top_candidates[:TOP_K_FOR_EMAIL]:
        lines.append(
            f"#{c.rank} **{c.symbol}** - {c.composite_score:.0f}/100 (conf {c.confidence_score:.0f})"
        )
    lines.append("")
    lines.append(f"[Open dashboard]({DEFAULT_DASHBOARD_URL})")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────
# Combined (buy+sell) digest formatters — F2 chunk 6
# ─────────────────────────────────────────────────────────────────────


def _combined_severity(buy_run: SuggestionRun, sell_run: SuggestionRun) -> str:
    """[HIGH]/[MED]/[----] for combined subject, based on max composite across BOTH sides."""

    def _top_score(run):
        return max((c.composite_score for c in run.top_candidates), default=0.0)

    top_score = max(_top_score(buy_run), _top_score(sell_run))
    if top_score >= 70:
        return "HIGH"
    if top_score >= 55:
        return "MED"
    return "----"


def _format_combined_subject(buy_run: SuggestionRun, sell_run: SuggestionRun) -> str:
    severity = _combined_severity(buy_run, sell_run)
    buy_top_symbols = ", ".join(c.symbol for c in buy_run.top_candidates[:5])
    sell_top_symbols = ", ".join(c.symbol for c in sell_run.top_candidates[:5])
    return (
        f"[{severity}] Weekly suggestions - {buy_run.run_date_ist} - "
        f"buy: {buy_top_symbols or '—'} | sell: {sell_top_symbols or '—'}"
    )


def _format_side_html(
    run: SuggestionRun,
    dossiers: list[dict],
    title: str,
    accent_color: str,
) -> str:
    """Render one side (buy or sell) as an HTML block for the combined email.

    Mirrors _format_email_html per-card markup but with a title row and
    a configurable accent color so buy and sell are visually distinguishable.
    """
    if not run.top_candidates:
        return (
            f'<h2 style="font-size: 18px; margin: 24px 0 8px; color: {accent_color};">{title}</h2>'
            f'<p style="font-size: 14px; color: #666; margin: 0 0 12px;">'
            f"No eligible candidates this week "
            f"(considered {run.candidates_considered}, passed gates {run.candidates_post_gates})."
            "</p>"
        )

    dossier_by_isin = {d.get("isin"): d for d in dossiers}
    parts: list[str] = [
        f'<h2 style="font-size: 18px; margin: 24px 0 8px; color: {accent_color};">{title}</h2>',
        f'<p style="font-size: 12px; color: #666; margin: 0 0 12px;">'
        f"Universe: {run.universe_size} | Eligible: {run.candidates_post_gates} | "
        f"Top: {len(run.top_candidates[:TOP_K_FOR_EMAIL])}"
        "</p>",
    ]

    for c in run.top_candidates[:TOP_K_FOR_EMAIL]:
        dossier = dossier_by_isin.get(c.isin, {})
        plain_english = dossier.get("plain_english_summary") or dossier.get(
            "one_line_thesis", "(no summary)"
        )
        verdict = dossier.get("valuation_verdict", "(no verdict)")

        parts.append(
            f'<div style="margin-bottom: 16px; padding: 12px; background: #f9f9f9; border-radius: 6px; border-left: 4px solid {accent_color};">'
            '<div style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 8px;">'
            f'<h3 style="font-size: 16px; margin: 0;">#{c.rank} {c.symbol}</h3>'
            f'<span style="font-family: monospace; font-size: 12px; color: #666;">composite {c.composite_score:.1f} | confidence {c.confidence_score:.0f}</span>'
            "</div>"
            f'<p style="margin: 8px 0; font-size: 13px; color: #333; line-height: 1.5;">{plain_english}</p>'
            f"{_format_score_breakdown_html(run, c)}"
            f'<p style="margin: 4px 0 0; font-size: 11px; color: #555; font-style: italic;">Valuation: {verdict}</p>'
            "</div>"
        )

    return "\n".join(parts)


def _format_combined_email_html(
    buy_run: SuggestionRun,
    buy_dossiers: list[dict],
    sell_run: SuggestionRun,
    sell_dossiers: list[dict],
) -> str:
    buy_block = _format_side_html(buy_run, buy_dossiers, "=== BUY-SIDE ===", "#2563eb")
    sell_block = _format_side_html(
        sell_run, sell_dossiers, "=== SELL-SIDE ===", "#dc2626"
    )

    return "\n".join(
        [
            '<div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 700px; margin: 0 auto; padding: 16px; color: #1a1a1a;">',
            f'<h1 style="font-size: 22px; margin-bottom: 4px;">Weekly Suggestions — {buy_run.run_date_ist}</h1>',
            '<p style="color: #666; margin-top: 0; font-size: 13px;">Buy and sell sides delivered together.</p>',
            '<hr style="border: none; border-top: 1px solid #e5e5e5; margin: 16px 0;">',
            buy_block,
            '<hr style="border: none; border-top: 1px solid #e5e5e5; margin: 24px 0;">',
            sell_block,
            '<hr style="border: none; border-top: 1px solid #e5e5e5; margin: 24px 0;">',
            f'<p style="font-size: 14px;"><a href="{DEFAULT_DASHBOARD_URL}" style="color: #2563eb; text-decoration: none; font-weight: 500;">Open full dashboard</a> for analyst details and action buttons.</p>',
            '<p style="font-size: 11px; color: #999; margin-top: 16px;">'
            "You decide. The system synthesizes; it does not advise. Buy or sell via ICICI Direct as usual."
            "</p>",
            '<p style="font-size: 11px; color: #999; margin-top: 8px;">'
            "Did not get the ntfy push? Confirm your iPhone ntfy app is subscribed to your configured digests topic on <code>https://ntfy.sh</code>."
            "</p>",
            "</div>",
        ]
    )


def _format_side_text(run: SuggestionRun, dossiers: list[dict], heading: str) -> str:
    """One side as plain text for the combined email."""
    if not run.top_candidates:
        return (
            f"{heading}\n"
            f"  No eligible candidates (considered {run.candidates_considered}, "
            f"passed gates {run.candidates_post_gates})."
        )

    dossier_by_isin = {d.get("isin"): d for d in dossiers}
    lines = [heading]
    for c in run.top_candidates[:TOP_K_FOR_EMAIL]:
        dossier = dossier_by_isin.get(c.isin, {})
        summary = dossier.get("plain_english_summary") or dossier.get(
            "one_line_thesis", "(none)"
        )
        lines.append(
            f"  #{c.rank} {c.symbol}  composite={c.composite_score:.1f}  conf={c.confidence_score:.0f}"
        )
        lines.append(f"    {_format_score_breakdown(run, c)}")
        lines.append(f"    {summary}")
    return "\n".join(lines)


def _format_combined_email_text(
    buy_run: SuggestionRun,
    buy_dossiers: list[dict],
    sell_run: SuggestionRun,
    sell_dossiers: list[dict],
) -> str:
    return "\n".join(
        [
            f"Weekly Suggestions - {buy_run.run_date_ist}",
            "=" * 70,
            "",
            _format_side_text(buy_run, buy_dossiers, "=== BUY-SIDE ==="),
            "",
            _format_side_text(sell_run, sell_dossiers, "=== SELL-SIDE ==="),
            "",
            f"Open: {DEFAULT_DASHBOARD_URL}",
        ]
    )


def _format_combined_ntfy_body(buy_run: SuggestionRun, sell_run: SuggestionRun) -> str:
    """Compact markdown for the iPhone push covering both sides."""
    lines: list[str] = [f"**Weekly Suggestions ({buy_run.run_date_ist})**", ""]

    lines.append(f"**=== BUY-SIDE === ({len(buy_run.top_candidates)} top)**")
    if buy_run.top_candidates:
        for c in buy_run.top_candidates[:TOP_K_FOR_EMAIL]:
            lines.append(
                f"#{c.rank} **{c.symbol}** - {c.composite_score:.0f}/100 (conf {c.confidence_score:.0f})"
            )
    else:
        lines.append("(no eligible candidates)")

    lines.append("")
    lines.append(f"**=== SELL-SIDE === ({len(sell_run.top_candidates)} top)**")
    if sell_run.top_candidates:
        for c in sell_run.top_candidates[:TOP_K_FOR_EMAIL]:
            lines.append(
                f"#{c.rank} **{c.symbol}** - {c.composite_score:.0f}/100 (conf {c.confidence_score:.0f})"
            )
    else:
        lines.append("(no eligible candidates)")

    lines.append("")
    lines.append(f"[Open dashboard]({DEFAULT_DASHBOARD_URL})")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────
# Delivery transports
# ─────────────────────────────────────────────────────────────────────


def _send_email(subject: str, html: str, text: str) -> dict:
    """Send the digest email via the notify.email() wrapper.

    A2 (Chat 5): delegates to notify.email() so all Resend traffic
    flows through a single wrapper. The wrapper returns the same
    {ok, id, error} dict shape this function used to return inline,
    so _log_delivery's existing field reads continue to work.
    """
    result = notify_email(subject=subject, html=html, text=text)
    if result.get("ok"):
        log.info("Resend email sent: id=%s", result.get("id"))
    else:
        log.error("Resend email failed: %s", result.get("error"))
    return result


def _send_ntfy(title: str, body: str, priority: str = "default") -> dict:
    """Send the weekly digest via the public ntfy channel (F2b).

    Was self-hosted ntfy on Tailscale Funnel. iOS delivery on that path was
    poll-based and silently dropped digests. push_public("digests", …) hits
    ntfy.sh with an unguessable-topic and reaches iOS instantly via APNs.

    See notify.push_public and PROJECT_STATE Section 12.
    """
    try:
        response = push_public(
            "digests",
            title=title,
            message=body,
            priority=priority,
            tags=["chart_with_upwards_trend"],
        )
        log.info("ntfy digest pushed via public channel: %s", response.get("id", "ok"))
        return {"ok": True, "status": 200, "response": response}
    except Exception as exc:
        log.error("ntfy digest push failed: %s", exc)
        return {"ok": False, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────
# Audit log
# ─────────────────────────────────────────────────────────────────────


def _log_delivery(
    run_id: ObjectId | None,
    run_date_ist: str,
    top_count: int,
    subject: str,
    email_result: dict,
    ntfy_result: dict,
) -> None:
    """Persist the delivery attempt for auditing."""
    try:
        Collections.digest_deliveries().insert_one(
            {
                "run_id": run_id,
                "run_date_ist": run_date_ist,
                "sent_at": utcnow(),
                "top_count": top_count,
                "subject": subject,
                "email_ok": email_result.get("ok", False),
                "email_id": email_result.get("id"),
                "email_error": email_result.get("error"),
                "ntfy_ok": ntfy_result.get("ok", False),
                "ntfy_status": ntfy_result.get("status"),
                "ntfy_error": ntfy_result.get("error"),
            }
        )
    except Exception as exc:
        log.error("Failed to log digest delivery: %s", exc)


# ─────────────────────────────────────────────────────────────────────
# Public delivery entry points
# ─────────────────────────────────────────────────────────────────────


def send_weekly_digest(run: SuggestionRun, run_id: ObjectId | None = None) -> dict:
    """Send the single-direction weekly digest via email + ntfy.

    Used for manual reruns and for --direction=buy or --direction=sell
    standalone cron paths. The --direction=both production path uses
    send_combined_digest below.
    """
    dossiers: list[dict] = []
    if run.notes:
        try:
            dossiers = json.loads(run.notes).get("dossiers", [])
        except (json.JSONDecodeError, TypeError):
            log.warning("Could not parse dossiers from run.notes for digest")

    subject = _format_subject(run)
    html = _format_email_html(run, dossiers)
    text = _format_email_text(run, dossiers)
    ntfy_body = _format_ntfy_body(run)

    log.info("Sending digest: %s", subject)

    email_result = _send_email(subject, html, text)

    if run.top_candidates:
        top_composite = run.top_candidates[0].composite_score
        ntfy_priority = "high" if top_composite >= 70 else "default"
    else:
        ntfy_priority = "low"

    ntfy_result = _send_ntfy(subject, ntfy_body, priority=ntfy_priority)

    _log_delivery(
        run_id=run_id,
        run_date_ist=run.run_date_ist,
        top_count=len(run.top_candidates[:TOP_K_FOR_EMAIL]),
        subject=subject,
        email_result=email_result,
        ntfy_result=ntfy_result,
    )

    return {"subject": subject, "email": email_result, "ntfy": ntfy_result}


def send_combined_digest(buy_run: SuggestionRun, sell_run: SuggestionRun) -> dict:
    """Send ONE email + ONE ntfy push covering both buy and sell sides.

    Used by the `--direction=both` cron path in run_weekly_suggestions
    (F2 chunk 6). Avoids spamming the user with two emails 30 minutes
    apart, which trains them to dismiss the inbox notification.

    Both runs are expected to be from the SAME run_date_ist (same Sunday).
    If they differ we log a warning but still send.

    Delivery row is attached to the BUY run id so digest_deliveries
    history stays chronological with the existing schema (one row per
    delivery, one delivery per run-date). Sell-side outcomes are still
    recorded under the sell run id by create_outcomes_for_run; this only
    affects the delivery audit trail.
    """
    if buy_run.run_date_ist != sell_run.run_date_ist:
        log.warning(
            "send_combined_digest: run_date_ist mismatch buy=%s sell=%s",
            buy_run.run_date_ist,
            sell_run.run_date_ist,
        )

    # Parse dossiers from each side's notes.
    def _parse_dossiers(run: SuggestionRun) -> list[dict]:
        if not run.notes:
            return []
        try:
            return json.loads(run.notes).get("dossiers", []) or []
        except (json.JSONDecodeError, TypeError):
            log.warning(
                "Could not parse dossiers from run.notes for combined digest "
                "(direction=%s, run_date_ist=%s)",
                run.direction,
                run.run_date_ist,
            )
            return []

    buy_dossiers = _parse_dossiers(buy_run)
    sell_dossiers = _parse_dossiers(sell_run)

    # Resolve persisted buy run id for the delivery log.
    buy_doc = Collections.suggestion_runs().find_one(
        {
            "direction": "buy",
            "run_date_ist": buy_run.run_date_ist,
            "status": {"$in": ["success", "partial"]},
        },
        sort=[("run_date", -1)],
        projection={"_id": 1},
    )
    buy_run_id = buy_doc["_id"] if buy_doc else None

    subject = _format_combined_subject(buy_run, sell_run)
    html = _format_combined_email_html(buy_run, buy_dossiers, sell_run, sell_dossiers)
    text = _format_combined_email_text(buy_run, buy_dossiers, sell_run, sell_dossiers)
    ntfy_body = _format_combined_ntfy_body(buy_run, sell_run)

    log.info("Sending combined digest: %s", subject)

    email_result = _send_email(subject, html, text)

    severity = _combined_severity(buy_run, sell_run)
    ntfy_priority = "high" if severity == "HIGH" else "default"
    ntfy_result = _send_ntfy(subject, ntfy_body, priority=ntfy_priority)

    top_count = len(buy_run.top_candidates[:TOP_K_FOR_EMAIL]) + len(
        sell_run.top_candidates[:TOP_K_FOR_EMAIL]
    )
    _log_delivery(
        run_id=buy_run_id,
        run_date_ist=buy_run.run_date_ist,
        top_count=top_count,
        subject=subject,
        email_result=email_result,
        ntfy_result=ntfy_result,
    )

    return {
        "subject": subject,
        "email": email_result,
        "ntfy": ntfy_result,
        "buy_top": len(buy_run.top_candidates),
        "sell_top": len(sell_run.top_candidates),
    }
