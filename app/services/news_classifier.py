"""Claude Haiku classifier for news articles.

Batched: one Anthropic call classifies up to N articles in a single turn,
which is dramatically cheaper than per-article calls.

Output schema enforced by JSON parsing + validation. If Claude returns
malformed JSON, we retry once with a more constrained prompt; on second
failure, articles are marked classified=False with a logged error.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from app.config.settings import settings
from app.db.client import Collections
from app.models._common import utcnow

log = logging.getLogger(__name__)


# How many articles to classify per Anthropic call.
# Haiku handles ~30 well within token budget; we stay conservative.
BATCH_SIZE = 25


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
    """Build the user-message block for the batch."""
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
    """Extract the JSON array from Claude's response. Tolerant of fenced markdown."""
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
    """Validate one classification dict. Returns cleaned dict or None on invalid."""
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
    """Send one batch to Anthropic. Returns dict of article_id_str to classification_dict.

    Returns empty dict on persistent failure.
    """
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

    results: dict[str, dict] = {}
    article_ids_in_order = [str(a["_id"]) for a in articles]

    for i, item in enumerate(parsed):
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", "")) or (
            article_ids_in_order[i] if i < len(article_ids_in_order) else ""
        )
        if not item_id:
            continue
        cleaned = _validate_classification({**item, "id": item_id}, item_id)
        if cleaned:
            results[item_id] = cleaned

    return results


def classify_unclassified(
    limit: int | None = None,
    isin_filter: list[str] | None = None,
    only_recent_days: int | None = 35,
) -> dict:
    """Classify all news articles where classified=False.

    Args:
        limit: max number of articles to classify in this run (None = all)
        isin_filter: only classify articles whose entities_isins overlaps this list
        only_recent_days: skip articles fetched more than N days ago (cost control)

    Returns:
        Stats dict.
    """
    coll = Collections.news_articles()
    query: dict = {"classified": False}
    if isin_filter:
        query["entities_isins"] = {"$in": isin_filter}
    if only_recent_days is not None:
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(days=only_recent_days)
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
        "model": settings.ANTHROPIC_MODEL_FAST,
    }

    if not pending:
        log.info("No unclassified articles found")
        return stats

    log.info("Classifying %d articles in batches of %d", len(pending), BATCH_SIZE)

    now = utcnow()
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

        for article in batch:
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
            stats["classified"] += 1

    log.info(
        "Classification complete: %d/%d articles classified across %d batches (%d failed)",
        stats["classified"],
        len(pending),
        stats["batches"],
        stats["failed_batches"],
    )
    return stats
