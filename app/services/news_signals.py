"""News signal aggregation — turn classified articles into per-stock numeric signals.

Inputs: classified `news_articles` for a given ISIN over a recency window.
Outputs: a NewsSignals dict consumable by the scoring engine.

Signals computed per stock:
  - net_sentiment: weighted sentiment score, -1.0 to +1.0
  - story_count_30d: total non-noise stories
  - high_severity_negative_count: hard signal for risk/exclusion
  - story_velocity: recent (7d) vs prior (8-30d) story count ratio
  - days_since_latest_news: freshness indicator
  - has_news: false means the candidate had zero classified articles
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from app.db.client import Collections

log = logging.getLogger(__name__)

_THEME_WEIGHTS = {
    "earnings": 1.0,
    "regulatory": 0.9,
    "corporate_action": 0.8,
    "management_commentary": 0.7,
    "sector_macro": 0.4,
    "noise": 0.0,
}

_SEVERITY_WEIGHTS = {
    "high": 1.0,
    "medium": 0.6,
    "low": 0.3,
}

_SENTIMENT_VALUES = {
    "positive": 1.0,
    "neutral": 0.0,
    "negative": -1.0,
}


def _max_theme_weight(themes: list[str]) -> float:
    if not themes:
        return 0.0
    return max(_THEME_WEIGHTS.get(t, 0.0) for t in themes)


def compute_news_signals_for_isin(
    isin: str,
    window_days: int = 30,
    recency_split_days: int = 7,
) -> dict:
    """Compute news signals for one stock over the last `window_days`."""
    now = datetime.now(
        timezone.utc
    )  # tz-ok: aware base for news recency-window cutoffs computed below
    cutoff_window = now - timedelta(days=window_days)
    cutoff_recent = now - timedelta(days=recency_split_days)

    coll = Collections.news_articles()
    cursor = coll.find(
        {
            "entities_isins": isin,
            "classified": True,
            "fetched_at": {"$gte": cutoff_window},
        },
        {
            "_id": 0,
            "sentiment": 1,
            "sentiment_confidence": 1,
            "themes": 1,
            "severity": 1,
            "fetched_at": 1,
            "published_at": 1,
        },
    )
    articles = list(cursor)

    if not articles:
        return {
            "has_news": False,
            "net_sentiment": 0.0,
            "story_count": 0,
            "high_severity_negative_count": 0,
            "story_velocity": 1.0,
            "days_since_latest_news": None,
            "articles_considered": 0,
        }

    weighted_sum = 0.0
    weight_total = 0.0
    non_noise_count = 0
    high_sev_neg = 0
    recent_count = 0
    older_count = 0
    latest_dt: datetime | None = None

    for a in articles:
        themes = a.get("themes", []) or []
        sentiment = a.get("sentiment", "neutral")
        confidence = a.get("sentiment_confidence")
        if confidence is None:
            confidence = 0.5
        severity = a.get("severity", "low")

        theme_w = _max_theme_weight(themes)
        if theme_w == 0.0:
            continue

        non_noise_count += 1

        sev_w = _SEVERITY_WEIGHTS.get(severity, 0.3)
        sent_v = _SENTIMENT_VALUES.get(sentiment, 0.0)

        article_weight = float(confidence) * theme_w * sev_w
        weighted_sum += sent_v * article_weight
        weight_total += article_weight

        if severity == "high" and sentiment == "negative":
            high_sev_neg += 1

        # #76 U5-d: velocity + days_since_latest must reflect when the story was
        # PUBLISHED, not when we happened to fetch it. Windowing these on
        # fetched_at let a news backfill (many articles ingested at once)
        # inflate story_velocity and corrupt days_since_latest_news. Prefer
        # published_at; fall back to fetched_at only when published_at is absent.
        when = a.get("published_at") or a.get("fetched_at")
        if when is not None:
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            if when >= cutoff_recent:
                recent_count += 1
            else:
                older_count += 1
            if latest_dt is None or when > latest_dt:
                latest_dt = when

    net_sentiment = (weighted_sum / weight_total) if weight_total > 0 else 0.0

    recent_days = recency_split_days
    older_days = window_days - recency_split_days
    recent_rate = recent_count / recent_days if recent_days > 0 else 0.0
    older_rate = older_count / older_days if older_days > 0 else 0.0
    if older_rate > 0:
        velocity = recent_rate / older_rate
    elif recent_rate > 0:
        velocity = 2.0
    else:
        velocity = 1.0

    days_since_latest = None
    if latest_dt is not None:
        days_since_latest = (now - latest_dt).total_seconds() / 86400.0

    return {
        "has_news": non_noise_count > 0,
        "net_sentiment": round(net_sentiment, 4),
        "story_count": non_noise_count,
        "high_severity_negative_count": high_sev_neg,
        "story_velocity": round(velocity, 3),
        "days_since_latest_news": round(days_since_latest, 1)
        if days_since_latest is not None
        else None,
        "articles_considered": len(articles),
    }


def compute_news_signals_bulk(
    isins: list[str],
    window_days: int = 30,
) -> dict[str, dict]:
    """Compute news signals for many ISINs."""
    return {
        isin: compute_news_signals_for_isin(isin, window_days=window_days)
        for isin in isins
    }
