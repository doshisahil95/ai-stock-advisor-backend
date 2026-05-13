"""Dossier generator -- Claude Sonnet produces a structured per-candidate brief.

Claude generates NARRATIVE only.
Numbers come from our data.
The prompt is explicit about not inventing facts.
We then validate the output JSON schema; on validation failure we retry once.
On second failure we mark narrative_unavailable and keep the structured signals.
"""

from __future__ import annotations

import json
import logging
from typing import Any

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

If the input data is insufficient to produce a confident bull or bear case, use phrases like "Limited data available on..." rather than inventing reasons.
"""


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


def _build_user_prompt(
    candidate: CandidateScore,
    fundamentals: dict | None,
    news_articles: list[dict],
    held_symbols_by_sector: dict[str, list[str]],
) -> str:
    """Assemble the full per-candidate prompt."""
    f = fundamentals or {}

    def _fmt_num(val: Any, suffix: str = "", div: float | None = None) -> str:
        if val is None:
            return "n/a"
        try:
            from bson import Decimal128
            from decimal import Decimal

            if isinstance(val, Decimal128):
                val = float(val.to_decimal())
            elif isinstance(val, Decimal):
                val = float(val)
            else:
                val = float(val)
            if div:
                val = val / div
            return f"{val:,.2f}{suffix}"
        except (ValueError, TypeError):
            return "n/a"

    def _fmt_pct(val: Any) -> str:
        if val is None:
            return "n/a"
        try:
            from bson import Decimal128
            from decimal import Decimal

            if isinstance(val, Decimal128):
                val = float(val.to_decimal())
            elif isinstance(val, Decimal):
                val = float(val)
            else:
                val = float(val)
            return f"{val * 100:.2f}%"
        except (ValueError, TypeError):
            return "n/a"

    parts = [
        f"## CANDIDATE: {candidate.symbol} ({candidate.name})",
        f"Sector: {candidate.sector or 'unknown'}",
        f"Composite Score: {candidate.composite_score:.1f}/100  Rank: #{candidate.rank}  Confidence: {candidate.confidence_score:.0f}/100",
        "",
        "## SCORE BREAKDOWN",
        f"- Quality:    {candidate.quality_score:.1f}/100",
        f"- Valuation:  {candidate.valuation_score:.1f}/100",
        f"- Momentum:   {candidate.momentum_score:.1f}/100",
        f"- News:       {candidate.news_score:.1f}/100",
        "",
        "## FUNDAMENTALS",
        f"- Market Cap:       INR {_fmt_num(f.get('market_cap'), ' Cr', div=1_00_00_000)}",
        f"- P/E (trailing):   {_fmt_num(f.get('pe_ratio'))}",
        f"- P/B:              {_fmt_num(f.get('pb_ratio'))}",
        f"- ROE:              {_fmt_pct(f.get('return_on_equity'))}",
        f"- ROA:              {_fmt_pct(f.get('return_on_assets'))}",
        f"- Operating Margin: {_fmt_pct(f.get('operating_margin'))}",
        f"- Debt/Equity:      {_fmt_num(f.get('debt_to_equity'))}",
        f"- Earnings Growth (YoY): {_fmt_pct(f.get('earnings_growth_yoy'))}",
        f"- Revenue Growth (YoY):  {_fmt_pct(f.get('revenue_growth_yoy'))}",
        f"- Dividend Yield:   {_fmt_pct(f.get('dividend_yield'))}",
        f"- Beta:             {_fmt_num(f.get('beta'))}",
        "",
        "## PRICE CONTEXT",
        f"- Current:          INR {_fmt_num(candidate.current_price)}",
        f"- 52-Week High:     INR {_fmt_num(f.get('fifty_two_week_high'))}",
        f"- 52-Week Low:      INR {_fmt_num(f.get('fifty_two_week_low'))}",
        "",
        "## RECENT NEWS (last 30d, classified)",
        _format_news_summaries(news_articles),
        "",
        "## USER'S CURRENT PORTFOLIO (sector exposure)",
        _format_portfolio_context(held_symbols_by_sector),
        "",
        "Now produce the JSON dossier per the schema in the system prompt.",
    ]
    return "\n".join(parts)


def _parse_dossier(raw_text: str) -> dict | None:
    """Extract and validate the dossier JSON from Claude's response."""
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

    required = [
        "plain_english_summary",
        "one_line_thesis",
        "bull_case",
        "bear_case",
        "key_risks",
        "valuation_verdict",
        "portfolio_fit",
    ]
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
    parsed["portfolio_fit"] = str(parsed["portfolio_fit"])[:300]
    return parsed


def _empty_dossier(reason: str) -> dict:
    """Fallback dossier for when narrative generation fails."""
    return {
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
        "portfolio_fit": "(unavailable)",
        "narrative_unavailable": True,
        "narrative_unavailable_reason": reason,
    }


def _generate_one(
    candidate: CandidateScore,
    fundamentals: dict | None,
    news_articles: list[dict],
    held_symbols_by_sector: dict[str, list[str]],
) -> dict:
    """Generate a single dossier. Always returns a dict (with fallback on failure)."""
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    user_prompt = _build_user_prompt(
        candidate,
        fundamentals,
        news_articles,
        held_symbols_by_sector,
    )

    for attempt in range(2):
        try:
            message = client.messages.create(
                model=settings.ANTHROPIC_MODEL_PRIMARY,
                max_tokens=2048,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except Exception as exc:
            log.error(
                "Dossier API call failed for %s (attempt %d): %s",
                candidate.symbol,
                attempt + 1,
                exc,
            )
            if attempt == 0:
                continue
            return _empty_dossier(f"api_error: {type(exc).__name__}")

        raw_text = ""
        for block in message.content:
            if hasattr(block, "text"):
                raw_text += block.text

        parsed = _parse_dossier(raw_text)
        if parsed:
            log.info("  Dossier OK for %s", candidate.symbol)
            parsed["model"] = settings.ANTHROPIC_MODEL_PRIMARY
            parsed["narrative_unavailable"] = False
            return parsed

        log.warning(
            "Dossier parse failed for %s on attempt %d", candidate.symbol, attempt + 1
        )

    return _empty_dossier("parse_failure")


def generate_dossiers_for_top_k(
    top_candidates: list[CandidateScore],
    fundamentals_by_isin: dict[str, dict],
) -> list[dict]:
    """Generate dossiers for the top-K candidates."""
    if not top_candidates:
        return []

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
        log.info("Generating dossier for #%d %s", c.rank, c.symbol)
        dossier = _generate_one(
            c,
            fundamentals_by_isin.get(c.isin),
            news,
            held_by_sector,
        )
        dossier["isin"] = c.isin
        dossier["symbol"] = c.symbol
        dossiers.append(dossier)
    return dossiers
