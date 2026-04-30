"""Holding computation service.

Holdings are derived state — never written to directly. After any change to
`transactions` for a stock, call recompute_holding(isin) to rebuild the holding
from scratch using FIFO accounting.

This is intentionally simple (replay all transactions every time) rather than
incremental (apply just the new transaction). A typical stock has <1000
transactions in its lifetime; replay takes <50ms. Simplicity > micro-optimization.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from pymongo import ASCENDING

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


def _fifo_replay(transactions: Iterable[dict]) -> dict:
    """Replay transactions chronologically with FIFO depletion.

    Returns a dict of computed fields ready to merge into the Holding doc.
    """
    lots: deque[_Lot] = deque()
    realized_pnl = Decimal("0")
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
            lots.append(
                _Lot(
                    transaction_id=tx["_id"],
                    quantity=qty,
                    price=price,
                    fees=fees,
                    trade_date=trade_date,
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


def recompute_holding(isin: str) -> Holding | None:
    """Rebuild the holding for `isin` from its transactions.

    Returns the recomputed Holding (after upsert). If no transactions exist,
    soft-deletes any existing holding and returns None.
    """
    txs_coll = Collections.transactions()
    holdings_coll = Collections.holdings()

    # Pull all non-deleted transactions for this ISIN, oldest first
    transactions = list(
        txs_coll.find(
            {"isin": isin, "deleted_at": None},
        ).sort("trade_date", ASCENDING)
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
        update_doc = _convert_decimals_to_decimal128({
            **computed,
            **meta,
            "last_recomputed_at": utcnow(),
            "updated_at": utcnow(),
            "deleted_at": utcnow(),
        })
        set_on_insert = _convert_decimals_to_decimal128({
            "isin": isin,
            "_schema_version": 1,
            "created_at": utcnow(),
            "user_notes": "",
            "thesis": "",
            "tags": [],
            "stop_loss": None,
            "target_price": None,
            "alert_on": ["stop_loss", "target", "earnings", "news", "52w_high"],
        })
        holdings_coll.update_one(
            {"isin": isin},
            {"$set": update_doc, "$setOnInsert": set_on_insert},
            upsert=True,
        )
        return None

    # Upsert active holding
    update_doc = _convert_decimals_to_decimal128(
        {
            **computed,
            **meta,
            "last_recomputed_at": utcnow(),
            "updated_at": utcnow(),
        }
    )
    set_on_insert = _convert_decimals_to_decimal128(
        {
            "isin": isin,
            "_schema_version": 1,
            "created_at": utcnow(),
            "deleted_at": None,
            "user_notes": "",
            "thesis": "",
            "tags": [],
            "stop_loss": None,
            "target_price": None,
            "alert_on": ["stop_loss", "target", "earnings", "news", "52w_high"],
        }
    )

    holdings_coll.update_one(
        {"isin": isin, "deleted_at": None},
        {"$set": update_doc, "$setOnInsert": set_on_insert},
        upsert=True,
    )

    doc = holdings_coll.find_one({"isin": isin, "deleted_at": None})
    return Holding(**doc) if doc else None
