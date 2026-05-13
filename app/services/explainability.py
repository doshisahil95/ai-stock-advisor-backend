"""Explainability layer for the Suggestions Engine.

Static catalogs and helpers that translate the technical signals, group scores,
gates, confidence deductions, and feedback actions into plain English that a
non-analyst can read.

This module is purely additive. It does not change any computation; it only
enriches API responses with `*_meta` fields that the frontend can render as
tooltips, popovers, and "what does this mean" copy.

Design:
    - Catalogs are module-level dicts so they are cheap to read and easy to
      audit.
    - The router calls `enrich_run(run_dict)` after JSON-converting a
      SuggestionRun. That call adds:
        * candidate.signal_meta     -- per-signal display + raw value + description
        * candidate.group_meta      -- per-group label + description + interpretation
        * candidate.gate_meta       -- per-gate plain-English pass/fail rationale
        * candidate.confidence_meta -- score interpretation + deduction explainer
        * run.feedback_meta         -- explains the three feedback actions
        * run.page_intro            -- "How to read this page" copy
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from bson import Decimal128

from app.services.fundamentals_service import get_latest_bulk as get_fundamentals_bulk

log = logging.getLogger(__name__)


# Signal catalog
# Each entry describes ONE raw signal that feeds the scoring engine.
# `formatter_kind` controls how the raw fundamental value is rendered.

SIGNAL_META: dict[str, dict[str, str]] = {
    # Quality signals
    "return_on_equity": {
        "display_name": "Return on Equity (ROE)",
        "short_description": "How efficiently the company turns shareholder capital into profit.",
        "what_higher_means": "Higher is better. 15%+ is generally considered strong for Indian large-caps.",
        "formatter_kind": "percent_decimal",
        "fundamentals_field": "return_on_equity",
    },
    "return_on_assets": {
        "display_name": "Return on Assets (ROA)",
        "short_description": "How efficiently the company turns ALL its assets (debt + equity) into profit.",
        "what_higher_means": "Higher is better. ROA gives a debt-neutral view of efficiency.",
        "formatter_kind": "percent_decimal",
        "fundamentals_field": "return_on_assets",
    },
    "operating_margin": {
        "display_name": "Operating Margin",
        "short_description": "Profit from core operations as a percentage of revenue, before interest and tax.",
        "what_higher_means": "Higher means more pricing power and operating efficiency.",
        "formatter_kind": "percent_decimal",
        "fundamentals_field": "operating_margin",
    },
    "debt_to_equity": {
        "display_name": "Debt-to-Equity (D/E)",
        "short_description": "How much debt the company carries compared to shareholder equity.",
        "what_higher_means": "Lower is better. D/E above 1.5 starts looking risky for non-financials.",
        "formatter_kind": "ratio",
        "fundamentals_field": "debt_to_equity",
    },
    # Valuation signals
    "pe_ratio": {
        "display_name": "Price-to-Earnings (P/E)",
        "short_description": "How many years of current earnings the market is paying for the stock today.",
        "what_higher_means": "Lower is generally better (cheaper). Very low P/E can also signal trouble.",
        "formatter_kind": "multiple",
        "fundamentals_field": "pe_ratio",
    },
    "pb_ratio": {
        "display_name": "Price-to-Book (P/B)",
        "short_description": "Market price compared to the company's book (accounting) value per share.",
        "what_higher_means": "Lower means cheaper relative to book value. Useful for asset-heavy businesses.",
        "formatter_kind": "multiple",
        "fundamentals_field": "pb_ratio",
    },
    "earnings_growth_yoy": {
        "display_name": "Earnings Growth (YoY)",
        "short_description": "How much the company's earnings grew year-over-year.",
        "what_higher_means": "Higher is better. Sustained double-digit growth is a positive valuation signal.",
        "formatter_kind": "percent_decimal",
        "fundamentals_field": "earnings_growth_yoy",
    },
    # Momentum signals
    "return_3m": {
        "display_name": "3-Month Return",
        "short_description": "How the stock price has moved over the last 3 months.",
        "what_higher_means": "Higher means recent momentum is positive. Extreme runs may also signal stretched valuations.",
        "formatter_kind": "percent_already",
        "fundamentals_field": None,  # Computed from price_history, not stored
    },
    "return_6m": {
        "display_name": "6-Month Return",
        "short_description": "How the stock price has moved over the last 6 months.",
        "what_higher_means": "Higher means medium-term momentum is positive.",
        "formatter_kind": "percent_already",
        "fundamentals_field": None,
    },
    "dist_from_52w_high_pct": {
        "display_name": "Distance from 52-Week High",
        "short_description": "How far below the 52-week high the stock is trading right now.",
        "what_higher_means": "Closer to 0% (i.e. near the high) reads as strong momentum. Deep discounts can be value or value traps.",
        "formatter_kind": "percent_already",
        "fundamentals_field": None,
    },
    # News signals (raw values not persisted post-run; we show normalized only)
    "news_net_sentiment": {
        "display_name": "News Net Sentiment",
        "short_description": "Average sentiment of recent classified news in the last 30 days.",
        "what_higher_means": "Higher means recent coverage skews positive.",
        "formatter_kind": "score_only",
        "fundamentals_field": None,
    },
    "news_story_velocity": {
        "display_name": "News Story Velocity",
        "short_description": "Whether news coverage is accelerating (recent week vs prior weeks).",
        "what_higher_means": "Higher means coverage is picking up. This can be good (catalyst) or bad (controversy).",
        "formatter_kind": "score_only",
        "fundamentals_field": None,
    },
    "news_story_count": {
        "display_name": "News Story Count",
        "short_description": "How many classified news stories exist for this stock in the last 30 days.",
        "what_higher_means": "Higher means more analyst and media attention. Zero coverage is a signal too.",
        "formatter_kind": "score_only",
        "fundamentals_field": None,
    },
}


# Group catalog
# Each group is a weighted bundle of signals. Q/V/M/N = 30/25/25/20.

GROUP_META: dict[str, dict[str, str]] = {
    "quality": {
        "display_name": "Quality",
        "weight_pct": "30%",
        "what_it_measures": (
            "How financially healthy and well-run the business is. "
            "Built from ROE, ROA, operating margin, and debt levels."
        ),
        "interpretation_strong": "Strong fundamentals. The company makes good money and is not over-leveraged.",
        "interpretation_ok": "Average fundamentals for the NIFTY 100 universe.",
        "interpretation_weak": "Below-average fundamentals. Could be cyclical weakness or a structural issue.",
    },
    "valuation": {
        "display_name": "Valuation",
        "weight_pct": "25%",
        "what_it_measures": (
            "How expensive the stock is relative to its earnings, book value, and growth. "
            "Built from P/E, P/B, and earnings growth."
        ),
        "interpretation_strong": "Looks cheap relative to peers. Could be a value opportunity or a value trap.",
        "interpretation_ok": "Reasonably priced. Not a bargain, not expensive.",
        "interpretation_weak": "Looks expensive on the standard multiples. Growth expectations need to be very high.",
    },
    "momentum": {
        "display_name": "Momentum",
        "weight_pct": "25%",
        "what_it_measures": (
            "Whether the stock price has been trending up or down recently. "
            "Built from 3-month return, 6-month return, and distance from 52-week high."
        ),
        "interpretation_strong": "Trading near recent highs with strong recent gains. Trend is your friend, until it isn't.",
        "interpretation_ok": "Mixed price action. No clear up- or down-trend.",
        "interpretation_weak": "Price has been weak. Could be a contrarian setup or continued downtrend.",
    },
    "news": {
        "display_name": "News",
        "weight_pct": "20%",
        "what_it_measures": (
            "Sentiment, volume, and recency of news coverage in the last 30 days. "
            "Built from net sentiment, story velocity, and story count."
        ),
        "interpretation_strong": "Recent news is overwhelmingly positive and coverage is heating up.",
        "interpretation_ok": "Mixed or balanced news. Nothing one-sided.",
        "interpretation_weak": (
            "Recent news skews negative or coverage is sparse. "
            "If sparse, the engine may be operating with limited information."
        ),
    },
}


# Gate catalog
# Gates are pass/fail filters. A failed gate makes the candidate ineligible.

GATE_META: dict[str, dict[str, str]] = {
    "debt_to_equity": {
        "display_name": "Debt-to-Equity check",
        "why_we_check": (
            "Companies with very high leverage (D/E > 1.5) are vulnerable to interest "
            "rate moves and earnings slowdowns. We exclude them by default."
        ),
        "plain_english_pass": "The company's debt level is within a healthy range.",
        "plain_english_fail": "The company carries too much debt to pass our default safety filter.",
    },
    "return_on_equity": {
        "display_name": "Return on Equity check",
        "why_we_check": (
            "ROE below 10% over time often signals capital destruction. "
            "We require a minimum 10% ROE so we are not accumulating low-quality compounders."
        ),
        "plain_english_pass": "The company is generating decent returns on shareholder capital.",
        "plain_english_fail": "The company is not earning enough on its equity to pass our quality filter.",
    },
    "market_cap": {
        "display_name": "Market Capitalization check",
        "why_we_check": (
            "We require at least Rs 10,000 Cr market cap to ensure liquidity and "
            "stay within the broad large-cap NIFTY 100 universe."
        ),
        "plain_english_pass": "The company is large enough to trade easily and meets our liquidity floor.",
        "plain_english_fail": "The company is too small to pass our liquidity filter.",
    },
    "high_severity_negative_news": {
        "display_name": "High-severity negative news check",
        "why_we_check": (
            "If there is more than 1 high-severity NEGATIVE news story in the last "
            "30 days (regulatory action, fraud allegations, major management exit, etc.), "
            "we exclude until things settle down."
        ),
        "plain_english_pass": "No serious negative-news red flags in the last 30 days.",
        "plain_english_fail": "Recent serious negative news. Excluded until the picture clears up.",
    },
}


# Confidence catalog

CONFIDENCE_META: dict[str, str] = {
    "what_it_means": (
        "Confidence is a 0-100 score that tells you how trustworthy this week's "
        "ranking is for THIS stock. It is computed deterministically from data freshness "
        "and signal availability, not from the LLM. Composite score answers 'is this stock "
        "attractive?'; confidence answers 'should I trust the answer?'."
    ),
    "interpretation_high": "High confidence (90+). All signals are fresh and complete.",
    "interpretation_med": "Medium confidence (70-89). Some signals are missing or slightly stale.",
    "interpretation_low": "Low confidence (<70). Significant data gaps. Treat the ranking as a hint, not a verdict.",
    "deduction_categories": (
        "Confidence is reduced when fundamentals are missing or stale, prices are stale, "
        "no recent news has been classified, or any signal group is well below the universe median."
    ),
}


# Feedback action catalog

FEEDBACK_META: dict[str, dict[str, str]] = {
    "acted": {
        "display_name": "Acted on this",
        "what_it_does": "Mark that you actually opened a position in this stock based on the suggestion.",
        "side_effects": (
            "The suggestion outcome is moved from 'open' to 'acted'. The system will "
            "still track its 30/60/90/180-day return vs NIFTY 100 so you can see whether "
            "the engine is helping you. The stock is added to monitored_stocks."
        ),
    },
    "passed": {
        "display_name": "Passed",
        "what_it_does": "Mark that you saw the suggestion but chose not to act on it.",
        "side_effects": (
            "The suggestion outcome is moved to 'passed'. The stock will not be excluded "
            "from future runs. Useful for tracking how often the engine surfaces ideas you "
            "consider but skip."
        ),
    },
    "rejected": {
        "display_name": "Not interested (90 days)",
        "what_it_does": "Tell the system you don't want to see this stock again for the next 90 days.",
        "side_effects": (
            "The stock is excluded from the next ~13 weekly runs. After 90 days the "
            "rejection expires automatically and the stock can be surfaced again."
        ),
    },
}


# Page-level intro

PAGE_INTRO: dict[str, Any] = {
    "title": "How to read this page",
    "summary": (
        "Every Sunday morning the system scans the NIFTY 100 (minus stocks you already "
        "hold and minus stocks you've recently rejected) and ranks them by a composite "
        "score built from four signal groups. The top candidates get a Claude-generated "
        "research dossier. Nothing here is a buy or sell instruction -- the system records, "
        "analyzes, and advises only. You decide and you trade manually."
    ),
    "bullets": [
        "Composite score (0-100) is the headline ranking. 70+ is strong; 55-69 is okay; below 55 is weak.",
        "Confidence score (0-100) tells you how much to trust the ranking for that specific stock.",
        "Q / V / M / N bars are Quality, Valuation, Momentum, News. Each is 0-100 within this week's universe.",
        "Quality gates are hard filters. A failed gate makes the candidate ineligible regardless of score.",
        "Performance tab tracks the engine's suggestions vs the NIFTY 100 over 30, 60, 90, and 180 days.",
        "History tab shows past weekly runs and their outcomes.",
    ],
}


# Reverse map: group_name -> set of signal_names. Keep in sync with
# scoring_service.GROUP_SIGNALS.
_GROUP_TO_SIGNALS: dict[str, set[str]] = {
    "quality": {
        "return_on_equity",
        "return_on_assets",
        "operating_margin",
        "debt_to_equity",
    },
    "valuation": {
        "pe_ratio",
        "pb_ratio",
        "earnings_growth_yoy",
    },
    "momentum": {
        "return_3m",
        "return_6m",
        "dist_from_52w_high_pct",
    },
    "news": {
        "news_net_sentiment",
        "news_story_velocity",
        "news_story_count",
    },
}


# Helpers


def _to_float(v: Any) -> float | None:
    """Coerce Decimal128/Decimal/numeric to float; None on failure."""
    if v is None:
        return None
    try:
        if isinstance(v, Decimal128):
            return float(v.to_decimal())
        if isinstance(v, Decimal):
            return float(v)
        if isinstance(v, str):
            return float(v)
        return float(v)
    except (ValueError, TypeError):
        return None


def _format_raw(formatter_kind: str, raw: float | None) -> str:
    """Format a raw fundamental value for plain-English display."""
    if raw is None:
        return "n/a"
    if formatter_kind == "percent_decimal":
        # Stored as decimal (0.142 = 14.2%)
        return f"{raw * 100:.1f}%"
    if formatter_kind == "percent_already":
        # Stored as percent already (e.g. return_3m comes out as -3.4)
        return f"{raw:+.1f}%"
    if formatter_kind == "ratio":
        return f"{raw:.2f}"
    if formatter_kind == "multiple":
        return f"{raw:.1f}x"
    if formatter_kind == "currency_inr_cr":
        return f"Rs {raw / 1_00_00_000:,.0f} Cr"
    if formatter_kind == "score_only":
        return "—"  # Raw value not available post-run for news signals
    return f"{raw}"


def _interpret_score(score: float | None) -> str:
    """Map a 0-100 score to a band label."""
    if score is None:
        return "unknown"
    if score >= 70:
        return "strong"
    if score >= 50:
        return "ok"
    return "weak"


def _interpret_confidence(score: float | None) -> str:
    """Map a 0-100 confidence score to a band label."""
    if score is None:
        return "unknown"
    if score >= 90:
        return "high"
    if score >= 70:
        return "med"
    return "low"


def _build_signal_meta(
    signals: list[dict],
    fundamentals_doc: dict | None,
) -> list[dict]:
    """Per-signal display rows for the UI.

    Each row has: signal_name, display_name, short_description, what_higher_means,
    raw_value_formatted, normalized_score, weight, available, group.
    """
    out: list[dict] = []
    for sig in signals:
        signal_name = sig.get("signal_name", "")
        meta = SIGNAL_META.get(signal_name)
        if meta is None:
            # Unknown signal -- surface what we can
            out.append(
                {
                    "signal_name": signal_name,
                    "display_name": signal_name,
                    "short_description": "",
                    "what_higher_means": "",
                    "raw_value_formatted": "—",
                    "normalized_score": sig.get("normalized_score", 0.0),
                    "weight": sig.get("weight", 0.0),
                    "available": sig.get("available", False),
                    "group": "",
                }
            )
            continue

        # Find which group this signal belongs to
        group = ""
        for group_name, group_def in _GROUP_TO_SIGNALS.items():
            if signal_name in group_def:
                group = group_name
                break

        raw_formatted = "—"
        if meta.get("fundamentals_field") and fundamentals_doc:
            raw = _to_float(fundamentals_doc.get(meta["fundamentals_field"]))
            raw_formatted = _format_raw(meta["formatter_kind"], raw)
        elif meta.get("fundamentals_field") is None and sig.get("available"):
            # Computed signal (price-momentum or news). We don't have raw.
            # Show the normalized score as a hint, not the raw underlying value.
            raw_formatted = "—"

        out.append(
            {
                "signal_name": signal_name,
                "display_name": meta["display_name"],
                "short_description": meta["short_description"],
                "what_higher_means": meta["what_higher_means"],
                "raw_value_formatted": raw_formatted,
                "normalized_score": sig.get("normalized_score", 0.0),
                "weight": sig.get("weight", 0.0),
                "available": sig.get("available", False),
                "group": group,
            }
        )
    return out


def _build_group_meta(candidate: dict) -> dict[str, dict]:
    """Per-group interpretation for the four QVMN bars."""
    out: dict[str, dict] = {}
    for group_name, meta in GROUP_META.items():
        score = candidate.get(f"{group_name}_score")
        score_float = _to_float(score)
        band = _interpret_score(score_float)
        if band == "strong":
            interp = meta["interpretation_strong"]
        elif band == "ok":
            interp = meta["interpretation_ok"]
        else:
            interp = meta["interpretation_weak"]
        out[group_name] = {
            "display_name": meta["display_name"],
            "weight_pct": meta["weight_pct"],
            "what_it_measures": meta["what_it_measures"],
            "score": score_float,
            "band": band,
            "this_candidate_interpretation": interp,
        }
    return out


def _build_gate_meta(gates: list[dict]) -> list[dict]:
    """Per-gate plain-English summary."""
    out: list[dict] = []
    for g in gates:
        gate_name = g.get("gate_name", "")
        meta = GATE_META.get(gate_name)
        if meta is None:
            out.append(
                {
                    "gate_name": gate_name,
                    "display_name": gate_name,
                    "why_we_check": "",
                    "passed": g.get("passed", False),
                    "skipped": g.get("skipped", False),
                    "threshold": g.get("threshold", ""),
                    "actual_value": g.get("actual_value", ""),
                    "skip_reason": g.get("skip_reason", ""),
                    "plain_english": "",
                }
            )
            continue

        if g.get("skipped"):
            plain = f"Skipped: {g.get('skip_reason', 'data unavailable')}"
        elif g.get("passed"):
            plain = meta["plain_english_pass"]
        else:
            plain = meta["plain_english_fail"]

        out.append(
            {
                "gate_name": gate_name,
                "display_name": meta["display_name"],
                "why_we_check": meta["why_we_check"],
                "passed": g.get("passed", False),
                "skipped": g.get("skipped", False),
                "threshold": g.get("threshold", ""),
                "actual_value": g.get("actual_value", ""),
                "skip_reason": g.get("skip_reason", ""),
                "plain_english": plain,
            }
        )
    return out


def _build_confidence_meta(
    confidence_score: float | None,
    deductions: list[str],
) -> dict:
    """Confidence interpretation block."""
    band = _interpret_confidence(_to_float(confidence_score))
    if band == "high":
        interp = CONFIDENCE_META["interpretation_high"]
    elif band == "med":
        interp = CONFIDENCE_META["interpretation_med"]
    else:
        interp = CONFIDENCE_META["interpretation_low"]
    return {
        "score": _to_float(confidence_score),
        "band": band,
        "what_it_means": CONFIDENCE_META["what_it_means"],
        "this_candidate_interpretation": interp,
        "deduction_categories": CONFIDENCE_META["deduction_categories"],
        "deductions": deductions or [],
    }


def enrich_candidate(candidate: dict, fundamentals_doc: dict | None) -> dict:
    """Mutate a serialized candidate dict in-place with the *_meta fields."""
    candidate["signal_meta"] = _build_signal_meta(
        candidate.get("signals", []),
        fundamentals_doc,
    )
    candidate["group_meta"] = _build_group_meta(candidate)
    candidate["gate_meta"] = _build_gate_meta(candidate.get("gates", []))
    candidate["confidence_meta"] = _build_confidence_meta(
        candidate.get("confidence_score"),
        candidate.get("confidence_deductions", []),
    )
    return candidate


def enrich_run(run_dict: dict) -> dict:
    """Add explainability metadata to a serialized SuggestionRun dict.

    Fetches fundamentals once for the top-K ISINs. Mutates the dict in place
    (and returns it) so the router can do `return enrich_run(serialized)`.
    """
    top = run_dict.get("top_candidates", []) or []
    isins = [c.get("isin") for c in top if c.get("isin")]

    fundamentals_by_isin: dict[str, dict] = {}
    if isins:
        try:
            fundamentals_by_isin = get_fundamentals_bulk(isins)
        except Exception as exc:
            log.warning("enrich_run: failed to load fundamentals: %s", exc)
            fundamentals_by_isin = {}

    for c in top:
        isin = c.get("isin")
        f = fundamentals_by_isin.get(isin) if isin else None
        enrich_candidate(c, f)

    run_dict["feedback_meta"] = FEEDBACK_META
    run_dict["page_intro"] = PAGE_INTRO
    return run_dict
