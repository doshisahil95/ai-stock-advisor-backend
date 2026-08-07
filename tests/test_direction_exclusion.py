"""Hermetic tests for TD1/#43 direction-scoped feedback exclusion.

get_excluded_isins now honors monitored_stocks.feedback_direction so a
sell-side "rejected" no longer suppresses the buy side (and vice versa),
while legacy/direction-less docs keep the prior direction-agnostic behavior.

Pure in-memory FakeCollection harness (#33) — no Atlas, no network.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services.suggestion_engine import get_excluded_isins

BUY_ISIN = "INE000A01001"
SELL_ISIN = "INE000A01002"
LEGACY_ISIN = "INE000A01003"

# A fixed "now" well inside both the 90d rejected and 30d acted windows.
NOW = datetime(2026, 8, 7, tzinfo=timezone.utc)
RECENT = NOW - timedelta(days=5)  # inside both windows


def _rejected_doc(isin: str, feedback_direction: str | None) -> dict:
    doc = {
        "isin": isin,
        "status": "rejected",
        "rejected_at": RECENT,
        "added_by": "user_explicit",
    }
    if feedback_direction is not None:
        doc["feedback_direction"] = feedback_direction
    return doc


def _acted_doc(isin: str, feedback_direction: str | None) -> dict:
    doc = {
        "isin": isin,
        "status": "tracking",
        "acted_at": RECENT,
        "added_by": "user_explicit",
    }
    if feedback_direction is not None:
        doc["feedback_direction"] = feedback_direction
    return doc


def test_buy_rejection_excludes_buy_not_sell(fake_db):
    """A buy-side rejection excludes the ISIN from the buy pipeline but NOT
    the sell pipeline — the core leak TD1/#43 closes."""
    fake_db["monitored_stocks"].seed(_rejected_doc(BUY_ISIN, "buy"))

    buy = get_excluded_isins(now=NOW, direction="buy")
    sell = get_excluded_isins(now=NOW, direction="sell")

    assert BUY_ISIN in buy["rejected"]
    assert BUY_ISIN not in sell["rejected"]


def test_sell_rejection_excludes_sell_not_buy(fake_db):
    """A sell-side rejection excludes the ISIN from the sell pipeline but NOT
    the buy pipeline (the specific INFY scenario the old code flagged)."""
    fake_db["monitored_stocks"].seed(_rejected_doc(SELL_ISIN, "sell"))

    buy = get_excluded_isins(now=NOW, direction="buy")
    sell = get_excluded_isins(now=NOW, direction="sell")

    assert SELL_ISIN in sell["rejected"]
    assert SELL_ISIN not in buy["rejected"]


def test_legacy_doc_without_direction_excludes_both(fake_db):
    """BACK-COMPAT: a pre-#43 doc (no feedback_direction) must behave exactly
    as before — excluded on BOTH directions. This guarantees the two live
    pre-#43 docs keep their current behavior with zero migration."""
    fake_db["monitored_stocks"].seed(_rejected_doc(LEGACY_ISIN, None))

    buy = get_excluded_isins(now=NOW, direction="buy")
    sell = get_excluded_isins(now=NOW, direction="sell")

    assert LEGACY_ISIN in buy["rejected"]
    assert LEGACY_ISIN in sell["rejected"]


def test_acted_bucket_is_direction_scoped(fake_db):
    """The F5b 'acted' (tracking) bucket is direction-scoped too."""
    fake_db["monitored_stocks"].seed(_acted_doc(BUY_ISIN, "buy"))

    buy = get_excluded_isins(now=NOW, direction="buy")
    sell = get_excluded_isins(now=NOW, direction="sell")

    assert BUY_ISIN in buy["acted"]
    assert BUY_ISIN not in sell["acted"]


def test_mixed_docs_route_correctly(fake_db):
    """A buy-rejected, a sell-rejected, and a legacy doc together resolve to
    the correct per-direction exclusion sets."""
    fake_db["monitored_stocks"].seed(
        _rejected_doc(BUY_ISIN, "buy"),
        _rejected_doc(SELL_ISIN, "sell"),
        _rejected_doc(LEGACY_ISIN, None),
    )

    buy = get_excluded_isins(now=NOW, direction="buy")
    sell = get_excluded_isins(now=NOW, direction="sell")

    assert buy["rejected"] == {BUY_ISIN, LEGACY_ISIN}
    assert sell["rejected"] == {SELL_ISIN, LEGACY_ISIN}


def test_default_direction_is_buy(fake_db):
    """Called with no direction arg, defaults to 'buy' (back-compat with any
    caller that predates the param)."""
    fake_db["monitored_stocks"].seed(
        _rejected_doc(BUY_ISIN, "buy"),
        _rejected_doc(SELL_ISIN, "sell"),
    )

    default = get_excluded_isins(now=NOW)

    assert BUY_ISIN in default["rejected"]
    assert SELL_ISIN not in default["rejected"]
