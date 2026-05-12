"""Tavily client wrapper with retry, quota tracking, and a hard daily ceiling.

We use Tavily PAYG. Cost is metered per credit:
  - basic search    = 1 credit
  - advanced search = 2 credits

This module is the ONLY place that should call Tavily directly. All callers
(news fetcher, future agent search tool, future corp action poller) go
through `search()`. That gives us:
  - One quota counter (persisted to Mongo so it survives restarts)
  - One retry policy
  - One place to apply the daily call ceiling
  - One place to log all calls for cost auditing

Quota tracking is per UTC day. Each call increments the day's counter
BEFORE the request fires, so a crash doesn't lose the count. If the
counter exceeds settings.TAVILY_DAILY_CALL_LIMIT, we raise TavilyQuotaExceeded
and the caller decides what to do.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from pymongo import ReturnDocument

from app.config.settings import settings
from app.db.client import Collections

log = logging.getLogger(__name__)

# Lazy-import the Tavily SDK so test environments without it can still
# import this module (they'll fail at call time, not import time).
_tavily_client = None


def _get_client():
    """Lazy-init the Tavily SDK client. Cached at module level."""
    global _tavily_client
    if _tavily_client is None:
        from tavily import TavilyClient

        _tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)
    return _tavily_client


class TavilyQuotaExceeded(Exception):
    """Raised when the daily Tavily call ceiling has been hit."""


class TavilyError(Exception):
    """Raised on Tavily API errors that are not quota-related."""


# ── Quota tracking ───────────────────────────────────────────────────────────


def _today_utc_str() -> str:
    """Today's date in UTC as YYYY-MM-DD."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _increment_quota(use_case: str, credits: int) -> int:
    """Atomically bump today's call counter. Returns the NEW total calls today.

    We track:
      - calls_today: total request count
      - credits_today: estimated credits used (basic=1, advanced=2)
      - per_use_case: breakdown by caller for diagnostics
    """
    today = _today_utc_str()
    result = Collections.tavily_quota().find_one_and_update(
        {"date_utc": today},
        {
            "$inc": {
                "calls_today": 1,
                "credits_today": credits,
                f"per_use_case.{use_case}.calls": 1,
                f"per_use_case.{use_case}.credits": credits,
            },
            "$setOnInsert": {
                "date_utc": today,
                "first_call_at": datetime.now(timezone.utc),
            },
            "$set": {
                "last_call_at": datetime.now(timezone.utc),
            },
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return result["calls_today"]


def get_today_quota() -> dict:
    """Read today's quota state. Returns a doc-shaped dict (or zero state if no calls yet)."""
    today = _today_utc_str()
    doc = Collections.tavily_quota().find_one({"date_utc": today})
    if not doc:
        return {
            "date_utc": today,
            "calls_today": 0,
            "credits_today": 0,
            "per_use_case": {},
        }
    return doc


def get_quota_history(days: int = 7) -> list[dict]:
    """Last N days of quota usage. Newest first."""
    return list(
        Collections.tavily_quota().find({}, {"_id": 0}).sort("date_utc", -1).limit(days)
    )


# ── Search ───────────────────────────────────────────────────────────────────


def search(
    query: str,
    use_case: str,
    max_results: int | None = None,
    search_depth: str | None = None,
    days: int | None = None,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    max_retries: int = 2,
    retry_backoff_sec: float = 2.0,
) -> dict:
    """Execute one Tavily search.

    Args:
        query: search string
        use_case: short identifier for quota breakdown ("news_fetch", "agent", etc.)
        max_results: how many results to return (defaults to settings)
        search_depth: "basic" (1 credit) or "advanced" (2 credits)
        days: restrict results to last N days (Tavily-specific param)
        include_domains: list of domains to restrict to
        exclude_domains: list of domains to exclude
        max_retries: how many times to retry on transient errors
        retry_backoff_sec: backoff multiplier between retries

    Returns:
        Tavily's response dict, normalized. Has keys: query, answer (optional),
        results (list of {title, url, content, score, published_date?}).

    Raises:
        TavilyQuotaExceeded: if daily ceiling hit
        TavilyError: on persistent API failure
    """
    depth = search_depth or settings.TAVILY_SEARCH_DEPTH
    n_results = (
        max_results
        if max_results is not None
        else settings.TAVILY_MAX_RESULTS_PER_QUERY
    )
    credits = 2 if depth == "advanced" else 1

    # Pre-flight quota check (read-only, fast)
    pre_check = get_today_quota()
    if pre_check["calls_today"] >= settings.TAVILY_DAILY_CALL_LIMIT:
        raise TavilyQuotaExceeded(
            f"Daily Tavily call ceiling hit: {pre_check['calls_today']} >= "
            f"{settings.TAVILY_DAILY_CALL_LIMIT}. Resets at 00:00 UTC."
        )

    # Increment counter BEFORE the call (so a crash doesn't undercount)
    new_total = _increment_quota(use_case, credits)
    log.info(
        "Tavily search [%s, %s, %d credits] (%d/%d today): %s",
        use_case,
        depth,
        credits,
        new_total,
        settings.TAVILY_DAILY_CALL_LIMIT,
        query[:80] + ("..." if len(query) > 80 else ""),
    )

    client = _get_client()
    last_exc: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            kwargs: dict[str, Any] = {
                "query": query,
                "max_results": n_results,
                "search_depth": depth,
            }
            if days is not None:
                kwargs["days"] = days
            if include_domains:
                kwargs["include_domains"] = include_domains
            if exclude_domains:
                kwargs["exclude_domains"] = exclude_domains

            response = client.search(**kwargs)
            return response

        except Exception as exc:
            last_exc = exc
            err_str = str(exc).lower()
            # Quota / rate limit on Tavily side — surface as quota exceeded
            if "quota" in err_str or "rate" in err_str or "429" in err_str:
                log.warning("Tavily quota/rate error: %s", exc)
                raise TavilyQuotaExceeded(f"Tavily API quota error: {exc}") from exc
            log.warning(
                "Tavily search failed (attempt %d/%d): %s",
                attempt + 1,
                max_retries + 1,
                exc,
            )
            if attempt < max_retries:
                time.sleep(retry_backoff_sec * (attempt + 1))

    raise TavilyError(
        f"Tavily search failed after {max_retries + 1} attempts: {last_exc}"
    )
