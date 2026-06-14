"""Conversation service (#27, Chat 6) — on-demand market-data enrichment.

`ensure_stock_context(isin)` guarantees the per-stock reference data the chat
needs — instrument identity, fundamentals, upcoming earnings, recent classified
news — exists and is reasonably fresh, fetching on demand when it is missing or
stale. This is the shared substrate behind POST /chat/holdings/{isin}, so a name
can be researched whether or not it is a current holding (the user's
"if I'm researching it, it's to buy" requirement).

Design / invariants:
- REUSES the existing cron-path services verbatim (fundamentals_service,
  news_fetcher, news_classifier, instrument_service). No parallel fetch/persist
  logic is introduced.
- Writes ONLY to the Phase-2 reference collections (instruments_fundamentals,
  earnings_calendar, news_articles) via those services — exactly what the weekly
  cron writes. It never touches Phase-1 portfolio data (holdings, transactions).
  The held/position overlay is layered separately by the chat service (Unit 3).
- Freshness gates keep a chat turn cheap: already-fresh data skips straight
  through with no external (yfinance / Tavily / Anthropic) calls.

This module is the buy-research data layer only — the structured Sonnet call,
Conversation persistence, and prompt assembly land in Unit 3.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from app.db.client import Collections
from app.models._common import utcnow
from app.services import (
    fundamentals_service,
    instrument_service,
    news_classifier,
    news_fetcher,
)
from app.services.tavily_client import TavilyQuotaExceeded

log = logging.getLogger(__name__)

# Fundamentals are considered fresh within this window (mirror the scoring
# engine's fundamentals_service.DEFAULT_FRESHNESS_DAYS = 14).
FUNDAMENTALS_MAX_AGE_DAYS = 14

# News surfaced to the model: same 30d window the buy dossier uses.
NEWS_LOOKBACK_DAYS = 30
# Don't re-hit Tavily if we already pulled this name within this window. A
# recently-attempted fetch (even one that produced nothing) counts, so we don't
# burn quota re-fetching the same stock every chat turn.
NEWS_REFETCH_AFTER_DAYS = 7
# Cap on classified articles fed into the prompt (mirror the dossier's limit).
NEWS_DISPLAY_LIMIT = 8

# Earnings calendar: if we refreshed (any outcome) within this window, trust it
# rather than re-querying yfinance every turn for names with no upcoming event.
EARNINGS_REFRESH_AFTER_DAYS = 14

_NEWS_PROJECTION = {
    "_id": 1,
    "title": 1,
    "url": 1,
    "source": 1,
    "summary": 1,
    "published_at": 1,
    "fetched_at": 1,
    "sentiment": 1,
    "sentiment_confidence": 1,
    "themes": 1,
    "severity": 1,
    "classifier_summary": 1,
}


# ── Identity ────────────────────────────────────────────────────────────────
def _resolve_identity(isin: str) -> dict | None:
    """ISIN -> {isin, symbol, name, exchange} from the instruments master.

    None if the ISIN is not a known NSE instrument (caller returns 404). We do
    NOT attempt a yfinance rescue: the master holds the full NSE equity list, so
    a miss almost always means a bad ISIN rather than a real gap, and yfinance is
    symbol-keyed (it cannot resolve from an ISIN alone).
    """
    instr = instrument_service.lookup_by_isin(isin)
    if not instr:
        return None
    return {
        "isin": isin,
        "symbol": instr.get("symbol", ""),
        "name": instr.get("name", ""),
        "exchange": instr.get("exchange", "NSE"),
    }


# ── Fundamentals ────────────────────────────────────────────────────────────
def _ensure_fundamentals(identity: dict) -> tuple[dict | None, str]:
    """Return (fundamentals_doc_or_None, status).

    status: fresh | refreshed | stale | unavailable
    """
    isin = identity["isin"]
    existing = fundamentals_service.get_latest_for_isin(isin)
    if fundamentals_service.is_fresh(existing, FUNDAMENTALS_MAX_AGE_DAYS):
        return existing, "fresh"

    refreshed = fundamentals_service.refresh_one(
        isin, identity["symbol"], identity["exchange"]
    )
    if refreshed is None:
        # Fetch failed; serve whatever stale doc we have, if any.
        return existing, ("stale" if existing else "unavailable")

    # Re-read so downstream sees the canonical persisted (Decimal128) shape.
    return fundamentals_service.get_latest_for_isin(isin), "refreshed"


# ── Earnings ────────────────────────────────────────────────────────────────
def _earnings_recently_refreshed(isin: str) -> bool:
    cutoff = utcnow() - timedelta(days=EARNINGS_REFRESH_AFTER_DAYS)
    return (
        Collections.earnings_calendar().find_one(
            {"isin": isin, "fetched_at": {"$gte": cutoff}}, {"_id": 1}
        )
        is not None
    )


def _ensure_earnings(identity: dict) -> tuple[datetime | None, str]:
    """Return (next_earnings_date_or_None, status).

    status: on_file | none_upcoming | refreshed | refresh_failed
    """
    isin = identity["isin"]
    nxt = fundamentals_service.get_next_earnings_for_isin(isin)
    if nxt is not None:
        return nxt, "on_file"
    if _earnings_recently_refreshed(isin):
        return None, "none_upcoming"

    try:
        fundamentals_service.refresh_earnings_for(
            isin, identity["symbol"], identity["exchange"]
        )
    except Exception as exc:  # yfinance hiccup — non-fatal for a chat turn
        log.warning("earnings refresh failed for %s: %s", isin, exc)
        return None, "refresh_failed"

    return fundamentals_service.get_next_earnings_for_isin(isin), "refreshed"


# ── News ────────────────────────────────────────────────────────────────────
def _classified_news(isin: str) -> list[dict]:
    cutoff = utcnow() - timedelta(days=NEWS_LOOKBACK_DAYS)
    cursor = (
        Collections.news_articles()
        .find(
            {
                "entities_isins": isin,
                "classified": True,
                "fetched_at": {"$gte": cutoff},
            },
            _NEWS_PROJECTION,
        )
        .sort("fetched_at", -1)
        .limit(NEWS_DISPLAY_LIMIT)
    )
    return list(cursor)


def _news_recently_fetched(isin: str) -> bool:
    cutoff = utcnow() - timedelta(days=NEWS_REFETCH_AFTER_DAYS)
    return (
        Collections.news_articles().find_one(
            {"entities_isins": isin, "fetched_at": {"$gte": cutoff}}, {"_id": 1}
        )
        is not None
    )


def _ensure_news(identity: dict) -> tuple[list[dict], str]:
    """Return (classified_news_list, status).

    status: cached | fetched | quota_exceeded | fetch_failed
    """
    isin = identity["isin"]
    if _news_recently_fetched(isin):
        return _classified_news(isin), "cached"

    try:
        news_fetcher.fetch_for_instrument(isin, identity["symbol"], identity["name"])
    except TavilyQuotaExceeded:
        log.warning("Tavily quota exceeded; serving cached news for %s", isin)
        return _classified_news(isin), "quota_exceeded"
    except Exception as exc:
        log.warning("news fetch failed for %s: %s", isin, exc)
        return _classified_news(isin), "fetch_failed"

    # Classify just the freshly-fetched articles for this ISIN.
    try:
        news_classifier.classify_unclassified(isin_filter=[isin], only_recent_days=35)
    except Exception as exc:
        log.warning("news classify failed for %s: %s", isin, exc)

    return _classified_news(isin), "fetched"


# ── Orchestrator ────────────────────────────────────────────────────────────
def ensure_stock_context(isin: str) -> dict:
    """Ensure + return read-mostly market context for one ISIN.

    Returns {"isin", "resolved": False} when the ISIN is not a known instrument.
    Otherwise returns identity + fundamentals + earnings + classified news, each
    with a status flag so the caller (and tests) can see whether data was served
    warm or fetched on demand.
    """
    code = isin.upper()
    identity = _resolve_identity(code)
    if identity is None:
        return {"isin": code, "resolved": False}

    fundamentals, f_status = _ensure_fundamentals(identity)
    next_earnings, e_status = _ensure_earnings(identity)
    news, n_status = _ensure_news(identity)

    # sector / industry live on the fundamentals doc, not the instruments master.
    if fundamentals:
        identity["sector"] = fundamentals.get("sector", "") or ""
        identity["industry"] = fundamentals.get("industry", "") or ""

    return {
        "resolved": True,
        **identity,
        "fundamentals": fundamentals,
        "fundamentals_status": f_status,
        "next_earnings": next_earnings,
        "earnings_status": e_status,
        "news": news,
        "news_status": n_status,
    }
