"""Dossier generator -- Claude Sonnet produces a structured per-candidate brief.

Claude generates NARRATIVE only.
Numbers come from our data.
The prompt is explicit about not inventing facts.
We then validate the output JSON schema; on validation failure we retry once.
On second failure we mark narrative_unavailable and keep the structured signals.

F2 (chunk 5): adds a sell-side prompt and direction-aware schema validation.
The frontend dossier parser is unchanged for buy-side. Sell-side dossiers
swap `portfolio_fit` for `tax_consideration` and `concentration_note`.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from bson import Decimal128

from app.config.settings import settings
from app.db.client import Collections
from app.models.suggestion import CandidateScore

log = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a financial analyst producing a one-page research dossier on a candidate stock for an Indian retail investor.

CRITICAL CONSTRAINTS:
1. You generate NARRATIVE ONLY. Do NOT invent numbers, percentages, or facts not in the input data.
2. You are NOT a broker. NEVER say buy or sell or recommend. You synthesize information; the user decides.
3. Tone is honest and slightly contrarian. If the data is ambiguous, say so. If the bull case is weak, say so. Do not pad.
4. Output ONLY valid JSON matching the requested schema. No prose outside the JSON.

OUTPUT SCHEMA -- return a single JSON object with these fields:
- plain_english_summary: a string, 2 to 3 sentences, max 500 characters, written in plain language for a NON-ANALYST. Tell the reader why the system surfaced this stock this week, what the main upside is, and what the main risk is. Do not use jargon. Do not say buy or sell. If signals are weak or missing, say so honestly.
- one_line_thesis: a string, max 150 characters, the analyst-tone one-line version of the same idea.
- bull_case: an array of EXACTLY 3 strings, each max 200 characters, each grounded in the input data
- bear_case: an array of EXACTLY 3 strings, each max 200 characters
- key_risks: an array of EXACTLY 3 strings, each max 150 characters
- valuation_verdict: a string, max 200 characters. Choose one label from these options and add a brief rationale: deep value, reasonable, fairly priced, premium, overpriced
- portfolio_fit: a string, max 250 characters, commenting on sector overlap with current holdings

If the input data is insufficient to produce a confident bull or bear case, use phrases like "Limited data available on..." rather than inventing reasons."""


# F2: sell-side prompt. Same JSON envelope as the buy prompt so the
# frontend parser is unchanged. Swaps `portfolio_fit` for
# `tax_consideration` and `concentration_note` so the sell narrative
# can speak directly to STCG/LTCG and portfolio weight -- both are
# decision-relevant facts unique to a stock the user already owns.
_SYSTEM_PROMPT_SELL = """You are a financial analyst producing a one-page profit-booking dossier on a stock the user CURRENTLY HOLDS in their Indian portfolio.

CRITICAL CONSTRAINTS:
1. You generate NARRATIVE ONLY. Do NOT invent numbers, percentages, or facts not in the input data.
2. You are NOT a broker. NEVER say buy or sell or recommend. You synthesize information; the user decides.
3. Tone is honest and slightly contrarian. If the data is ambiguous, say so. If the case for booking profit is weak, say so. Do not pad.
4. Output ONLY valid JSON matching the requested schema. No prose outside the JSON.
5. ALWAYS reference the user's specific position context (cost basis, current unrealized gain, holding period and the related tax treatment) when the data is provided. These are the facts that distinguish a sell-side dossier from a generic stock writeup.

OUTPUT SCHEMA -- return a single JSON object with these fields:
- plain_english_summary: a string, 2 to 3 sentences, max 500 characters, written in plain language for a NON-ANALYST. Tell the reader why the system surfaced this position for profit-booking consideration this week, including their current unrealized gain and tax window. Mention the main reason FOR considering trimming and the main reason AGAINST. Do not use jargon. Do not say buy or sell. If signals are weak or missing, say so honestly.
- one_line_thesis: a string, max 150 characters, the analyst-tone one-line version of the same idea.
- bull_case: an array of EXACTLY 3 strings, each max 200 characters. Reasons to CONTINUE HOLDING. Grounded in the input data.
- bear_case: an array of EXACTLY 3 strings, each max 200 characters. Reasons to CONSIDER TRIMMING the position. Grounded in the input data.
- key_risks: an array of EXACTLY 3 strings, each max 150 characters. Specific tail risks to be aware of regardless of the decision.
- valuation_verdict: a string, max 200 characters. Choose one label from these options and add a brief rationale: deep value, reasonable, fairly priced, premium, overpriced.
- tax_consideration: a string, max 250 characters. Plainly state whether the position is LTCG-eligible (held > 365 days) or STCG (held <= 365 days), the rough tax cost on a sale TODAY, and whether waiting for LTCG (if applicable) materially changes the math.
- concentration_note: a string, max 250 characters. State the position's weight in the portfolio and whether that weight is elevated (>10% in a single stock is meaningfully concentrated).

If any input field is missing, say so explicitly in the relevant field (e.g., "Holding period not available -- cannot give tax verdict.") rather than inventing values.
"""


def _to_float(val: Any) -> float | None:
    """Coerce Mongo/Decimal/Decimal128/str/numeric to float, or None."""
    if val is None:
        return None
    try:
        if isinstance(val, Decimal128):
            val = val.to_decimal()
        if isinstance(val, Decimal):
            return float(val)
        return float(val)
    except (ValueError, TypeError):
        return None


def _format_news_summaries(news_articles: list[dict]) -> str:
    if not news_articles:
        return "(no recent classified news)"
    lines = []
    for a in news_articles[:8]:
        sentiment = a.get("sentiment", "?")
        severity = a.get("severity", "?")
        themes = ", ".join(a.get("themes", []))
        title = a.get("title", "")[:120]
        summary = a.get("classifier_summary", "")[:200]
        lines.append(f"- [{sentiment}/{severity}/{themes}] {title} -- {summary}")
    return "\n".join(lines)


def _format_portfolio_context(held_symbols_by_sector: dict[str, list[str]]) -> str:
    if not held_symbols_by_sector:
        return "(no current holdings recorded)"
    lines = []
    for sector, symbols in sorted(held_symbols_by_sector.items()):
        sym_str = ", ".join(symbols)
        n = len(symbols)
        lines.append(f"- {sector}: {sym_str} ({n} positions)")
    return "\n".join(lines)


def _build_position_context_block(
    candidate: CandidateScore,
    holding: dict,
    portfolio_value: Any,
    next_earnings: Any,
) -> str:
    """F2: assemble the sell-side POSITION CONTEXT block.

    Pure string assembly. Called only when direction='sell' and the
    holding dict is non-None. Numbers are sourced from the holding
    doc plus the candidate's current_price (set by score_sell_candidates).
    """
    qty = _to_float(holding.get("quantity"))
    avg_cost = _to_float(holding.get("avg_cost"))
    invested = _to_float(holding.get("invested_amount"))
    target_price = _to_float(holding.get("target_price"))
    latest_close = _to_float(candidate.current_price)
    pv = _to_float(portfolio_value)

    # Unrealized gain %
    unrealized_gain_pct = None
    if (
        latest_close is not None
        and qty is not None
        and qty > 0
        and invested is not None
        and invested > 0
    ):
        current_value = latest_close * qty
        unrealized_gain_pct = (current_value - invested) / invested * 100

    # Tax window
    first_purchased = holding.get("first_purchased_at")
    tax_window = "(holding period unknown)"
    if first_purchased is not None:
        fp = first_purchased
        if hasattr(fp, "tzinfo") and fp.tzinfo is not None:
            fp = fp.replace(tzinfo=None)
        now_naive = datetime.utcnow()
        days_held = (now_naive - fp).total_seconds() / 86400.0
        if days_held > 365:
            tax_window = "LTCG-eligible (held > 365 days)"
        else:
            days_to_ltcg = int(365 - days_held)
            if days_to_ltcg <= 30:
                tax_window = f"near-LTCG ({days_to_ltcg} days to LTCG eligibility)"
            else:
                tax_window = f"STCG ({days_to_ltcg} days to LTCG eligibility)"

    # Portfolio weight %
    portfolio_weight_pct = None
    if (
        latest_close is not None
        and qty is not None
        and qty > 0
        and pv is not None
        and pv > 0
    ):
        portfolio_weight_pct = latest_close * qty / pv * 100

    # Next earnings
    next_earnings_str = "(no upcoming earnings event recorded)"
    if next_earnings is not None:
        ne = next_earnings
        if hasattr(ne, "tzinfo") and ne.tzinfo is not None:
            ne = ne.replace(tzinfo=None)
        days_to_earn = (ne - datetime.utcnow()).total_seconds() / 86400.0
        next_earnings_str = (
            f"{ne.date().isoformat()} ({days_to_earn:+.0f} days from now)"
        )

    lines = ["", "## POSITION CONTEXT (sell-side)"]
    lines.append(
        f"- Quantity held: {qty:,.4f}" if qty is not None else "- Quantity held: n/a"
    )
    lines.append(
        f"- Average cost per share: INR {avg_cost:,.2f}"
        if avg_cost is not None
        else "- Average cost per share: n/a"
    )
    lines.append(
        f"- Total invested amount: INR {invested:,.2f}"
        if invested is not None
        else "- Total invested amount: n/a"
    )
    lines.append(
        f"- Current price (latest close used by engine): INR {latest_close:,.2f}"
        if latest_close is not None
        else "- Current price: n/a"
    )
    lines.append(
        f"- Unrealized gain: {unrealized_gain_pct:+.2f}%"
        if unrealized_gain_pct is not None
        else "- Unrealized gain: n/a"
    )
    lines.append(
        f"- Target price set by user: INR {target_price:,.2f}"
        if target_price is not None
        else "- Target price set by user: not set"
    )
    lines.append(f"- Tax window: {tax_window}")
    lines.append(
        f"- Portfolio weight: {portfolio_weight_pct:.2f}% of total portfolio value"
        if portfolio_weight_pct is not None
        else "- Portfolio weight: n/a"
    )
    lines.append(f"- Next earnings event: {next_earnings_str}")
    return "\n".join(lines)


def _build_user_prompt(
    candidate: CandidateScore,
    fundamentals: dict | None,
    news_articles: list[dict],
    held_symbols_by_sector: dict[str, list[str]],
    direction: str = "buy",
    holding: dict | None = None,
    portfolio_value: Any = None,
    next_earnings: Any = None,
) -> str:
    """Assemble the full per-candidate prompt.

    F2 (chunk 5): for direction='sell', appends a 'POSITION CONTEXT'
    block with cost basis, current unrealized gain %, tax window
    (LTCG / STCG / days_to_ltcg), portfolio weight %, and next
    earnings date when available.
    """
    f = fundamentals or {}

    def _fmt_num(val: Any, suffix: str = "", div: float | None = None) -> str:
        v = _to_float(val)
        if v is None:
            return "n/a"
        if div:
            v = v / div
        return f"{v:,.2f}{suffix}"

    def _fmt_pct(val: Any) -> str:
        v = _to_float(val)
        if v is None:
            return "n/a"
        return f"{v * 100:.2f}%"

    parts = [
        f"## CANDIDATE: {candidate.symbol} ({candidate.name})",
        f"Sector: {candidate.sector or 'unknown'}",
        f"Composite Score: {candidate.composite_score:.1f}/100   Rank: #{candidate.rank}   Confidence: {candidate.confidence_score:.0f}/100",
        "",
        "## SCORE BREAKDOWN",
        f"- Quality: {candidate.quality_score:.1f}/100",
        f"- Valuation: {candidate.valuation_score:.1f}/100",
        f"- Momentum: {candidate.momentum_score:.1f}/100",
        f"- News: {candidate.news_score:.1f}/100",
        "",
        "## FUNDAMENTALS",
        f"- Market Cap: INR {_fmt_num(f.get('market_cap'), ' Cr', div=1_00_00_000)}",
        f"- P/E (trailing): {_fmt_num(f.get('pe_ratio'))}",
        f"- P/B: {_fmt_num(f.get('pb_ratio'))}",
        f"- ROE: {_fmt_pct(f.get('return_on_equity'))}",
        f"- ROA: {_fmt_pct(f.get('return_on_assets'))}",
        f"- Operating Margin: {_fmt_pct(f.get('operating_margin'))}",
        f"- Debt/Equity: {_fmt_num(f.get('debt_to_equity'))}",
        f"- Earnings Growth (YoY): {_fmt_pct(f.get('earnings_growth_yoy'))}",
        f"- Revenue Growth (YoY): {_fmt_pct(f.get('revenue_growth_yoy'))}",
        f"- Dividend Yield: {_fmt_pct(f.get('dividend_yield'))}",
        f"- Beta: {_fmt_num(f.get('beta'))}",
        "",
        "## PRICE CONTEXT",
        f"- Current: INR {_fmt_num(candidate.current_price)}",
        f"- 52-Week High: INR {_fmt_num(f.get('fifty_two_week_high'))}",
        f"- 52-Week Low: INR {_fmt_num(f.get('fifty_two_week_low'))}",
        "",
        "## RECENT NEWS (last 30d, classified)",
        _format_news_summaries(news_articles),
        "",
        "## USER'S CURRENT PORTFOLIO (sector exposure)",
        _format_portfolio_context(held_symbols_by_sector),
    ]

    prompt = "\n".join(parts)

    # F2: append sell-side position context BEFORE the closing instruction.
    if direction == "sell" and holding is not None:
        prompt += _build_position_context_block(
            candidate, holding, portfolio_value, next_earnings
        )

    prompt += "\n\nNow produce the JSON dossier per the schema in the system prompt."
    return prompt


def _parse_dossier(raw_text: str, direction: str = "buy") -> dict | None:
    """Extract and validate the dossier JSON from Claude's response.

    F2: required field set switches on direction.
      - buy:  …, valuation_verdict, portfolio_fit
      - sell: …, valuation_verdict, tax_consideration, concentration_note
    """
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < 0 or end <= start:
        return None

    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None

    common_required = [
        "plain_english_summary",
        "one_line_thesis",
        "bull_case",
        "bear_case",
        "key_risks",
        "valuation_verdict",
    ]
    if direction == "sell":
        required = common_required + ["tax_consideration", "concentration_note"]
    else:
        required = common_required + ["portfolio_fit"]

    for key in required:
        if key not in parsed:
            return None

    for key in ["bull_case", "bear_case", "key_risks"]:
        if not isinstance(parsed[key], list):
            return None
        while len(parsed[key]) < 3:
            parsed[key].append("(insufficient data)")
        parsed[key] = parsed[key][:3]
        parsed[key] = [str(x)[:300] for x in parsed[key]]

    parsed["plain_english_summary"] = str(parsed["plain_english_summary"])[:500]
    parsed["one_line_thesis"] = str(parsed["one_line_thesis"])[:200]
    parsed["valuation_verdict"] = str(parsed["valuation_verdict"])[:300]

    if direction == "sell":
        parsed["tax_consideration"] = str(parsed["tax_consideration"])[:300]
        parsed["concentration_note"] = str(parsed["concentration_note"])[:300]
    else:
        parsed["portfolio_fit"] = str(parsed["portfolio_fit"])[:300]

    return parsed


def _empty_dossier(reason: str, direction: str = "buy") -> dict:
    """Fallback dossier for when narrative generation fails.

    Returned shape depends on direction so the frontend can render the
    same fields it expects for a successful dossier of that direction.
    """
    base = {
        "plain_english_summary": "(narrative unavailable -- see signal scores and gates below for the data the engine used)",
        "one_line_thesis": "(narrative unavailable -- see signals)",
        "bull_case": [
            "(narrative unavailable)",
            "(narrative unavailable)",
            "(narrative unavailable)",
        ],
        "bear_case": [
            "(narrative unavailable)",
            "(narrative unavailable)",
            "(narrative unavailable)",
        ],
        "key_risks": [
            "(narrative unavailable)",
            "(narrative unavailable)",
            "(narrative unavailable)",
        ],
        "valuation_verdict": f"(unavailable: {reason})",
        "narrative_unavailable": True,
        "narrative_unavailable_reason": reason,
    }
    if direction == "sell":
        base["tax_consideration"] = "(unavailable)"
        base["concentration_note"] = "(unavailable)"
    else:
        base["portfolio_fit"] = "(unavailable)"
    return base


def _generate_one(
    candidate: CandidateScore,
    fundamentals: dict | None,
    news_articles: list[dict],
    held_symbols_by_sector: dict[str, list[str]],
    direction: str = "buy",
    holding: dict | None = None,
    portfolio_value: Any = None,
    next_earnings: Any = None,
) -> dict:
    """Generate a single dossier. Always returns a dict (with fallback on failure).

    F2: direction selects prompt + schema validation + empty-fallback shape.
    """
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    user_prompt = _build_user_prompt(
        candidate,
        fundamentals,
        news_articles,
        held_symbols_by_sector,
        direction=direction,
        holding=holding,
        portfolio_value=portfolio_value,
        next_earnings=next_earnings,
    )

    system_prompt = _SYSTEM_PROMPT_SELL if direction == "sell" else _SYSTEM_PROMPT

    for attempt in range(2):
        try:
            message = client.messages.create(
                model=settings.ANTHROPIC_MODEL_PRIMARY,
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except Exception as exc:
            log.error(
                "Dossier API call failed for %s (attempt %d, direction=%s): %s",
                candidate.symbol,
                attempt + 1,
                direction,
                exc,
            )
            if attempt == 0:
                continue
            return _empty_dossier(
                f"api_error: {type(exc).__name__}", direction=direction
            )

        raw_text = ""
        for block in message.content:
            if hasattr(block, "text"):
                raw_text += block.text

        parsed = _parse_dossier(raw_text, direction=direction)
        if parsed:
            log.info("  Dossier OK for %s (direction=%s)", candidate.symbol, direction)
            parsed["model"] = settings.ANTHROPIC_MODEL_PRIMARY
            parsed["narrative_unavailable"] = False
            return parsed

        log.warning(
            "Dossier parse failed for %s on attempt %d (direction=%s)",
            candidate.symbol,
            attempt + 1,
            direction,
        )

    return _empty_dossier("parse_failure", direction=direction)


def generate_dossiers_for_top_k(
    top_candidates: list[CandidateScore],
    fundamentals_by_isin: dict[str, dict],
    direction: str = "buy",
    holdings_by_isin: dict[str, dict] | None = None,
    portfolio_value: Any = None,
    next_earnings_by_isin: dict[str, datetime] | None = None,
) -> list[dict]:
    """Generate dossiers for the top-K candidates.

    F2 (chunk 5): when direction='sell', looks up per-candidate holding
    metadata + next earnings to enrich the prompt with cost basis,
    unrealized gain, tax window, portfolio weight, and earnings date.

    Args:
        top_candidates: ranked CandidateScore list (already filtered).
        fundamentals_by_isin: latest fundamentals per ISIN.
        direction: 'buy' (default, back-compat) or 'sell'.
        holdings_by_isin: required for sell-side -- holding doc per ISIN
            with quantity / avg_cost / invested_amount / first_purchased_at
            / target_price. Ignored for buy-side.
        portfolio_value: required for sell-side -- total portfolio value
            in INR for portfolio_weight_pct narrative. Ignored for buy-side.
        next_earnings_by_isin: optional for both -- next earnings date per
            ISIN. Used in the sell-side position context block.
    """
    if not top_candidates:
        return []

    holdings_lookup = holdings_by_isin or {}
    earnings_lookup = next_earnings_by_isin or {}

    held_by_sector: dict[str, list[str]] = {}
    for h in Collections.holdings().find(
        {"deleted_at": None},
        {"_id": 0, "symbol": 1, "sector": 1},
    ):
        sector = h.get("sector") or "Unknown"
        held_by_sector.setdefault(sector, []).append(h["symbol"])

    dossiers: list[dict] = []
    for c in top_candidates:
        news_cursor = (
            Collections.news_articles()
            .find(
                {
                    "entities_isins": c.isin,
                    "classified": True,
                },
                {
                    "_id": 0,
                    "title": 1,
                    "sentiment": 1,
                    "severity": 1,
                    "themes": 1,
                    "classifier_summary": 1,
                    "published_at": 1,
                    "fetched_at": 1,
                },
            )
            .sort("fetched_at", -1)
            .limit(8)
        )
        news = list(news_cursor)
        log.info(
            "Generating dossier for #%d %s (direction=%s)",
            c.rank,
            c.symbol,
            direction,
        )
        dossier = _generate_one(
            c,
            fundamentals_by_isin.get(c.isin),
            news,
            held_by_sector,
            direction=direction,
            holding=holdings_lookup.get(c.isin),
            portfolio_value=portfolio_value,
            next_earnings=earnings_lookup.get(c.isin),
        )
        dossier["isin"] = c.isin
        dossier["symbol"] = c.symbol
        dossier["direction"] = direction  # F2: mark on the dossier itself
        dossiers.append(dossier)
    return dossiers
