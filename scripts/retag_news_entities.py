"""One-shot backfill: re-tag news_articles.entities_isins (master_todo #50).

Pre-#50, news_fetcher stamped the QUERY isin onto entities_isins for every
Tavily result with no relevance check, and the dedup $addToSet branch appended
OTHER companies' ISINs onto shared aggregator URLs. So entities_isins meant
"any query that surfaced this URL", not "companies this article is about" --
which leaked wrong-company news into the #27 chat, the news_score signal, the
dossier news block, and (going forward) the #57 news-alert evaluator.

This script re-derives entities_isins / entities_symbols for existing docs by
re-running the SAME deterministic matcher used at fetch time
(news_fetcher._article_mentions_company), so the two never drift. For each
article it considers only the companies in fetched_for_isins (provenance -- the
queries that actually surfaced the URL), resolves each ISIN to its instrument
name/symbol, and keeps a company's ISIN in entities_isins ONLY if the article
title/summary references it.

Provenance (fetched_for_isins / fetched_for_symbols) is NEVER modified.

Pre-production cleanup: safe to run against the live collection before GO-LIVE
(#42). Always --dry-run first.

Usage:
  # Preview what would change (no writes)
  PYTHONPATH=. uv run python scripts/retag_news_entities.py --dry-run

  # Apply
  PYTHONPATH=. uv run python scripts/retag_news_entities.py
"""

from __future__ import annotations

import argparse
import logging
import sys

from app.db.client import Collections
from app.models._common import utcnow
from app.services.news_fetcher import _article_mentions_company

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


def _load_instrument_index() -> dict[str, dict]:
    """isin -> {symbol, name} for every instrument (single lookup pass)."""
    idx: dict[str, dict] = {}
    for inst in Collections.instruments().find(
        {}, {"_id": 0, "isin": 1, "symbol": 1, "name": 1}
    ):
        isin = inst.get("isin")
        if isin:
            idx[isin] = {
                "symbol": (inst.get("symbol") or "").upper(),
                "name": inst.get("name") or "",
            }
    return idx


def _recompute_entities(
    article: dict, instr_idx: dict[str, dict]
) -> tuple[list[str], list[str]]:
    """Return (entities_isins, entities_symbols) the article SHOULD carry.

    Only companies in fetched_for_isins are candidates (provenance); each is
    kept only if the article text references it via the shared matcher.
    """
    title = article.get("title", "") or ""
    summary = article.get("summary", "") or ""
    fetched_isins = article.get("fetched_for_isins", []) or []

    keep_isins: list[str] = []
    keep_symbols: list[str] = []
    for isin in fetched_isins:
        meta = instr_idx.get(isin)
        if meta is None:
            # Unknown instrument -- we cannot verify the mention, so we drop it
            # from entities (provenance is untouched). Conservative: a name we
            # can't resolve should not be asserted as "about".
            continue
        if _article_mentions_company(title, summary, meta["symbol"], meta["name"]):
            keep_isins.append(isin)
            if meta["symbol"]:
                keep_symbols.append(meta["symbol"])

    # Stable + de-duplicated.
    keep_isins = list(dict.fromkeys(keep_isins))
    keep_symbols = list(dict.fromkeys(keep_symbols))
    return keep_isins, keep_symbols


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Re-tag news_articles.entities_isins via the #50 matcher"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process at most N articles (debugging)",
    )
    args = parser.parse_args()

    coll = Collections.news_articles()
    instr_idx = _load_instrument_index()
    log.info("Loaded %d instruments for name/symbol resolution", len(instr_idx))

    cursor = coll.find(
        {},
        {
            "_id": 1,
            "title": 1,
            "summary": 1,
            "fetched_for_isins": 1,
            "entities_isins": 1,
            "entities_symbols": 1,
        },
    )
    if args.limit:
        cursor = cursor.limit(args.limit)

    now = utcnow()
    scanned = 0
    changed = 0
    stripped_isin_total = 0
    emptied = 0

    for art in cursor:
        scanned += 1
        old_isins = art.get("entities_isins", []) or []
        new_isins, new_symbols = _recompute_entities(art, instr_idx)

        if set(new_isins) == set(old_isins):
            continue

        changed += 1
        removed = set(old_isins) - set(new_isins)
        stripped_isin_total += len(removed)
        if not new_isins:
            emptied += 1

        log.info(
            "  %s: entities_isins %s -> %s (removed %s)",
            art["_id"],
            old_isins,
            new_isins,
            sorted(removed) if removed else [],
        )

        if not args.dry_run:
            coll.update_one(
                {"_id": art["_id"]},
                {
                    "$set": {
                        "entities_isins": new_isins,
                        "entities_symbols": new_symbols,
                        "updated_at": now,
                    }
                },
            )

    mode = "DRY-RUN (no writes)" if args.dry_run else "APPLIED"
    log.info("=" * 70)
    log.info(" Re-tag complete [%s]", mode)
    log.info("   scanned:            %d", scanned)
    log.info("   changed:            %d", changed)
    log.info("   ISIN tags stripped: %d", stripped_isin_total)
    log.info("   emptied entities:   %d", emptied)
    log.info("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
