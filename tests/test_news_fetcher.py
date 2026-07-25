"""Tests for the #50 entity-relevance gate in news_fetcher.

Two layers:
  1. Pure-function tests for _article_mentions_company / _company_name_tokens
     (the deterministic matcher -- no DB, no network).
  2. Insert-path gating in _persist_results via a FakeCollection: a NEW article
     that mentions the company keeps its ISIN in entities_isins; one that does
     NOT is still persisted (provenance intact) but with entities_isins == [].

The dedup $addToSet MERGE branch (a URL seen under a second company's query)
is NOT unit-tested here: tests/_fakes.FakeCollection.insert_one never raises
DuplicateKeyError and update_one implements only $set (not $addToSet), so
covering it would mean over-building the harness (an explicit Chat B
anti-pattern). That branch is verified live on EC2 -- see the chat test block.
"""

from __future__ import annotations

import app.services.news_fetcher as nf
from tests._fakes import FakeCollection


# ── 1. Pure matcher ──────────────────────────────────────────────────────────


def test_symbol_token_match():
    assert nf._article_mentions_company(
        "HDFCBANK Q3 profit rises 20%", "", "HDFCBANK", "HDFC Bank Limited"
    )


def test_distinctive_name_token_match():
    # "hdfc" is a distinctive name token even without the symbol present.
    assert nf._article_mentions_company(
        "HDFC Bank reports strong quarter", "", "HDFCBANK", "HDFC Bank Limited"
    )


def test_off_topic_article_no_match():
    # The HDFCBANK query surfaced a TCS article -> must NOT match.
    assert not nf._article_mentions_company(
        "TCS wins large cloud deal in Europe",
        "Tata Consultancy Services signs multi-year contract",
        "HDFCBANK",
        "HDFC Bank Limited",
    )


def test_generic_token_alone_does_not_match():
    # "bank"/"india"/"finance" are generic -> an unrelated bank article must
    # not get tagged to this company purely on a generic token overlap.
    assert not nf._article_mentions_company(
        "Kenya's Family Bank posts record profit",
        "The bank in India-unrelated market grows deposits",
        "HDFCBANK",
        "HDFC Bank Limited",
    )


def test_empty_article_text_no_match():
    assert not nf._article_mentions_company("", "", "INFY", "Infosys Limited")


def test_summary_only_match():
    assert nf._article_mentions_company(
        "Market wrap", "Infosys guides higher on AI demand", "INFY", "Infosys Limited"
    )


def test_company_name_tokens_strips_suffix_and_generics():
    toks = nf._company_name_tokens("Tata Motors Limited")
    assert "tata" in toks
    assert "limited" not in toks  # suffix stripped
    assert "motors" not in toks  # generic dropped


def test_company_name_tokens_case_insensitive():
    assert nf._company_name_tokens("Reliance Industries") == {"reliance"}


# ── 2. Insert-path gating in _persist_results ────────────────────────────────


def _seed_news_collection(monkeypatch) -> FakeCollection:
    fake = FakeCollection()
    monkeypatch.setattr(
        nf.Collections, "news_articles", staticmethod(lambda: fake), raising=False
    )
    return fake


def _fresh_stats() -> dict:
    return {
        "fetched": 0,
        "new_inserted": 0,
        "merged_existing": 0,
        "skipped_excluded_domain": 0,
        "skipped_low_signal_url": 0,
        "skipped_off_topic_entity": 0,
    }


def test_persist_on_topic_tags_entity(monkeypatch):
    fake = _seed_news_collection(monkeypatch)
    stats = _fresh_stats()
    results = [
        {
            "url": "https://economictimes.indiatimes.com/hdfcbank-q3",
            "title": "HDFC Bank Q3 profit rises",
            "content": "HDFC Bank reported higher net interest income.",
            "score": 0.9,
        }
    ]
    # _persist_results takes (results, isin, symbol, name, stats). Here the
    # symbol token itself ("HDFCBANK") appears in the text, so it matches.
    nf._persist_results(
        results, "INE040A01034", "HDFCBANK", "HDFC Bank Limited", stats
    )

    assert stats["new_inserted"] == 1
    assert stats["skipped_off_topic_entity"] == 0
    doc = fake.find_one({"url": results[0]["url"]})
    assert doc["entities_isins"] == ["INE040A01034"]
    assert doc["entities_symbols"] == ["HDFCBANK"]
    assert doc["fetched_for_isins"] == ["INE040A01034"]


def test_persist_off_topic_keeps_provenance_but_empties_entity(monkeypatch):
    fake = _seed_news_collection(monkeypatch)
    stats = _fresh_stats()
    results = [
        {
            "url": "https://reuters.com/family-bank-kenya",
            "title": "Kenya's Family Bank posts record profit",
            "content": "The Nairobi lender grew deposits sharply.",
            "score": 0.5,
        }
    ]
    nf._persist_results(
        results, "INE040A01034", "HDFCBANK", "HDFC Bank Limited", stats
    )

    assert stats["new_inserted"] == 1
    assert stats["skipped_off_topic_entity"] == 1
    doc = fake.find_one({"url": results[0]["url"]})
    # Provenance recorded; entity NOT asserted.
    assert doc["fetched_for_isins"] == ["INE040A01034"]
    assert doc["fetched_for_symbols"] == ["HDFCBANK"]
    assert doc["entities_isins"] == []
    assert doc["entities_symbols"] == []
