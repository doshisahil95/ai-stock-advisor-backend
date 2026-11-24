"""Regression guard for the "inert news signal" bug (post-Chat-15).

After #80 H3 changed the news-signal window to query `published_at`, every
article (which the fetcher wrote with published_at=null) stopped matching, so
compute_news_signals_for_isin returned has_news=False for every stock. The fix
falls back to fetched_at when published_at is null. These tests lock that in.

Hermetic: the `fake_db` fixture patches Collections.news_articles to an
in-memory FakeCollection (no Atlas, no network).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services.news_signals import compute_news_signals_for_isin

ISIN = "INE000A01001"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _article(
    *,
    published_at: datetime | None,
    fetched_at: datetime,
    themes: list[str] | None = None,
    sentiment: str = "positive",
    severity: str = "high",
    confidence: float = 0.9,
) -> dict:
    return {
        "entities_isins": [ISIN],
        "classified": True,
        "sentiment": sentiment,
        "sentiment_confidence": confidence,
        "themes": themes if themes is not None else ["earnings"],
        "severity": severity,
        "published_at": published_at,
        "fetched_at": fetched_at,
    }


def test_legacy_null_published_at_falls_back_to_fetched_at(fake_db):
    # THE regression guard: published_at=None (field present, value null) must
    # still be counted via fetched_at inside the window.
    now = _now()
    fake_db["news_articles"].seed(
        _article(published_at=None, fetched_at=now - timedelta(days=2))
    )
    sig = compute_news_signals_for_isin(ISIN)
    assert sig["has_news"] is True
    assert sig["story_count"] == 1
    assert sig["articles_considered"] == 1
    assert sig["net_sentiment"] > 0


def test_published_at_within_window_is_counted(fake_db):
    now = _now()
    fake_db["news_articles"].seed(
        _article(
            published_at=now - timedelta(days=3),
            fetched_at=now - timedelta(days=1),
        )
    )
    sig = compute_news_signals_for_isin(ISIN)
    assert sig["has_news"] is True
    assert sig["story_count"] == 1


def test_published_at_older_than_window_is_excluded(fake_db):
    # Old publish date but recent fetch (a backfill) must NOT enter the window.
    now = _now()
    fake_db["news_articles"].seed(
        _article(
            published_at=now - timedelta(days=40),
            fetched_at=now - timedelta(days=1),
        )
    )
    sig = compute_news_signals_for_isin(ISIN)
    assert sig["has_news"] is False
    assert sig["articles_considered"] == 0


def test_null_published_at_old_fetch_is_excluded(fake_db):
    now = _now()
    fake_db["news_articles"].seed(
        _article(published_at=None, fetched_at=now - timedelta(days=40))
    )
    sig = compute_news_signals_for_isin(ISIN)
    assert sig["has_news"] is False


def test_noise_theme_not_counted(fake_db):
    now = _now()
    fake_db["news_articles"].seed(
        _article(
            published_at=None,
            fetched_at=now - timedelta(days=1),
            themes=["noise"],
        )
    )
    sig = compute_news_signals_for_isin(ISIN)
    assert sig["has_news"] is False
    assert sig["story_count"] == 0


def test_high_severity_negative_counted(fake_db):
    now = _now()
    fake_db["news_articles"].seed(
        _article(
            published_at=None,
            fetched_at=now - timedelta(days=1),
            sentiment="negative",
            severity="high",
        )
    )
    sig = compute_news_signals_for_isin(ISIN)
    assert sig["high_severity_negative_count"] == 1


def test_velocity_and_recency_use_published_at(fake_db):
    # 2 recent (<=7d) + 1 older -> a real split, NOT the hardcoded 2.0 fallback
    # (which only fires when older_rate == 0).
    now = _now()
    fake_db["news_articles"].seed(
        _article(
            published_at=now - timedelta(days=1),
            fetched_at=now - timedelta(days=1),
        ),
        _article(
            published_at=now - timedelta(days=2),
            fetched_at=now - timedelta(days=2),
        ),
        _article(
            published_at=now - timedelta(days=20),
            fetched_at=now - timedelta(days=20),
        ),
    )
    sig = compute_news_signals_for_isin(ISIN)
    assert sig["story_count"] == 3
    assert sig["story_velocity"] > 1.0
    assert sig["story_velocity"] != 2.0
    assert sig["days_since_latest_news"] is not None
    assert sig["days_since_latest_news"] < 3
