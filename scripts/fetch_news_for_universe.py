"""Fetch + classify news for the suggestion universe.

#75 U4-d: the LIVE crontab runs this WEEKLY on Sunday 06:30 IST
(`30 6 * * 0 ... --include-held`), 30 min before the 07:00 suggestions run, so
news is fresh BEFORE the Sunday morning digest. (An earlier docstring said
"daily"; that never matched the crontab.)

Three-phase (as of #50 + #57):
  1. fetch_for_universe: Tavily calls, persist to news_articles (rule-gate on
     entities_isins via _article_mentions_company in news_fetcher)
  2. classify_unclassified: Anthropic Haiku classifies anything new
  2b. confirm_entities_llm: Haiku entity-confirmation for (article, company)
     pairs the rule-gate was uncertain about (additive: only adds ISINs)
  3. evaluate_news_alerts: fire ntfy alerts for held+watchlist names on
     high-severity fresh news (depends on #50 entity accuracy)

Usage:
  # Production weekly run (Sunday 06:30 IST via cron)
  PYTHONPATH=. uv run python scripts/fetch_news_for_universe.py --include-held

  # Smoke test on 5 stocks
  PYTHONPATH=. uv run python scripts/fetch_news_for_universe.py --limit 5

  # Just classify what's already fetched
  PYTHONPATH=. uv run python scripts/fetch_news_for_universe.py --skip-fetch

  # Just fetch, no classification
  PYTHONPATH=. uv run python scripts/fetch_news_for_universe.py --skip-classify
"""

from __future__ import annotations

import argparse
import logging
import sys

from app.db.client import Collections
from app.services.cron_heartbeat_service import cron_run
from app.services.news_alerts import evaluate_news_alerts
from app.services.news_classifier import classify_unclassified, confirm_entities_llm
from app.services.news_fetcher import fetch_for_universe
from app.services.suggestion_engine import get_watchlist_isins
from app.services.tavily_client import get_today_quota

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


def get_universe_for_news() -> list[dict]:
    """NIFTY 100 minus held (we only need news for stocks we don't own)."""
    held_isins = set(
        h["isin"]
        for h in Collections.holdings().find(
            {"deleted_at": None},
            {"_id": 0, "isin": 1},
        )
    )
    cursor = Collections.instruments().find(
        {"in_nifty100": True, "isin": {"$nin": list(held_isins)}},
        {"_id": 0, "isin": 1, "symbol": 1, "name": 1, "exchange": 1},
    )
    return list(cursor)


def get_watchlist_for_news() -> list[dict]:
    """Watchlisted ISINs resolved to instrument dicts for news fetch (F13).

    Reuses suggestion_engine.get_watchlist_isins() -- the single source of
    truth for watchlist membership (status=="watchlist") -- and resolves to
    {isin, symbol, name, exchange}. Folded into the fetch universe by main()
    so watchlist names (typically outside NIFTY 100) get news + Haiku
    classification like any other candidate. Part of the F13 data-volume
    multiplier: each name consumes one Tavily call/run (TD33 daily quota).
    """
    isins = get_watchlist_isins()
    if not isins:
        return []
    return list(
        Collections.instruments().find(
            {"isin": {"$in": list(isins)}},
            {"_id": 0, "isin": 1, "symbol": 1, "name": 1, "exchange": 1},
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch + classify news for the suggestion universe"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Limit to first N stocks"
    )
    parser.add_argument("--days", type=int, default=30, help="News recency window")
    parser.add_argument(
        "--skip-fetch", action="store_true", help="Skip Tavily fetch, only classify"
    )
    parser.add_argument(
        "--skip-classify",
        action="store_true",
        help="Skip Anthropic classify, only fetch",
    )
    parser.add_argument(
        "--include-held",
        action="store_true",
        help="Also fetch news for currently-held stocks",
    )
    args = parser.parse_args()

    with cron_run("fetch_news_for_universe") as hb:
        hb.metadata["limit"] = args.limit
        hb.metadata["days"] = args.days
        hb.metadata["skip_fetch"] = args.skip_fetch
        hb.metadata["skip_classify"] = args.skip_classify
        hb.metadata["include_held"] = args.include_held

        print("=" * 70)
        print(" News fetch + classification")
        print("=" * 70)

        if not args.skip_fetch:
            if args.include_held:
                cursor = Collections.instruments().find(
                    {"in_nifty100": True},
                    {"_id": 0, "isin": 1, "symbol": 1, "name": 1, "exchange": 1},
                )
                universe = list(cursor)
            else:
                universe = get_universe_for_news()

            # F13: fold in watchlisted ISINs (status=="watchlist") regardless
            # of branch -- watchlist names are typically outside NIFTY 100 and
            # would otherwise never get news. Deduped by ISIN. Data-volume
            # multiplier: each added name consumes one Tavily call/run against
            # the daily quota (TD33), which stops the run early if exceeded.
            seen = {u["isin"] for u in universe}
            for inst in get_watchlist_for_news():
                if inst["isin"] not in seen:
                    seen.add(inst["isin"])
                    universe.append(inst)

            if args.limit:
                universe = universe[: args.limit]

            print(
                f"\nPhase 1: Fetching news for {len(universe)} stocks (last {args.days}d)"
            )
            print(
                f"  Tavily quota before: {get_today_quota().get('calls_today', 0)} calls today\n"
            )

            fetch_stats = fetch_for_universe(universe, days=args.days)

            hb.metadata["fetch_attempted"] = fetch_stats["attempted"]
            hb.metadata["fetch_succeeded"] = fetch_stats["succeeded"]
            hb.metadata["fetch_failed"] = fetch_stats["failed"]
            hb.metadata["articles_new"] = fetch_stats["total_new_inserted"]
            hb.metadata["articles_merged"] = fetch_stats["total_merged"]
            if fetch_stats.get("quota_exceeded"):
                hb.metadata["quota_exceeded"] = True
                hb.metadata["stopped_early_at"] = fetch_stats["stopped_early_at"]

            print()
            print(f"  Attempted:   {fetch_stats['attempted']}")
            print(f"  Succeeded:   {fetch_stats['succeeded']}")
            print(f"  Failed:      {fetch_stats['failed']}")
            print(
                f"  Articles:    {fetch_stats['total_fetched']} fetched, "
                f"{fetch_stats['total_new_inserted']} new, {fetch_stats['total_merged']} merged"
            )
            if fetch_stats.get("quota_exceeded"):
                print(
                    f"  WARN — Tavily quota exceeded -- stopped at stock {fetch_stats['stopped_early_at']}"
                )

            quota = get_today_quota()
            hb.metadata["tavily_calls_today"] = quota.get("calls_today", 0)
            hb.metadata["tavily_credits_today"] = quota.get("credits_today", 0)
            print(
                f"  Tavily quota after:  {quota.get('calls_today', 0)} calls, "
                f"~{quota.get('credits_today', 0)} credits today"
            )
        else:
            print("\nPhase 1: SKIPPED (--skip-fetch)")

        if not args.skip_classify:
            print(f"\nPhase 2: Classifying unclassified articles")
            cls_stats = classify_unclassified(only_recent_days=35)

            hb.metadata["classify_found"] = cls_stats["found_unclassified"]
            hb.metadata["classify_done"] = cls_stats["classified"]
            hb.metadata["classify_batches"] = cls_stats["batches"]
            hb.metadata["classify_failed_batches"] = cls_stats["failed_batches"]

            print()
            print(f"  Found unclassified: {cls_stats['found_unclassified']}")
            print(f"  Classified:         {cls_stats['classified']}")
            print(
                f"  Batches:            {cls_stats['batches']} ({cls_stats['failed_batches']} failed)"
            )
            print(f"  Model:              {cls_stats['model']}")

            # master_todo #50 Phase 2b: LLM entity-confirmation for (article,
            # company) pairs the rule-gate rejected conservatively. Additive --
            # only adds ISINs back into entities_isins, never strips them.
            # Guarded so a Haiku failure here can't fail the classify step.
            try:
                ec_stats = confirm_entities_llm(only_recent_days=35)
                hb.metadata["entity_confirm_pairs_checked"] = ec_stats["pairs_checked"]
                hb.metadata["entity_confirm_pairs_confirmed"] = ec_stats["pairs_confirmed"]
                if ec_stats["pairs_checked"]:
                    print(
                        f"\nPhase 2b: Entity confirmation"
                        f"\n  Pairs checked:  {ec_stats['pairs_checked']}"
                        f"\n  Confirmed:      {ec_stats['pairs_confirmed']}"
                        f"\n  Rejected:       {ec_stats['pairs_rejected']}"
                        f"\n  Batches:        {ec_stats['batches']}"
                        f" ({ec_stats['failed_batches']} failed)"
                    )
            except Exception:
                log.exception("confirm_entities_llm failed after classification")
                hb.metadata["entity_confirm_error"] = True

            # master_todo #57: fire news alerts for names the user cares about
            # (held with "news" in alert_on UNION watchlist) on the freshly
            # classified, entity-correct (#50) articles. Runs only when we
            # classified this pass. Guarded so an alerting failure can never
            # fail the cron's primary job (fetch + classify) -- mirrors the
            # #41/#56 guarded caller in refresh_prices_intraday.py.
            try:
                alerts_fired = evaluate_news_alerts()
                hb.metadata["news_alerts_fired"] = alerts_fired
                print(f"  News alerts fired:  {alerts_fired}")
            except Exception:
                log.exception("evaluate_news_alerts failed after classification")
                hb.metadata["news_alerts_error"] = True
        else:
            print("\nPhase 2: SKIPPED (--skip-classify)")

        print()
        print("=" * 70)
        print(" Done")
        print("=" * 70)
        return 0


if __name__ == "__main__":
    sys.exit(main())
