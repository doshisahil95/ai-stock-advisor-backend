"""Suggestion engine — orchestrates one full weekly run.

This is the single entry point invoked by the cron. It:
  1. Builds the candidate universe (NIFTY 100 minus held minus rejected)
  2. Reads fundamentals + price history in bulk
  3. Calls scoring_service.score_candidates() (pure function)
  4. Persists the SuggestionRun doc

Notification (email / ntfy) and dossier generation (Claude) are NOT here —
those land in Units 2 and 3. Unit 1 produces the ranked list and persists
it; reading the run doc with mongosh confirms it works.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from app.db.client import Collections
from app.models._common import _convert_decimals_to_decimal128, utcnow
from app.models.suggestion import SuggestionRun
from app.services.fundamentals_service import (
    DEFAULT_FRESHNESS_DAYS,
    get_latest_bulk as get_fundamentals_bulk,
    is_fresh as is_fundamentals_fresh,
)
from app.services.price_service import get_price_history
from app.services.scoring_service import (
    DEFAULT_CONFIG,
    score_candidates,
)

log = logging.getLogger(__name__)

# How many trading days of price history we read per candidate.
# 252 = ~1 trading year, sufficient for 52w high/low + 6M return + momentum signals.
PRICE_HISTORY_DAYS = 252

# ── Universe building ────────────────────────────────────────────────────────


def build_universe() -> list[dict]:
    """Return the NIFTY 100 universe as list of {isin, symbol, exchange, name, sector}.

    Reads from `instruments` where in_nifty100 = true.
    """
    cursor = Collections.instruments().find(
        {"in_nifty100": True},
        {"_id": 0, "isin": 1, "symbol": 1, "exchange": 1, "name": 1},
    )
    return list(cursor)


def get_held_isins() -> set[str]:
    """ISINs the user currently holds (active, non-deleted)."""
    cursor = Collections.holdings().find(
        {"deleted_at": None},
        {"_id": 0, "isin": 1},
    )
    return {d["isin"] for d in cursor}


def get_rejected_isins(rejection_window_days: int = 90) -> set[str]:
    """ISINs the user has rejected within the last `rejection_window_days`.

    Rejections are stored in `monitored_stocks` with status="rejected" and a
    `rejected_at` timestamp. Time-bound: a rejection from > 90 days ago no
    longer excludes the stock.
    """
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
    """Drop held + rejected stocks. Returns (filtered_list, exclusion_counts)."""
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


# ── Data freshness filtering ─────────────────────────────────────────────────


def filter_by_data_freshness(
    candidates: list[dict],
    fundamentals_by_isin: dict[str, dict],
    price_history_by_isin: dict[str, list[dict]],
    fundamentals_max_age_days: int = DEFAULT_FRESHNESS_DAYS,
    price_max_age_days: int = 5,
) -> tuple[list[dict], int]:
    """Drop candidates with stale or missing data. Returns (filtered, dropped_count)."""
    filtered: list[dict] = []
    dropped = 0
    now = datetime.now(timezone.utc)

    for c in candidates:
        isin = c["isin"]
        fundamentals = fundamentals_by_isin.get(isin)
        prices = price_history_by_isin.get(isin, [])

        # Fundamentals must exist and be fresh
        if not is_fundamentals_fresh(fundamentals, fundamentals_max_age_days):
            log.info("  Drop %s (%s): fundamentals stale or missing", c["symbol"], isin)
            dropped += 1
            continue

        # Latest price must be recent
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


# ── Bulk price history loader ────────────────────────────────────────────────


def load_price_histories(
    isins: list[str],
    days: int = PRICE_HISTORY_DAYS,
) -> dict[str, list[dict]]:
    """Load N days of price history for many ISINs.
    Returns {isin: [price_doc, ...]} (newest-first per ISIN).
    """
    out: dict[str, list[dict]] = {}
    for isin in isins:
        history = get_price_history(isin, days=days)
        # get_price_history returns DESC (newest-first) — we keep that.
        out[isin] = history
    return out


# ── Run orchestration ────────────────────────────────────────────────────────


def _today_ist_str() -> str:
    """Current date in IST as YYYY-MM-DD."""
    # IST is UTC+5:30
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc + timedelta(hours=5, minutes=30)
    return now_ist.strftime("%Y-%m-%d")


def run_suggestions(
    config: dict | None = None,
    run_type: str = "manual",
    limit: int | None = None,
    dry_run: bool = False,
    top_k_override: int | None = None,
) -> SuggestionRun:
    """Execute one full suggestions run end-to-end.

    Args:
        config: scoring config; defaults to scoring_service.DEFAULT_CONFIG.
        run_type: "scheduled" (cron), "manual", or "dry_run".
        limit: if set, take only the first N stocks from the universe (testing).
        dry_run: if True, do not persist the SuggestionRun (useful for local testing).
        top_k_override: override config["top_k"].

    Returns the SuggestionRun (also persisted to Mongo unless dry_run).
    """
    cfg = config or DEFAULT_CONFIG
    if top_k_override is not None:
        cfg = {**cfg, "top_k": top_k_override}

    started_at = utcnow()
    log.info(
        "=== Suggestions run starting (run_type=%s, dry_run=%s) ===", run_type, dry_run
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
        # 1. Universe
        universe = build_universe()
        run.universe_size = len(universe)
        log.info("Universe: %d NIFTY 100 stocks", len(universe))

        if limit:
            universe = universe[:limit]
            log.info("  --limit applied: %d stocks", len(universe))

        # 2. Filter held + rejected
        held = get_held_isins()
        rejected = get_rejected_isins()
        filtered, exclusions = filter_universe(universe, held, rejected)
        run.excluded_held = exclusions["held"]
        run.excluded_rejected = exclusions["rejected"]
        log.info(
            "Excluded: %d held, %d rejected → %d candidates pre-data-check",
            exclusions["held"],
            exclusions["rejected"],
            len(filtered),
        )

        # 3. Bulk-load fundamentals + prices
        isins = [c["isin"] for c in filtered]
        log.info("Loading fundamentals for %d candidates", len(isins))
        fundamentals_map = get_fundamentals_bulk(isins)
        log.info("  Fundamentals loaded: %d/%d", len(fundamentals_map), len(isins))

        log.info("Loading price history for %d candidates", len(isins))
        price_map = load_price_histories(isins, days=PRICE_HISTORY_DAYS)
        log.info(
            "  Price histories loaded: %d/%d",
            sum(1 for v in price_map.values() if v),
            len(isins),
        )

        # 4. Drop stale-data candidates
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
            run.error = "Zero candidates after filtering — check data freshness"
            run.finished_at = utcnow()
            log.error(run.error)
            if not dry_run:
                _persist_run(run)
            return run

        # 5. Score
        log.info("Scoring %d candidates", len(filtered))
        scored = score_candidates(filtered, fundamentals_map, price_map, cfg)
        eligible_count = sum(1 for s in scored if s.gates_failed == 0)
        run.candidates_post_gates = eligible_count
        log.info("  Eligible after gates: %d", eligible_count)

        # 6. Pick top K, store full list too
        top_k = cfg["top_k"]
        run.all_candidates = scored
        # top_candidates: only those that passed gates
        run.top_candidates = [s for s in scored if s.gates_failed == 0][:top_k]

        run.status = "success" if eligible_count > 0 else "partial"
        run.finished_at = utcnow()

        if not dry_run:
            _persist_run(run)

        # Log the top 5 for cron output visibility
        log.info("=== Top candidates ===")
        for c in run.top_candidates[:5]:
            log.info(
                "  #%d %s (%s) — composite=%.1f conf=%.0f Q=%.0f V=%.0f M=%.0f",
                c.rank,
                c.symbol,
                c.isin,
                c.composite_score,
                c.confidence_score,
                c.quality_score,
                c.valuation_score,
                c.momentum_score,
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


def _persist_run(run: SuggestionRun) -> None:
    """Insert the SuggestionRun into Mongo."""
    doc = run.to_mongo()
    Collections.suggestion_runs().insert_one(doc)
    log.info("Persisted SuggestionRun id=%s status=%s", doc.get("_id"), run.status)


def get_latest_run() -> dict | None:
    """Read the most recent successful SuggestionRun. None if no runs yet."""
    return Collections.suggestion_runs().find_one(
        {"status": {"$in": ["success", "partial"]}},
        sort=[("run_date", -1)],
    )
