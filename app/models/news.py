"""News article + classification models.

`news_articles` was scaffolded in Phase 1 with indexes already created. This
module defines the Pydantic shape we write and read.

Schema reflects the indexes already in place:
  - url (unique)
  - published_at (desc)
  - entities_isins (multikey)
  - entities_symbols (multikey)
  - themes (multikey)
  - source
  - body_purged_at (for deferred body cleanup)
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.models._common import BaseDoc, PyObjectId, utcnow

SentimentLabel = Literal["positive", "negative", "neutral"]
SeverityLabel = Literal["high", "medium", "low"]
ThemeLabel = Literal[
    "earnings",
    "regulatory",
    "corporate_action",
    "management_commentary",
    "sector_macro",
    "noise",
]


class NewsArticle(BaseDoc):
    """One news article. Append-only, dedupe by URL.

    Lifecycle:
      1. Inserted by news_fetcher with classification fields=None
      2. classifier.py fills in sentiment/themes/severity in a batched pass
      3. Optionally purged of body_text after 30 days (storage hygiene)
    """

    id: PyObjectId | None = Field(default=None, alias="_id")

    # Identity
    url: str = Field(..., description="Canonical URL — UNIQUE")
    title: str
    source: str = Field(
        default="", description="Domain (e.g. 'economictimes.indiatimes.com')"
    )

    # Content
    summary: str = Field(default="", description="Tavily's summary/snippet")
    body_text: str = Field(
        default="", description="Full content — purged after retention window"
    )
    body_purged_at: datetime | None = None

    # Provenance
    published_at: datetime | None = Field(
        default=None, description="Publisher's date if available"
    )
    fetched_at: datetime = Field(default_factory=utcnow)
    fetched_for_isins: list[str] = Field(
        default_factory=list,
        description="Which ISINs triggered this fetch — same article can be relevant to many",
    )
    fetched_for_symbols: list[str] = Field(default_factory=list)
    tavily_score: float | None = Field(default=None, description="Tavily relevance 0-1")

    # Entity extraction (filled at fetch time from search context)
    entities_isins: list[str] = Field(
        default_factory=list,
        description="ISINs we believe this article is about",
    )
    entities_symbols: list[str] = Field(default_factory=list)

    # Classification (filled by Haiku classifier in a separate pass)
    classified: bool = Field(default=False)
    classified_at: datetime | None = None
    classification_model: str = Field(default="")
    sentiment: SentimentLabel | None = None
    sentiment_confidence: float | None = Field(
        default=None, description="0-1, classifier confidence"
    )
    themes: list[ThemeLabel] = Field(default_factory=list)
    severity: SeverityLabel | None = None
    classifier_summary: str = Field(
        default="",
        description="2-line synthesized summary from classifier (the user-facing version)",
    )

    # Audit
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
