
# PROJECT_STATE.md

Living source of truth for the Personal AI Stock Advisor. Updated at the end of every chat. This file is the bootstrap document for any new conversation with an AI assistant.

If you (the assistant) are reading this for the first time in a new chat: read it top to bottom before doing anything. Do not skim. Do not assume. Do not redesign. The prior chat hit context limits or context drift — that's why we're here.

## Section 0: How to start a new chat

Paste this verbatim at the top of any new chat with an AI assistant working on this project:

```
I need you to continue work on a project called Personal AI Stock Advisor.

Before you do ANYTHING else, read the following in order:
1. https://github.com/doshisahil95/ai-stock-advisor-backend/blob/main/docs/PROJECT_STATE.md
2. The current HEAD commit of both repos:
   - https://github.com/doshisahil95/ai-stock-advisor-backend
   - https://github.com/doshisahil95/ai-stock-advisor-frontend
3. https://github.com/doshisahil95/ai-stock-advisor-backend/blob/main/docs/data_flow.md
4. Both repo READMEs

GitHub content may be cached. Whenever you read a file, capture the commit
SHA you read at, and re-read if the user tells you they have pushed since.

Today's scope is: <DESCRIBE THE FEATURE OR FIX FOR THIS CHAT>

Hard rules:
- Do not invent parallel patterns. Evolve existing code, don't redesign.
- Re-read files at HEAD before patching them. Do not trust memory.
- Hand me full file contents OR exact find-and-replace. Never "rest unchanged".
- Use canvas artifacts for files. Use chat for tests.
- In every mapping table, the Action column must say NEW FILE, REPLACE
  EXISTING, or PATCH.
- If you start hallucinating, drifting, or forgetting facts, say
  "I AM LOSING CONTEXT" so I can switch to a new chat.

Acknowledge by summarizing back to me:
- What you understood about the project from PROJECT_STATE.md
- What's already shipped vs open
- The exact scope of today's chat
- Any uncertainty you have before starting

Do not start coding until I confirm your summary is accurate.
```

## Section 1: Project identity

Personal AI Stock Advisor. Single-user portfolio + research tool for Indian NSE equities. Built for and by Sahil Doshi (Senior Consulting Engineer, MongoDB, India).

Strict design constraint that overrides everything else: the system never executes trades. Sahil trades manually in ICICI Direct. The system records, analyzes, and advises only. Any feature that would auto-place an order is out of scope, permanently.

The system is also not regulatory advice. Dossiers and suggestions must use phrasing like "the system flagged this because..." and never "buy" or "sell" as imperatives. The user decides; the user trades.

Goal of the tool: grow money. Every feature is judged on whether it helps with one of:
1. Buy better (find opportunities you'd otherwise miss)
2. Sell better (exit before reversals, hold through noise)
3. Avoid mistakes (concentration, FOMO, panic sells, missed corporate actions)
4. Reduce costs (taxes, fees, opportunity cost of dead capital)

Anything that doesn't map to one of these is decoration and gets cut.

Explicitly NOT a goal: dividend tracking, accounting, financial planning, tax filing, goal-based planning. The tool informs investment decisions; bank statements and the CA handle the rest.

## Section 2: User communication preferences (apply to all chats)

- Honest, slightly contrarian opinions over fake agreement. The user will push back when he disagrees; the assistant must do the same.
- Build right, no shortcuts. Do not introduce avoidable rework.
- Math accuracy and legal compliance matter. If something is mathematically wrong or legally non-compliant, call it out immediately.
- Use existing project conventions. Do not invent parallel patterns.
- Give full file contents OR exact find-and-replace instructions. Never use placeholders like "rest unchanged" or "// existing code here".
- Do not truncate important code.
- Prefer meaningful units of work. Small enough to test, not so tiny that we ping-pong.
- Give concrete test commands when appropriate.
- Files go in canvas artifacts. Tests go in chat as fenced code blocks.
- Every mapping table must use Action column values: NEW FILE, REPLACE EXISTING, or PATCH.
- The user edits on Mac, commits, pushes. EC2 is for build/test/deploy/debug. The assistant should not edit Mac files directly; it produces artifacts the user pastes.

## Section 3: Tech stack

### Backend

- Python 3.12
- FastAPI
- Pydantic v2
- MongoDB Atlas, M10 cluster, ap-south-1 region
- uv (package manager — replaces pip/poetry)
- yfinance (price + fundamentals + earnings calendar data; free tier)
- Anthropic Claude SDK (Sonnet 4.5 for dossiers, Haiku 4.5 for classification)
- Tavily (news search; free tier, daily quota enforced)
- Resend (transactional email for digests)
- ntfy (push notifications — both self-hosted private and ntfy.sh public)

### Frontend

- Next.js 16 (Turbopack)
- React 19
- TypeScript strict mode
- Tailwind v4
- shadcn/ui Nova preset
- Recharts (price charts)
- TanStack Query (server state)
- react-hook-form + zod (forms)
- sonner (toasts)
- next-themes (dark mode)

### Hosting

- AWS EC2 t3.micro instance in ap-south-1
- Tailscale only — no public ingress, no Caddy yet
- MongoDB Atlas M10 (separate from EC2)

## Section 4: Infrastructure paths and ports

### Network

- EC2 Tailscale IP: 100.112.20.41
- Backend port on EC2: 8000
- Frontend port on EC2: 3000
- Backend port on Mac (local dev): 8001 (NOT 8000)
- Frontend port on Mac (local dev): 3000

This Mac vs EC2 port difference is a real, recurring source of confusion for assistants. The assistant has gotten this wrong multiple times. Always specify which machine when giving test commands.

### Repo paths

Mac:
- Backend: `~/Projects/Personal/ai-stock-advisor/ai-stock-advisor-backend`
- Frontend: `~/Projects/Personal/ai-stock-advisor/ai-stock-advisor-frontend`

EC2:
- Backend: `/home/ubuntu/ai-stock-advisor-backend` (alias `~/ai-stock-advisor-backend`)
- Frontend: `/home/ubuntu/ai-stock-advisor-frontend` (alias `~/ai-stock-advisor-frontend`)

### Secrets paths

The application resolves secrets via `app/config/settings.py`:

```python
EC2_SECRETS = Path("/etc/portfolio-advisor/secrets.env")
LOCAL_SECRETS = Path(__file__).resolve().parents[2] / ".env"
SECRETS_FILE = EC2_SECRETS if EC2_SECRETS.exists() else LOCAL_SECRETS
```

So:
- On EC2 the file is `/etc/portfolio-advisor/secrets.env` (chmod 600, owned by root)
- On Mac the file is `<repo>/.env` (chmod 600, gitignored)
- The Settings class uses `pydantic-settings` with `model_config = SettingsConfigDict(env_file=str(SECRETS_FILE), env_file_encoding="utf-8", case_sensitive=True, extra="ignore")`
- Pydantic-settings reads the file directly into the Settings object — secrets are NOT exported to `os.environ`

If the assistant ever suggests `~/secrets/secrets.env` on EC2, it is wrong. That path was a transient debug artifact.

### Deploy scripts

On EC2:
- `~/deploy.sh` — pulls backend, runs `uv sync`, restarts `portfolio-advisor.service`
- `~/deploy-ui.sh` — pulls frontend, runs `npm install --legacy-peer-deps`, runs `npm run gen-api`, runs `npm run build`, restarts `portfolio-advisor-ui.service`

The `gen-api` step in `deploy-ui.sh` regenerates `lib/api-types.ts` against the running backend's OpenAPI spec. That file is gitignored. On Mac, running `npm run gen-api` without overriding the URL will fail because Mac backend is on port 8001 and the default is 8000. Use:
```bash
API_OPENAPI_URL=http://100.112.20.41:8000 npm run gen-api
```
or just skip it — `lib/api-types.ts` is not used at runtime; `lib/api.ts` is hand-typed.

### systemd units on EC2

- `portfolio-advisor.service` — runs `uvicorn app.main:app --port 8000 --host 0.0.0.0` as user `ubuntu`, with `EnvironmentFile` NOT used (settings.py loads from `/etc/portfolio-advisor/secrets.env` directly), `Environment="PYTHONPATH=/home/ubuntu/ai-stock-advisor-backend"`, `Environment="PYTHONUNBUFFERED=1"`. Logs to journald.
- `portfolio-advisor-ui.service` — runs `node /home/ubuntu/ai-stock-advisor-frontend/node_modules/next/dist/bin/next start` on port 3000 with hardening (NoNewPrivileges, PrivateTmp, ProtectSystem=strict, ReadWritePaths includes the frontend dir and /tmp).
- A sudoers entry at `/etc/sudoers.d/portfolio-advisor-systemctl` lets `ubuntu` restart these services without password.

### Repos

- Backend: https://github.com/doshisahil95/ai-stock-advisor-backend
- Frontend: https://github.com/doshisahil95/ai-stock-advisor-frontend

GitHub is the source of truth for code. GitHub may serve cached content via Glean's reader. When in doubt, find the latest commit SHA and read at that SHA explicitly.

## Section 5: Backend file map

Directory layout under `app/`:

```
app/
  main.py                    — FastAPI bootstrap, router includes, lifespan
  config/
    settings.py              — pydantic-settings, loads secrets file
  db/
    client.py                — Mongo client, get_db(), Collections accessor class
    indexes.py               — ensure_indexes() called on startup
  models/
    _common.py               — utcnow(), Decimal128 helpers, ObjectId helpers
    instrument.py            — Instrument (NSE master record)
    holding.py               — Holding (active position)
    transaction.py           — Transaction (BUY/SELL/SPLIT/BONUS/DEMERGER)
    fundamentals.py          — InstrumentFundamentals (per-ISIN, per-refresh)
    suggestion.py            — SuggestionRun, SuggestionOutcome, CandidateScore,
                               SignalScore, GateResult
    news.py                  — NewsArticle (live model)
    news_article.py          — DEAD; older parallel model, do not use, do not import
    monitored_stock.py       — MonitoredStock; Literal status is DRIFTED (see tech debt)
    macro_signal.py          — placeholder
    conversation.py          — placeholder (will be used for chat features F1/F3)
    reconciliation.py        — ReconciliationSnapshot
    cost_basis_adjustment.py — CostBasisAdjustment
  routers/
    holdings.py              — /portfolio/holdings, /portfolio/holdings/{isin},
                               /sell, /preview-sell, /history, /transactions
    portfolio.py             — /portfolio/summary
    transactions.py          — /transactions/search, /transactions/{id} CRUD,
                               /transactions/audit/recent, /transactions/{id}/audit
    reconciliation.py        — /reconciliation/snapshot, /snapshots, /auto-snapshot
    instruments.py           — /instruments (symbol_overrides CRUD)
    cost_basis.py            — /cost-basis/adjustments
    suggestions.py           — /suggestions/latest, /runs, /runs/{id},
                               /performance, /{isin}/feedback
  services/
    instrument_service.py    — lookup_isin, bulk_lookup_isins, refresh
    price_service.py         — EOD + intraday fetch, bulk_get_latest_prices,
                               annotate_with_current_price, get_previous_close
    holdings_service.py      — recompute_holding, validate_replay, preview_sell,
                               _to_decimal helper
    portfolio_service.py     — compute_summary
    transactions_audit_service.py — log_change, get_audit_for_transaction
    reconciliation.py        — take_auto_snapshot, drift detection
    cost_basis_service.py    — get_active_adjustments, total_adjustment_amount
    fundamentals_service.py  — yfinance provider, refresh_one, refresh_universe,
                               get_latest_for_isin, get_latest_bulk, is_fresh,
                               _normalize_debt_to_equity, _normalize_dividend_yield
    tavily_client.py         — quota-tracked wrapper, TavilyQuotaExceeded
    news_fetcher.py          — fetch_for_instrument, fetch_for_universe
    news_classifier.py       — Haiku batch classifier, retry pass
    news_signals.py          — compute_news_signals_for_isin, _bulk
    scoring_service.py       — extract_signals, score_candidates,
                               Q/V/M/N weights, gates, version "1.0.0-unit2"
    dossier_service.py       — generate_dossiers_for_top_k, Sonnet,
                               plain_english_summary in schema
    suggestion_engine.py     — run_suggestions (full pipeline)
    outcome_tracker.py       — create_outcomes_for_run, snapshot_open_outcomes,
                               compute_system_performance
    digest_delivery.py       — send_weekly_digest (Resend + ntfy)
    explainability.py        — SIGNAL_META, GROUP_META, GATE_META, FEEDBACK_META,
                               PAGE_INTRO, enrich_run, enrich_candidate
    notify.py                — push_private, push_public, email (generic wrappers;
                               digest_delivery uses its own copies of Resend +
                               ntfy code, not these — that's intentional drift)
scripts/
  init_db.py
  refresh_instruments.py
  refresh_prices.py
  refresh_prices_intraday.py
  take_reconciliation_snapshot.py
  seed_nifty100.py
  seed_cost_basis_adjustments.py
  import_orderbooks.py
  reconcile_staging.py
  promote_staging.py
  add_manual_transactions.py
  refresh_fundamentals.py
  fetch_news_for_universe.py
  run_weekly_suggestions.py
  track_suggestion_outcomes.py
docs/
  data_flow.md               — Phase 1 invariants; missing Phase 2 collections
  PROJECT_STATE.md           — THIS FILE
pyproject.toml
README.md                    — stale; says Phase 2 is "what's next" with old ordering
```

## Section 6: Frontend file map

Directory layout:

```
app/
  layout.tsx                 — root layout, fonts, ThemeProvider, QueryProvider
  page.tsx                   — dashboard
  globals.css                — Tailwind v4 imports, font variable mappings,
                               shadcn .dark class
  holdings/[isin]/page.tsx   — single holding drill-down
  reconciliation/page.tsx
  cost-basis/page.tsx
  transactions/page.tsx
  transactions/audit/page.tsx
  suggestions/page.tsx
components/
  ui/                        — shadcn primitives (button, card, dialog, popover,
                               tabs, separator, badge, skeleton, etc.)
  holdings-table.tsx
  buy-sheet.tsx
  sell-sheet.tsx
  edit-transaction-sheet.tsx
  holding-header.tsx, holding-stats.tsx, price-chart.tsx,
  transactions-list.tsx, notes-panel.tsx
  reconciliation-badge.tsx
  theme-toggle.tsx
  refresh-button.tsx
  suggestion-card.tsx        — full explainability layer (Commit B)
  explain-popover.tsx        — reusable info-icon popover (Commit B)
  page-intro.tsx             — "How to read this page" collapsible (Commit B)
lib/
  api.ts                     — hand-typed API client; SINGLE SOURCE OF TRUTH for
                               frontend types; ~600 lines
  api-types.ts               — GITIGNORED; auto-generated by `npm run gen-api`;
                               not actually used at runtime; do not check in
  format.ts                  — inr(value), pct(value, withSign?),
                               colorForChange(value), dateTime(iso), nf, date
  utils.ts                   — cn() (clsx + tailwind-merge)
  config.ts                  — apiBaseUrl (reads NEXT_PUBLIC_API_BASE_URL env)
  query-client.tsx           — TanStack Query provider
package.json
tsconfig.json                — paths: "@/*" -> "./*"
```

## Section 7: Database collections (exhaustive)

All collections live in MongoDB Atlas M10. The DB name is set by env (`MONGODB_DB_NAME`). All collections accessed via `Collections.<name>()` from `app.db.client`. Indexes ensured at startup via `app/db/indexes.py`.

### Phase 1 collections

`instruments`
- Master NSE/BSE instrument list, refreshed daily from Zerodha Kite instruments CSV
- Key fields: `exchange`, `symbol`, `isin`, `name`, `instrument_type`, `segment`, `lot_size`, `tick_size`, `source`, `last_seen_at`, `last_changed_at`, `in_nifty100`
- Count: ~2,368 total; 100 with `in_nifty100=True`
- Indexes: `(exchange, symbol)` unique, `isin`, `last_seen_at`, `last_changed_at`, `in_nifty100`
- Writer: `scripts/refresh_instruments.py` (delta-aware), `scripts/seed_nifty100.py`, manual upserts for BSE-only stocks

`symbol_overrides`
- Manual ISIN aliases when the master list is wrong or missing
- Key fields: `exchange`, `symbol`, `isin`, `reason`, `created_at`
- Writer: `/instruments` router (CRUD)

`holdings`
- Active positions, one doc per ISIN; soft-deleted on full exit
- Key fields: `isin`, `symbol`, `exchange`, `name`, `sector`, `industry`, `quantity` (Decimal128), `avg_cost`, `invested_amount`, `realized_pnl`, `first_purchased_at`, `last_traded_at`, `thesis`, `notes`, `stop_loss`, `target_price`, `tags`, `deleted_at`
- INVARIANT: every query MUST include `deleted_at: None` to see active holdings; deleted holdings preserve replay correctness (FIFO needs full history)
- Indexes: `isin` unique (partial: only where deleted_at is None), `(deleted_at, last_traded_at)`
- Writer: `recompute_holding(isin)` in `holdings_service.py` is the ONLY authoritative writer; idempotent; recomputes from `transactions` from scratch using FIFO
- Note: `realized_pnl` is structural (FIFO computes it as a side-effect) but per user direction is HIDDEN in UI (see Section 13, Cleanup chat)

`transactions`
- Append-only ledger of all trades and corporate actions
- Key fields: `isin`, `symbol`, `exchange`, `type` (BUY/SELL/SPLIT/BONUS/DEMERGER), `trade_date`, `quantity` (Decimal128), `price`, `total_fees`, `remaining_quantity` (for FIFO lot tracking), `notes`, `source`, `corporate_action.ratio_from`, `corporate_action.ratio_to`, `fully_consumed_at`, `deleted_at`
- INVARIANT: never directly UPDATEd or DELETEd; edits and deletes go through `/transactions/{id}` PATCH/DELETE which require a reason, write to `transactions_audit` first, then apply the change, then call `recompute_holding`
- Indexes: `(isin, trade_date)`, `(symbol, trade_date)`, `trade_date`

`transactions_staging`
- Holding area for the bulk ICICI order book imports before promotion to live
- Same shape as `transactions`
- Cleared by `scripts/promote_staging.py --confirm --wipe-live`

`transactions_audit`
- Append-only audit log; one doc per edit/delete
- Key fields: `transaction_id`, `action` (edit/delete), `reason`, `changed_fields` (dict of {field: [before, after]}), `performed_at`, `symbol`
- INVARIANT: written BEFORE the actual change is applied, so even if the apply step crashes, the intent is recorded

`prices_daily`
- EOD OHLCV bars; ~5 years of history
- Key fields: `isin`, `date` (UTC-naive midnight), `open`, `high`, `low`, `close` (Decimal128), `volume`, `source`
- Count: ~115,791 docs across 100 NIFTY 100 ISINs (~1,158 per stock), plus 32 held ISINs
- Indexes: `(isin, date)` unique
- Writer: `scripts/refresh_prices.py` (yfinance)

`prices_intraday`
- Latest intraday quote captured every 15 min during market hours
- Key fields: `isin`, `symbol`, `date` (UTC), `captured_at`, OHLCV, `source="yfinance_5m_latest"`
- INVARIANT: append-only within a day (not upserted) so we keep history
- No TTL configured yet
- Writer: `scripts/refresh_prices_intraday.py`
- Consumer: `bulk_get_latest_prices` prefers today's intraday over EOD; falls back to EOD

`reconciliation_snapshots`
- Daily comparisons of our system totals vs ICICI Direct portfolio totals
- Key fields: `type` (manual/auto), `taken_at`, `our_invested`, `our_current_value`, `our_day_gain`, `icici_invested`, `icici_current_value`, `icici_day_gain`, `drift_invested_pct`, `drift_current_pct`, `drift_alerts` (list of strings), `notes`
- Writer: `/reconciliation/snapshot` (manual) or `/reconciliation/auto-snapshot` (cron at 19:30 IST weekdays)
- Drift detection rules: invested has baseline-relative drift; current_value uses absolute ₹15k threshold (intra-day timing is noise); day_gain dropped from alerts (always noise)

`cost_basis_adjustments`
- Audit trail for tax-correct cost basis adjustments (e.g., TMPV/TMCV demerger per IT Act Section 49(2C))
- Key fields: `name`, `amount` (Decimal128), `effective_date`, `it_act_section`, `rationale`, `source_documents`, `created_at`
- Consumer: `compute_summary` adds `broker_invested = our_invested + total_adjustment`, plus `broker_unrealized_pnl` and `broker_unrealized_pnl_pct`, so the UI can show both tax view and broker view

`user_profile`
- Single doc, `_id="sahil"`
- Holds investing philosophy notes, TMPV/TMCV cost basis annotation, etc.

### Phase 2 collections (Suggestions Engine)

`monitored_stocks`
- User-feedback state for stocks the engine has surfaced, plus watchlist entries (F13)
- Key fields: `isin`, `status` (writers use "tracking"/"passed"/"rejected"/"watchlist"; Pydantic model says "tracking"/"promoted_to_holding"/"dropped" — SCHEMA DRIFT, see tech debt), `acted_at`, `passed_at`, `rejected_at`, `last_feedback_at`, `last_feedback_action`, `last_feedback_note`, `created_at`, `updated_at`
- INVARIANT: writes go through `routers/suggestions.submit_feedback` only, using raw `update_one` (Pydantic bypassed because of the schema drift)
- Consumer: `suggestion_engine.get_rejected_isins()` excludes `status="rejected" AND rejected_at >= now - 90d` from the universe
- Future consumer (F6): also exclude `status="passed"` for the current run and `status="tracking"` (acted) permanently
- Indexes: `isin` unique, `(status, rejected_at)`

`instruments_fundamentals`
- One doc per ISIN per fundamentals refresh (so we have history)
- Key fields: `isin`, `symbol`, `as_of` (date), `fetched_at` (datetime), `market_cap`, `pe_ratio`, `pb_ratio`, `dividend_yield`, `return_on_equity`, `return_on_assets`, `operating_margin`, `debt_to_equity`, `earnings_growth_yoy`, `revenue_growth_yoy`, `beta`, `fifty_two_week_high`, `fifty_two_week_low`, `sector` (yfinance), `industry`, `source`, `source_raw` (full yfinance dict for replay), `fields_present`, `fields_missing`
- Indexes: `isin_latest_unique` (unique, latest only via `(isin, fetched_at desc)`), `fetched_at`
- Writer: `scripts/refresh_fundamentals.py` → `fundamentals_service.refresh_one`
- Consumer: `suggestion_engine` (scoring), `explainability.py` (raw values for UI rendering)

`news_articles`
- Classified news per article; one doc per URL with `$addToSet`-merged `entities_isins`
- Key fields: `url` (unique), `title`, `published_at`, `fetched_at`, `source`, `body` (purged after classification), `body_purged_at`, `entities_isins` (list), `themes` (Literal[earnings|regulatory|corporate_action|management_commentary|sector_macro|noise]), `sentiment` (positive/neutral/negative/mixed), `sentiment_confidence`, `severity` (low/medium/high), `classifier_summary`, `classified` (bool)
- Indexes: `url` unique, `(entities_isins, classified, fetched_at)`, `(classified, fetched_at)`
- Writer: `news_fetcher.py` (fetch) then `news_classifier.py` (classify in two-phase Haiku batches: BATCH_SIZE=25 main pass, RETRY_PASS_BATCH_SIZE=3 for stragglers)
- Consumer: `news_signals.py` (compute net_sentiment, story_velocity, story_count), `dossier_service.py` (per-candidate news context, last 8 articles)

`suggestion_runs`
- Append-only history of every weekly run
- Key fields: `_id`, `_schema_version`, `run_date`, `run_date_ist`, `run_type` (scheduled/manual), `status` (success/partial/failure), `started_at`, `finished_at`, `error`, `universe_size`, `excluded_held`, `excluded_rejected`, `excluded_stale_data`, `candidates_considered`, `candidates_post_gates`, `config` (full snapshot of weights, gates, freshness, scoring, top_k, version), `top_candidates` (list of `CandidateScore` docs, persisted in full), `all_candidates`, `top_k`, `notes` (JSON string containing `dossiers` array)
- INVARIANT: append-only; never updated; re-running creates a new doc
- Future (F2): a `direction` field will distinguish "buy" runs (default) from "sell" runs
- Indexes: `(run_date desc)`, `(run_date_ist, run_type)`, `(status)`

`suggestion_outcomes`
- One doc per top-K candidate per run; tracks actual stock + benchmark over 30/60/90/180-day windows
- Key fields: `isin`, `symbol`, `suggestion_run_id`, `suggested_at`, `suggested_at_price`, `suggested_rank`, `suggested_composite_score`, `tracking_status` (open/acted/passed/rejected/expired), `price_at_30d/60d/90d/180d`, `nifty_at_30d/60d/90d/180d` (these are RETURN PERCENTAGES vs benchmark, not prices — equal-weighted NIFTY 100), `excess_return_30d/60d/90d/180d`, `user_action_at`, `user_action_note`, `created_at`, `updated_at`
- INVARIANT (changed in Commit A.5): snapshot eligibility is `tracking_status != "expired"`, NOT `tracking_status == "open"`. The user's label (acted/passed/rejected) is metadata; data collection continues regardless so per-bucket performance is measurable.
- INVARIANT: outcomes only auto-flip to "expired" if still labeled "open" at day 180. User-set labels are never overwritten.
- Indexes: `(isin, suggested_at desc)`, `(suggested_at desc)`, `(tracking_status)`, `(suggestion_run_id)`
- Writer: `outcome_tracker.create_outcomes_for_run` at run time, `snapshot_open_outcomes` daily

`tavily_quota`
- One doc per UTC day; counters incremented atomically
- Key fields: `date` (YYYY-MM-DD string), `total_calls`, `total_credits`, `per_use_case.<name>.calls`, `per_use_case.<name>.credits`
- Indexes: `date` unique
- Writer: `tavily_client.py` `$inc` updates with upsert
- INVARIANT: `TAVILY_DAILY_CALL_LIMIT` (default 200) enforced; raises `TavilyQuotaExceeded` when hit

`digest_deliveries`
- Audit log of weekly digest emails + ntfy pushes
- Key fields: `run_id`, `sent_at`, `email_status`, `ntfy_status`, `top_candidates_count`, `errors`
- Indexes: `(sent_at desc)`, `(run_id)`
- Writer: `digest_delivery.send_weekly_digest`

`digests` / `alerts_log` / `conversations` / `macro_signals`
- Scaffolds; not actively written by current code
- `conversations` will be used for chat features (F1, F3)
- Reserved; do not delete

### Future collections (planned, not yet created)

`cron_heartbeats` (F4)
- One doc per cron run; `cron_name`, `started_at`, `finished_at`, `status` (success/failure), `error`, `metadata`
- Daily 21:00 IST check job reads this to detect missed runs

`monitored_stocks_audit` (F10)
- Audit trail for `monitored_stocks` writes (currently only journald logs preserve feedback transitions)
- One doc per feedback action; `isin`, `action`, `previous_status`, `new_status`, `note`, `performed_at`

`earnings_calendar` (F14, folded into F2)
- Cached earnings dates from yfinance `Ticker.calendar`
- One doc per ISIN per earnings event; `isin`, `earnings_date`, `fetched_at`, `source`
- Consumer: F2 sell-side scoring (earnings proximity signal), F2 buy-side gate (skip if within 5 days)

## Section 8: API endpoints (exhaustive)

All routes are under the FastAPI app, served on port 8000 (EC2) or 8001 (Mac local). All return JSON. ISIN path params are validated 12-char.

### Phase 1

```
GET    /health
GET    /portfolio/holdings                          → Holding[]
GET    /portfolio/holdings/{isin}                   → Holding
POST   /portfolio/holdings                          → Holding (BUY)
PATCH  /portfolio/holdings/{isin}                   → Holding (notes/thesis/stop_loss/target_price/tags only)
POST   /portfolio/holdings/{isin}/sell              → Holding OR {message, realized_total}
POST   /portfolio/holdings/{isin}/preview-sell      → SellPreview
GET    /portfolio/holdings/{isin}/history?days=N    → PriceBar[]
GET    /portfolio/holdings/{isin}/transactions      → Transaction[]
GET    /portfolio/summary                           → PortfolioSummary
GET    /transactions/search?symbol&type&from_date&to_date&skip&limit
                                                    → {results, total}
GET    /transactions/{id}                           → Transaction
PATCH  /transactions/{id}                           → Transaction (requires reason)
DELETE /transactions/{id}                           → {deleted: true} (requires reason)
GET    /transactions/audit/recent?limit=N           → AuditEntry[]
GET    /transactions/{id}/audit                     → AuditEntry[]
POST   /reconciliation/snapshot                     → ReconciliationSnapshot (manual)
GET    /reconciliation/snapshots                    → ReconciliationSnapshot[]
POST   /reconciliation/auto-snapshot                → ReconciliationSnapshot (cron)
GET    /cost-basis/adjustments                      → CostBasisAdjustment[]
GET    /instruments                                 → symbol_overrides list
POST   /instruments                                 → symbol_overrides upsert
DELETE /instruments/{exchange}/{symbol}             → delete override
```

### Phase 2 (Suggestions)

```
GET    /suggestions/latest                          → SuggestionRun + enrichment
GET    /suggestions/runs?limit=N&skip=N             → {runs, total, limit, skip}
GET    /suggestions/runs/{run_id}                   → SuggestionRun + enrichment
GET    /suggestions/performance                     → SuggestionPerformance with by_bucket
POST   /suggestions/{isin}/feedback                 → {isin, action, status}
       Body: {action: "acted"|"passed"|"rejected", note?: string}
```

### Future endpoints (planned)

```
POST   /watchlist/{isin}                            → add to watchlist (F13)
DELETE /watchlist/{isin}                            → remove from watchlist (F13)
GET    /watchlist                                   → list watchlist (F13)
GET    /portfolio/risk-summary                      → concentration & risk alerts (F12)
GET    /portfolio/by-tag?tag=X                      → holdings grouped/filtered by tag (F15)
POST   /chat/suggestions                            → ad-hoc chat about suggestions (F1)
POST   /chat/holdings/{isin}                        → ad-hoc chat about a holding (F3)
GET    /tax/capital-gains?fy=YYYY-YY                → capital gains pack (F11)
GET    /cron/heartbeats                             → cron health status (F4)
```

### Sell endpoint response shape (critical, often confused)

`POST /portfolio/holdings/{isin}/sell` returns one of:
- The full updated Holding doc (partial sell, position still active)
- `{message: "Position fully exited", realized_total: "<string Decimal>"}` (full exit)

The frontend discriminates via type guard on the `_id` field, NOT a `status` field. The original SellSheet was written this way; do not change it.

## Section 9: Cron registry on EC2

Run `crontab -l` to see current state. As of last update of this doc, the registered cron entries on EC2 are:

```
# Daily instrument refresh — 03:00 IST
0 3 * * * cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/refresh_instruments.py >> /home/ubuntu/cron-instruments.log 2>&1

# Weekday EOD price refresh — 19:00 IST
0 19 * * 1-5 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/refresh_prices.py >> /home/ubuntu/cron-prices.log 2>&1

# Intraday price refresh — every 15 min during market hours (09:15–15:45 IST), weekdays
*/15 9-15 * * 1-5 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/refresh_prices_intraday.py >> /home/ubuntu/cron-prices-intraday.log 2>&1

# Daily reconciliation auto-snapshot — 19:30 IST (after price refresh)
30 19 * * 1-5 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/take_reconciliation_snapshot.py >> /home/ubuntu/cron-reconciliation.log 2>&1

# Weekly log truncation — Sunday 00:00 IST
0 0 * * 0 truncate -s 0 /home/ubuntu/cron-*.log
```

NOT YET REGISTERED (Phase 2 jobs, will be added in Chat 2 via F5a):
- `scripts/refresh_fundamentals.py` — weekly, Saturday late evening
- `scripts/fetch_news_for_universe.py` — daily
- `scripts/run_weekly_suggestions.py --notify` — Sunday 06:00 IST (for buy-side)
- `scripts/run_weekly_suggestions.py --direction=sell --notify` — Sunday 07:00 IST (for sell-side, after F2 ships)
- `scripts/track_suggestion_outcomes.py` — daily, after 19:00 EOD price refresh
- `scripts/cron_health_check.py` — daily 21:00 IST (F4)

No silent failures: every cron registration must include log file paths AND write a heartbeat to `cron_heartbeats` (F4 dependency).

## Section 10: Settings and environment variables

Configured in `app/config/settings.py` via pydantic-settings reading `/etc/portfolio-advisor/secrets.env` (EC2) or `<repo>/.env` (Mac). All required unless marked default.

### Anthropic
- `ANTHROPIC_API_KEY` (required)
- `ANTHROPIC_MODEL_PRIMARY` (default `"claude-sonnet-4-5"`) — used by dossier_service, chat features
- `ANTHROPIC_MODEL_FAST` (default `"claude-haiku-4-5"`) — used by news_classifier

### MongoDB
- `MONGODB_URL` (required)
- `MONGODB_DB_NAME` (required)

### Tavily
- `TAVILY_API_KEY` (required)
- `TAVILY_DAILY_CALL_LIMIT` (default 200) — hard ceiling enforced before API call
- `TAVILY_SEARCH_DEPTH` (default `"basic"`)
- `TAVILY_MAX_RESULTS_PER_QUERY` (default 5)

### Email (Resend)
- `RESEND_API_KEY` (required)
- `RESEND_FROM` (e.g., `"advisor@your-domain.com"`)
- `DIGEST_TO` (your email)

### ntfy
- `NTFY_URL` (private, self-hosted, behind Tailscale Funnel)
- `NTFY_USER`, `NTFY_PASS` (basic auth for private)
- `NTFY_TOPIC_PRICE`, `NTFY_TOPIC_NEWS`, `NTFY_TOPIC_ERRORS` (public ntfy.sh topics, unguessable so they act as bearer tokens)

## Section 11: Phase 1 INVARIANTS — never violate

These come straight from `docs/data_flow.md`. They are hard rules.

1. Transactions are immutable except through the audited PATCH/DELETE flow. Every PATCH/DELETE writes a `transactions_audit` entry BEFORE applying the change. The reason field is required.

2. `recompute_holding(isin)` is the only authoritative writer to `holdings`. It is idempotent and recomputes from `transactions` from scratch using FIFO. Never write directly to `holdings`. Call `recompute_holding` after any transaction change.

3. `validate_replay(isin, simulated_transactions)` simulates a transaction set and rejects any timeline that produces negative quantity at any point. Both PATCH and DELETE on `/transactions/{id}` call this before applying.

4. `holdings.deleted_at = None` filter is universal. Every read of active holdings must include this filter. Deleted holdings preserve replay correctness.

5. Cost basis is IT-Act-correct, not broker-nominal. `holdings.invested_amount` reflects the tax-correct cost basis (which for TMPV/TMCV reflects the 68.85/31.15 cost basis split per Tata Motors official Section 49(2C) disclosure). The broker-nominal view is recoverable as `holdings.invested_amount + total_cost_basis_adjustment` and surfaced via `summary.totals.broker_invested`.

6. `prices_intraday` writes are append-only within a day (inserted, not upserted) so we keep intraday history.

7. ICICI portfolio display shows TMPV at ~813 and TMCV at ~253 (sums to ~1,06,673), which is ~25k higher than our correct ~81,337. Our numbers reflect tax-correct cost basis; ICICI display is cosmetically wrong but does not affect actual money or tax filing.

## Section 12: Phase 2 INVARIANTS

1. `suggestion_runs` are append-only. Re-running creates a new doc; never UPDATEd.

2. `tavily_quota` is one doc per UTC day with `$inc` counters. Hard ceiling enforced.

3. Confidence score is deterministic (computed from data freshness and signal availability), NOT LLM-generated. Composite score answers "is this stock attractive?"; confidence answers "should I trust the answer?"

4. The dossier prompt requires narrative-only output. Numbers come from our data. The prompt forbids "buy" or "sell" imperatives. The prompt also forbids inventing facts not in the input.

5. `gate_meta`, `group_meta`, `signal_meta`, `confidence_meta`, `feedback_meta`, `page_intro` are PRESENTATION metadata, added by `routers/suggestions._serialize_run` via `enrich_run`. They are NOT in the persistent model. The router calls `enrich_run` after JSON conversion; the underlying `suggestion_runs` doc is never mutated.

6. Snapshot eligibility for `outcome_tracker.snapshot_open_outcomes` is `tracking_status != "expired"`, NOT `tracking_status == "open"`. User-set labels (acted/passed/rejected) do not gate data collection. (Changed in Commit A.5.)

7. Auto-expiry only flips outcomes that are still labeled "open" at day 180. A user-set label is never auto-overwritten. (Changed in Commit A.5.)

8. Feedback re-labels the MOST RECENT non-expired outcome for the ISIN, regardless of its current `tracking_status`. (Fixed in Commit A.5.1.)

9. The 90-day rejection window: `monitored_stocks.status == "rejected" AND rejected_at >= now - 90d` excludes the ISIN from the universe in `suggestion_engine.get_rejected_isins`. Auto-expires.

10. Per `monitored_stocks` schema-vs-writer drift: the model says `Literal["tracking", "promoted_to_holding", "dropped"]` but the writer writes `"tracking"`, `"passed"`, `"rejected"`. The writer uses raw `update_one` so Pydantic is bypassed. If you ever load a `monitored_stocks` doc through `MonitoredStock(**doc)` it will throw. See tech debt.

11. The `notes` field on a `SuggestionRun` is a JSON string containing `{dossiers: [...]}`. The router parses it and exposes `dossiers` at the top level of the response, then strips `notes`.

12. The router also strips `all_candidates` from the response to keep payloads small. The persisted doc still has it.

## Section 13: Shipped vs Open

### Shipped through this point

Phase 1 (all shipped, all locked):
- Holdings dashboard with day-gain coloring
- FIFO cost basis with fee allocation and precision
- ICICI Order Book import → staging → reconcile → promote pipeline
- Manual transaction entry for IPOs, demergers, bonuses, splits
- Transaction edit/delete with mandatory reason + audit log
- Preview-sell endpoint
- Reconciliation snapshots (manual + auto) with drift detection
- Cost basis adjustments (TMPV/TMCV demerger seeded)
- EOD + intraday price refresh
- Tax view vs broker view in portfolio summary
- Single-holding drill-down page with chart, transactions, notes panel
- Audit log page
- Dark mode toggle
- Reconciliation badge in header
- Recent activity card (moved to header button)

Phase 2 Suggestions Engine:
- Unit 1: foundations (models, indexes, yfinance fundamentals, scoring, persistence)
- Unit 2: news fetch + Haiku classify, Sonnet dossier generator
- Unit 3: outcomes, performance, frontend page with three tabs
- Commit A (backend explainability): explainability catalog, plain_english_summary on dossiers, enrich_run on responses
- Commit A.5 (feedback correctness): snapshot gating fixed, outcome relabel for "rejected", `by_bucket` performance breakdown
- Commit A.5.1 (re-label correctness): outcome relabel updates the most recent non-expired outcome regardless of current status
- Commit B (frontend explainability): popovers on QVMN, confidence, gates, signals, feedback buttons; "What this means" plain-English block; "How to read this page" page intro; vanish-on-click for actioned cards (session-scoped); performance tab renders `by_bucket` table per window

### Open items (final scope, prioritized)

**F2. Sell-side suggestions — ABSOLUTELY NECESSARY**
- Currently the engine only surfaces buy candidates from the NIFTY 100 universe minus held stocks
- Need a parallel surface that scans HELD stocks and suggests when to book profit
- Different scoring (overvalued signal, momentum-reversal, target-price hit, sector concentration too high)
- Different gates (must be in profit by X%? must have held > 1 year for LTCG?)
- Different UI surface (likely a second tab on Suggestions)
- Different dossier prompt (must include current cost basis, current unrealized gain, tax-implication note for STCG vs LTCG)
- **Includes earnings proximity (was F14)**: yfinance `Ticker.calendar` for held stocks; sell-side penalty for "within 5 days of earnings" (too noisy); buy-side adds a gate to skip suggesting buys within 5 days of earnings of that stock
- Same Sunday cron, runs at 07:00 IST (one hour after buy-side)
- Largest single unit; own chat

**F4. Cron health monitoring — ABSOLUTELY NECESSARY**
- Every cron must write a heartbeat doc to a `cron_heartbeats` collection on completion (success or failure)
- A daily 21:00 IST cron checks "did each registered cron run today?" and fires ntfy on any missed runs or failures
- Phase 1 crons (price refresh, instruments, reconciliation) get instrumented in the same commit
- No silent failures — the user has explicitly demanded this

**F5a. Phase 2 cron registration — ABSOLUTELY NECESSARY**
- `refresh_fundamentals.py` weekly (Sat evening)
- `fetch_news_for_universe.py` daily
- `run_weekly_suggestions.py --notify` Sunday 06:00 IST (buy-side, after F2 also `--direction=sell` at 07:00)
- `track_suggestion_outcomes.py` daily (after EOD price refresh)
- Must be wired with log files AND F4 heartbeats

**F5b. Acted-but-not-held trap fix**
- Currently if user clicks "Acted" but doesn't add to holdings, the stock resurfaces next week
- Fix: soft-exclude `monitored_stocks.status == "tracking" AND acted_at >= now - 30d` from `build_universe`
- Small change in `suggestion_engine.get_excluded_isins` (rename from `get_rejected_isins`)
- Bundled with F6

**F6. Stateful suggestion feedback**
- Replaces the session-scoped vanish-on-click from Commit B with persistent backend exclusion
- `build_universe` excludes:
  - `acted` → permanent (until user manually clears OR adds to holdings → F5b handles this)
  - `passed` → THIS run only (resurfaces next Sunday — market changes)
  - `rejected` → 90 days
- API: each candidate response carries `user_action` field so UI can show "already-actioned" badge instead of just hiding
- Recommended UX: render actioned cards collapsed with a small "✓ acted / ✓ passed / ✓ rejected" badge so user remembers; option to expand
- Frontend removes `actedThisSession` set since backend handles state

**F10. monitored_stocks audit trail**
- Currently feedback history is lost beyond log rotation
- New `monitored_stocks_audit` collection: one doc per feedback action with `isin`, `action`, `previous_status`, `new_status`, `note`, `performed_at`
- Append-only, similar pattern to `transactions_audit`
- Bundled with F6

**F1. Ad-hoc chat about suggestions**
- A chat surface accessible from the Suggestions page where the user can ask the configured AI models questions about the current suggestions
- Purpose: improve suggestions for personal use by interrogating the model
- Uses Sonnet via Anthropic SDK
- State stored in `conversations` collection (already scaffolded)
- System prompt seeded with the current SuggestionRun JSON so the model has context
- Same conversational infrastructure as F3 — ship together

**F3. Ad-hoc chat about a specific holding**
- A chat surface accessible from each holding's detail page
- User pastes a tip from family/friend; the model analyzes it in context (cost basis, current price, recent news, sector, position size) and gives a non-prescriptive view
- Shares conversational infrastructure with F1
- System prompt seeded with the holding's full state + recent news + portfolio context

**F12. Concentration & risk dashboard**
- New endpoint `/portfolio/risk-summary` that returns alerts:
  - Single-stock concentration > 15%
  - Sector concentration > 30%
  - Correlated-group concentration (e.g., energy+utilities) > 20%
- Frontend renders as a card on dashboard
- Maps to "avoid mistakes" lever — over-concentration is how most retail loses money
- Bundled with F15

**F15. Tag-based portfolio views**
- The `holdings.tags` field already exists and is editable; nothing consumes it
- Add: backend filtering + aggregation by tag, frontend filter chips on dashboard
- Aggregate performance by tag (are "high-conviction" picks actually beating "tactical" picks?)
- F2 sell-side respects tags: "long-term-compounder" only suggests sell on extreme overvaluation
- Bundled with F12

**F13. Watchlist (extends suggestions universe)**
- Ability to put any NSE/BSE stock on a watchlist
- New `status="watchlist"` value in `monitored_stocks`
- `build_universe` becomes: `NIFTY 100 ∪ watchlist − held − excluded`
- Watchlist stocks go through same scoring, same gates, same dossiers — no special-case logic
- IMPORTANT: `refresh_fundamentals.py` must be extended to include watchlist ISINs (currently NIFTY 100 + held only)
- IMPORTANT: `fetch_news_for_universe.py` must be extended similarly
- Frontend: "Watch" button on suggestion cards and holding detail pages, plus a `/watchlist` page
- Future chat features (F1/F3) can reference watchlist stocks
- Shipped after F2 so the universe-extension pattern is established

**F11. Capital gains pack (re-scoped from FY tax pack)**
- Small reformatter on top of existing `transactions` + `recompute_holding` data
- Surfaces STCG/LTCG by FY, with per-trade breakdown
- New endpoint `GET /tax/capital-gains?fy=YYYY-YY`
- Simple frontend page that renders the breakdown
- No new computation — everything is already produced by FIFO
- Useful for CA at year end

**Realized P&L UI hiding (small cleanup, bundled in Chat 8)**
- Remove `realized_pnl` stat card from dashboard
- Remove `realized_pnl` row from holding detail
- Remove "Exited holdings" surface from main nav (still accessible via transactions search)
- KEEP `realized_pnl` on reconciliation page (debugging aid for drift alerts)
- KEEP all backend computation untouched (structural; FIFO produces it as a side-effect)

**F5c. Tech debt commit**
- `monitored_stocks.status` Literal vs actual writes mismatch: update model to `Literal["tracking", "passed", "rejected", "watchlist"]` and add the fields the writer actually uses
- Delete dead `app/models/news_article.py` after confirming no imports
- Update `docs/data_flow.md` to document Phase 2 collections and invariants from Section 12
- Reconcile two-paths drift: `digest_delivery.py` has its own copy of Resend + ntfy code rather than using `notify.py` wrappers — pick one path
- Bundled with F5d in Chat 8

**F5d. README updates**
- Backend README still says Phase 2 is "what's next" with the old 2.1/2.2/2.3/2.4 ordering — rewrite to reflect what actually shipped
- Frontend README review

**F7. One-time real data import — DONE LAST (Chat 9)**

This is intentionally the final chat. Reason: every preceding chat will create test artifacts (test feedback rows, test SELL transactions, test conversations, test heartbeats, etc.). If we load real data first, every test session corrupts production state. Loading last means F7 becomes the natural reset button — every test artifact gets wiped clean as part of going live.

Design:
- Backend-only wrapper script `refresh_from_icici.py` (no UI — agreed overkill for one-time use)
- Reads CSVs from `~/ai-stock-advisor-backend/data/icici/orderbooks/<FY>.csv` (gitignored)
- Pipeline: `import_orderbooks.py` → `add_manual_transactions.py` (idempotent) → `reconcile_staging.py` (report) → gated `promote_staging.py --confirm --wipe-live`
- Default behavior: wipe-and-replace (only `transactions`, `transactions_staging`, `holdings`)
- Safety rail INVERTED: `--keep-ui-trades` flag for the rare case where you want to merge in trades entered through the UI after the import (instead of the original "wipe is opt-in" design — since this runs last, wipe IS the feature)
- Other collections (`monitored_stocks`, `conversations`, `cost_basis_adjustments`, `user_profile`, `instruments_fundamentals`, `prices_daily`, `prices_intraday`, etc.) are NOT wiped — they're either re-seeded automatically (cost basis) or contain valid history we want to keep
- After go-live, ALL future trades go through the Buy/Sell UI (which writes through `validate_replay`, audit, and `recompute_holding`). Never re-run this script except for a deliberate full reset.

Chat 9 is really a checklist, not a feature build:
1. Pull latest ICICI Order Book CSVs (one per FY)
2. Pull current ICICI Demat Holdings snapshot (for reconciliation target numbers)
3. Run wrapper script (wipes by default)
4. Inspect reconciliation report
5. Fix any drift via `add_manual_transactions.py` for cost basis splits, missing IPOs/bonuses
6. Re-reconcile until clean
7. Confirm dashboard, holdings, drill-down, suggestions all show real data
8. Run first real `run_weekly_suggestions.py --notify` and verify email arrives

The wrapper script itself is ~50 lines of glue; can be written at the start of Chat 9.

### Final chat split plan

| # | Chat | Scope | Why this order |
|---|---|---|---|
| 2 | Cron observability | F4 + F5a | Smallest, lowest risk; gets system actually running autonomously |
| 3 | Stateful suggestions | F6 + F5b + F10 | Replaces session-scoped vanish with proper backend state; closes the acted-not-held trap; adds audit trail |
| 4 | Sell-side suggestions | F2 (includes earnings proximity from F14) | Largest single unit; own chat |
| 5 | Chat features | F1 + F3 | Shared conversational infra |
| 6 | Portfolio intelligence | F12 + F15 | Both small, both map to "avoid mistakes" / "buy-sell better" |
| 7 | Watchlist | F13 | After sell-side so universe-extension pattern is established |
| 8 | Pre-launch cleanup | F11 + realized P&L hide + F5c + F5d | Tidy before going live |
| **9** | **GO LIVE** | **F7 one-time real data import** | **Tests are done; test pollution gets wiped; tool becomes real** |

7 working chats + 1 import chat = 8 total chats to ship everything.

## Section 14: Conventions the assistant has repeatedly drifted on

The assistant has confused these multiple times in past chats. Memorize them.

1. Port 8001 (Mac local), port 8000 (EC2). Always specify which.

2. Secrets path on EC2 is `/etc/portfolio-advisor/secrets.env` — NOT `~/secrets/secrets.env`. The latter was a transient debug artifact. Confirmed by `find` on the live EC2.

3. `lib/api.ts` is hand-typed (~600 lines). The auto-generated `lib/api-types.ts` is gitignored and not used at runtime. When extending types, edit `lib/api.ts` directly. When the file is becoming long, prefer additive patches over full replacement.

4. Mutations in frontend use `refetchQueries` (synchronous, blocks until refetch finishes so toast appears AFTER fresh data), NOT `invalidateQueries` (lazy).

5. `cn` helper is at `@/lib/utils` (clsx + tailwind-merge).

6. Format helpers at `@/lib/format`: `inr(value)`, `pct(value, withSign?)`, `colorForChange(value)`, `dateTime(iso)`, `nf`, `date(iso)`.

7. `Collections` accessor: `from app.db.client import Collections`, then `Collections.holdings()`, etc. Never raw `db["holdings"]`.

8. Decimal128 vs Decimal: helpers in `app/models/_common.py`. Mongo stores Decimal128; Python code works with Decimal; conversion happens at the boundary.

9. Datetimes: UTC-naive in Mongo. IST in UI. `utcnow()` from `app/models/_common.py`. Watch for naive-vs-aware errors — the codebase has hit this multiple times.

10. Heredoc for multi-line Python in shell: use `<<'EOF'` form, NOT nested `bash -c "..."`.

11. Original `SuggestionCard` takes parent-owned mutation via `onFeedback` callback and `feedbackPending` prop. Mutation lives in parent. Do not redesign.

12. `/suggestions` page uses shadcn Tabs. Do not replace with custom button toggles.

13. Existing card structure: top bar with back link, header with refresh, error/empty/loading states, then Tabs with three values: "latest" / "performance" / "history". Performance and history tabs use `enabled: activeTab === "..."`.

14. Original `SuggestionCard` has helpers `Section`, `DossierSection`, `GroupBar`, etc. inline at the bottom of the same file. Keep them or evolve them; don't extract or rename without reason.

15. Tailwind v4 + shadcn `.dark` class pickup is automatic — don't add explicit `useTheme` calls just to flip colors.

## Section 15: Anti-patterns the assistant has fallen into

These have caused real rework. Avoid.

1. Full-file rewrites instead of additive patches. Once file is long, rewrite invites drift and inflates diff. For `lib/api.ts` specifically: always patch additively unless explicitly asked.

2. Inventing parallel patterns. If page uses shadcn Tabs, don't introduce a custom Toggle. If card uses parent-owned mutations, don't switch to internal mutations.

3. Trusting memory for function names / response shapes / paths. RE-READ AT HEAD before patching.

4. Truncating code with "rest unchanged" or "// existing code here". Forbidden.

5. Asking "is this OK?" without applying the edit. If user has asked for the edit, apply it.

6. Micro-commits when meaningful units of work are expected.

7. Assuming GitHub content is current. Always check commit SHA.

8. Producing files significantly larger than originals. If existing is 600 lines and new is 1,200, something is wrong. Halt and explain.

9. Inventing fields in API responses. If unsure, hit the live endpoint and inspect.

10. Forgetting to call `enrich_run` from new endpoints. Any `/suggestions/...` endpoint returning a SuggestionRun-shaped response should go through `_serialize_run`.

11. Forgetting `holdings.deleted_at = None` is universal.

12. Generating cron entries without log file paths or heartbeat monitoring. Per F4, no silent failures.

13. Designing UI/UX features that aren't requested (e.g., a `/news` page when news only feeds dossiers; a backtesting UI; visual heatmaps). The tool is decision-support, not consumption.

## Section 16: "I am losing context" — escalation protocol

When the assistant notices ANY of the following symptoms, it must say verbatim:

> I AM LOSING CONTEXT

so the user can switch to a new chat. Better to escalate early than ship a broken commit.

### Triggers (any one is sufficient)

- Cannot recall a specific file structure that was discussed earlier in the chat
- Conflating Phase 1 facts with Phase 2 facts
- Forgetting which Commit (A, A.5, A.5.1, B) shipped which behavior
- Producing a file significantly larger than the original (>1.5x line count) without an explicit reason
- Starting to use generic patterns (e.g., shadcn defaults) instead of project conventions (e.g., the project's existing `Section`, `GroupBar`, `DossierSection`)
- Forgetting the port difference between Mac and EC2
- Forgetting the secrets path
- Forgetting the chat split plan from Section 13
- The user has to correct the same drift twice in the same chat
- The assistant has called `glean_document_reader` or `code_search` more than ~15 times in a single chat without converging
- The "Truncation Notice" appears in the assistant's context (the system tells the assistant earlier messages were dropped)
- The assistant is about to produce a third large code artifact and is unsure whether prior decisions still apply

### What "switching chats" means

The user copies the bootstrap prompt from Section 0 into a fresh chat. The new chat reads PROJECT_STATE.md first, then both repos at HEAD, then `docs/data_flow.md`, then READMEs. The user states the scope. The assistant summarizes back. Only then does coding start.

The new chat is responsible for updating PROJECT_STATE.md at the end of its work, as the last commit, so the next chat is bootstrapped from current state.

### What NOT to do

- Do not silently degrade. User has explicitly said "don't silently degrade."
- Do not try to "wing it" through context loss. Ship-quality code requires full context.
- Do not produce artifacts when uncertain about conventions.

## Section 17: "Am I hallucinating?" diagnostic questions

If the user suspects the assistant has drifted, the user can ask any of these. The assistant should be able to answer all correctly without re-reading. If any wrong, switch chats.

1. "What's the backend port on Mac local?" → 8001
2. "What's the backend port on EC2?" → 8000
3. "Where do secrets live on EC2?" → `/etc/portfolio-advisor/secrets.env`
4. "Where do secrets live on Mac?" → `<repo>/.env` (resolved via `LOCAL_SECRETS` fallback)
5. "What does `recompute_holding(isin)` do?" → It is the only authoritative writer to `holdings`. Idempotent. Recomputes from `transactions` from scratch using FIFO. Always call after a transaction change.
6. "What's the gating filter on `snapshot_open_outcomes`?" → `tracking_status != "expired"` (was `== "open"` pre-Commit-A.5)
7. "Where does the dossier `plain_english_summary` field originate?" → `dossier_service.py`'s `_SYSTEM_PROMPT`, Sonnet, max 500 chars. Added in Commit A.
8. "What is the universe filter in `build_universe`?" → NIFTY 100 (`instruments.in_nifty100 == True`) ∪ watchlist (after F13) − held (`holdings` where `deleted_at == None`) − excluded (rejected 90d, passed this-run-only after F6, acted permanently after F6)
9. "What's the Q/V/M/N weight breakdown?" → 30% / 25% / 25% / 20%, version `"1.0.0-unit2"`
10. "Is `lib/api-types.ts` checked into git?" → No, gitignored. Auto-generated by `npm run gen-api`. Hand-typed source is `lib/api.ts`.
11. "What does the user prefer: refetchQueries or invalidateQueries?" → `refetchQueries` (synchronous)
12. "What is the sell endpoint's response shape?" → Either full updated Holding doc (partial sell) or `{message, realized_total}` (full exit). Discriminated via type guard on `_id`.
13. "Is dividend tracking part of this project?" → No. Dropped. Dividends settle to user's bank account; this tool is not an accounting system.
14. "When does F7 (real data import) run in the chat sequence?" → Last. Chat 9. After all features are built and tested, so test pollution gets wiped on go-live.

## Section 18: Tech debt registry (filed, not fixed)

Tracked here so nothing gets lost. Cleared as part of Chat 8 (F5c + F5d).

1. `app/models/monitored_stock.py` — `status: Literal["tracking", "promoted_to_holding", "dropped"]` does not match writer reality. Writer uses raw `update_one` so Pydantic is bypassed. After F13 ships, will also need `"watchlist"` value.

2. `app/models/news_article.py` — Older parallel model. Live model is `app/models/news.py`. Pick one and delete the other.

3. `docs/data_flow.md` — Dated 2026-05-09. Missing Phase 2 collections and invariants. Update during F5c.

4. `digest_delivery.py` has its own inline copies of Resend + ntfy code instead of using `notify.py` wrappers. Two paths. Pick one.

5. `dossier_service.py` `valuation_verdict` is a single string with both label and rationale. To color-code labels, split into `valuation_label` and `valuation_rationale`. Defer until UI needs it.

6. `SignalScore.raw_value` is misnamed — stores normalized 0-100 score, not raw fundamental value. `explainability.py` fetches raw values from `instruments_fundamentals` at API enrichment time as workaround.

7. News signal raw values (`net_sentiment`, `story_velocity`, `story_count`) not persisted post-run. Frontend shows normalized only. Fix would require persisting `news_signals_by_isin` in `SuggestionRun`.

8. Backend `README.md` stale (Phase 2 "what's next" with old ordering).

9. `top_k` default in `scoring_service.DEFAULT_CONFIG` is 10 (correct). CLI script docstring example shows `--top-k 5` which is misleading.

10. `holdings.stop_loss` and `holdings.target_price` fields are editable in UI but nothing consumes them. Either wire to ntfy alerts (intraday price refresh) or remove. Decide during cleanup.

## Section 19: How to update this document

This file is updated at the end of every chat as the LAST commit.

What to update:
1. Section 13 — move shipped items from "open" to "shipped"; add any new open items discovered
2. Section 9 — update cron registry if cron entries were added/changed
3. Section 14 — add any new convention the assistant drifted on
4. Section 15 — add any new anti-pattern that caused rework
5. Section 16 — add any new triggers that should signal context loss
6. Section 17 — add new diagnostic Q&A if a new fact category emerges
7. Section 18 — add/remove tech debt items
8. Section 12 — add any new Phase 2 invariant introduced
9. Section 11 — add any new Phase 1 invariant introduced (rare; Phase 1 is locked)
10. Section 7 — add new collections; update field lists when models change
11. Section 8 — add new endpoints; update existing endpoint shapes
12. Section 5/6 — add new files; remove deleted files

Commit message convention for PROJECT_STATE.md updates:
```
docs: update PROJECT_STATE.md after <chat scope>

- <bullet list of sections changed>
```

If the chat ended due to context loss (per Section 16), the LAST thing the assistant does before stopping is propose the PROJECT_STATE.md update. The user applies it manually since the assistant is no longer reliable.

## Section 20: Trade-off rationale (decisions that might look weird)

For future-you (or a future assistant) who asks "why is this like this":

1. **yfinance over Tijori / Screener Pro**: yfinance is free and works. Tijori is a future upgrade. Screener.in does NOT have a public Pro API (verified). Apify scraper rejected as TOS-gray and brittle. The `FundamentalsProvider` protocol in `fundamentals_service.py` is designed for swap-in replacement.

2. **Confidence is numeric 0-100 with deterministic deductions, not band-only**: Bands hide information. Deductions are stored as plain English strings so they render directly.

3. **Suggestions run Sunday 06:00 IST (buy) and 07:00 IST (sell after F2)**: Sunday because Indian market is closed. Morning so user reads with coffee.

4. **Top-K = 10**: Five was initial; user requested 10 mid-build. Engine default and CLI default are both 10.

5. **90-day rejection cooldown for "rejected"**: Long enough to not nag. Short enough that material change can resurface.

6. **Zero cooldown for "passed" (F6)**: Per user — market conditions change, the same stock can become more relevant next week. "Passed" is "saw it, no opinion right now."

7. **"Acted" should soft-exclude for 30 days (F5b/F6)**: Hidden trap — if you click Acted but don't add to holdings, it resurfaces. Soft exclusion gives ICICI settlement time to land.

8. **Outcome snapshot ignores `tracking_status` for data collection (Commit A.5)**: Was filtering on `"open"` only, which silently broke performance measurement.

9. **Vanish-on-click is session-scoped today (Commit B), persistent after F6**: Initial implementation was simple. F6 makes it correct.

10. **`digest_delivery.py` having its own Resend/ntfy path**: Defer to tech debt commit.

11. **Schema drift on `monitored_stocks.status`**: Defer to tech debt commit; rename ripples.

12. **`enrich_run` mutates dict in-place AND returns it**: Looks weird, works. Input is already a copy.

13. **Why `valuation_verdict` is one string, not `{label, rationale}`**: Sonnet finds it easier per JSON schema. Defer until UI needs color-coding.

14. **Why keep `all_candidates` persisted but strip from API**: Replay-ability for future re-ranking with new weights. Keep payload light.

15. **Dividend tracking dropped (F8)**: User direction. Dividends settle to bank. This tool is for investment decisions, not accounting.

16. **Realized P&L hidden in UI but kept in backend (Chat 8 cleanup)**: User direction. The math is structural (FIFO produces it for free); the UI was clutter. Reconciliation page keeps it as debug aid for drift alerts.

17. **F7 sequenced last (Chat 9)**: Building features first means lots of test data pollution. F7's wipe-by-default behavior becomes the natural reset to clean state on go-live.

18. **F8 dropped instead of "do it later"**: Sahil framed his goal as "grow my money." Dividends auto-arrive in bank; tracking them adds zero decision value. Maintaining a feature that doesn't drive decisions is decoration.

19. **F14 folded into F2 instead of standalone**: Earnings proximity matters most for sell decisions (timing) and as a small gate on buys (skip near-earnings noise). Doesn't justify its own surface.

20. **Watchlist (F13) extends the engine universe, not a separate scoring path**: Watchlisted stocks go through the same gates, scoring, and dossiers. Special-casing would create two parallel pipelines to maintain.

## Section 21: What is intentionally NOT included in this project

So future chats don't accidentally try to add these:

- Auto-trading. Never. Hard constraint.
- Multi-user support. Single-user by design.
- Mutual funds, FDs, foreign equities, derivatives, crypto. NSE/BSE equities only.
- Native mobile app. Web responsive is the plan.
- Tax filing. The system surfaces tax-correct cost basis to inform manual filing. It does not file.
- **Dividend tracking** (F8 dropped). Dividends settle to bank.
- **Accounting or financial planning**. Not the goal.
- **Goal-based planning** ("save X for Y by Z"). Accounting, not investing.
- Real-time tick data. Intraday refresh is every 15 minutes — fine for this user's holding-period.
- A public-facing dashboard. Tailscale only.
- Backtesting framework. Outcome tracking on real suggestions is the on-line equivalent.
- Notification customization UI. Settings live in `secrets.env`.
- Account aggregation (Plaid-equivalent). Data via ICICI ZIP imports + manual entry.
- Social features / comparison to other investors.
- Technical indicator alerts (RSI, MACD, etc.). Noise at retail scale.
- Options tracking. User doesn't trade options.
- Index fund comparison page. `compute_system_performance` already gives excess return vs EW NIFTY 100.
- A separate `/news` page. News feeds dossiers; standalone news consumption is time-sink.
- Heatmap / pretty visualizations. Visual fidelity ≠ signal.
- Portfolio rebalancing recommender (target-allocation based). User has no target allocation, by design.
- Social sentiment tracking. High noise, low signal.

## Section 22: Glossary

- **ISIN**: International Securities Identification Number. 12-char unique identifier. Primary key for stocks. NSE/BSE quotes for the same company share an ISIN.
- **NSE**: National Stock Exchange of India.
- **NIFTY 100**: Index of top 100 NSE stocks by market cap. The Suggestions universe.
- **FIFO**: First-in-first-out cost basis. Required by Indian Income Tax Act.
- **LTCG / STCG**: Long-Term / Short-Term Capital Gains. >1 year holding = LTCG, ≤1 year = STCG. Tax rates differ.
- **Section 49(2C)**: IT Act clause governing cost basis allocation in demergers.
- **ICICI Direct**: The user's broker.
- **ICICI ZIP**: CSV exports from ICICI's "Order Book" download.
- **TMPV / TMCV**: Tata Motors PV and CV, split via demerger Oct 2025. Cost basis 68.85/31.15.
- **EW NIFTY**: Equal-weighted NIFTY 100 return — benchmark for outcome tracking.
- **Composite score**: 0-100, weighted sum of Q/V/M/N normalized scores.
- **Confidence score**: 0-100, deterministic, from data freshness + signal availability.
- **Dossier**: Sonnet-generated per-candidate research note (plain_english_summary, one_line_thesis, bull/bear/risks, valuation_verdict, portfolio_fit).
- **Outcome**: `suggestion_outcomes` doc tracking what happened to a suggested stock vs benchmark over 30/60/90/180 days.
- **Bucket**: User-action label on an outcome (open/acted/passed/rejected/expired).
- **Watchlist**: User-curated list of stocks outside NIFTY 100 that should be considered by the engine (F13).

End of PROJECT_STATE.md.
