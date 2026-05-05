"""Idempotent index creation.

Run once at app startup. PyMongo's create_index is idempotent — if an index
with the same key spec already exists it's a no-op.
"""

from __future__ import annotations

import logging

from pymongo import ASCENDING, DESCENDING, IndexModel

from app.db.client import Collections

log = logging.getLogger(__name__)


def ensure_all_indexes() -> dict[str, list[str]]:
    """Create every index our app expects. Returns {collection: [index_names]}."""
    results: dict[str, list[str]] = {}

    # ── transactions ─────────────────────────────────────────────────────────
    results["transactions"] = Collections.transactions().create_indexes(
        [
            IndexModel(
                [("isin", ASCENDING), ("trade_date", DESCENDING)],
                name="isin_trade_date_desc",
            ),
            IndexModel([("trade_date", DESCENDING)], name="trade_date_desc"),
            IndexModel(
                [("type", ASCENDING), ("isin", ASCENDING), ("trade_date", ASCENDING)],
                name="type_isin_trade_date_asc",  # used for FIFO depletion
            ),
            IndexModel([("source_ref", ASCENDING)], name="source_ref"),
        ]
    )

    # ── holdings ─────────────────────────────────────────────────────────────
    # Unique on isin among non-deleted (partial index)
    results["holdings"] = Collections.holdings().create_indexes(
        [
            IndexModel(
                [("isin", ASCENDING)],
                name="isin_unique_active",
                unique=True,
                partialFilterExpression={"deleted_at": None},
            ),
            IndexModel([("deleted_at", ASCENDING)], name="deleted_at"),
            IndexModel([("sector", ASCENDING)], name="sector"),
            IndexModel([("tags", ASCENDING)], name="tags"),
        ]
    )

    # ── monitored_stocks ─────────────────────────────────────────────────────
    results["monitored_stocks"] = Collections.monitored_stocks().create_indexes(
        [
            IndexModel(
                [("isin", ASCENDING)],
                name="isin_unique_active",
                unique=True,
                partialFilterExpression={"status": "tracking"},
            ),
            IndexModel([("status", ASCENDING)], name="status"),
            IndexModel([("conviction", DESCENDING)], name="conviction_desc"),
            IndexModel(
                [("last_user_interest_at", DESCENDING)], name="last_user_interest_desc"
            ),
        ]
    )

    # ── news_articles ────────────────────────────────────────────────────────
    results["news_articles"] = Collections.news_articles().create_indexes(
        [
            IndexModel([("url", ASCENDING)], name="url_unique", unique=True),
            IndexModel([("published_at", DESCENDING)], name="published_desc"),
            IndexModel(
                [("entities_isins", ASCENDING), ("published_at", DESCENDING)],
                name="isins_published_desc",
            ),
            IndexModel(
                [("entities_symbols", ASCENDING), ("published_at", DESCENDING)],
                name="symbols_published_desc",
            ),
            IndexModel([("themes", ASCENDING)], name="themes"),
            IndexModel([("source", ASCENDING)], name="source"),
            # TTL on body_text — actually, we can't TTL a single field, so we'll
            # purge body_text via a scheduled job that runs daily. Index helps the job:
            IndexModel([("body_purged_at", ASCENDING)], name="body_purged_at"),
        ]
    )

    # ── alerts_log ───────────────────────────────────────────────────────────
    results["alerts_log"] = Collections.alerts_log().create_indexes(
        [
            IndexModel([("sent_at", DESCENDING)], name="sent_at_desc"),
            IndexModel(
                [("isin", ASCENDING), ("sent_at", DESCENDING)],
                name="isin_sent_desc",
            ),
            IndexModel([("alert_type", ASCENDING)], name="alert_type"),
            IndexModel([("delivery_status", ASCENDING)], name="delivery_status"),
        ]
    )

    # ── digests ──────────────────────────────────────────────────────────────
    results["digests"] = Collections.digests().create_indexes(
        [
            IndexModel(
                [("for_date", DESCENDING), ("digest_type", ASCENDING)],
                name="for_date_type",
            ),
            IndexModel([("generated_at", DESCENDING)], name="generated_at_desc"),
        ]
    )

    # ── prices_daily ─────────────────────────────────────────────────────────
    results["prices_daily"] = Collections.prices_daily().create_indexes(
        [
            IndexModel(
                [("isin", ASCENDING), ("date", DESCENDING)],
                name="isin_date_unique",
                unique=True,
            ),
            IndexModel([("date", DESCENDING)], name="date_desc"),
            IndexModel(
                [("symbol", ASCENDING), ("date", DESCENDING)], name="symbol_date_desc"
            ),
        ]
    )

    # ── macro_signals ────────────────────────────────────────────────────────
    results["macro_signals"] = Collections.macro_signals().create_indexes(
        [
            IndexModel([("date", DESCENDING)], name="date_unique", unique=True),
        ]
    )

    # ── conversations ────────────────────────────────────────────────────────
    results["conversations"] = Collections.conversations().create_indexes(
        [
            IndexModel([("created_at", DESCENDING)], name="created_at_desc"),
            IndexModel(
                [("intent", ASCENDING), ("created_at", DESCENDING)],
                name="intent_created_desc",
            ),
            IndexModel(
                [("related_entities_isins", ASCENDING), ("created_at", DESCENDING)],
                name="isins_created_desc",
            ),
            IndexModel([("related_holding_id", ASCENDING)], name="related_holding"),
        ]
    )

    # ── instruments ──────────────────────────────────────────────────────────
    results["instruments"] = Collections.instruments().create_indexes(
        [
            IndexModel(
                [("exchange", ASCENDING), ("symbol", ASCENDING)],
                name="exchange_symbol_unique",
                unique=True,
            ),
            IndexModel([("isin", ASCENDING)], name="isin"),
            IndexModel([("last_seen_at", DESCENDING)], name="last_seen_at_desc"),
            IndexModel([("last_changed_at", DESCENDING)], name="last_changed_at_desc"),
        ]
    )

    # ── symbol_overrides ─────────────────────────────────────────────────────
    results["symbol_overrides"] = Collections.symbol_overrides().create_indexes(
        [
            IndexModel(
                [("source_broker", ASCENDING), ("source_symbol", ASCENDING)],
                name="broker_symbol_unique",
                unique=True,
            ),
        ]
    )

    # ── reconciliation_snapshots ─────────────────────────────────────────────
    results["reconciliation_snapshots"] = (
        Collections.reconciliation_snapshots().create_indexes(
            [
                IndexModel([("taken_at", DESCENDING)], name="taken_at_desc"),
                IndexModel(
                    [("type", ASCENDING), ("taken_at", DESCENDING)],
                    name="type_taken_at_desc",
                ),
                IndexModel(
                    [("has_drift", ASCENDING), ("taken_at", DESCENDING)],
                    name="drift_taken_at_desc",
                ),
            ]
        )
    )

    return results
