"""Conversation service (#27, Chat 6) — on-demand enrichment + ad-hoc chat.

Two layers, one module:

1. ENRICHMENT (Unit 2): `ensure_stock_context(isin)` guarantees the per-stock
   reference data the chat needs — identity, fundamentals, upcoming earnings,
   recent classified news — fetching on demand when missing or stale, via the
   existing cron-path services. Writes only Phase-2 reference collections; never
   Phase-1 portfolio data.

2. CHAT (Unit 3): `chat_about_holding(isin, ...)` (F3) and
   `chat_about_suggestions(...)` (F1) assemble read-only context, call Claude
   Sonnet for a structured {answer, intent} envelope (mirroring
   dossier_service._generate_one), and persist a Conversation.

Design / invariants:
- REUSES existing services verbatim — fundamentals_service, news_fetcher,
  news_classifier, instrument_service (enrichment); dossier_service helpers,
  suggestion_engine, price_service (chat). No parallel LLM client, no parallel
  fetch/persist logic.
- The chat answer carries the SAME hard constraint as the dossier prompt:
  narrative only, never say buy/sell, never invent numbers. For a not-yet-owned
  stock it takes a buy-research framing (fundamentals + classified news +
  valuation); for a held stock it additionally gets the position/tax overlay.
- Chat is read-only on the user's PORTFOLIO. Enrichment may refresh shared
  market reference data (fundamentals/earnings/news) on demand — the same
  collections the weekly cron writes — which is not a Phase-1 write.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta
from decimal import Decimal

from app.config.settings import settings
from app.db.client import Collections
from app.models._common import utcnow
from app.models.conversation import Conversation
from app.services import (
    fundamentals_service,
    instrument_service,
    news_classifier,
    news_fetcher,
)
from app.services.dossier_service import _format_news_summaries, _to_float
from app.services.price_service import bulk_get_latest_prices
from app.services.suggestion_engine import (
    compute_portfolio_value,
    get_active_holdings_full,
    get_latest_run,
)
from app.services.tavily_client import TavilyQuotaExceeded

log = logging.getLogger(__name__)

# ── Enrichment tunables (Unit 2) ─────────────────────────────────────────────
# Fundamentals are considered fresh within this window (mirror the scoring
# engine's fundamentals_service.DEFAULT_FRESHNESS_DAYS = 14).
FUNDAMENTALS_MAX_AGE_DAYS = 14
# News surfaced to the model: same 30d window the buy dossier uses.
NEWS_LOOKBACK_DAYS = 30
# Don't re-hit Tavily if we already pulled this name within this window. A
# recently-attempted fetch (even one that produced nothing) counts, so we don't
# burn quota re-fetching the same stock every chat turn.
NEWS_REFETCH_AFTER_DAYS = 7
# Cap on classified articles fed into the prompt (mirror the dossier's limit).
NEWS_DISPLAY_LIMIT = 8
# Earnings calendar: if we refreshed (any outcome) within this window, trust it
# rather than re-querying yfinance every turn for names with no upcoming event.
EARNINGS_REFRESH_AFTER_DAYS = 14

# ── Chat tunables (Unit 3) ───────────────────────────────────────────────────
_CHAT_MAX_TOKENS = 1500
# Claude Sonnet 4.5 list price (USD per million tokens) as of this writing.
# Kept as operational constants in code (same convention as notify.py limits);
# used only to populate Conversation.cost_usd for cost review.
_SONNET_USD_PER_MTOK_INPUT = Decimal("3")
_SONNET_USD_PER_MTOK_OUTPUT = Decimal("15")
# Top candidates per direction fed into the F1 suggestions context.
_SUGGESTIONS_TOP_N = 10

_VALID_INTENTS = {
    "should_i_buy",
    "should_i_sell",
    "price_target_request",
    "allocation_request",
    "news_question",
    "general_market",
    "thesis_check",
    "educational",
    "other",
}

_NEWS_PROJECTION = {
    "_id": 1,
    "title": 1,
    "url": 1,
    "source": 1,
    "summary": 1,
    "published_at": 1,
    "fetched_at": 1,
    "sentiment": 1,
    "sentiment_confidence": 1,
    "themes": 1,
    "severity": 1,
    "classifier_summary": 1,
}

_SYSTEM_PROMPT_CHAT = """You are a financial research assistant for a single Indian retail investor researching NSE-listed stocks. You answer ad-hoc questions grounded ONLY in the data provided in the user message.

CRITICAL CONSTRAINTS:
1. NARRATIVE ONLY. Do NOT invent numbers, percentages, or facts not present in the input data. If a data point is missing, say so plainly (e.g. "Limited classified news is on file for this name") rather than guessing.
2. You are NOT a broker. NEVER explicitly say "buy", "sell", or "I recommend". You synthesize the available evidence -- fundamentals, recent classified news, valuation, and (when provided) the user's position and tax context -- and let the user decide. You may lay out the bull case, the bear case, valuation, risks, and what to watch.
3. Tone is honest, concise, and slightly contrarian. If the bull case is weak, say so. If the data is ambiguous, say so. Do not pad.
4. If the user provides a sentiment overlay (cautious / neutral / aggressive), adjust your emphasis accordingly WITHOUT changing the underlying facts.
5. Output ONLY a single valid JSON object, no prose outside it, with exactly these fields:
   - "answer": a string of readable markdown for a non-analyst. Typically 2 to 6 short paragraphs or bullet points. This is your full response to the user's question.
   - "intent": a single string classifying the user's question. Choose exactly one of: should_i_buy, should_i_sell, price_target_request, allocation_request, news_question, general_market, thesis_check, educational, other.
"""


# ── Identity ────────────────────────────────────────────────────────────────
def _resolve_identity(isin: str) -> dict | None:
    """ISIN -> {isin, symbol, name, exchange} from the instruments master.

    None if the ISIN is not a known NSE instrument (caller returns 404). We do
    NOT attempt a yfinance rescue: the master holds the full NSE equity list, so
    a miss almost always means a bad ISIN rather than a real gap, and yfinance is
    symbol-keyed (it cannot resolve from an ISIN alone).
    """
    instr = instrument_service.lookup_by_isin(isin)
    if not instr:
        return None
    return {
        "isin": isin,
        "symbol": instr.get("symbol", ""),
        "name": instr.get("name", ""),
        "exchange": instr.get("exchange", "NSE"),
    }


# ── Fundamentals ────────────────────────────────────────────────────────────
def _ensure_fundamentals(identity: dict) -> tuple[dict | None, str]:
    """Return (fundamentals_doc_or_None, status: fresh|refreshed|stale|unavailable)."""
    isin = identity["isin"]
    existing = fundamentals_service.get_latest_for_isin(isin)
    if fundamentals_service.is_fresh(existing, FUNDAMENTALS_MAX_AGE_DAYS):
        return existing, "fresh"

    refreshed = fundamentals_service.refresh_one(
        isin, identity["symbol"], identity["exchange"]
    )
    if refreshed is None:
        return existing, ("stale" if existing else "unavailable")

    # Re-read so downstream sees the canonical persisted (Decimal128) shape.
    return fundamentals_service.get_latest_for_isin(isin), "refreshed"


# ── Earnings ────────────────────────────────────────────────────────────────
def _earnings_recently_refreshed(isin: str) -> bool:
    cutoff = utcnow() - timedelta(days=EARNINGS_REFRESH_AFTER_DAYS)
    return (
        Collections.earnings_calendar().find_one(
            {"isin": isin, "fetched_at": {"$gte": cutoff}}, {"_id": 1}
        )
        is not None
    )


def _ensure_earnings(identity: dict) -> tuple[datetime | None, str]:
    """Return (next_earnings_date_or_None, status: on_file|none_upcoming|refreshed|refresh_failed)."""
    isin = identity["isin"]
    nxt = fundamentals_service.get_next_earnings_for_isin(isin)
    if nxt is not None:
        return nxt, "on_file"
    if _earnings_recently_refreshed(isin):
        return None, "none_upcoming"

    try:
        fundamentals_service.refresh_earnings_for(
            isin, identity["symbol"], identity["exchange"]
        )
    except Exception as exc:  # yfinance hiccup — non-fatal for a chat turn
        log.warning("earnings refresh failed for %s: %s", isin, exc)
        return None, "refresh_failed"

    return fundamentals_service.get_next_earnings_for_isin(isin), "refreshed"


# ── News ────────────────────────────────────────────────────────────────────
def _classified_news(isin: str) -> list[dict]:
    cutoff = utcnow() - timedelta(days=NEWS_LOOKBACK_DAYS)
    cursor = (
        Collections.news_articles()
        .find(
            {
                "entities_isins": isin,
                "classified": True,
                "fetched_at": {"$gte": cutoff},
            },
            _NEWS_PROJECTION,
        )
        .sort("fetched_at", -1)
        .limit(NEWS_DISPLAY_LIMIT)
    )
    return list(cursor)


def _news_recently_fetched(isin: str) -> bool:
    cutoff = utcnow() - timedelta(days=NEWS_REFETCH_AFTER_DAYS)
    return (
        Collections.news_articles().find_one(
            {"entities_isins": isin, "fetched_at": {"$gte": cutoff}}, {"_id": 1}
        )
        is not None
    )


def _ensure_news(identity: dict) -> tuple[list[dict], str]:
    """Return (classified_news_list, status: cached|fetched|quota_exceeded|fetch_failed)."""
    isin = identity["isin"]
    if _news_recently_fetched(isin):
        return _classified_news(isin), "cached"

    try:
        news_fetcher.fetch_for_instrument(isin, identity["symbol"], identity["name"])
    except TavilyQuotaExceeded:
        log.warning("Tavily quota exceeded; serving cached news for %s", isin)
        return _classified_news(isin), "quota_exceeded"
    except Exception as exc:
        log.warning("news fetch failed for %s: %s", isin, exc)
        return _classified_news(isin), "fetch_failed"

    # Classify just the freshly-fetched articles for this ISIN.
    try:
        news_classifier.classify_unclassified(isin_filter=[isin], only_recent_days=35)
    except Exception as exc:
        log.warning("news classify failed for %s: %s", isin, exc)

    return _classified_news(isin), "fetched"


# ── Enrichment orchestrator (Unit 2) ─────────────────────────────────────────
def ensure_stock_context(isin: str) -> dict:
    """Ensure + return read-mostly market context for one ISIN.

    Returns {"isin", "resolved": False} when the ISIN is not a known instrument.
    Otherwise returns identity + fundamentals + earnings + classified news, each
    with a status flag so the caller (and tests) can see whether data was served
    warm or fetched on demand.
    """
    code = isin.upper()
    identity = _resolve_identity(code)
    if identity is None:
        return {"isin": code, "resolved": False}

    fundamentals, f_status = _ensure_fundamentals(identity)
    next_earnings, e_status = _ensure_earnings(identity)
    news, n_status = _ensure_news(identity)

    # sector / industry live on the fundamentals doc, not the instruments master.
    if fundamentals:
        identity["sector"] = fundamentals.get("sector", "") or ""
        identity["industry"] = fundamentals.get("industry", "") or ""

    return {
        "resolved": True,
        **identity,
        "fundamentals": fundamentals,
        "fundamentals_status": f_status,
        "next_earnings": next_earnings,
        "earnings_status": e_status,
        "news": news,
        "news_status": n_status,
    }


# ── Prompt formatting (Unit 3) ───────────────────────────────────────────────
# Module-level mirrors of the closures inside dossier_service._build_user_prompt
# (which are not importable). Same formatting so the model sees consistent data.
def _fmt_num(val, suffix: str = "", div: float | None = None) -> str:
    v = _to_float(val)
    if v is None:
        return "n/a"
    if div:
        v = v / div
    return f"{v:,.2f}{suffix}"


def _fmt_pct(val) -> str:
    v = _to_float(val)
    if v is None:
        return "n/a"
    return f"{v * 100:.2f}%"


def _format_fundamentals_block(f: dict) -> str:
    return "\n".join(
        [
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
        ]
    )


def _format_position_block(
    holding: dict, current_price, portfolio_value, next_earnings
) -> str:
    """Held-position overlay for F3 (mirrors dossier_service._build_position_context_block
    semantics: LTCG > 365 days, near-LTCG within 30 days, weight = close*qty/PV).

    Reimplemented here (not imported) because the dossier helper is coupled to a
    CandidateScore object that the chat path does not construct.
    """
    qty = _to_float(holding.get("quantity"))
    avg_cost = _to_float(holding.get("avg_cost"))
    invested = _to_float(holding.get("invested_amount"))
    target_price = _to_float(holding.get("target_price"))
    latest_close = _to_float(current_price)
    pv = _to_float(portfolio_value)

    unrealized_gain_pct = None
    if (
        latest_close is not None
        and qty is not None
        and qty > 0
        and invested is not None
        and invested > 0
    ):
        unrealized_gain_pct = (latest_close * qty - invested) / invested * 100

    first_purchased = holding.get("first_purchased_at")
    tax_window = "(holding period unknown)"
    if first_purchased is not None:
        fp = first_purchased
        if hasattr(fp, "tzinfo") and fp.tzinfo is not None:
            fp = fp.replace(tzinfo=None)
        days_held = (datetime.utcnow() - fp).total_seconds() / 86400.0
        if days_held > 365:
            tax_window = "LTCG-eligible (held > 365 days)"
        else:
            days_to_ltcg = int(365 - days_held)
            if days_to_ltcg <= 30:
                tax_window = f"near-LTCG ({days_to_ltcg} days to LTCG eligibility)"
            else:
                tax_window = f"STCG ({days_to_ltcg} days to LTCG eligibility)"

    portfolio_weight_pct = None
    if (
        latest_close is not None
        and qty is not None
        and qty > 0
        and pv is not None
        and pv > 0
    ):
        portfolio_weight_pct = latest_close * qty / pv * 100

    next_earnings_str = "(no upcoming earnings event recorded)"
    if next_earnings is not None:
        ne = next_earnings
        if hasattr(ne, "tzinfo") and ne.tzinfo is not None:
            ne = ne.replace(tzinfo=None)
        days_to_earn = (ne - datetime.utcnow()).total_seconds() / 86400.0
        next_earnings_str = (
            f"{ne.date().isoformat()} ({days_to_earn:+.0f} days from now)"
        )

    lines = ["", "## POSITION CONTEXT (user currently holds this)"]
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
        f"- Current price: INR {latest_close:,.2f}"
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


def _build_holding_prompt(
    ctx: dict, overlay: dict | None, query: str, sentiment
) -> str:
    f = ctx.get("fundamentals") or {}
    held = overlay is not None

    current_price = None
    if overlay and overlay.get("current_price") is not None:
        current_price = _to_float(overlay["current_price"])
    if current_price is None:
        current_price = _to_float(f.get("current_price"))

    parts = [
        f"## STOCK: {ctx.get('symbol')} ({ctx.get('name')})",
        f"Sector: {ctx.get('sector') or 'unknown'}",
        f"Currently held by user: {'yes' if held else 'no (research / not-yet-owned)'}",
        "",
        "## FUNDAMENTALS",
        _format_fundamentals_block(f),
        "",
        "## PRICE CONTEXT",
        f"- Current: INR {current_price:,.2f}"
        if current_price is not None
        else "- Current: n/a",
        f"- 52-Week High: INR {_fmt_num(f.get('fifty_two_week_high'))}",
        f"- 52-Week Low: INR {_fmt_num(f.get('fifty_two_week_low'))}",
        "",
        "## RECENT NEWS (last 30d, classified)",
        _format_news_summaries(ctx.get("news") or []),
    ]

    if held:
        parts.append(
            _format_position_block(
                overlay["holding"],
                overlay.get("current_price"),
                overlay.get("portfolio_value"),
                ctx.get("next_earnings"),
            )
        )
    else:
        # Buy-research framing: a not-yet-owned stock is being researched to buy.
        parts += [
            "",
            "## CONTEXT NOTE",
            "The user does NOT currently hold this stock; they are researching it "
            "(typically with a view to a potential purchase). Frame the analysis as "
            "a buy-side research synthesis: bull case, bear case, valuation, and key "
            "risks grounded in the data above. Do not say buy or sell.",
        ]

    if sentiment:
        parts += [
            "",
            "## USER SENTIMENT OVERLAY",
            f"The user says they are feeling {sentiment} about this decision. "
            "Adjust emphasis accordingly without changing the facts.",
        ]

    parts += [
        "",
        "## USER QUESTION",
        query,
        "",
        "Now answer per the JSON schema in the system prompt.",
    ]
    return "\n".join(parts)


def _build_suggestions_context() -> tuple[str, list[str]]:
    """Read-only summary of the latest buy + sell runs (F1). Returns (text, cited_isins)."""
    blocks: list[str] = []
    cited: list[str] = []
    for direction in ("buy", "sell"):
        run = get_latest_run(direction)
        if not run:
            continue
        top = run.get("top_candidates") or []
        if not top:
            continue

        thesis_by_isin: dict[str, str] = {}
        notes = run.get("notes")
        if notes:
            try:
                for d in json.loads(notes).get("dossiers", []):
                    if d.get("isin"):
                        thesis_by_isin[d["isin"]] = d.get("one_line_thesis", "")
            except (json.JSONDecodeError, TypeError):
                pass

        run_label = run.get("run_date_ist") or "recent"
        blocks.append(f"## LATEST {direction.upper()} SUGGESTIONS (run {run_label})")
        for c in top[:_SUGGESTIONS_TOP_N]:
            isin = c.get("isin")
            if isin:
                cited.append(isin)
            comp = _to_float(c.get("composite_score"))
            conf = _to_float(c.get("confidence_score"))
            comp_s = f"{comp:.1f}" if comp is not None else "n/a"
            conf_s = f"{conf:.0f}" if conf is not None else "n/a"
            line = (
                f"- #{c.get('rank', '?')} {c.get('symbol', '?')} ({c.get('name', '')}) "
                f"composite={comp_s} confidence={conf_s}"
            )
            thesis = thesis_by_isin.get(isin or "", "")
            if thesis:
                line += f" -- {thesis}"
            blocks.append(line)
        blocks.append("")

    if not blocks:
        return "(no suggestion runs are on file yet)", []
    return "\n".join(blocks).strip(), cited


def _build_suggestions_prompt(context_text: str, query: str, sentiment) -> str:
    parts = [
        "The user is asking about the latest weekly stock suggestions produced by "
        "the engine. Use ONLY the run data below; do not invent additional names "
        "or numbers.",
        "",
        context_text,
    ]
    if sentiment:
        parts += [
            "",
            "## USER SENTIMENT OVERLAY",
            f"The user says they are feeling {sentiment}. Adjust emphasis "
            "accordingly without changing the facts.",
        ]
    parts += [
        "",
        "## USER QUESTION",
        query,
        "",
        "Now answer per the JSON schema in the system prompt.",
    ]
    return "\n".join(parts)


# ── LLM call + parse (Unit 3) ────────────────────────────────────────────────
def _parse_chat(raw_text: str) -> dict | None:
    """Extract {answer, intent} from the model output. Mirrors the fence-strip +
    brace-slice approach in dossier_service._parse_dossier."""
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

    answer = parsed.get("answer")
    if not answer or not isinstance(answer, str):
        return None
    intent = parsed.get("intent", "other")
    if intent not in _VALID_INTENTS:
        intent = "other"
    return {"answer": answer.strip(), "intent": intent}


def _call_sonnet(system_prompt: str, user_prompt: str) -> tuple[dict, int, int, str]:
    """Single structured Sonnet call. Returns (result, input_tokens, output_tokens,
    model_used). result always has {answer, intent} (graceful fallback on failure).
    Mirrors dossier_service._generate_one wiring."""
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    last_message = None
    for attempt in range(2):
        try:
            message = client.messages.create(
                model=settings.ANTHROPIC_MODEL_PRIMARY,
                max_tokens=_CHAT_MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except Exception as exc:
            log.error("Chat API call failed (attempt %d): %s", attempt + 1, exc)
            if attempt == 0:
                continue
            return (
                {
                    "answer": "(Chat is temporarily unavailable -- the model call "
                    "failed. Please try again shortly.)",
                    "intent": "other",
                },
                0,
                0,
                settings.ANTHROPIC_MODEL_PRIMARY,
            )

        last_message = message
        raw = "".join(b.text for b in message.content if hasattr(b, "text"))
        in_tok = getattr(message.usage, "input_tokens", 0) or 0
        out_tok = getattr(message.usage, "output_tokens", 0) or 0
        parsed = _parse_chat(raw)
        if parsed:
            return parsed, in_tok, out_tok, settings.ANTHROPIC_MODEL_PRIMARY
        log.warning("Chat parse failed on attempt %d", attempt + 1)

    in_tok = getattr(last_message.usage, "input_tokens", 0) if last_message else 0
    out_tok = getattr(last_message.usage, "output_tokens", 0) if last_message else 0
    return (
        {
            "answer": "(Could not produce a structured answer for that question. "
            "Please try rephrasing.)",
            "intent": "other",
        },
        in_tok or 0,
        out_tok or 0,
        settings.ANTHROPIC_MODEL_PRIMARY,
    )


def _compute_cost(input_tokens: int, output_tokens: int) -> Decimal:
    return (
        Decimal(input_tokens) / Decimal(1_000_000) * _SONNET_USD_PER_MTOK_INPUT
        + Decimal(output_tokens) / Decimal(1_000_000) * _SONNET_USD_PER_MTOK_OUTPUT
    )


# ── Persistence (Unit 3) ─────────────────────────────────────────────────────
def _persist_conversation(
    *,
    scope: str,
    query: str,
    result: dict,
    sentiment,
    related_isins: list[str],
    holding_id,
    cited_news_ids: list,
    input_tokens: int,
    output_tokens: int,
    model_used: str,
    duration_ms: int,
) -> dict:
    """Insert a Conversation and return the persisted Mongo doc (re-read), so the
    router serializes POST responses and GET /history rows through one path."""
    conv = Conversation(
        query=query,
        response=result["answer"],
        intent=result["intent"],
        scope=scope,
        sentiment_overlay=sentiment,
        related_entities_isins=related_isins,
        related_holding_id=holding_id,
        cited_news_ids=cited_news_ids,
        model_used=model_used,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=_compute_cost(input_tokens, output_tokens),
        duration_ms=duration_ms,
    )
    inserted = Collections.conversations().insert_one(conv.to_mongo())
    return Collections.conversations().find_one({"_id": inserted.inserted_id})


# ── Held overlay (Unit 3) ────────────────────────────────────────────────────
def _held_overlay(isin: str) -> dict | None:
    """If the ISIN is an active holding, return its doc + current price + total
    portfolio value (for the position/tax overlay). None if not held."""
    holding = Collections.holdings().find_one({"isin": isin, "deleted_at": None})
    if not holding:
        return None
    current_price = (bulk_get_latest_prices([isin]).get(isin) or {}).get("close")
    holdings_full = get_active_holdings_full()
    all_prices = bulk_get_latest_prices([h["isin"] for h in holdings_full])
    portfolio_value = compute_portfolio_value(holdings_full, all_prices)
    return {
        "holding": holding,
        "current_price": current_price,
        "portfolio_value": portfolio_value,
    }


# ── Chat orchestrators (Unit 3) ──────────────────────────────────────────────
def chat_about_holding(isin: str, query: str, sentiment=None) -> dict | None:
    """F3: chat about a specific stock (held or researched not-yet-owned).

    Returns the persisted conversation doc, or None if the ISIN is not a known
    NSE instrument (router -> 404)."""
    started = time.monotonic()
    code = isin.upper()
    ctx = ensure_stock_context(code)
    if not ctx.get("resolved"):
        return None

    overlay = _held_overlay(code)
    user_prompt = _build_holding_prompt(ctx, overlay, query, sentiment)
    result, in_tok, out_tok, model_used = _call_sonnet(_SYSTEM_PROMPT_CHAT, user_prompt)
    duration_ms = int((time.monotonic() - started) * 1000)

    return _persist_conversation(
        scope="holding",
        query=query,
        result=result,
        sentiment=sentiment,
        related_isins=[code],
        holding_id=(overlay["holding"]["_id"] if overlay else None),
        cited_news_ids=[a["_id"] for a in (ctx.get("news") or []) if a.get("_id")],
        input_tokens=in_tok,
        output_tokens=out_tok,
        model_used=model_used,
        duration_ms=duration_ms,
    )


def chat_about_suggestions(query: str, sentiment=None) -> dict:
    """F1: chat about the latest weekly suggestion runs. Returns the persisted
    conversation doc."""
    started = time.monotonic()
    context_text, cited_isins = _build_suggestions_context()
    user_prompt = _build_suggestions_prompt(context_text, query, sentiment)
    result, in_tok, out_tok, model_used = _call_sonnet(_SYSTEM_PROMPT_CHAT, user_prompt)
    duration_ms = int((time.monotonic() - started) * 1000)

    return _persist_conversation(
        scope="suggestions",
        query=query,
        result=result,
        sentiment=sentiment,
        related_isins=cited_isins,
        holding_id=None,
        cited_news_ids=[],
        input_tokens=in_tok,
        output_tokens=out_tok,
        model_used=model_used,
        duration_ms=duration_ms,
    )
