"""News articles — full text 90 days, summaries kept forever."""

from datetime import datetime
from typing import Literal

from pydantic import Field, HttpUrl

from app.models._common import BaseDoc, PyObjectId, utcnow

NewsSource = Literal[
    "moneycontrol",
    "livemint",
    "et_markets",
    "reuters_india",
    "bloomberg",
    "tavily",
    "manual",
    "rss_other",
]
SentimentLabel = Literal[
    "very_negative", "negative", "neutral", "positive", "very_positive"
]
ImpactEstimate = Literal["low", "medium", "high"]


class NewsArticle(BaseDoc):
    """A news article ingested from RSS, Tavily, or other source."""

    id: PyObjectId | None = Field(default=None, alias="_id")

    # Source
    url: str = Field(..., description="Canonical URL — used for dedup")
    title: str
    source: NewsSource
    author: str = ""
    published_at: datetime
    fetched_at: datetime = Field(default_factory=utcnow)

    # Content
    body_text: str = Field(
        default="", description="Cleaned article body — purged after 90 days"
    )
    body_purged_at: datetime | None = None
    summary: str = Field(
        default="", description="Claude Haiku 2-3 sentence summary — kept forever"
    )

    # Extracted entities
    entities_symbols: list[str] = Field(
        default_factory=list, description="Tickers mentioned"
    )
    entities_isins: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    themes: list[str] = Field(
        default_factory=list,
        description="e.g., 'earnings', 'guidance_cut', 'rate_cut', 'fii_outflow'",
    )

    # Sentiment
    sentiment_score: float | None = Field(default=None, ge=-1, le=1)
    sentiment_label: SentimentLabel | None = None
    impact_estimate: ImpactEstimate | None = None

    # Embeddings (Phase 4 — for RAG)
    embedding: list[float] | None = None
    embedding_model: str = ""

    # Tracking
    used_in_digests: list[PyObjectId] = Field(default_factory=list)
    triggered_alerts: list[PyObjectId] = Field(default_factory=list)

    # Audit
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
