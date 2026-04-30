"""Instrument service — Mongo-backed ISIN lookup and Kite CSV refresh.

Three responsibilities:
  1. lookup_isin(symbol, exchange, broker) — single point lookup
  2. bulk_lookup_isins(symbols, exchange, broker) — efficient batch lookup
  3. refresh_from_kite() — full refresh of `instruments` from Kite's public CSV
  4. add_override(...) / list_overrides() / delete_override() — manage overrides
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone
from typing import Literal

import requests
from pymongo import UpdateOne

from app.db.client import Collections

log = logging.getLogger(__name__)

NSE_EQUITY_LIST_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
HTTP_TIMEOUT_SEC = 60

# NSE blocks bots; send a real browser User-Agent
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/csv,application/csv,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}

BrokerType = Literal["ICICI", "ZERODHA", "OTHER"]

# ── Lookups ──────────────────────────────────────────────────────────────────


def lookup_isin(
    symbol: str,
    exchange: str = "NSE",
    broker: BrokerType = "ICICI",
) -> str | None:
    """Look up the ISIN for a single (broker, symbol, exchange).

    Resolution order:
      1. Apply any broker-specific override (broker:source_symbol → target)
      2. Direct match in `instruments` (exchange, symbol)
    """
    sym = symbol.upper()
    exch = exchange.upper()

    # 1. Try override
    override = Collections.symbol_overrides().find_one(
        {
            "source_broker": broker,
            "source_symbol": sym,
        }
    )
    if override:
        target_exch = override["target_exchange"]
        target_sym = override["target_symbol"]
        instr = Collections.instruments().find_one(
            {"exchange": target_exch, "symbol": target_sym},
            {"isin": 1, "_id": 0},
        )
        if instr:
            return instr["isin"]
        log.warning(
            "Override %s:%s → %s:%s, but target not found in instruments",
            broker,
            sym,
            target_exch,
            target_sym,
        )

    # 2. Direct lookup
    instr = Collections.instruments().find_one(
        {"exchange": exch, "symbol": sym},
        {"isin": 1, "_id": 0},
    )
    if instr:
        return instr["isin"]

    # 3. NSE fallback for BSE lookups
    if exch == "BSE":
        instr = Collections.instruments().find_one(
            {"exchange": "NSE", "symbol": sym},
            {"isin": 1, "_id": 0},
        )
        if instr:
            log.info("BSE fallback: resolved %s via NSE master", sym)
            return instr["isin"]

    return None


def lookup_metadata(
    symbol: str,
    exchange: str = "NSE",
    broker: BrokerType = "ICICI",
) -> dict | None:
    """Return full instrument metadata (name, isin, exchange, lot_size, etc.)
    for a single (broker, symbol, exchange).

    Same resolution order as lookup_isin: override → direct match.
    """
    sym = symbol.upper()
    exch = exchange.upper()

    # 1. Try override
    override = Collections.symbol_overrides().find_one(
        {
            "source_broker": broker,
            "source_symbol": sym,
        }
    )
    if override:
        target_exch = override["target_exchange"]
        target_sym = override["target_symbol"]
        return Collections.instruments().find_one(
            {"exchange": target_exch, "symbol": target_sym},
        )

    # 2. Direct lookup
    instr = Collections.instruments().find_one(
        {"exchange": exch, "symbol": sym},
    )
    if instr:
        return instr

    # 3. NSE fallback for BSE
    if exch == "BSE":
        return Collections.instruments().find_one(
            {"exchange": "NSE", "symbol": sym},
        )

    return None


def bulk_lookup_isins(
    symbols: list[str],
    exchange: str = "NSE",
    broker: BrokerType = "ICICI",
) -> dict[str, str | None]:
    """Resolve many symbols in (typically) 2 round-trips.

    Returns: {input_symbol_uppercased: isin_or_None}
    """
    if not symbols:
        return {}

    upper_syms = [s.upper() for s in symbols]
    results: dict[str, str | None] = {s: None for s in upper_syms}

    # 1. Pull all overrides matching any of these symbols, for the given broker
    override_docs = list(
        Collections.symbol_overrides().find(
            {
                "source_broker": broker,
                "source_symbol": {"$in": upper_syms},
            }
        )
    )
    overrides_by_input = {o["source_symbol"]: o for o in override_docs}

    # 2. Split into "look up via override target" vs "look up directly"
    direct_targets: list[
        tuple[str, str]
    ] = []  # (input_sym, target_sym) for direct lookups
    override_targets: list[
        tuple[str, str, str]
    ] = []  # (input_sym, target_exch, target_sym)

    for s in upper_syms:
        if s in overrides_by_input:
            o = overrides_by_input[s]
            override_targets.append((s, o["target_exchange"], o["target_symbol"]))
        else:
            direct_targets.append((s, s))

    # 3. ONE bulk query for direct lookups (all on same exchange)
    # 3. ONE bulk query for direct lookups (all on same exchange)
    if direct_targets:
        direct_syms = [t[1] for t in direct_targets]
        direct_docs = Collections.instruments().find(
            {"exchange": exchange.upper(), "symbol": {"$in": direct_syms}},
            {"symbol": 1, "isin": 1, "_id": 0},
        )
        isin_by_sym = {d["symbol"]: d["isin"] for d in direct_docs}
        for input_sym, target_sym in direct_targets:
            results[input_sym] = isin_by_sym.get(target_sym)

        # 3b. NSE fallback for any unresolved BSE lookups
        # (ISIN is exchange-agnostic; same instrument may be dual-listed.
        #  We only ingest NSE master, so unresolved BSE symbols may exist there.)
        if exchange.upper() == "BSE":
            unresolved_syms = [
                target_sym
                for input_sym, target_sym in direct_targets
                if results.get(input_sym) is None
            ]
            if unresolved_syms:
                fallback_docs = Collections.instruments().find(
                    {"exchange": "NSE", "symbol": {"$in": unresolved_syms}},
                    {"symbol": 1, "isin": 1, "_id": 0},
                )
                fallback_isin_by_sym = {d["symbol"]: d["isin"] for d in fallback_docs}
                for input_sym, target_sym in direct_targets:
                    if (
                        results.get(input_sym) is None
                        and target_sym in fallback_isin_by_sym
                    ):
                        results[input_sym] = fallback_isin_by_sym[target_sym]
                        log.info("BSE fallback: resolved %s via NSE master", target_sym)
    # 4. Resolve overridden targets (typically very few — individual queries are fine)
    for input_sym, target_exch, target_sym in override_targets:
        instr = Collections.instruments().find_one(
            {"exchange": target_exch, "symbol": target_sym},
            {"isin": 1, "_id": 0},
        )
        results[input_sym] = instr["isin"] if instr else None

    return results


# ── Refresh from Kite ────────────────────────────────────────────────────────


def fetch_nse_equity_csv() -> str:
    """Download NSE's official equity master (~2500 NSE-listed stocks)."""
    log.info("Downloading NSE equity master from %s", NSE_EQUITY_LIST_URL)
    response = requests.get(
        NSE_EQUITY_LIST_URL,
        headers=_BROWSER_HEADERS,
        timeout=HTTP_TIMEOUT_SEC,
    )
    response.raise_for_status()
    log.info("Downloaded %d bytes", len(response.content))
    return response.text


def parse_equity_rows(csv_text: str) -> list[dict]:
    """Parse NSE EQUITY_L.csv → instrument dicts.

    NSE columns (with leading spaces — they're in the actual file):
      SYMBOL, NAME OF COMPANY, SERIES, DATE OF LISTING,
      PAID UP VALUE, MARKET LOT, ISIN NUMBER, FACE VALUE
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    rows: list[dict] = []
    skipped = 0

    for raw_row in reader:
        # NSE's column names have inconsistent leading/trailing whitespace
        row = {k.strip(): (v.strip() if v else "") for k, v in raw_row.items()}

        symbol = row.get("SYMBOL", "").upper()
        isin = row.get("ISIN NUMBER", "").upper()
        series = row.get("SERIES", "").upper()
        name = row.get("NAME OF COMPANY", "")

        # Filter to actively-traded equity series (EQ, BE, BZ, etc.)
        # Skip rights issues (RR), partly-paid (PP), etc.
        if not symbol or not isin:
            skipped += 1
            continue
        if len(isin) != 12 or not isin.isalnum():
            skipped += 1
            continue
        if series not in ("EQ", "BE", "BZ", "SM", "ST", "IL"):
            skipped += 1
            continue

        try:
            lot_size = int(float(row.get("MARKET LOT") or 1))
        except (ValueError, TypeError):
            lot_size = 1

        rows.append(
            {
                "exchange": "NSE",
                "symbol": symbol,
                "isin": isin,
                "name": name,
                "instrument_type": "EQ",
                "segment": series,  # NSE uses series codes (EQ, BE, etc.)
                "lot_size": lot_size,
                "tick_size": 0.05,  # NSE default tick for equity
                "source": "nse_official",
                "refreshed_at": datetime.now(timezone.utc),
            }
        )

    log.info("Parsed %d NSE equity rows (skipped %d non-equity)", len(rows), skipped)
    return rows


def refresh_from_nse() -> dict:
    """Download NSE equity master and update `instruments` collection.

    Delta-aware: only writes rows where content actually changed.
    Unchanged rows get a single-field `last_seen_at` update so we know
    they're still listed.

    Returns stats: {inserted, updated, unchanged, delisted_skipped, total}.
    """
    csv_text = fetch_nse_equity_csv()
    new_rows = parse_equity_rows(csv_text)

    if not new_rows:
        log.error("No equity rows parsed — aborting to avoid wiping collection")
        return {
            "status": "no_rows",
            "fetched": 0,
            "inserted": 0,
            "updated": 0,
            "unchanged": 0,
        }

    coll = Collections.instruments()
    now = datetime.now(timezone.utc)

    # Read existing instruments into memory (~50ms for 2.5K docs)
    existing_docs = {
        (d["exchange"], d["symbol"]): d
        for d in coll.find(
            {},
            {
                "_id": 0,
                "exchange": 1,
                "symbol": 1,
                "isin": 1,
                "name": 1,
                "instrument_type": 1,
                "segment": 1,
                "lot_size": 1,
                "tick_size": 1,
            },
        )
    }

    # Fields we compare to detect "real" changes (excludes timestamps)
    compare_fields = (
        "isin",
        "name",
        "instrument_type",
        "segment",
        "lot_size",
        "tick_size",
    )

    inserts: list[UpdateOne] = []
    updates: list[UpdateOne] = []
    unchanged_keys: list[tuple[str, str]] = []

    seen_keys: set[tuple[str, str]] = set()
    for row in new_rows:
        key = (row["exchange"], row["symbol"])
        seen_keys.add(key)

        existing = existing_docs.get(key)
        if existing is None:
            # New instrument
            doc = {**row, "last_seen_at": now, "last_changed_at": now}
            inserts.append(
                UpdateOne(
                    {"exchange": key[0], "symbol": key[1]}, {"$set": doc}, upsert=True
                )
            )
            continue

        # Compare meaningful fields
        changed = any(existing.get(f) != row.get(f) for f in compare_fields)
        if changed:
            doc = {**row, "last_seen_at": now, "last_changed_at": now}
            updates.append(
                UpdateOne({"exchange": key[0], "symbol": key[1]}, {"$set": doc})
            )
        else:
            unchanged_keys.append(key)

    # Apply changes — splits into separate bulk_write calls for clarity in logs
    inserted_count = updated_count = 0

    if inserts:
        result = coll.bulk_write(inserts, ordered=False)
        inserted_count = result.upserted_count
    if updates:
        result = coll.bulk_write(updates, ordered=False)
        updated_count = result.modified_count

    # Cheap "still alive" touch for unchanged rows — single-field write
    if unchanged_keys:
        # Use $or with manageable batch size for the WHERE clause
        chunk_size = 500
        for i in range(0, len(unchanged_keys), chunk_size):
            batch = unchanged_keys[i : i + chunk_size]
            coll.update_many(
                {"$or": [{"exchange": e, "symbol": s} for e, s in batch]},
                {"$set": {"last_seen_at": now}},
            )

    # Find any DB instruments not in this CSV — they may be delisted
    db_keys = set(existing_docs.keys())
    not_seen_today = db_keys - seen_keys

    total = coll.estimated_document_count()
    log.info(
        "Refresh complete: %d inserted, %d updated, %d unchanged, %d not in today's CSV (potentially delisted), %d total",
        inserted_count,
        updated_count,
        len(unchanged_keys),
        len(not_seen_today),
        total,
    )

    return {
        "status": "ok",
        "fetched": len(new_rows),
        "inserted": inserted_count,
        "updated": updated_count,
        "unchanged": len(unchanged_keys),
        "not_in_today_csv": len(not_seen_today),
        "total_in_collection": total,
    }


# ── Override management ──────────────────────────────────────────────────────


def add_override(
    source_symbol: str,
    target_symbol: str,
    target_exchange: str = "NSE",
    source_broker: BrokerType = "ICICI",
    notes: str = "",
) -> dict:
    """Add or update a broker symbol override.

    Validates that the target instrument exists in `instruments` first.
    """
    src_sym = source_symbol.upper()
    tgt_sym = target_symbol.upper()
    tgt_exch = target_exchange.upper()

    target = Collections.instruments().find_one(
        {"exchange": tgt_exch, "symbol": tgt_sym},
        {"_id": 1, "name": 1},
    )
    if not target:
        raise ValueError(
            f"Cannot create override: target {tgt_exch}:{tgt_sym} not found in instruments. "
            f"Run refresh_from_kite() to update the instruments collection."
        )

    from app.models.symbol_override import SymbolOverride

    override = SymbolOverride(
        source_broker=source_broker,
        source_symbol=src_sym,
        target_exchange=tgt_exch,
        target_symbol=tgt_sym,
        notes=notes,
    )
    payload = override.model_dump()
    payload["updated_at"] = datetime.now(timezone.utc)

    Collections.symbol_overrides().update_one(
        {"source_broker": source_broker, "source_symbol": src_sym},
        {"$set": payload},
        upsert=True,
    )
    log.info(
        "Added override: %s:%s → %s:%s (%s)",
        source_broker,
        src_sym,
        tgt_exch,
        tgt_sym,
        target.get("name", ""),
    )
    return {
        "source_broker": source_broker,
        "source_symbol": src_sym,
        "target_exchange": tgt_exch,
        "target_symbol": tgt_sym,
        "target_name": target.get("name", ""),
    }


def list_overrides(source_broker: BrokerType | None = None) -> list[dict]:
    """List all overrides (optionally filtered by broker)."""
    query = {"source_broker": source_broker} if source_broker else {}
    return list(Collections.symbol_overrides().find(query, {"_id": 0}))


def delete_override(source_broker: BrokerType, source_symbol: str) -> bool:
    """Remove an override. Returns True if a doc was deleted."""
    result = Collections.symbol_overrides().delete_one(
        {
            "source_broker": source_broker,
            "source_symbol": source_symbol.upper(),
        }
    )
    return result.deleted_count > 0
