
# AI Stock Advisor — Backend

Personal portfolio advisory tool for NSE equities. Strictly **advisory** — the system never executes trades. The user trades manually in their broker (ICICI Direct), then records transactions via this API.

This repo is the FastAPI + MongoDB backend. The frontend lives at [`ai-stock-advisor-frontend`](https://github.com/doshisahil95/ai-stock-advisor-frontend).

## What it does today

A complete portfolio dashboard with full audit trail and tax-correct cost basis:

- **Portfolio computation** — FIFO-based cost basis with full handling of corporate actions (splits, bonuses, demergers including Section 49(2C) cost apportionment)
- **Live prices** — yfinance EOD bars + 15-min intraday refresh during market hours
- **Reconciliation tracking** — daily auto-snapshots + manual checks against the broker, drift alerts via push notification + email
- **Cost-basis audit trail** — every IT-Act-driven divergence between our cost and the broker's is documented with calculation, rationale, and source documents (CA-facing)
- **Transaction edit/delete** — every change is captured in an append-only audit log; FIFO replay validates that edits don't create impossible holding states
- **Buy/sell with FIFO preview** — show realized P&L before confirming a sell

## Stack

- **Python 3.12**, [`uv`](https://github.com/astral-sh/uv) for packaging
- **FastAPI** + Pydantic v2
- **MongoDB Atlas M10** (`ap-south-1`)
- **yfinance** for OHLCV (EOD + intraday)
- **Anthropic Claude** + **Tavily** (provisioned for Phase 2)
- **Resend** (transactional email) + **ntfy** (push notifications)
- Hosted on AWS EC2 t3.micro (`ap-south-1`), accessed only via Tailscale

## Architecture

```
+----------+     yfinance     +-----------+     +---------+     +----------+
| ICICI    |    (EOD + 15m)   | EC2:8000  |<--->| Mongo   |<-->| Frontend |
| (manual) | ---------------> | FastAPI   |     | Atlas   |    | Next.js  |
+----------+                  +-----------+     | M10     |    | EC2:3000 |
     |                              ^           +---------+    +----------+
     | (corp actions, broker        |                              ^
     |  reconciliation)             | (cron)                       | (browser
     v                              v                              | over Tailscale)
  Manual ingestion via       scripts/refresh_*                     |
  scripts/ + UI              scripts/take_*                        |
                                                                   |
                              +----------+                         |
                              | Resend   |<-- alerts ------+       |
                              | + ntfy   |                 |       |
                              +----------+                 |       |
                                                  drift detection  |
```

For the full data-flow reference (collections, invariants, gotchas), see [`docs/data_flow.md`](docs/data_flow.md).

## API Surface

### Portfolio
- `GET /portfolio/summary` — totals, sector breakdown, top movers, broker-view P&L
- `GET /portfolio/holdings` — annotated list with live prices, P&L, day gain
- `GET /portfolio/holdings/{isin}` — single holding with all metadata
- `GET /portfolio/holdings/{isin}/history` — OHLCV chart data
- `GET /portfolio/holdings/{isin}/transactions` — all txns for one stock
- `POST /portfolio/holdings` — record a BUY (auto-resolves ISIN via NSE master)
- `POST /portfolio/holdings/{isin}/sell` — record a SELL (FIFO depletion)
- `POST /portfolio/holdings/{isin}/preview-sell` — simulate a SELL without writing
- `PATCH /portfolio/holdings/{isin}` — update thesis, notes, stop_loss, target_price, tags

### Transactions
- `GET /transactions/search` — filter by symbol (prefix), type, date range, paginated
- `GET /transactions/{id}` — fetch one
- `PATCH /transactions/{id}` — edit (validated against impossible state, audit-logged, recomputes holding)
- `DELETE /transactions/{id}` — soft-delete (validated, audit-logged, recomputes holding)
- `GET /transactions/audit/recent` — append-only edit/delete log
- `GET /transactions/{id}/audit` — audit history for one transaction

### Reconciliation
- `GET /reconciliation/latest` — most recent snapshot (filterable by type)
- `GET /reconciliation/history` — last N snapshots
- `POST /reconciliation/snapshot` — manual snapshot (your ICICI numbers + ours, with optional baseline accept)
- `POST /reconciliation/auto-snapshot` — system-side only (cron entry point)

### Cost basis
- `GET /cost-basis/adjustments` — full audit list of IT-Act-driven divergences (Section 49(2C), 47(vid), etc.)

### Instruments
- `GET /instruments/search` — symbol/ISIN lookup against NSE master

## Collections

| Collection | Holds |
|---|---|
| `transactions` | Every BUY/SELL/SPLIT/BONUS/DIVIDEND |
| `transactions_staging` | CSV imports awaiting promotion |
| `transactions_audit` | Append-only edit/delete log |
| `holdings` | Computed current state per ISIN; soft-deleted on full exit |
| `instruments` | NSE master (~2,365 symbols, ISIN, sector) |
| `prices_daily` | EOD OHLCV bars |
| `prices_intraday` | 15-min snapshots during market hours |
| `reconciliation_snapshots` | ICICI-vs-our comparison snapshots |
| `cost_basis_adjustments` | IT-Act-driven divergences |
| `user_profile` | Preferences, reconciliation baseline |

## Critical invariants

These MUST hold or computed P&L is wrong:

1. **Transactions are immutable except via audited edit/delete.** PATCH and DELETE write to `transactions_audit` BEFORE applying. `validate_replay()` rejects any change that would create a negative-quantity moment in the timeline.
2. **`recompute_holding(isin)` is the only authoritative way to update a holding.** Replays all non-deleted transactions FIFO from scratch. Idempotent.
3. **`holdings.deleted_at = None` filter is universal.** Soft-deleted (fully-exited) holdings are excluded from all aggregations.
4. **Cost basis = IT-Act-correct, not broker-nominal.** Our `invested_amount` reflects post-49(2C) cost. The broker's "invested" is recoverable by adding `cost_basis_adjustments` back — exposed as `totals.broker_invested`.
5. **`prices_intraday` writes are append-only within a day.** Each cron run inserts a new doc; we never overwrite. `bulk_get_latest_prices` prefers today's intraday, falls back to EOD.

## Cron jobs (on EC2)

| Schedule (IST) | Script | Purpose |
|---|---|---|
| 03:00 daily | `refresh_instruments.py` | NSE master refresh |
| 19:00 weekdays | `refresh_prices.py` | EOD prices after market close |
| Every 15 min, 09:00–15:45 weekdays | `refresh_prices_intraday.py` | Intraday snapshots |
| 19:30 weekdays | `take_reconciliation_snapshot.py` | Auto reconciliation |
| 00:00 Sunday | log truncation | Bound cron logs |

## Local development

Requires `uv`:

```bash
git clone https://github.com/doshisahil95/ai-stock-advisor-backend.git
cd ai-stock-advisor-backend

# Install deps via uv
uv sync

# Configure secrets (ask the maintainer for .env)
cp .env.example .env

# Run locally
PYTHONPATH=. uv run uvicorn app.main:app --reload --port 8000

# Run tests
PYTHONPATH=. uv run pytest tests/
```

## Deployment

EC2 t3.micro runs the API as a systemd service. Pull-and-restart via `~/deploy.sh`:

```bash
# On the EC2 host
~/deploy.sh
sudo systemctl status portfolio-advisor.service
```

Logs:
```bash
sudo journalctl -u portfolio-advisor.service -f
```

## Repository layout

```
app/
├── config/         # settings (env vars, secrets)
├── db/             # Mongo client, collections, indexes
├── models/         # Pydantic schemas
├── routers/        # FastAPI endpoints (portfolio, transactions, reconciliation, etc.)
├── services/       # Business logic (FIFO, recompute, reconciliation, cost basis)
└── main.py
docs/
└── data_flow.md    # Future-self reference for collections + invariants
scripts/
├── refresh_*.py    # Cron entry points for data refresh
├── seed_*.py       # Idempotent seed scripts (cost basis adjustments, etc.)
├── take_*.py       # Reconciliation snapshot cron entry
├── add_manual_transactions.py  # For corp action repair
└── ...
tests/
└── ...
pyproject.toml
```

## What's next (Phase 2)

The advisory dashboard is complete. Phase 2 adds the AI agent layer:

- **2.1** Daily news digest (Tavily + Claude classification, email via Resend)
- **2.2** `/news` page — timeline of stories with summaries
- **2.3** Conversational agent (`/agent`) — natural-language questions about the portfolio with tool access
- **2.4** Alerts — stop-loss/target hits, significant news, via ntfy
- Tavily-driven proactive corp action detection (weekly cron)

## License

Personal project. No license; all rights reserved.
