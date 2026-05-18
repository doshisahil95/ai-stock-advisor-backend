"""MongoDB client singleton and collection accessors.

One connection pool for the whole app. PyMongo's MongoClient is thread-safe
and pooled by default; we just keep a module-level singleton.

Index management is handled separately in `app/db/indexes.py` and called
once at app startup.
"""

from __future__ import annotations

from functools import lru_cache

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from app.config.settings import settings


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    """Singleton Mongo client. Created on first call, reused afterwards."""
    return MongoClient(
        settings.MONGODB_URI,
        # Reasonable defaults for a single-app, single-DB setup
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=10000,
        maxPoolSize=20,
        minPoolSize=2,
        retryWrites=True,
        appname="portfolio-advisor",
    )


def get_db() -> Database:
    """The single database we use."""
    return get_client()[settings.MONGODB_DB_NAME]


# ─── Typed collection accessors ─────────────────────────────────────
# Use these everywhere instead of get_db().some_collection — gives autocomplete
# and a single place to rename if we ever need to.


class Collections:
    """Strongly named collection getters."""

    @staticmethod
    def user_profile() -> Collection:
        return get_db()["user_profile"]

    @staticmethod
    def transactions() -> Collection:
        return get_db()["transactions"]

    @staticmethod
    def holdings() -> Collection:
        return get_db()["holdings"]

    @staticmethod
    def monitored_stocks() -> Collection:
        return get_db()["monitored_stocks"]

    @staticmethod
    def news_articles() -> Collection:
        return get_db()["news_articles"]

    @staticmethod
    def alerts_log() -> Collection:
        return get_db()["alerts_log"]

    @staticmethod
    def digests() -> Collection:
        return get_db()["digests"]

    @staticmethod
    def prices_daily() -> Collection:
        return get_db()["prices_daily"]

    @staticmethod
    def macro_signals() -> Collection:
        return get_db()["macro_signals"]

    @staticmethod
    def conversations() -> Collection:
        return get_db()["conversations"]

    @staticmethod
    def instruments() -> Collection:
        return get_db()["instruments"]

    @staticmethod
    def symbol_overrides() -> Collection:
        return get_db()["symbol_overrides"]

    @staticmethod
    def transactions_staging() -> Collection:
        """Staging area for bulk imports — validated before promote."""
        return get_db()["transactions_staging"]

    @staticmethod
    def reconciliation_snapshots():
        return get_db()["reconciliation_snapshots"]

    @staticmethod
    def prices_intraday():
        return get_db()["prices_intraday"]

    @staticmethod
    def cost_basis_adjustments() -> Collection:
        return get_db()["cost_basis_adjustments"]

    @staticmethod
    def transactions_audit() -> Collection:
        return get_db()["transactions_audit"]

    @staticmethod
    def monitored_stocks_audit() -> Collection:
        """Append-only audit trail for monitored_stocks feedback writes (F10).

        One doc per /suggestions/{isin}/feedback call. Written BEFORE the
        monitored_stocks update is applied so the intent is preserved even
        if the apply step crashes. Mirrors transactions_audit pattern.
        """
        return get_db()["monitored_stocks_audit"]

    # ─── Phase 2: Suggestions Engine ────────────────────────────────

    @staticmethod
    def instruments_fundamentals() -> Collection:
        """Per-ISIN fundamentals snapshots (yfinance, weekly refresh)."""
        return get_db()["instruments_fundamentals"]

    @staticmethod
    def suggestion_runs() -> Collection:
        """One doc per weekly suggestions cron run (append-only)."""
        return get_db()["suggestion_runs"]

    @staticmethod
    def suggestion_outcomes() -> Collection:
        """Tracking record per suggestion across its 180-day lifecycle."""
        return get_db()["suggestion_outcomes"]

    @staticmethod
    def tavily_quota() -> Collection:
        """Daily Tavily quota tracking (one doc per UTC date)."""
        return get_db()["tavily_quota"]

    @staticmethod
    def digest_deliveries() -> Collection:
        """Per-run digest delivery log (one doc per Sunday cron, success or failure)."""
        return get_db()["digest_deliveries"]

    # ─── F4: Cron health monitoring ─────────────────────────────────

    @staticmethod
    def earnings_calendar() -> Collection:
        """Upcoming + historical earnings events per ISIN (F14).

        Source = yfinance Ticker.calendar, refreshed weekly alongside
        fundamentals. One doc per (isin, earnings_date). Consumed by
        suggestion_engine gates/signals (buy-side skip if earnings in
        next 5 days; sell-side penalty in the same window).
        """
        return get_db()["earnings_calendar"]

    @staticmethod
    def cron_heartbeats() -> Collection:
        """One doc per cron run with start/finish/status/error/metadata.

        TTL'd at 60 days via indexes.py. Read by /cron/heartbeats endpoint and
        by scripts/cron_health_check.py.
        """
        return get_db()["cron_heartbeats"]


def ping() -> bool:
    """Quick connectivity check. Returns True if Atlas responds."""
    try:
        get_client().admin.command("ping")
        return True
    except Exception:
        return False
