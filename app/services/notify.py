"""Wrappers for ntfy push notifications and Resend email.

Two notification paths:
- push_private(): self-hosted ntfy via Tailscale Funnel. For sensitive content
  (digests, errors). Slower iOS delivery.
- push_public(): public ntfy.sh service with random unguessable topics.
  For time-critical alerts (price, news, F4 cron-health errors). Instant
  full-content iOS push.
"""

from typing import Literal

import requests
import resend
from base64 import b64encode

from app.config.settings import settings

PrivateTopic = Literal["digests", "errors"]
PublicChannel = Literal["price", "news", "errors", "digests"]

_NTFY_AUTH = b64encode(f"{settings.NTFY_USER}:{settings.NTFY_PASS}".encode()).decode()
_PRIORITY_MAP = {"min": 1, "low": 2, "default": 3, "high": 4, "urgent": 5}

resend.api_key = settings.RESEND_API_KEY


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


def push_private(
    topic: PrivateTopic,
    title: str,
    message: str,
    priority: str = "default",
    tags: list[str] | None = None,
) -> dict:
    """Send via self-hosted ntfy (Tailscale Funnel).

    Use for sensitive content. iOS delivery is slower (poll-based) but content
    never touches public infrastructure.

    Topics: 'digests', 'errors'
    """
    return _publish(
        base_url=settings.NTFY_URL,
        topic=topic,
        title=title,
        message=message,
        priority=priority,
        tags=tags,
        auth_header=f"Basic {_NTFY_AUTH}",
    )


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
) -> dict:
    """Send an email via Resend.

    Args:
        subject: Email subject line.
        html: HTML body. Required.
        to: Recipient address. Defaults to settings.RESEND_TO.
        text: Optional plain-text body. When provided, Resend sends
            multipart/alternative so non-HTML clients render correctly.

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
    """
    try:
        payload: dict[str, object] = {
            "from": settings.RESEND_FROM,
            "to": to or settings.RESEND_TO,
            "subject": subject,
            "html": html,
        }
        if text is not None:
            payload["text"] = text
        response = resend.Emails.send(payload)
        return {
            "ok": True,
            "id": response.get("id") if isinstance(response, dict) else None,
            "error": None,
        }
    except Exception as exc:
        return {"ok": False, "id": None, "error": str(exc)}
