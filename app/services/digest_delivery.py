"""Send the weekly suggestions digest via Resend (email) and ntfy (push).

Unit 3 polish:
  - Top 10 in email (was 5)
  - "Did you get the push?" banner in email
  - Per-delivery audit log in `digest_deliveries` collection
  - Sends digest even when zero candidates (so user knows the system ran)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import requests
from bson import ObjectId

from app.config.settings import settings
from app.db.client import Collections
from app.models._common import utcnow
from app.models.suggestion import SuggestionRun

log = logging.getLogger(__name__)

DEFAULT_DASHBOARD_URL = f"http://{settings.TAILSCALE_IP}:3000/suggestions"
NTFY_PUBLIC_HELP_URL = "https://portfolio-advisor.tail0c8705.ts.net"
TOP_K_FOR_EMAIL = 10  # was 5


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
            '<p style="margin: 4px 0; font-family: monospace; font-size: 11px; color: #888;">'
            f"Q={c.quality_score:.0f} V={c.valuation_score:.0f} M={c.momentum_score:.0f} N={c.news_score:.0f}"
            "</p>"
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
        f"Did not get the ntfy push? Check that your ntfy app is subscribed to topic <code>portfolio-suggestions</code> on <code>{NTFY_PUBLIC_HELP_URL}</code> with credentials."
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
            f"#{c.rank}  {c.symbol}  composite={c.composite_score:.1f}  conf={c.confidence_score:.0f}"
        )
        lines.append(
            f"     Q={c.quality_score:.0f} V={c.valuation_score:.0f} M={c.momentum_score:.0f} N={c.news_score:.0f}"
        )
        lines.append(f"     {summary}")
        lines.append(f"     Valuation: {dossier.get('valuation_verdict', '(none)')}")
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


def _send_email(subject: str, html: str, text: str) -> dict:
    try:
        import resend

        resend.api_key = settings.RESEND_API_KEY
        response = resend.Emails.send(
            {
                "from": settings.RESEND_FROM,
                "to": settings.RESEND_TO,
                "subject": subject,
                "html": html,
                "text": text,
            }
        )
        log.info("Resend email sent: id=%s", response.get("id"))
        return {"ok": True, "id": response.get("id")}
    except Exception as exc:
        log.error("Resend email failed: %s", exc)
        return {"ok": False, "error": str(exc)}


def _send_ntfy(title: str, body: str, priority: str = "default") -> dict:
    try:
        url = f"{settings.NTFY_URL.rstrip('/')}/portfolio-suggestions"
        response = requests.post(
            url,
            data=body.encode("utf-8"),
            headers={
                "Title": title,
                "Markdown": "yes",
                "Priority": priority,
            },
            auth=(settings.NTFY_USER, settings.NTFY_PASS),
            timeout=10,
        )
        response.raise_for_status()
        log.info("ntfy push sent: status=%s", response.status_code)
        return {"ok": True, "status": response.status_code}
    except Exception as exc:
        log.error("ntfy push failed: %s", exc)
        return {"ok": False, "error": str(exc)}


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


def send_weekly_digest(run: SuggestionRun, run_id: ObjectId | None = None) -> dict:
    """Send the weekly digest via email + ntfy. Returns delivery stats.
    Sends even if zero candidates so user knows the system ran.
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

    return {
        "subject": subject,
        "email": email_result,
        "ntfy": ntfy_result,
    }
