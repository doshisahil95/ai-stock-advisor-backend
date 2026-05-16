"""Centralized settings.

Looks for secrets in this order:
1. /etc/portfolio-advisor/secrets.env (production on EC2)
2. ./.env (local development on Mac)
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

EC2_SECRETS = Path("/etc/portfolio-advisor/secrets.env")
LOCAL_SECRETS = Path(__file__).resolve().parents[2] / ".env"

SECRETS_FILE = EC2_SECRETS if EC2_SECRETS.exists() else LOCAL_SECRETS


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(SECRETS_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Anthropic
    ANTHROPIC_API_KEY: str
    ANTHROPIC_MODEL_PRIMARY: str = "claude-sonnet-4-5"
    ANTHROPIC_MODEL_FAST: str = "claude-haiku-4-5"

    # Tavily
    TAVILY_API_KEY: str
    # Per-fetch limits (defensive — Tavily PAYG has spending cap, but we cap calls too)
    TAVILY_MAX_RESULTS_PER_QUERY: int = 5
    TAVILY_SEARCH_DEPTH: str = "basic"  # "basic" = 1 credit; "advanced" = 2 credits
    TAVILY_DAILY_CALL_LIMIT: int = 200  # Hard ceiling per UTC day across all use cases

    # MongoDB
    MONGODB_URI: str
    MONGODB_DB_NAME: str = "portfolio"

    # Self-hosted ntfy (for digests + errors — sensitive content)
    NTFY_URL: str
    NTFY_USER: str
    NTFY_PASS: str

    # Public ntfy.sh (for time-critical alerts — instant push with full content)
    NTFY_PUBLIC_URL: str = "https://ntfy.sh"
    NTFY_PUBLIC_TOPIC_PRICE: str
    NTFY_PUBLIC_TOPIC_NEWS: str
    NTFY_PUBLIC_TOPIC_ERRORS: str  # F4: cron health alerts (instant iOS push)

    # Resend
    RESEND_API_KEY: str
    RESEND_FROM: str
    RESEND_TO: str

    # Server binding
    TAILSCALE_IP: str = "100.112.20.41"
    API_PORT: int = 8000


settings = Settings()
