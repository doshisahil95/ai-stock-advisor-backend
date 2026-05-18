
# PROJECT_STATE.md

Living source of truth for the Personal AI Stock Advisor.
Updated at the end of every chat.

This file is the bootstrap document for any new conversation with an AI assistant.
If you (the assistant) are reading this for the first time in a new chat: read it top to bottom before doing anything.
Do not skim.
Do not assume.
Do not redesign.
The prior chat hit context limits or context drift — that's why we're here.

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

GitHub content may be cached.
Whenever you read a file, capture the commit
SHA you read at, and re-read if the user tells you they have pushed since.

Today's scope is: <DESCRIBE THE FEATURE OR FIX FOR THIS CHAT>

Hard rules:
- Do not invent parallel patterns.
  Evolve existing code, don't redesign.
- Re-read files at HEAD before patching them.
  Do not trust memory.
- Hand me full file contents OR exact find-and-replace.
  Never "rest unchanged".
- Use canvas artifacts for files.
  Use chat for tests.
- PROJECT_STATE.md is ALWAYS delivered as a complete full-file replacement,
  never as a patch, find-and-replace, or "rest unchanged".
  No exceptions,
  no matter how small the edit.
- Every code/file change MUST be followed by a `git add .` + `git commit -m`
  block in chat, ready to paste, written in the project's commit-message style.
- Every test block MUST begin with `ssh ubuntu@100.112.20.41` and run curls
  against `localhost:8000` from inside the box (not against the Tailscale IP
  from the laptop).
- In every mapping table, the Action column must say NEW FILE, REPLACE
  EXISTING, or PATCH.
- BEFORE constructing any class or dataclass via `Foo(field=...)`, run
  `grep -A 20 "class Foo" <path>` on the actual file on disk and verify
  every field name you reference. Glean snippets are often call sites or
  docstrings, NOT the @dataclass definition. Three field-name drifts in
  Chat 4 forced this rule. (See Section 14.)
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

Personal AI Stock Advisor.
Single-user portfolio + research tool for Indian NSE equities.
Built for and by Sahil Doshi (Senior Consulting Engineer, MongoDB, India).

Strict design constraint that overrides everything else: the system never executes trades.
Sahil trades manually in ICICI Direct.
The system records, analyzes, and advises only.
Any feature that would auto-place an order is out of scope, permanently.

The system is also not regulatory advice.
Dossiers and suggestions must use phrasing like "the system flagged this because..." and "this is a good buy because..." or "this is a good sell because...".
The user decides; the user trades.

The goal of the system is to maximise the investments.
Goal of the tool: grow money.
Every feature is judged on whether it helps with one of:

- Buy better (find opportunities you'd otherwise miss)
- Sell better (exit before reversals, hold through noise)
- Avoid mistakes (concentration, FOMO, panic sells, missed corporate actions)
- Reduce costs (taxes, fees, opportunity cost of dead capital)

Anything that doesn't map to one of these is decoration and gets cut.

Explicitly NOT a goal: dividend tracking, accounting, financial planning, tax filing, goal-based planning.
The tool informs investment decisions; bank statements and the CA handle the rest.

## Section 2: User communication preferences (apply to all chats)

- Honest, slightly contrarian opinions over fake agreement.
  The user will push back when he disagrees; the assistant must do the same.
- Build right, no shortcuts.
  Do not introduce avoidable rework.
- Math accuracy and legal compliance matter.
  If something is mathematically wrong or legally non-compliant, call it out immediately.
- Use existing project conventions.
  Do not invent parallel patterns.
- Give full file contents OR exact find-and-replace instructions.
  Never use placeholders like "rest unchanged" or "// existing code here".
  Do not truncate important code.
- Prefer meaningful units of work.
  Small enough to test, not so tiny that we ping-pong.
- Give concrete test commands when appropriate.
- Files go in canvas artifacts.
  Tests go in chat as fenced code blocks.
- Every mapping table must use Action column values: NEW FILE, REPLACE EXISTING, or PATCH.
- The user edits on Mac, commits, pushes.
  EC2 is for build/test/deploy/debug.
  The assistant should not edit Mac files directly; it produces artifacts the user pastes.
- Every code/file delivery in chat MUST be followed by a paste-ready `git add .` + `git commit -m "..."` block in the project's existing commit-message style.
- Every test block in chat MUST start with `ssh ubuntu@100.112.20.41` and run subsequent curls against `localhost:8000`.
  Do not give curls against the Tailscale IP from the Mac.
- PROJECT_STATE.md is ALWAYS delivered as a complete full-file replacement, never a patch or diff or find-and-replace.
  No exceptions.

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
- ntfy (push notifications — public ntfy.sh for all paths after F2b; self-hosted private path is still installed on EC2 but no longer used and pending decommission — see Section 18)

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
- EC2 Tailscale IP: `100.112.20.41`
- SSH from Mac: `ssh ubuntu@100.112.20.41`
- Backend port on EC2: `8000`
- Frontend port on EC2: `3000`
- Backend port on Mac (local dev): `8001` (NOT 8000)
- Frontend port on Mac (local dev): `3000`

This Mac vs EC2 port difference is a real, recurring source of confusion for assistants.
The assistant has gotten this wrong multiple times.
Always specify which machine when giving test commands.
For chat-supplied test blocks, the standing convention is "SSH into EC2 first, then curl localhost:8000" — see Section 14.

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

The `Settings` class uses pydantic-settings with `model_config = SettingsConfigDict(env_file=str(SECRETS_FILE), env_file_encoding="utf-8", case_sensitive=True, extra="ignore")`.
Pydantic-settings reads the file directly into the `Settings` object — secrets are NOT exported to `os.environ`.

If the assistant ever suggests `~/secrets/secrets.env` on EC2, it is wrong.
That path was a transient debug artifact.

F2b addition (Chat 4): `NTFY_PUBLIC_TOPIC_DIGESTS` must be present in `/etc/portfolio-advisor/secrets.env` — required (no default). If missing, app startup fails with a Pydantic validation error. Subscribe the iPhone ntfy app to the topic value before running cron.

### Deploy scripts
On EC2:
- `~/deploy.sh` — pulls backend, runs `uv sync`, restarts `portfolio-advisor.service`
- `~/deploy-ui.sh` — pulls frontend, runs `npm install --legacy-peer-deps`, runs `npm run gen-api`, runs `npm run build`, restarts `portfolio-advisor-ui.service`

The `gen-api` step in `deploy-ui.sh` regenerates `lib/api-types.ts` against the running backend's OpenAPI spec.
That file is gitignored.
On Mac, running `npm run gen-api` without overriding the URL will fail because Mac backend is on port 8001 and the default is 8000.
Use:

```
API_OPENAPI_URL=http://100.112.20.41:8000 npm run gen-api
```

or just skip it — `lib/api-types.ts` is not used at runtime; `lib/api.ts` is hand-typed.

### systemd units on EC2
- `portfolio-advisor.service` — runs `uvicorn app.main:app --port 8000 --host 0.0.0.0` as user `ubuntu`, with `EnvironmentFile` NOT used (settings.py loads from `/etc/portfolio-advisor/secrets.env` directly), `Environment="PYTHONPATH=/home/ubuntu/ai-stock-advisor-backend"`, `Environment="PYTHONUNBUFFERED=1"`.
  Logs to journald.
- `portfolio-advisor-ui.service` — runs `node /home/ubuntu/ai-stock-advisor-frontend/node_modules/next/dist/bin/next start` on port 3000 with hardening (`NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict`, `ReadWritePaths` includes the frontend dir and `/tmp`).

A sudoers entry at `/etc/sudoers.d/portfolio-advisor-systemctl` lets `ubuntu` restart these services without password.

### Repos
- Backend: https://github.com/doshisahil95/ai-stock-advisor-backend
- Frontend: https://github.com/doshisahil95/ai-stock-advisor-frontend

GitHub is the source of truth for code.
GitHub may serve cached content via Glean's reader.
When in doubt, find the latest commit SHA and read at that SHA explicitly.

## Section 5: Backend file map

Directory layout under `app/`:

```
app/
  main.py                     FastAPI bootstrap, router includes, lifespan
  config/
    settings.py               pydantic-settings, loads secrets file
                              F2b: NTFY_PUBLIC_TOPIC_DIGESTS (required)
  db/
    client.py                 Mongo client, get_db(), Collections accessor class
                              (incl. Collections.monitored_stocks_audit() — F10)
                              (incl. Collections.earnings_calendar() — F14)
    indexes.py                ensure_indexes() called on startup
                              (incl. monitored_stocks_audit indexes — F10)
                              (incl. earnings_calendar indexes — F14)
  models/
    _common.py                utcnow(), Decimal128 helpers, ObjectId helpers
    instrument.py             Instrument (NSE master record)
    holding.py                Holding (active position)
    transaction.py            Transaction (BUY/SELL/SPLIT/BONUS/DEMERGER)
    fundamentals.py           InstrumentFundamentals (per-ISIN, per-refresh)
    earnings_event.py         F14: EarningsEvent (one doc per ISIN per earnings_date)
    suggestion.py             SuggestionRun, SuggestionOutcome, CandidateScore,
                              SignalScore, GateResult
                              F2: SuggestionDirection literal; direction field
                              on SuggestionRun and SuggestionOutcome (default
                              "buy" so pre-F2 docs coerce cleanly)
    news.py                   NewsArticle (live model)
    news_article.py           DEAD; older parallel model, do not use, do not import
    monitored_stock.py        MonitoredStock; Literal status is DRIFTED (see tech debt)
    macro_signal.py           placeholder
    conversation.py           placeholder (will be used for chat features F1/F3)
    reconciliation.py         ReconciliationSnapshot
    cost_basis_adjustment.py  CostBasisAdjustment
  routers/
    holdings.py               /portfolio/holdings, /portfolio/holdings/{isin},
                              /sell, /preview-sell, /history, /transactions
    portfolio.py              /portfolio/summary
    transactions.py           /transactions/search, /transactions/{id} CRUD,
                              /transactions/audit/recent, /transactions/{id}/audit
    reconciliation.py         /reconciliation/snapshot, /snapshots, /auto-snapshot
    instruments.py            /instruments (symbol_overrides CRUD)
    cost_basis.py             /cost-basis/adjustments
    suggestions.py            /suggestions/latest, /runs, /runs/{id},
                              /performance, /{isin}/feedback,
                              /{isin}/audit, /feedback/audit/recent (F10)
                              F2: ?direction=buy|sell on /latest, /runs,
                              /performance. /runs/{id} unchanged (direction
                              is implicit in the stored doc).
    cron.py                   /cron/heartbeats (F4 — health summary +
                              recent heartbeats; mirrors reconciliation.py
                              local _serialize helper)
  services/
    instrument_service.py     lookup_isin, bulk_lookup_isins, refresh
    price_service.py          EOD + intraday fetch, bulk_get_latest_prices,
                              annotate_with_current_price, get_previous_close
    holdings_service.py       recompute_holding, validate_replay, preview_sell,
                              _to_decimal helper
    portfolio_service.py      compute_summary
    transactions_audit_service.py  log_change, get_audit_for_transaction
    monitored_stocks_audit_service.py  F10: log_change (write-before-apply),
                                       get_audit_for_isin, get_recent_audit
    reconciliation.py         take_auto_snapshot, drift detection
    cost_basis_service.py     get_active_adjustments, total_adjustment_amount
    fundamentals_service.py   yfinance provider, refresh_one, refresh_universe,
                              get_latest_for_isin, get_latest_bulk, is_fresh,
                              _normalize_debt_to_equity, _normalize_dividend_yield
                              F14: fetch_earnings_calendar_yfinance,
                              refresh_earnings_for, refresh_earnings_universe,
                              get_next_earnings_for_isin, get_next_earnings_bulk,
                              _sanitize_for_bson (yfinance dates coerce)
    tavily_client.py          quota-tracked wrapper, TavilyQuotaExceeded
    news_fetcher.py           fetch_for_instrument, fetch_for_universe
    news_classifier.py        Haiku batch classifier, retry pass
    news_signals.py           compute_news_signals_for_isin, _bulk
    scoring_service.py        extract_signals, score_candidates,
                              Q/V/M/N weights, gates, version "1.0.0-unit2"
                              F14: evaluate_earnings_proximity_gate (shared);
                              evaluate_gates accepts optional next_earnings;
                              score_candidates accepts optional
                              next_earnings_by_isin (buy-side wires it in
                              suggestion_engine).
                              F2: DEFAULT_SELL_CONFIG, GROUP_SIGNALS_SELL,
                              extract_sell_signals, evaluate_sell_gates
                              (in_profit, min_position_age, earnings_proximity),
                              score_sell_candidates. score_group +
                              composite_for_candidate refactored to accept
                              optional group_signals_def (back-compat with
                              GROUP_SIGNALS default).
    dossier_service.py        generate_dossiers_for_top_k, Sonnet,
                              plain_english_summary in schema
                              F2: _SYSTEM_PROMPT_SELL with tax_consideration +
                              concentration_note; _parse_dossier required
                              fields switch on direction; per-candidate
                              POSITION CONTEXT block (cost basis, unrealized
                              gain %, tax window, portfolio weight, next
                              earnings) appended for sell-side.
    suggestion_engine.py      run_suggestions (full pipeline);
                              get_excluded_isins (F6+F5b: rejected 90d,
                              passed this-run, acted 30d)
                              F2: run_suggestions(direction="buy"|"sell")
                              dispatches to _run_buy_pipeline (F14 gate now
                              activated) or _run_sell_pipeline (universe =
                              active holdings, portfolio_value computed via
                              bulk_get_latest_prices, sell-side scoring +
                              dossier).
    outcome_tracker.py        create_outcomes_for_run, snapshot_open_outcomes,
                              compute_system_performance
                              F2: create_outcomes_for_run stamps direction;
                              compute_system_performance accepts optional
                              direction filter and sign-flips excess_return
                              for sell-side at read time.
    digest_delivery.py        send_weekly_digest (Resend + ntfy)
                              F2b: ntfy via push_public("digests", ...) on
                              public ntfy.sh; private path retired here.
                              F2 (Chat 4): send_combined_digest(buy_run,
                              sell_run) for the --direction=both cron path.
                              KNOWN BUG: sell-side sections (in both
                              send_weekly_digest sell standalone AND
                              send_combined_digest sell section) render
                              Q=V=M=N=0 because CandidateScore has fixed
                              buy-side group fields; sell-side group scores
                              live separately. See Section 18.
    explainability.py         SIGNAL_META, GROUP_META, GATE_META, FEEDBACK_META,
                              PAGE_INTRO, enrich_run, enrich_candidate;
                              _load_monitored_bulk + _build_user_action (F6)
                              F2: SIGNAL_META extended (unrealized_gain_pct,
                              target_price_proximity, portfolio_weight_pct,
                              is_ltcg_eligible, high_severity_negative_count).
                              GROUP_META extended (booking_opportunity,
                              valuation_stretch, risk, tax_concentration).
                              GATE_META extended (earnings_proximity,
                              in_profit, min_position_age).
                              _GROUP_TO_SIGNALS extended for sell groups.
                              NOT YET DONE: enrich_run page_intro still
                              buy-centric for sell runs.
    notify.py                 push_private, push_public, email (generic wrappers;
                              digest_delivery uses its own copies of Resend +
                              ntfy code, not these — that's intentional drift).
                              PublicChannel now includes "errors" (F4) and
                              "digests" (F2b)
    cron_heartbeat_service.py F4: cron_run context manager, CRON_REGISTRY,
                              get_recent_heartbeats, get_latest_per_cron,
                              count_today_heartbeats, ist_today_window_utc,
                              is_expected_today
                              F2: CRON_REGISTRY includes
                              "weekly_suggestions_sell" CronSpec.
                              CONVENTION (Section 14): CronSpec fields are
                              (cron_name, description, schedule_human,
                              expected_weekdays, min_runs_per_day=1). Three
                              field-name drifts in Chat 4 produced this rule.
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
    refresh_fundamentals.py        F14: default universe is now NIFTY 100 ∪
                                   active holdings (held stocks outside
                                   NIFTY 100 still need fundamentals +
                                   earnings for F2 sell-side); folds earnings
                                   refresh into the same Sunday cron via
                                   refresh_earnings_universe.
                                   --holdings-only and --symbols overrides
                                   preserved.
    fetch_news_for_universe.py
    run_weekly_suggestions.py      F2: --direction=buy|sell|both (default
                                   "buy"). "both" runs buy then sell under
                                   ONE heartbeat and emits ONE combined
                                   digest via send_combined_digest.
                                   --no-notify skips outcomes + digest.
                                   --skip-dossiers skips Claude (smoke-test
                                   only; not for production).
                                   _do_buy/_do_sell/_do_both call sites use
                                   ctx.meta = {...} (NOT ctx["meta"] — see
                                   Section 14).
    track_suggestion_outcomes.py
    cron_health_check.py           F4: daily 21:00 IST; reads CRON_REGISTRY +
                                   today's heartbeats; fires single batched
                                   push_public("errors", ...) on anomalies
docs/
  data_flow.md                  Phase 1 invariants; missing Phase 2 collections
  PROJECT_STATE.md              THIS FILE
pyproject.toml
README.md                       stale; says Phase 2 is "what's next" with old ordering
```

## Section 6: Frontend file map

Directory layout:

```
app/
  layout.tsx                  root layout, fonts, ThemeProvider, QueryProvider
  page.tsx                    dashboard
  globals.css                 Tailwind v4 imports, font variable mappings,
                              shadcn .dark class
  holdings/[isin]/page.tsx    single holding drill-down
  reconciliation/page.tsx
  cost-basis/page.tsx
  transactions/page.tsx
  transactions/audit/page.tsx
  suggestions/page.tsx        F6: no actedThisSession; user_action stamp from
                              backend drives the collapsed-card render
                              F2: PENDING (next chat) — Buy/Sell toggle,
                              direction-aware fetch, sell-side dossier
                              rendering (tax_consideration +
                              concentration_note instead of portfolio_fit),
                              sell-side group_meta display
                              (booking_opportunity/valuation_stretch/risk/
                              tax_concentration instead of Q/V/M/N)
components/
  ui/                         shadcn primitives (button, card, dialog, popover,
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
  suggestion-card.tsx         full explainability layer (Commit B);
                              F6: CollapsedFeedbackRow when user_action != null
                              F2: PENDING (next chat) — branch on
                              dossier.direction to render tax_consideration +
                              concentration_note for sell, portfolio_fit for
                              buy; sell-side group bars from group_meta
  explain-popover.tsx         reusable info-icon popover (Commit B)
  page-intro.tsx              "How to read this page" collapsible (Commit B)
lib/
  api.ts                      hand-typed API client; SINGLE SOURCE OF TRUTH for
                              frontend types; ~600 lines.
                              F6+F10: UserAction, MonitoredStocksAuditEntry,
                              getRecentFeedbackAudit, getFeedbackAuditForIsin,
                              previous_status on submitFeedback response,
                              excluded_acted on SuggestionRun
                              F2: PENDING (next chat) — SuggestionDirection
                              type, direction param on getLatestRun /
                              listRuns / getPerformance, direction on
                              SuggestionRun + SuggestionOutcome + Dossier
  api-types.ts                GITIGNORED; auto-generated by `npm run gen-api`;
                              not actually used at runtime; do not check in
  format.ts                   inr(value), pct(value, withSign?),
                              colorForChange(value), dateTime(iso), nf, date
  utils.ts                    cn() (clsx + tailwind-merge)
  config.ts                   apiBaseUrl (reads NEXT_PUBLIC_API_BASE_URL env)
  query-client.tsx            TanStack Query provider
package.json
tsconfig.json                 paths: "@/*" -> "./*"
```

## Section 7: Database collections (exhaustive)

All collections live in MongoDB Atlas M10.
The DB name is set by env (`MONGODB_DB_NAME`).
All collections accessed via `Collections.<name>()` from `app.db.client`.
Indexes ensured at startup via `app/db/indexes.py`.

### Phase 1 collections

#### `instruments`
- Master NSE/BSE instrument list, refreshed daily from Zerodha Kite instruments CSV
- Key fields: `exchange`, `symbol`, `isin`, `name`, `instrument_type`, `segment`, `lot_size`, `tick_size`, `source`, `last_seen_at`, `last_changed_at`, `in_nifty100`
- Count: ~2,368 total; 100 with `in_nifty100=True`
- Indexes: `(exchange, symbol)` unique, `isin`, `last_seen_at`, `last_changed_at`, `in_nifty100`
- Writer: `scripts/refresh_instruments.py` (delta-aware), `scripts/seed_nifty100.py`, manual upserts for BSE-only stocks

#### `symbol_overrides`
- Manual ISIN aliases when the master list is wrong or missing
- Key fields: `exchange`, `symbol`, `isin`, `reason`, `created_at`
- Writer: `/instruments` router (CRUD)

#### `holdings`
- Active positions, one doc per ISIN; soft-deleted on full exit
- Key fields: `isin`, `symbol`, `exchange`, `name`, `sector`, `industry`, `quantity` (Decimal128), `avg_cost`, `invested_amount`, `realized_pnl`, `first_purchased_at`, `last_traded_at`, `thesis`, `notes`, `stop_loss`, `target_price`, `tags`, `deleted_at`
- INVARIANT: every query MUST include `deleted_at: None` to see active holdings; deleted holdings preserve replay correctness (FIFO needs full history)
- Indexes: `isin` unique (partial: only where `deleted_at` is None), `(deleted_at, last_traded_at)`
- Writer: `recompute_holding(isin)` in `holdings_service.py` is the ONLY authoritative writer; idempotent; recomputes from transactions from scratch using FIFO
- Note: `realized_pnl` is structural (FIFO computes it as a side-effect) but per user direction is HIDDEN in UI (see Section 13, Cleanup chat)
- F2 (Chat 4): `target_price` is now consumed by sell-side scoring (`target_price_proximity` signal in `booking_opportunity` group). `stop_loss` still unconsumed — see tech debt.

#### `transactions`
- Append-only ledger of all trades and corporate actions
- Key fields: `isin`, `symbol`, `exchange`, `type` (BUY/SELL/SPLIT/BONUS/DEMERGER), `trade_date`, `quantity` (Decimal128), `price`, `total_fees`, `remaining_quantity` (for FIFO lot tracking), `notes`, `source`, `corporate_action.ratio_from`, `corporate_action.ratio_to`, `fully_consumed_at`, `deleted_at`
- INVARIANT: never directly UPDATEd or DELETEd; edits and deletes go through `/transactions/{id}` PATCH/DELETE which require a reason, write to `transactions_audit` first, then apply the change, then call `recompute_holding`
- Indexes: `(isin, trade_date)`, `(symbol, trade_date)`, `trade_date`

#### `transactions_staging`
- Holding area for the bulk ICICI order book imports before promotion to live
- Same shape as `transactions`
- Cleared by `scripts/promote_staging.py --confirm --wipe-live`

#### `transactions_audit`
- Append-only audit log; one doc per edit/delete
- Key fields: `transaction_id`, `action` (edit/delete), `reason`, `changed_fields` (dict of {field: [before, after]}), `performed_at`, `symbol`
- INVARIANT: written BEFORE the actual change is applied, so even if the apply step crashes, the intent is recorded

#### `prices_daily`
- EOD OHLCV bars; ~5 years of history
- Key fields: `isin`, `date` (UTC-naive midnight), `open`, `high`, `low`, `close` (Decimal128), `volume`, `source`
- Count: ~115,791 docs across 100 NIFTY 100 ISINs (~1,158 per stock), plus 32 held ISINs
- Indexes: `(isin, date)` unique
- Writer: `scripts/refresh_prices.py` (yfinance)

#### `prices_intraday`
- Latest intraday quote captured every 15 min during market hours
- Key fields: `isin`, `symbol`, `date` (UTC), `captured_at`, OHLCV, `source="yfinance_5m_latest"`
- INVARIANT: append-only within a day (not upserted) so we keep history
- No TTL configured yet
- Writer: `scripts/refresh_prices_intraday.py`
- Consumer: `bulk_get_latest_prices` prefers today's intraday over EOD; falls back to EOD

#### `reconciliation_snapshots`
- Daily comparisons of our system totals vs ICICI Direct portfolio totals
- Key fields: `type` (manual/auto), `taken_at`, `our_invested`, `our_current_value`, `our_day_gain`, `icici_invested`, `icici_current_value`, `icici_day_gain`, `drift_invested_pct`, `drift_current_pct`, `drift_alerts` (list of strings), `notes`
- Writer: `/reconciliation/snapshot` (manual) or `/reconciliation/auto-snapshot` (cron at 19:30 IST weekdays)
- Drift detection rules: invested has baseline-relative drift; current_value uses absolute 15k threshold (intra-day timing is noise); day_gain dropped from alerts (always noise)

#### `cost_basis_adjustments`
- Audit trail for tax-correct cost basis adjustments (e.g., TMPV/TMCV demerger per IT Act Section 49(2C))
- Key fields: `name`, `amount` (Decimal128), `effective_date`, `it_act_section`, `rationale`, `source_documents`, `created_at`
- Consumer: `compute_summary` adds `broker_invested = our_invested + total_adjustment`, plus `broker_unrealized_pnl` and `broker_unrealized_pnl_pct`, so the UI can show both tax view and broker view

#### `user_profile`
- Single doc, `_id="sahil"`
- Holds investing philosophy notes, TMPV/TMCV cost basis annotation, etc.

### Phase 2 collections (Suggestions Engine)

#### `monitored_stocks`
- User-feedback state for stocks the engine has surfaced, plus watchlist entries (F13)
- Key fields: `isin`, `status` (writers use `"tracking"/"passed"/"rejected"/"watchlist"`; Pydantic model says `"tracking"/"promoted_to_holding"/"dropped"` — SCHEMA DRIFT, see tech debt), `acted_at`, `passed_at`, `rejected_at`, `last_feedback_at`, `last_feedback_action`, `last_feedback_note`, `created_at`, `updated_at`
- INVARIANT: writes go through `routers/suggestions.submit_feedback` only, using raw `update_one` (Pydantic bypassed because of the schema drift)
- INVARIANT (F10): every write is preceded by a `monitored_stocks_audit_service.log_change(...)` insert. Audit row lands BEFORE the `update_one` apply, so even if the apply crashes the intent is recorded. Same write-before-apply pattern as `transactions_audit`.
- Consumer: `suggestion_engine.get_excluded_isins()` (renamed from `get_rejected_isins` in Chat 3) returns three buckets at run-build time:
  - `rejected` — `status="rejected"` AND `rejected_at >= now - 90d`
  - `passed` — `status="passed"` for this run only (resurfaces next Sunday)
  - `acted` — `status="tracking"` AND `acted_at >= now - 30d` (F5b 30-day soft-exclude; naturally suppressed thereafter by the held filter if the trade landed, or resurfaces if it didn't)
- Consumer: `explainability._build_user_action()` at serialization time stamps each enriched candidate with `user_action` (null | "acted" | "passed" | "rejected") + the corresponding timestamp.
  This is the second of the two F6 exclusion mechanisms — see Section 14.
- F2 (Chat 4): `monitored_stocks` is CURRENTLY DIRECTION-AGNOSTIC. A user rejecting a SELL suggestion for INFY also suppresses the next BUY suggestion for INFY for 90 days, and vice versa. Documented in `get_excluded_isins` and `filter_sell_universe` docstrings. Acceptable for v1 (both interpretations are defensible: "I'm done thinking about INFY"). Add a `direction` column if it bites in practice — pending tech debt item.
- Indexes: `isin` unique, `(status, rejected_at)`

#### `monitored_stocks_audit` (F10 — shipped Chat 3)
- Append-only audit log for `monitored_stocks` writes; one doc per `POST /suggestions/{isin}/feedback`
- Key fields: `isin`, `action` (`"acted"|"passed"|"rejected"`), `previous_status` (string or null), `new_status`, `note`, `performed_at`, `_schema_version` (1)
- INVARIANT: append-only.
  Writer (`monitored_stocks_audit_service.log_change`) is invoked BEFORE the corresponding `monitored_stocks.update_one` apply in `submit_feedback`, so intent survives even if the apply step crashes.
  Mirrors `transactions_audit` exactly.
- Indexes: `(performed_at desc)`, `(isin, performed_at desc)`
- Writer: `app/services/monitored_stocks_audit_service.py`
- Consumer: `GET /suggestions/{isin}/audit` (per-ISIN history), `GET /suggestions/feedback/audit/recent?limit=N` (cross-ISIN feed for ops/debug surfaces and the frontend audit-trail view)

#### `instruments_fundamentals`
- One doc per ISIN per fundamentals refresh (so we have history)
- Key fields: `isin`, `symbol`, `as_of` (date), `fetched_at` (datetime), `market_cap`, `pe_ratio`, `pb_ratio`, `dividend_yield`, `return_on_equity`, `return_on_assets`, `operating_margin`, `debt_to_equity`, `earnings_growth_yoy`, `revenue_growth_yoy`, `beta`, `fifty_two_week_high`, `fifty_two_week_low`, `sector` (yfinance), `industry`, `source`, `source_raw` (full yfinance dict for replay), `fields_present`, `fields_missing`
- Indexes: `isin_latest_unique` (unique, latest only via `(isin, fetched_at desc)`), `fetched_at`
- Writer: `scripts/refresh_fundamentals.py` → `fundamentals_service.refresh_one`. F14: default universe is now NIFTY 100 ∪ active holdings (held stocks outside NIFTY 100 also need fundamentals for F2 sell-side scoring).
- Consumer: `suggestion_engine` (scoring), `explainability.py` (raw values for UI rendering)

#### `earnings_calendar` (F14 — shipped Chat 4)
- Upcoming + historical earnings events per ISIN. Source = yfinance `Ticker.calendar`, refreshed weekly alongside fundamentals.
- Key fields: `isin`, `symbol`, `exchange`, `earnings_date` (tz-naive datetime), `source` ("yfinance"), `source_raw` (sanitized yfinance calendar dict), `fetched_at`, `created_at`
- INVARIANT (refresh semantics): `refresh_earnings_for(isin, symbol, exchange)` deletes ALL future events for the ISIN (>= today) then re-inserts the freshly-fetched list. Past events are immutable history. yfinance occasionally shifts a confirmed date — we lose the "we used to think it was 7/25" history (acceptable for v1; consumer only ever asks "next earnings >= today").
- INVARIANT (BSON sanitization): yfinance `Ticker.calendar` contains `datetime.date` values (notably `Ex-Dividend Date`) that BSON cannot encode. `_sanitize_for_bson` in `fundamentals_service.py` recursively walks dicts/lists and coerces date → datetime, tz-aware → naive, Timestamp/numpy scalars → native, unknown → `str()`. Applied to `source_raw` before insert.
- Indexes: `(isin, earnings_date)` unique, `(earnings_date asc)`, `(isin)`, `(fetched_at desc)`
- Writer: `fundamentals_service.refresh_earnings_for` (single ISIN), `refresh_earnings_universe` (bulk; called by `scripts/refresh_fundamentals.py`)
- Consumer: `fundamentals_service.get_next_earnings_for_isin` / `get_next_earnings_bulk`; `suggestion_engine` (buy + sell pipelines) threads result into `score_candidates` / `score_sell_candidates`; `scoring_service.evaluate_earnings_proximity_gate` skips trades within 5 days of an earnings event (shared between buy and sell).

#### `news_articles`
- Classified news per article; one doc per URL with `$addToSet`-merged `entities_isins`
- Key fields: `url` (unique), `title`, `published_at`, `fetched_at`, `source`, `body` (purged after classification), `body_purged_at`, `entities_isins` (list), `themes` (`Literal[earnings|regulatory|corporate_action|management_commentary|sector_macro|noise]`), `sentiment` (positive/neutral/negative/mixed), `sentiment_confidence`, `severity` (low/medium/high), `classifier_summary`, `classified` (bool)
- Indexes: `url` unique, `(entities_isins, classified, fetched_at)`, `(classified, fetched_at)`
- Writer: `news_fetcher.py` (fetch) then `news_classifier.py` (classify in two-phase Haiku batches: `BATCH_SIZE=25` main pass, `RETRY_PASS_BATCH_SIZE=3` for stragglers)
- Consumer: `news_signals.py` (compute `net_sentiment`, `story_velocity`, `story_count`), `dossier_service.py` (per-candidate news context, last 8 articles)

#### `suggestion_runs`
- Append-only history of every weekly run
- Key fields: `_id`, `_schema_version`, `run_date`, `run_date_ist`, `run_type` (scheduled/manual), `direction` (`"buy"`|`"sell"`, default `"buy"`), `status` (success/partial/failure), `started_at`, `finished_at`, `error`, `universe_size`, `excluded_held`, `excluded_rejected`, `excluded_passed` (F6), `excluded_acted` (F5b), `excluded_stale_data`, `candidates_considered`, `candidates_post_gates`, `config` (full snapshot of weights, gates, freshness, scoring, top_k, version), `top_candidates` (list of CandidateScore docs, persisted in full), `all_candidates`, `top_k`, `notes` (JSON string containing dossiers array)
- INVARIANT: append-only; never updated; re-running creates a new doc
- INVARIANT: `top_candidates[*].user_action` is NOT in the persisted doc. It is added at API serialization time by `enrich_run` only. See Section 12 + Section 14.
- INVARIANT (F2 / Chat 4): pre-F2 runs persisted without a `direction` key still load cleanly. Pydantic default = `"buy"` via `model_validate`. The router serializer (`_serialize_run`) also defensively defaults missing `direction` to `"buy"` for the raw-dict path, and `/runs` adds it to the projection. Sell-side runs persist with `direction="sell"` explicitly.
- Indexes: `(run_date desc)`, `(run_date_ist, run_type)`, `(status)`

#### `suggestion_outcomes`
- One doc per top-K candidate per run; tracks actual stock + benchmark over 30/60/90/180-day windows
- Key fields: `isin`, `symbol`, `suggestion_run_id`, `suggested_at`, `suggested_at_price`, `suggested_rank`, `suggested_composite_score`, `tracking_status` (open/acted/passed/rejected/expired), `direction` (`"buy"`|`"sell"`, default `"buy"`), `price_at_30d/60d/90d/180d`, `nifty_at_30d/60d/90d/180d` (these are RETURN PERCENTAGES vs benchmark, not prices — equal-weighted NIFTY 100), `excess_return_30d/60d/90d/180d`, `user_action_at`, `user_action_note`, `created_at`, `updated_at`
- INVARIANT (changed in Commit A.5): snapshot eligibility is `tracking_status != "expired"`, NOT `tracking_status == "open"`. The user's label (acted/passed/rejected) is metadata; data collection continues regardless so per-bucket performance is measurable.
- INVARIANT: outcomes only auto-flip to `"expired"` if still labeled `"open"` at day 180. User-set labels are never overwritten.
- INVARIANT (F2 / Chat 4): `direction` defaults to `"buy"` for pre-F2 outcomes via the Pydantic default. `compute_system_performance(direction="sell")` sign-flips `excess_return` per outcome before aggregating so "higher is better" framing is preserved.
- Indexes: `(isin, suggested_at desc)`, `(suggested_at desc)`, `(tracking_status)`, `(suggestion_run_id)`
- Writer: `outcome_tracker.create_outcomes_for_run` at run time (stamps direction), `snapshot_open_outcomes` daily (direction-agnostic; same snapshot serves both directions)

#### `tavily_quota`
- One doc per UTC day; counters incremented atomically
- Key fields: `date` (YYYY-MM-DD string), `total_calls`, `total_credits`, `per_use_case.<name>.calls`, `per_use_case.<name>.credits`
- Indexes: `date` unique
- Writer: `tavily_client.py` `$inc` updates with upsert
- INVARIANT: `TAVILY_DAILY_CALL_LIMIT` (default 200) enforced; raises `TavilyQuotaExceeded` when hit

#### `digest_deliveries`
- Audit log of weekly digest emails + ntfy pushes
- Key fields: `run_id`, `run_date_ist`, `sent_at`, `top_count`, `subject`, `email_ok`, `email_id`, `email_error`, `ntfy_ok`, `ntfy_status`, `ntfy_error`
- F2 (Chat 4): for combined-digest sends (`--direction=both` cron path), the row attaches to the BUY run id so one row per delivery is preserved. `top_count = buy_top + sell_top`.
- Indexes: `(sent_at desc)`, `(run_id)`
- Writer: `digest_delivery.send_weekly_digest` (single-direction) or `digest_delivery.send_combined_digest` (both)

#### `cron_heartbeats` (F4 — shipped Chat 2)
- One doc per cron run with start/finish/status/error/metadata. Written by every cron script via the `cron_run()` context manager in `app/services/cron_heartbeat_service.py`.
- Key fields: `cron_name`, `started_at`, `finished_at`, `status` (`"success"|"failure"|"skipped"`), `error`, `metadata` (dict, per-cron stats), `_schema_version`
- INVARIANT: append-only. Wrapper writes exactly one doc per run on exit; on exception the heartbeat is recorded with `status="failure"` and the exception re-raised so the script's own exit-code path is preserved.
- INVARIANT: heartbeat write is best-effort — if Mongo is unreachable the write is swallowed rather than masking the underlying cron error. The missing heartbeat itself is what the next day's health check catches.
- INVARIANT (Chat 4): the context manager yields a `_Heartbeat` object that exposes `.meta` as an ATTRIBUTE. Set via `ctx.meta = {...}` (full replace) or `ctx.meta[key] = value`. `ctx["meta"] = ...` raises TypeError. (Three call sites in `run_weekly_suggestions.py` had this bug in Chat 4; fixed in chunk 6.2.)
- `"skipped"` status is for "nothing to do" runs (e.g., intraday refresh when market is closed). Counts as healthy in the daily check.
- Indexes: `(cron_name, started_at desc)`, `(started_at desc)`, TTL on `started_at` (60 days)
- Consumer: `GET /cron/heartbeats` router; `scripts/cron_health_check.py` (daily 21:00 IST)
- Writer: `app.services.cron_heartbeat_service.cron_run()` context manager — used by all registered cron scripts including `cron_health_check` itself
- The expected cron schedule lives in code as `CRON_REGISTRY` (a list of `CronSpec` entries) in `cron_heartbeat_service.py` — NOT in Mongo. Keep `CRON_REGISTRY` and `crontab -l` in sync whenever a cron is added or rescheduled.

### `digests` / `alerts_log` / `conversations` / `macro_signals`
Scaffolds; not actively written by current code.
`conversations` will be used for chat features (F1, F3).
Reserved; do not delete.

### Future collections (planned, not yet created)
- None pending in the current plan after F14 shipped. F11 (capital gains pack) is a read-only reformatter on existing collections.

## Section 8: API endpoints (exhaustive)

All routes are under the FastAPI app, served on port 8000 (EC2) or 8001 (Mac local).
All return JSON.
ISIN path params are validated 12-char.

### Phase 1

```
GET    /health
GET    /portfolio/holdings                           Holding[]
GET    /portfolio/holdings/{isin}                    Holding
POST   /portfolio/holdings                           Holding (BUY)
PATCH  /portfolio/holdings/{isin}                    Holding (notes/thesis/stop_loss/target_price/tags only)
POST   /portfolio/holdings/{isin}/sell               Holding OR {message, realized_total}
POST   /portfolio/holdings/{isin}/preview-sell       SellPreview
GET    /portfolio/holdings/{isin}/history?days=N     PriceBar[]
GET    /portfolio/holdings/{isin}/transactions       Transaction[]
GET    /portfolio/summary                            PortfolioSummary
GET    /transactions/search?symbol&type&from_date&to_date&skip&limit
                                                     {results, total}
GET    /transactions/{id}                            Transaction
PATCH  /transactions/{id}                            Transaction (requires reason)
DELETE /transactions/{id}                            {deleted: true} (requires reason)
GET    /transactions/audit/recent?limit=N            AuditEntry[]
GET    /transactions/{id}/audit                      AuditEntry[]
POST   /reconciliation/snapshot                      ReconciliationSnapshot (manual)
GET    /reconciliation/snapshots                     ReconciliationSnapshot[]
POST   /reconciliation/auto-snapshot                 ReconciliationSnapshot (cron)
GET    /cost-basis/adjustments                       CostBasisAdjustment[]
GET    /instruments                                  symbol_overrides list
POST   /instruments                                  symbol_overrides upsert
DELETE /instruments/{exchange}/{symbol}              delete override
```

### Phase 2 (Suggestions)

```
GET    /suggestions/latest?direction=buy|sell        SuggestionRun + enrichment
                                                     F2: ?direction defaults to "buy"
                                                     for back-compat; pre-F2 docs without
                                                     the field match the buy filter via
                                                     $or {direction:"buy"} OR
                                                        {direction:{$exists:false}}.
GET    /suggestions/runs?direction=buy|sell&limit=N&skip=N
                                                     {runs, total, limit, skip}
                                                     F2: same direction semantics
GET    /suggestions/runs/{run_id}                    SuggestionRun + enrichment
                                                     direction is implicit in the doc
GET    /suggestions/performance?direction=buy|sell   SuggestionPerformance with by_bucket
                                                     F2: direction optional. None =
                                                     cross-direction (legacy; semantically
                                                     muddy). "sell" sign-flips
                                                     excess_return at aggregation time.
POST   /suggestions/{isin}/feedback                  {isin, action, status, previous_status}
                                                     Body: {action: "acted"|"passed"|"rejected", note?: string}
                                                     NOTE: direction-agnostic; see
                                                     monitored_stocks tech debt
GET    /suggestions/{isin}/audit?limit=N             MonitoredStocksAuditEntry[]   (F10)
GET    /suggestions/feedback/audit/recent?limit=N    MonitoredStocksAuditEntry[]   (F10)
GET    /cron/heartbeats?limit=N                      {heartbeats, health_summary}
                                                     (F4 — shipped Chat 2)
                                                     F2: registry now includes
                                                     weekly_suggestions_sell
```

`/cron/heartbeats` response shape:
- `heartbeats`: newest-first list of recent cron run docs (default limit 200, capped at 1000)
- `health_summary`: one entry per registered cron with `cron_name`, `description`, `schedule`, `expected_today`, `min_runs_per_day`, `last_run_at`, `last_status`, `last_error`, `today_total`, `today_success`, `today_failure`, `today_skipped`, `healthy`
- `healthy = true` when either (a) cron is not expected today, or (b) `today_success + today_skipped >= min_runs_per_day` AND `today_failure == 0`

F10 feedback-audit endpoint shape (shipped Chat 3):
- Each row: `{_id, isin, action, previous_status, new_status, note, performed_at, _schema_version}`
- `/suggestions/{isin}/audit` is backed by the `(isin, performed_at desc)` compound index; mirrors `GET /transactions/{id}/audit`
- `/suggestions/feedback/audit/recent` is backed by the `(performed_at desc)` index; mirrors `GET /transactions/audit/recent`
- The static-path `/feedback/audit/recent` route is declared BEFORE the dynamic `/{isin}/audit` route in `routers/suggestions.py` to avoid any route-ordering ambiguity

### Future endpoints (planned)

```
POST   /watchlist/{isin}                             add to watchlist (F13)
DELETE /watchlist/{isin}                             remove from watchlist (F13)
GET    /watchlist                                    list watchlist (F13)
GET    /portfolio/risk-summary                       concentration & risk alerts (F12)
GET    /portfolio/by-tag?tag=X                       holdings grouped/filtered by tag (F15)
POST   /chat/suggestions                             ad-hoc chat about suggestions (F1)
POST   /chat/holdings/{isin}                         ad-hoc chat about a holding (F3)
GET    /tax/capital-gains?fy=YYYY-YY                 capital gains pack (F11)
```

### Sell endpoint response shape (critical, often confused)
`POST /portfolio/holdings/{isin}/sell` returns one of:
- The full updated `Holding` doc (partial sell, position still active)
- `{message: "Position fully exited", realized_total: "<string Decimal>"}` (full exit)

The frontend discriminates via type guard on the `_id` field, NOT a status field.
The original `SellSheet` was written this way; do not change it.

## Section 9: Cron registry on EC2

Run `crontab -l` to see current state.
As of Chat 4, every script below is heartbeat-instrumented via `app.services.cron_heartbeat_service.cron_run()` and writes a doc to `cron_heartbeats` on completion (success, failure, or skipped).
The daily `cron_health_check` at 21:00 IST consumes those heartbeats and fires `push_public("errors", ...)` on anomalies.
`CRON_REGISTRY` in `cron_heartbeat_service.py` is the in-code mirror of this schedule — keep both in sync.

Registered entries on EC2:

```cron
# Phase 1 crons (heartbeat-instrumented Chat 2)
# Daily instrument refresh — 03:00 IST
0 3 * * * cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/refresh_instruments.py >> /home/ubuntu/cron-instruments.log 2>&1
# Weekday EOD price refresh — 19:00 IST
0 19 * * 1-5 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/refresh_prices.py >> /home/ubuntu/cron-prices.log 2>&1
# Intraday price refresh — every 15 min during market hours (09:15-15:45 IST), weekdays
*/15 9-15 * * 1-5 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/refresh_prices_intraday.py >> /home/ubuntu/cron-prices-intraday.log 2>&1
# Daily reconciliation auto-snapshot — 19:30 IST (after price refresh)
30 19 * * 1-5 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/take_reconciliation_snapshot.py >> /home/ubuntu/cron-reconciliation.log 2>&1

# Phase 2 crons (registered Chat 2 via F5a — all heartbeat-instrumented)
# Sunday 06:00 IST — refresh fundamentals + earnings calendar for NIFTY 100 ∪ held (F14 expansion)
0 6 * * 0 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/refresh_fundamentals.py >> /home/ubuntu/cron-fundamentals.log 2>&1
# Sunday 06:30 IST — fetch + classify news for the universe
30 6 * * 0 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/fetch_news_for_universe.py >> /home/ubuntu/cron-news.log 2>&1
# Sunday 07:00 IST — run weekly suggestions
# PENDING: line still uses default (--direction=buy implicit). Chat 4 added
# --direction=buy|sell|both. To get combined buy+sell digest, swap this line
# to use --direction=both. Until swapped, sell-side will NOT run on Sunday cron.
0 7 * * 0 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/run_weekly_suggestions.py --notify --run-type scheduled >> /home/ubuntu/cron-suggestions.log 2>&1
# Weekdays 19:45 IST — outcome tracking snapshot (after 19:00 EOD refresh + 19:30 reconciliation)
45 19 * * 1-5 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/track_suggestion_outcomes.py >> /home/ubuntu/cron-outcomes.log 2>&1

# F4 cron health monitoring (added Chat 2)
# Daily 21:00 IST — health check; fires ntfy on anomalies
0 21 * * * cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/cron_health_check.py >> /home/ubuntu/cron-health.log 2>&1

# Maintenance
# Weekly log truncation — keep last ~10K lines on logs > 10MB
0 0 * * 0 find /home/ubuntu -maxdepth 1 -name "cron-*.log" -size +10M -exec sh -c 'tail -10000 "$1" > "$1.tmp" && mv "$1.tmp" "$1"' _ {} \;
```

PENDING ONE-TIME EC2 STEPS (Chat 4 follow-up — manual, not committable):
- Swap the Sunday 07:00 IST line to `... run_weekly_suggestions.py --direction=both --notify --run-type scheduled ...` so the combined buy+sell digest path is exercised by cron. Until done, sell-side suggestions only run from manual `--direction=sell` invocations.
- Stop + disable the self-hosted private ntfy service (F2b moved digests to public ntfy.sh; the private service is no longer used). One-time: `sudo systemctl stop ntfy && sudo systemctl disable ntfy`.

`CRON_REGISTRY` (in code) now also contains:
- `weekly_suggestions_sell` — `CronSpec(cron_name="weekly_suggestions_sell", description="Weekly sell-side suggestions: profit-booking candidates from active holdings.", schedule_human="Sun 07:30 IST", expected_weekdays={6})`
  - The standalone `weekly_suggestions_sell` cron line is NOT yet registered on EC2. The recommended production path is `--direction=both` under the existing `weekly_suggestions` umbrella heartbeat. The standalone registry entry exists so a future deployment topology that wants two separate runs can install the matching crontab line without code changes.

No silent failures: every cron registration must include log file paths AND be heartbeat-instrumented via `cron_run()` AND have a corresponding `CronSpec` entry in `CRON_REGISTRY`.
Adding a cron without all three breaks the F4 contract.

## Section 10: Settings and environment variables

Configured in `app/config/settings.py` via pydantic-settings reading `/etc/portfolio-advisor/secrets.env` (EC2) or `<repo>/.env` (Mac).
All required unless marked default.

### Anthropic
- `ANTHROPIC_API_KEY` (required)
- `ANTHROPIC_MODEL_PRIMARY` (default `"claude-sonnet-4-5"`) — used by `dossier_service`, chat features
- `ANTHROPIC_MODEL_FAST` (default `"claude-haiku-4-5"`) — used by `news_classifier`

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
- `NTFY_URL` (was: private self-hosted, behind Tailscale Funnel). F2b: no longer used by digest_delivery. Pending decommission. `push_private` still exists in `notify.py` for any future genuinely-sensitive content path.
- `NTFY_USER`, `NTFY_PASS` (basic auth for private — same as above)
- `NTFY_PUBLIC_URL` (default `"https://ntfy.sh"`)
- `NTFY_PUBLIC_TOPIC_PRICE`, `NTFY_PUBLIC_TOPIC_NEWS`, `NTFY_PUBLIC_TOPIC_ERRORS` (public ntfy.sh topics; unguessable strings act as bearer tokens; full content delivered instantly to iOS)
- `NTFY_PUBLIC_TOPIC_DIGESTS` (F2b — REQUIRED, no default. Used by `digest_delivery._send_ntfy` for weekly digest pushes. Must be subscribed on the iPhone ntfy app.)
- `NTFY_PUBLIC_TOPIC_ERRORS` specifically is used by F4 `cron_health_check` — if you change the topic value, also update the subscription on the iPhone ntfy app
- All `NTFY_PUBLIC_TOPIC_*` values must be IDENTICAL on EC2 and Mac so dev-testing of alert paths reaches the same subscribed device
- `push_public(channel)` signature: `channel: Literal["price", "news", "errors", "digests"]`; defined in `app/services/notify.py`. F4 cron alerts use `push_public("errors", ...)` for instant iOS delivery; content is "script name + error message", no portfolio/PII data. F2b digests use `push_public("digests", ...)`; content includes top symbols and composite scores, no PII.

## Section 11: Phase 1 INVARIANTS — never violate

These come straight from `docs/data_flow.md`.
They are hard rules.

- Transactions are immutable except through the audited PATCH/DELETE flow. Every PATCH/DELETE writes a `transactions_audit` entry BEFORE applying the change. The `reason` field is required.
- `recompute_holding(isin)` is the only authoritative writer to `holdings`. It is idempotent and recomputes from `transactions` from scratch using FIFO. Never write directly to `holdings`. Call `recompute_holding` after any transaction change.
- `validate_replay(isin, simulated_transactions)` simulates a transaction set and rejects any timeline that produces negative quantity at any point. Both PATCH and DELETE on `/transactions/{id}` call this before applying.
- `holdings.deleted_at = None` filter is universal. Every read of active holdings must include this filter. Deleted holdings preserve replay correctness.
- Cost basis is IT-Act-correct, not broker-nominal. `holdings.invested_amount` reflects the tax-correct cost basis (which for TMPV/TMCV reflects the 68.85/31.15 cost basis split per Tata Motors official Section 49(2C) disclosure). The broker-nominal view is recoverable as `holdings.invested_amount + total_cost_basis_adjustment` and surfaced via `summary.totals.broker_invested`.
- `prices_intraday` writes are append-only within a day (inserted, not upserted) so we keep intraday history.
- ICICI portfolio display shows TMPV at ~813 and TMCV at ~253 (sums to ~1,06,673), which is ~25k higher than our correct ~81,337. Our numbers reflect tax-correct cost basis; ICICI display is cosmetically wrong but does not affect actual money or tax filing.

## Section 12: Phase 2 INVARIANTS

- `suggestion_runs` are append-only. Re-running creates a new doc; never UPDATEd.
- `tavily_quota` is one doc per UTC day with `$inc` counters. Hard ceiling enforced.
- Confidence score is deterministic (computed from data freshness and signal availability), NOT LLM-generated. Composite score answers "is this stock attractive?"; confidence answers "should I trust the answer?"
- The dossier prompt requires narrative-only output. Numbers come from our data. The prompt forbids "buy" or "sell" imperatives. The prompt also forbids inventing facts not in the input.
- `gate_meta`, `group_meta`, `signal_meta`, `confidence_meta`, `feedback_meta`, `page_intro`, and `user_action` are PRESENTATION metadata, added by `routers/suggestions._serialize_run` via `enrich_run`. They are NOT in the persistent model. The router calls `enrich_run` after JSON conversion; the underlying `suggestion_runs` doc is never mutated. (`user_action` was added in Chat 3 via F6; see Section 14 for the two-mechanism rationale.)
- Snapshot eligibility for `outcome_tracker.snapshot_open_outcomes` is `tracking_status != "expired"`, NOT `tracking_status == "open"`. User-set labels (acted/passed/rejected) do not gate data collection. (Changed in Commit A.5.)
- Auto-expiry only flips outcomes that are still labeled `"open"` at day 180. A user-set label is never auto-overwritten. (Changed in Commit A.5.)
- Feedback re-labels the MOST RECENT non-expired outcome for the ISIN, regardless of its current `tracking_status`. (Fixed in Commit A.5.1.)
- `suggestion_engine.get_excluded_isins()` (renamed from `get_rejected_isins` in Chat 3 / F6) returns three buckets used to exclude ISINs at run-build time:
  - `rejected` — `monitored_stocks.status == "rejected"` AND `rejected_at >= now - 90d`. Auto-expires after 90 days. The 90-day window is intentionally NOT env-configurable; change the constant in `suggestion_engine.py` in one place if it ever needs to move.
  - `passed` — `monitored_stocks.status == "passed"`. THIS run only — naturally resurfaces on the next run because the bucket is recomputed every time.
  - `acted` — `monitored_stocks.status == "tracking"` AND `acted_at >= now - 30d` (F5b). Soft-exclude for 30 days; naturally suppressed thereafter by the held filter if the trade landed, or resurfaces if it didn't. There is no manual-clear mechanism and we deliberately did not build one.
- F10 write-before-apply: every `POST /suggestions/{isin}/feedback` writes the `monitored_stocks_audit` row via `monitored_stocks_audit_service.log_change(...)` BEFORE the corresponding `monitored_stocks.update_one` apply. Same invariant as `transactions_audit` — intent survives even if the apply step crashes.
- Per `monitored_stocks` schema-vs-writer drift: the model says `Literal["tracking", "promoted_to_holding", "dropped"]` but the writer writes `"tracking"`, `"passed"`, `"rejected"`. The writer uses raw `update_one` so Pydantic is bypassed. If you ever load a `monitored_stocks` doc through `MonitoredStock(**doc)` it will throw. See tech debt (F5c).
- The `notes` field on a `SuggestionRun` is a JSON string containing `{dossiers: [...]}`. The router parses it and exposes `dossiers` at the top level of the response, then strips `notes`. The router also strips `all_candidates` from the response to keep payloads small. The persisted doc still has it.

### F2 / F14 invariants (Chat 4)

- `SuggestionDirection` liter
# PROJECT_STATE.md

Living source of truth for the Personal AI Stock Advisor.
Updated at the end of every chat.

This file is the bootstrap document for any new conversation with an AI assistant.
If you (the assistant) are reading this for the first time in a new chat: read it top to bottom before doing anything.
Do not skim.
Do not assume.
Do not redesign.
The prior chat hit context limits or context drift — that's why we're here.

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

GitHub content may be cached.
Whenever you read a file, capture the commit
SHA you read at, and re-read if the user tells you they have pushed since.

Today's scope is: <DESCRIBE THE FEATURE OR FIX FOR THIS CHAT>

Hard rules:
- Do not invent parallel patterns.
  Evolve existing code, don't redesign.
- Re-read files at HEAD before patching them.
  Do not trust memory.
- Hand me full file contents OR exact find-and-replace.
  Never "rest unchanged".
- Use canvas artifacts for files.
  Use chat for tests.
- PROJECT_STATE.md is ALWAYS delivered as a complete full-file replacement,
  never as a patch, find-and-replace, or "rest unchanged".
  No exceptions,
  no matter how small the edit.
- Every code/file change MUST be followed by a `git add .` + `git commit -m`
  block in chat, ready to paste, written in the project's commit-message style.
- Every test block MUST begin with `ssh ubuntu@100.112.20.41` and run curls
  against `localhost:8000` from inside the box (not against the Tailscale IP
  from the laptop).
- In every mapping table, the Action column must say NEW FILE, REPLACE
  EXISTING, or PATCH.
- BEFORE constructing any class or dataclass via `Foo(field=...)`, run
  `grep -A 20 "class Foo" <path>` on the actual file on disk and verify
  every field name you reference. Glean snippets are often call sites or
  docstrings, NOT the @dataclass definition. Three field-name drifts in
  Chat 4 forced this rule. (See Section 14.)
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

Personal AI Stock Advisor.
Single-user portfolio + research tool for Indian NSE equities.
Built for and by Sahil Doshi (Senior Consulting Engineer, MongoDB, India).

Strict design constraint that overrides everything else: the system never executes trades.
Sahil trades manually in ICICI Direct.
The system records, analyzes, and advises only.
Any feature that would auto-place an order is out of scope, permanently.

The system is also not regulatory advice.
Dossiers and suggestions must use phrasing like "the system flagged this because..." and "this is a good buy because..." or "this is a good sell because...".
The user decides; the user trades.

The goal of the system is to maximise the investments.
Goal of the tool: grow money.
Every feature is judged on whether it helps with one of:

- Buy better (find opportunities you'd otherwise miss)
- Sell better (exit before reversals, hold through noise)
- Avoid mistakes (concentration, FOMO, panic sells, missed corporate actions)
- Reduce costs (taxes, fees, opportunity cost of dead capital)

Anything that doesn't map to one of these is decoration and gets cut.

Explicitly NOT a goal: dividend tracking, accounting, financial planning, tax filing, goal-based planning.
The tool informs investment decisions; bank statements and the CA handle the rest.

## Section 2: User communication preferences (apply to all chats)

- Honest, slightly contrarian opinions over fake agreement.
  The user will push back when he disagrees; the assistant must do the same.
- Build right, no shortcuts.
  Do not introduce avoidable rework.
- Math accuracy and legal compliance matter.
  If something is mathematically wrong or legally non-compliant, call it out immediately.
- Use existing project conventions.
  Do not invent parallel patterns.
- Give full file contents OR exact find-and-replace instructions.
  Never use placeholders like "rest unchanged" or "// existing code here".
  Do not truncate important code.
- Prefer meaningful units of work.
  Small enough to test, not so tiny that we ping-pong.
- Give concrete test commands when appropriate.
- Files go in canvas artifacts.
  Tests go in chat as fenced code blocks.
- Every mapping table must use Action column values: NEW FILE, REPLACE EXISTING, or PATCH.
- The user edits on Mac, commits, pushes.
  EC2 is for build/test/deploy/debug.
  The assistant should not edit Mac files directly; it produces artifacts the user pastes.
- Every code/file delivery in chat MUST be followed by a paste-ready `git add .` + `git commit -m "..."` block in the project's existing commit-message style.
- Every test block in chat MUST start with `ssh ubuntu@100.112.20.41` and run subsequent curls against `localhost:8000`.
  Do not give curls against the Tailscale IP from the Mac.
- PROJECT_STATE.md is ALWAYS delivered as a complete full-file replacement, never a patch or diff or find-and-replace.
  No exceptions.

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
- ntfy (push notifications — public ntfy.sh for all paths after F2b; self-hosted private path is still installed on EC2 but no longer used and pending decommission — see Section 18)

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
- EC2 Tailscale IP: `100.112.20.41`
- SSH from Mac: `ssh ubuntu@100.112.20.41`
- Backend port on EC2: `8000`
- Frontend port on EC2: `3000`
- Backend port on Mac (local dev): `8001` (NOT 8000)
- Frontend port on Mac (local dev): `3000`

This Mac vs EC2 port difference is a real, recurring source of confusion for assistants.
The assistant has gotten this wrong multiple times.
Always specify which machine when giving test commands.
For chat-supplied test blocks, the standing convention is "SSH into EC2 first, then curl localhost:8000" — see Section 14.

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

The `Settings` class uses pydantic-settings with `model_config = SettingsConfigDict(env_file=str(SECRETS_FILE), env_file_encoding="utf-8", case_sensitive=True, extra="ignore")`.
Pydantic-settings reads the file directly into the `Settings` object — secrets are NOT exported to `os.environ`.

If the assistant ever suggests `~/secrets/secrets.env` on EC2, it is wrong.
That path was a transient debug artifact.

F2b addition (Chat 4): `NTFY_PUBLIC_TOPIC_DIGESTS` must be present in `/etc/portfolio-advisor/secrets.env` — required (no default). If missing, app startup fails with a Pydantic validation error. Subscribe the iPhone ntfy app to the topic value before running cron.

### Deploy scripts
On EC2:
- `~/deploy.sh` — pulls backend, runs `uv sync`, restarts `portfolio-advisor.service`
- `~/deploy-ui.sh` — pulls frontend, runs `npm install --legacy-peer-deps`, runs `npm run gen-api`, runs `npm run build`, restarts `portfolio-advisor-ui.service`

The `gen-api` step in `deploy-ui.sh` regenerates `lib/api-types.ts` against the running backend's OpenAPI spec.
That file is gitignored.
On Mac, running `npm run gen-api` without overriding the URL will fail because Mac backend is on port 8001 and the default is 8000.
Use:

```
API_OPENAPI_URL=http://100.112.20.41:8000 npm run gen-api
```

or just skip it — `lib/api-types.ts` is not used at runtime; `lib/api.ts` is hand-typed.

### systemd units on EC2
- `portfolio-advisor.service` — runs `uvicorn app.main:app --port 8000 --host 0.0.0.0` as user `ubuntu`, with `EnvironmentFile` NOT used (settings.py loads from `/etc/portfolio-advisor/secrets.env` directly), `Environment="PYTHONPATH=/home/ubuntu/ai-stock-advisor-backend"`, `Environment="PYTHONUNBUFFERED=1"`.
  Logs to journald.
- `portfolio-advisor-ui.service` — runs `node /home/ubuntu/ai-stock-advisor-frontend/node_modules/next/dist/bin/next start` on port 3000 with hardening (`NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict`, `ReadWritePaths` includes the frontend dir and `/tmp`).

A sudoers entry at `/etc/sudoers.d/portfolio-advisor-systemctl` lets `ubuntu` restart these services without password.

### Repos
- Backend: https://github.com/doshisahil95/ai-stock-advisor-backend
- Frontend: https://github.com/doshisahil95/ai-stock-advisor-frontend

GitHub is the source of truth for code.
GitHub may serve cached content via Glean's reader.
When in doubt, find the latest commit SHA and read at that SHA explicitly.

## Section 5: Backend file map

Directory layout under `app/`:

```
app/
  main.py                     FastAPI bootstrap, router includes, lifespan
  config/
    settings.py               pydantic-settings, loads secrets file
                              F2b: NTFY_PUBLIC_TOPIC_DIGESTS (required)
  db/
    client.py                 Mongo client, get_db(), Collections accessor class
                              (incl. Collections.monitored_stocks_audit() — F10)
                              (incl. Collections.earnings_calendar() — F14)
    indexes.py                ensure_indexes() called on startup
                              (incl. monitored_stocks_audit indexes — F10)
                              (incl. earnings_calendar indexes — F14)
  models/
    _common.py                utcnow(), Decimal128 helpers, ObjectId helpers
    instrument.py             Instrument (NSE master record)
    holding.py                Holding (active position)
    transaction.py            Transaction (BUY/SELL/SPLIT/BONUS/DEMERGER)
    fundamentals.py           InstrumentFundamentals (per-ISIN, per-refresh)
    earnings_event.py         F14: EarningsEvent (one doc per ISIN per earnings_date)
    suggestion.py             SuggestionRun, SuggestionOutcome, CandidateScore,
                              SignalScore, GateResult
                              F2: SuggestionDirection literal; direction field
                              on SuggestionRun and SuggestionOutcome (default
                              "buy" so pre-F2 docs coerce cleanly)
    news.py                   NewsArticle (live model)
    news_article.py           DEAD; older parallel model, do not use, do not import
    monitored_stock.py        MonitoredStock; Literal status is DRIFTED (see tech debt)
    macro_signal.py           placeholder
    conversation.py           placeholder (will be used for chat features F1/F3)
    reconciliation.py         ReconciliationSnapshot
    cost_basis_adjustment.py  CostBasisAdjustment
  routers/
    holdings.py               /portfolio/holdings, /portfolio/holdings/{isin},
                              /sell, /preview-sell, /history, /transactions
    portfolio.py              /portfolio/summary
    transactions.py           /transactions/search, /transactions/{id} CRUD,
                              /transactions/audit/recent, /transactions/{id}/audit
    reconciliation.py         /reconciliation/snapshot, /snapshots, /auto-snapshot
    instruments.py            /instruments (symbol_overrides CRUD)
    cost_basis.py             /cost-basis/adjustments
    suggestions.py            /suggestions/latest, /runs, /runs/{id},
                              /performance, /{isin}/feedback,
                              /{isin}/audit, /feedback/audit/recent (F10)
                              F2: ?direction=buy|sell on /latest, /runs,
                              /performance. /runs/{id} unchanged (direction
                              is implicit in the stored doc).
    cron.py                   /cron/heartbeats (F4 — health summary +
                              recent heartbeats; mirrors reconciliation.py
                              local _serialize helper)
  services/
    instrument_service.py     lookup_isin, bulk_lookup_isins, refresh
    price_service.py          EOD + intraday fetch, bulk_get_latest_prices,
                              annotate_with_current_price, get_previous_close
    holdings_service.py       recompute_holding, validate_replay, preview_sell,
                              _to_decimal helper
    portfolio_service.py      compute_summary
    transactions_audit_service.py  log_change, get_audit_for_transaction
    monitored_stocks_audit_service.py  F10: log_change (write-before-apply),
                                       get_audit_for_isin, get_recent_audit
    reconciliation.py         take_auto_snapshot, drift detection
    cost_basis_service.py     get_active_adjustments, total_adjustment_amount
    fundamentals_service.py   yfinance provider, refresh_one, refresh_universe,
                              get_latest_for_isin, get_latest_bulk, is_fresh,
                              _normalize_debt_to_equity, _normalize_dividend_yield
                              F14: fetch_earnings_calendar_yfinance,
                              refresh_earnings_for, refresh_earnings_universe,
                              get_next_earnings_for_isin, get_next_earnings_bulk,
                              _sanitize_for_bson (yfinance dates coerce)
    tavily_client.py          quota-tracked wrapper, TavilyQuotaExceeded
    news_fetcher.py           fetch_for_instrument, fetch_for_universe
    news_classifier.py        Haiku batch classifier, retry pass
    news_signals.py           compute_news_signals_for_isin, _bulk
    scoring_service.py        extract_signals, score_candidates,
                              Q/V/M/N weights, gates, version "1.0.0-unit2"
                              F14: evaluate_earnings_proximity_gate (shared);
                              evaluate_gates accepts optional next_earnings;
                              score_candidates accepts optional
                              next_earnings_by_isin (buy-side wires it in
                              suggestion_engine).
                              F2: DEFAULT_SELL_CONFIG, GROUP_SIGNALS_SELL,
                              extract_sell_signals, evaluate_sell_gates
                              (in_profit, min_position_age, earnings_proximity),
                              score_sell_candidates. score_group +
                              composite_for_candidate refactored to accept
                              optional group_signals_def (back-compat with
                              GROUP_SIGNALS default).
    dossier_service.py        generate_dossiers_for_top_k, Sonnet,
                              plain_english_summary in schema
                              F2: _SYSTEM_PROMPT_SELL with tax_consideration +
                              concentration_note; _parse_dossier required
                              fields switch on direction; per-candidate
                              POSITION CONTEXT block (cost basis, unrealized
                              gain %, tax window, portfolio weight, next
                              earnings) appended for sell-side.
    suggestion_engine.py      run_suggestions (full pipeline);
                              get_excluded_isins (F6+F5b: rejected 90d,
                              passed this-run, acted 30d)
                              F2: run_suggestions(direction="buy"|"sell")
                              dispatches to _run_buy_pipeline (F14 gate now
                              activated) or _run_sell_pipeline (universe =
                              active holdings, portfolio_value computed via
                              bulk_get_latest_prices, sell-side scoring +
                              dossier).
    outcome_tracker.py        create_outcomes_for_run, snapshot_open_outcomes,
                              compute_system_performance
                              F2: create_outcomes_for_run stamps direction;
                              compute_system_performance accepts optional
                              direction filter and sign-flips excess_return
                              for sell-side at read time.
    digest_delivery.py        send_weekly_digest (Resend + ntfy)
                              F2b: ntfy via push_public("digests", ...) on
                              public ntfy.sh; private path retired here.
                              F2 (Chat 4): send_combined_digest(buy_run,
                              sell_run) for the --direction=both cron path.
                              KNOWN BUG: sell-side sections (in both
                              send_weekly_digest sell standalone AND
                              send_combined_digest sell section) render
                              Q=V=M=N=0 because CandidateScore has fixed
                              buy-side group fields; sell-side group scores
                              live separately. See Section 18.
    explainability.py         SIGNAL_META, GROUP_META, GATE_META, FEEDBACK_META,
                              PAGE_INTRO, enrich_run, enrich_candidate;
                              _load_monitored_bulk + _build_user_action (F6)
                              F2: SIGNAL_META extended (unrealized_gain_pct,
                              target_price_proximity, portfolio_weight_pct,
                              is_ltcg_eligible, high_severity_negative_count).
                              GROUP_META extended (booking_opportunity,
                              valuation_stretch, risk, tax_concentration).
                              GATE_META extended (earnings_proximity,
                              in_profit, min_position_age).
                              _GROUP_TO_SIGNALS extended for sell groups.
                              NOT YET DONE: enrich_run page_intro still
                              buy-centric for sell runs.
    notify.py                 push_private, push_public, email (generic wrappers;
                              digest_delivery uses its own copies of Resend +
                              ntfy code, not these — that's intentional drift).
                              PublicChannel now includes "errors" (F4) and
                              "digests" (F2b)
    cron_heartbeat_service.py F4: cron_run context manager, CRON_REGISTRY,
                              get_recent_heartbeats, get_latest_per_cron,
                              count_today_heartbeats, ist_today_window_utc,
                              is_expected_today
                              F2: CRON_REGISTRY includes
                              "weekly_suggestions_sell" CronSpec.
                              CONVENTION (Section 14): CronSpec fields are
                              (cron_name, description, schedule_human,
                              expected_weekdays, min_runs_per_day=1). Three
                              field-name drifts in Chat 4 produced this rule.
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
    refresh_fundamentals.py        F14: default universe is now NIFTY 100 ∪
                                   active holdings (held stocks outside
                                   NIFTY 100 still need fundamentals +
                                   earnings for F2 sell-side); folds earnings
                                   refresh into the same Sunday cron via
                                   refresh_earnings_universe.
                                   --holdings-only and --symbols overrides
                                   preserved.
    fetch_news_for_universe.py
    run_weekly_suggestions.py      F2: --direction=buy|sell|both (default
                                   "buy"). "both" runs buy then sell under
                                   ONE heartbeat and emits ONE combined
                                   digest via send_combined_digest.
                                   --no-notify skips outcomes + digest.
                                   --skip-dossiers skips Claude (smoke-test
                                   only; not for production).
                                   _do_buy/_do_sell/_do_both call sites use
                                   ctx.meta = {...} (NOT ctx["meta"] — see
                                   Section 14).
    track_suggestion_outcomes.py
    cron_health_check.py           F4: daily 21:00 IST; reads CRON_REGISTRY +
                                   today's heartbeats; fires single batched
                                   push_public("errors", ...) on anomalies
docs/
  data_flow.md                  Phase 1 invariants; missing Phase 2 collections
  PROJECT_STATE.md              THIS FILE
pyproject.toml
README.md                       stale; says Phase 2 is "what's next" with old ordering
```

## Section 6: Frontend file map

Directory layout:

```
app/
  layout.tsx                  root layout, fonts, ThemeProvider, QueryProvider
  page.tsx                    dashboard
  globals.css                 Tailwind v4 imports, font variable mappings,
                              shadcn .dark class
  holdings/[isin]/page.tsx    single holding drill-down
  reconciliation/page.tsx
  cost-basis/page.tsx
  transactions/page.tsx
  transactions/audit/page.tsx
  suggestions/page.tsx        F6: no actedThisSession; user_action stamp from
                              backend drives the collapsed-card render
                              F2: PENDING (next chat) — Buy/Sell toggle,
                              direction-aware fetch, sell-side dossier
                              rendering (tax_consideration +
                              concentration_note instead of portfolio_fit),
                              sell-side group_meta display
                              (booking_opportunity/valuation_stretch/risk/
                              tax_concentration instead of Q/V/M/N)
components/
  ui/                         shadcn primitives (button, card, dialog, popover,
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
  suggestion-card.tsx         full explainability layer (Commit B);
                              F6: CollapsedFeedbackRow when user_action != null
                              F2: PENDING (next chat) — branch on
                              dossier.direction to render tax_consideration +
                              concentration_note for sell, portfolio_fit for
                              buy; sell-side group bars from group_meta
  explain-popover.tsx         reusable info-icon popover (Commit B)
  page-intro.tsx              "How to read this page" collapsible (Commit B)
lib/
  api.ts                      hand-typed API client; SINGLE SOURCE OF TRUTH for
                              frontend types; ~600 lines.
                              F6+F10: UserAction, MonitoredStocksAuditEntry,
                              getRecentFeedbackAudit, getFeedbackAuditForIsin,
                              previous_status on submitFeedback response,
                              excluded_acted on SuggestionRun
                              F2: PENDING (next chat) — SuggestionDirection
                              type, direction param on getLatestRun /
                              listRuns / getPerformance, direction on
                              SuggestionRun + SuggestionOutcome + Dossier
  api-types.ts                GITIGNORED; auto-generated by `npm run gen-api`;
                              not actually used at runtime; do not check in
  format.ts                   inr(value), pct(value, withSign?),
                              colorForChange(value), dateTime(iso), nf, date
  utils.ts                    cn() (clsx + tailwind-merge)
  config.ts                   apiBaseUrl (reads NEXT_PUBLIC_API_BASE_URL env)
  query-client.tsx            TanStack Query provider
package.json
tsconfig.json                 paths: "@/*" -> "./*"
```

## Section 7: Database collections (exhaustive)

All collections live in MongoDB Atlas M10.
The DB name is set by env (`MONGODB_DB_NAME`).
All collections accessed via `Collections.<name>()` from `app.db.client`.
Indexes ensured at startup via `app/db/indexes.py`.

### Phase 1 collections

#### `instruments`
- Master NSE/BSE instrument list, refreshed daily from Zerodha Kite instruments CSV
- Key fields: `exchange`, `symbol`, `isin`, `name`, `instrument_type`, `segment`, `lot_size`, `tick_size`, `source`, `last_seen_at`, `last_changed_at`, `in_nifty100`
- Count: ~2,368 total; 100 with `in_nifty100=True`
- Indexes: `(exchange, symbol)` unique, `isin`, `last_seen_at`, `last_changed_at`, `in_nifty100`
- Writer: `scripts/refresh_instruments.py` (delta-aware), `scripts/seed_nifty100.py`, manual upserts for BSE-only stocks

#### `symbol_overrides`
- Manual ISIN aliases when the master list is wrong or missing
- Key fields: `exchange`, `symbol`, `isin`, `reason`, `created_at`
- Writer: `/instruments` router (CRUD)

#### `holdings`
- Active positions, one doc per ISIN; soft-deleted on full exit
- Key fields: `isin`, `symbol`, `exchange`, `name`, `sector`, `industry`, `quantity` (Decimal128), `avg_cost`, `invested_amount`, `realized_pnl`, `first_purchased_at`, `last_traded_at`, `thesis`, `notes`, `stop_loss`, `target_price`, `tags`, `deleted_at`
- INVARIANT: every query MUST include `deleted_at: None` to see active holdings; deleted holdings preserve replay correctness (FIFO needs full history)
- Indexes: `isin` unique (partial: only where `deleted_at` is None), `(deleted_at, last_traded_at)`
- Writer: `recompute_holding(isin)` in `holdings_service.py` is the ONLY authoritative writer; idempotent; recomputes from transactions from scratch using FIFO
- Note: `realized_pnl` is structural (FIFO computes it as a side-effect) but per user direction is HIDDEN in UI (see Section 13, Cleanup chat)
- F2 (Chat 4): `target_price` is now consumed by sell-side scoring (`target_price_proximity` signal in `booking_opportunity` group). `stop_loss` still unconsumed — see tech debt.

#### `transactions`
- Append-only ledger of all trades and corporate actions
- Key fields: `isin`, `symbol`, `exchange`, `type` (BUY/SELL/SPLIT/BONUS/DEMERGER), `trade_date`, `quantity` (Decimal128), `price`, `total_fees`, `remaining_quantity` (for FIFO lot tracking), `notes`, `source`, `corporate_action.ratio_from`, `corporate_action.ratio_to`, `fully_consumed_at`, `deleted_at`
- INVARIANT: never directly UPDATEd or DELETEd; edits and deletes go through `/transactions/{id}` PATCH/DELETE which require a reason, write to `transactions_audit` first, then apply the change, then call `recompute_holding`
- Indexes: `(isin, trade_date)`, `(symbol, trade_date)`, `trade_date`

#### `transactions_staging`
- Holding area for the bulk ICICI order book imports before promotion to live
- Same shape as `transactions`
- Cleared by `scripts/promote_staging.py --confirm --wipe-live`

#### `transactions_audit`
- Append-only audit log; one doc per edit/delete
- Key fields: `transaction_id`, `action` (edit/delete), `reason`, `changed_fields` (dict of {field: [before, after]}), `performed_at`, `symbol`
- INVARIANT: written BEFORE the actual change is applied, so even if the apply step crashes, the intent is recorded

#### `prices_daily`
- EOD OHLCV bars; ~5 years of history
- Key fields: `isin`, `date` (UTC-naive midnight), `open`, `high`, `low`, `close` (Decimal128), `volume`, `source`
- Count: ~115,791 docs across 100 NIFTY 100 ISINs (~1,158 per stock), plus 32 held ISINs
- Indexes: `(isin, date)` unique
- Writer: `scripts/refresh_prices.py` (yfinance)

#### `prices_intraday`
- Latest intraday quote captured every 15 min during market hours
- Key fields: `isin`, `symbol`, `date` (UTC), `captured_at`, OHLCV, `source="yfinance_5m_latest"`
- INVARIANT: append-only within a day (not upserted) so we keep history
- No TTL configured yet
- Writer: `scripts/refresh_prices_intraday.py`
- Consumer: `bulk_get_latest_prices` prefers today's intraday over EOD; falls back to EOD

#### `reconciliation_snapshots`
- Daily comparisons of our system totals vs ICICI Direct portfolio totals
- Key fields: `type` (manual/auto), `taken_at`, `our_invested`, `our_current_value`, `our_day_gain`, `icici_invested`, `icici_current_value`, `icici_day_gain`, `drift_invested_pct`, `drift_current_pct`, `drift_alerts` (list of strings), `notes`
- Writer: `/reconciliation/snapshot` (manual) or `/reconciliation/auto-snapshot` (cron at 19:30 IST weekdays)
- Drift detection rules: invested has baseline-relative drift; current_value uses absolute 15k threshold (intra-day timing is noise); day_gain dropped from alerts (always noise)

#### `cost_basis_adjustments`
- Audit trail for tax-correct cost basis adjustments (e.g., TMPV/TMCV demerger per IT Act Section 49(2C))
- Key fields: `name`, `amount` (Decimal128), `effective_date`, `it_act_section`, `rationale`, `source_documents`, `created_at`
- Consumer: `compute_summary` adds `broker_invested = our_invested + total_adjustment`, plus `broker_unrealized_pnl` and `broker_unrealized_pnl_pct`, so the UI can show both tax view and broker view

#### `user_profile`
- Single doc, `_id="sahil"`
- Holds investing philosophy notes, TMPV/TMCV cost basis annotation, etc.

### Phase 2 collections (Suggestions Engine)

#### `monitored_stocks`
- User-feedback state for stocks the engine has surfaced, plus watchlist entries (F13)
- Key fields: `isin`, `status` (writers use `"tracking"/"passed"/"rejected"/"watchlist"`; Pydantic model says `"tracking"/"promoted_to_holding"/"dropped"` — SCHEMA DRIFT, see tech debt), `acted_at`, `passed_at`, `rejected_at`, `last_feedback_at`, `last_feedback_action`, `last_feedback_note`, `created_at`, `updated_at`
- INVARIANT: writes go through `routers/suggestions.submit_feedback` only, using raw `update_one` (Pydantic bypassed because of the schema drift)
- INVARIANT (F10): every write is preceded by a `monitored_stocks_audit_service.log_change(...)` insert. Audit row lands BEFORE the `update_one` apply, so even if the apply crashes the intent is recorded. Same write-before-apply pattern as `transactions_audit`.
- Consumer: `suggestion_engine.get_excluded_isins()` (renamed from `get_rejected_isins` in Chat 3) returns three buckets at run-build time:
  - `rejected` — `status="rejected"` AND `rejected_at >= now - 90d`
  - `passed` — `status="passed"` for this run only (resurfaces next Sunday)
  - `acted` — `status="tracking"` AND `acted_at >= now - 30d` (F5b 30-day soft-exclude; naturally suppressed thereafter by the held filter if the trade landed, or resurfaces if it didn't)
- Consumer: `explainability._build_user_action()` at serialization time stamps each enriched candidate with `user_action` (null | "acted" | "passed" | "rejected") + the corresponding timestamp.
  This is the second of the two F6 exclusion mechanisms — see Section 14.
- F2 (Chat 4): `monitored_stocks` is CURRENTLY DIRECTION-AGNOSTIC. A user rejecting a SELL suggestion for INFY also suppresses the next BUY suggestion for INFY for 90 days, and vice versa. Documented in `get_excluded_isins` and `filter_sell_universe` docstrings. Acceptable for v1 (both interpretations are defensible: "I'm done thinking about INFY"). Add a `direction` column if it bites in practice — pending tech debt item.
- Indexes: `isin` unique, `(status, rejected_at)`

#### `monitored_stocks_audit` (F10 — shipped Chat 3)
- Append-only audit log for `monitored_stocks` writes; one doc per `POST /suggestions/{isin}/feedback`
- Key fields: `isin`, `action` (`"acted"|"passed"|"rejected"`), `previous_status` (string or null), `new_status`, `note`, `performed_at`, `_schema_version` (1)
- INVARIANT: append-only.
  Writer (`monitored_stocks_audit_service.log_change`) is invoked BEFORE the corresponding `monitored_stocks.update_one` apply in `submit_feedback`, so intent survives even if the apply step crashes.
  Mirrors `transactions_audit` exactly.
- Indexes: `(performed_at desc)`, `(isin, performed_at desc)`
- Writer: `app/services/monitored_stocks_audit_service.py`
- Consumer: `GET /suggestions/{isin}/audit` (per-ISIN history), `GET /suggestions/feedback/audit/recent?limit=N` (cross-ISIN feed for ops/debug surfaces and the frontend audit-trail view)

#### `instruments_fundamentals`
- One doc per ISIN per fundamentals refresh (so we have history)
- Key fields: `isin`, `symbol`, `as_of` (date), `fetched_at` (datetime), `market_cap`, `pe_ratio`, `pb_ratio`, `dividend_yield`, `return_on_equity`, `return_on_assets`, `operating_margin`, `debt_to_equity`, `earnings_growth_yoy`, `revenue_growth_yoy`, `beta`, `fifty_two_week_high`, `fifty_two_week_low`, `sector` (yfinance), `industry`, `source`, `source_raw` (full yfinance dict for replay), `fields_present`, `fields_missing`
- Indexes: `isin_latest_unique` (unique, latest only via `(isin, fetched_at desc)`), `fetched_at`
- Writer: `scripts/refresh_fundamentals.py` → `fundamentals_service.refresh_one`. F14: default universe is now NIFTY 100 ∪ active holdings (held stocks outside NIFTY 100 also need fundamentals for F2 sell-side scoring).
- Consumer: `suggestion_engine` (scoring), `explainability.py` (raw values for UI rendering)

#### `earnings_calendar` (F14 — shipped Chat 4)
- Upcoming + historical earnings events per ISIN. Source = yfinance `Ticker.calendar`, refreshed weekly alongside fundamentals.
- Key fields: `isin`, `symbol`, `exchange`, `earnings_date` (tz-naive datetime), `source` ("yfinance"), `source_raw` (sanitized yfinance calendar dict), `fetched_at`, `created_at`
- INVARIANT (refresh semantics): `refresh_earnings_for(isin, symbol, exchange)` deletes ALL future events for the ISIN (>= today) then re-inserts the freshly-fetched list. Past events are immutable history. yfinance occasionally shifts a confirmed date — we lose the "we used to think it was 7/25" history (acceptable for v1; consumer only ever asks "next earnings >= today").
- INVARIANT (BSON sanitization): yfinance `Ticker.calendar` contains `datetime.date` values (notably `Ex-Dividend Date`) that BSON cannot encode. `_sanitize_for_bson` in `fundamentals_service.py` recursively walks dicts/lists and coerces date → datetime, tz-aware → naive, Timestamp/numpy scalars → native, unknown → `str()`. Applied to `source_raw` before insert.
- Indexes: `(isin, earnings_date)` unique, `(earnings_date asc)`, `(isin)`, `(fetched_at desc)`
- Writer: `fundamentals_service.refresh_earnings_for` (single ISIN), `refresh_earnings_universe` (bulk; called by `scripts/refresh_fundamentals.py`)
- Consumer: `fundamentals_service.get_next_earnings_for_isin` / `get_next_earnings_bulk`; `suggestion_engine` (buy + sell pipelines) threads result into `score_candidates` / `score_sell_candidates`; `scoring_service.evaluate_earnings_proximity_gate` skips trades within 5 days of an earnings event (shared between buy and sell).

#### `news_articles`
- Classified news per article; one doc per URL with `$addToSet`-merged `entities_isins`
- Key fields: `url` (unique), `title`, `published_at`, `fetched_at`, `source`, `body` (purged after classification), `body_purged_at`, `entities_isins` (list), `themes` (`Literal[earnings|regulatory|corporate_action|management_commentary|sector_macro|noise]`), `sentiment` (positive/neutral/negative/mixed), `sentiment_confidence`, `severity` (low/medium/high), `classifier_summary`, `classified` (bool)
- Indexes: `url` unique, `(entities_isins, classified, fetched_at)`, `(classified, fetched_at)`
- Writer: `news_fetcher.py` (fetch) then `news_classifier.py` (classify in two-phase Haiku batches: `BATCH_SIZE=25` main pass, `RETRY_PASS_BATCH_SIZE=3` for stragglers)
- Consumer: `news_signals.py` (compute `net_sentiment`, `story_velocity`, `story_count`), `dossier_service.py` (per-candidate news context, last 8 articles)

#### `suggestion_runs`
- Append-only history of every weekly run
- Key fields: `_id`, `_schema_version`, `run_date`, `run_date_ist`, `run_type` (scheduled/manual), `direction` (`"buy"`|`"sell"`, default `"buy"`), `status` (success/partial/failure), `started_at`, `finished_at`, `error`, `universe_size`, `excluded_held`, `excluded_rejected`, `excluded_passed` (F6), `excluded_acted` (F5b), `excluded_stale_data`, `candidates_considered`, `candidates_post_gates`, `config` (full snapshot of weights, gates, freshness, scoring, top_k, version), `top_candidates` (list of CandidateScore docs, persisted in full), `all_candidates`, `top_k`, `notes` (JSON string containing dossiers array)
- INVARIANT: append-only; never updated; re-running creates a new doc
- INVARIANT: `top_candidates[*].user_action` is NOT in the persisted doc. It is added at API serialization time by `enrich_run` only. See Section 12 + Section 14.
- INVARIANT (F2 / Chat 4): pre-F2 runs persisted without a `direction` key still load cleanly. Pydantic default = `"buy"` via `model_validate`. The router serializer (`_serialize_run`) also defensively defaults missing `direction` to `"buy"` for the raw-dict path, and `/runs` adds it to the projection. Sell-side runs persist with `direction="sell"` explicitly.
- Indexes: `(run_date desc)`, `(run_date_ist, run_type)`, `(status)`

#### `suggestion_outcomes`
- One doc per top-K candidate per run; tracks actual stock + benchmark over 30/60/90/180-day windows
- Key fields: `isin`, `symbol`, `suggestion_run_id`, `suggested_at`, `suggested_at_price`, `suggested_rank`, `suggested_composite_score`, `tracking_status` (open/acted/passed/rejected/expired), `direction` (`"buy"`|`"sell"`, default `"buy"`), `price_at_30d/60d/90d/180d`, `nifty_at_30d/60d/90d/180d` (these are RETURN PERCENTAGES vs benchmark, not prices — equal-weighted NIFTY 100), `excess_return_30d/60d/90d/180d`, `user_action_at`, `user_action_note`, `created_at`, `updated_at`
- INVARIANT (changed in Commit A.5): snapshot eligibility is `tracking_status != "expired"`, NOT `tracking_status == "open"`. The user's label (acted/passed/rejected) is metadata; data collection continues regardless so per-bucket performance is measurable.
- INVARIANT: outcomes only auto-flip to `"expired"` if still labeled `"open"` at day 180. User-set labels are never overwritten.
- INVARIANT (F2 / Chat 4): `direction` defaults to `"buy"` for pre-F2 outcomes via the Pydantic default. `compute_system_performance(direction="sell")` sign-flips `excess_return` per outcome before aggregating so "higher is better" framing is preserved.
- Indexes: `(isin, suggested_at desc)`, `(suggested_at desc)`, `(tracking_status)`, `(suggestion_run_id)`
- Writer: `outcome_tracker.create_outcomes_for_run` at run time (stamps direction), `snapshot_open_outcomes` daily (direction-agnostic; same snapshot serves both directions)

#### `tavily_quota`
- One doc per UTC day; counters incremented atomically
- Key fields: `date` (YYYY-MM-DD string), `total_calls`, `total_credits`, `per_use_case.<name>.calls`, `per_use_case.<name>.credits`
- Indexes: `date` unique
- Writer: `tavily_client.py` `$inc` updates with upsert
- INVARIANT: `TAVILY_DAILY_CALL_LIMIT` (default 200) enforced; raises `TavilyQuotaExceeded` when hit

#### `digest_deliveries`
- Audit log of weekly digest emails + ntfy pushes
- Key fields: `run_id`, `run_date_ist`, `sent_at`, `top_count`, `subject`, `email_ok`, `email_id`, `email_error`, `ntfy_ok`, `ntfy_status`, `ntfy_error`
- F2 (Chat 4): for combined-digest sends (`--direction=both` cron path), the row attaches to the BUY run id so one row per delivery is preserved. `top_count = buy_top + sell_top`.
- Indexes: `(sent_at desc)`, `(run_id)`
- Writer: `digest_delivery.send_weekly_digest` (single-direction) or `digest_delivery.send_combined_digest` (both)

#### `cron_heartbeats` (F4 — shipped Chat 2)
- One doc per cron run with start/finish/status/error/metadata. Written by every cron script via the `cron_run()` context manager in `app/services/cron_heartbeat_service.py`.
- Key fields: `cron_name`, `started_at`, `finished_at`, `status` (`"success"|"failure"|"skipped"`), `error`, `metadata` (dict, per-cron stats), `_schema_version`
- INVARIANT: append-only. Wrapper writes exactly one doc per run on exit; on exception the heartbeat is recorded with `status="failure"` and the exception re-raised so the script's own exit-code path is preserved.
- INVARIANT: heartbeat write is best-effort — if Mongo is unreachable the write is swallowed rather than masking the underlying cron error. The missing heartbeat itself is what the next day's health check catches.
- INVARIANT (Chat 4): the context manager yields a `_Heartbeat` object that exposes `.meta` as an ATTRIBUTE. Set via `ctx.meta = {...}` (full replace) or `ctx.meta[key] = value`. `ctx["meta"] = ...` raises TypeError. (Three call sites in `run_weekly_suggestions.py` had this bug in Chat 4; fixed in chunk 6.2.)
- `"skipped"` status is for "nothing to do" runs (e.g., intraday refresh when market is closed). Counts as healthy in the daily check.
- Indexes: `(cron_name, started_at desc)`, `(started_at desc)`, TTL on `started_at` (60 days)
- Consumer: `GET /cron/heartbeats` router; `scripts/cron_health_check.py` (daily 21:00 IST)
- Writer: `app.services.cron_heartbeat_service.cron_run()` context manager — used by all registered cron scripts including `cron_health_check` itself
- The expected cron schedule lives in code as `CRON_REGISTRY` (a list of `CronSpec` entries) in `cron_heartbeat_service.py` — NOT in Mongo. Keep `CRON_REGISTRY` and `crontab -l` in sync whenever a cron is added or rescheduled.

### `digests` / `alerts_log` / `conversations` / `macro_signals`
Scaffolds; not actively written by current code.
`conversations` will be used for chat features (F1, F3).
Reserved; do not delete.

### Future collections (planned, not yet created)
- None pending in the current plan after F14 shipped. F11 (capital gains pack) is a read-only reformatter on existing collections.

## Section 8: API endpoints (exhaustive)

All routes are under the FastAPI app, served on port 8000 (EC2) or 8001 (Mac local).
All return JSON.
ISIN path params are validated 12-char.

### Phase 1

```
GET    /health
GET    /portfolio/holdings                           Holding[]
GET    /portfolio/holdings/{isin}                    Holding
POST   /portfolio/holdings                           Holding (BUY)
PATCH  /portfolio/holdings/{isin}                    Holding (notes/thesis/stop_loss/target_price/tags only)
POST   /portfolio/holdings/{isin}/sell               Holding OR {message, realized_total}
POST   /portfolio/holdings/{isin}/preview-sell       SellPreview
GET    /portfolio/holdings/{isin}/history?days=N     PriceBar[]
GET    /portfolio/holdings/{isin}/transactions       Transaction[]
GET    /portfolio/summary                            PortfolioSummary
GET    /transactions/search?symbol&type&from_date&to_date&skip&limit
                                                     {results, total}
GET    /transactions/{id}                            Transaction
PATCH  /transactions/{id}                            Transaction (requires reason)
DELETE /transactions/{id}                            {deleted: true} (requires reason)
GET    /transactions/audit/recent?limit=N            AuditEntry[]
GET    /transactions/{id}/audit                      AuditEntry[]
POST   /reconciliation/snapshot                      ReconciliationSnapshot (manual)
GET    /reconciliation/snapshots                     ReconciliationSnapshot[]
POST   /reconciliation/auto-snapshot                 ReconciliationSnapshot (cron)
GET    /cost-basis/adjustments                       CostBasisAdjustment[]
GET    /instruments                                  symbol_overrides list
POST   /instruments                                  symbol_overrides upsert
DELETE /instruments/{exchange}/{symbol}              delete override
```

### Phase 2 (Suggestions)

```
GET    /suggestions/latest?direction=buy|sell        SuggestionRun + enrichment
                                                     F2: ?direction defaults to "buy"
                                                     for back-compat; pre-F2 docs without
                                                     the field match the buy filter via
                                                     $or {direction:"buy"} OR
                                                        {direction:{$exists:false}}.
GET    /suggestions/runs?direction=buy|sell&limit=N&skip=N
                                                     {runs, total, limit, skip}
                                                     F2: same direction semantics
GET    /suggestions/runs/{run_id}                    SuggestionRun + enrichment
                                                     direction is implicit in the doc
GET    /suggestions/performance?direction=buy|sell   SuggestionPerformance with by_bucket
                                                     F2: direction optional. None =
                                                     cross-direction (legacy; semantically
                                                     muddy). "sell" sign-flips
                                                     excess_return at aggregation time.
POST   /suggestions/{isin}/feedback                  {isin, action, status, previous_status}
                                                     Body: {action: "acted"|"passed"|"rejected", note?: string}
                                                     NOTE: direction-agnostic; see
                                                     monitored_stocks tech debt
GET    /suggestions/{isin}/audit?limit=N             MonitoredStocksAuditEntry[]   (F10)
GET    /suggestions/feedback/audit/recent?limit=N    MonitoredStocksAuditEntry[]   (F10)
GET    /cron/heartbeats?limit=N                      {heartbeats, health_summary}
                                                     (F4 — shipped Chat 2)
                                                     F2: registry now includes
                                                     weekly_suggestions_sell
```

`/cron/heartbeats` response shape:
- `heartbeats`: newest-first list of recent cron run docs (default limit 200, capped at 1000)
- `health_summary`: one entry per registered cron with `cron_name`, `description`, `schedule`, `expected_today`, `min_runs_per_day`, `last_run_at`, `last_status`, `last_error`, `today_total`, `today_success`, `today_failure`, `today_skipped`, `healthy`
- `healthy = true` when either (a) cron is not expected today, or (b) `today_success + today_skipped >= min_runs_per_day` AND `today_failure == 0`

F10 feedback-audit endpoint shape (shipped Chat 3):
- Each row: `{_id, isin, action, previous_status, new_status, note, performed_at, _schema_version}`
- `/suggestions/{isin}/audit` is backed by the `(isin, performed_at desc)` compound index; mirrors `GET /transactions/{id}/audit`
- `/suggestions/feedback/audit/recent` is backed by the `(performed_at desc)` index; mirrors `GET /transactions/audit/recent`
- The static-path `/feedback/audit/recent` route is declared BEFORE the dynamic `/{isin}/audit` route in `routers/suggestions.py` to avoid any route-ordering ambiguity

### Future endpoints (planned)

```
POST   /watchlist/{isin}                             add to watchlist (F13)
DELETE /watchlist/{isin}                             remove from watchlist (F13)
GET    /watchlist                                    list watchlist (F13)
GET    /portfolio/risk-summary                       concentration & risk alerts (F12)
GET    /portfolio/by-tag?tag=X                       holdings grouped/filtered by tag (F15)
POST   /chat/suggestions                             ad-hoc chat about suggestions (F1)
POST   /chat/holdings/{isin}                         ad-hoc chat about a holding (F3)
GET    /tax/capital-gains?fy=YYYY-YY                 capital gains pack (F11)
```

### Sell endpoint response shape (critical, often confused)
`POST /portfolio/holdings/{isin}/sell` returns one of:
- The full updated `Holding` doc (partial sell, position still active)
- `{message: "Position fully exited", realized_total: "<string Decimal>"}` (full exit)

The frontend discriminates via type guard on the `_id` field, NOT a status field.
The original `SellSheet` was written this way; do not change it.

## Section 9: Cron registry on EC2

Run `crontab -l` to see current state.
As of Chat 4, every script below is heartbeat-instrumented via `app.services.cron_heartbeat_service.cron_run()` and writes a doc to `cron_heartbeats` on completion (success, failure, or skipped).
The daily `cron_health_check` at 21:00 IST consumes those heartbeats and fires `push_public("errors", ...)` on anomalies.
`CRON_REGISTRY` in `cron_heartbeat_service.py` is the in-code mirror of this schedule — keep both in sync.

Registered entries on EC2:

```cron
# Phase 1 crons (heartbeat-instrumented Chat 2)
# Daily instrument refresh — 03:00 IST
0 3 * * * cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/refresh_instruments.py >> /home/ubuntu/cron-instruments.log 2>&1
# Weekday EOD price refresh — 19:00 IST
0 19 * * 1-5 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/refresh_prices.py >> /home/ubuntu/cron-prices.log 2>&1
# Intraday price refresh — every 15 min during market hours (09:15-15:45 IST), weekdays
*/15 9-15 * * 1-5 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/refresh_prices_intraday.py >> /home/ubuntu/cron-prices-intraday.log 2>&1
# Daily reconciliation auto-snapshot — 19:30 IST (after price refresh)
30 19 * * 1-5 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/take_reconciliation_snapshot.py >> /home/ubuntu/cron-reconciliation.log 2>&1

# Phase 2 crons (registered Chat 2 via F5a — all heartbeat-instrumented)
# Sunday 06:00 IST — refresh fundamentals + earnings calendar for NIFTY 100 ∪ held (F14 expansion)
0 6 * * 0 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/refresh_fundamentals.py >> /home/ubuntu/cron-fundamentals.log 2>&1
# Sunday 06:30 IST — fetch + classify news for the universe
30 6 * * 0 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/fetch_news_for_universe.py >> /home/ubuntu/cron-news.log 2>&1
# Sunday 07:00 IST — run weekly suggestions
# PENDING: line still uses default (--direction=buy implicit). Chat 4 added
# --direction=buy|sell|both. To get combined buy+sell digest, swap this line
# to use --direction=both. Until swapped, sell-side will NOT run on Sunday cron.
0 7 * * 0 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/run_weekly_suggestions.py --notify --run-type scheduled >> /home/ubuntu/cron-suggestions.log 2>&1
# Weekdays 19:45 IST — outcome tracking snapshot (after 19:00 EOD refresh + 19:30 reconciliation)
45 19 * * 1-5 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/track_suggestion_outcomes.py >> /home/ubuntu/cron-outcomes.log 2>&1

# F4 cron health monitoring (added Chat 2)
# Daily 21:00 IST — health check; fires ntfy on anomalies
0 21 * * * cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/cron_health_check.py >> /home/ubuntu/cron-health.log 2>&1

# Maintenance
# Weekly log truncation — keep last ~10K lines on logs > 10MB
0 0 * * 0 find /home/ubuntu -maxdepth 1 -name "cron-*.log" -size +10M -exec sh -c 'tail -10000 "$1" > "$1.tmp" && mv "$1.tmp" "$1"' _ {} \;
```

PENDING ONE-TIME EC2 STEPS (Chat 4 follow-up — manual, not committable):
- Swap the Sunday 07:00 IST line to `... run_weekly_suggestions.py --direction=both --notify --run-type scheduled ...` so the combined buy+sell digest path is exercised by cron. Until done, sell-side suggestions only run from manual `--direction=sell` invocations.
- Stop + disable the self-hosted private ntfy service (F2b moved digests to public ntfy.sh; the private service is no longer used). One-time: `sudo systemctl stop ntfy && sudo systemctl disable ntfy`.

`CRON_REGISTRY` (in code) now also contains:
- `weekly_suggestions_sell` — `CronSpec(cron_name="weekly_suggestions_sell", description="Weekly sell-side suggestions: profit-booking candidates from active holdings.", schedule_human="Sun 07:30 IST", expected_weekdays={6})`
  - The standalone `weekly_suggestions_sell` cron line is NOT yet registered on EC2. The recommended production path is `--direction=both` under the existing `weekly_suggestions` umbrella heartbeat. The standalone registry entry exists so a future deployment topology that wants two separate runs can install the matching crontab line without code changes.

No silent failures: every cron registration must include log file paths AND be heartbeat-instrumented via `cron_run()` AND have a corresponding `CronSpec` entry in `CRON_REGISTRY`.
Adding a cron without all three breaks the F4 contract.

## Section 10: Settings and environment variables

Configured in `app/config/settings.py` via pydantic-settings reading `/etc/portfolio-advisor/secrets.env` (EC2) or `<repo>/.env` (Mac).
All required unless marked default.

### Anthropic
- `ANTHROPIC_API_KEY` (required)
- `ANTHROPIC_MODEL_PRIMARY` (default `"claude-sonnet-4-5"`) — used by `dossier_service`, chat features
- `ANTHROPIC_MODEL_FAST` (default `"claude-haiku-4-5"`) — used by `news_classifier`

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
- `NTFY_URL` (was: private self-hosted, behind Tailscale Funnel). F2b: no longer used by digest_delivery. Pending decommission. `push_private` still exists in `notify.py` for any future genuinely-sensitive content path.
- `NTFY_USER`, `NTFY_PASS` (basic auth for private — same as above)
- `NTFY_PUBLIC_URL` (default `"https://ntfy.sh"`)
- `NTFY_PUBLIC_TOPIC_PRICE`, `NTFY_PUBLIC_TOPIC_NEWS`, `NTFY_PUBLIC_TOPIC_ERRORS` (public ntfy.sh topics; unguessable strings act as bearer tokens; full content delivered instantly to iOS)
- `NTFY_PUBLIC_TOPIC_DIGESTS` (F2b — REQUIRED, no default. Used by `digest_delivery._send_ntfy` for weekly digest pushes. Must be subscribed on the iPhone ntfy app.)
- `NTFY_PUBLIC_TOPIC_ERRORS` specifically is used by F4 `cron_health_check` — if you change the topic value, also update the subscription on the iPhone ntfy app
- All `NTFY_PUBLIC_TOPIC_*` values must be IDENTICAL on EC2 and Mac so dev-testing of alert paths reaches the same subscribed device
- `push_public(channel)` signature: `channel: Literal["price", "news", "errors", "digests"]`; defined in `app/services/notify.py`. F4 cron alerts use `push_public("errors", ...)` for instant iOS delivery; content is "script name + error message", no portfolio/PII data. F2b digests use `push_public("digests", ...)`; content includes top symbols and composite scores, no PII.

## Section 11: Phase 1 INVARIANTS — never violate

These come straight from `docs/data_flow.md`.
They are hard rules.

- Transactions are immutable except through the audited PATCH/DELETE flow. Every PATCH/DELETE writes a `transactions_audit` entry BEFORE applying the change. The `reason` field is required.
- `recompute_holding(isin)` is the only authoritative writer to `holdings`. It is idempotent and recomputes from `transactions` from scratch using FIFO. Never write directly to `holdings`. Call `recompute_holding` after any transaction change.
- `validate_replay(isin, simulated_transactions)` simulates a transaction set and rejects any timeline that produces negative quantity at any point. Both PATCH and DELETE on `/transactions/{id}` call this before applying.
- `holdings.deleted_at = None` filter is universal. Every read of active holdings must include this filter. Deleted holdings preserve replay correctness.
- Cost basis is IT-Act-correct, not broker-nominal. `holdings.invested_amount` reflects the tax-correct cost basis (which for TMPV/TMCV reflects the 68.85/31.15 cost basis split per Tata Motors official Section 49(2C) disclosure). The broker-nominal view is recoverable as `holdings.invested_amount + total_cost_basis_adjustment` and surfaced via `summary.totals.broker_invested`.
- `prices_intraday` writes are append-only within a day (inserted, not upserted) so we keep intraday history.
- ICICI portfolio display shows TMPV at ~813 and TMCV at ~253 (sums to ~1,06,673), which is ~25k higher than our correct ~81,337. Our numbers reflect tax-correct cost basis; ICICI display is cosmetically wrong but does not affect actual money or tax filing.

## Section 12: Phase 2 INVARIANTS

- `suggestion_runs` are append-only. Re-running creates a new doc; never UPDATEd.
- `tavily_quota` is one doc per UTC day with `$inc` counters. Hard ceiling enforced.
- Confidence score is deterministic (computed from data freshness and signal availability), NOT LLM-generated. Composite score answers "is this stock attractive?"; confidence answers "should I trust the answer?"
- The dossier prompt requires narrative-only output. Numbers come from our data. The prompt forbids "buy" or "sell" imperatives. The prompt also forbids inventing facts not in the input.
- `gate_meta`, `group_meta`, `signal_meta`, `confidence_meta`, `feedback_meta`, `page_intro`, and `user_action` are PRESENTATION metadata, added by `routers/suggestions._serialize_run` via `enrich_run`. They are NOT in the persistent model. The router calls `enrich_run` after JSON conversion; the underlying `suggestion_runs` doc is never mutated. (`user_action` was added in Chat 3 via F6; see Section 14 for the two-mechanism rationale.)
- Snapshot eligibility for `outcome_tracker.snapshot_open_outcomes` is `tracking_status != "expired"`, NOT `tracking_status == "open"`. User-set labels (acted/passed/rejected) do not gate data collection. (Changed in Commit A.5.)
- Auto-expiry only flips outcomes that are still labeled `"open"` at day 180. A user-set label is never auto-overwritten. (Changed in Commit A.5.)
- Feedback re-labels the MOST RECENT non-expired outcome for the ISIN, regardless of its current `tracking_status`. (Fixed in Commit A.5.1.)
- `suggestion_engine.get_excluded_isins()` (renamed from `get_rejected_isins` in Chat 3 / F6) returns three buckets used to exclude ISINs at run-build time:
  - `rejected` — `monitored_stocks.status == "rejected"` AND `rejected_at >= now - 90d`. Auto-expires after 90 days. The 90-day window is intentionally NOT env-configurable; change the constant in `suggestion_engine.py` in one place if it ever needs to move.
  - `passed` — `monitored_stocks.status == "passed"`. THIS run only — naturally resurfaces on the next run because the bucket is recomputed every time.
  - `acted` — `monitored_stocks.status == "tracking"` AND `acted_at >= now - 30d` (F5b). Soft-exclude for 30 days; naturally suppressed thereafter by the held filter if the trade landed, or resurfaces if it didn't. There is no manual-clear mechanism and we deliberately did not build one.
- F10 write-before-apply: every `POST /suggestions/{isin}/feedback` writes the `monitored_stocks_audit` row via `monitored_stocks_audit_service.log_change(...)` BEFORE the corresponding `monitored_stocks.update_one` apply. Same invariant as `transactions_audit` — intent survives even if the apply step crashes.
- Per `monitored_stocks` schema-vs-writer drift: the model says `Literal["tracking", "promoted_to_holding", "dropped"]` but the writer writes `"tracking"`, `"passed"`, `"rejected"`. The writer uses raw `update_one` so Pydantic is bypassed. If you ever load a `monitored_stocks` doc through `MonitoredStock(**doc)` it will throw. See tech debt (F5c).
- The `notes` field on a `SuggestionRun` is a JSON string containing `{dossiers: [...]}`. The router parses it and exposes `dossiers` at the top level of the response, then strips `notes`. The router also strips `all_candidates` from the response to keep payloads small. The persisted doc still has it.

### F2 / F14 invariants (Chat 4)

- `SuggestionDirection` literal = `"buy" | "sell"`. Both `SuggestionRun.direction` and `SuggestionOutcome.direction` default to `"buy"` so pre-F2 persisted docs coerce cleanly via `model_validate`.
- The router serializer (`_serialize_run`) and the `/runs` projection BOTH defensively default missing `direction` to `"buy"` on the raw-dict path. Pydantic defaults fire on `model_validate`; the router serializes raw dicts and needs its own default. (Bug fixed in chunk 3.1.)
- `compute_system_performance(direction="sell")` SIGN-FLIPS `excess_return` per outcome before aggregating, so "higher avg_excess_return_pct = engine helpful" framing is consistent regardless of side. Cross-direction (`direction=None`) is supported but semantically muddy and discouraged.
- `snapshot_open_outcomes` is DIRECTION-AGNOSTIC: it snapshots prices for all non-expired outcomes (both directions) on the same daily schedule. Sign-flipping happens at read time, not at write time. Correct division of concerns.
- `earnings_calendar` refresh has REPLACE-FUTURE semantics: `refresh_earnings_for(isin, ...)` deletes all events for the ISIN with `earnings_date >= today` then re-inserts the freshly-fetched list. Past events are never touched. yfinance date shifts therefore lose the "we used to think it was 7/25" history (acceptable for v1 since the consumer only ever asks "next earnings >= today").
- `_sanitize_for_bson` is applied to `Ticker.calendar` BEFORE inserting into `earnings_calendar` because yfinance puts `datetime.date` values in `Ex-Dividend Date` (BSON can't encode `date`, only `datetime`). Recursively walks dicts/lists; coerces date → datetime, tz-aware → naive, Timestamp/numpy → native, unknown → `str()`. Future-proofs against new yfinance fields.
- F14 earnings-proximity gate is SHARED between buy and sell via `evaluate_earnings_proximity_gate`. Both directions skip trades within 5 days of a known earnings event. When `next_earnings` is None the gate reports `skipped=True, passed=True` (absence of data is not evidence of imminence).
- Sell-side scoring uses different groups (`booking_opportunity`/`valuation_stretch`/`risk`/`tax_concentration`) and different gates (`in_profit`/`min_position_age`/`earnings_proximity`). `high_severity_negative_news` is NOT a sell gate — it's a SIGNAL in the sell `risk` group (we WANT to surface bad-news stocks as sell candidates, not hide them).
- `CandidateScore` has FIXED buy-side group fields (`quality_score`, `valuation_score`, `momentum_score`, `news_score`). Sell-side rows leave them at 0.0; the actual sell-side group scores live in the signals list and are surfaced via `group_meta` from `explainability.py`. KNOWN DISPLAY BUG: `digest_delivery` renders Q=V=M=N=0 in sell-side email/ntfy sections because the template doesn't branch on direction — see Section 18.
- `monitored_stocks` is currently DIRECTION-AGNOSTIC. A user rejecting a SELL suggestion for INFY also suppresses next BUY for INFY for 90 days, and vice versa. Acceptable for v1; add a `direction` column if it bites in practice (tech debt).
- F2 combined-digest delivery: when `scripts/run_weekly_suggestions.py --direction=both` runs, `send_combined_digest(buy_run, sell_run)` emits ONE email + ONE ntfy push covering both sides. The `digest_deliveries` row attaches to the buy run id so chronological history (one row per delivery) is preserved.

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
- Commit A (backend explainability): explainability catalog, `plain_english_summary` on dossiers, `enrich_run` on responses
- Commit A.5 (feedback correctness): snapshot gating fixed, outcome relabel for "rejected", by_bucket performance breakdown
- Commit A.5.1 (re-label correctness): outcome relabel updates the most recent non-expired outcome regardless of current status
- Commit B (frontend explainability): popovers on QVMN, confidence, gates, signals, feedback buttons; "What this means" plain-English block; "How to read this page" page intro; vanish-on-click for actioned cards (session-scoped — REPLACED in Chat 3); performance tab renders by_bucket table per window

Chat 2 (F4 + F5a) — Cron observability shipped:
- F4: `cron_heartbeats` collection with 60-day TTL; `cron_run()` context manager wrapping every cron script (success/failure/skipped); `CRON_REGISTRY` in code mirroring `crontab -l`; `GET /cron/heartbeats` endpoint returning recent heartbeats + per-cron health summary; `scripts/cron_health_check.py` runs daily 21:00 IST and fires `push_public("errors", ...)` on missed runs / failures; `ntfy.PublicChannel` extended with `"errors"`; `NTFY_PUBLIC_TOPIC_ERRORS` added to settings.
- F5a: all four Phase 2 crons registered on EC2 with log files and heartbeat instrumentation — `refresh_fundamentals` (Sun 06:00 IST), `fetch_news_for_universe` (Sun 06:30 IST), `run_weekly_suggestions --notify --run-type scheduled` (Sun 07:00 IST, buy-side), `track_suggestion_outcomes` (weekdays 19:45 IST).
- All eight historic Phase 1 + Phase 2 crons now write heartbeats from the same wrapper.

Chat 3 (F6 + F5b + F10) — Stateful feedback shipped:
- F6 (stateful suggestion feedback): replaces the session-scoped vanish-on-click from Commit B with persistent backend exclusion. Two mechanisms (both required, see Section 14):
  - `suggestion_engine.get_excluded_isins()` (renamed from `get_rejected_isins`) runs at run-build time and returns `{rejected, passed, acted}` buckets. `filter_universe` consumes the dict; saves Tavily + Sonnet cost by not scoring excluded ISINs.
  - `explainability._build_user_action()` runs at serialization time. Each enriched candidate carries a `user_action` field (null | "acted" | "passed" | "rejected") plus the relevant timestamp, so a stale cached run (e.g. Sunday run viewed Tuesday after Monday's feedback) renders correctly. Lookup is one bulk `monitored_stocks.find({"isin": {"$in": [...]}})` per run-serialization, dict lookup per candidate (mirrors `bulk_get_latest_prices`).
- `SuggestionRun` carries new `excluded_passed` + `excluded_acted` counters.
- Frontend: `actedThisSession` set REMOVED from `app/suggestions/page.tsx`. `suggestion-card.tsx` renders a collapsed `CollapsedFeedbackRow` when `user_action != null`, with expand affordance. Parent-owned mutation flow (`onFeedback`, `feedbackPending`) preserved.
- `lib/api.ts`: additive — `UserAction`, `MonitoredStocksAuditEntry`, `excluded_acted?`, `previous_status` on `submitFeedback` response, plus the two new audit-endpoint wrappers.
- F5b (acted-but-not-held trap fix): `get_excluded_isins` includes the `acted` bucket (`status="tracking"` AND `acted_at >= now - 30d`) with `ACTED_EXCLUDE_WINDOW_DAYS = 30`. Naturally suppressed thereafter by the held filter if the trade landed, or resurfaces if it didn't. No manual-clear mechanism by design.
- F10 (monitored_stocks_audit append-only audit collection): new `monitored_stocks_audit` collection with `(performed_at desc)` + `(isin, performed_at desc)` indexes; `Collections.monitored_stocks_audit()` accessor; `app/services/monitored_stocks_audit_service.py`; `submit_feedback` writes audit row BEFORE the `update_one` apply, then applies, then re-labels the latest non-expired outcome; response now includes `previous_status`. New endpoints `GET /suggestions/{isin}/audit` and `GET /suggestions/feedback/audit/recent?limit=N`.

Chat 4 (F2b + F14 + F2 backend) — Sell-side foundation + plumbing shipped:
- F2b (ntfy public migration for digests): `digest_delivery._send_ntfy` switched from self-hosted private path (poll-based on iOS — silently dropped digests) to `push_public("digests", ...)` on public ntfy.sh. `notify.PublicChannel` extended with `"digests"`. `NTFY_PUBLIC_TOPIC_DIGESTS` added to settings (required, no default). Verified end-to-end: server emits message, iPhone receives push instantly via APNs.
- F14 (earnings calendar foundation): NEW `earnings_calendar` collection with `(isin, earnings_date)` unique + 3 supporting indexes; NEW `EarningsEvent` Pydantic model; `Collections.earnings_calendar()` accessor; `fundamentals_service.fetch_earnings_calendar_yfinance`, `refresh_earnings_for` (replace-future semantics), `refresh_earnings_universe`, `get_next_earnings_for_isin`, `get_next_earnings_bulk`; `_sanitize_for_bson` to coerce `datetime.date` from yfinance Ex-Dividend before BSON insert; `scripts/refresh_fundamentals.py` default universe expanded to NIFTY 100 ∪ active holdings and now refreshes earnings in the same Sunday cron; F14 earnings-proximity gate shared between buy and sell via `evaluate_earnings_proximity_gate`.
- F2 (sell-side backend): `SuggestionDirection` Literal; `direction` field on `SuggestionRun` + `SuggestionOutcome` (default "buy"); router defensive defaulting in `_serialize_run` + `/runs` projection for pre-F2 docs; `DEFAULT_SELL_CONFIG`, `GROUP_SIGNALS_SELL`, `extract_sell_signals`, `evaluate_sell_gates`, `score_sell_candidates` in `scoring_service.py`; `score_group` + `composite_for_candidate` refactored to accept optional `group_signals_def` for sharing buy/sell normalization pipeline; `suggestion_engine.run_suggestions(direction=...)` dispatches to `_run_buy_pipeline` (now also activates F14 gate via `next_earnings_by_isin`) or `_run_sell_pipeline` (universe = active holdings, `portfolio_value` computed once via `bulk_get_latest_prices`); `dossier_service._SYSTEM_PROMPT_SELL` with `tax_consideration` + `concentration_note` fields, direction-aware `_parse_dossier` validation, per-candidate POSITION CONTEXT block; `outcome_tracker.create_outcomes_for_run` stamps `direction`; `compute_system_performance(direction=...)` with sign-flip for sell.
- F2 (router + CLI + cron registry + combined digest):
  - All four read endpoints (`/suggestions/latest`, `/runs`, `/runs/{id}`, `/performance`) accept `?direction=buy|sell` (default "buy" for back-compat).
  - `scripts/run_weekly_suggestions.py --direction=buy|sell|both` (default "buy"). `--no-notify` skips outcomes + digest. `--skip-dossiers` skips Claude (smoke-test only).
  - "both" runs buy then sell under ONE heartbeat and emits ONE combined digest via `digest_delivery.send_combined_digest`.
  - `CRON_REGISTRY` includes `weekly_suggestions_sell` (cron_name, description, schedule_human="Sun 07:30 IST", expected_weekdays={6}).
  - `send_combined_digest(buy_run, sell_run)`: composes subject with severity from max composite across both sides, blue-accent buy section and red-accent sell section in HTML email, parallel plain-text body, compact ntfy push with === BUY-SIDE === / === SELL-SIDE === headers. Delivery row attaches to the buy run id.

### Open items (final scope, prioritized)

#### Chat 4 continuation (NEW CHAT — start here)

Remaining work to close F2 fully:

1. F2 frontend (chunk 7 in Chat 4 plan):
   - `lib/api.ts`: add `SuggestionDirection` type, add `direction` query param to `getLatestRun` / `listRuns` / `getPerformance`, add `direction` field to `SuggestionRun` / `SuggestionOutcome` / `Dossier` types.
   - `app/suggestions/page.tsx`: Buy/Sell toggle (segmented control or shadcn Tabs — match existing tab pattern), direction-aware data fetch, persist last-selected side in URL or localStorage.
   - `components/suggestion-card.tsx`: branch on `dossier.direction` to render `tax_consideration` + `concentration_note` blocks instead of `portfolio_fit`; render sell-side group bars (booking_opportunity/valuation_stretch/risk/tax_concentration) from `group_meta` instead of Q/V/M/N; sell-side gate badges (in_profit, min_position_age, earnings_proximity); sell-side feedback buttons phrasing ("Sold", "Watched", "Disagree" or similar — defer copy to user).
   - Performance tab: optional direction filter (or hide direction selector and show buy by default).

2. KNOWN BUG to fix as part of frontend chunk OR a tiny backend-only patch (one or the other, your call):
   - `digest_delivery._format_email_html`, `_format_email_text`, and `_format_section_html` / `_format_section_text` all hard-code `Q={...} V={...} M={...} N={...}` in the per-candidate block. For sell-side runs and sell-side sections of combined digests, this prints `Q=0 V=0 M=0 N=0` because `CandidateScore` has fixed buy-side group fields and sell-side group scores live separately. Email + ntfy both display wrong scores for sell.
   - Quick fix: branch on `run.direction` (or on candidate-side direction from the parent run) and either (a) omit the Q/V/M/N line for sell-side, or (b) render sell-side group scores from a passed-in `group_meta` lookup. (a) is the smaller patch and sufficient because the email already has `composite | confidence` — the bar chart breakdown is icing.
   - User confirmed this bug from a real email received at 15:56 IST on 2026-05-18.

3. PROJECT_STATE.md rewrite (chunk 8 in Chat 4 plan):
   - This document IS that rewrite (partial — produced at the close of Chat 4 due to context loss). Next chat may further consolidate.

4. ONE-TIME EC2 STEPS (manual, not committable):
   - Update Sunday crontab line to use `--direction=both` (see Section 9).
   - Stop + disable self-hosted private ntfy service: `sudo systemctl stop ntfy && sudo systemctl disable ntfy` (F2b leftover).

#### F1. Ad-hoc chat about suggestions (Chat 5)
- A chat surface accessible from the Suggestions page where the user can ask the configured AI models questions about the current suggestions
- Purpose: improve suggestions for personal use by interrogating the model
- Uses Sonnet via Anthropic SDK
- State stored in `conversations` collection (already scaffolded)
- System prompt seeded with the current SuggestionRun JSON so the model has context
- Same conversational infrastructure as F3 — ship together

#### F3. Ad-hoc chat about a specific holding (Chat 5)
- A chat surface accessible from each holding's detail page
- User pastes a tip from family/friend; the model analyzes it in context (cost basis, current price, recent news, sector, position size) and gives a non-prescriptive view
- Shares conversational infrastructure with F1
- System prompt seeded with the holding's full state + recent news + portfolio context

#### F12. Concentration & risk dashboard (Chat 6)
- New endpoint `/portfolio/risk-summary` that returns alerts:
  - Single-stock concentration > 15%
  - Sector concentration > 30%
  - Correlated-group concentration (e.g., energy+utilities) > 20%
- Frontend renders as a card on dashboard
- Maps to "avoid mistakes" lever — over-concentration is how most retail loses money
- Bundled with F15

#### F15. Tag-based portfolio views (Chat 6)
- The `holdings.tags` field already exists and is editable; nothing consumes it
- Add: backend filtering + aggregation by tag, frontend filter chips on dashboard
- Aggregate performance by tag (are "high-conviction" picks actually beating "tactical" picks?)
- F2 sell-side respects tags: "long-term-compounder" only suggests sell on extreme overvaluation
- Bundled with F12

#### F13. Watchlist (extends suggestions universe) (Chat 7)
- Ability to put any NSE/BSE stock on a watchlist
- New `status="watchlist"` value in `monitored_stocks`
- `build_universe` becomes: NIFTY 100 ∪ watchlist − held − excluded
- Watchlist stocks go through same scoring, same gates, same dossiers — no special-case logic
- IMPORTANT: `refresh_fundamentals.py` must be extended to include watchlist ISINs (currently NIFTY 100 + held only after F14)
- IMPORTANT: `fetch_news_for_universe.py` must be extended similarly
- Frontend: "Watch" button on suggestion cards and holding detail pages, plus a `/watchlist` page
- Future chat features (F1/F3) can reference watchlist stocks
- Shipped after F2 so the universe-extension pattern is established

#### F11. Capital gains pack (re-scoped from FY tax pack) (Chat 8)
- Small reformatter on top of existing transactions + `recompute_holding` data
- Surfaces STCG/LTCG by FY, with per-trade breakdown
- New endpoint `GET /tax/capital-gains?fy=YYYY-YY`
- Simple frontend page that renders the breakdown
- No new computation — everything is already produced by FIFO
- Useful for CA at year end

#### Realized P&L UI hiding (small cleanup, bundled in Chat 8)
- Remove `realized_pnl` stat card from dashboard
- Remove `realized_pnl` row from holding detail
- Remove "Exited holdings" surface from main nav (still accessible via transactions search)
- KEEP `realized_pnl` on reconciliation page (debugging aid for drift alerts)
- KEEP all backend computation untouched (structural; FIFO produces it as a side-effect)

#### F5c. Tech debt commit (Chat 8)
- `monitored_stocks.status` Literal vs actual writes mismatch: update model to `Literal["tracking", "passed", "rejected", "watchlist"]` and add the fields the writer actually uses
- ADD direction column to `monitored_stocks` if direction-agnostic feedback bites in practice (see Section 18)
- Delete dead `app/models/news_article.py` after confirming no imports
- Update `docs/data_flow.md` to document Phase 2 collections and invariants (including F6/F5b/F10 from Chat 3 and F2/F2b/F14 from Chat 4)
- Reconcile two-paths drift: `digest_delivery.py` has its own copy of Resend + ntfy code rather than using `notify.py` wrappers — pick one path
- Fix the digest sell-side Q/V/M/N=0 cosmetic bug if not fixed earlier in Chat 4 continuation
- Bundled with F5d in Chat 8

#### F5d. README updates (Chat 8)
- Backend README still says Phase 2 is "what's next" with the old 2.1/2.2/2.3/2.4 ordering — rewrite to reflect what actually shipped
- Frontend README review

#### F7. One-time real data import — DONE LAST (Chat 9)

This is intentionally the final chat.
Reason: every preceding chat will create test artifacts (test feedback rows, test SELL transactions, test conversations, test heartbeats, etc.).
If we load real data first, every test session corrupts production state.
Loading last means F7 becomes the natural reset button — every test artifact gets wiped clean as part of going live.

Design:
- Backend-only wrapper script `refresh_from_icici.py` (no UI — agreed overkill for one-time use)
- Reads CSVs from `~/ai-stock-advisor-backend/data/icici/orderbooks/<FY>.csv` (gitignored)
- Pipeline: `import_orderbooks.py` → `add_manual_transactions.py` (idempotent) → `reconcile_staging.py` (report) → gated `promote_staging.py --confirm --wipe-live`
- Default behavior: wipe-and-replace (only `transactions`, `transactions_staging`, `holdings`)
- Safety rail INVERTED: `--keep-ui-trades` flag for the rare case where you want to merge in trades entered through the UI after the import (instead of the original "wipe is opt-in" design — since this runs last, wipe IS the feature)
- Other collections (`monitored_stocks`, `monitored_stocks_audit`, `conversations`, `cost_basis_adjustments`, `user_profile`, `instruments_fundamentals`, `earnings_calendar`, `prices_daily`, `prices_intraday`, etc.) are NOT wiped — they're either re-seeded automatically (cost basis) or contain valid history we want to keep
- After go-live, ALL future trades go through the Buy/Sell UI (which writes through `validate_replay`, audit, and `recompute_holding`). Never re-run this script except for a deliberate full reset.

Chat 9 is really a checklist, not a feature build:
1. Pull latest ICICI Order Book CSVs (one per FY)
2. Pull current ICICI Demat Holdings snapshot (for reconciliation target numbers)
3. Run wrapper script (wipes by default)
4. Inspect reconciliation report
5. Fix any drift via `add_manual_transactions.py` for cost basis splits, missing IPOs/bonuses
6. Re-reconcile until clean
7. Confirm dashboard, holdings, drill-down, suggestions all show real data
8. Run first real `run_weekly_suggestions.py --direction=both` and verify email arrives

The wrapper script itself is ~50 lines of glue; can be written at the start of Chat 9.

### Final chat split plan

| # | Chat | Scope | Status |
|---|---|---|---|
| 2 | Cron observability | F4 + F5a | SHIPPED 2026-05-16 |
| 3 | Stateful suggestions | F6 + F5b + F10 | SHIPPED 2026-05-17 |
| 4 | Sell-side suggestions | F2 + F2b + F14 | BACKEND SHIPPED 2026-05-18 (partial); frontend + digest bug + EC2 crontab swap + private ntfy decommission pending in CONTINUATION CHAT |
| 4.5 | Sell-side frontend | F2 frontend + digest sell-side bug fix + EC2 crontab swap + private ntfy decommission | NEXT |
| 5 | Chat features | F1 + F3 | open |
| 6 | Portfolio intelligence | F12 + F15 | open |
| 7 | Watchlist | F13 | open |
| 8 | Pre-launch cleanup | F11 + realized P&L hide + F5c + F5d | open |
| 9 | GO LIVE | F7 one-time real data import | open |

After Chat 4 (partial), Chat 4.5 + 5 working chats + 1 import chat remain.

## Section 14: Conventions the assistant has repeatedly drifted on

The assistant has confused these multiple times in past chats.
Memorize them.

- Port 8001 (Mac local), port 8000 (EC2). Always specify which.
- SSH-first for tests: every test block in chat MUST begin with `ssh ubuntu@100.112.20.41` and run curls against `localhost:8000` from inside the box. Do not give curls against the Tailscale IP from the Mac. Standing convention from Chat 3.
- Commit-block-after-code: every code/file delivery in chat MUST be followed by a paste-ready `git add .` + `git commit -m "..."` block, written in the project's existing commit-message style (subject ≤72 chars, optional body bullets). Standing convention from Chat 3.
- PROJECT_STATE.md is ALWAYS delivered as a complete full-file replacement, never as a patch, find-and-replace, or "rest unchanged", no matter how small the edit. This is non-negotiable and overrides any default preference for find-and-replace tooling. Standing convention from Chat 3.
- F6 two-mechanism feedback exclusion is intentional and both are required:
  - `get_excluded_isins` runs at **run-build time** — saves Tavily + Sonnet cost by not scoring excluded ISINs in the first place.
  - `user_action` stamping in `enrich_candidate` (via `_build_user_action`) runs at **serialization time** — handles the stale-cached-run case (Sunday run viewed Tuesday after Monday's feedback) where the persisted `top_candidates` already includes ISINs the user has since acted on.
  - Both are needed because they do different jobs. Removing either one breaks something.
- The 90-day rejected cooldown (`REJECTED_EXCLUDE_WINDOW_DAYS = 90`) and the 30-day acted soft-exclude (`ACTED_EXCLUDE_WINDOW_DAYS = 30`) are intentionally NOT env-configurable. If the windows ever need to move, change the constants in `suggestion_engine.py` in one place. Avoiding config knobs that don't earn their keep is a deliberate simplicity choice.
- F10 write-before-apply: `monitored_stocks_audit_service.log_change(...)` is called BEFORE `monitored_stocks.update_one(...)` in `submit_feedback`. Same pattern as `transactions_audit_service.log_change(...)` relative to transactions PATCH/DELETE.
- Secrets path on EC2 is `/etc/portfolio-advisor/secrets.env` — NOT `~/secrets/secrets.env`. The latter was a transient debug artifact. Confirmed by `find` on the live EC2.
- `lib/api.ts` is hand-typed (~600 lines). The auto-generated `lib/api-types.ts` is gitignored and not used at runtime. When extending types, edit `lib/api.ts` directly. When the file is becoming long, prefer additive patches over full replacement.
- Mutations in frontend use `refetchQueries` (synchronous, blocks until refetch finishes so toast appears AFTER fresh data), NOT `invalidateQueries` (lazy).
- `cn` helper is at `@/lib/utils` (clsx + tailwind-merge). Format helpers at `@/lib/format`: `inr(value)`, `pct(value, withSign?)`, `colorForChange(value)`, `dateTime(iso)`, `nf`, `date(iso)`.
- Collections accessor: `from app.db.client import Collections`, then `Collections.holdings()`, etc. Never raw `db["holdings"]`.
- Decimal128 vs Decimal: helpers in `app/models/_common.py`. Mongo stores Decimal128; Python code works with Decimal; conversion happens at the boundary.
- Datetimes: UTC-naive in Mongo. IST in UI. `utcnow()` from `app/models/_common.py`. Watch for naive-vs-aware errors — the codebase has hit this multiple times.
- Heredoc for multi-line Python in shell: use `<<'EOF'` form, NOT nested `bash -c "..."`.
- Original `SuggestionCard` takes parent-owned mutation via `onFeedback` callback and `feedbackPending` prop. Mutation lives in parent. Do not redesign.
- `/suggestions` page uses shadcn Tabs. Do not replace with custom button toggles. Existing card structure: top bar with back link, header with refresh, error/empty/loading states, then Tabs with three values: `"latest"` / `"performance"` / `"history"`. Performance and history tabs use `enabled: activeTab === "..."`.
- Original `SuggestionCard` has helpers `Section`, `DossierSection`, `GroupBar`, etc. inline at the bottom of the same file. Keep them or evolve them; don't extract or rename without reason.
- Tailwind v4 + shadcn `.dark` class pickup is automatic — don't add explicit `useTheme` calls just to flip colors.
- Every cron script registered on EC2 must be wrapped in `cron_run("<name>")` from `app.services.cron_heartbeat_service` AND have a matching `CronSpec` in `CRON_REGISTRY` AND have a crontab entry with log file redirection. All three. (F4 contract.)

### Chat 4 additions

- **DO NOT trust Glean snippets or memory for dataclass / Pydantic model field names.** BEFORE writing any patch that constructs `Foo(field=...)`, run `grep -B 2 -A 20 "class Foo" <file_path>` on the actual file on disk (EC2 or local repo). Three drifts in Chat 4 for `CronSpec` (`job_name` → `name` → `cron_name`, all wrong before the fourth attempt). Glean snippets often surface call sites or docstrings that LOOK like field definitions; only the `@dataclass` body is authoritative. Same rule for `_Heartbeat`, `CandidateScore`, `EarningsEvent`, etc.
- **`cron_run()` yields a `_Heartbeat` object that exposes `.meta` as an ATTRIBUTE, not `__setitem__`.** Use `ctx.meta = {...}` (full replace) or `ctx.meta[key] = value` (per-key set). `ctx["meta"] = ...` raises `TypeError: '_Heartbeat' object does not support item assignment`. Three call sites in `run_weekly_suggestions.py` had this bug; fixed in chunk 6.2.
- **The `/cron/heartbeats` endpoint returns `{heartbeats, health_summary}`, not `{registry, recent}` or `{jobs}`.** Each `health_summary` row has `cron_name`, `description`, `schedule`, `expected_today`, `min_runs_per_day`, `last_run_at`, `last_status`, `last_error`, `today_total`, `today_success`, `today_failure`, `today_skipped`, `healthy`. Each `heartbeats` row has `cron_name`, `started_at`, `finished_at`, `status`, `error`, `metadata`. The assistant wrote tests using three different wrong key names in Chat 4 before getting it right.
- **`Collections.instruments_fundamentals()` is the accessor name** — NOT `Collections.fundamentals_snapshots()` (that doesn't exist). The on-disk collection name is `instruments_fundamentals`. Verified by `grep "def instruments_fundamentals" app/db/client.py`.
- **`run_suggestions()` is SLOW by default** — even with `--no-notify` it still generates Claude dossiers for top-K candidates (~2-4 min). Use `--skip-dossiers` for orchestrator smoke tests. Production cron must NOT use `--skip-dossiers` (digests would be empty).

## Section 15: Anti-patterns the assistant has fallen into

These have caused real rework.
Avoid.

- Full-file rewrites instead of additive patches. Once file is long, rewrite invites drift and inflates diff. For `lib/api.ts` specifically: always patch additively unless explicitly asked. EXCEPTION: PROJECT_STATE.md is always full-file (Section 14 standing convention).
- Inventing parallel patterns. If page uses shadcn Tabs, don't introduce a custom Toggle. If card uses parent-owned mutations, don't switch to internal mutations.
- Trusting memory for function names / response shapes / paths. RE-READ AT HEAD before patching.
- Truncating code with "rest unchanged" or "// existing code here". Forbidden.
- Asking "is this OK?" without applying the edit. If user has asked for the edit, apply it.
- Micro-commits when meaningful units of work are expected.
- Assuming GitHub content is current. Always check commit SHA.
- Producing files significantly larger than originals. If existing is 600 lines and new is 1,200, something is wrong. Halt and explain.
- Inventing fields in API responses. If unsure, hit the live endpoint and inspect.
- Forgetting to call `enrich_run` from new endpoints. Any `/suggestions/...` endpoint returning a SuggestionRun-shaped response should go through `_serialize_run`.
- Forgetting `holdings.deleted_at = None` is universal.
- Generating cron entries without log file paths or heartbeat monitoring. Per F4, no silent failures.
- Designing UI/UX features that aren't requested (e.g., a `/news` page when news only feeds dossiers; a backtesting UI; visual heatmaps). The tool is decision-support, not consumption.
- Shipping a code change without the paste-ready `git add .` + commit-message block. (Chat 3 standing convention; Section 14.)
- Shipping a test block without the `ssh ubuntu@100.112.20.41` first line. (Chat 3 standing convention; Section 14.)
- Trying to use `artifact_edit` or any find-and-replace flow on PROJECT_STATE.md instead of delivering it as a full-file artifact. (Chat 3 standing convention; Section 14.)
- Confusing the two F6 mechanisms (`get_excluded_isins` at run-build vs `_build_user_action` at serialization) or treating one as redundant. Both are required.

### Chat 4 additions

- **Guessing dataclass / model field names from Glean snippets without `grep`ing the file on disk first.** Three `CronSpec` drifts in Chat 4 (`job_name`, `name`, then correct `cron_name`) plus one `_Heartbeat` drift (`ctx["meta"]` vs correct `ctx.meta`). Each rebound consumed user context. THE FIX IS: BEFORE writing `Foo(field=value)`, run `grep -B 2 -A 20 "class Foo" <file>` on the actual on-disk file. No exceptions for "small" patches.
- **Writing multi-chunk plans that span >3 chunks without re-reading every touched file at HEAD before each chunk.** Chat 4 had a 6-chunk plan; chunks 2 / 3.1 / 4 / 6 all required mid-chunk recovery patches because the assistant wrote from memory of files read at the start. Pattern: re-read EVERY touched file at HEAD at the start of each chunk, even if read earlier in the chat.
- **Writing the same test block with three different wrong API response shapes for `/cron/heartbeats`.** The endpoint returns `{heartbeats, health_summary}` — verifiable in one `code_search` call. The assistant called it `{registry, recent}`, `{jobs}`, then finally checked. Test shapes are part of the API contract; don't guess.

## Section 16: "I am losing context" — escalation protocol

When the assistant notices ANY of the following symptoms, it must say verbatim:

```
I AM LOSING CONTEXT
```

so the user can switch to a new chat.
Better to escalate early than ship a broken commit.

### Triggers (any one is sufficient)
- Cannot recall a specific file structure that was discussed earlier in the chat
- Conflating Phase 1 facts with Phase 2 facts
- Forgetting which Commit (A, A.5, A.5.1, B) shipped which behavior
- Forgetting which Chat (2, 3, 4) shipped which feature (F4, F5a, F6, F5b, F10, F2, F2b, F14)
- Producing a file significantly larger than the original (>1.5x line count) without an explicit reason
- Starting to use generic patterns (e.g., shadcn defaults) instead of project conventions (e.g., the project's existing Section, GroupBar, DossierSection)
- Forgetting the port difference between Mac and EC2
- Forgetting the SSH-first test convention or the commit-block-after-code convention
- Forgetting the secrets path
- Forgetting the chat split plan from Section 13
- The user has to correct the same drift twice in the same chat
- The assistant has called glean_document_reader or code_search more than ~15 times in a single chat without converging
- The "Truncation Notice" appears in the assistant's context (the system tells the assistant earlier messages were dropped)
- The assistant is about to produce a third large code artifact and is unsure whether prior decisions still apply
- Chat 4 trigger added: the assistant has shipped two or more patches with WRONG field names in the same chat (e.g., guessing dataclass fields without grepping)
- Chat 4 trigger added: the assistant has shipped a test block with a WRONG API response shape and had to revise it

### What "switching chats" means
The user copies the bootstrap prompt from Section 0 into a fresh chat.
The new chat reads PROJECT_STATE.md first, then both repos at HEAD, then `docs/data_flow.md`, then READMEs.
The user states the scope.
The assistant summarizes back.
Only then does coding start.

The new chat is responsible for updating PROJECT_STATE.md at the end of its work, as the last commit, so the next chat is bootstrapped from current state.

### What NOT to do
- Do not silently degrade. User has explicitly said "don't silently degrade."
- Do not try to "wing it" through context loss. Ship-quality code requires full context.
- Do not produce artifacts when uncertain about conventions.

## Section 17: "Am I hallucinating?" diagnostic questions

If the user suspects the assistant has drifted, the user can ask any of these.
The assistant should be able to answer all correctly without re-reading.
If any wrong, switch chats.

- "What's the backend port on Mac local?" → 8001
- "What's the backend port on EC2?" → 8000
- "How does the assistant SSH into EC2?" → `ssh ubuntu@100.112.20.41`
- "Where do secrets live on EC2?" → `/etc/portfolio-advisor/secrets.env`
- "Where do secrets live on Mac?" → `<repo>/.env` (resolved via `LOCAL_SECRETS` fallback)
- "What does `recompute_holding(isin)` do?" → It is the only authoritative writer to `holdings`. Idempotent. Recomputes from transactions from scratch using FIFO. Always call after a transaction change.
- "What's the gating filter on `snapshot_open_outcomes`?" → `tracking_status != "expired"` (was `== "open"` pre-Commit-A.5)
- "Where does the dossier `plain_english_summary` field originate?" → `dossier_service.py`'s `_SYSTEM_PROMPT`, Sonnet, max 500 chars. Added in Commit A.
- "What is the universe filter in `build_universe`?" → NIFTY 100 (`instruments.in_nifty100 == True`) ∪ watchlist (after F13) − held (holdings where `deleted_at == None`) − excluded buckets returned by `get_excluded_isins` (rejected 90d, passed this-run-only, acted 30d soft-exclude). Renamed from `get_rejected_isins` in Chat 3.
- "What are the two F6 feedback-exclusion mechanisms and why both?" → `get_excluded_isins` at run-build time (saves Tavily + Sonnet cost) AND `_build_user_action` stamping at serialization time (handles stale-cached-run case). Both required.
- "What's the acted soft-exclude window? Is it env-configurable?" → 30 days (`ACTED_EXCLUDE_WINDOW_DAYS = 30`). Not env-configurable, by design. Same for the 90-day rejected window.
- "What's the F10 write-before-apply rule?" → `monitored_stocks_audit_service.log_change(...)` runs BEFORE `monitored_stocks.update_one(...)` in `submit_feedback`. Same pattern as `transactions_audit`.
- "What's the Q/V/M/N weight breakdown?" → 30% / 25% / 25% / 20%, version `"1.0.0-unit2"`
- "Is `lib/api-types.ts` checked into git?" → No, gitignored. Auto-generated by `npm run gen-api`. Hand-typed source is `lib/api.ts`.
- "What does the user prefer: `refetchQueries` or `invalidateQueries`?" → `refetchQueries` (synchronous)
- "What is the sell endpoint's response shape?" → Either full updated `Holding` doc (partial sell) or `{message, realized_total}` (full exit). Discriminated via type guard on `_id`.
- "Is dividend tracking part of this project?" → No. Dropped. Dividends settle to user's bank account; this tool is not an accounting system.
- "When does F7 (real data import) run in the chat sequence?" → Last. Chat 9. After all features are built and tested, so test pollution gets wiped on go-live.
- "How does a cron register itself with the F4 health system?" → Wrap `main()` body in `with cron_run("<cron_name>") as hb:` from `app.services.cron_heartbeat_service`, AND add a `CronSpec` entry to `CRON_REGISTRY` in the same file, AND add the crontab line on EC2 with log file redirection. All three are required.
- "Where do F4 cron failure alerts go?" → `push_public("errors", ...)` on public ntfy.sh, topic = `NTFY_PUBLIC_TOPIC_ERRORS`. Same topic value on Mac and EC2 so dev tests reach the phone.
- "What is the heartbeat schema?" → `{cron_name, started_at, finished_at, status ("success"|"failure"|"skipped"), error, metadata, _schema_version: 1}`. TTL 60 days on `started_at`.
- "What's the healthy/unhealthy rule?" → Healthy iff (not expected today) OR (`today_success + today_skipped >= min_runs_per_day` AND `today_failure == 0`).
- "How is PROJECT_STATE.md delivered?" → Always as a complete full-file canvas artifact, never as a patch or find-and-replace. No exceptions.
- "What must accompany every code/file delivery?" → A paste-ready `git add .` + `git commit -m "..."` block in chat.
- "How do test blocks start?" → With `ssh ubuntu@100.112.20.41`, followed by curls against `localhost:8000`.

### Chat 4 additions

- "What are the fields on `CronSpec`?" → `cron_name`, `description`, `schedule_human`, `expected_weekdays` (set of IST weekday numbers Mon=0..Sun=6), `min_runs_per_day` (default 1). NOT `name`, NOT `job_name`, NOT `schedule_cron`, NOT `crontab`, NOT `max_age_hours`.
- "How do you set metadata on a `_Heartbeat`?" → `ctx.meta = {...}` (full replace) or `ctx.meta[key] = value`. `_Heartbeat` is the object yielded by `cron_run()`. It exposes `.meta` as an ATTRIBUTE, not `__setitem__`. `ctx["meta"] = ...` raises TypeError.
- "What's the response shape of `/cron/heartbeats`?" → `{heartbeats: [...], health_summary: [...]}`. NOT `{registry, recent}`. NOT `{jobs}`.
- "What's the collection name for fundamentals snapshots?" → `instruments_fundamentals`. Accessor: `Collections.instruments_fundamentals()`. NOT `fundamentals_snapshots`.
- "Does `run_suggestions()` default to skipping dossiers?" → No. It generates dossiers by default (~2-4 min per run). Use `skip_dossiers=True` for orchestrator smoke tests. The CLI exposes this as `--skip-dossiers`. Production cron must NOT skip dossiers.
- "What's the new ntfy topic for digests (F2b)?" → `NTFY_PUBLIC_TOPIC_DIGESTS`, required (no default), used by `push_public("digests", ...)` in `digest_delivery._send_ntfy`.
- "What's the F14 earnings-proximity gate threshold?" → 5 days. Shared between buy and sell via `evaluate_earnings_proximity_gate`. Skips trades within 5 days of a known earnings event.
- "What's the sell-side gate set?" → `in_profit` (unrealized P&L >= 0%), `min_position_age` (held >= 30 days), `earnings_proximity` (> 5 days from next earnings). NOT `high_severity_negative_news` — that's a SIGNAL in the sell `risk` group, not a gate.
- "How does `compute_system_performance(direction='sell')` handle excess_return?" → It SIGN-FLIPS `excess_return` per outcome before aggregating, so "higher avg_excess_return_pct = engine helpful" framing is consistent regardless of side.

## Section 18: Tech debt registry (filed, not fixed)

Tracked here so nothing gets lost.
Cleared as part of Chat 8 (F5c + F5d) unless explicitly fixed earlier.

- `app/models/monitored_stock.py` — `status: Literal["tracking", "promoted_to_holding", "dropped"]` does not match writer reality. Writer uses raw `update_one` so Pydantic is bypassed. After F13 ships, will also need `"watchlist"` value.
- `monitored_stocks` is DIRECTION-AGNOSTIC (F2 / Chat 4). A user rejecting a SELL suggestion for INFY also suppresses the next BUY suggestion for INFY for 90 days, and vice versa. Acceptable for v1 (both interpretations are defensible). Add a `direction` column to `monitored_stocks` if it bites in practice — at which point F6 needs a partial rewrite to look up per-direction state.
- `app/models/news_article.py` — Older parallel model. Live model is `app/models/news.py`. Pick one and delete the other.
- `docs/data_flow.md` — Dated 2026-05-09. Missing Phase 2 collections and invariants (including F6/F5b/F10 from Chat 3 and F2/F2b/F14 from Chat 4). Update during F5c.
- `digest_delivery.py` has its own inline copies of Resend + ntfy code instead of using `notify.py` wrappers. Two paths. Pick one.
- `dossier_service.py` `valuation_verdict` is a single string with both label and rationale. To color-code labels, split into `valuation_label` and `valuation_rationale`. Defer until UI needs it.
- `SignalScore.raw_value` is misnamed — stores normalized 0-100 score, not raw fundamental value. `explainability.py` fetches raw values from `instruments_fundamentals` at API enrichment time as workaround.
- News signal raw values (`net_sentiment`, `story_velocity`, `story_count`) not persisted post-run. Frontend shows normalized only. Fix would require persisting `news_signals_by_isin` in SuggestionRun.
- Backend `README.md` stale (Phase 2 "what's next" with old ordering).
- `top_k` default in `scoring_service.DEFAULT_CONFIG` is 10 (correct). CLI script docstring example shows `--top-k 5` which is misleading.
- `holdings.stop_loss` field is editable in UI but nothing consumes it. (`target_price` is now consumed by sell-side as of F2 / Chat 4.) Either wire `stop_loss` to ntfy alerts (intraday price refresh comparison) or remove. Decide during cleanup.
- `app/services/cron_heartbeat_service.py` has an unused `SATURDAY` weekday-set constant (kept in case fundamentals ever move back to Saturday). Trivial — remove during F5c if still unused.
- `scripts/track_suggestion_outcomes.py` docstring header still says "Daily 18:30 IST" inside a parenthetical, even though the cron actually runs at 19:45 IST. Cosmetic — fix during F5c.

### Chat 4 additions

- **DIGEST SELL-SIDE Q/V/M/N BUG (real, user-confirmed):** `digest_delivery._format_email_html` (single-direction sell digest) and `_format_section_html`/`_format_section_text` (sell section of combined digest) hard-code per-candidate `Q={c.quality_score:.0f} V={c.valuation_score:.0f} M={c.momentum_score:.0f} N={c.news_score:.0f}`. For sell-side rows, `CandidateScore` has those fields at 0.0 because sell-side group scores live separately (booking_opportunity/valuation_stretch/risk/tax_concentration). User received email at 2026-05-18 15:56 IST showing `Q=0 V=0 M=0 N=0` for every LT/TATASTEEL/NTPC/... entry. Quick fix: branch on direction and either (a) omit the Q/V/M/N line for sell (composite + confidence already display), or (b) render sell-side group scores from a passed-in `group_meta`. Same fix applies to `_format_email_text` plain-text path. Suggested for early Chat 4.5 (cheaper than waiting for F5c).
- **CandidateScore has fixed buy-side group fields (`quality_score`, `valuation_score`, `momentum_score`, `news_score`).** For first-class sell-side group score fields (`booking_opportunity_score`, etc.) we'd need a model schema bump. Defer to F5c or until the digest+UI need them rendered as colored bars rather than text.
- **EC2 crontab Sunday line still uses default `--direction=buy` implicit** (the `--direction` flag was added in Chat 4 but the crontab line was not updated). Until updated, sell-side does NOT run on Sunday cron — only manual `--direction=sell` invocations exercise it. Recommended Chat 4.5 step: update the line to `--direction=both`.
- **EC2 self-hosted private ntfy service still running** but no longer used by `digest_delivery` after F2b. Pending one-time decommission: `sudo systemctl stop ntfy && sudo systemctl disable ntfy`. Confirm no other consumers first (`grep -r "push_private" app/`).
- **`enrich_run` page_intro is still buy-centric** even when `run.direction == "sell"`. The page renders correctly otherwise (gates, signals, group_meta all populate from the catalogs), but the introductory text talks about buying. Defer to Chat 4.5 frontend chunk or do a tiny additive backend patch (`PAGE_INTRO_SELL` literal + branch in `enrich_run`).

## Section 19: How to update this document

This file is updated at the end of every chat as the LAST commit.
ALWAYS delivered as a complete full-file canvas artifact, never as a patch, diff, or find-and-replace.
Standing convention from Chat 3; see Section 14.

What to update:
- Section 13 → move shipped items from "open" to "shipped"; add any new open items discovered; advance the chat split plan pointer
- Section 9 → update cron registry if cron entries were added/changed; document any pending manual EC2 steps
- Section 14 → add any new convention the assistant drifted on
- Section 15 → add any new anti-pattern that caused rework
- Section 16 → add any new triggers that should signal context loss
- Section 17 → add new diagnostic Q&A if a new fact category emerges
- Section 18 → add/remove tech debt items
- Section 12 → add any new Phase 2 invariant introduced
- Section 11 → add any new Phase 1 invariant introduced (rare; Phase 1 is locked)
- Section 7 → add new collections; update field lists when models change
- Section 8 → add new endpoints; update existing endpoint shapes
- Section 5/6 → add new files; remove deleted files

Commit message convention for PROJECT_STATE.md updates:

```
docs: update PROJECT_STATE.md after <chat scope>
- <bullet list of sections changed>
```

If the chat ended due to context loss (per Section 16), the LAST thing the assistant does before stopping is propose the PROJECT_STATE.md update.
The user applies it manually since the assistant is no longer reliable.

## Section 20: Trade-off rationale (decisions that might look weird)

For future-you (or a future assistant) who asks "why is this like this":

- yfinance over Tijori / Screener Pro: yfinance is free and works. Tijori is a future upgrade. Screener.in does NOT have a public Pro API (verified). Apify scraper rejected as TOS-gray and brittle. The `FundamentalsProvider` protocol in `fundamentals_service.py` is designed for swap-in replacement.
- Confidence is numeric 0-100 with deterministic deductions, not band-only: Bands hide information. Deductions are stored as plain English strings so they render directly.
- Suggestions run Sunday 06:00 IST (buy) and 07:00 IST (sell after F2): Sunday because Indian market is closed. Morning so user reads with coffee.
- Top-K = 10: Five was initial; user requested 10 mid-build. Engine default and CLI default are both 10.
- 90-day rejection cooldown for "rejected": Long enough to not nag. Short enough that material change can resurface. Intentionally NOT env-configurable — change the constant in `suggestion_engine.py` in one place if it ever needs to move.
- Zero cooldown for "passed" (F6): Per user — market conditions change, the same stock can become more relevant next week. "Passed" is "saw it, no opinion right now." Manual mid-week reruns also resurface it — that's intentional (if you're manually rerunning, you want fresh context).
- "Acted" soft-excludes for 30 days (F5b, F6): This is the ENTIRE acted rule, not a sub-mechanism of a permanent rule. After 30 days, the suggestion can resurface — intentional, because the underlying thesis may have strengthened (system may want to suggest buy-more for a position doing well, or sell-more for one about to give back gains). If the trade actually landed in holdings, the existing held filter in `build_universe` keeps it from resurfacing as a buy suggestion regardless — no special-case needed. The 30-day cap is what closes the acted-but-not-held trap. There is no manual-clear mechanism and we deliberately did not build one (mongosh is the escape hatch if operationally needed).
- Outcome snapshot ignores `tracking_status` for data collection (Commit A.5): Was filtering on `"open"` only, which silently broke performance measurement.
- Session-scoped vanish-on-click (Commit B) replaced by persistent backend state (Chat 3 / F6 + F5b + F10): Initial implementation was simple. Chat 3 makes it correct — feedback is durable, audit-trailed, and survives across browser sessions.
- `digest_delivery.py` having its own Resend/ntfy path: Defer to tech debt commit.
- Schema drift on `monitored_stocks.status`: Defer to tech debt commit (F5c); rename ripples.
- `enrich_run` mutates dict in-place AND returns it: Looks weird, works. Input is already a copy.
- Two-mechanism F6 exclusion (run-build `get_excluded_isins` + serialization-time `_build_user_action`): They do different jobs. Run-build exclusion saves Tavily + Sonnet cost by not scoring excluded ISINs. Serialization-time stamping handles the stale-cached-run case (Sunday run viewed Tuesday after Monday's feedback) where the persisted `top_candidates` already includes ISINs the user has since acted on. Both are needed.
- F10 read endpoints (`GET /suggestions/{isin}/audit` + `GET /suggestions/feedback/audit/recent`) shipped alongside the write path: Without them the audit is invisible without going to Mongo directly, which defeats F10's motivation.
- F10 static-path route declared before dynamic-path route: `/feedback/audit/recent` is declared in `routers/suggestions.py` BEFORE `/{isin}/audit`. The 12-char ISIN validator would prevent collision anyway, but declaring statically-pathed routes first is the safer convention and mirrors how `transactions.py` handles `/audit/recent` vs `/{id}/audit`.
- Why `valuation_verdict` is one string, not `{label, rationale}`: Sonnet finds it easier per JSON schema. Defer until UI needs color-coding.
- Why keep `all_candidates` persisted but strip from API: Replay-ability for future re-ranking with new weights. Keep payload light.
- Dividend tracking dropped (F8): User direction. Dividends settle to bank. This tool is for investment decisions, not accounting.
- Realized P&L hidden in UI but kept in backend (Chat 8 cleanup): User direction. The math is structural (FIFO produces it for free); the UI was clutter. Reconciliation page keeps it as debug aid for drift alerts.
- F7 sequenced last (Chat 9): Building features first means lots of test data pollution. F7's wipe-by-default behavior becomes the natural reset to clean state on go-live.
- F8 dropped instead of "do it later": Sahil framed his goal as "grow my money." Dividends auto-arrive in bank; tracking them adds zero decision value. Maintaining a feature that doesn't drive decisions is decoration.
- F14 folded into F2 instead of standalone: Earnings proximity matters most for sell decisions (timing) and as a small gate on buys (skip near-earnings noise). Doesn't justify its own surface.
- Watchlist (F13) extends the engine universe, not a separate scoring path: Watchlisted stocks go through the same gates, scoring, and dossiers. Special-casing would create two parallel pipelines to maintain.
- F4 ntfy errors channel chose public ntfy.sh (`push_public(channel="errors")`) over private self-hosted (`push_private(topic="errors")`): The private path is slower on iOS (poll-based) and the user has explicitly demanded no silent failures. Cron-failure alerts are name + error message only — no portfolio data, no PII — so the public path's content-exposure trade-off is acceptable. The `"errors"` channel was added to `settings.NTFY_PUBLIC_TOPIC_ERRORS` and to the `PublicChannel` Literal in `notify.py` during F4.
- F4 `CRON_REGISTRY` lives in code (`app/services/cron_heartbeat_service.py`), not in Mongo: Single-user system, schedule changes rarely, version-controlled with the heartbeat logic. The risk of drift between `crontab` and `CRON_REGISTRY` is mitigated by the health check itself — a missing `CRON_REGISTRY` entry would silently never alert, but a `crontab` entry missing from `CRON_REGISTRY` would simply not be tracked (loud failure on first ops review of `/cron/heartbeats`). Re-evaluate if the cron count gets large (>20) or if non-developers need to edit the schedule.
- F4 intraday uses "strict per-slot heartbeats" (~28/day) rather than "lenient first-of-day": Strict gives forensic value — you can see which 15-min slot failed and correlate with yfinance outages. The health check only alerts on complete absence (`today_success + today_skipped < min_runs_per_day`), so transient single-slot failures don't over-alert. `mark_skipped()` is used for "no holdings" / "market closed" cases so they count as healthy.
- `cron_health_check.py` is itself a registered cron in `CRON_REGISTRY`: It writes its own heartbeat so tomorrow's run can detect if today's check died silently. The check excludes itself when scanning today's anomalies to avoid a chicken-and-egg false positive.
- F5a kept user's Sunday cron chain (06:00 fundamentals → 06:30 news → 07:00 suggestions) instead of the originally-proposed Saturday-evening fundamentals + daily-05:00 news + Sunday-06:00 suggestions: User's existing schedule was already well-designed (fundamentals + news ready before the suggestion engine reads them on the same morning). `CRON_REGISTRY` was adjusted to match the existing schedule, not the other way around.

### Chat 4 additions

- F2b (digests on public ntfy.sh): the self-hosted ntfy on Tailscale Funnel was poll-based on iOS and silently dropped digests for days at a stretch. Public ntfy.sh delivers via APNs in ~1 sec. Digest content (top symbols, composite scores, broad valuation hints) has no PII and no broker credentials, so the public path's content-exposure trade-off is acceptable. Same logic that justified F4's `push_public("errors", ...)` extended to digests. The private path remains available in `notify.push_private` for any future genuinely-sensitive content.
- F14 (earnings calendar) shipped as a foundation collection + gate rather than as a UI feature: the consumer is the suggestion engine, not a `/calendar` page. Adding a calendar UI would be decoration for a single-user tool — the value is in the gating, not the consumption.
- F14 `refresh-future` semantics (delete >= today + reinsert) rather than per-event versioning: yfinance occasionally shifts confirmed earnings dates. The consumer only asks "next earnings >= today" — never "what date did we previously think Q2 was?". Versioning would be defensive without consumer demand. If we ever want to track date-shifts as an audit signal (e.g., companies that repeatedly shift dates), add a `supersedes` field then.
- F14 + F2 sell-side scoring: `score_group` and `composite_for_candidate` were refactored to accept an optional `group_signals_def` parameter (defaults to `GROUP_SIGNALS` for buy-side back-compat) so buy and sell can share the normalization pipeline without parallel copies. The alternative — two separate near-identical scoring entry points — would have created exactly the "parallel patterns" trap Section 14 warns against.
- F2 `CandidateScore` keeps fixed buy-side group fields (`quality_score`, `valuation_score`, `momentum_score`, `news_score`) at 0.0 for sell-side rows rather than getting first-class sell-side group fields: would require a model schema bump and migration; the actual sell-side group scores flow through `normalized_by_group` and `composite_for_candidate` to compute the composite correctly, and the frontend can read group scores from `group_meta` in `enrich_run`. The trade-off is the digest cosmetic bug documented in Section 18.
- F2 `--direction=both` as the production cron path (instead of two separate crontab lines): one Python process, one heartbeat row, one combined digest, one notification on the iPhone. The user explicitly didn't want two emails 30 minutes apart. The `weekly_suggestions_sell` `CronSpec` is kept in the registry for the alternative deployment topology, but the recommended production setup is the `--direction=both` umbrella.
- F2 `compute_system_performance(direction='sell')` sign-flips `excess_return` at read time, not at write time: snapshots are raw data and direction-agnostic by design (one `snapshot_open_outcomes` daily run serves both directions). Interpretation belongs at the consumer boundary. Same division-of-concerns principle as gate evaluation vs scoring (gates filter eligibility, scores rank within eligibility).
- F2 sell-side outcome direction stamping (vs inferring direction from `suggestion_run_id`): denormalization is intentional for query efficiency. Without the stamped field, every read of outcomes would need a `$lookup` to `suggestion_runs` to filter by direction. The field is 4 bytes and immutable (set at outcome creation, never updated). Worth the storage.

## Section 21: What is intentionally NOT included in this project

So future chats don't accidentally try to add these:

- Auto-trading. Never. Hard constraint.
- Multi-user support. Single-user by design.
- Mutual funds, FDs, foreign equities, derivatives, crypto. NSE/BSE equities only.
- Native mobile app. Web responsive is the plan.
- Tax filing. The system surfaces tax-correct cost basis to inform manual filing. It does not file.
- Dividend tracking (F8 dropped). Dividends settle to bank.
- Accounting or financial planning. Not the goal.
- Goal-based planning ("save X for Y by Z"). Accounting, not investing.
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
- Manual-clear endpoint for feedback (acted/passed/rejected). Deliberately not built. If operationally needed, use mongosh as the escape hatch. The 30-day acted soft-exclude, the per-run passed bucket, and the 90-day rejected cooldown all auto-expire.
- A `/calendar` / earnings-events page (F14 is a gating signal, not a consumption surface).
- A loss-cutting sell pipeline. F2 sell-side is for booking PROFITS only (the `in_profit` gate enforces this). Loss-cutting has different signals and is deliberately out of scope; not on the roadmap.

## Section 22: Glossary

- ISIN: International Securities Identification Number. 12-char unique identifier. Primary key for stocks. NSE/BSE quotes for the same company share an ISIN.
- NSE: National Stock Exchange of India.
- NIFTY 100: Index of top 100 NSE stocks by market cap. The Suggestions universe.
- FIFO: First-in-first-out cost basis. Required by Indian Income Tax Act.
- LTCG / STCG: Long-Term / Short-Term Capital Gains. >1 year holding = LTCG, ≤1 year = STCG. Tax rates differ (LTCG 12.5% above ₹1.25L exemption post Budget 2024; STCG 20%).
- Section 49(2C): IT Act clause governing cost basis allocation in demergers.
- ICICI Direct: The user's broker.
- ICICI ZIP: CSV exports from ICICI's "Order Book" download.
- TMPV / TMCV: Tata Motors PV and CV, split via demerger Oct 2025. Cost basis 68.85/31.15.
- EW NIFTY: Equal-weighted NIFTY 100 return — benchmark for outcome tracking.
- Composite score: 0-100, weighted sum of Q/V/M/N normalized scores (buy-side) or booking_opportunity/valuation_stretch/risk/tax_concentration normalized scores (sell-side, F2 / Chat 4).
- Confidence score: 0-100, deterministic, from data freshness + signal availability.
- Dossier: Sonnet-generated per-candidate research note (`plain_english_summary`, `one_line_thesis`, bull/bear/risks, `valuation_verdict`, `portfolio_fit` for buy / `tax_consideration` + `concentration_note` for sell).
- Outcome: `suggestion_outcomes` doc tracking what happened to a suggested stock vs benchmark over 30/60/90/180 days.
- Bucket: User-action label on an outcome (open/acted/passed/rejected/expired).
- Watchlist: User-curated list of stocks outside NIFTY 100 that should be considered by the engine (F13).
- `user_action`: Per-candidate stamp added at API serialization time (F6) — `null` | `"acted"` | `"passed"` | `"rejected"` — drives the collapsed-card render on the frontend. Not persisted in `suggestion_runs`.
- `direction` (F2 / Chat 4): `"buy"` | `"sell"` field on `SuggestionRun` and `SuggestionOutcome`. Defaults to `"buy"` so pre-F2 docs coerce. Buy-side scans NIFTY 100 minus held; sell-side scans held holdings for profit-booking candidates.
- `monitored_stocks_audit`: Append-only audit collection for feedback writes (F10). One doc per `POST /suggestions/{isin}/feedback`, written BEFORE the corresponding `monitored_stocks.update_one` apply.
- `earnings_calendar` (F14 / Chat 4): Cached upcoming + historical earnings events per ISIN. Source = yfinance `Ticker.calendar`. Consumer = F2 buy + sell scoring (gates skip trades within 5 days of an event).
- Combined digest (F2 / Chat 4): ONE email + ONE ntfy push sent by `send_combined_digest(buy_run, sell_run)` when the cron uses `--direction=both`. Avoids two notifications 30 minutes apart.

End of PROJECT_STATE.md.
