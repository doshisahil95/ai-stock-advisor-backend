"""Suggestion engine — orchestrates one full weekly run (Unit 3).

Adds outcome creation + delivery hooks vs Unit 2.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta

from app.db.client import Collections
from app.models._common import utcnow
from app.models.suggestion import SuggestionRun
from app.services.digest_delivery import send_weekly_digest
from app.services.dossier_service import generate_dossiers_for_top_k
from app.services.fundamentals_service import (
    DEFAULT_FRESHNESS_DAYS,
    get_latest_bulk as get_fundamentals_bulk,
    is_fresh as is_fundamentals_fresh,
)
from app.services.news_signals import compute_news_signals_bulk
from app.services.outcome_tracker import create_outcomes_for_run
from app.services.price_service import get_price_history
from app.services.scoring_service import (
    DEFAULT_CONFIG,
    score_candidates,
)

log = logging.getLogger(__name__)

PRICE_HISTORY_DAYS = 252


def build_universe() -> list[dict]:
    cursor = Collections.instruments().find(
        {"in_nifty100": True},
        {"_id": 0, "isin": 1, "symbol": 1, "exchange": 1, "name": 1},
    )
    return list(cursor)


def get_held_isins() -> set[str]:
    cursor = Collections.holdings().find(
        {"deleted_at": None},
        {"_id": 0, "isin": 1},
    )
    return {d["isin"] for d in cursor}


def get_rejected_isins(rejection_window_days: int = 90) -> set[str]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=rejection_window_days)
    cursor = Collections.monitored_stocks().find(
        {
            "status": "rejected",
            "rejected_at": {"$gte": cutoff},
        },
        {"_id": 0, "isin": 1},
    )
    return {d["isin"] for d in cursor}


def filter_universe(
    universe: list[dict],
    held: set[str],
    rejected: set[str],
) -> tuple[list[dict], dict[str, int]]:
    filtered: list[dict] = []
    counts = {"held": 0, "rejected": 0}
    for inst in universe:
        if inst["isin"] in held:
            counts["held"] += 1
            continue
        if inst["isin"] in rejected:
            counts["rejected"] += 1
            continue
        filtered.append(inst)
    return filtered, counts


def filter_by_data_freshness(
    candidates: list[dict],
    fundamentals_by_isin: dict[str, dict],
    price_history_by_isin: dict[str, list[dict]],
    fundamentals_max_age_days: int = DEFAULT_FRESHNESS_DAYS,
    price_max_age_days: int = 5,
) -> tuple[list[dict], int]:
    filtered: list[dict] = []
    dropped = 0
    now = datetime.now(timezone.utc)

    for c in candidates:
        isin = c["isin"]
        fundamentals = fundamentals_by_isin.get(isin)
        prices = price_history_by_isin.get(isin, [])

        if not is_fundamentals_fresh(fundamentals, fundamentals_max_age_days):
            log.info("  Drop %s (%s): fundamentals stale or missing", c["symbol"], isin)
            dropped += 1
            continue

        if not prices:
            log.info("  Drop %s (%s): no price history", c["symbol"], isin)
            dropped += 1
            continue

        latest_pdate = prices[0].get("date")
        if latest_pdate is None:
            log.info("  Drop %s (%s): latest price missing date", c["symbol"], isin)
            dropped += 1
            continue
        if latest_pdate.tzinfo is None:
            latest_pdate = latest_pdate.replace(tzinfo=timezone.utc)
        age_days = (now - latest_pdate).total_seconds() / 86400.0
        if age_days > price_max_age_days:
            log.info(
                "  Drop %s (%s): latest price %.1fd old (max %d)",
                c["symbol"],
                isin,
                age_days,
                price_max_age_days,
            )
            dropped += 1
            continue

        filtered.append(c)
    return filtered, dropped


def load_price_histories(
    isins: list[str],
    days: int = PRICE_HISTORY_DAYS,
) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for isin in isins:
        history = get_price_history(isin, days=days)
        out[isin] = history
    return out


def _today_ist_str() -> str:
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc + timedelta(hours=5, minutes=30)
    return now_ist.strftime("%Y-%m-%d")


def run_suggestions(
    config: dict | None = None,
    run_type: str = "manual",
    limit: int | None = None,
    dry_run: bool = False,
    top_k_override: int | None = None,
    skip_dossiers: bool = False,
    notify: bool = False,
) -> SuggestionRun:
    """Execute one full suggestions run end-to-end.

    Args:
        notify: if True (production runs), send email + ntfy AND create
                outcome-tracking records. Default False so manual/testing
                runs do not spam delivery.
    """
    cfg = config or DEFAULT_CONFIG
    if top_k_override is not None:
        cfg = {**cfg, "top_k": top_k_override}

    started_at = utcnow()
    log.info(
        "=== Suggestions run starting (run_type=%s, dry_run=%s, skip_dossiers=%s, notify=%s) ===",
        run_type,
        dry_run,
        skip_dossiers,
        notify,
    )

    run = SuggestionRun(
        run_date=started_at,
        run_date_ist=_today_ist_str(),
        run_type=run_type if not dry_run else "dry_run",
        status="running",
        started_at=started_at,
        config=cfg,
        top_k=cfg["top_k"],
    )

    try:
        universe = build_universe()
        run.universe_size = len(universe)
        log.info("Universe: %d NIFTY 100 stocks", len(universe))

        if limit:
            universe = universe[:limit]
            log.info("  --limit applied: %d stocks", len(universe))

        held = get_held_isins()
        rejected = get_rejected_isins()
        filtered, exclusions = filter_universe(universe, held, rejected)
        run.excluded_held = exclusions["held"]
        run.excluded_rejected = exclusions["rejected"]
        log.info(
            "Excluded: %d held, %d rejected -> %d candidates pre-data-check",
            exclusions["held"],
            exclusions["rejected"],
            len(filtered),
        )

        isins = [c["isin"] for c in filtered]
        log.info("Loading fundamentals for %d candidates", len(isins))
        fundamentals_map = get_fundamentals_bulk(isins)
        log.info("  Fundamentals loaded: %d/%d", len(fundamentals_map), len(isins))

        log.info("Loading price history for %d candidates", len(isins))
        price_map = load_price_histories(isins, days=PRICE_HISTORY_DAYS)
        loaded_prices = sum(1 for v in price_map.values() if v)
        log.info("  Price histories loaded: %d/%d", loaded_prices, len(isins))

        log.info("Computing news signals for %d candidates", len(isins))
        news_map = compute_news_signals_bulk(isins, window_days=30)
        candidates_with_news = sum(1 for s in news_map.values() if s.get("has_news"))
        log.info("  Candidates with news: %d/%d", candidates_with_news, len(isins))

        filtered, stale_dropped = filter_by_data_freshness(
            filtered,
            fundamentals_map,
            price_map,
            fundamentals_max_age_days=cfg["freshness"]["fundamentals_max_age_days"],
            price_max_age_days=cfg["freshness"]["prices_max_age_days"],
        )
        run.excluded_stale_data = stale_dropped
        run.candidates_considered = len(filtered)
        log.info("After freshness filter: %d candidates", len(filtered))

        if not filtered:
            run.status = "failed"
            run.error = "Zero candidates after filtering -- check data freshness"
            run.finished_at = utcnow()
            log.error(run.error)
            if not dry_run:
                _persist_run(run)
            return run

        log.info("Scoring %d candidates", len(filtered))
        scored = score_candidates(filtered, fundamentals_map, price_map, news_map, cfg)
        eligible_count = sum(1 for s in scored if s.gates_failed == 0)
        run.candidates_post_gates = eligible_count
        log.info("  Eligible after gates: %d", eligible_count)

        top_k = cfg["top_k"]
        run.all_candidates = scored
        run.top_candidates = [s for s in scored if s.gates_failed == 0][:top_k]

        if not skip_dossiers and run.top_candidates:
            log.info(
                "Generating dossiers for top %d candidates", len(run.top_candidates)
            )
            dossiers = generate_dossiers_for_top_k(
                run.top_candidates,
                fundamentals_map,
            )
            run.notes = _serialize_dossiers(dossiers)
        else:
            log.info(
                "Skipping dossiers (skip_dossiers=%s, top=%d)",
                skip_dossiers,
                len(run.top_candidates),
            )

        run.status = "success" if eligible_count > 0 else "partial"
        run.finished_at = utcnow()

        if not dry_run:
            inserted_id = _persist_run(run)

            if notify and run.top_candidates:
                # 1. Create outcome-tracking records
                try:
                    create_outcomes_for_run(
                        inserted_id, run.run_date, run.top_candidates
                    )
                except Exception as exc:
                    log.error("create_outcomes_for_run failed: %s", exc)

                # 2. Send email + ntfy digest
                try:
                    delivery = send_weekly_digest(run)
                    log.info("Digest delivery result: %s", delivery)
                except Exception as exc:
                    log.error("send_weekly_digest failed: %s", exc)

        log.info("=== Top candidates ===")
        for c in run.top_candidates[:5]:
            log.info(
                "  #%d %s (%s) -- composite=%.1f conf=%.0f Q=%.0f V=%.0f M=%.0f N=%.0f",
                c.rank,
                c.symbol,
                c.isin,
                c.composite_score,
                c.confidence_score,
                c.quality_score,
                c.valuation_score,
                c.momentum_score,
                c.news_score,
            )

        return run

    except Exception as exc:
        log.exception("Suggestions run failed")
        run.status = "failed"
        run.error = f"{type(exc).__name__}: {exc}"
        run.finished_at = utcnow()
        if not dry_run:
            _persist_run(run)
        raise


def _serialize_dossiers(dossiers: list[dict]) -> str:
    return json.dumps({"dossiers": dossiers}, default=str)


def _persist_run(run: SuggestionRun):
    """Insert the SuggestionRun. Returns the inserted _id (ObjectId)."""
    doc = run.to_mongo()
    result = Collections.suggestion_runs().insert_one(doc)
    log.info("Persisted SuggestionRun id=%s status=%s", result.inserted_id, run.status)
    return result.inserted_id


def get_latest_run() -> dict | None:
    return Collections.suggestion_runs().find_one(
        {"status": {"$in": ["success", "partial"]}},
        sort=[("run_date", -1)],
    )
