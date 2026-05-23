"""Suggestion engine — orchestrates one full weekly run (Unit 3).

F2 (chunk 5): adds a sell-side pipeline behind the same run_suggestions
entry point, switched by direction. Buy-side is unchanged except that
it now activates the F14 earnings-proximity gate by passing
next_earnings_by_isin to score_candidates.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from bson import Decimal128

from app.db.client import Collections
from app.models._common import utcnow
from app.models.suggestion import SuggestionDirection, SuggestionRun
from app.services.digest_delivery import send_weekly_digest
from app.services.dossier_service import generate_dossiers_for_top_k
from app.services.fundamentals_service import (
    DEFAULT_FRESHNESS_DAYS,
    get_latest_bulk as get_fundamentals_bulk,
    get_next_earnings_bulk,
    is_fresh as is_fundamentals_fresh,
)
from app.services.news_signals import compute_news_signals_bulk
from app.services.outcome_tracker import create_outcomes_for_run
from app.services.price_service import (
    bulk_get_latest_prices,
    get_price_history,
)
from app.services.scoring_service import (
    DEFAULT_CONFIG,
    DEFAULT_SELL_CONFIG,
    score_candidates,
    score_sell_candidates,
)

log = logging.getLogger(__name__)

PRICE_HISTORY_DAYS = 252


# ─────────────────────────────────────────────────────────────────────
# Universe builders
# ─────────────────────────────────────────────────────────────────────


def build_universe() -> list[dict]:
    """Buy-side universe: NIFTY 100 instruments."""
    cursor = Collections.instruments().find(
        {"in_nifty100": True},
        {"_id": 0, "isin": 1, "symbol": 1, "exchange": 1, "name": 1},
    )
    return list(cursor)


def get_held_isins() -> set[str]:
    """All ISINs currently held (active holdings only)."""
    cursor = Collections.holdings().find(
        {"deleted_at": None},
        {"_id": 0, "isin": 1},
    )
    return {d["isin"] for d in cursor}


def get_active_holdings_full() -> list[dict]:
    """Sell-side universe: full active holding docs.

    Used to build the candidate list AND to compute portfolio_value
    and feed extract_sell_signals. Returns full docs (not just isin).
    """
    cursor = Collections.holdings().find(
        {"deleted_at": None},
        {
            "_id": 0,
            "isin": 1,
            "symbol": 1,
            "exchange": 1,
            "name": 1,
            "quantity": 1,
            "avg_cost": 1,
            "invested_amount": 1,
            "first_purchased_at": 1,
            "target_price": 1,
            "stop_loss": 1,
        },
    )
    return list(cursor)


# F5b: acted-but-not-held soft-exclude window. Closes the loop where the
# user clicks "Acted" but the position doesn't end up in holdings (sold
# quickly, broker reconcile lag, didn't actually place the trade). After
# 30 days the held filter takes over if the trade landed; otherwise the
# candidate resurfaces — which is the right behavior either way.
ACTED_EXCLUDE_WINDOW_DAYS = 30
REJECTED_EXCLUDE_WINDOW_DAYS = 90


def _to_aware_utc(dt):
    """Normalize a Mongo-fetched datetime to tz-aware UTC for comparison."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_excluded_isins(
    now: datetime | None = None,
    rejection_window_days: int = REJECTED_EXCLUDE_WINDOW_DAYS,
    acted_window_days: int = ACTED_EXCLUDE_WINDOW_DAYS,
) -> dict[str, set[str]]:
    """Return ISINs to exclude from build_universe, split by bucket.

    Renamed and broadened from get_rejected_isins (Chat 3 / F6 / F5b).
    Buckets:
      - "rejected": status=="rejected" AND rejected_at >= now - 90d
      - "acted":    status=="tracking" AND acted_at    >= now - 30d  (F5b)

    "passed" is NOT included. Per PROJECT_STATE 13 F6 / 20.7, a "passed"
    action is a per-run UI hint (the API enrichment path stamps user_action
    so the card collapses on the current view); the next scheduled run gets
    a fresh look because market conditions change. See enrich_run for the
    user_action gating logic.

    Note (F2 chunk 5): monitored_stocks is currently direction-agnostic.
    A user rejecting a SELL suggestion for INFY will also suppress the next
    BUY suggestion for INFY for 90 days. Acceptable for v1 since both
    interpretations are reasonable ("I'm done thinking about INFY") and the
    next chunk(s) of work may add a direction column to monitored_stocks.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    rejected_cutoff = now - timedelta(days=rejection_window_days)
    acted_cutoff = now - timedelta(days=acted_window_days)

    # Single scan; route into per-bucket sets in Python. Universe of
    # ever-feedback'd ISINs is tiny (single-user, low frequency).
    cursor = Collections.monitored_stocks().find(
        {"status": {"$in": ["rejected", "tracking"]}},
        {"_id": 0, "isin": 1, "status": 1, "rejected_at": 1, "acted_at": 1},
    )

    rejected: set[str] = set()
    acted: set[str] = set()
    for doc in cursor:
        isin = doc.get("isin")
        if not isin:
            continue
        status_val = doc.get("status")
        if status_val == "rejected":
            rejected_at = _to_aware_utc(doc.get("rejected_at"))
            if rejected_at and rejected_at >= rejected_cutoff:
                rejected.add(isin)
        elif status_val == "tracking":
            acted_at = _to_aware_utc(doc.get("acted_at"))
            if acted_at and acted_at >= acted_cutoff:
                acted.add(isin)

    return {"rejected": rejected, "acted": acted}


def filter_universe(
    universe: list[dict],
    held: set[str],
    excluded: dict[str, set[str]],
) -> tuple[list[dict], dict[str, int]]:
    """Filter universe by held + per-bucket excluded sets.

    Buy-side helper. Sell-side has a separate filter (sell universe is
    HELD by construction, so no held filter; only excluded buckets).

    Returns the filtered list and a counter dict with keys:
    held, rejected, acted.
    """
    filtered: list[dict] = []
    counts = {"held": 0, "rejected": 0, "acted": 0}
    rejected = excluded.get("rejected", set())
    acted = excluded.get("acted", set())
    for inst in universe:
        isin = inst["isin"]
        if isin in held:
            counts["held"] += 1
            continue
        if isin in rejected:
            counts["rejected"] += 1
            continue
        if isin in acted:
            counts["acted"] += 1
            continue
        filtered.append(inst)
    return filtered, counts


def filter_sell_universe(
    holdings: list[dict],
    excluded: dict[str, set[str]],
) -> tuple[list[dict], dict[str, int]]:
    """Filter sell-side universe (active holdings) by excluded buckets.

    Sell-side does NOT exclude by 'held' (held IS the universe).
    Still applies the F6 'rejected' and F5b 'acted' filters: if the user
    rejected a sell suggestion for INFY 5 days ago, don't surface it
    again next Sunday.
    """
    filtered: list[dict] = []
    counts = {"rejected": 0, "acted": 0}
    rejected = excluded.get("rejected", set())
    acted = excluded.get("acted", set())
    for h in holdings:
        isin = h["isin"]
        if isin in rejected:
            counts["rejected"] += 1
            continue
        if isin in acted:
            counts["acted"] += 1
            continue
        filtered.append(h)
    return filtered, counts


# ─────────────────────────────────────────────────────────────────────
# Data freshness + price history
# ─────────────────────────────────────────────────────────────────────


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


# ─────────────────────────────────────────────────────────────────────
# Sell-side helpers
# ─────────────────────────────────────────────────────────────────────


def _dec(v) -> Decimal | None:
    """Coerce Mongo / numeric → Decimal."""
    if v is None:
        return None
    if isinstance(v, Decimal128):
        return v.to_decimal()
    if isinstance(v, Decimal):
        return v
    try:
        return Decimal(str(v))
    except Exception:
        return None


def compute_portfolio_value(
    holdings: list[dict],
    latest_prices_by_isin: dict[str, dict],
) -> Decimal:
    """Total portfolio market value in INR.

    Sum of (quantity * latest_close) across all holdings that have a
    price available. Holdings without a price are skipped (their weight
    is implicitly underestimated; this is OK for the relative-weight
    scoring use case).
    """
    total = Decimal("0")
    for h in holdings:
        qty = _dec(h.get("quantity"))
        latest = latest_prices_by_isin.get(h["isin"])
        if qty is None or qty <= 0 or latest is None:
            continue
        px = _dec(latest.get("close"))
        if px is None or px <= 0:
            continue
        total += qty * px
    return total


# ─────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────


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
    direction: SuggestionDirection = "buy",
) -> SuggestionRun:
    """Execute one full suggestions run end-to-end.

    F2 (chunk 5): direction selects buy-side (default, back-compat) or
    sell-side pipeline.

    Args:
        config: scoring config override. Defaults to DEFAULT_CONFIG
            (buy) or DEFAULT_SELL_CONFIG (sell). Passing config
            overrides the default for either direction.
        notify: if True (production runs), send email + ntfy AND create
            outcome-tracking records. Default False so manual/testing
            runs do not spam delivery.
        direction: 'buy' (existing pipeline) or 'sell' (F2).
    """
    if direction == "sell":
        if config is None:
            config = DEFAULT_SELL_CONFIG
        return _run_sell_pipeline(
            config=config,
            run_type=run_type,
            limit=limit,
            dry_run=dry_run,
            top_k_override=top_k_override,
            skip_dossiers=skip_dossiers,
            notify=notify,
        )
    # Default and back-compat: buy
    if config is None:
        config = DEFAULT_CONFIG
    return _run_buy_pipeline(
        config=config,
        run_type=run_type,
        limit=limit,
        dry_run=dry_run,
        top_k_override=top_k_override,
        skip_dossiers=skip_dossiers,
        notify=notify,
    )


def _run_buy_pipeline(
    config: dict,
    run_type: str,
    limit: int | None,
    dry_run: bool,
    top_k_override: int | None,
    skip_dossiers: bool,
    notify: bool,
) -> SuggestionRun:
    cfg = config
    if top_k_override is not None:
        cfg = {**cfg, "top_k": top_k_override}

    started_at = utcnow()
    log.info(
        "=== Buy suggestions run starting (run_type=%s, dry_run=%s, "
        "skip_dossiers=%s, notify=%s) ===",
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
        direction="buy",
    )

    try:
        universe = build_universe()
        run.universe_size = len(universe)
        log.info("Universe: %d NIFTY 100 stocks", len(universe))

        if limit:
            universe = universe[:limit]
            log.info("  --limit applied: %d stocks", len(universe))

        held = get_held_isins()
        excluded = get_excluded_isins(now=started_at)
        filtered, exclusions = filter_universe(universe, held, excluded)
        run.excluded_held = exclusions["held"]
        run.excluded_rejected = exclusions["rejected"]
        run.excluded_acted = exclusions["acted"]
        log.info(
            "Excluded: %d held, %d rejected (90d), %d acted (30d / F5b) "
            "-> %d candidates pre-data-check",
            exclusions["held"],
            exclusions["rejected"],
            exclusions["acted"],
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

        # F14: load earnings calendar for the universe so the
        # earnings-proximity gate stops being skipped on buy-side.
        log.info("Loading earnings calendar for %d candidates", len(isins))
        next_earnings_map = get_next_earnings_bulk(isins)
        log.info(
            "  Upcoming earnings events: %d/%d", len(next_earnings_map), len(isins)
        )

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
        scored = score_candidates(
            filtered,
            fundamentals_map,
            price_map,
            news_map,
            cfg,
            next_earnings_by_isin=next_earnings_map,  # F14: activate gate
        )
        eligible_count = sum(1 for s in scored if s.gates_failed == 0)
        run.candidates_post_gates = eligible_count
        log.info("  Eligible after gates: %d", eligible_count)

        top_k = cfg["top_k"]
        run.all_candidates = scored
        run.top_candidates = [s for s in scored if s.gates_failed == 0][:top_k]

        if not skip_dossiers and run.top_candidates:
            log.info(
                "Generating dossiers for top %d candidates",
                len(run.top_candidates),
            )
            dossiers = generate_dossiers_for_top_k(
                run.top_candidates,
                fundamentals_map,
                direction="buy",
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
                        inserted_id,
                        run.run_date,
                        run.top_candidates,
                        direction="buy",
                    )
                except Exception as exc:
                    log.error("create_outcomes_for_run failed: %s", exc)

                # 2. Send email + ntfy digest
                try:
                    delivery = send_weekly_digest(run)
                    log.info("Digest delivery result: %s", delivery)
                except Exception as exc:
                    log.error("send_weekly_digest failed: %s", exc)

        log.info("=== Top buy candidates ===")
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
        log.exception("Buy suggestions run failed")
        run.status = "failed"
        run.error = f"{type(exc).__name__}: {exc}"
        run.finished_at = utcnow()
        if not dry_run:
            _persist_run(run)
        raise


def _run_sell_pipeline(
    config: dict,
    run_type: str,
    limit: int | None,
    dry_run: bool,
    top_k_override: int | None,
    skip_dossiers: bool,
    notify: bool,
) -> SuggestionRun:
    """Sell-side pipeline. Universe = active holdings."""
    cfg = config
    if top_k_override is not None:
        cfg = {**cfg, "top_k": top_k_override}

    started_at = utcnow()
    log.info(
        "=== Sell suggestions run starting (run_type=%s, dry_run=%s, "
        "skip_dossiers=%s, notify=%s) ===",
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
        direction="sell",
    )

    try:
        holdings = get_active_holdings_full()
        run.universe_size = len(holdings)
        log.info("Universe: %d active holdings", len(holdings))

        if limit:
            holdings = holdings[:limit]
            log.info("  --limit applied: %d holdings", len(holdings))

        excluded = get_excluded_isins(now=started_at)
        filtered_holdings, exclusions = filter_sell_universe(holdings, excluded)
        # Reuse the same SuggestionRun fields for visibility — held is N/A
        # for sell-side so excluded_held stays 0.
        run.excluded_held = 0
        run.excluded_rejected = exclusions["rejected"]
        run.excluded_acted = exclusions["acted"]
        log.info(
            "Excluded: %d rejected (90d), %d acted (30d / F5b) -> %d candidates "
            "pre-data-check",
            exclusions["rejected"],
            exclusions["acted"],
            len(filtered_holdings),
        )

        isins = [h["isin"] for h in filtered_holdings]
        log.info("Loading fundamentals for %d holdings", len(isins))
        fundamentals_map = get_fundamentals_bulk(isins)
        log.info("  Fundamentals loaded: %d/%d", len(fundamentals_map), len(isins))

        log.info("Loading price history for %d holdings", len(isins))
        price_map = load_price_histories(isins, days=PRICE_HISTORY_DAYS)
        loaded_prices = sum(1 for v in price_map.values() if v)
        log.info("  Price histories loaded: %d/%d", loaded_prices, len(isins))

        log.info("Computing news signals for %d holdings", len(isins))
        news_map = compute_news_signals_bulk(isins, window_days=30)
        candidates_with_news = sum(1 for s in news_map.values() if s.get("has_news"))
        log.info("  Holdings with news: %d/%d", candidates_with_news, len(isins))

        log.info("Loading earnings calendar for %d holdings", len(isins))
        next_earnings_map = get_next_earnings_bulk(isins)
        log.info(
            "  Upcoming earnings events: %d/%d", len(next_earnings_map), len(isins)
        )

        # Compute portfolio value once. Uses bulk_get_latest_prices which
        # prefers today's intraday quote then falls back to EOD.
        latest_prices = bulk_get_latest_prices(isins)
        portfolio_value = compute_portfolio_value(filtered_holdings, latest_prices)
        log.info(
            "  Portfolio value: INR %s (basis for portfolio_weight_pct)",
            portfolio_value,
        )

        # Reuse buy-side freshness filter — same fundamentals/price age rules.
        # filtered_holdings IS already a list of dicts with isin+symbol, so the
        # signature lines up.
        filtered_holdings, stale_dropped = filter_by_data_freshness(
            filtered_holdings,
            fundamentals_map,
            price_map,
            fundamentals_max_age_days=cfg["freshness"]["fundamentals_max_age_days"],
            price_max_age_days=cfg["freshness"]["prices_max_age_days"],
        )
        run.excluded_stale_data = stale_dropped
        run.candidates_considered = len(filtered_holdings)
        log.info("After freshness filter: %d holdings", len(filtered_holdings))

        if not filtered_holdings:
            run.status = "failed"
            run.error = "Zero sell candidates after filtering -- check holdings + data freshness"
            run.finished_at = utcnow()
            log.error(run.error)
            if not dry_run:
                _persist_run(run)
            return run

        # holdings_by_isin needed by score_sell_candidates for cost basis etc.
        holdings_by_isin = {h["isin"]: h for h in filtered_holdings}

        log.info("Scoring %d sell candidates", len(filtered_holdings))
        scored = score_sell_candidates(
            filtered_holdings,
            fundamentals_map,
            price_map,
            news_map,
            holdings_by_isin,
            next_earnings_map,
            portfolio_value,
            cfg,
        )
        eligible_count = sum(1 for s in scored if s.gates_failed == 0)
        run.candidates_post_gates = eligible_count
        log.info("  Eligible after sell-side gates: %d", eligible_count)

        top_k = cfg["top_k"]
        run.all_candidates = scored
        run.top_candidates = [s for s in scored if s.gates_failed == 0][:top_k]

        if not skip_dossiers and run.top_candidates:
            log.info(
                "Generating sell-side dossiers for top %d candidates",
                len(run.top_candidates),
            )
            dossiers = generate_dossiers_for_top_k(
                run.top_candidates,
                fundamentals_map,
                direction="sell",
                holdings_by_isin=holdings_by_isin,
                portfolio_value=portfolio_value,
                next_earnings_by_isin=next_earnings_map,
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
                try:
                    create_outcomes_for_run(
                        inserted_id,
                        run.run_date,
                        run.top_candidates,
                        direction="sell",
                    )
                except Exception as exc:
                    log.error("create_outcomes_for_run (sell) failed: %s", exc)

                # The production --direction=both cron path emits ONE combined
                # email + ntfy push via the shared digest delivery flow (see
                # scripts/run_weekly_suggestions.py and digest_delivery).
                # This send_weekly_digest call is the standalone --direction=sell
                # path used by manual reruns and ad-hoc testing only.
                try:
                    delivery = send_weekly_digest(run)
                    log.info("Digest delivery (sell) result: %s", delivery)
                except Exception as exc:
                    log.error("send_weekly_digest (sell) failed: %s", exc)

        log.info("=== Top sell candidates ===")
        for c in run.top_candidates[:5]:
            log.info(
                "  #%d %s (%s) -- composite=%.1f conf=%.0f",
                c.rank,
                c.symbol,
                c.isin,
                c.composite_score,
                c.confidence_score,
            )

        return run

    except Exception as exc:
        log.exception("Sell suggestions run failed")
        run.status = "failed"
        run.error = f"{type(exc).__name__}: {exc}"
        run.finished_at = utcnow()
        if not dry_run:
            _persist_run(run)
        raise


# ─────────────────────────────────────────────────────────────────────
# Persistence
# ─────────────────────────────────────────────────────────────────────


def _serialize_dossiers(dossiers: list[dict]) -> str:
    return json.dumps({"dossiers": dossiers}, default=str)


def _persist_run(run: SuggestionRun):
    """Insert the SuggestionRun. Returns the inserted _id (ObjectId)."""
    doc = run.to_mongo()
    result = Collections.suggestion_runs().insert_one(doc)
    log.info(
        "Persisted SuggestionRun id=%s status=%s direction=%s",
        result.inserted_id,
        run.status,
        run.direction,
    )
    return result.inserted_id


def get_latest_run(direction: SuggestionDirection | None = None) -> dict | None:
    """Most recent successful/partial run. Optionally filtered by direction."""
    query: dict = {"status": {"$in": ["success", "partial"]}}
    if direction is not None:
        query["direction"] = direction
    return Collections.suggestion_runs().find_one(
        query,
        sort=[("run_date", -1)],
    )
