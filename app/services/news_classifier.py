"""Claude Haiku classifier for news articles.

Three-phase classification (as of #50):
  1. Main pass: large batches (BATCH_SIZE=25) — sentiment/severity/themes.
  2. Retry pass: stragglers in tiny batches (RETRY_PASS_BATCH_SIZE=3).
  3. Entity-confirmation pass (confirm_entities_llm): for articles where the
     rule-gate (_article_mentions_company in news_fetcher) was uncertain or
     left ISINs unconfirmed, ask Haiku per (article, company) pair whether the
     article is actually about that company. Additive: only adds ISINs back into
     entities_isins (never removes); runs after phases 1+2.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from bson import ObjectId

from app.config.settings import settings
from app.db.client import Collections
from app.models._common import utcnow

log = logging.getLogger(__name__)


BATCH_SIZE = 25
RETRY_PASS_BATCH_SIZE = 3

_VALID_SENTIMENTS = {"positive", "negative", "neutral"}
_VALID_SEVERITIES = {"high", "medium", "low"}
_VALID_THEMES = {
    "earnings",
    "regulatory",
    "corporate_action",
    "management_commentary",
    "sector_macro",
    "noise",
}


_SYSTEM_PROMPT = """You are a financial news classifier for an Indian stock advisor system.

For each article, output a JSON object with these EXACT fields:
- id: the article's id (echo back, do not modify)
- sentiment: "positive" or "negative" or "neutral" (impact on the company's stock price, NOT general tone)
- sentiment_confidence: 0.0-1.0 (your confidence in the sentiment label)
- themes: array of strings, choose from earnings, regulatory, corporate_action, management_commentary, sector_macro, noise. Multiple allowed. Use noise for low-information stories.
- severity: "high" or "medium" or "low" (how materially this story would influence a buy/sell decision)
- summary: ONE sentence (max 25 words) capturing the essential fact. Be neutral, factual.

Output a single JSON array, one object per article, in input order. No prose outside the array.

Sentiment guidance for stocks:
- Earnings beat, regulatory approval, new contract, management upgrade = positive
- Earnings miss, regulatory action, fraud, debt issues, management downgrade = negative
- Pure announcement (board meeting scheduled, dividend record date) = neutral
- Generic market recap not specific to this company = neutral

Be ruthless about the noise theme. If the article does not move a thoughtful buy/sell decision, it is noise.
"""


def _build_user_prompt(articles: list[dict]) -> str:
    lines = [
        "Classify these articles. Return one JSON object per article in a single array.\n"
    ]
    for a in articles:
        lines.append(
            "---\n"
            "id: " + str(a["_id"]) + "\n"
            "company_context: " + ", ".join(a.get("entities_symbols", [])) + "\n"
            "title: " + (a.get("title", "") or "") + "\n"
            "summary: " + (a.get("summary", "") or "")[:500] + "\n"
        )
    return "\n".join(lines)


def _parse_response(raw_text: str) -> list[dict] | None:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    start = text.find("[")
    end = text.rfind("]")
    if start < 0 or end < 0 or end <= start:
        log.warning("No JSON array found in classifier response")
        return None

    try:
        parsed = json.loads(text[start : end + 1])
        if not isinstance(parsed, list):
            log.warning("Classifier output is not a list")
            return None
        return parsed
    except json.JSONDecodeError as exc:
        log.warning("Classifier JSON parse failed: %s", exc)
        return None


def _validate_classification(c: dict, expected_id: str) -> dict | None:
    """Validate one LLM-returned classification.

    F27 fix (Chat 5.5+): caller no longer pre-merges id into the dict before
    calling, so the strict id-match check below actually fires — if the LLM
    returned the wrong id (hallucinated, mis-ordered) we drop the item and
    the retry pass will re-classify the article in a tiny batch.
    """
    if str(c.get("id", "")) != expected_id:
        return None

    sentiment = c.get("sentiment", "").lower().strip()
    if sentiment not in _VALID_SENTIMENTS:
        sentiment = "neutral"

    try:
        confidence = float(c.get("sentiment_confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))
    except (ValueError, TypeError):
        confidence = 0.5

    themes_raw = c.get("themes", [])
    if not isinstance(themes_raw, list):
        themes_raw = []
    themes = [t for t in themes_raw if isinstance(t, str) and t in _VALID_THEMES]
    if not themes:
        themes = ["noise"]

    severity = c.get("severity", "").lower().strip()
    if severity not in _VALID_SEVERITIES:
        severity = "low"

    summary = (c.get("summary", "") or "").strip()
    if len(summary) > 300:
        summary = summary[:297] + "..."

    return {
        "sentiment": sentiment,
        "sentiment_confidence": confidence,
        "themes": themes,
        "severity": severity,
        "classifier_summary": summary,
    }


def _classify_batch(articles: list[dict]) -> dict[str, dict]:
    """Send one batch to Anthropic. Returns dict of article_id_str -> classification."""
    if not articles:
        return {}

    from anthropic import Anthropic

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    user_prompt = _build_user_prompt(articles)

    try:
        message = client.messages.create(
            model=settings.ANTHROPIC_MODEL_FAST,
            max_tokens=4096,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as exc:
        log.error("Anthropic batch call failed: %s", exc)
        return {}

    raw_text = ""
    for block in message.content:
        if hasattr(block, "text"):
            raw_text += block.text

    parsed = _parse_response(raw_text)
    if parsed is None:
        log.info("Retrying batch with stricter prompt")
        try:
            message = client.messages.create(
                model=settings.ANTHROPIC_MODEL_FAST,
                max_tokens=4096,
                system=_SYSTEM_PROMPT
                + "\n\nIMPORTANT: Output ONLY the JSON array. No prose, no markdown fences, nothing else.",
                messages=[{"role": "user", "content": user_prompt}],
            )
            raw_text = ""
            for block in message.content:
                if hasattr(block, "text"):
                    raw_text += block.text
            parsed = _parse_response(raw_text)
        except Exception as exc:
            log.error("Anthropic retry call failed: %s", exc)
            return {}

    if parsed is None:
        log.error("Classifier returned unparseable output after retry")
        return {}

        # F27 fix (Chat 5.5+): drop the positional fallback and stop pre-merging
    # the id before validation. Pre-fix:
    #   - If LLM omitted 'id', we used article_ids_in_order[i] (positional).
    #     But the LLM is only best-effort about preserving input order, so a
    #     reorder/insert/omit by the model silently assigned one article's
    #     classification to another article (same INDEX, different actual id).
    #   - The validator's id-equality check was structurally a no-op because
    #     we then merged {**item, "id": item_id} before passing it in, which
    #     overrode item['id'] with item_id (making str(c.get('id'))==expected_id
    #     true by construction).
    # Now: only items where LLM-returned 'id' exists AND matches the article's
    # actual _id are accepted. Items the LLM omitted or mislabeled get dropped
    # and the existing retry pass (lines further down) re-classifies them in
    # tiny RETRY_PASS_BATCH_SIZE=3 batches.
    article_ids_in_batch = {str(a["_id"]) for a in articles}
    results: dict[str, dict] = {}
    for item in parsed:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", ""))
        if not item_id or item_id not in article_ids_in_batch:
            # LLM hallucinated id or returned an id not in this batch — drop.
            continue
        cleaned = _validate_classification(item, item_id)
        if cleaned:
            results[item_id] = cleaned
    return results


def _apply_classifications(
    articles: list[dict],
    results: dict[str, dict],
    coll,
    now: datetime,
) -> int:
    """Write classification results back to Mongo. Returns count applied."""
    applied = 0
    for article in articles:
        article_id = str(article["_id"])
        cls = results.get(article_id)
        if not cls:
            continue
        coll.update_one(
            {"_id": ObjectId(article_id)},
            {
                "$set": {
                    "classified": True,
                    "classified_at": now,
                    "classification_model": settings.ANTHROPIC_MODEL_FAST,
                    "sentiment": cls["sentiment"],
                    "sentiment_confidence": cls["sentiment_confidence"],
                    "themes": cls["themes"],
                    "severity": cls["severity"],
                    "classifier_summary": cls["classifier_summary"],
                    "updated_at": now,
                }
            },
        )
        applied += 1
    return applied


def classify_unclassified(
    limit: int | None = None,
    isin_filter: list[str] | None = None,
    only_recent_days: int | None = 35,
) -> dict:
    """Classify all news articles where classified=False."""
    coll = Collections.news_articles()
    query: dict = {"classified": False}
    if isin_filter:
        query["entities_isins"] = {"$in": isin_filter}
    if only_recent_days is not None:
        from datetime import timedelta

        cutoff = utcnow() - timedelta(days=only_recent_days)
        query["fetched_at"] = {"$gte": cutoff}

    cursor = coll.find(
        query,
        {"_id": 1, "title": 1, "summary": 1, "entities_symbols": 1, "url": 1},
    ).sort("fetched_at", -1)
    if limit:
        cursor = cursor.limit(limit)
    pending = list(cursor)

    stats = {
        "found_unclassified": len(pending),
        "classified": 0,
        "batches": 0,
        "failed_batches": 0,
        "retry_pass_classified": 0,
        "retry_pass_batches": 0,
        "still_unclassified": 0,
        "model": settings.ANTHROPIC_MODEL_FAST,
    }

    if not pending:
        log.info("No unclassified articles found")
        return stats

    log.info("Classifying %d articles in batches of %d", len(pending), BATCH_SIZE)
    now = utcnow()

    # Phase 1: Main pass
    for i in range(0, len(pending), BATCH_SIZE):
        batch = pending[i : i + BATCH_SIZE]
        stats["batches"] += 1
        log.info(
            "  Batch %d/%d (%d articles)",
            stats["batches"],
            (len(pending) + BATCH_SIZE - 1) // BATCH_SIZE,
            len(batch),
        )

        results = _classify_batch(batch)
        if not results:
            stats["failed_batches"] += 1
            log.warning("  Batch %d returned zero classifications", stats["batches"])
            continue

        applied = _apply_classifications(batch, results, coll, now)
        stats["classified"] += applied

    # Phase 2: Retry pass for stragglers
    pending_ids = [a["_id"] for a in pending]
    still_unclassified = list(
        coll.find(
            {"_id": {"$in": pending_ids}, "classified": False},
            {"_id": 1, "title": 1, "summary": 1, "entities_symbols": 1, "url": 1},
        )
    )

    if still_unclassified:
        log.info(
            "Retry pass: %d articles still unclassified, processing in batches of %d",
            len(still_unclassified),
            RETRY_PASS_BATCH_SIZE,
        )
        for i in range(0, len(still_unclassified), RETRY_PASS_BATCH_SIZE):
            mini_batch = still_unclassified[i : i + RETRY_PASS_BATCH_SIZE]
            stats["retry_pass_batches"] += 1
            results = _classify_batch(mini_batch)
            if not results:
                continue
            applied = _apply_classifications(mini_batch, results, coll, now)
            stats["retry_pass_classified"] += applied

        final_unclassified = coll.count_documents(
            {"_id": {"$in": pending_ids}, "classified": False}
        )
        stats["still_unclassified"] = final_unclassified
        if final_unclassified > 0:
            log.warning(
                "After retry pass, %d articles remain unclassified -- will be picked up next run",
                final_unclassified,
            )

    total_classified = stats["classified"] + stats["retry_pass_classified"]
    log.info(
        "Classification complete: %d/%d (%d main + %d retry), %d failed batches, %d still unclassified",
        total_classified,
        len(pending),
        stats["classified"],
        stats["retry_pass_classified"],
        stats["failed_batches"],
        stats["still_unclassified"],
    )
    return stats


# ── Entity-confirmation pass (master_todo #50, phase 3) ─────────────────────

# A separate, lightweight Haiku pass that runs AFTER the main classify pass.
# It covers ISINs that the rule-gate (_article_mentions_company) was uncertain
# about: articles that were fetched for a company but not yet entity-tagged
# (i.e. fetched_for_isins ⊃ entities_isins). For each such (article, company)
# pair, Haiku answers a binary "is this article actually about this company?"
# question. Confirmed pairs get $addToSet'd back into entities_isins.
#
# Pairs are batched to keep Haiku calls cheap. Output is additive: the pass
# can only ADD ISINs back; it never strips ones the rule-gate already accepted.
# (Rule-gate false-positives from known-good matches are trusted; the LLM
# handles the cases the rule-gate had to reject conservatively.)

_ENTITY_CONFIRM_SYSTEM_PROMPT = """You are a relevance checker for a financial news system.

For each item, decide whether the news article is actually ABOUT the named company.
"About" means the company is a primary or significant subject of the story -- not just a passing mention in a list or an unrelated context.

Output a single JSON array, one object per item, in input order:
[{"id": "<the id field echoed back>", "is_about": true or false}, ...]

No prose outside the array.

Guidelines:
- true: the article discusses the company's earnings, products, management, stock, deals, regulatory actions, or is clearly focused on that company.
- false: the company is mentioned only incidentally (e.g. as one of many stocks in a market recap), the article is about a similarly-named company in a different sector/country, or the company is not meaningfully relevant to the story.
"""

_ENTITY_CONFIRM_BATCH_SIZE = 20  # pairs per Haiku call


def _build_entity_confirm_prompt(pairs: list[dict]) -> str:
    """Build the user prompt for the entity-confirmation batch."""
    lines = [
        "Decide whether each article is about the named company.\n"
    ]
    for p in pairs:
        lines.append(
            "---\n"
            f"id: {p['pair_id']}\n"
            f"company: {p['name']} ({p['symbol']})\n"
            f"title: {p['title']}\n"
            f"summary: {p['summary'][:400]}\n"
        )
    return "\n".join(lines)


def _call_entity_confirm_batch(pairs: list[dict]) -> dict[str, bool]:
    """Call Haiku on a batch of (article, company) pairs. Returns {pair_id: is_about}."""
    if not pairs:
        return {}
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    prompt = _build_entity_confirm_prompt(pairs)

    for attempt in range(2):
        try:
            message = client.messages.create(
                model=settings.ANTHROPIC_MODEL_FAST,
                max_tokens=1024,
                system=_ENTITY_CONFIRM_SYSTEM_PROMPT
                + (
                    "\n\nIMPORTANT: Output ONLY the JSON array. No prose, no markdown."
                    if attempt > 0
                    else ""
                ),
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:
            log.error("Entity-confirm Haiku call failed (attempt %d): %s", attempt + 1, exc)
            return {}

        raw = "".join(
            block.text for block in message.content if hasattr(block, "text")
        )
        parsed = _parse_response(raw)  # reuse existing JSON-array parser
        if parsed is None:
            if attempt == 0:
                log.warning("Entity-confirm: unparseable response, retrying")
                continue
            log.error("Entity-confirm: unparseable after retry")
            return {}

        pair_ids_in_batch = {p["pair_id"] for p in pairs}
        results: dict[str, bool] = {}
        for item in parsed:
            if not isinstance(item, dict):
                continue
            pid = str(item.get("id", ""))
            if pid not in pair_ids_in_batch:
                continue
            is_about = item.get("is_about")
            if isinstance(is_about, bool):
                results[pid] = is_about
        return results

    return {}


def confirm_entities_llm(only_recent_days: int | None = 35) -> dict:
    """LLM entity-confirmation pass (master_todo #50, additive).

    Finds classified articles where some fetched_for_isins entries are absent
    from entities_isins (rule-gate conservatively rejected them), asks Haiku
    per (article, company) pair, and $addToSet confirmed ISINs back.

    Returns stats dict.
    """
    from datetime import timedelta

    coll = Collections.news_articles()
    query: dict = {"classified": True, "fetched_for_isins": {"$exists": True}}
    if only_recent_days is not None:
        cutoff = utcnow() - timedelta(days=only_recent_days)
        query["fetched_at"] = {"$gte": cutoff}

    # Fetch docs that have at least one fetched_for_isin -- we'll filter for
    # unconfirmed pairs in Python (simpler than a $expr $setDifference query).
    cursor = coll.find(
        query,
        {
            "_id": 1,
            "title": 1,
            "summary": 1,
            "fetched_for_isins": 1,
            "fetched_for_symbols": 1,
            "entities_isins": 1,
        },
    )
    articles = list(cursor)

    # Load instrument name index for all ISINs seen in fetched_for_isins.
    all_fetched_isins: set[str] = set()
    for art in articles:
        for isin in art.get("fetched_for_isins", []) or []:
            all_fetched_isins.add(isin)

    instr_idx: dict[str, dict] = {}
    if all_fetched_isins:
        for inst in Collections.instruments().find(
            {"isin": {"$in": list(all_fetched_isins)}},
            {"_id": 0, "isin": 1, "symbol": 1, "name": 1},
        ):
            isin = inst.get("isin")
            if isin:
                instr_idx[isin] = {
                    "symbol": (inst.get("symbol") or "").upper(),
                    "name": inst.get("name") or "",
                }

    # Build (article, company) pairs where the ISIN is NOT yet in entities_isins.
    pairs: list[dict] = []
    for art in articles:
        confirmed = set(art.get("entities_isins", []) or [])
        title = (art.get("title") or "").strip()
        summary = (art.get("summary") or "").strip()
        for isin in art.get("fetched_for_isins", []) or []:
            if isin in confirmed:
                continue  # rule-gate already accepted this one -- skip
            meta = instr_idx.get(isin)
            if meta is None:
                continue  # unknown instrument -- cannot ask LLM
            pairs.append(
                {
                    "pair_id": f"{art['_id']}|{isin}",
                    "article_id": art["_id"],
                    "isin": isin,
                    "symbol": meta["symbol"],
                    "name": meta["name"],
                    "title": title,
                    "summary": summary,
                }
            )

    stats = {
        "articles_scanned": len(articles),
        "pairs_checked": len(pairs),
        "pairs_confirmed": 0,
        "pairs_rejected": 0,
        "batches": 0,
        "failed_batches": 0,
        "model": settings.ANTHROPIC_MODEL_FAST,
    }

    if not pairs:
        log.info("Entity-confirm: no unconfirmed pairs to check")
        return stats

    log.info(
        "Entity-confirm: checking %d (article, company) pairs in batches of %d",
        len(pairs),
        _ENTITY_CONFIRM_BATCH_SIZE,
    )
    now = utcnow()

    for i in range(0, len(pairs), _ENTITY_CONFIRM_BATCH_SIZE):
        batch = pairs[i : i + _ENTITY_CONFIRM_BATCH_SIZE]
        stats["batches"] += 1
        results = _call_entity_confirm_batch(batch)
        if not results:
            stats["failed_batches"] += 1
            log.warning(
                "Entity-confirm batch %d returned no results", stats["batches"]
            )
            continue

        for p in batch:
            pid = p["pair_id"]
            is_about = results.get(pid)
            if is_about is None:
                continue  # LLM didn't return a verdict for this pair -- skip
            if is_about:
                stats["pairs_confirmed"] += 1
                coll.update_one(
                    {"_id": p["article_id"]},
                    {
                        "$addToSet": {
                            "entities_isins": p["isin"],
                            "entities_symbols": p["symbol"],
                        },
                        "$set": {"updated_at": now},
                    },
                )
            else:
                stats["pairs_rejected"] += 1

    log.info(
        "Entity-confirm complete: %d pairs checked, %d confirmed, %d rejected, "
        "%d batches (%d failed)",
        stats["pairs_checked"],
        stats["pairs_confirmed"],
        stats["pairs_rejected"],
        stats["batches"],
        stats["failed_batches"],
    )
    return stats
