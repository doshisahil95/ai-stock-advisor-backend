"""Scoring engine for Phase 2 suggestions.

Pure-function module. No I/O — takes inputs, returns CandidateScore objects.
This makes it trivially testable and makes runs reproducible (same inputs +
same config = same outputs, byte-for-byte).

Design:
  - Each signal is normalized to 0-100 within the surviving universe
    (z-score → sigmoid → scaled), so scores are relative within a run.
  - Signals are grouped (Quality, Valuation, Momentum, News).
  - Group scores are weighted means of their signals.
  - Composite is weighted sum of group scores.
  - Confidence is computed deterministically (NOT from the composite —
    it captures data quality + signal agreement).

Unit 1 implements Quality + Valuation + Momentum. News group always returns
0.0 with no signals (will be filled in Unit 2 — weights re-balance then).

The config is passed in (not imported from settings) so the SuggestionRun
can snapshot the exact config used and replay later.
"""

from __future__ import annotations

import logging
import math
import statistics
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any

from app.models.suggestion import CandidateScore, GateResult, SignalScore

log = logging.getLogger(__name__)

# ── Config (frozen per run, snapshotted into SuggestionRun.config) ───────────

DEFAULT_CONFIG = {
    "weights": {
        "quality": 0.35,
        "valuation": 0.30,
        "momentum": 0.35,
        "news": 0.0,  # Unit 1: news disabled. Unit 2 will rebalance to 0.30/0.25/0.25/0.20.
    },
    "gates": {
        # Hard filters. Stocks failing any of these are dropped from scoring entirely.
        "max_debt_to_equity": 1.5,  # D/E ratio (post-normalization, decimal)
        "min_return_on_equity": 0.10,  # 10% as decimal
        "min_market_cap_inr": 10_000 * 1_00_00_000,  # ₹10,000 crore in rupees
    },
    "freshness": {
        "fundamentals_max_age_days": 14,
        "prices_max_age_days": 5,  # 5 trading days = ~1 calendar week
    },
    "scoring": {
        # Signals that are "lower is better" (e.g., debt) get inverted before normalization
        "lower_is_better": ["debt_to_equity", "pe_ratio", "pb_ratio"],
    },
    "top_k": 10,
    "version": "1.0.0-unit1",
}

# ── Helpers ──────────────────────────────────────────────────────────────────


def _dec(v: Any) -> Decimal | None:
    """Coerce Decimal128/Decimal/float/int -> Decimal. None passes through."""
    if v is None:
        return None
    from bson import Decimal128

    if isinstance(v, Decimal128):
        return v.to_decimal()
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, float)):
        if isinstance(v, float) and v != v:  # NaN
            return None
        return Decimal(str(v))
    return None


def _flt(v: Any) -> float | None:
    """Coerce to float. None on missing / NaN / failure."""
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
    """Convert raw signal values to 0-100 normalized scores within the universe.

    Method:
      1. Drop None values for stats
      2. Compute z-score per value (against universe mean+stddev)
      3. Apply logistic (sigmoid) to map z to (0, 1)
      4. Scale to (0, 100)
      5. If lower_is_better, invert (100 - score)

    Returns the same-length list with None preserved where input was None.
    """
    valid = [v for v in values if v is not None]
    if len(valid) < 2:
        # Not enough data for normalization; return 50.0 for any present value
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
        # Sigmoid: 1 / (1 + e^(-z)) maps z to (0, 1).
        # Cap z to ±5 to avoid floating overflow.
        z = max(-5.0, min(5.0, z))
        sigmoid = 1.0 / (1.0 + math.exp(-z))
        score = sigmoid * 100.0
        if lower_is_better:
            score = 100.0 - score
        out.append(round(score, 2))
    return out


# ── Quality gates ────────────────────────────────────────────────────────────


def evaluate_gates(fundamentals: dict | None, config: dict) -> list[GateResult]:
    """Run quality gates against a candidate's fundamentals. Returns gate results.
    A candidate "fails" the gates if any non-skipped gate has passed=False.
    """
    gates: list[GateResult] = []
    gate_config = config["gates"]

    if fundamentals is None:
        # Fundamentals missing entirely — skip all gates with reasons
        for gate_name in ["debt_to_equity", "return_on_equity", "market_cap"]:
            gates.append(
                GateResult(
                    gate_name=gate_name,
                    passed=False,
                    skipped=True,
                    skip_reason="Fundamentals doc missing for this ISIN",
                )
            )
        return gates

    # Gate 1: debt-to-equity
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

    # Gate 2: ROE
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

    # Gate 3: market cap floor
    mc = _flt(fundamentals.get("market_cap"))
    floor = gate_config["min_market_cap_inr"]
    floor_cr = floor / 1_00_00_000
    if mc is None:
        gates.append(
            GateResult(
                gate_name="market_cap",
                passed=False,
                skipped=True,
                threshold=f"Mkt Cap >= ₹{floor_cr:,.0f} Cr",
                skip_reason="market_cap not available from yfinance",
            )
        )
    else:
        passed = mc >= floor
        gates.append(
            GateResult(
                gate_name="market_cap",
                passed=passed,
                threshold=f"Mkt Cap >= ₹{floor_cr:,.0f} Cr",
                actual_value=f"Mkt Cap = ₹{mc / 1_00_00_000:,.0f} Cr",
            )
        )

    return gates


def gates_summary(gates: list[GateResult]) -> tuple[int, int, int, bool]:
    """Returns (passed, failed, skipped, candidate_eligible).
    A candidate is eligible if no non-skipped gate failed.
    """
    passed = sum(1 for g in gates if g.passed and not g.skipped)
    failed = sum(1 for g in gates if not g.passed and not g.skipped)
    skipped = sum(1 for g in gates if g.skipped)
    eligible = failed == 0  # Skipped gates are tolerated, hard fails are not
    return passed, failed, skipped, eligible


# ── Per-stock signal extraction ──────────────────────────────────────────────


def extract_signals(
    fundamentals: dict | None,
    price_history: list[dict],
) -> dict[str, float | None]:
    """Pull all raw signal values from fundamentals + price history.

    price_history is newest-first list of {date, close, ...} as returned by
    get_price_history() from price_service.

    Returns {signal_name: raw_value_or_None}.
    """
    signals: dict[str, float | None] = {}

    # Fundamentals-derived signals
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

    # Price-derived signals (price_history is newest-first)
    if price_history and len(price_history) >= 2:
        # Most recent close
        latest_close = _flt(price_history[0].get("close"))
        signals["_latest_close"] = latest_close

        # 3M return: ~63 trading days
        if len(price_history) > 63 and latest_close is not None:
            old = _flt(price_history[63].get("close"))
            signals["return_3m"] = (
                (latest_close / old - 1) * 100 if old and old > 0 else None
            )
        else:
            signals["return_3m"] = None

        # 6M return: ~126 trading days
        if len(price_history) > 126 and latest_close is not None:
            old = _flt(price_history[126].get("close"))
            signals["return_6m"] = (
                (latest_close / old - 1) * 100 if old and old > 0 else None
            )
        else:
            signals["return_6m"] = None

        # Distance from 52-week high (negative % = below high; we want close to 0 = strong)
        # Use up to 252 trading days
        window = price_history[: min(252, len(price_history))]
        closes = [_flt(p.get("close")) for p in window]
        closes = [c for c in closes if c is not None]
        if closes and latest_close is not None:
            high_52w = max(closes)
            low_52w = min(closes)
            signals["dist_from_52w_high_pct"] = (
                (latest_close / high_52w - 1) * 100 if high_52w > 0 else None
            )
            # Distance from 52w low (positive = above low; higher = stronger)
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

    return signals


# ── Group scoring ────────────────────────────────────────────────────────────

# Which signals belong to which group, and their weight WITHIN the group
GROUP_SIGNALS = {
    "quality": {
        "return_on_equity": 0.35,
        "return_on_assets": 0.20,
        "operating_margin": 0.20,
        "debt_to_equity": 0.25,  # lower is better
    },
    "valuation": {
        "pe_ratio": 0.50,  # lower is better
        "pb_ratio": 0.30,  # lower is better
        "earnings_growth_yoy": 0.20,
    },
    "momentum": {
        "return_3m": 0.30,
        "return_6m": 0.40,
        "dist_from_52w_high_pct": 0.30,  # closer to 0 = stronger; we add 100 implicitly via sigmoid
    },
}


def score_group(
    group_name: str,
    candidate_signals: dict[str, dict[str, float | None]],
    lower_is_better_set: set[str],
) -> dict[str, dict[str, float | None]]:
    """Score one group across all candidates.

    candidate_signals: {isin: {signal_name: raw_value_or_None}}
    Returns {isin: {signal_name: normalized_score_0_100, ...}} for this group's signals.
    Per-isin missing signals stay None.
    """
    out: dict[str, dict[str, float | None]] = {isin: {} for isin in candidate_signals}
    group_def = GROUP_SIGNALS.get(group_name, {})
    for signal_name in group_def:
        # Collect raw values across candidates in stable order
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
    config: dict,
) -> tuple[float, dict[str, float], list[SignalScore]]:
    """Compute composite score, group scores, and SignalScore list for one candidate.

    normalized_by_group: {group_name: {isin: {signal_name: normalized_score}}}
    """
    group_scores: dict[str, float] = {}
    signal_scores: list[SignalScore] = []
    weights = config["weights"]

    for group_name, signal_weights in GROUP_SIGNALS.items():
        per_signal = normalized_by_group.get(group_name, {}).get(isin, {})
        # Compute weighted mean across this group's signals (skip None values)
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
                    raw_value=f"{score:.2f}",  # Already normalized — actual raw stored elsewhere
                    normalized_score=score,
                    weight=weight_in_group * weights.get(group_name, 0.0),
                    available=True,
                )
            )
        if total_weight > 0:
            group_scores[group_name] = weighted_sum / total_weight
        else:
            group_scores[group_name] = 0.0

    # News group: always 0 in Unit 1
    group_scores.setdefault("news", 0.0)

    composite = sum(
        group_scores.get(g, 0.0) * weights.get(g, 0.0)
        for g in ("quality", "valuation", "momentum", "news")
    )
    return (
        round(composite, 2),
        {k: round(v, 2) for k, v in group_scores.items()},
        signal_scores,
    )


# ── Confidence ───────────────────────────────────────────────────────────────


def compute_confidence(
    fundamentals: dict | None,
    fundamentals_age_days: float | None,
    price_age_days: float | None,
    group_scores: dict[str, float],
    gates: list[GateResult],
    has_news: bool = False,  # Unit 2 will set this to True when news data is present
) -> tuple[float, list[str]]:
    """Compute confidence_score (0-100) deterministically.

    Returns (score, list_of_deduction_reasons).
    """
    score = 100.0
    reasons: list[str] = []

    # Data freshness
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

    # Signal availability per group
    median_signal_score = 50.0  # by construction (sigmoid centered at universe mean)
    for group_name, group_score in group_scores.items():
        if group_name == "news":
            continue  # Unit 1: news intentionally absent
        if group_score < median_signal_score - 10:
            score -= 10
            reasons.append(f"{group_name.title()} group below median (-10)")

    # News absence is a -10 (will go away in Unit 2)
    if not has_news:
        score -= 10
        reasons.append("News signals not yet integrated (-10)")

    # Gates almost-failed
    almost_failed = 0
    for gate in gates:
        if gate.skipped or not gate.passed:
            continue
        # We don't have margin info per gate yet; placeholder. In Unit 2/3 we
        # can extract numeric margins from gate.actual_value if needed.

    # Floor
    score = max(0.0, min(100.0, score))
    return round(score, 2), reasons


# ── Public entry: score a full candidate set ─────────────────────────────────


def score_candidates(
    candidates: list[dict],
    fundamentals_by_isin: dict[str, dict],
    price_history_by_isin: dict[str, list[dict]],
    config: dict | None = None,
) -> list[CandidateScore]:
    """Score all eligible candidates and return ranked CandidateScore objects.

    Args:
        candidates: list of {isin, symbol, name, sector, exchange} dicts.
                    Should already exclude held + rejected stocks.
        fundamentals_by_isin: {isin: fundamentals_doc} from get_latest_bulk()
        price_history_by_isin: {isin: list[price_doc]} (newest-first per ISIN)
        config: optional override of DEFAULT_CONFIG; defaults used if None.

    Returns:
        Sorted list of CandidateScore (best first). Stocks failing gates are
        included with composite_score=0.0 and gates_failed > 0 so the run doc
        captures them — but they go to the BOTTOM of the list, not the top.
    """
    cfg = config or DEFAULT_CONFIG
    lower_is_better_set = set(cfg["scoring"]["lower_is_better"])

    # 1. Build per-candidate signal map
    candidate_signals: dict[str, dict[str, float | None]] = {}
    for c in candidates:
        isin = c["isin"]
        candidate_signals[isin] = extract_signals(
            fundamentals_by_isin.get(isin),
            price_history_by_isin.get(isin, []),
        )

    # 2. Evaluate gates per candidate
    candidate_gates: dict[str, list[GateResult]] = {}
    eligible_isins: list[str] = []
    for c in candidates:
        isin = c["isin"]
        gates = evaluate_gates(fundamentals_by_isin.get(isin), cfg)
        candidate_gates[isin] = gates
        _, _, _, eligible = gates_summary(gates)
        if eligible:
            eligible_isins.append(isin)

    # 3. Score eligible candidates per group (cross-candidate normalization)
    eligible_signals = {isin: candidate_signals[isin] for isin in eligible_isins}
    normalized_by_group: dict[str, dict[str, dict[str, float | None]]] = {}
    for group_name in GROUP_SIGNALS:
        normalized_by_group[group_name] = score_group(
            group_name,
            eligible_signals,
            lower_is_better_set,
        )

    # 4. Build CandidateScore objects
    now = datetime.now(timezone.utc)
    results: list[CandidateScore] = []

    for c in candidates:
        isin = c["isin"]
        gates = candidate_gates[isin]
        passed, failed, skipped, eligible = gates_summary(gates)

        fundamentals = fundamentals_by_isin.get(isin)
        prices = price_history_by_isin.get(isin, [])

        if eligible:
            composite, group_scores, signal_scores = composite_for_candidate(
                isin,
                normalized_by_group,
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

        # Ages for confidence
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

        confidence, deductions = compute_confidence(
            fundamentals=fundamentals,
            fundamentals_age_days=fundamentals_age_days,
            price_age_days=price_age_days,
            group_scores=group_scores,
            gates=gates,
            has_news=False,  # Unit 1
        )

        results.append(
            CandidateScore(
                isin=isin,
                symbol=c["symbol"],
                name=c.get("name", ""),
                sector=c.get("sector", "")
                or (fundamentals.get("sector", "") if fundamentals else ""),
                composite_score=composite,
                rank=0,  # filled after sort
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

    # 5. Sort by composite (eligible first by score, then ineligible at bottom)
    results.sort(
        key=lambda r: (r.gates_failed == 0, r.composite_score),
        reverse=True,
    )
    for i, r in enumerate(results):
        r.rank = i + 1

    return results
