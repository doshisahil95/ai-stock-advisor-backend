"""Send the weekly suggestions digest via Resend (email) and ntfy (push)."""

from __future__ import annotations

import json
import logging

import requests

from app.config.settings import settings
from app.models.suggestion import SuggestionRun

log = logging.getLogger(__name__)

# Frontend URL for the "Open dashboard" link in email
DEFAULT_DASHBOARD_URL = f"http://{settings.TAILSCALE_IP}:3000/suggestions"


def _priority_label(top_composite: float) -> str:
    """Subject-line priority bracket per our convention."""
    if top_composite >= 70:
        return "HIGH"
    if top_composite >= 55:
        return "MED"
    return "----"


def _format_subject(run: SuggestionRun) -> str:
    """Subject: [HIGH] Weekly suggestions - 11 May - top: HINDZINC, COALINDIA, ..."""
    top = run.top_candidates[:5]
    if not top:
        return f"[----] Weekly suggestions - {run.run_date_ist} - no candidates"

    top_composite = top[0].composite_score
    priority = _priority_label(top_composite)
    symbols = ", ".join(c.symbol for c in top)
    return f"[{priority}] Weekly suggestions - {run.run_date_ist} - top: {symbols}"


def _format_email_html(run: SuggestionRun, dossiers: list[dict]) -> str:
    """HTML body for the email."""
    if not run.top_candidates:
        return "<p>No eligible candidates this week. Check the system.</p>"

    dossier_by_isin = {d.get("isin"): d for d in dossiers}

    html_parts = [
        '<div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 700px; margin: 0 auto; padding: 16px; color: #1a1a1a;">',
        f'<h1 style="font-size: 22px; margin-bottom: 4px;">Weekly Suggestions - {run.run_date_ist}</h1>',
        f'<p style="color: #666; margin-top: 0; font-size: 14px;">Universe: {run.universe_size} | Eligible: {run.candidates_post_gates} | Top: {len(run.top_candidates)}</p>',
        '<hr style="border: none; border-top: 1px solid #e5e5e5; margin: 16px 0;">',
    ]

    for c in run.top_candidates[:5]:
        dossier = dossier_by_isin.get(c.isin, {})
        thesis = dossier.get("one_line_thesis", "(no thesis)")
        verdict = dossier.get("valuation_verdict", "(no verdict)")

        html_parts.append(
            '<div style="margin-bottom: 24px; padding: 12px; background: #f9f9f9; border-radius: 6px; border-left: 4px solid #2563eb;">'
            '<div style="display: flex; justify-content: space-between; align-items: baseline;">'
            f'<h2 style="font-size: 18px; margin: 0;">#{c.rank} {c.symbol}</h2>'
            f'<span style="font-family: monospace; font-size: 13px;">composite {c.composite_score:.1f} | confidence {c.confidence_score:.0f}</span>'
            "</div>"
            f'<p style="margin: 8px 0; font-size: 14px; color: #444;">{thesis}</p>'
            '<p style="margin: 4px 0; font-family: monospace; font-size: 12px; color: #666;">'
            f"Q={c.quality_score:.0f} V={c.valuation_score:.0f} M={c.momentum_score:.0f} N={c.news_score:.0f}"
            "</p>"
            f'<p style="margin: 8px 0 0; font-size: 13px; color: #555; font-style: italic;">{verdict}</p>'
            "</div>"
        )

    html_parts.append(
        '<hr style="border: none; border-top: 1px solid #e5e5e5; margin: 16px 0;">'
        f'<p style="font-size: 14px;"><a href="{DEFAULT_DASHBOARD_URL}" style="color: #2563eb; text-decoration: none; font-weight: 500;">Open full dashboard</a></p>'
        '<p style="font-size: 11px; color: #999; margin-top: 24px;">'
        "You decide. The system synthesizes; it does not advise. Buy or skip via ICICI Direct as usual."
        "</p>"
        "</div>"
    )
    return "\n".join(html_parts)


def _format_email_text(run: SuggestionRun, dossiers: list[dict]) -> str:
    """Plain-text fallback for email clients without HTML."""
    if not run.top_candidates:
        return "No eligible candidates this week."

    dossier_by_isin = {d.get("isin"): d for d in dossiers}
    lines = [
        f"Weekly Suggestions - {run.run_date_ist}",
        f"Universe: {run.universe_size} | Eligible: {run.candidates_post_gates} | Top: {len(run.top_candidates)}",
        "=" * 70,
        "",
    ]
    for c in run.top_candidates[:5]:
        dossier = dossier_by_isin.get(c.isin, {})
        lines.append(
            f"#{c.rank}  {c.symbol}  composite={c.composite_score:.1f}  conf={c.confidence_score:.0f}"
        )
        lines.append(
            f"     Q={c.quality_score:.0f} V={c.valuation_score:.0f} M={c.momentum_score:.0f} N={c.news_score:.0f}"
        )
        lines.append(f"     Thesis:  {dossier.get('one_line_thesis', '(none)')}")
        lines.append(f"     Verdict: {dossier.get('valuation_verdict', '(none)')}")
        lines.append("")

    lines.append(f"Open: {DEFAULT_DASHBOARD_URL}")
    return "\n".join(lines)


def _format_ntfy_body(run: SuggestionRun) -> str:
    """Compact ntfy push body (markdown)."""
    if not run.top_candidates:
        return "No eligible candidates."
    lines = [f"**Top 5** ({run.run_date_ist}):", ""]
    for c in run.top_candidates[:5]:
        lines.append(
            f"#{c.rank} **{c.symbol}** - {c.composite_score:.0f}/100 (conf {c.confidence_score:.0f})"
        )
    lines.append("")
    lines.append(f"[Open dashboard]({DEFAULT_DASHBOARD_URL})")
    return "\n".join(lines)


def _send_email(subject: str, html: str, text: str) -> dict:
    """Send via Resend Python SDK."""
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
    """Send via self-hosted ntfy (basic auth, markdown body)."""
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


def send_weekly_digest(run: SuggestionRun) -> dict:
    """Send the weekly digest via email + ntfy. Returns delivery stats."""
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

    top_composite = run.top_candidates[0].composite_score if run.top_candidates else 0
    ntfy_priority = "high" if top_composite >= 70 else "default"
    ntfy_result = _send_ntfy(subject, ntfy_body, priority=ntfy_priority)

    return {
        "subject": subject,
        "email": email_result,
        "ntfy": ntfy_result,
    }
