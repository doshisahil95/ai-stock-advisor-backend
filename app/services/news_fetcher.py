"""News fetcher — call Tavily for each candidate, dedupe, persist to news_articles.

Uses Tavily's topic="news" mode for higher-signal results.
Falls back to a simpler query if the primary returns zero hits.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from pymongo.errors import DuplicateKeyError

from app.db.client import Collections
from app.models._common import _convert_decimals_to_decimal128, utcnow
from app.services.tavily_client import (
    TavilyError,
    TavilyQuotaExceeded,
    search as tavily_search,
)

log = logging.getLogger(__name__)

# Domains to exclude — pure stock-quote / aggregator pages with no news value.
# These return generic price snapshots that classify as 'noise' and waste credits.
_EXCLUDED_DOMAINS = [
    # Yahoo Finance — quote pages
    "in.finance.yahoo.com",
    "finance.yahoo.com",
    # Google Finance — quote pages
    "google.com",
    # Stock data / charting platforms
    "stockanalysis.com",
    "tradingview.com",
    "in.investing.com",
    "investing.com",
    # Indian stock listings (data, not news)
    "screener.in",
    "tickertape.in",
    "groww.in",
    "marketsmojo.com",
    "equitypandit.com",
    "moneymanthan.com",
    "5paisa.com",
    "indiainfoline.com",
    "trendlyne.com",
]

# URL-pattern exclusions for sites that have BOTH news AND noise pages.
# A URL containing any of these patterns is treated as low-signal.
_EXCLUDED_URL_PATTERNS = [
    "/stockpricequote/",
    "/share-price/",
    "/get-quotes/",
    "/quote/",
    "/finance/quote/",
    "/stock-share-price/",
    "/company-info/",
    "/equities/",
]


def _domain_of(url: str) -> str:
    try:
        netloc = urlparse(url).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return ""


def _url_path(url: str) -> str:
    try:
        return urlparse(url).path.lower()
    except Exception:
        return ""


def _is_low_signal_url(url: str) -> bool:
    """True if URL matches a known noise pattern beyond the domain check."""
    path = _url_path(url)
    return any(pat in path for pat in _EXCLUDED_URL_PATTERNS)


def _build_query(symbol: str, name: str) -> str:
    """Primary query — uses Tavily's news topic to find actual news articles.

    With topic="news", Tavily restricts to news sources and respects `days`.
    We just describe the company; no boolean operators (Tavily handles them
    inconsistently and they tend to dilute relevance).
    """
    clean_name = name
    for suffix in [" Limited", " Ltd", " Ltd.", " Corp", " Corporation"]:
        if clean_name.endswith(suffix):
            clean_name = clean_name[: -len(suffix)].strip()

    if clean_name and clean_name.upper() != symbol.upper():
        return f"{clean_name} ({symbol}) NSE"
    return f"{symbol} NSE India"


def _build_fallback_query(symbol: str, name: str) -> str:
    """Simpler query for the retry pass when primary returns 0 results."""
    if name:
        clean_name = name
        for suffix in [" Limited", " Ltd", " Ltd.", " Corp", " Corporation"]:
            if clean_name.endswith(suffix):
                clean_name = clean_name[: -len(suffix)].strip()
        return clean_name
    return f"{symbol} stock"


def _normalize_published_at(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    if isinstance(raw, str):
        for fmt in (
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S%z",
        ):
            try:
                d = datetime.strptime(raw, fmt)
                if d.tzinfo is None:
                    d = d.replace(tzinfo=timezone.utc)
                return d
            except ValueError:
                continue
        try:
            d = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _persist_results(
    results: list[dict],
    isin: str,
    symbol: str,
    stats: dict,
) -> None:
    """Persist Tavily results into news_articles with dedup by URL."""
    coll = Collections.news_articles()
    now = utcnow()

    for r in results:
        url = (r.get("url") or "").strip()
        if not url:
            continue

        domain = _domain_of(url)
        if domain in _EXCLUDED_DOMAINS:
            stats["skipped_excluded_domain"] += 1
            continue

        if _is_low_signal_url(url):
            stats["skipped_low_signal_url"] += 1
            continue

        title = (r.get("title") or "").strip()
        summary = (r.get("content") or r.get("snippet") or "").strip()
        score = r.get("score")
        try:
            score_f = float(score) if score is not None else None
        except (ValueError, TypeError):
            score_f = None
        published_at = _normalize_published_at(
            r.get("published_date") or r.get("published_at")
        )

        try:
            doc = {
                "url": url,
                "title": title,
                "source": domain,
                "summary": summary,
                "body_text": "",
                "tavily_score": score_f,
                "published_at": published_at,
                "fetched_at": now,
                "fetched_for_isins": [isin],
                "fetched_for_symbols": [symbol.upper()],
                "entities_isins": [isin],
                "entities_symbols": [symbol.upper()],
                "classified": False,
                "themes": [],
                "_schema_version": 1,
                "created_at": now,
                "updated_at": now,
            }
            coll.insert_one(_convert_decimals_to_decimal128(doc))
            stats["new_inserted"] += 1
        except DuplicateKeyError:
            coll.update_one(
                {"url": url},
                {
                    "$addToSet": {
                        "entities_isins": isin,
                        "entities_symbols": symbol.upper(),
                        "fetched_for_isins": isin,
                        "fetched_for_symbols": symbol.upper(),
                    },
                    "$set": {"updated_at": now},
                },
            )
            stats["merged_existing"] += 1


def fetch_for_instrument(
    isin: str,
    symbol: str,
    name: str,
    days: int = 30,
    use_case: str = "suggestions_news",
) -> dict:
    """Fetch news for one stock. Persist to news_articles. Returns stats.

    Strategy:
      1. Primary query with topic="news" + days filter
      2. If zero usable results, retry with simpler fallback query
    """
    stats = {
        "isin": isin,
        "symbol": symbol,
        "fetched": 0,
        "new_inserted": 0,
        "merged_existing": 0,
        "skipped_excluded_domain": 0,
        "skipped_low_signal_url": 0,
        "fallback_used": False,
        "error": None,
    }

    primary_query = _build_query(symbol, name)

    try:
        response = tavily_search(
            query=primary_query,
            use_case=use_case,
            search_depth="basic",
            topic="news",
            days=days,
            exclude_domains=_EXCLUDED_DOMAINS,
        )
    except TavilyQuotaExceeded:
        raise
    except (TavilyError, Exception) as exc:
        log.warning("Primary fetch failed for %s (%s): %s", symbol, isin, exc)
        stats["error"] = str(exc)
        return stats

    results = response.get("results", []) or []
    stats["fetched"] = len(results)
    _persist_results(results, isin, symbol, stats)

    # Fallback if we got nothing useful (zero results OR everything was filtered)
    inserted_or_merged = stats["new_inserted"] + stats["merged_existing"]
    if inserted_or_merged == 0:
        fallback_query = _build_fallback_query(symbol, name)
        if fallback_query != primary_query:
            log.info(
                "  No usable results for %s on primary; retrying with fallback: %s",
                symbol,
                fallback_query,
            )
            stats["fallback_used"] = True
            try:
                response = tavily_search(
                    query=fallback_query,
                    use_case=use_case + "_fallback",
                    search_depth="basic",
                    topic="news",
                    days=days,
                    exclude_domains=_EXCLUDED_DOMAINS,
                )
                fb_results = response.get("results", []) or []
                stats["fetched"] += len(fb_results)
                _persist_results(fb_results, isin, symbol, stats)
            except TavilyQuotaExceeded:
                raise
            except Exception as exc:
                log.warning("Fallback fetch failed for %s: %s", symbol, exc)

    log.info(
        "  News %s (%s): fetched=%d, new=%d, merged=%d, dom-excl=%d, url-excl=%d, fb=%s",
        symbol,
        isin,
        stats["fetched"],
        stats["new_inserted"],
        stats["merged_existing"],
        stats["skipped_excluded_domain"],
        stats["skipped_low_signal_url"],
        stats["fallback_used"],
    )
    return stats


def fetch_for_universe(
    instruments: list[dict],
    days: int = 30,
    use_case: str = "suggestions_news",
    stop_on_quota_exceeded: bool = True,
) -> dict:
    """Fetch news for many instruments sequentially."""
    aggregate = {
        "attempted": len(instruments),
        "succeeded": 0,
        "failed": 0,
        "total_fetched": 0,
        "total_new_inserted": 0,
        "total_merged": 0,
        "total_dom_excluded": 0,
        "total_url_excluded": 0,
        "fallback_count": 0,
        "quota_exceeded": False,
        "stopped_early_at": None,
        "per_stock_errors": [],
    }

    for i, inst in enumerate(instruments):
        isin = inst["isin"]
        symbol = inst["symbol"]
        name = inst.get("name", "")

        try:
            stats = fetch_for_instrument(
                isin, symbol, name, days=days, use_case=use_case
            )
            if stats["error"]:
                aggregate["failed"] += 1
                aggregate["per_stock_errors"].append(
                    {
                        "isin": isin,
                        "symbol": symbol,
                        "error": stats["error"],
                    }
                )
            else:
                aggregate["succeeded"] += 1
            aggregate["total_fetched"] += stats["fetched"]
            aggregate["total_new_inserted"] += stats["new_inserted"]
            aggregate["total_merged"] += stats["merged_existing"]
            aggregate["total_dom_excluded"] += stats["skipped_excluded_domain"]
            aggregate["total_url_excluded"] += stats["skipped_low_signal_url"]
            if stats["fallback_used"]:
                aggregate["fallback_count"] += 1

        except TavilyQuotaExceeded as exc:
            log.error(
                "Tavily quota exceeded at stock %d/%d: %s", i + 1, len(instruments), exc
            )
            aggregate["quota_exceeded"] = True
            aggregate["stopped_early_at"] = i
            if stop_on_quota_exceeded:
                break

    log.info(
        "News fetch complete: %d/%d succeeded, %d new, %d merged, "
        "%d dom-excl, %d url-excl, %d fallbacks used",
        aggregate["succeeded"],
        aggregate["attempted"],
        aggregate["total_new_inserted"],
        aggregate["total_merged"],
        aggregate["total_dom_excluded"],
        aggregate["total_url_excluded"],
        aggregate["fallback_count"],
    )
    return aggregate
