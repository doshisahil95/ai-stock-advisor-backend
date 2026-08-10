"""Wrappers for ntfy push notifications and Resend email.

Notification paths:
- push_public(): public ntfy.sh service with random unguessable topics.
  For time-critical alerts (price, news, F4 cron-health errors) AND for
  digest delivery. Instant full-content iOS push.
- email(): Resend transactional email. Returns {ok, id, error}; never
  raises (Section A2 part 1 wrapper contract).

F2b (2026-05-18): self-hosted ntfy via Tailscale Funnel was retired
because iOS poll-based delivery dropped digests silently. Public ntfy.sh
with unguessable topics is the only live push transport.
"""

import logging
import time
from typing import Literal

import requests
import resend

from app.config.settings import settings

log = logging.getLogger(__name__)

PublicChannel = Literal["price", "news", "errors", "digests"]

_PRIORITY_MAP = {"min": 1, "low": 2, "default": 3, "high": 4, "urgent": 5}

resend.api_key = settings.RESEND_API_KEY


def _parse_cc_recipients(primary: str) -> list[str]:
    """Parse settings.RESEND_CC into a clean BCC list (master_todo #83 / #60 Part A).

    RESEND_CC is a comma-separated string in the secrets file. Split on commas,
    strip whitespace, drop empty entries, de-duplicate (preserving order), and
    exclude the primary recipient so it is never both To and Bcc. Returns [] when
    RESEND_CC is unset — in that case email() adds no bcc key and behavior is
    byte-identical to pre-#83. Additive-only: RESEND_TO stays the single primary.
    """
    seen: set[str] = set()
    if primary:
        seen.add(primary.strip().lower())
    out: list[str] = []
    for raw in settings.RESEND_CC.split(","):
        addr = raw.strip()
        if not addr:
            continue
        key = addr.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(addr)
    return out


# ─────────────────────────────────────────────────────────────────────
# Resend transient-failure retry (master_todo #20, P3-4 — Phase 6)
# ─────────────────────────────────────────────────────────────────────
# email() runs in cron AND in the sync-Uvicorn request threadpool, so the
# backoff below is a BLOCKING time.sleep that ties up one worker thread for
# its whole duration. On the single-user box that is acceptable, so we keep
# it conservative: ONE retry (2 attempts total) with a fixed 30s backoff —
# worst-case ~30s of added latency on a single thread, well inside anyio's
# default 40-thread pool.
#
# Only transient failures are retried: HTTP 429 (rate limited) and 5xx
# (Resend-side). 400s and every other client error are PERMANENT and are
# returned immediately — retrying them would just burn another 30s for the
# same failure. Non-HTTP errors (e.g. a requests timeout that carries no
# status) are also not retried, staying within the "transient 5xx / 429"
# scope of #20.
#
# The {ok, id, error} contract is unchanged and no exception is ever raised:
# callers (digest_delivery._send_email, reconciliation._send_drift_alerts,
# scripts/cron_health_check dual-transport) all branch on result["ok"].
_EMAIL_SEND_MAX_ATTEMPTS = 2  # 1 initial send + 1 retry
_EMAIL_RETRY_BACKOFF_SECONDS = 30
_TRANSIENT_EMAIL_STATUSES = frozenset({429, 500, 502, 503, 504})
_TRANSIENT_EMAIL_ERROR_TYPES = frozenset(
    {"rate_limit_exceeded", "internal_server_error", "application_error"}
)


def _email_error_status(exc: Exception) -> int | None:
    """Best-effort HTTP status from a Resend SDK exception.

    resend>=2.4 raises typed ResendErrors that carry the HTTP status code on
    ``.code`` (and on ``.status_code`` in some versions). Read whichever is an
    int (or an all-digit string). Returns None when no status can be
    determined — that is treated as non-transient (not retried).
    """
    for attr in ("status_code", "code"):
        val = getattr(exc, attr, None)
        if isinstance(val, bool):  # bool is an int subclass — never a status
            continue
        if isinstance(val, int):
            return val
        if isinstance(val, str) and val.isdigit():
            return int(val)
    return None


def _is_transient_email_error(exc: Exception) -> bool:
    """True only for retryable transient Resend failures (429 + 5xx).

    400s and other client errors are permanent and return False. Falls back to
    the SDK's string ``error_type`` so we still classify correctly if the
    status code is not exposed as an int on a given SDK version.
    """
    if _email_error_status(exc) in _TRANSIENT_EMAIL_STATUSES:
        return True
    error_type = getattr(exc, "error_type", None)
    return isinstance(error_type, str) and error_type in _TRANSIENT_EMAIL_ERROR_TYPES


def _publish(
    base_url: str,
    topic: str,
    title: str,
    message: str,
    priority: str,
    tags: list[str] | None,
    auth_header: str | None,
) -> dict:
    """Internal: POST to ntfy's JSON publish endpoint."""
    payload = {
        "topic": topic,
        "title": title,
        "message": message,
        "priority": _PRIORITY_MAP.get(priority, 3),
        "tags": tags or [],
    }
    headers = {"Content-Type": "application/json"}
    if auth_header:
        headers["Authorization"] = auth_header
    response = requests.post(base_url, json=payload, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()


def push_public(
    channel: PublicChannel,
    title: str,
    message: str,
    priority: str = "default",
    tags: list[str] | None = None,
) -> dict:
    """Send via public ntfy.sh with random unguessable topics.

    Use for time-critical alerts. iOS delivery is instant with full content
    in the notification banner. Trade-off: ntfy.sh + APNs see the content.

    channel: 'price' | 'news' | 'errors' (F4 cron health)
    """
    topic_map = {
        "price": settings.NTFY_PUBLIC_TOPIC_PRICE,
        "news": settings.NTFY_PUBLIC_TOPIC_NEWS,
        "errors": settings.NTFY_PUBLIC_TOPIC_ERRORS,
        "digests": settings.NTFY_PUBLIC_TOPIC_DIGESTS,
    }
    topic = topic_map[channel]  # Literal type guarantees this is a valid key
    return _publish(
        base_url=settings.NTFY_PUBLIC_URL,
        topic=topic,
        title=title,
        message=message,
        priority=priority,
        tags=tags,
        auth_header=None,  # public topics use unguessability as auth
    )


def email(
    subject: str,
    html: str,
    to: str | None = None,
    text: str | None = None,
    include_cc: bool = True,
) -> dict:
    """Send an email via Resend.

    Args:
        subject: Email subject line.
        html: HTML body. Required.
        to: Recipient address. Defaults to settings.RESEND_TO.
        text: Optional plain-text body. When provided, Resend sends
            multipart/alternative so non-HTML clients render correctly.
        include_cc: When True (default), any addresses in settings.RESEND_CC
            are added as BCC recipients (de-duped, primary excluded) so digests
            and drift alerts fan out to an advisor/spouse. Pass False for
            operator-only mail (cron-health) so it stays author-only. When
            RESEND_CC is unset this flag has no observable effect (master_todo
            #83 / #60 Part A).

    Returns:
        dict shaped {"ok": bool, "id": str | None, "error": str | None}.
        On success, "id" is the Resend message id and "error" is None.
        On failure, "ok" is False, "id" is None, "error" carries the
        exception message. Callers should not raise on email failure —
        digest delivery is best-effort and the delivery audit row
        records the outcome.

    A2 (Chat 5): consolidates Resend traffic so digest_delivery._send_email
    can delegate here instead of reimplementing the resend.Emails.send
    call inline. Return shape mirrors what _send_email used to return
    so the digest_deliveries audit row schema is preserved.

    #20 (Phase 6): transient failures (HTTP 429 / 5xx) are retried once
    after a blocking 30s backoff; 400s and other client errors are returned
    immediately. The {ok, id, error} contract and the no-raise guarantee are
    unchanged — see the module-level retry notes above.
    """
    primary = to or settings.RESEND_TO
    payload: dict[str, object] = {
        "from": settings.RESEND_FROM,
        "to": primary,
        "subject": subject,
        "html": html,
    }
    if text is not None:
        payload["text"] = text
    # #83 (#60 Part A): fan extra recipients out via BCC (hidden from each
    # other). Only when opted-in AND RESEND_CC is non-empty — otherwise no bcc
    # key is added and the send is byte-identical to pre-#83.
    if include_cc:
        bcc = _parse_cc_recipients(primary)
        if bcc:
            payload["bcc"] = bcc

    last_error: str | None = None
    for attempt in range(1, _EMAIL_SEND_MAX_ATTEMPTS + 1):
        try:
            response = resend.Emails.send(payload)
            return {
                "ok": True,
                "id": response.get("id") if isinstance(response, dict) else None,
                "error": None,
            }
        except Exception as exc:
            last_error = str(exc)
            if _is_transient_email_error(exc) and attempt < _EMAIL_SEND_MAX_ATTEMPTS:
                log.warning(
                    "Resend email failed (attempt %d/%d, status=%s); "
                    "retrying in %ds: %s",
                    attempt,
                    _EMAIL_SEND_MAX_ATTEMPTS,
                    _email_error_status(exc),
                    _EMAIL_RETRY_BACKOFF_SECONDS,
                    last_error,
                )
                time.sleep(_EMAIL_RETRY_BACKOFF_SECONDS)
                continue
            # Permanent error (e.g. 400), unknown error shape, or the retry
            # budget is exhausted: return the contract dict, never raise.
            return {"ok": False, "id": None, "error": last_error}

    # Unreachable (the loop always returns) but keeps the contract explicit.
    return {"ok": False, "id": None, "error": last_error}
