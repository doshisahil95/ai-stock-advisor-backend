"""End-to-end smoke test: load config, hit Anthropic, MongoDB, both ntfy paths, email."""

import time
from app.config.settings import settings
from app.services.notify import push_private, push_public, email
from anthropic import Anthropic
from anthropic._exceptions import OverloadedError, RateLimitError, APIStatusError
from pymongo import MongoClient


def call_anthropic_with_retry(client: Anthropic, max_retries: int = 5) -> str:
    """Call Anthropic with exponential backoff on transient errors."""
    for attempt in range(max_retries):
        try:
            msg = client.messages.create(
                model=settings.ANTHROPIC_MODEL_PRIMARY,
                max_tokens=50,
                messages=[
                    {"role": "user", "content": "Reply with exactly: 'Stack works.'"}
                ],
            )
            return msg.content[0].text.strip()
        except (OverloadedError, RateLimitError) as e:
            if attempt == max_retries - 1:
                raise
            wait = 2**attempt
            print(f"  ⚠ Anthropic {type(e).__name__} — retry in {wait}s")
            time.sleep(wait)
        except APIStatusError as e:
            if e.status_code in (502, 503, 504) and attempt < max_retries - 1:
                wait = 2**attempt
                print(f"  ⚠ Anthropic {e.status_code} — retry in {wait}s")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Anthropic retries exhausted")


def main() -> None:
    print("✓ Config loaded")
    print(f"  Anthropic key: {settings.ANTHROPIC_API_KEY[:15]}...")
    print(f"  Mongo host:    {settings.MONGODB_URI.split('@')[1].split('/')[0]}")
    print(f"  ntfy private:  {settings.NTFY_URL}")
    print(
        f"  ntfy public:   {settings.NTFY_PUBLIC_URL}/{settings.NTFY_PUBLIC_TOPIC_PRICE[:20]}..."
    )

    # Anthropic
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    reply = call_anthropic_with_retry(client)
    print(f"✓ Anthropic:    {reply}")

    # MongoDB
    mongo = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
    mongo.admin.command("ping")
    db = mongo[settings.MONGODB_DB_NAME]
    db.smoke_test.insert_one({"test": "ok"})
    db.smoke_test.delete_many({})
    print("✓ MongoDB:      ping ok, insert+delete ok")

    # Private ntfy (self-hosted via Tailscale Funnel)
    private_resp = push_private(
        topic="digests",
        title="🛠️ Smoke test (private)",
        message="Self-hosted ntfy works. Content stays on your EC2.",
        priority="default",
        tags=["lock"],
    )
    print(f"✓ ntfy private: id={private_resp.get('id')}")

    # Public ntfy.sh — instant iOS delivery
    public_resp = push_public(
        channel="price",
        title="🛠️ Smoke test (public)",
        message=f"Public ntfy.sh works with full content. Claude said: {reply}",
        priority="high",
        tags=["zap"],
    )
    print(f"✓ ntfy public:  id={public_resp.get('id')}")

    # Email
    email_resp = email(
        subject="Portfolio Advisor — smoke test",
        html=f"<h2>All systems go.</h2><p>Claude said: <em>{reply}</em></p>",
    )
    print(f"✓ Email:        id={email_resp.get('id')}")

    print("\n🎉 All checks passed.")
    print("\nExpect on your iPhone:")
    print(
        "  - 1 'private' notification in #digests (may show 'ntfy: new message' first)"
    )
    print("  - 1 'public' notification with FULL content visible in banner")


if __name__ == "__main__":
    main()
