"""Import ICICI Order Book CSV files into transactions_staging.

Reads all CSVs in the source folder (default ~/Downloads/2022.csv ... 2026.csv),
parses ICICI's column layout, resolves ISINs via the instruments collection,
and writes everything to transactions_staging for review.

NEVER writes to the real `transactions` collection — that's promote_staging.py.

Usage:
    PYTHONPATH=. uv run python scripts/import_orderbooks.py
    PYTHONPATH=. uv run python scripts/import_orderbooks.py --source ~/some/other/folder
    PYTHONPATH=. uv run python scripts/import_orderbooks.py --wipe   # clear staging first
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app.db.client import Collections
from app.models._common import _convert_decimals_to_decimal128
from app.services.instrument_service import bulk_lookup_isins

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)
log = logging.getLogger(__name__)

DEFAULT_SOURCE_DIR = Path.home() / "Downloads"
DEFAULT_FILES = ["2022.csv", "2023.csv", "2024.csv", "2025.csv", "2026.csv"]

# ── ICICI CSV column names (verified against your sample) ────────────────────
COL_DATE = "Date"
COL_STOCK = "Stock"
COL_ACTION = "Action"
COL_QTY = "Qty"
COL_PRICE = "Price"
COL_TRADE_VALUE = "Trade Value"
COL_ORDER_REF = "Order Ref."
COL_SETTLEMENT = "Settlement"
COL_SEGMENT = "Segment"
COL_EXCHANGE = "Exchange"
COL_STT = "STT"
COL_TXN_CHARGES = "Transaction and SEBI Turnover charges"
COL_STAMP_DUTY = "Stamp Duty"
COL_BROKERAGE = "Brokerage + Service Tax"


def _parse_decimal(raw: str | None) -> Decimal:
    if raw is None or raw.strip() == "":
        return Decimal("0")
    cleaned = raw.replace(",", "").replace("₹", "").strip()
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return Decimal("0")


def _parse_date(raw: str) -> datetime:
    """ICICI uses DD-Mon-YY (e.g. '25-Jul-22'). Returns UTC midnight datetime."""
    cleaned = raw.strip()
    # Try several formats
    for fmt in ("%d-%b-%y", "%d-%b-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            naive = datetime.strptime(cleaned, fmt)
            return naive.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {raw!r}")


def _normalize_action(raw: str) -> str:
    """ICICI uses 'Buy'/'Sell' (sometimes with extra whitespace). Returns BUY/SELL."""
    a = (raw or "").strip().upper()
    if a in ("BUY", "B"):
        return "BUY"
    if a in ("SELL", "S"):
        return "SELL"
    raise ValueError(f"Unknown action: {raw!r}")


def _normalize_exchange(raw: str) -> str:
    e = (raw or "").strip().upper()
    if e in ("NSE", "N"):
        return "NSE"
    if e in ("BSE", "B"):
        return "BSE"
    return "NSE"  # default


def parse_csv(path: Path) -> list[dict]:
    """Parse one ICICI CSV. Returns list of normalized dicts (NOT Mongo-shape yet)."""
    rows: list[dict] = []
    with path.open(
        encoding="utf-8-sig"
    ) as f:  # utf-8-sig handles ICICI's BOM if present
        reader = csv.DictReader(f)
        for line_no, raw in enumerate(
            reader, start=2
        ):  # 2 = first data row (after header)
            try:
                # Aggregate all the fee components
                fees = (
                    _parse_decimal(raw.get(COL_STT))
                    + _parse_decimal(raw.get(COL_TXN_CHARGES))
                    + _parse_decimal(raw.get(COL_STAMP_DUTY))
                    + _parse_decimal(raw.get(COL_BROKERAGE))
                )
                rows.append(
                    {
                        "trade_date": _parse_date(raw[COL_DATE]),
                        "settlement_date": None,  # ICICI's "Settlement" column is a cycle code (e.g. "2022140"), not a date
                        "settlement_ref": (raw.get(COL_SETTLEMENT) or "").strip(),
                        "symbol": raw[COL_STOCK].strip().upper(),
                        "exchange": _normalize_exchange(raw.get(COL_EXCHANGE, "NSE")),
                        "type": _normalize_action(raw[COL_ACTION]),
                        "quantity": _parse_decimal(raw[COL_QTY]),
                        "price": _parse_decimal(raw[COL_PRICE]),
                        "trade_value": _parse_decimal(raw.get(COL_TRADE_VALUE)),
                        "total_fees": fees,
                        "source": "csv_import",
                        "source_ref": f"{path.name}:row_{line_no}|order_ref:{raw.get(COL_ORDER_REF, '').strip()}",
                        "notes": "",
                    }
                )
            except (KeyError, ValueError) as exc:
                log.warning("Skipping %s row %d: %s", path.name, line_no, exc)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import ICICI Order Books into staging"
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE_DIR,
        help=f"Source folder (default: {DEFAULT_SOURCE_DIR})",
    )
    parser.add_argument(
        "--wipe",
        action="store_true",
        help="Wipe transactions_staging before importing",
    )
    args = parser.parse_args()

    source_dir = args.source.expanduser().resolve()
    print(f"Source folder: {source_dir}")

    files = [
        source_dir / name for name in DEFAULT_FILES if (source_dir / name).exists()
    ]
    if not files:
        print(f"❌ No CSV files found. Expected: {DEFAULT_FILES}")
        return 1
    print(f"Found {len(files)} files: {[f.name for f in files]}")

    # Wipe staging if requested
    staging = Collections.transactions_staging()
    if args.wipe:
        deleted = staging.delete_many({}).deleted_count
        print(f"Wiped staging: deleted {deleted} previous staging documents")
    elif staging.estimated_document_count() > 0:
        print(f"⚠️  Staging already has {staging.estimated_document_count()} documents.")
        print(f"   Use --wipe to clear, or proceed (rows will be appended).")

    # Parse all CSVs
    all_rows: list[dict] = []
    per_file_counts: dict[str, int] = {}
    for path in files:
        rows = parse_csv(path)
        per_file_counts[path.name] = len(rows)
        all_rows.extend(rows)
        print(f"  ✓ {path.name}: {len(rows)} rows")

    print(f"\nTotal parsed rows: {len(all_rows)}")

    # Resolve ISINs in batch
    distinct_symbols = sorted({r["symbol"] for r in all_rows if r["exchange"] == "NSE"})
    print(f"Resolving ISINs for {len(distinct_symbols)} distinct NSE symbols...")
    isin_map = bulk_lookup_isins(distinct_symbols, exchange="NSE", broker="ICICI")

    # BSE symbols too (if any) — separate batch
    bse_symbols = sorted({r["symbol"] for r in all_rows if r["exchange"] == "BSE"})
    if bse_symbols:
        print(f"Resolving ISINs for {len(bse_symbols)} distinct BSE symbols...")
        bse_isin_map = bulk_lookup_isins(bse_symbols, exchange="BSE", broker="ICICI")
        for s, i in bse_isin_map.items():
            isin_map[s] = i  # NSE+BSE maps merged

    # Annotate rows with ISIN; collect unmapped
    unmapped: dict[str, dict] = {}  # symbol -> {count, total_value}
    for row in all_rows:
        sym = row["symbol"]
        isin = isin_map.get(sym)
        if isin:
            row["isin"] = isin
        else:
            entry = unmapped.setdefault(sym, {"count": 0, "total_value": Decimal("0")})
            entry["count"] += 1
            entry["total_value"] += row["trade_value"]

    # Insert into staging — only rows with ISIN
    valid_rows = [r for r in all_rows if "isin" in r]
    skipped_rows = [r for r in all_rows if "isin" not in r]

    if valid_rows:
        # Add staging-specific metadata
        for r in valid_rows:
            r["_schema_version"] = 1
            r["created_at"] = datetime.now(timezone.utc)
            r["updated_at"] = datetime.now(timezone.utc)
            r["deleted_at"] = None
            # remaining_quantity will be computed during recompute_holding;
            # for BUY rows in staging, initialize to qty (FIFO logic will adjust on promote)
            if r["type"] == "BUY":
                r["remaining_quantity"] = r["quantity"]

        # Convert decimals -> Decimal128 and insert
        docs = [_convert_decimals_to_decimal128(r) for r in valid_rows]
        staging.insert_many(docs, ordered=False)
        print(f"\n✓ Inserted {len(valid_rows)} rows into transactions_staging")

    if skipped_rows:
        print(f"\n⚠️  Skipped {len(skipped_rows)} rows due to unmapped symbols:")
        for sym, stats in sorted(unmapped.items(), key=lambda x: -x[1]["count"]):
            print(
                f"    {sym:15s}  {stats['count']:>3} rows, ₹{stats['total_value']:>12,.2f}"
            )
        print()
        print("To resolve these, add overrides via API:")
        print("  curl -X POST http://127.0.0.1:8000/instruments/overrides \\")
        print("    -H 'Content-Type: application/json' \\")
        print(
            '    -d \'{"source_symbol": "SHK", "target_symbol": "SUDARSCHEM",'
            ' "target_exchange": "NSE", "source_broker": "ICICI",'
            ' "notes": "ICICI internal code"}\''
        )
        print()
        print("Then re-run with --wipe to retry the full import:")
        print("  PYTHONPATH=. uv run python scripts/import_orderbooks.py --wipe")
    else:
        print("\n🎉 All symbols resolved cleanly. No overrides needed.")

    print()
    print("Next: run reconciliation report")
    print("  PYTHONPATH=. uv run python scripts/reconcile_staging.py")

    return 0


if __name__ == "__main__":
    sys.exit(main())
