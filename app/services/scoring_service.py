"""Scoring engine for Phase 2 suggestions — Unit 2 (with News)."""

from __future__ import annotations

import logging
import math
import statistics
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from bson import Decimal128

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


def evaluate_gates(
    fundamentals: dict | None,
    news_signals: dict | None,
    config: dict,
) -> list[GateResult]:
    """Run quality gates against a candidate. Unit 2 adds the news gate."""
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
        signals["news_net_sentiment"] = float(news_signals["net_sentiment"]) * 100
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
) -> dict[str, dict[str, float | None]]:
    out: dict[str, dict[str, float | None]] = {isin: {} for isin in candidate_signals}
    group_def = GROUP_SIGNALS.get(group_name, {})
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
) -> tuple[float, dict[str, float], list[SignalScore]]:
    """Compute composite score for one candidate."""
    group_scores: dict[str, float] = {}
    signal_scores: list[SignalScore] = []
    weights = config["weights"]

    for group_name, signal_weights in GROUP_SIGNALS.items():
        per_signal = normalized_by_group.get(group_name, {}).get(isin, {})
        total_weight = 0.0
        weighted_sum = 0.0
        for signal_name, weight_in_group in signal_weights.items():
            score = per_signal.get(signal_name)
            if score is None:
                signal_scores.append(
                    SignalScore(
                        signal_name=signal_name,
                        raw_value="",
                        normalized_score=0.0,
                        weight=weight_in_group * weights.get(group_name, 0.0),
                        available=False,
                    )
                )
                continue
            weighted_sum += score * weight_in_group
            total_weight += weight_in_group
            signal_scores.append(
                SignalScore(
                    signal_name=signal_name,
                    raw_value=f"{score:.2f}",
                    normalized_score=score,
                    weight=weight_in_group * weights.get(group_name, 0.0),
                    available=True,
                )
            )

        if total_weight > 0:
            group_scores[group_name] = weighted_sum / total_weight
        elif group_name == "news" and not candidate_has_news:
            group_scores[group_name] = 50.0
        else:
            group_scores[group_name] = 0.0

    composite = sum(
        group_scores.get(g, 0.0) * weights.get(g, 0.0)
        for g in ("quality", "valuation", "momentum", "news")
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
) -> list[CandidateScore]:
    """Score all candidates and return ranked CandidateScore objects."""
    cfg = config or DEFAULT_CONFIG
    lower_is_better_set = set(cfg["scoring"]["lower_is_better"])

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

    now = datetime.now(timezone.utc)
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
