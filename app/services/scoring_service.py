"""Scoring engine for Phase 2 suggestions — Unit 2 (with News)."""

from __future__ import annotations

import logging
import math
import statistics
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from bson import Decimal128

from app.models._common import utcnow
from app.models.suggestion import CandidateScore, GateResult, SignalScore

log = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "weights": {
        "quality": 0.30,
        "valuation": 0.25,
        "momentum": 0.25,
        "news": 0.20,
    },
    "gates": {
        "max_debt_to_equity": 1.5,
        "min_return_on_equity": 0.10,
        "min_market_cap_inr": 10_000 * 1_00_00_000,
        "max_high_severity_negative_news_30d": 1,
        # F14: shared between buy and sell via evaluate_earnings_proximity_gate.
        # Both pipelines thread next_earnings_by_isin -- see
        # suggestion_engine._run_buy_pipeline and _run_sell_pipeline.
        # When earnings_calendar has no entry, the gate reports skipped
        # (which counts as passed) so missing data does not exclude.
        "earnings_proximity_days": 5,
    },
    "freshness": {
        "fundamentals_max_age_days": 14,
        "prices_max_age_days": 5,
    },
    "scoring": {
        "lower_is_better": ["debt_to_equity", "pe_ratio", "pb_ratio"],
    },
    "top_k": 10,
    "version": "1.0.0-unit2",
}


def _dec(v: Any) -> Decimal | None:
    if v is None:
        return None
    if isinstance(v, Decimal128):
        return v.to_decimal()
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, float)):
        if isinstance(v, float) and v != v:
            return None
        return Decimal(str(v))
    return None


def _flt(v: Any) -> float | None:
    d = _dec(v)
    if d is None:
        return None
    try:
        return float(d)
    except Exception:
        return None


def _normalize_to_100(
    values: list[float | None], lower_is_better: bool = False
) -> list[float | None]:
    """Convert raw signal values to 0-100 normalized scores within the universe."""
    valid = [v for v in values if v is not None]
    if len(valid) < 2:
        return [50.0 if v is not None else None for v in values]

    mean = statistics.mean(valid)
    try:
        stdev = statistics.stdev(valid)
    except statistics.StatisticsError:
        stdev = 0.0

    if stdev == 0:
        return [50.0 if v is not None else None for v in values]

    out: list[float | None] = []
    for v in values:
        if v is None:
            out.append(None)
            continue
        z = (v - mean) / stdev
        z = max(-5.0, min(5.0, z))
        sigmoid = 1.0 / (1.0 + math.exp(-z))
        score = sigmoid * 100.0
        if lower_is_better:
            score = 100.0 - score
        out.append(round(score, 2))
    return out


def evaluate_earnings_proximity_gate(
    next_earnings: datetime | None,
    max_days_within: int,
) -> GateResult:
    """F14: shared gate for buy and sell. Skip trades within N days of earnings.

    The semantics are identical in both directions:
      * Buying right before earnings is noisy (the price reaction often
        dominates the fundamental thesis).
      * Selling right before earnings is also noisy (locking in a loss
        right before a beat, or missing upside on a guide raise).

    When next_earnings is None the gate reports `skipped=True, passed=True`
    so the candidate is not excluded -- absence of earnings data is not
    evidence of an imminent event.
    """
    if next_earnings is None:
        return GateResult(
            gate_name="earnings_proximity",
            passed=True,
            skipped=True,
            threshold=f"next earnings > {max_days_within} days away",
            skip_reason="No upcoming earnings event in earnings_calendar",
        )

    naive_next = (
        next_earnings.replace(tzinfo=None)
        if next_earnings.tzinfo is not None
        else next_earnings
    )
    now_naive = utcnow().replace(tzinfo=None)
    days_until = (naive_next - now_naive).total_seconds() / 86400.0
    passed = days_until > max_days_within

    return GateResult(
        gate_name="earnings_proximity",
        passed=passed,
        threshold=f"next earnings > {max_days_within} days away",
        actual_value=(
            f"earnings on {naive_next.date().isoformat()} ({days_until:+.1f}d from now)"
        ),
    )


def evaluate_gates(
    fundamentals: dict | None,
    news_signals: dict | None,
    config: dict,
    next_earnings: datetime | None = None,
) -> list[GateResult]:
    """Run quality gates against a candidate. Unit 2 adds the news gate.

    F14: `next_earnings` is optional for back-compat. Existing buy-side
    callers that don't pass it get an always-`skipped` earnings_proximity
    gate (which counts as passed for eligibility).
    """
    gates: list[GateResult] = []
    gate_config = config["gates"]

    if fundamentals is None:
        for gate_name in ["debt_to_equity", "return_on_equity", "market_cap"]:
            gates.append(
                GateResult(
                    gate_name=gate_name,
                    passed=False,
                    skipped=True,
                    skip_reason="Fundamentals doc missing for this ISIN",
                )
            )
    else:
        de = _flt(fundamentals.get("debt_to_equity"))
        if de is None:
            gates.append(
                GateResult(
                    gate_name="debt_to_equity",
                    passed=False,
                    skipped=True,
                    threshold=f"D/E <= {gate_config['max_debt_to_equity']}",
                    skip_reason="debt_to_equity not available from yfinance",
                )
            )
        else:
            passed = de <= gate_config["max_debt_to_equity"]
            gates.append(
                GateResult(
                    gate_name="debt_to_equity",
                    passed=passed,
                    threshold=f"D/E <= {gate_config['max_debt_to_equity']}",
                    actual_value=f"D/E = {de:.2f}",
                )
            )

        roe = _flt(fundamentals.get("return_on_equity"))
        if roe is None:
            gates.append(
                GateResult(
                    gate_name="return_on_equity",
                    passed=False,
                    skipped=True,
                    threshold=f"ROE >= {gate_config['min_return_on_equity'] * 100:.0f}%",
                    skip_reason="return_on_equity not available from yfinance",
                )
            )
        else:
            passed = roe >= gate_config["min_return_on_equity"]
            gates.append(
                GateResult(
                    gate_name="return_on_equity",
                    passed=passed,
                    threshold=f"ROE >= {gate_config['min_return_on_equity'] * 100:.0f}%",
                    actual_value=f"ROE = {roe * 100:.2f}%",
                )
            )

        mc = _flt(fundamentals.get("market_cap"))
        floor = gate_config["min_market_cap_inr"]
        floor_cr = floor / 1_00_00_000
        if mc is None:
            gates.append(
                GateResult(
                    gate_name="market_cap",
                    passed=False,
                    skipped=True,
                    threshold=f"Mkt Cap >= INR {floor_cr:,.0f} Cr",
                    skip_reason="market_cap not available from yfinance",
                )
            )
        else:
            passed = mc >= floor
            gates.append(
                GateResult(
                    gate_name="market_cap",
                    passed=passed,
                    threshold=f"Mkt Cap >= INR {floor_cr:,.0f} Cr",
                    actual_value=f"Mkt Cap = INR {mc / 1_00_00_000:,.0f} Cr",
                )
            )

    if news_signals is None or not news_signals.get("has_news"):
        gates.append(
            GateResult(
                gate_name="high_severity_negative_news",
                passed=True,
                skipped=True,
                skip_reason="No classified news in 30d window",
            )
        )
    else:
        bad_count = news_signals.get("high_severity_negative_count", 0)
        max_allowed = gate_config["max_high_severity_negative_news_30d"]
        passed = bad_count <= max_allowed
        gates.append(
            GateResult(
                gate_name="high_severity_negative_news",
                passed=passed,
                threshold=f"high-severity negative stories (30d) <= {max_allowed}",
                actual_value=f"count = {bad_count}",
            )
        )

    # F14: earnings proximity (shared with sell-side via the same helper).
    gates.append(
        evaluate_earnings_proximity_gate(
            next_earnings,
            gate_config.get("earnings_proximity_days", 5),
        )
    )

    return gates


def gates_summary(gates: list[GateResult]) -> tuple[int, int, int, bool]:
    passed = sum(1 for g in gates if g.passed and not g.skipped)
    failed = sum(1 for g in gates if not g.passed and not g.skipped)
    skipped = sum(1 for g in gates if g.skipped)
    eligible = failed == 0
    return passed, failed, skipped, eligible


def extract_signals(
    fundamentals: dict | None,
    price_history: list[dict],
    news_signals: dict | None,
) -> dict[str, float | None]:
    """Pull all raw signal values from fundamentals + price history + news."""
    signals: dict[str, float | None] = {}

    if fundamentals:
        signals["return_on_equity"] = _flt(fundamentals.get("return_on_equity"))
        signals["return_on_assets"] = _flt(fundamentals.get("return_on_assets"))
        signals["operating_margin"] = _flt(fundamentals.get("operating_margin"))
        signals["debt_to_equity"] = _flt(fundamentals.get("debt_to_equity"))
        signals["pe_ratio"] = _flt(fundamentals.get("pe_ratio"))
        signals["pb_ratio"] = _flt(fundamentals.get("pb_ratio"))
        signals["earnings_growth_yoy"] = _flt(fundamentals.get("earnings_growth_yoy"))
        signals["revenue_growth_yoy"] = _flt(fundamentals.get("revenue_growth_yoy"))
    else:
        for k in [
            "return_on_equity",
            "return_on_assets",
            "operating_margin",
            "debt_to_equity",
            "pe_ratio",
            "pb_ratio",
            "earnings_growth_yoy",
            "revenue_growth_yoy",
        ]:
            signals[k] = None

    if price_history and len(price_history) >= 2:
        latest_close = _flt(price_history[0].get("close"))
        signals["_latest_close"] = latest_close

        if len(price_history) > 63 and latest_close is not None:
            old = _flt(price_history[63].get("close"))
            signals["return_3m"] = (
                (latest_close / old - 1) * 100 if old and old > 0 else None
            )
        else:
            signals["return_3m"] = None

        if len(price_history) > 126 and latest_close is not None:
            old = _flt(price_history[126].get("close"))
            signals["return_6m"] = (
                (latest_close / old - 1) * 100 if old and old > 0 else None
            )
        else:
            signals["return_6m"] = None

        window = price_history[: min(252, len(price_history))]
        closes = [_flt(p.get("close")) for p in window]
        closes = [c for c in closes if c is not None]
        if closes and latest_close is not None:
            high_52w = max(closes)
            low_52w = min(closes)
            signals["dist_from_52w_high_pct"] = (
                (latest_close / high_52w - 1) * 100 if high_52w > 0 else None
            )
            signals["dist_from_52w_low_pct"] = (
                (latest_close / low_52w - 1) * 100 if low_52w > 0 else None
            )
        else:
            signals["dist_from_52w_high_pct"] = None
            signals["dist_from_52w_low_pct"] = None
    else:
        signals["_latest_close"] = None
        signals["return_3m"] = None
        signals["return_6m"] = None
        signals["dist_from_52w_high_pct"] = None
        signals["dist_from_52w_low_pct"] = None

    if news_signals and news_signals.get("has_news"):
        # #80 M3: use .get() not bracket access — a legacy/partial news dict
        # where has_news is truthy but net_sentiment is absent would raise
        # KeyError; float(None) raises TypeError. Either aborts the whole run.
        ns = news_signals.get("net_sentiment")
        signals["news_net_sentiment"] = float(ns) * 100 if ns is not None else None
        signals["news_story_velocity"] = float(news_signals.get("story_velocity", 1.0))
        signals["news_story_count"] = min(
            float(news_signals.get("story_count", 0)), 30.0
        )
    else:
        signals["news_net_sentiment"] = None
        signals["news_story_velocity"] = None
        signals["news_story_count"] = None

    return signals


GROUP_SIGNALS = {
    "quality": {
        "return_on_equity": 0.35,
        "return_on_assets": 0.20,
        "operating_margin": 0.20,
        "debt_to_equity": 0.25,
    },
    "valuation": {
        "pe_ratio": 0.50,
        "pb_ratio": 0.30,
        "earnings_growth_yoy": 0.20,
    },
    "momentum": {
        "return_3m": 0.30,
        "return_6m": 0.40,
        "dist_from_52w_high_pct": 0.30,
    },
    "news": {
        "news_net_sentiment": 0.55,
        "news_story_velocity": 0.25,
        "news_story_count": 0.20,
    },
}


def score_group(
    group_name: str,
    candidate_signals: dict[str, dict[str, float | None]],
    lower_is_better_set: set[str],
    group_signals_def: dict[str, dict[str, float]] | None = None,
) -> dict[str, dict[str, float | None]]:
    """Per-universe z-score → sigmoid → 0..100 normalization for one group.

    `group_signals_def` defaults to the module-level `GROUP_SIGNALS` (buy-side).
    Sell-side passes `GROUP_SIGNALS_SELL`. Buy-side behaviour byte-identical
    when called without this argument.
    """
    out: dict[str, dict[str, float | None]] = {isin: {} for isin in candidate_signals}
    group_def_map = (
        group_signals_def if group_signals_def is not None else GROUP_SIGNALS
    )
    group_def = group_def_map.get(group_name, {})
    for signal_name in group_def:
        isins_ordered = list(candidate_signals.keys())
        values = [candidate_signals[isin].get(signal_name) for isin in isins_ordered]
        normalized = _normalize_to_100(
            values,
            lower_is_better=signal_name in lower_is_better_set,
        )
        for isin, norm in zip(isins_ordered, normalized):
            out[isin][signal_name] = norm
    return out


def composite_for_candidate(
    isin: str,
    normalized_by_group: dict[str, dict[str, dict[str, float | None]]],
    candidate_has_news: bool,
    config: dict,
    group_signals_def: dict[str, dict[str, float]] | None = None,
    missing_group_default: float = 0.0,
    candidate_signals_for_isin: dict[str, float | None] | None = None,
) -> tuple[float, dict[str, float], list[SignalScore]]:
    """Compute composite score for one candidate.

    `group_signals_def` defaults to module-level GROUP_SIGNALS (buy-side).

    `missing_group_default` is the score assigned to a group when ALL its
    signals are unavailable for this candidate. Buy-side keeps the historic
    behaviour: 0.0 (hard penalty), except the news group which falls back
    to 50.0 when the candidate has no classified news in the window.
    Sell-side passes 50.0 so missing tax/concentration data doesn't tank
    the composite.

    A3+A4 (Chat 5): when `candidate_signals_for_isin` is provided (the dict
    returned by extract_signals / extract_sell_signals for this ISIN),
    SignalScore.raw_value is populated with the actual raw input that fed
    normalization (fundamental ratio, momentum %, news scaled-sentiment /
    velocity / count). When None (back-compat), falls back to the historic
    behaviour of stringifying the normalized score -- preserves the prior
    wire shape for any caller missed by the audit.
    """
    group_scores: dict[str, float] = {}
    signal_scores: list[SignalScore] = []
    weights = config["weights"]
    group_def_map = (
        group_signals_def if group_signals_def is not None else GROUP_SIGNALS
    )
    raw_signals = candidate_signals_for_isin or {}
    for group_name, signal_weights in group_def_map.items():
        per_signal = normalized_by_group.get(group_name, {}).get(isin, {})
        total_weight = 0.0
        weighted_sum = 0.0
        for signal_name, weight_in_group in signal_weights.items():
            score = per_signal.get(signal_name)
            raw_input = raw_signals.get(signal_name)
            if score is None:
                # Signal unavailable for normalization. Still surface a raw
                # input if extract_signals captured one; otherwise empty.
                signal_scores.append(
                    SignalScore(
                        signal_name=signal_name,
                        raw_value=(f"{raw_input:.4f}" if raw_input is not None else ""),
                        normalized_score=0.0,
                        weight=weight_in_group * weights.get(group_name, 0.0),
                        available=False,
                    )
                )
                continue
            weighted_sum += score * weight_in_group
            total_weight += weight_in_group
            # A3+A4: write the RAW input (fundamental / momentum % / news
            # scaled-sentiment / velocity / count) instead of the normalized
            # 0-100 score (which already lives in normalized_score).
            # Back-compat fallback: if no raw_signals dict was passed,
            # preserve the historic (incorrect) string of the normalized
            # score so any unaudited caller does not crash.
            if candidate_signals_for_isin is not None:
                raw_value_str = f"{raw_input:.4f}" if raw_input is not None else ""
            else:
                raw_value_str = f"{score:.2f}"
            signal_scores.append(
                SignalScore(
                    signal_name=signal_name,
                    raw_value=raw_value_str,
                    normalized_score=score,
                    weight=weight_in_group * weights.get(group_name, 0.0),
                    available=True,
                )
            )
        if total_weight > 0:
            group_scores[group_name] = weighted_sum / total_weight
        elif group_name == "news" and not candidate_has_news:
            # Buy-side back-compat: candidate with no news in 30d → neutral news.
            group_scores[group_name] = 50.0
        else:
            group_scores[group_name] = missing_group_default
    composite = sum(
        group_scores.get(g, 0.0) * weights.get(g, 0.0) for g in group_def_map.keys()
    )
    return (
        round(composite, 2),
        {k: round(v, 2) for k, v in group_scores.items()},
        signal_scores,
    )


def compute_confidence(
    fundamentals: dict | None,
    fundamentals_age_days: float | None,
    price_age_days: float | None,
    group_scores: dict[str, float],
    gates: list[GateResult],
    has_news: bool,
    news_freshness_days: float | None,
) -> tuple[float, list[str]]:
    """Compute confidence_score (0-100) deterministically."""
    score = 100.0
    reasons: list[str] = []

    if fundamentals is None:
        score -= 30
        reasons.append("Fundamentals snapshot missing (-30)")
    elif fundamentals_age_days is not None and fundamentals_age_days > 14:
        score -= 15
        reasons.append(f"Fundamentals stale ({fundamentals_age_days:.0f}d old, -15)")

    if price_age_days is None or price_age_days > 7:
        score -= 15
        age_str = f"{price_age_days:.0f}d" if price_age_days is not None else "unknown"
        reasons.append(f"Price data stale ({age_str}, -15)")

    if not has_news:
        score -= 10
        reasons.append("No classified news in 30d window (-10)")
    elif news_freshness_days is not None and news_freshness_days > 14:
        score -= 5
        reasons.append(f"Latest news older than 14d ({news_freshness_days:.0f}d, -5)")

    median_signal_score = 50.0
    for group_name, group_score in group_scores.items():
        if group_name == "news" and not has_news:
            continue
        if group_score < median_signal_score - 10:
            score -= 10
            reasons.append(f"{group_name.title()} group below median (-10)")

    score = max(0.0, min(100.0, score))
    return round(score, 2), reasons


def score_candidates(
    candidates: list[dict],
    fundamentals_by_isin: dict[str, dict],
    price_history_by_isin: dict[str, list[dict]],
    news_signals_by_isin: dict[str, dict],
    config: dict | None = None,
    next_earnings_by_isin: dict[str, datetime] | None = None,
) -> list[CandidateScore]:
    """Score all candidates and return ranked CandidateScore objects.

    F14: `next_earnings_by_isin` is optional for back-compat. When omitted,
    the earnings-proximity gate reports skipped (which counts as passed).
    Buy-side engine wires this in chunk 5.
    """
    cfg = config or DEFAULT_CONFIG
    lower_is_better_set = set(cfg["scoring"]["lower_is_better"])
    next_earnings_map = next_earnings_by_isin or {}

    candidate_signals: dict[str, dict[str, float | None]] = {}
    for c in candidates:
        isin = c["isin"]
        candidate_signals[isin] = extract_signals(
            fundamentals_by_isin.get(isin),
            price_history_by_isin.get(isin, []),
            news_signals_by_isin.get(isin),
        )

    candidate_gates: dict[str, list[GateResult]] = {}
    eligible_isins: list[str] = []
    for c in candidates:
        isin = c["isin"]
        gates = evaluate_gates(
            fundamentals_by_isin.get(isin),
            news_signals_by_isin.get(isin),
            cfg,
            next_earnings_map.get(isin),
        )
        candidate_gates[isin] = gates
        _, _, _, eligible = gates_summary(gates)
        if eligible:
            eligible_isins.append(isin)

    eligible_signals = {isin: candidate_signals[isin] for isin in eligible_isins}
    normalized_by_group: dict[str, dict[str, dict[str, float | None]]] = {}
    for group_name in GROUP_SIGNALS:
        normalized_by_group[group_name] = score_group(
            group_name,
            eligible_signals,
            lower_is_better_set,
        )

    now = datetime.now(
        timezone.utc
    )  # tz-ok: aware base for fundamentals/price age diffs (both coerced aware below)
    results: list[CandidateScore] = []

    for c in candidates:
        isin = c["isin"]
        gates = candidate_gates[isin]
        passed, failed, skipped, eligible = gates_summary(gates)

        fundamentals = fundamentals_by_isin.get(isin)
        prices = price_history_by_isin.get(isin, [])
        news_signals = news_signals_by_isin.get(isin)
        has_news = bool(news_signals and news_signals.get("has_news"))

        if eligible:
            composite, group_scores, signal_scores = composite_for_candidate(
                isin,
                normalized_by_group,
                has_news,
                cfg,
                candidate_signals_for_isin=candidate_signals.get(isin),
            )
        else:
            composite, group_scores, signal_scores = (
                0.0,
                {
                    "quality": 0.0,
                    "valuation": 0.0,
                    "momentum": 0.0,
                    "news": 0.0,
                },
                [],
            )

        fundamentals_age_days: float | None = None
        if fundamentals and fundamentals.get("fetched_at"):
            ft = fundamentals["fetched_at"]
            if ft.tzinfo is None:
                ft = ft.replace(tzinfo=timezone.utc)
            fundamentals_age_days = (now - ft).total_seconds() / 86400.0

        price_age_days: float | None = None
        latest_price_ts: datetime | None = None
        latest_price_value = None
        if prices:
            pdate = prices[0].get("date")
            if pdate:
                if pdate.tzinfo is None:
                    pdate = pdate.replace(tzinfo=timezone.utc)
                price_age_days = (now - pdate).total_seconds() / 86400.0
                latest_price_ts = pdate
            latest_price_value = _dec(prices[0].get("close"))

        news_freshness = None
        if news_signals:
            news_freshness = news_signals.get("days_since_latest_news")

        confidence, deductions = compute_confidence(
            fundamentals=fundamentals,
            fundamentals_age_days=fundamentals_age_days,
            price_age_days=price_age_days,
            group_scores=group_scores,
            gates=gates,
            has_news=has_news,
            news_freshness_days=news_freshness,
        )

        results.append(
            CandidateScore(
                isin=isin,
                symbol=c["symbol"],
                name=c.get("name", ""),
                sector=c.get("sector", "")
                or (fundamentals.get("sector", "") if fundamentals else ""),
                composite_score=composite,
                rank=0,
                confidence_score=confidence,
                confidence_deductions=deductions,
                quality_score=group_scores["quality"],
                valuation_score=group_scores["valuation"],
                momentum_score=group_scores["momentum"],
                news_score=group_scores["news"],
                signals=signal_scores,
                gates=gates,
                gates_passed=passed,
                gates_failed=failed,
                gates_skipped=skipped,
                fundamentals_fetched_at=fundamentals.get("fetched_at")
                if fundamentals
                else None,
                price_as_of=latest_price_ts,
                current_price=latest_price_value,
            )
        )

    results.sort(
        key=lambda r: (r.gates_failed == 0, r.composite_score),
        reverse=True,
    )
    for i, r in enumerate(results):
        r.rank = i + 1
    return results


# ─────────────────────────────────────────────────────────────────────
# F2: Sell-side scoring
# ─────────────────────────────────────────────────────────────────────
#
# Mirrors the buy-side pipeline (extract → gate → normalize → score)
# but with:
#   * a different config (DEFAULT_SELL_CONFIG)
#   * a different group/signal map (GROUP_SIGNALS_SELL)
#   * different signal extraction (extract_sell_signals: pulls
#     holding-specific values like unrealized_gain_pct,
#     portfolio_weight_pct, target_price_proximity, is_ltcg_eligible)
#   * different gates (in_profit, min_position_age, earnings_proximity)
#
# Shared with buy-side: _normalize_to_100, gates_summary,
# compute_confidence, score_group, composite_for_candidate,
# evaluate_earnings_proximity_gate, _flt, _dec.

DEFAULT_SELL_CONFIG = {
    "weights": {
        "booking_opportunity": 0.30,
        "valuation_stretch": 0.25,
        "risk": 0.25,
        "tax_concentration": 0.20,
    },
    "gates": {
        # In profit: only suggest selling positions that are at least
        # break-even. Loss-cutting is a separate use case (chunk N+1).
        "min_unrealized_pnl_pct": 0.0,
        # Brand-new positions (< 30 days) shouldn't be sell candidates --
        # gives the thesis time to play out.
        "min_position_age_days": 30,
        # Shared with buy: skip if next earnings within 5 days.
        "earnings_proximity_days": 5,
    },
    "freshness": {
        "fundamentals_max_age_days": 14,
        "prices_max_age_days": 5,
    },
    "scoring": {
        # In SELL context, "lower is a stronger sell signal" for these:
        #   earnings_growth_yoy: lower = decelerating earnings = bigger sell signal
        #   news_net_sentiment: more negative = bigger sell signal
        # All other signals: higher = bigger sell signal (no inversion).
        "lower_is_better": ["earnings_growth_yoy", "news_net_sentiment"],
    },
    "top_k": 10,
    "version": "1.0.0-sell-unit1",
}


GROUP_SIGNALS_SELL = {
    "booking_opportunity": {
        # How attractive is it to take profits RIGHT NOW?
        "unrealized_gain_pct": 0.40,
        "return_3m": 0.25,
        "dist_from_52w_high_pct": 0.20,
        "target_price_proximity": 0.15,
    },
    "valuation_stretch": {
        # Is the stock expensive relative to its current earnings power?
        "pe_ratio": 0.50,
        "pb_ratio": 0.30,
        "earnings_growth_yoy": 0.20,  # lower_is_better in sell context
    },
    "risk": {
        # Are there warning signs that justify trimming exposure?
        "news_net_sentiment": 0.40,  # lower_is_better in sell context
        "high_severity_negative_count": 0.25,
        "debt_to_equity": 0.20,
        "news_story_velocity": 0.15,
    },
    "tax_concentration": {
        # Are there structural reasons to trim NOW vs later?
        "is_ltcg_eligible": 0.50,
        "portfolio_weight_pct": 0.50,
    },
}


def extract_sell_signals(
    fundamentals: dict | None,
    price_history: list[dict],
    news_signals: dict | None,
    holding: dict,
    portfolio_value: Decimal,
) -> dict[str, float | None]:
    """Pull all raw sell-side signal values from fundamentals + prices + news + holding.

    Re-uses extract_signals (buy-side) for the fundamentals/price/news
    signals that are direction-neutral. Adds holding-specific signals
    that only make sense for stocks we own.

    Args:
        fundamentals: latest fundamentals_snapshots doc for this ISIN, or None.
        price_history: list of price docs (newest first).
        news_signals: news_signals dict from compute_news_signals_for_isin.
        holding: holdings doc for this ISIN. Must be active (deleted_at=None)
            but we don't re-check that here; caller filters universe.
        portfolio_value: current TOTAL portfolio market value in INR
            (sum of qty * current_price across active holdings). Used for
            portfolio_weight_pct computation. Must be > 0; caller is
            responsible.

    Returns dict of {signal_name: value or None}.
    """
    signals: dict[str, float | None] = {}

    # Re-use buy-side extraction for direction-neutral signals.
    base = extract_signals(fundamentals, price_history, news_signals)

    # Fundamentals signals carried through. Direction inversion is handled
    # in DEFAULT_SELL_CONFIG['scoring']['lower_is_better'].
    signals["pe_ratio"] = base.get("pe_ratio")
    signals["pb_ratio"] = base.get("pb_ratio")
    signals["earnings_growth_yoy"] = base.get("earnings_growth_yoy")
    signals["debt_to_equity"] = base.get("debt_to_equity")

    # Momentum / price signals.
    signals["return_3m"] = base.get("return_3m")
    signals["dist_from_52w_high_pct"] = base.get("dist_from_52w_high_pct")

    # News signals.
    signals["news_net_sentiment"] = base.get("news_net_sentiment")
    signals["news_story_velocity"] = base.get("news_story_velocity")
    if news_signals and news_signals.get("has_news"):
        signals["high_severity_negative_count"] = float(
            news_signals.get("high_severity_negative_count", 0)
        )
    else:
        signals["high_severity_negative_count"] = None

    # Holding-specific signals.
    latest_close = base.get("_latest_close")
    invested = _flt(holding.get("invested_amount"))
    qty = _flt(holding.get("quantity"))

    # unrealized_gain_pct: (current_value - invested) / invested * 100
    if (
        latest_close is not None
        and qty is not None
        and qty > 0
        and invested is not None
        and invested > 0
    ):
        current_value = latest_close * qty
        signals["unrealized_gain_pct"] = ((current_value - invested) / invested) * 100
    else:
        signals["unrealized_gain_pct"] = None

    # portfolio_weight_pct: this holding's current_value / total_portfolio * 100
    pv_float = _flt(portfolio_value)
    if (
        latest_close is not None
        and qty is not None
        and qty > 0
        and pv_float is not None
        and pv_float > 0
    ):
        signals["portfolio_weight_pct"] = (latest_close * qty / pv_float) * 100
    else:
        signals["portfolio_weight_pct"] = None

    # target_price_proximity: current_price / target_price * 100; 100 = exact target hit
    target_price = _flt(holding.get("target_price"))
    if target_price is not None and target_price > 0 and latest_close is not None:
        signals["target_price_proximity"] = (latest_close / target_price) * 100
    else:
        signals["target_price_proximity"] = None

    # is_ltcg_eligible: binary 100 / 0 based on > 365 days holding period.
    first_purchased = holding.get("first_purchased_at")
    if first_purchased is not None:
        naive_fp = (
            first_purchased.replace(tzinfo=None)
            if hasattr(first_purchased, "tzinfo") and first_purchased.tzinfo is not None
            else first_purchased
        )
        now_naive = utcnow().replace(tzinfo=None)
        days_held = (now_naive - naive_fp).total_seconds() / 86400.0
        # India equity LTCG threshold: > 365 days.
        signals["is_ltcg_eligible"] = 100.0 if days_held > 365 else 0.0
    else:
        signals["is_ltcg_eligible"] = None

    # Internal field used by score_sell_candidates for confidence + price_as_of.
    signals["_latest_close"] = latest_close

    return signals


def evaluate_sell_gates(
    holding: dict,
    current_price: Decimal | None,
    next_earnings: datetime | None,
    config: dict,
) -> list[GateResult]:
    """Run hard-fail gates against a held stock for sell-side eligibility.

    Three gates:
      1. in_profit         -- holding must be at least break-even
      2. min_position_age  -- holding must be older than 30d
      3. earnings_proximity -- next earnings must be > 5 days away

    high_severity_negative_news is NOT a gate here -- it's a SIGNAL
    in the 'risk' group. We WANT to surface stocks with bad news as
    sell candidates, not hide them.

    Mirrors evaluate_gates structure (skipped vs passed/failed) so the
    explainability layer renders them identically.
    """
    gates: list[GateResult] = []
    gate_config = config["gates"]

    # 1. In-profit gate
    invested = _flt(holding.get("invested_amount"))
    qty = _flt(holding.get("quantity"))
    px = _flt(current_price)
    pnl_threshold = gate_config["min_unrealized_pnl_pct"]
    if invested is None or invested <= 0 or qty is None or qty <= 0 or px is None:
        gates.append(
            GateResult(
                gate_name="in_profit",
                passed=False,
                skipped=True,
                threshold=f"unrealized P&L >= {pnl_threshold:.0f}%",
                skip_reason="Missing invested_amount, quantity, or current price",
            )
        )
    else:
        current_value = px * qty
        unrealized_pct = ((current_value - invested) / invested) * 100
        passed = unrealized_pct >= pnl_threshold
        gates.append(
            GateResult(
                gate_name="in_profit",
                passed=passed,
                threshold=f"unrealized P&L >= {pnl_threshold:.0f}%",
                actual_value=f"P&L = {unrealized_pct:+.2f}%",
            )
        )

    # 2. Min position age gate
    age_threshold = gate_config["min_position_age_days"]
    first_purchased = holding.get("first_purchased_at")
    if first_purchased is None:
        gates.append(
            GateResult(
                gate_name="min_position_age",
                passed=False,
                skipped=True,
                threshold=f"position held >= {age_threshold} days",
                skip_reason="Holding missing first_purchased_at",
            )
        )
    else:
        naive_fp = (
            first_purchased.replace(tzinfo=None)
            if hasattr(first_purchased, "tzinfo") and first_purchased.tzinfo is not None
            else first_purchased
        )
        now_naive = utcnow().replace(tzinfo=None)
        days_held = (now_naive - naive_fp).total_seconds() / 86400.0
        passed = days_held >= age_threshold
        gates.append(
            GateResult(
                gate_name="min_position_age",
                passed=passed,
                threshold=f"position held >= {age_threshold} days",
                actual_value=f"held {days_held:.0f} days",
            )
        )

    # 3. Earnings proximity (shared helper).
    gates.append(
        evaluate_earnings_proximity_gate(
            next_earnings,
            gate_config["earnings_proximity_days"],
        )
    )

    return gates


def score_sell_candidates(
    candidates: list[dict],
    fundamentals_by_isin: dict[str, dict],
    price_history_by_isin: dict[str, list[dict]],
    news_signals_by_isin: dict[str, dict],
    holdings_by_isin: dict[str, dict],
    next_earnings_by_isin: dict[str, datetime],
    portfolio_value: Decimal,
    config: dict | None = None,
) -> list[CandidateScore]:
    """Score held stocks for sell-side suggestions.

    Args:
        candidates: list of {isin, symbol, name?, sector?} for the held universe.
        fundamentals_by_isin: latest fundamentals snapshot per ISIN.
        price_history_by_isin: 1y daily price docs per ISIN (newest first).
        news_signals_by_isin: news signals per ISIN.
        holdings_by_isin: active holdings doc per ISIN.
        next_earnings_by_isin: {isin: next earnings date}; missing means no event.
        portfolio_value: total portfolio current value in INR.
        config: defaults to DEFAULT_SELL_CONFIG.

    Returns ranked list of CandidateScore. Same model as buy-side, just
    different group_scores (booking_opportunity / valuation_stretch /
    risk / tax_concentration instead of QVMN).

    The CandidateScore model has fixed buy-side group fields
    (quality_score, valuation_score, momentum_score, news_score). We
    keep those at 0.0 for sell-side rows; the per-group scores live in
    the signals list and in normalized_by_group during composition.
    Frontend will read group_meta (from explainability) for display.
    """
    cfg = config or DEFAULT_SELL_CONFIG
    lower_is_better_set = set(cfg["scoring"]["lower_is_better"])

    # Phase 1: extract sell-side signals for every candidate.
    candidate_signals: dict[str, dict[str, float | None]] = {}
    for c in candidates:
        isin = c["isin"]
        holding = holdings_by_isin.get(isin)
        if holding is None:
            # Should not happen if caller filters universe correctly, but
            # be defensive: a candidate without a holding cannot be scored.
            log.warning("score_sell_candidates: no holding for ISIN %s", isin)
            candidate_signals[isin] = {}
            continue
        candidate_signals[isin] = extract_sell_signals(
            fundamentals_by_isin.get(isin),
            price_history_by_isin.get(isin, []),
            news_signals_by_isin.get(isin),
            holding,
            portfolio_value,
        )

    # Phase 2: run sell-side gates per candidate.
    candidate_gates: dict[str, list[GateResult]] = {}
    eligible_isins: list[str] = []
    for c in candidates:
        isin = c["isin"]
        holding = holdings_by_isin.get(isin, {})
        sig = candidate_signals.get(isin, {})
        latest_close = sig.get("_latest_close")
        latest_close_dec = (
            Decimal(str(latest_close)) if latest_close is not None else None
        )
        gates = evaluate_sell_gates(
            holding,
            latest_close_dec,
            next_earnings_by_isin.get(isin),
            cfg,
        )
        candidate_gates[isin] = gates
        _, _, _, eligible = gates_summary(gates)
        if eligible:
            eligible_isins.append(isin)

    # Phase 3: normalize within the ELIGIBLE universe per group.
    eligible_signals = {isin: candidate_signals[isin] for isin in eligible_isins}
    normalized_by_group: dict[str, dict[str, dict[str, float | None]]] = {}
    for group_name in GROUP_SIGNALS_SELL:
        normalized_by_group[group_name] = score_group(
            group_name,
            eligible_signals,
            lower_is_better_set,
            group_signals_def=GROUP_SIGNALS_SELL,
        )

    # Phase 4: compose final candidate scores.
    now = datetime.now(
        timezone.utc
    )  # tz-ok: aware base for fundamentals/price age diffs (both coerced aware below)
    results: list[CandidateScore] = []
    for c in candidates:
        isin = c["isin"]
        gates = candidate_gates[isin]
        passed, failed, skipped, eligible = gates_summary(gates)
        fundamentals = fundamentals_by_isin.get(isin)
        prices = price_history_by_isin.get(isin, [])
        news_sig = news_signals_by_isin.get(isin)
        has_news = bool(news_sig and news_sig.get("has_news"))

        if eligible:
            composite, group_scores, signal_scores = composite_for_candidate(
                isin,
                normalized_by_group,
                has_news,
                cfg,
                group_signals_def=GROUP_SIGNALS_SELL,
                missing_group_default=50.0,
                candidate_signals_for_isin=candidate_signals.get(isin),
            )
        else:
            composite = 0.0
            group_scores = {g: 0.0 for g in GROUP_SIGNALS_SELL}
            signal_scores = []

        # Age + price-staleness for confidence (same buy-side logic).
        fundamentals_age_days: float | None = None
        if fundamentals and fundamentals.get("fetched_at"):
            ft = fundamentals["fetched_at"]
            if ft.tzinfo is None:
                ft = ft.replace(tzinfo=timezone.utc)
            fundamentals_age_days = (now - ft).total_seconds() / 86400.0
        price_age_days: float | None = None
        latest_price_ts: datetime | None = None
        latest_price_value = None
        if prices:
            pdate = prices[0].get("date")
            # #80 M4: extract close OUTSIDE `if pdate` (mirrors buy-side).
            # Buy-side sets latest_price_value unconditionally when prices exist;
            # sell-side set it inside `if pdate`, leaving it None when the price
            # doc has a close but a missing date field. A None current_price
            # flows into create_outcomes_for_run as suggested_at_price=0, which
            # permanently disables excess-return computation for that outcome
            # (the `if suggested_price and suggested_price > 0` guard never fires
            # and the field guard `if outcome.get(field_name) is not None`
            # short-circuits all future runs for that outcome).
            latest_price_value = _dec(prices[0].get("close"))
            if pdate:
                if pdate.tzinfo is None:
                    pdate = pdate.replace(tzinfo=timezone.utc)
                price_age_days = (now - pdate).total_seconds() / 86400.0
                latest_price_ts = pdate
        news_freshness = news_sig.get("days_since_latest_news") if news_sig else None

        confidence, deductions = compute_confidence(
            fundamentals=fundamentals,
            fundamentals_age_days=fundamentals_age_days,
            price_age_days=price_age_days,
            group_scores=group_scores,
            gates=gates,
            has_news=has_news,
            news_freshness_days=news_freshness,
        )

        # TD7/#45: sell group scores are now FIRST-CLASS persisted fields on
        # CandidateScore (booking_opportunity/valuation_stretch/risk/
        # tax_concentration), populated from the group_scores dict just like
        # the buy pipeline populates quality/valuation/momentum/news. The
        # buy-named fields stay 0.0 for a sell run (buy semantics don't apply);
        # direction on the parent SuggestionRun disambiguates which quartet is
        # meaningful. explainability._build_group_meta reads f"{group}_score",
        # so these keys now flow through to sell group_meta correctly (before
        # #45 they were dropped here and group_meta read nonexistent keys).
        results.append(
            CandidateScore(
                isin=isin,
                symbol=c["symbol"],
                name=c.get("name", ""),
                sector=c.get("sector", "")
                or (fundamentals.get("sector", "") if fundamentals else ""),
                composite_score=composite,
                rank=0,
                confidence_score=confidence,
                confidence_deductions=deductions,
                quality_score=0.0,
                valuation_score=0.0,
                momentum_score=0.0,
                news_score=0.0,
                booking_opportunity_score=group_scores.get("booking_opportunity", 0.0),
                valuation_stretch_score=group_scores.get("valuation_stretch", 0.0),
                risk_score=group_scores.get("risk", 0.0),
                tax_concentration_score=group_scores.get("tax_concentration", 0.0),
                signals=signal_scores,
                gates=gates,
                gates_passed=passed,
                gates_failed=failed,
                gates_skipped=skipped,
                fundamentals_fetched_at=(
                    fundamentals.get("fetched_at") if fundamentals else None
                ),
                price_as_of=latest_price_ts,
                current_price=latest_price_value,
            )
        )

    results.sort(
        key=lambda r: (r.gates_failed == 0, r.composite_score),
        reverse=True,
    )
    for i, r in enumerate(results):
        r.rank = i + 1
    return results
