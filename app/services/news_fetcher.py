"""News fetcher — call Tavily for each candidate, dedupe, persist to news_articles.

Usage pattern:
  for instrument in candidates:
      n = fetch_for_instrument(isin, symbol, name, days=30)
  ...

Dedup strategy:
  Each article is inserted with `url` as the unique key. If the same URL
  is returned again (e.g., RELIANCE story also surfaces in TCS search),
  we $addToSet the new ISIN/symbol to entities_isins/entities_symbols
  AND fetched_for_isins/fetched_for_symbols. No new doc, no overwrite.

Failure handling:
  - One stock failing does NOT abort the whole run.
  - Tavily quota exceeded propagates up (caller decides whether to abort).
  - Per-stock errors are logged and counted in the returned stats.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from pymongo import UpdateOne
from pymongo.errors import DuplicateKeyError

from app.db.client import Collections
from app.models._common import _convert_decimals_to_decimal128, utcnow
from app.services.tavily_client import (
    TavilyError,
    TavilyQuotaExceeded,
    search as tavily_search,
)

log = logging.getLogger(__name__)

# Domains we deliberately don't want to index — pure aggregator pages, low signal
_EXCLUDED_DOMAINS = [
    "in.finance.yahoo.com",
    "finance.yahoo.com",
    "stockanalysis.com",
    "tradingview.com",
]


def _domain_of(url: str) -> str:
    """Extract bare domain from a URL. Empty string if parse fails."""
    try:
        netloc = urlparse(url).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return ""


def _build_query(symbol: str, name: str) -> str:
    """Compose a Tavily query for one stock.

    Heuristic: company name is more discriminating than ticker symbol
    (NSE tickers can be ambiguous — "INFY" vs Infosys, "DLF" the company,
    "BPCL" both common). Use both, prefer name.
    """
    # Strip common suffixes from name to keep query tight
    clean_name = name
    for suffix in [" Limited", " Ltd", " Ltd.", " Corp", " Corporation"]:
        if clean_name.endswith(suffix):
            clean_name = clean_name[: -len(suffix)].strip()

    if clean_name:
        return f'"{clean_name}" OR "{symbol}" stock NSE India news'
    return f'"{symbol}" stock NSE India news'


def _normalize_published_at(raw: Any) -> datetime | None:
    """Tavily returns published_date in various shapes. Normalize to tz-aware UTC."""
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    if isinstance(raw, str):
        # Common shapes: "2026-05-09", "2026-05-09T14:30:00Z", "Wed, 09 May 2026 ..."
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
        # Fallback: try fromisoformat (handles +00:00 style)
        try:
            d = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def fetch_for_instrument(
    isin: str,
    symbol: str,
    name: str,
    days: int = 30,
    use_case: str = "suggestions_news",
) -> dict:
    """Fetch news for one stock. Persist to news_articles. Returns stats.

    Args:
        isin, symbol, name: stock identity
        days: how many recent days of news to ask Tavily for
        use_case: identifier for Tavily quota breakdown

    Returns:
        {"isin": ..., "symbol": ..., "fetched": N, "new_inserted": N,
         "merged_existing": N, "skipped_excluded_domain": N, "error": str|None}
    """
    stats = {
        "isin": isin,
        "symbol": symbol,
        "fetched": 0,
        "new_inserted": 0,
        "merged_existing": 0,
        "skipped_excluded_domain": 0,
        "error": None,
    }

    query = _build_query(symbol, name)

    try:
        response = tavily_search(
            query=query,
            use_case=use_case,
            search_depth="basic",
            days=days,
            exclude_domains=_EXCLUDED_DOMAINS,
        )
    except TavilyQuotaExceeded:
        # Propagate — orchestrator decides what to do
        raise
    except (TavilyError, Exception) as exc:
        log.warning("Fetch failed for %s (%s): %s", symbol, isin, exc)
        stats["error"] = str(exc)
        return stats

    results = response.get("results", []) or []
    stats["fetched"] = len(results)

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

        # Try insert. On duplicate URL, $addToSet the entities/triggers
        # so the article is "linked" to this stock too.
        try:
            doc = {
                "url": url,
                "title": title,
                "source": domain,
                "summary": summary,
                "body_text": "",  # we don't store full content for now
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
            # Article exists from a prior fetch (possibly for a different stock).
            # Merge this stock into its entity sets without overwriting anything else.
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

    log.info(
        "  News %s (%s): fetched=%d, new=%d, merged=%d, excluded=%d",
        symbol,
        isin,
        stats["fetched"],
        stats["new_inserted"],
        stats["merged_existing"],
        stats["skipped_excluded_domain"],
    )
    return stats


def fetch_for_universe(
    instruments: list[dict],
    days: int = 30,
    use_case: str = "suggestions_news",
    stop_on_quota_exceeded: bool = True,
) -> dict:
    """Fetch news for many instruments sequentially.

    Args:
        instruments: list of {isin, symbol, name} dicts
        days: news recency window
        use_case: Tavily quota use_case
        stop_on_quota_exceeded: if True, return early on quota error

    Returns:
        Aggregate stats dict.
    """
    aggregate = {
        "attempted": len(instruments),
        "succeeded": 0,
        "failed": 0,
        "total_fetched": 0,
        "total_new_inserted": 0,
        "total_merged": 0,
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

        except TavilyQuotaExceeded as exc:
            log.error(
                "Tavily quota exceeded at stock %d/%d: %s", i + 1, len(instruments), exc
            )
            aggregate["quota_exceeded"] = True
            aggregate["stopped_early_at"] = i
            if stop_on_quota_exceeded:
                break

    log.info(
        "News fetch complete: %d/%d succeeded, %d total inserted, %d merged",
        aggregate["succeeded"],
        aggregate["attempted"],
        aggregate["total_new_inserted"],
        aggregate["total_merged"],
    )
    return aggregate
