
# Portfolio Advisor — Data Flow Reference

> Last updated: 2026-05-09. This is a "future-self" doc — open it when you need
> to remember why something works the way it does.

## High-level architecture

```
+----------+     yfinance     +-----------+     +---------+     +----------+
| ICICI    |    (EOD + 15m)   | EC2:8000  |<--->| Mongo   |<-->| Frontend |
| (manual) | ---------------> | FastAPI   |     | Atlas   |    | Next.js  |
+----------+                  +-----------+     | M10     |    | EC2:3000 |
     |                              ^           +---------+    +----------+
     | (corp actions, broker        |                              ^
     |  reconciliation)             |                              |
     v                              |                              |
  Manual ingestion via              | (cron)                       | (browser
  scripts/ + UI                     |                              | over Tailscale)
                                    v                              |
                             scripts/refresh_*                     |
                             scripts/take_*                        |
                                                                   |
                              +----------+                         |
                              | Resend   |<-- alerts ------+       |
                              | + ntfy   |                 |       |
                              +----------+                 |       |
                                                  drift detection  |
```

All access is via Tailscale (no public ingress). EC2 is t3.micro in `ap-south-1`.

---

## Collections

| Collection | Holds | Written by | Read by |
|---|---|---|---|
| `transactions` | Every BUY/SELL/SPLIT/BONUS/DIVIDEND | Manual UI, scripts, `record_buy`/`record_sell` | `_fifo_replay`, `recompute_holding`, search endpoint |
| `transactions_staging` | CSV imports awaiting promotion | Import scripts | `transactions` (after promote) |
| `transactions_audit` | Append-only edit/delete log | `transactions_audit_service.log_change()` | `/transactions/audit/recent` |
| `holdings` | Computed current state per ISIN; soft-deleted on full exit | `recompute_holding()` after every txn change | All read endpoints |
| `instruments` | NSE master (~2,365 symbols, ISIN, exchange, sector) | Daily cron `refresh_instruments.py` | Symbol→ISIN lookup |
| `prices_daily` | EOD OHLCV bars | `refresh_prices.py` (19:00 IST weekdays) | Charts, holdings annotation, drift baseline |
| `prices_intraday` | 15-min snapshots during market hours | `refresh_prices_intraday.py` (every 15m, 09:00–15:45 IST weekdays) | Holdings annotation (preferred over EOD if same-day intraday exists) |
| `reconciliation_snapshots` | ICICI vs our-side comparison snapshots | UI form (manual), cron `take_reconciliation_snapshot.py` (auto, daily 19:30) | Reconciliation page, badge |
| `cost_basis_adjustments` | IT-Act-driven divergences (e.g. Section 49(2C) demerger) | Manual seed `seed_cost_basis_adjustments.py` | `/cost-basis` page, broker-view P&L computation |
| `user_profile` | Preferences, reconciliation_baseline | Manual + reconciliation flow | Various |

---

## Critical invariants

These MUST hold or computed P&L is wrong:

1. **Transactions are immutable except via audited edit/delete.**
   The PATCH and DELETE endpoints in `app/routers/transactions.py` write to
   `transactions_audit` BEFORE applying the change. `validate_replay()` rejects
   any edit/delete that would create a negative-quantity moment in the timeline.

2. **`recompute_holding(isin)` is the only authoritative way to update a holding.**
   Called after every buy/sell/edit/delete. Replays all non-deleted transactions
   FIFO from scratch. Idempotent.

3. **`holdings.deleted_at = None` filter is universal.**
   Soft-deleted (fully-exited) holdings are excluded from all aggregations
   (summary, sector breakdown, top movers). They remain in the DB for audit.

4. **Cost basis = IT-Act-correct, not broker-nominal.**
   Our `holdings.invested_amount` reflects post-49(2C) cost basis (e.g. for
   TMPV demerger, the pre-demerger ₹81,337 is split 68.85% / 31.15%). Broker's
   "invested" is recoverable by adding `cost_basis_adjustments` back —
   exposed as `totals.broker_invested` on `/portfolio/summary`.

5. **`prices_intraday` writes are append-only within a day.**
   Each cron run inserts a new doc; we never overwrite. The intraday-vs-EOD
   selection in `bulk_get_latest_prices` picks the most recent intraday from
   today's UTC window, falling back to EOD.

---

## Cron jobs (on EC2, `crontab -l`)

| Schedule | Script | Purpose |
|---|---|---|
| `0 3 * * *` | `refresh_instruments.py` | Refresh NSE master daily |
| `0 19 * * 1-5` | `refresh_prices.py` | Daily EOD prices (after market close) |
| `*/15 9-15 * * 1-5` | `refresh_prices_intraday.py` | 15-min intraday during market hours |
| `30 19 * * 1-5` | `take_reconciliation_snapshot.py` | Auto reconciliation (system-side) |
| `0 0 * * 0` | log truncation | Keep cron logs bounded |

---

## Adding a new corporate action

When ICICI applies a corporate action that we miss (e.g. a new demerger, bonus,
or split), the workflow is:

1. **Detect** — usually via reconciliation drift alert, or manual ICICI check
2. **Diagnose** — find the corp action on NSE.com (Corporate Information →
   Bonuses/Splits/Demergers) or PIB notices
3. **Add transactions** — use `scripts/add_manual_transactions.py` to apply
   the corp action to your transactions (idempotent, marks via tags)
4. **Recompute** — `recompute_holding(<affected isin>)` runs automatically
5. **Document** — if the action creates a tax-basis vs broker-basis divergence
   (e.g. Section 49(2C) demerger), add an entry to
   `scripts/seed_cost_basis_adjustments.py` and re-run the seed
6. **Reconcile** — take a fresh manual reconciliation snapshot to confirm
   the new state matches ICICI's updated portfolio

---

## When realized P&L for a closed FY changes

This happens only via transaction edit/delete. The audit log is the source of
truth: `/transactions/audit/recent` shows every change with before/after,
reason, timestamp.

If your CA flags a discrepancy in a prior FY, search the audit log for
transactions in that period. Each entry has the original snapshot AND the
post-edit snapshot, so you can reconstruct what was filed vs what's now
showing.

---

## Common gotchas

1. **Mongo dates are timezone-naive.** Always strip tzinfo before comparing.
   Multiple bugs traced to mixing aware datetimes from API parsing with naive
   datetimes from Mongo. See `validate_replay`'s `_naive()` helper as the pattern.

2. **`yfinance` ticker format is `<SYMBOL>.NS` for NSE.** Conversion in
   `to_yahoo_ticker()`. Don't forget when adding new fetch logic.

3. **`Decimal` vs `Decimal128`.** API responses convert via `_convert_decimals_to_decimal128`
   on write, `_to_decimal` on read. Never write raw `Decimal` to Mongo — pymongo
   raises `bson.errors.InvalidDocument`.

4. **Soft-delete check.** Many queries use `{"deleted_at": None}`. Forgetting it
   means you'll see exited holdings in your "active" data.

5. **Frontend caching.** React Query caches aggressively. After mutations
   (buy/sell/edit/delete), use `refetchQueries` (synchronous) instead of
   `invalidateQueries` (lazy) to ensure UI reflects new state immediately.
