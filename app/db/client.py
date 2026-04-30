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


# ── Typed collection accessors ───────────────────────────────────────────────
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


def ping() -> bool:
    """Quick connectivity check. Returns True if Atlas responds."""
    try:
        get_client().admin.command("ping")
        return True
    except Exception:
        return False
