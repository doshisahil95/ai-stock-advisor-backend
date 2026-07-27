"""Shared fixtures for the #33 harness.

`fake_db` swaps every Collections.* accessor the services-under-test touch
for an in-memory FakeCollection, so tests are hermetic (no Atlas, no
network) and run anywhere via `uv run python -m pytest`.
"""

from __future__ import annotations

import pytest

import app.db.client as db_client
from tests._fakes import FakeCollection

# Accessors the targeted services call. Patching the class attribute is seen
# by every module that did `from app.db.client import Collections`, since they
# all reference the same class object and call the accessor at call-time.
_COLLECTION_NAMES = [
    "transactions",
    "holdings",
    "instruments",
    "recompute_locks",
    "reconciliation_snapshots",
    "user_profile",
    "monitored_stocks",
    "monitored_stocks_audit",
    "suggestion_outcomes",
    "suggestion_runs",
    # #65: compute_dividend_drift reads these two as well.
    "dividend_announcements",
    "news_articles",
    # #68: record_corporate_action writes the §49(2C) demerger adjustment here.
    "cost_basis_adjustments",
]


@pytest.fixture
def fake_db(monkeypatch) -> dict[str, FakeCollection]:
    fakes: dict[str, FakeCollection] = {
        name: FakeCollection() for name in _COLLECTION_NAMES
    }
    for name in _COLLECTION_NAMES:
        monkeypatch.setattr(
            db_client.Collections,
            name,
            staticmethod(lambda _n=name: fakes[_n]),
            raising=False,
        )
    return fakes
