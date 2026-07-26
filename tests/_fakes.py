"""In-memory Mongo doubles for the #33 pytest harness.

Zero external dependency: a minimal FakeCollection implementing only the
operators the services under test actually use (equality incl. array-multikey
membership, None, $ne, $in, $nin, $exists, $gte/$gt/$lte/$lt, $or, $and), plus
sort/limit/skip on find() and an upsert-aware update_one. Decimal values are
stored as-is (or as Decimal128 when the service wraps them via
_convert_decimals_to_decimal128); the model Money validator accepts both on
read.

($gte/$gt/$lte/$lt + array-multikey equality added for #65's
compute_dividend_drift: date-window/news-recency ranges and the
{themes: "corporate_action"} / {entities_isins: isin} multikey matches.)
"""

from __future__ import annotations

import copy
from datetime import datetime

from bson import ObjectId

_MISSING = object()


def oid() -> ObjectId:
    return ObjectId()


def _eq_or_member(actual, val) -> bool:
    """Mongo equality: on a scalar field it's ==, on an array field (multikey)
    it matches if the value is a MEMBER of the array. Mirrors how a query like
    {themes: "corporate_action"} or {entities_isins: isin} matches a list field.
    """
    if isinstance(actual, (list, tuple)):
        return val in actual
    return actual == val


def _match_value(actual, present: bool, cond) -> bool:
    if isinstance(cond, dict) and any(k.startswith("$") for k in cond):
        for op, val in cond.items():
            if op == "$ne":
                if actual == val:
                    return False
            elif op == "$in":
                if actual not in val:
                    return False
            elif op == "$nin":
                if actual in val:
                    return False
            elif op == "$exists":
                if bool(val) != present:
                    return False
            elif op == "$gte":
                if actual is None or not (actual >= val):
                    return False
            elif op == "$gt":
                if actual is None or not (actual > val):
                    return False
            elif op == "$lte":
                if actual is None or not (actual <= val):
                    return False
            elif op == "$lt":
                if actual is None or not (actual < val):
                    return False
            else:
                raise NotImplementedError(f"FakeCollection: operator {op} unsupported")
        return True
    return _eq_or_member(actual, cond)


def _matches(doc: dict, filt: dict) -> bool:
    for key, cond in filt.items():
        if key == "$or":
            if not any(_matches(doc, sub) for sub in cond):
                return False
        elif key == "$and":
            if not all(_matches(doc, sub) for sub in cond):
                return False
        else:
            present = key in doc
            actual = doc.get(key)
            if not _match_value(actual, present, cond):
                return False
    return True


def _sort_key(v):
    # None sorts first; same-field values are always the same type in practice.
    return (v is None, v)


class _Cursor:
    def __init__(self, docs: list[dict]):
        self._docs = docs

    def sort(self, key, direction: int = 1):
        self._docs.sort(key=lambda d: _sort_key(d.get(key)), reverse=(direction == -1))
        return self

    def skip(self, n: int):
        self._docs = self._docs[n:]
        return self

    def limit(self, n: int):
        self._docs = self._docs[:n]
        return self

    def __iter__(self):
        return iter(self._docs)

    def __list__(self):
        return list(self._docs)


class _InsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class _UpdateResult:
    def __init__(self, matched_count: int, upserted_id):
        self.matched_count = matched_count
        self.modified_count = matched_count
        self.upserted_id = upserted_id


class _DeleteResult:
    def __init__(self, deleted_count: int):
        self.deleted_count = deleted_count


class FakeCollection:
    """A deliberately tiny, in-memory stand-in for a pymongo collection."""

    def __init__(self, docs: list[dict] | None = None):
        self._docs: list[dict] = [copy.deepcopy(d) for d in (docs or [])]

    # ── seeding helpers (test-only) ──────────────────────────────────────
    def seed(self, *docs: dict) -> "FakeCollection":
        for d in docs:
            self.insert_one(copy.deepcopy(d))
        return self

    # ── pymongo-compatible surface ───────────────────────────────────────
    def find(self, filt: dict | None = None, projection=None) -> _Cursor:
        filt = filt or {}
        return _Cursor([copy.deepcopy(d) for d in self._docs if _matches(d, filt)])

    def find_one(self, filt: dict | None = None, projection=None, sort=None):
        filt = filt or {}
        matched = [d for d in self._docs if _matches(d, filt)]
        if sort:
            for key, direction in reversed(sort):
                matched.sort(
                    key=lambda d: _sort_key(d.get(key)), reverse=(direction == -1)
                )
        return copy.deepcopy(matched[0]) if matched else None

    def insert_one(self, doc: dict) -> _InsertResult:
        doc = copy.deepcopy(doc)
        if "_id" not in doc:
            doc["_id"] = ObjectId()
        self._docs.append(doc)
        return _InsertResult(doc["_id"])

    def update_one(
        self, filt: dict, update: dict, upsert: bool = False
    ) -> _UpdateResult:
        for d in self._docs:
            if _matches(d, filt):
                for k, v in update.get("$set", {}).items():
                    d[k] = copy.deepcopy(v)
                return _UpdateResult(1, None)
        if upsert:
            newdoc: dict = {}
            # Mongo seeds the filter's equality conditions into an upsert insert.
            for k, v in filt.items():
                if not k.startswith("$") and not isinstance(v, dict):
                    newdoc[k] = copy.deepcopy(v)
            newdoc.update(copy.deepcopy(update.get("$setOnInsert", {})))
            newdoc.update(copy.deepcopy(update.get("$set", {})))
            if "_id" not in newdoc:
                newdoc["_id"] = ObjectId()
            self._docs.append(newdoc)
            return _UpdateResult(0, newdoc["_id"])
        return _UpdateResult(0, None)

    def delete_one(self, filt: dict) -> _DeleteResult:
        for i, d in enumerate(self._docs):
            if _matches(d, filt):
                del self._docs[i]
                return _DeleteResult(1)
        return _DeleteResult(0)

    def delete_many(self, filt: dict) -> _DeleteResult:
        before = len(self._docs)
        self._docs = [d for d in self._docs if not _matches(d, filt)]
        return _DeleteResult(before - len(self._docs))

    def count_documents(self, filt: dict | None = None) -> int:
        filt = filt or {}
        return sum(1 for d in self._docs if _matches(d, filt))


def tx(
    ttype: str,
    quantity=0,
    price=0,
    fees=0,
    trade_date: datetime | None = None,
    isin: str = "INE000A01001",
    symbol: str = "TEST",
    exchange: str = "NSE",
    _id: ObjectId | None = None,
    corporate_action: dict | None = None,
    created_at: datetime | None = None,
    deleted_at: datetime | None = None,
) -> dict:
    """Build a Mongo-shaped transaction dict for the FIFO/replay tests."""
    d = {
        "_id": _id or ObjectId(),
        "type": ttype,
        "quantity": quantity,
        "price": price,
        "total_fees": fees,
        "trade_date": trade_date or datetime(2024, 1, 1),
        "isin": isin,
        "symbol": symbol,
        "exchange": exchange,
        "deleted_at": deleted_at,
    }
    if corporate_action is not None:
        d["corporate_action"] = corporate_action
    if created_at is not None:
        d["created_at"] = created_at
    return d
