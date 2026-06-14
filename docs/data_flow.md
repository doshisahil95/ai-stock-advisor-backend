# Portfolio Advisor — Data Flow Reference

> Last updated: 2026-05-24 (post-Chat-5.5 small TD cleanup).  This is a "future-self" doc — open it when you need
> to remember why something works the way it does.

The system is split into two phases:

- **Phase 1** — portfolio truth: ICICI imports, manual transactions, FIFO replay, prices, reconciliation, cost-basis adjustments. Locked. Nothing in this phase generates suggestions; it answers "what do I own and what's it worth right now".
- **Phase 2** — suggestions engine: weekly buy + sell candidate ranking with shared scoring, news/fundamentals/momentum signals, earnings-proximity gate, stateful per-user feedback, and a single weekly digest. Read-only on Phase 1 data; the system never trades.

All access is via Tailscale (no public ingress). Backend FastAPI runs on EC2 t3.micro `100.112.20.41:8000` in `ap-south-1`. Frontend Next.js runs on EC2 `:3000`. Mongo is Atlas M10. Outbound transports: yfinance (prices), Anthropic (Claude Sonnet 4.5 + Haiku 4.5), Tavily (news search), Resend (email), public ntfy.sh (push). The self-hosted ntfy service on EC2 was decommissioned 2026-05-18 (F2b → TD8); the only live push transport is public ntfy.sh on random unguessable topics.

---

## Collections

### Phase 1

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
| `symbol_overrides` | Per-broker symbol mappings (ICICI/ZERODHA/OTHER → ISIN) | Manual UI via `/instruments/overrides` | ICICI import + reconciliation matching |
| `user_profile` | Preferences, reconciliation_baseline | Manual + reconciliation flow | Various |

### Phase 2

| Collection | Holds | Written by | Read by |
|---|---|---|---|
| `instruments_fundamentals` | Per-ISIN snapshot of yfinance fundamentals (ROE, ROA, margins, D/E, P/E, P/B, earnings growth) | Sunday cron `refresh_fundamentals.py` (06:00 IST) | Suggestions pipeline (signal extraction + raw-value lookup in explainability) |
| `news_articles` | Tavily search hits classified by Claude Haiku (positive/negative/neutral + severity) for held + watchlist universe | Sunday cron `fetch_news_for_universe.py --include-held` (06:30 IST) | `compute_news_signals_for_isin`, gates (max_high_severity_negative_news_30d), dossier links |
| `earnings_calendar` | Next-earnings dates per ISIN | F14 chunk 1-3 backfill + ongoing refresh | Shared earnings-proximity gate (buy + sell) |
| `suggestion_runs` | One doc per pipeline run; direction-aware (`"buy"` default for back-compat, or `"sell"`); embeds candidates with signals, gates, composite scores, dossiers | `run_suggestions()` / `run_sell_suggestions()` | `/suggestions/latest`, `/suggestions/runs`, frontend Insights tab |
| `suggestion_outcomes` | Per-candidate realized outcomes (price-at-suggestion vs price-at-window-end) for hindsight scoring | `scripts/track_suggestion_outcomes.py` | `/suggestions/performance` |
| `monitored_stocks` | Stateful per-ISIN watchlist with status (`tracking`/`passed`/`rejected`/`watchlist`) + feedback timestamps | `routers/suggestions.submit_feedback` via typed `MonitoredStockFeedbackPatch` (A1) | Two-mechanism exclusion: `get_excluded_isins` at run-build + `_build_user_action` at serialization |
| `monitored_stocks_audit` | Append-only log of every feedback transition (write-before-apply) | `submit_feedback` BEFORE the `monitored_stocks` update | Audit endpoint, debugging |
| `cron_heartbeats` | Per-`cron_name` last-success metadata + last-error blob | `cron_run()` decorator wrapping every cron script | Daily 21:00 IST `cron_health_check.py` (F4); `/cron/health` |
| `digest_deliveries` | Per-digest send audit (email id, ntfy id, candidate counts, direction) | `digest_delivery.send_weekly_digest` / `send_combined_digest` | Debugging stuck/dropped digests |
| `tavily_quota` | Daily Tavily call counter (per UTC day) | `news_fetcher` before every Tavily call | Throttling — refuses to issue searches once daily cap hit (resets 00:00 UTC) |

---

## Phase 1 flows

### ICICI import → staging → promotion

CSV exports from ICICI go through `scripts/import_orderbooks.py` which writes to `transactions_staging`. `scripts/reconcile_staging.py` matches staged rows against existing `transactions` + `symbol_overrides` and flags conflicts. `scripts/promote_staging.py` is the only path that moves rows from staging to live; it writes a `transactions_audit` entry per promoted row. Re-running an import is idempotent: staging is keyed on `(broker, broker_txn_id)`.

### Manual transactions + holding recompute

Buy/sell/edit/delete in the UI hits `app/routers/transactions.py`. Every write path calls `recompute_holding(isin)` after the transaction lands. PATCH and DELETE additionally write to `transactions_audit` BEFORE the change is applied (write-before-apply audit pattern), and run `validate_replay()` which rejects any edit/delete that would create a negative-quantity moment in the timeline.

### EOD + intraday prices

`refresh_prices.py` runs daily at 19:00 IST Mon-Fri, pulling all ISINs in `holdings` (active) via `yfinance` and upserting one `prices_daily` doc per ISIN per trading day. `refresh_prices_intraday.py` runs every 15 minutes from 09:00 to 15:45 IST Mon-Fri and APPENDS a new `prices_intraday` doc per cron tick (never overwrites). `bulk_get_latest_prices` picks the most recent same-day intraday row; falls back to EOD when none exists.

### Reconciliation

Manual reconciliation: user pastes the ICICI portfolio screen total into the UI form; backend writes a `reconciliation_snapshots` doc with both sides' invested / current_value / and the deltas. Auto reconciliation: `take_reconciliation_snapshot.py` runs daily at 19:30 IST after EOD prices land, using the cached ICICI baseline from `user_profile.reconciliation_baseline`. Drift detection is in `reconciliation._send_drift_alerts`: thresholds in `app/services/reconciliation.py` trigger one ntfy push (via `push_public(channel="price", ...)`) and one Resend email (via `notify.email(...)` — A2 part 2 ensures `sent.append("email")` only fires when `result["ok"]` is true).

### Cost basis adjustments

`scripts/seed_cost_basis_adjustments.py` is the source of truth for IT-Act-driven divergences from broker-nominal cost (TMPV/TMCV 49(2C) seeded). Each `cost_basis_adjustments` doc reduces the IT-Act-correct cost basis on `holdings.invested_amount` while preserving the broker-nominal view via `totals.broker_invested` on `/portfolio/summary`.

---

## Phase 2 flows

### Universe + fundamentals refresh

The buy-side universe is NIFTY 100 ∪ active holdings (held names outside NIFTY 100 still need fresh fundamentals + earnings for F2 sell-side scoring).  `scripts/seed_nifty100.py` is the one-time / occasional seeder — it fetches NSE's official `ind_nifty100list.csv`, marks matched instruments with `in_nifty100=True`, and backfills 5y of price history for the matched ISINs.  `refresh_fundamentals.py` then runs Sundays at 06:00 IST against `get_nifty100_union_holdings()` and upserts one `instruments_fundamentals` doc per ISIN: ROE, ROA, operating margin, debt-to-equity, P/E, P/B, earnings growth YoY, plus the fundamentals timestamp.  Missing-data ISINs are skipped (not zeroed) so normalization isn't poisoned.

### News pipeline (Tavily + classifier + signals)

`fetch_news_for_universe.py` runs Sundays at 06:30 IST with `--include-held` (A16 verified). For each ISIN in the universe ∪ active holdings ∪ watchlist, it issues a Tavily search (max 5 results per ISIN per week), then runs each hit through `news_classifier` (Claude Haiku 4.5) to assign sentiment polarity + severity + category. Results land in `news_articles`. `news_fetcher` consults `tavily_quota` before every call and refuses to search once the daily cap is hit `compute_news_signals_for_isin` aggregates `news_articles` over the trailing 30 days into three raw signal values that flow into scoring:

- `net_sentiment` ∈ [-1, +1] (scaled ×100 at extraction)
- `story_velocity` (ratio of last-7d to prior-23d story counts; baseline 1.0)
- `story_count` (clamped to 30)

### Earnings calendar gate (F14)

`earnings_calendar` carries `next_earnings_date` per ISIN. The shared `evaluate_earnings_proximity_gate` (F14 chunk 5 shipped) is consulted by both `_run_buy_pipeline` and `_run_sell_pipeline` — they thread `next_earnings_by_isin` into `score_candidates`/`score_sell_candidates`. The gate excludes candidates with earnings inside the configured proximity window (default 5 days per `DEFAULT_CONFIG.gates.earnings_proximity_days`). Missing earnings data is treated as "skipped" (which counts as passed) so absent data does not exclude (A5 comment refreshed).

### Suggestions engine — buy pipeline

`run_suggestions()` builds the candidate pool (universe minus held minus excluded via `get_excluded_isins` — first of two F5b exclusion mechanisms). For each candidate it calls `extract_signals` (raw fundamentals + 3m/6m returns + dist-from-52w-high + the three news signals), then `normalize_signals_within_universe` (cross-sectional 0-100 normalization per signal), then `composite_for_candidate` (group-weighted composite via `GROUP_SIGNALS`). Hard gates (`market_cap_min`, `max_high_severity_negative_news_30d`, `earnings_proximity_days`) filter the eligible set before composite ranking. The top N land in `suggestion_runs.top_candidates` with full signal/gate breakdown. A3+A4 (commit 2) wired `candidate_signals[isin]` into `composite_for_candidate` so `SignalScore.raw_value` now persists the actual raw input (raw fundamental / momentum % / news scaled-sentiment / velocity / count) instead of the normalized 0-100 score.

### Suggestions engine — sell pipeline

`run_sell_suggestions()` operates on currently-held ISINs only. `extract_sell_signals` augments fundamentals + momentum + news with holding-specific signals (`unrealized_gain_pct`, `portfolio_weight_pct`, days-held, etc.). `composite_for_candidate(group_signals_def=GROUP_SIGNALS_SELL, missing_group_default=50.0, candidate_signals_for_isin=candidate_signals.get(isin))` shares the same writer as buy. `missing_group_default=50.0` means missing tax/concentration data does not tank the composite (vs buy's 0.0 hard penalty). Same hard gates as buy plus sell-specific ones; surviving candidates are persisted with `direction="sell"` to disambiguate from buy runs.

### Stateful feedback + two-mechanism exclusion (F5/F5b/F6/F10)

The frontend Insights tab lets the user mark any candidate as `acted`, `passed`, `rejected`, or `watchlist`. `routers/suggestions.submit_feedback` writes to `monitored_stocks_audit` FIRST (F10 write-before-apply audit), then upserts `monitored_stocks` via `MonitoredStock(**doc).model_dump()` with the typed `MonitoredStockFeedbackPatch` model (`extra="forbid"`, A1 typed writer). The exclusion logic has TWO mechanisms (F5b two-mechanism guarantee):

1. **Run-build exclusion**: `get_excluded_isins` is queried before `extract_signals` so passed/rejected ISINs never enter the candidate pool.
2. **Serialization exclusion**: `_build_user_action` is called at `/suggestions/latest` serialization time so historical runs reflect current feedback state even if the run pre-dates the feedback.

Both must hold; relying on either alone leaks stale state into the UI.

### Weekly digest delivery (F2 / F2b)

`scripts/run_weekly_suggestions.py` runs Sundays at 07:00 IST with `--direction=both --notify --run-type scheduled`. It dispatches to both buy and sell pipelines and calls `digest_delivery.send_combined_digest(buy_run, sell_run)` — ONE Resend email (top 10 per direction + did-you-get-the-push banner) + ONE public ntfy.sh push covering both sides. `_send_email` delegates to `notify.email(subject=..., html=..., text=...)` which (post-A2 part 1) returns `{ok, id, error}` and never raises. Each delivery writes one `digest_deliveries` audit doc. The standalone `--direction=sell` reach inside `_run_sell_pipeline` (used by manual reruns / ad-hoc testing) is documented as such after A17 (commit 5) refreshed the stale chunk-6 NOTE.

### Cron health observability (F4)

Every cron script wraps its main entry in the `cron_run()` decorator which upserts a `cron_heartbeats` doc on success (with `last_success_at`, `last_success_summary`) or appends a `last_error_at`/`last_error_message` on failure. `CRON_REGISTRY` in `app/services/cron_heartbeat_service.py` enumerates the 10 expected crons with their `schedule_human` + `expected_weekdays` (A6 + A6.5 + A7 cleanups shipped in commit 3). `scripts/cron_health_check.py` runs daily at 21:00 IST IST, compares heartbeats to the registry, and `push_public(channel="errors", ...)` if any cron is missing or last-failed.

---

## Notification paths

Post-TD8 (commits 7a + 7b), the only live transports are:

- `push_public(channel, title, message, priority, tags)` — public ntfy.sh on random unguessable topics keyed by channel (`price`, `news`, `errors`, `digests`). Instant iOS delivery with full content in the banner. Trade-off: ntfy.sh + APNs see the content.
- `email(subject, html, text=None)` — Resend transactional. Returns `{ok, id, error}` and never raises (A2 part 1 wrapper contract). Both `digest_delivery._send_email` and `reconciliation._send_drift_alerts` branch on `result["ok"]`.

The self-hosted private ntfy service on EC2 was stopped + disabled on 2026-05-18 during F2b migration; `push_private`, `PrivateTopic`, `_NTFY_AUTH`, and the `b64encode` import were removed from `notify.py` in commit 7b (2026-05-23).

---

## Critical invariants

These MUST hold or computed P&L / suggestions / feedback are wrong:

1. **Transactions are immutable except via audited edit/delete.** The PATCH and DELETE endpoints in `app/routers/transactions.py` write to `transactions_audit` BEFORE applying the change. `validate_replay()` rejects any edit/delete that would create a negative-quantity moment in the timeline.

2. **`recompute_holding(isin)` is the only authoritative way to update a holding.** Called after every buy/sell/edit/delete. Replays all non-deleted transactions FIFO from scratch. Idempotent.

3. **`holdings.deleted_at = None` filter is universal.** Soft-deleted (fully-exited) holdings are excluded from all aggregations (summary, sector breakdown, top movers). They remain in the DB for audit.

4. **Cost basis = IT-Act-correct, not broker-nominal.** Our `holdings.invested_amount` reflects post-49(2C) cost basis (e.g. for TMPV demerger, the pre-demerger ₹81,337 is split 68.85% / 31.15%). Broker's "invested" is recoverable by adding `cost_basis_adjustments` back — exposed as `totals.broker_invested` on `/portfolio/summary`.

5. **`prices_intraday` writes are append-only within a day.** Each cron run inserts a new doc; we never overwrite. The intraday-vs-EOD selection in `bulk_get_latest_prices` picks the most recent intraday from today's UTC window, falling back to EOD.

6. **Feedback exclusion is two-mechanism (F5b).** `get_excluded_isins` at run-build time + `_build_user_action` at serialization time. Removing either leaks stale state into the UI.

7. **Feedback writes audit before applying (F10 write-before-apply).** `submit_feedback` inserts to `monitored_stocks_audit` FIRST, then upserts `monitored_stocks` via the typed `MonitoredStockFeedbackPatch`. If the audit insert fails, the state change never happens. Same pattern as `transactions_audit`.

8. **`SignalScore.raw_value` is the RAW input that fed normalization** (raw fundamental ratio, raw momentum %, or news scaled-sentiment / velocity / count) — NOT the normalized 0-100 score. The normalized score lives in `SignalScore.normalized_score`. Holds from commit 2 onward (A3+A4). Legacy runs predating commit 2 have `raw_value=f"{normalized:.2f}"` and should be regenerated if accuracy matters.

9. **Suggestion runs are direction-aware**, but back-compat defaults `direction="buy"` when missing. Any new caller of `run_suggestions` / `score_candidates` / `composite_for_candidate` that forgets to pass direction will produce a buy run.

10. **Tavily quota is checked before every call.** `news_fetcher` returns empty + logs a warning rather than risk overage. The quota is a daily call ceiling; resets at 00:00 UTC each day.

11. **`notify.email` and `notify.push_public` are NOT symmetric.** `email` swallows exceptions and returns `{ok, id, error}`; `push_public` raises via `_publish` → `response.raise_for_status()`. Callers that need delivery confirmation must branch on `result["ok"]` for email and on absence-of-exception for ntfy.

---

## Cron jobs (on EC2, `crontab -l`)

| Schedule | Script | Purpose |
|---|---|---|
| `0 3 * * *` | `refresh_instruments.py` | Refresh NSE master daily |
| `0 19 * * 1-5` | `refresh_prices.py` | Daily EOD prices (after market close) |
| `*/15 9-15 * * 1-5` | `refresh_prices_intraday.py` | 15-min intraday during market hours |
| `30 19 * * 1-5` | `take_reconciliation_snapshot.py` | Auto reconciliation (system-side) |
| `45 19 * * 1-5` | `track_suggestion_outcomes.py` | Per-candidate outcome tracking (weekdays 19:45 IST, after EOD prices land) |
| `0 6 * * 0` | `refresh_fundamentals.py` | Weekly fundamentals refresh for universe (Sun 06:00 IST) |
| `30 6 * * 0` | `fetch_news_for_universe.py --include-held` | Weekly news fetch + classification for universe ∪ held ∪ watchlist (Sun 06:30 IST) |
| `0 7 * * 0` | `run_weekly_suggestions.py --direction=both --notify --run-type scheduled` | Weekly buy + sell suggestion runs + combined digest (Sun 07:00 IST) |
| `0 21 * * *` | `cron_health_check.py` | F4 daily cron-health alerter |
| `0 0 * * 0` | log truncation (legacy) | **Superseded by logrotate** at `/etc/logrotate.d/portfolio-advisor` (weekly, rotate 4, compress). Safe to remove via `crontab -e` |

**Log retention** is handled by `logrotate` via `/etc/logrotate.d/portfolio-advisor` (installed 2026-05-24). Config: weekly rotation, rotate 4 (keep 4 weeks), `compress` + `delaycompress` (most recent rotation kept uncompressed for easier tail/grep), `copytruncate` (critical — preserves the `>>` redirect file handles that all crons use), `missingok` + `notifempty` (silent on Sunday-only crons that may not write between rotations). Covers all `/home/ubuntu/cron-*.log` files. The legacy `find ... -size +10M ... tail -10000` weekly crontab line is now redundant and can be removed via `crontab -e`.

The `CRON_REGISTRY` in `app/services/cron_heartbeat_service.py` is the source-of-truth registry that the daily health check compares heartbeats against. After A6 (commit 3), `run_weekly_suggestions`'s registry entry says `Sunday 07:00 IST` to match the actual crontab line. After A6.5 (commit 3), `refresh_instruments`'s registry description says "NSE EQUITY_L.csv" (was "Zerodha Kite" — same drift as A13 fixed in commit 4 + 4b).

---

## Adding a new corporate action

When ICICI applies a corporate action that we miss (e.g. a new demerger, bonus, or split), the workflow is:

1. **Detect** — usually via reconciliation drift alert, or manual ICICI check.
2. **Diagnose** — find the corp action on NSE.com (Corporate Information → Bonuses/Splits/Demergers) or PIB notices.
3. **Add transactions** — use `scripts/add_manual_transactions.py` to apply the corp action to your transactions (idempotent, marks via tags).
4. **Recompute** — `recompute_holding(<affected isin>)` runs automatically.
5. **Document** — if the action creates a tax-basis vs broker-basis divergence (e.g. Section 49(2C) demerger), add an entry to `scripts/seed_cost_basis_adjustments.py` and re-run the seed.
6. **Reconcile** — take a fresh manual reconciliation snapshot to confirm the new state matches ICICI's updated portfolio.

---

## When realized P&L for a closed FY changes

This happens only via transaction edit/delete. The audit log is the source of truth: `/transactions/audit/recent` shows every change with before/after, reason, timestamp. If your CA flags a discrepancy in a prior FY, search the audit log for transactions in that period. Each entry has the original snapshot AND the post-edit snapshot, so you can reconstruct what was filed vs what's now showing.

---

## When a stuck digest needs debugging

1. Check `digest_deliveries` for the most recent doc — confirms whether `send_combined_digest` was called and which channels were attempted.
2. If `delivery.email.ok = false`, look at `delivery.email.error` for the Resend message.
3. If ntfy is missing, check that the topic in `settings.NTFY_PUBLIC_TOPIC_DIGESTS` still matches the iPhone subscription (a topic rotation breaks the subscription silently).
4. Re-trigger manually via `scripts/run_weekly_suggestions.py --direction=both --notify --run-type manual` (the `--run-type` tag prevents the cron-health alerter from double-counting).
5. To inspect a specific past run end-to-end, query `suggestion_runs` by `run_date_ist` + `direction`; the full candidate list with signals + gates + dossiers is embedded.

---

## When a feedback action doesn't take effect

Two-mechanism exclusion (F5b) means a bug can hide in either layer. Diagnostic order:

1. Confirm the audit row landed: `db.monitored_stocks_audit.find({isin: "..."}).sort({_id: -1}).limit(5)`. If not, the API write failed silently — check `routers/suggestions.submit_feedback` logs.
2. Confirm the state mutation landed: `db.monitored_stocks.findOne({isin: "..."})`. Status + timestamps should match the latest audit row.
3. Confirm run-build exclusion: rebuild a buy/sell run and verify the ISIN does not appear (run-build mechanism).
4. Confirm serialization exclusion: hit `/suggestions/latest` and verify `user_action` reflects the latest feedback even on historical runs (serialization mechanism).

---

## Common gotchas

1. **Mongo dates are timezone-naive.** Always strip tzinfo before comparing. Multiple bugs traced to mixing aware datetimes from API parsing with naive datetimes from Mongo. See `validate_replay`'s `_naive()` helper as the pattern.

2. **`yfinance` ticker format is `<SYMBOL>.NS` for NSE.** Conversion in `to_yahoo_ticker()`. Don't forget when adding new fetch logic.

3. **`Decimal` vs `Decimal128`.** API responses convert via `_convert_decimals_to_decimal128` on write, `_to_decimal` on read. Never write raw `Decimal` to Mongo — pymongo raises `bson.errors.InvalidDocument`.

4. **Soft-delete check.** Many queries use `{"deleted_at": None}`. Forgetting it means you'll see exited holdings in your "active" data.

5. **Frontend caching.** React Query caches aggressively. After mutations (buy/sell/edit/delete), use `refetchQueries` (synchronous) instead of `invalidateQueries` (lazy) to ensure UI reflects new state immediately.

6. **`SignalScore.raw_value` shape changed in commit 2.** Anything reading historical `suggestion_runs` from before 2026-05-23 will see normalized 0-100 in `raw_value` instead of the raw input.  Post-TD11 (Chat 5.5), `explainability._build_signal_meta` reads `sig["raw_value"]` for momentum / news signals (`fundamentals_field=None`) — legacy pre-commit-2 runs will render the stringified normalized score as if it were a raw value for those signals; current runs render correctly.

7. **Suggestion direction defaults to `"buy"`.** Forgetting to pass `direction="sell"` when calling `run_suggestions` / `score_candidates` from a new code path will silently produce a buy run.

8. **Tavily quota is a daily call ceiling (resets 00:00 UTC), not per-run.** A failed Sunday fetch consumes part of that UTC day's budget. If you re-trigger manually, expect Tavily calls to refuse with "daily cap hit" in the log once the per-UTC-day ceiling is reached.

9. **`notify.email` never raises post-A2.** Old call sites that wrapped `email(...)` in `try/except Exception` will silently land `sent.append("email")` even on Resend failure. Fixed in `_send_drift_alerts` (A2 part 2). Any new caller must branch on `result["ok"]`.

10.  **TD9 closed 2026-05-24 (Chat 5.5).** The orphan `NTFY_URL` / `NTFY_USER` / `NTFY_PASS` keys were removed from `settings.py` + `/etc/portfolio-advisor/secrets.env` in one atomic commit so Pydantic v2 boot validation cannot drift between the model and the env file.  Public ntfy.sh (`NTFY_PUBLIC_TOPIC_*`) is the only live push transport.

11. **Production cron uses `--direction=both`.** The standalone `--direction=sell` reach inside `_run_sell_pipeline._send_weekly_digest` is only hit by manual reruns / ad-hoc testing. Production path is `send_combined_digest`, not `send_weekly_digest`.

---

## Open questions (carried forward)

- **Q3 (deferred from Chat 5)** — `holdings.stop_loss` field exists on the model but is never read or written by any code path. Two options: (a) wire to a new intraday-alerts surface, (b) remove. Punted out of Chat 5 to keep the audit pass focused.
- **TD9 (SHIPPED Chat 5.5 2026-05-24)** — `settings.NTFY_URL` / `NTFY_USER` / `NTFY_PASS` removed from `settings.py` + `/etc/portfolio-advisor/secrets.env` in one atomic commit.
- **TD11 (SHIPPED Chat 5.5 2026-05-24)** — `_build_signal_meta` now falls back to `sig["raw_value"]` for `fundamentals_field=None` signals (momentum + news) and renders via `meta["formatter_kind"]`.  Added `score_signed` + `count` formatters; reassigned `news_net_sentiment` / `news_story_velocity` / `news_story_count` / `high_severity_negative_count` away from `score_only`.  `is_ltcg_eligible` kept on `score_only` (binary semantic).