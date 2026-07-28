"""Holding computation service.

Holdings are derived state — never written to directly.

After any change to
`transactions` for a stock, call recompute_holding(isin) to rebuild the holding
from scratch using FIFO accounting.

This is intentionally simple (replay all transactions every time) rather than
incremental (apply just the new transaction).

A typical stock has <1000
transactions in its lifetime; replay takes <50ms.

Simplicity > micro-optimization.
"""

from __future__ import annotations
import logging
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError
from app.db.client import Collections
from app.models._common import _convert_decimals_to_decimal128, utcnow
from app.models.holding import Holding
from app.services.yfinance_lookup import fetch_metadata

log = logging.getLogger(__name__)


@dataclass
class _Lot:
    """One BUY lot in the FIFO queue."""

    transaction_id: object
    quantity: Decimal
    price: Decimal
    fees: Decimal
    trade_date: datetime
    # #53: the date used for the STCG/LTCG holding-period test. For a normal BUY
    # this equals trade_date. For a demerger receipt (which carries an explicit
    # `acquired_date` = the parent's original acquisition date), this is that
    # inherited date, so the holding period is measured from the parent's
    # acquisition, per the IT Act. FIFO ordering still uses trade_date; cost basis
    # still uses price. Only the buy_trade_date emitted into _realized_lots differs.
    acquired_date: datetime


def _to_decimal(value) -> Decimal:
    """Convert a Mongo-stored numeric value to Python Decimal.

    Handles Decimal128 (Mongo's native), Decimal, and string/int/float fallbacks.
    """
    from bson import Decimal128

    if isinstance(value, Decimal128):
        return value.to_decimal()
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _apply_split_or_bonus_to_dict_lots(
    lots: list[dict],
    ttype: str,
    ca: dict | None,
) -> None:
    """Mutate lot dicts in-place to apply a SPLIT or BONUS corporate action.

    Lot dict shape: requires "qty" key. "price" key is optional (preview_sell
    has it; validate_replay does not need to track price).
    Fees on lots are unaffected by corporate actions.

    SPLIT semantics (mirrors _fifo_replay):
        ratio_to / ratio_from multiplies qty; same ratio inversely scales price.
        E.g. 1:2 split (ratio_from=1, ratio_to=2): 100 sh @ ₹10 → 200 sh @ ₹5.

    BONUS semantics (mirrors _fifo_replay):
        ratio_to bonus shares for every ratio_from held.
        E.g. 1:1 bonus (ratio_from=1, ratio_to=1): 100 sh @ ₹10 → 200 sh @ ₹5
        (avg cost dilutes proportionally).

    F3/F4 fix (Chat 5.5+): preview_sell and validate_replay previously skipped
    SPLIT/BONUS entirely. preview_sell showed wrong preview math for any stock
    with a split/bonus in its history; validate_replay rejected legitimate
    post-split SELLs as oversells. _fifo_replay itself was correct all along
    (it uses _Lot dataclass and inline logic) — this helper mirrors that logic
    onto the dict-shaped lots used by preview/validate.
    """
    if not ca:
        return
    ratio_from = Decimal(str(ca.get("ratio_from", 0)))
    ratio_to = Decimal(str(ca.get("ratio_to", 0)))
    if ratio_from <= 0 or ratio_to <= 0:
        return
    if ttype == "SPLIT":
        for lot in lots:
            lot["qty"] = lot["qty"] * ratio_to / ratio_from
            if "price" in lot:
                lot["price"] = lot["price"] * ratio_from / ratio_to
    elif ttype == "BONUS":
        # First add bonus qty across all lots
        for lot in lots:
            bonus_qty = lot["qty"] * ratio_to / ratio_from
            lot["qty"] += bonus_qty
        # Then dilute price (formula uses event-level ratio, not per-lot qty)
        if any("price" in lot for lot in lots):
            dilution = ratio_from / (ratio_from + ratio_to)
            for lot in lots:
                if lot["qty"] > 0 and "price" in lot:
                    lot["price"] = lot["price"] * dilution


def _fifo_replay(transactions: Iterable[dict]) -> dict:
    """Replay transactions chronologically with FIFO depletion.

    Returns a dict of computed fields ready to merge into the Holding doc.
    """
    lots: deque[_Lot] = deque()
    realized_pnl = Decimal("0")
    # F11/#39: per-disposal capital-gains records captured during FIFO depletion.
    # Read-only consumer is tax_service.compute_capital_gains; _recompute_holding_impl
    # pops this off `computed` so it never lands on the holdings doc. This is NOT a
    # parallel FIFO path -- it is the single FIFO source of truth emitting one row per
    # buy-lot consumed by a SELL (buy/sell dates + per-share cost/proceeds incl. fees).
    realized_lots: list[dict] = []
    total_dividends = Decimal("0")

    first_purchased_at: datetime | None = None
    last_traded_at: datetime | None = None

    for tx in transactions:
        ttype = tx["type"]
        qty = Decimal(str(tx["quantity"]))
        price = Decimal(str(tx["price"]))
        fees = Decimal(str(tx.get("total_fees", 0)))
        trade_date = tx["trade_date"]
        last_traded_at = trade_date

        if ttype == "BUY":
            if first_purchased_at is None:
                first_purchased_at = trade_date
            # #53: demerger receipts carry an explicit acquired_date (the parent's
            # original acquisition date) for holding-period inheritance; a normal
            # BUY has none, so the lot's acquired_date defaults to its trade_date.
            acquired_date = tx.get("acquired_date") or trade_date
            lots.append(
                _Lot(
                    transaction_id=tx["_id"],
                    quantity=qty,
                    price=price,
                    fees=fees,
                    trade_date=trade_date,
                    acquired_date=acquired_date,
                )
            )
        elif ttype == "SELL":
            remaining_to_sell = qty
            sell_proceeds_per_share = price - (fees / qty if qty > 0 else Decimal("0"))
            while remaining_to_sell > 0 and lots:
                lot = lots[0]
                take = min(remaining_to_sell, lot.quantity)
                buy_cost_per_share = lot.price + (
                    lot.fees / lot.quantity if lot.quantity > 0 else Decimal("0")
                )
                realized_pnl += take * (sell_proceeds_per_share - buy_cost_per_share)
                # F11/#39: record this buy-lot -> sell disposal for capital-gains.
                # Per-share figures are already fee-normalized on both sides, so
                # take*(proceeds/sh - cost/sh) equals this lot's realized_pnl slice.
                realized_lots.append(
                    {
                        # #53: buy_trade_date is the HOLDING-PERIOD date (lot.acquired_date),
                        # which equals lot.trade_date for a normal BUY and the parent's
                        # inherited acquisition date for a demerger receipt. tax_service
                        # classifies STCG/LTCG off this date; cost basis is unaffected.
                        "buy_trade_date": lot.acquired_date,
                        "sell_trade_date": trade_date,
                        "quantity": take,
                        "buy_cost_per_share": buy_cost_per_share,
                        "sell_proceeds_per_share": sell_proceeds_per_share,
                    }
                )
                # Proportionally deplete the lot's buy-side fees too
                if lot.quantity > 0:
                    lot.fees -= lot.fees * take / lot.quantity
                lot.quantity -= take
                remaining_to_sell -= take
                if lot.quantity == 0:
                    lots.popleft()
            if remaining_to_sell > 0:
                # Sold more than owned — log but continue (data integrity issue, not crash)
                log.warning(
                    "Oversold detected for transaction %s: %s shares unaccounted",
                    tx.get("_id"),
                    remaining_to_sell,
                )
        elif ttype == "DIVIDEND":
            # price = per-share payout
            current_qty = sum((lot.quantity for lot in lots), Decimal("0"))
            total_dividends += current_qty * price
        elif ttype == "BONUS":
            # corporate_action.ratio_to bonus shares for every ratio_from held
            ca = tx.get("corporate_action") or {}
            ratio_from = Decimal(str(ca.get("ratio_from", 1)))
            ratio_to = Decimal(str(ca.get("ratio_to", 0)))
            if ratio_from > 0 and ratio_to > 0:
                # New zero-cost shares added proportional to existing holdings
                # Distribute across existing lots so cost basis dilutes correctly
                for lot in lots:
                    bonus_qty = lot.quantity * ratio_to / ratio_from
                    lot.quantity += bonus_qty
                # avg cost dilutes: same total cost, more shares
                # (lot.price stays in absolute terms; we'll compute avg later)
                # Recompute lot prices to reflect dilution
                for lot in lots:
                    if lot.quantity > 0:
                        lot.price = lot.price * (ratio_from / (ratio_from + ratio_to))
        elif ttype == "SPLIT":
            ca = tx.get("corporate_action") or {}
            ratio_from = Decimal(str(ca.get("ratio_from", 1)))
            ratio_to = Decimal(str(ca.get("ratio_to", 1)))
            if ratio_from > 0 and ratio_to > 0:
                for lot in lots:
                    lot.quantity = lot.quantity * ratio_to / ratio_from
                    lot.price = lot.price * ratio_from / ratio_to

    # Aggregate remaining lots
    remaining_qty = sum((lot.quantity for lot in lots), Decimal("0"))
    if remaining_qty > 0:
        invested = sum((lot.quantity * lot.price for lot in lots), Decimal("0")) + sum(
            (lot.fees for lot in lots), Decimal("0")
        )
        avg_cost = (invested / remaining_qty).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
        invested = invested.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        invested = Decimal("0")
        avg_cost = Decimal("0")

    realized_pnl = realized_pnl.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total_dividends = total_dividends.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return {
        "quantity": remaining_qty,
        "avg_cost": avg_cost,
        "invested_amount": invested,
        "realized_pnl": realized_pnl,
        "total_dividends_received": total_dividends,
        "first_purchased_at": first_purchased_at,
        "last_traded_at": last_traded_at,
        "_realized_lots": realized_lots,
        "_remaining_lots": [
            {
                "transaction_id": lot.transaction_id,
                "quantity": lot.quantity,
                "price": lot.price,
                "trade_date": lot.trade_date,
            }
            for lot in lots
        ],
    }


# ─── TD20: per-ISIN recompute serialization ──────────────────────────────
_RECOMPUTE_LOCK_WAIT_TIMEOUT = 10.0  # max seconds to wait for the lock
_RECOMPUTE_LOCK_POLL_INTERVAL = 0.05  # seconds between acquire attempts


@contextmanager
def _per_isin_recompute_lock(isin: str):
    """Advisory lock serializing recompute_holding for a single ISIN (TD20).

    Acquire = insert a doc with _id == isin into recompute_locks; the unique
    _id index makes the insert atomic, so exactly one holder wins. A
    DuplicateKeyError means someone else holds it -> poll until free or time
    out. Release = delete the doc in `finally`. A TTL index on acquired_at
    (indexes.py) reclaims the lock if a holder crashes before releasing.
    """
    locks = Collections.recompute_locks()
    deadline = time.monotonic() + _RECOMPUTE_LOCK_WAIT_TIMEOUT
    acquired = False
    while True:
        try:
            locks.insert_one({"_id": isin, "acquired_at": utcnow()})
            acquired = True
            break
        except DuplicateKeyError:
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    f"Could not acquire recompute lock for {isin} within "
                    f"{_RECOMPUTE_LOCK_WAIT_TIMEOUT}s "
                    f"(another recompute for this ISIN is in progress)."
                )
            time.sleep(_RECOMPUTE_LOCK_POLL_INTERVAL)
    try:
        yield
    finally:
        if acquired:
            locks.delete_one({"_id": isin})


def recompute_holding(isin: str) -> Holding | None:
    """Serialize recompute per-ISIN (TD20), then delegate to the impl.

    Concurrent writes to the same ISIN (a BUY and a SELL, or two rapid SELLs)
    could previously both insert their ledger row and then both run a full
    read-replay-overwrite of the holding aggregate, interleaving and leaving a
    stale/wrong holding. We take a per-ISIN advisory lock so recompute bodies
    for the same ISIN run strictly one-at-a-time. The lock sits at the service
    layer so EVERY caller is protected -- the API buy/sell handlers AND the
    out-of-process scripts (manual import, order-book promote, reconciliation)
    that also call recompute_holding. Different ISINs never contend.
    """
    with _per_isin_recompute_lock(isin):
        return _recompute_holding_impl(isin)


def _recompute_holding_impl(isin: str) -> Holding | None:
    """Rebuild the holding for `isin` from its transactions.

    Returns the recomputed Holding (after upsert).
    If no transactions exist,
    soft-deletes any existing holding and returns None.
    """
    txs_coll = Collections.transactions()
    holdings_coll = Collections.holdings()

    # Pull all non-deleted transactions for this ISIN, oldest first.
    # #77 U6-c: tie-break same-trade_date rows by created_at so the REAL replay
    # processes them in the SAME order validate_replay checks
    # ((trade_date, created_at)). A plain trade_date sort is Mongo-unstable for
    # equal keys, so an edit could PASS validation under one ordering yet the
    # replay match different lots -> different realized P&L + STCG/LTCG.
    transactions = list(
        txs_coll.find(
            {"isin": isin, "deleted_at": None},
        ).sort([("trade_date", ASCENDING), ("created_at", ASCENDING)])
    )

    if not transactions:
        # No transactions — soft-delete any existing holding
        holdings_coll.update_one(
            {"isin": isin, "deleted_at": None},
            {"$set": {"deleted_at": utcnow(), "updated_at": utcnow()}},
        )
        return None

    computed = _fifo_replay(transactions)
    remaining_lots = computed.pop("_remaining_lots")
    # F11/#39: capital-gains disposal records are for tax_service's read-only use;
    # drop them so they never get written onto the holding doc (extra="forbid" would
    # reject the extra key on the subsequent Holding(**doc) re-read).
    computed.pop("_realized_lots", None)

    # Update transactions[i].remaining_quantity for each BUY
    by_id = {lot["transaction_id"]: lot["quantity"] for lot in remaining_lots}
    for tx in transactions:
        if tx["type"] == "BUY":
            new_remaining = by_id.get(tx["_id"], Decimal("0"))
            txs_coll.update_one(
                {"_id": tx["_id"]},
                {
                    "$set": _convert_decimals_to_decimal128(
                        {
                            "remaining_quantity": new_remaining,
                            "updated_at": utcnow(),
                        }
                    )
                },
            )

    # Get / fetch metadata for display
    existing = holdings_coll.find_one({"isin": isin, "deleted_at": None})
    if existing and existing.get("name"):
        meta = {
            "name": existing.get("name", ""),
            "sector": existing.get("sector", ""),
            "industry": existing.get("industry", ""),
            "symbol": existing.get("symbol") or transactions[0]["symbol"],
            "exchange": existing.get("exchange")
            or transactions[0].get("exchange", "NSE"),
        }
    else:
        # First time — get name from NSE master (reliable),
        # sector/industry from yfinance (NSE doesn't publish those)
        first_tx = transactions[0]
        symbol = first_tx["symbol"]
        exchange = first_tx.get("exchange", "NSE")
        nse_doc = Collections.instruments().find_one(
            {"exchange": exchange, "symbol": symbol},
            {"name": 1, "_id": 0},
        )
        yf_meta = fetch_metadata(symbol, exchange)
        meta = {
            "name": (nse_doc and nse_doc.get("name")) or yf_meta.get("name", ""),
            "sector": yf_meta.get("sector", ""),
            "industry": yf_meta.get("industry", ""),
            "symbol": symbol,
            "exchange": exchange,
        }

    if computed["quantity"] == 0:
        # Fully exited — record (or update) the soft-deleted final state.
        # Filter on isin only (no deleted_at constraint) so this works whether
        # we're soft-deleting an active row, refreshing an already-deleted row,
        # or creating a fresh soft-deleted record (e.g., post --wipe-live).
        update_doc = _convert_decimals_to_decimal128(
            {
                **computed,
                **meta,
                "last_recomputed_at": utcnow(),
                "updated_at": utcnow(),
                "deleted_at": utcnow(),
            }
        )
        set_on_insert = _convert_decimals_to_decimal128(
            {
                "isin": isin,
                "_schema_version": 1,
                "created_at": utcnow(),
                "user_notes": "",
                "thesis": "",
                "tags": [],
                "stop_loss": None,
                "target_price": None,
                "alert_on": ["stop_loss", "target", "earnings", "news", "52w_high"],
            }
        )
        holdings_coll.update_one(
            {"isin": isin},
            {"$set": update_doc, "$setOnInsert": set_on_insert},
            upsert=True,
        )
        return None

    # ── Active branch (F2 fix, Chat 5.5+) ────────────────────────────────────
    # Two changes vs. pre-fix behavior:
    #
    # 1. Filter is {"isin": isin} (no deleted_at constraint) instead of
    #    {"isin": isin, "deleted_at": None}. This lets a soft-deleted doc
    #    reactivate cleanly via $set "deleted_at": None instead of leaving
    #    the stale soft-deleted doc orphaned and inserting a parallel
    #    active doc (the pre-fix behavior — F2 root bug).
    #
    # 2. Pre-fetch user-editable fields from the most-recently-updated doc
    #    BEFORE the cleanup delete_many, so multi-cycle re-entries preserve
    #    user_notes / thesis / tags / stop_loss / target_price / alert_on.
    #
    # 3. delete_many of stale soft-deleted docs (legacy F2 bug state where
    #    a previous re-entry created a parallel active doc). The active
    #    doc now carries cumulative realized_pnl across all cycles via
    #    FIFO replay, so soft-deleted snapshots are redundant.

    existing_for_user_fields = (
        holdings_coll.find_one(
            {"isin": isin},
            sort=[("updated_at", -1)],
            projection={
                "user_notes": 1,
                "thesis": 1,
                "tags": 1,
                "stop_loss": 1,
                "target_price": 1,
                "alert_on": 1,
                "created_at": 1,
                "_id": 0,
            },
        )
        or {}
    )

    holdings_coll.delete_many({"isin": isin, "deleted_at": {"$ne": None}})

    update_doc = _convert_decimals_to_decimal128(
        {
            **computed,
            **meta,
            "deleted_at": None,
            "last_recomputed_at": utcnow(),
            "updated_at": utcnow(),
        }
    )
    set_on_insert = _convert_decimals_to_decimal128(
        {
            "isin": isin,
            "_schema_version": 1,
            "created_at": existing_for_user_fields.get("created_at") or utcnow(),
            "user_notes": existing_for_user_fields.get("user_notes", ""),
            "thesis": existing_for_user_fields.get("thesis", ""),
            "tags": existing_for_user_fields.get("tags", []),
            "stop_loss": existing_for_user_fields.get("stop_loss"),
            "target_price": existing_for_user_fields.get("target_price"),
            "alert_on": existing_for_user_fields.get("alert_on")
            or ["stop_loss", "target", "earnings", "news", "52w_high"],
        }
    )
    holdings_coll.update_one(
        {"isin": isin},
        {"$set": update_doc, "$setOnInsert": set_on_insert},
        upsert=True,
    )
    doc = holdings_coll.find_one({"isin": isin, "deleted_at": None})
    return Holding(**doc) if doc else None


def preview_sell(
    isin: str,
    sell_quantity: Decimal,
    sell_price: Decimal,
    sell_fees: Decimal = Decimal("0"),
) -> dict:
    """Simulate a SELL transaction (no DB writes) and return what would happen.

    Used by the UI's Sell sheet to show "if you sell X at ₹Y, you'll realize ₹Z"
    before the user confirms.

    Replays all transactions to derive current open lots (FIFO + SPLIT + BONUS),
    then walks those lots to compute what this hypothetical SELL would consume.
    No DB writes.

    F3 fix (Chat 5.5+): SPLIT/BONUS now mutate lot quantities/prices via
        _apply_split_or_bonus_to_dict_lots (mirrors _fifo_replay semantics).
        Pre-fix, splits/bonuses were silently skipped, producing wrong preview
        numbers for any stock with a corporate action in its history.

    F5 fix (Chat 5.5+): Per-lot realized P&L now includes fee normalization
        on both the buy side (lot.fees / lot.qty) and the proposed sell side
        (sell_fees / sell_qty), mirroring _fifo_replay. Pre-fix, preview
        ignored fees entirely, producing a realized_pnl preview that didn't
        match the value actually persisted on submit.

    Returns:
        {
          "valid": True,
          "realized_pnl": Decimal,
          "remaining_qty": Decimal,
          "remaining_invested": Decimal,
          "remaining_avg_cost": Decimal,
          "fully_exits": bool,
          "lots_consumed": list[dict],
        }
        Or:
        {"valid": False, "error": "..."}
    """
    if sell_quantity <= 0:
        return {"valid": False, "error": "Quantity must be positive"}
    if sell_price <= 0:
        return {"valid": False, "error": "Price must be positive"}
    if sell_fees < 0:
        return {"valid": False, "error": "Fees cannot be negative"}

    transactions = list(
        Collections.transactions()
        .find({"isin": isin, "deleted_at": None})
        # #77 U6-c: same (trade_date, created_at) tie-break as the real replay
        # so the preview consumes lots in the identical order to the SELL.
        .sort([("trade_date", ASCENDING), ("created_at", ASCENDING)])
    )

    if not transactions:
        return {"valid": False, "error": f"No transactions found for {isin}"}

    # Reconstruct current open lots by replaying transactions FIFO.
    # Lot dict carries qty, price, fees, trade_date — fees needed for F5 fix.
    open_lots: list[dict] = []
    for tx in transactions:
        tx_type = tx.get("type")
        qty = _to_decimal(tx.get("quantity"))
        price = _to_decimal(tx.get("price"))
        fees = _to_decimal(tx.get("total_fees", 0))
        trade_date = tx.get("trade_date")
        if tx_type == "BUY":
            open_lots.append(
                {
                    "trade_date": trade_date,
                    "qty": qty,
                    "price": price,
                    "fees": fees,
                }
            )
        elif tx_type == "SELL":
            # Consume from oldest lots first; deplete fees proportionally
            qty_to_consume = qty
            for lot in open_lots:
                if qty_to_consume <= 0:
                    break
                consumed = min(qty_to_consume, lot["qty"])
                if lot["qty"] > 0:
                    lot["fees"] -= lot["fees"] * consumed / lot["qty"]
                lot["qty"] -= consumed
                qty_to_consume -= consumed
            # Drop fully-consumed lots
            open_lots = [lot for lot in open_lots if lot["qty"] > 0]
        elif tx_type in ("SPLIT", "BONUS"):
            # F3 fix: apply corporate action to lot quantities/prices in place
            _apply_split_or_bonus_to_dict_lots(
                open_lots, tx_type, tx.get("corporate_action")
            )

    available_qty = sum((lot["qty"] for lot in open_lots), start=Decimal("0"))
    if available_qty <= 0:
        return {"valid": False, "error": "Holding is already fully exited"}

    if sell_quantity > available_qty:
        return {
            "valid": False,
            "error": f"Not enough quantity. Available: {available_qty}, requested: {sell_quantity}",
        }

    # Now simulate the new SELL: walk open lots FIFO with fee normalization (F5 fix).
    sell_proceeds_per_share = sell_price - (
        sell_fees / sell_quantity if sell_quantity > 0 else Decimal("0")
    )
    qty_to_sell = sell_quantity
    realized_pnl = Decimal("0")
    lots_consumed: list[dict] = []

    # Working copy so we can compute remaining invested afterwards
    working = [
        {
            "trade_date": lot["trade_date"],
            "qty": lot["qty"],
            "price": lot["price"],
            "fees": lot["fees"],
        }
        for lot in open_lots
    ]

    for lot in working:
        if qty_to_sell <= 0:
            break
        if lot["qty"] <= 0:
            continue
        consumed = min(qty_to_sell, lot["qty"])
        buy_cost_per_share = lot["price"] + (
            lot["fees"] / lot["qty"] if lot["qty"] > 0 else Decimal("0")
        )
        lot_realized = (
            consumed * (sell_proceeds_per_share - buy_cost_per_share)
        ).quantize(Decimal("0.01"))
        realized_pnl += lot_realized
        lots_consumed.append(
            {
                "trade_date": (
                    lot["trade_date"].isoformat()
                    if hasattr(lot["trade_date"], "isoformat")
                    else str(lot["trade_date"])
                ),
                "qty_consumed": consumed,
                "cost_per_share": lot["price"],
                "realized_pnl": lot_realized,
            }
        )
        # Deplete fees proportionally on the working lot too
        if lot["qty"] > 0:
            lot["fees"] -= lot["fees"] * consumed / lot["qty"]
        lot["qty"] -= consumed
        qty_to_sell -= consumed

    realized_pnl = realized_pnl.quantize(Decimal("0.01"))
    remaining_qty = (available_qty - sell_quantity).quantize(Decimal("0.0001"))
    fully_exits = remaining_qty == 0
    # #77 U6-b: remaining_invested must INCLUDE residual per-lot fees to mirror
    # _fifo_replay (invested = Σ qty*price + Σ fees). The old qty*price-only sum
    # made the preview's remaining avg-cost diverge from the value the SELL
    # actually persists whenever any surviving lot carried fees.
    remaining_invested = sum(
        (
            (lot["qty"] * lot["price"] + lot["fees"]).quantize(Decimal("0.01"))
            for lot in working
            if lot["qty"] > 0
        ),
        start=Decimal("0"),
    )
    remaining_avg_cost = (
        (remaining_invested / remaining_qty).quantize(Decimal("0.0001"))
        if remaining_qty > 0
        else Decimal("0")
    )

    return {
        "valid": True,
        "realized_pnl": realized_pnl,
        "remaining_qty": remaining_qty,
        "remaining_invested": remaining_invested,
        "remaining_avg_cost": remaining_avg_cost,
        "fully_exits": fully_exits,
        "lots_consumed": lots_consumed,
    }


def validate_replay(transactions: list[dict]) -> tuple[bool, str | None]:
    """Run a FIFO simulation over the proposed transaction set and verify no
    impossible state arises (i.e.

    SELL > available qty at any chronological point).

    Returns (True, None) if valid; (False, "human-readable reason") if not.

    Used by the edit/delete endpoints to reject changes that would create a
    mathematically/legally invalid holding history (selling shares you don't own).

    F4 fix (Chat 5.5+): SPLIT/BONUS now mutate lot quantities via
        _apply_split_or_bonus_to_dict_lots (mirrors _fifo_replay semantics).
        Pre-fix, splits/bonuses were silently skipped, so a post-split SELL
        that legitimately uses split-adjusted quantities would be rejected
        as an oversell.
    """
    from datetime import datetime as _dt

    open_lots: list[dict] = []

    # Sort chronologically; ties broken by created_at if available
    def _naive(d):
        """Strip tzinfo so all comparisons are naive (Mongo stores naive dates)."""
        if d is None:
            return _dt.min
        if hasattr(d, "tzinfo") and d.tzinfo is not None:
            return d.replace(tzinfo=None)
        return d

    sorted_txs = sorted(
        transactions,
        key=lambda t: (_naive(t.get("trade_date")), _naive(t.get("created_at"))),
    )

    for tx in sorted_txs:
        if tx.get("deleted_at"):
            continue
        tx_type = tx.get("type")
        qty = _to_decimal(tx.get("quantity"))
        price = _to_decimal(tx.get("price"))
        trade_date = tx.get("trade_date")
        if tx_type == "BUY":
            open_lots.append({"qty": qty, "price": price})
        elif tx_type == "SELL":
            available = sum((lot["qty"] for lot in open_lots), Decimal("0"))
            if qty > available:
                date_str = (
                    trade_date.strftime("%d-%b-%Y")
                    if hasattr(trade_date, "strftime")
                    else str(trade_date)
                )
                return (
                    False,
                    f"SELL on {date_str} would sell {qty} shares but only {available} "
                    f"are available at that point in the timeline. "
                    f"Edit blocked to prevent an impossible holding state.",
                )
            qty_to_consume = qty
            for lot in open_lots:
                if qty_to_consume <= 0:
                    break
                consumed = min(qty_to_consume, lot["qty"])
                lot["qty"] -= consumed
                qty_to_consume -= consumed
            open_lots = [lot for lot in open_lots if lot["qty"] > 0]
        elif tx_type in ("SPLIT", "BONUS"):
            # F4 fix: apply corporate action to lot quantities in place so
            # post-CA SELLs validate against split-adjusted available qty.
            _apply_split_or_bonus_to_dict_lots(
                open_lots, tx_type, tx.get("corporate_action")
            )
        # DIVIDEND: payout, no lot mutation; ignore.
    return (True, None)
