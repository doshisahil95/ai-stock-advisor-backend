
# PROJECT_STATE.md

Living source of truth for the Personal AI Stock Advisor.
Updated at the end of every chat.

This file is the bootstrap document for any new conversation with an AI assistant. If you (the assistant) are reading this for the first time in a new chat: read it top to bottom before doing anything. Do not skim. Do not assume. Do not redesign. The prior chat hit context limits or context drift — that's why we're here.

## Section 0: How to start a new chat

Paste this verbatim at the top of any new chat with an AI assistant working on this project:

```
I need you to continue work on a project called Personal AI Stock Advisor.
Before you do ANYTHING else, read the following in order:
1. https://github.com/doshisahil95/ai-stock-advisor-backend/blob/main/docs/Project_State.md
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
- ASK ME FOR THE CURRENT BACKEND (and frontend if relevant) SHA BEFORE
  PROPOSING ANY CODE CHANGE. Re-read the actual file at that SHA before
  writing any find-and-replace block. Find-blocks written from snippet
  memory or earlier-read state cause silent failures. Standing convention
  from Chat 5; see Section 14. NO EXCEPTIONS.
- Hand me full file contents OR exact find-and-replace.
  Never "rest unchanged".
- Use canvas artifacts for files. Use chat for tests.
- Project_State.md is ALWAYS delivered as a complete full-file
  replacement, never as a patch, find-and-replace, or "rest unchanged".
  No exceptions, no matter how small the edit.
- Every code/file change MUST be followed by a `git add .` + `git commit -m`
  block in chat, ready to paste, written in the project's commit-message
  style.
- Every test block MUST begin with `ssh ubuntu@100.112.20.41` and run
  curls against `localhost:8000` from inside the box (not against the
  Tailscale IP from the laptop).
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
- What you understood about the project from Project_State.md
- What's already shipped vs open
- The exact scope of today's chat
- Any uncertainty you have before starting

Do not start coding until I confirm your summary is accurate.
```

Note on filename casing: the file on disk is `docs/Project_State.md` (title case). GitHub paths are case-sensitive. Earlier copies of this bootstrap used `PROJECT_STATE.md` (all-caps) and `404`'d. The Section 0 prompt above uses the correct casing.

## Section 1: Project identity

Personal AI Stock Advisor. Single-user portfolio + research tool for Indian NSE equities. Built for and by Sahil Doshi (Senior Consulting Engineer, MongoDB, India).

Strict design constraint that overrides everything else: the system never executes trades. Sahil trades manually in ICICI Direct. The system records, analyzes, and advises only. Any feature that would auto-place an order is out of scope, permanently.

The system is also not regulatory advice. Dossiers and suggestions must use phrasing like "the system flagged this because..." and "this is a good buy because..." or "this is a good sell because...". The user decides; the user trades.

The goal of the system is to maximise the investments. Goal of the tool: grow money. Every feature is judged on whether it helps with one of:
- Buy better (find opportunities you'd otherwise miss)
- Sell better (exit before reversals, hold through noise)
- Avoid mistakes (concentration, FOMO, panic sells, missed corporate actions)
- Reduce costs (taxes, fees, opportunity cost of dead capital)

Anything that doesn't map to one of these is decoration and gets cut.

Explicitly NOT a goal: dividend tracking, accounting, financial planning, tax filing, goal-based planning. The tool informs investment decisions; bank statements and the CA handle the rest.

## Section 2: User communication preferences (apply to all chats)

- Honest, slightly contrarian opinions over fake agreement. The user will push back when he disagrees; the assistant must do the same.
- Build right, no shortcuts. Do not introduce avoidable rework.
- Math accuracy and legal compliance matter. If something is mathematically wrong or legally non-compliant, call it out immediately.
- Use existing project conventions. Do not invent parallel patterns.
- Give full file contents OR exact find-and-replace instructions. Never use placeholders like "rest unchanged" or "// existing code here". Do not truncate important code.
- Prefer meaningful units of work. Small enough to test, not so tiny that we ping-pong.
- Give concrete test commands when appropriate.
- Files go in canvas artifacts. Tests go in chat as fenced code blocks.
- Every mapping table must use Action column values: NEW FILE, REPLACE EXISTING, or PATCH.
- The user edits on Mac, commits, pushes. EC2 is for build/test/deploy/debug. The assistant should not edit Mac files directly; it produces artifacts the user pastes.
- Every code/file delivery in chat MUST be followed by a paste-ready `git add .` + `git commit -m "..."` block in the project's existing commit-message style.
- Every test block in chat MUST start with `ssh ubuntu@100.112.20.41` and run subsequent curls against `localhost:8000`. Do not give curls against the Tailscale IP from the Mac.
- Project_State.md is ALWAYS delivered as a complete full-file replacement, never a patch or diff or find-and-replace. No exceptions.
- ASK FOR CURRENT BACKEND SHA BEFORE PROPOSING ANY CODE CHANGE. Re-read the file at that SHA before writing the patch. (Chat 5 standing convention; see Section 14.)

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
- Resend (transactional email for digests, drift alerts, smoke tests — all routed through `notify.email()` as of Chat 5 A2)
- ntfy (push notifications — public ntfy.sh for all paths after F2b; self-hosted private path is still installed on EC2 but no longer used and pending decommission — see Section 18 TD8)

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
- AWS EC2 t3.micro instance in ap-south-1, Elastic IP `3.111.254.128` (whitelisted in Atlas)
- Tailscale only for application traffic — no public ingress, no Caddy yet
- MongoDB Atlas M10 (separate from EC2; access list limited to EC2 EIP + dev IPs)

## Section 4: Infrastructure paths and ports

### Network
- EC2 Tailscale IP: `100.112.20.41`
- EC2 Elastic IPv4 (public, for Atlas access list etc): `3.111.254.128`
- SSH from Mac: `ssh ubuntu@100.112.20.41`
- Backend port on EC2: `8000`
- Frontend port on EC2: `3000`
- Backend port on Mac (local dev): `8001` (NOT 8000)
- Frontend port on Mac (local dev): `3000`

This Mac vs EC2 port difference is a real, recurring source of confusion for assistants. The assistant has gotten this wrong multiple times. Always specify which machine when giving test commands. For chat-supplied test blocks, the standing convention is "SSH into EC2 first, then curl localhost:8000" — see Section 14.

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

The `Settings` class uses pydantic-settings with `model_config = SettingsConfigDict(env_file=str(SECRETS_FILE), env_file_encoding="utf-8", case_sensitive=True, extra="ignore")`. Pydantic-settings reads the file directly into the `Settings` object — secrets are NOT exported to `os.environ`.

If the assistant ever suggests `~/secrets/secrets.env` on EC2, it is wrong. That path was a transient debug artifact.

F2b addition (Chat 4): `NTFY_PUBLIC_TOPIC_DIGESTS` must be present in `/etc/portfolio-advisor/secrets.env` — required (no default). If missing, app startup fails with a Pydantic validation error. Subscribe the iPhone ntfy app to the topic value before running cron.

Chat 5 reminder: when rotating the Atlas password, update BOTH `secrets.env` files (EC2 and Mac) in the same session. URL-encode any password containing `@ : / ? # [ ] ! % & = +` via `python3 -c "from urllib.parse import quote_plus; print(quote_plus('PASTE'))"`. Atlas shows the new password only once after generation; losing it forces another rotation.

### Deploy scripts
On EC2:
- `~/deploy.sh` — pulls backend, runs `uv sync`, restarts `portfolio-advisor.service`
- `~/deploy-ui.sh` — pulls frontend, runs `npm install --legacy-peer-deps`, runs `npm run gen-api`, runs `npm run build`, restarts `portfolio-advisor-ui.service`

The `gen-api` step in `deploy-ui.sh` regenerates `lib/api-types.ts` against the running backend's OpenAPI spec. That file is gitignored.

On Mac, running `npm run gen-api` without overriding the URL will fail because Mac backend is on port 8001 and the default is 8000. Use:

```
API_OPENAPI_URL=http://100.112.20.41:8000 npm run gen-api
```

or just skip it — `lib/api-types.ts` is not used at runtime; `lib/api.ts` is hand-typed.

### systemd units on EC2
- `portfolio-advisor.service` — runs `uvicorn app.main:app --port 8000 --host 0.0.0.0` as user `ubuntu`, with `EnvironmentFile` NOT used (settings.py loads from `/etc/portfolio-advisor/secrets.env` directly), `Environment="PYTHONPATH=/home/ubuntu/ai-stock-advisor-backend"`, `Environment="PYTHONUNBUFFERED=1"`. Logs to journald.
- `portfolio-advisor-ui.service` — runs `node /home/ubuntu/ai-stock-advisor-frontend/node_modules/next/dist/bin/next start` on port 3000 with hardening (`NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict`, `ReadWritePaths` includes the frontend dir and `/tmp`).

A sudoers entry at `/etc/sudoers.d/portfolio-advisor-systemctl` lets `ubuntu` restart these services without password.

### Repos
- Backend: https://github.com/doshisahil95/ai-stock-advisor-backend
- Frontend: https://github.com/doshisahil95/ai-stock-advisor-frontend

GitHub is the source of truth for code. GitHub may serve cached content via Glean's reader. When in doubt, find the latest commit SHA and read at that SHA explicitly.

Last verified SHAs (Chat 5 mid-progress, 2026-05-23):
- Backend: `d3f307ac526289e248924b70c99c7b47ce0518d2`
- Frontend: `e34e1264cdaaeace345a8fa9b433c6b3213a134b` (untouched in Chat 5)

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
  news.py                   NewsArticle (live model — the only news model)
  monitored_stock.py        MonitoredStock + MonitoredStockFeedbackPatch
                            Chat 5 A1 SHIPPED — MonitoringStatus Literal now
                            matches writer reality: ["tracking","passed",
                            "rejected","watchlist"]; feedback fields
                            (acted_at/passed_at/rejected_at/last_feedback_*)
                            declared on the model; MonitoredStockFeedbackPatch
                            is the typed wrapper the writer uses to build
                            the $set patch (catches Literal drift at write
                            time via pydantic ValidationError).
                            See Section 12.
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
                            Chat 5 A1: /{isin}/feedback now constructs
                            MonitoredStockFeedbackPatch and $set-s
                            patch.model_dump(exclude_none=True) so prior-
                            action *_at timestamps survive across status
                            flips. $setOnInsert seeds added_by, added_reason,
                            _schema_version.
                            TECH DEBT A19 (Chat 5 audit): three Query()
                            calls use deprecated regex= param (lines 103,
                            138, 206). Migrate to pattern=. Cosmetic.
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
  reconciliation.py         take_auto_snapshot, drift detection, notify_drift
                            Chat 5 A2 PENDING: notify_drift has TWO email()
                            call sites (email_critical line ~267,
                            email_drift line ~290) each wrapping email() in
                            a bare try with unconditional sent.append(...).
                            Post-A2 part 1, notify.email() returns
                            {ok,id,error} and swallows exceptions instead
                            of raising. The wrapper try/except never fires,
                            so sent.append() now runs even on Resend
                            failures. Fix: check result["ok"] before
                            appending. Same pattern at both sites.
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
                            score_sell_candidates.
                            score_group + composite_for_candidate refactored
                            to accept optional group_signals_def (back-compat
                            with GROUP_SIGNALS default).
                            TECH DEBT A5: comment in DEFAULT_CONFIG.gates
                            still says earnings_proximity is "always
                            'skipped' in buy-side responses ... until then"
                            — outdated since F14 chunk 5 wired it.
                            TECH DEBT A3+A4: composite_for_candidate writes
                            normalized 0-100 score (f"{score:.2f}") into
                            SignalScore.raw_value, even though the model
                            has separate raw_value AND normalized_score
                            fields. News signal raw inputs
                            (net_sentiment, story_velocity, story_count)
                            also not persisted. Fix: writer should preserve
                            raw input from extract_signals into raw_value
                            and write the normalized into normalized_score.
                            Open question Q2 resolved Chat 5: option (b),
                            fix the writer, don't rename the field.
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
                            TECH DEBT A17: stale pre-chunk-6 comment in
                            _run_sell_pipeline saying "TWO digests if both
                            run with notify=True" — chunk 6 added
                            --direction=both umbrella that combines into
                            one digest. Delete comment.
  outcome_tracker.py        create_outcomes_for_run, snapshot_open_outcomes,
                            compute_system_performance
                            F2: create_outcomes_for_run stamps direction;
                            compute_system_performance accepts optional
                            direction filter and sign-flips excess_return
                            for sell-side at read time.
  digest_delivery.py        send_weekly_digest (Resend + ntfy),
                            send_combined_digest (F2 Chat 4 — both directions)
                            F2b: ntfy via push_public("digests", ...) on
                            public ntfy.sh; private path retired here.
                            F2b (2026-05-20 / cea8eee): _format_score_breakdown
                            is DIRECTION-AWARE — sell rows render
                            Book/Stretch/Risk/Tax-Conc from group_meta lookup
                            instead of Q/V/M/N=0. Closes 2026-05-18 bug.
                            Chat 5 A2 part 1 SHIPPED: _send_email now
                            delegates to notify.email() which returns
                            {ok,id,error}. No more inline `import resend`.
                            Verified end-to-end on EC2: real digest email
                            arrived in inbox, email_ok=True, email_id
                            populated, multipart/alternative working.
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
                            TECH DEBT A18: enrich_run page_intro is
                            buy-centric for sell runs (intro text only;
                            gates/signals/group_meta populate correctly).
                            Add PAGE_INTRO_SELL literal + branch.
  notify.py                 push_private, push_public, email
                            Chat 5 A2 part 1 SHIPPED: email() now accepts
                            optional `text=` param for multipart, returns
                            {ok, id, error} instead of raw resend dict.
                            All Resend traffic in the backend flows
                            through this wrapper. Callers:
                            digest_delivery._send_email (delegates here),
                            reconciliation.notify_drift (TWO sites — A2
                            part 2 pending, both have a real bug per
                            note above), scripts/smoke_test.py (safe under
                            new shape because it uses .get('id') which
                            works for both old and new dicts).
                            PublicChannel = "price" | "news" | "errors" |
                            "digests". PrivateTopic = "digests" | "errors".
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
                            TECH DEBT A6: weekly_suggestions CronSpec has
                            schedule_human="Sunday 06:00 IST" but the
                            actual crontab line is `0 7 * * 0` (07:00).
                            Cosmetic only.
                            TECH DEBT A7: SATURDAY = {5} weekday-set
                            constant is unused. Remove.
scripts/
  init_db.py
  refresh_instruments.py        TECH DEBT A13: docstring says "refreshes
                                from Zerodha Kite" but actual implementation
                                is refresh_from_nse() reading NSE's
                                official EQUITY_L.csv. Fix doc.
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
                                 active holdings; folds earnings refresh
                                 into the same Sunday cron via
                                 refresh_earnings_universe. --holdings-only
                                 and --symbols overrides preserved.
  fetch_news_for_universe.py     TECH DEBT A16: default universe excludes
                                 held stocks (get_universe_for_news filters
                                 them out unless --include-held is passed).
                                 The sell pipeline scans held stocks; if
                                 the cron doesn't pass --include-held,
                                 sell-side news scores are systematically
                                 thin for held names. Manual EC2 verify.
  run_weekly_suggestions.py      F2: --direction=buy|sell|both (default
                                 "buy"). "both" runs buy then sell under
                                 ONE heartbeat and emits ONE combined
                                 digest via send_combined_digest.
                                 --no-notify skips outcomes + digest.
                                 --skip-dossiers skips Claude (smoke-test
                                 only; not for production — emails will be
                                 content-empty, see Chat 5 confirmation).
                                 _do_buy/_do_sell/_do_both call sites use
                                 ctx.meta = {...} (NOT ctx["meta"] — see
                                 Section 14).
  track_suggestion_outcomes.py
  cron_health_check.py           F4: daily 21:00 IST; reads CRON_REGISTRY +
                                 today's heartbeats; fires single batched
                                 push_public("errors", ...) on anomalies
  smoke_test.py                  end-to-end smoke: Anthropic ping, ntfy
                                 private, ntfy public, Resend. Uses
                                 email_resp.get('id') so safe under both
                                 old and new notify.email() return shapes
                                 (Chat 5 A2).
docs/
  data_flow.md                  Phase 1 invariants; STALE — missing every
                                Phase 2 collection, cron, invariant.
                                Rewrite scheduled as the final Chat 5
                                deliverable after bug fixes are deployed.
  Project_State.md              THIS FILE
pyproject.toml
README.md                       STALE — calls Phase 2 "what's next" with
                                old ordering; omits /suggestions, /cron,
                                all Phase 2 collections, F2/F4/F14 crons,
                                Chat 5 work. Rewrite during Chat 5
                                cleanup pass.
```

(Frontend file map unchanged from prior version; no frontend code touched in Chat 5.)

## Section 6: Frontend file map

Directory layout (unchanged from prior version — no frontend touches in Chat 5):

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
                              backend drives the collapsed-card render.
                              F2: SHIPPED — useState<SuggestionDirection>("buy");
                              shadcn Tabs with "buy"/"sell" triggers and a
                              direction-row card; per-direction TanStack query
                              keys; direction-aware page subtitle + empty-state
                              copy; direction-aware toast description on
                              feedback.
components/
  ui/                         shadcn primitives (button, card, dialog, popover,
                              tabs, separator, badge, skeleton, etc.)
  holdings-table.tsx
  buy-sheet.tsx
  sell-sheet.tsx              Phase-1 manual SELL transaction sheet with FIFO
                              preview. NOT the F2 sell-side suggestion surface.
                              That lives inside suggestion-card.tsx via the
                              isSellSide branch.
  edit-transaction-sheet.tsx
  holding-header.tsx, holding-stats.tsx, price-chart.tsx,
  transactions-list.tsx, notes-panel.tsx
  reconciliation-badge.tsx
  theme-toggle.tsx
  refresh-button.tsx
  suggestion-card.tsx         full explainability layer (Commit B);
                              F6: CollapsedFeedbackRow when user_action != null
                              F2: SHIPPED — isSellSide = Boolean(groupMeta?.
                              booking_opportunity); group bars switch labels;
                              dossier section renders tax_consideration +
                              concentration_note for sell, portfolio_fit for buy.
  explain-popover.tsx         reusable info-icon popover (Commit B)
  page-intro.tsx              "How to read this page" collapsible (Commit B)
lib/
  api.ts                      hand-typed API client; SINGLE SOURCE OF TRUTH for
                              frontend types; ~600 lines.
                              F6+F10: UserAction, MonitoredStocksAuditEntry,
                              getRecentFeedbackAudit, getFeedbackAuditForIsin,
                              previous_status on submitFeedback response,
                              excluded_acted on SuggestionRun.
                              F2: SHIPPED — SuggestionDirection type, direction
                              param on getLatestSuggestionRun / listSuggestionRuns
                              / getSuggestionPerformance, direction on
                              SuggestionRun + SuggestionOutcome + SuggestionDossier,
                              BucketKey type, by_bucket breakdowns on
                              SuggestionPerformance windows.
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

All collections live in MongoDB Atlas M10. The DB name is set by env (`MONGODB_DB_NAME`). All collections accessed via `Collections.<name>()` from `app.db.client`. Indexes ensured at startup via `app/db/indexes.py`.

### Phase 1 collections

#### `instruments`
- Master NSE/BSE instrument list, refreshed daily from NSE's official `EQUITY_L.csv` (tech debt A13: backend README and `refresh_instruments.py` docstring still reference Zerodha Kite — historical, never used)
- Key fields: `exchange`, `symbol`, `isin`, `name`, `instrument_type`, `segment`, `lot_size`, `tick_size`, `source`, `last_seen_at`, `last_changed_at`, `in_nifty100`
- Count: ~2,368 total; 100 with `in_nifty100=True`
- Indexes: `(exchange, symbol)` unique, `isin`, `last_seen_at`, `last_changed_at`, `in_nifty100`
- Writer: `scripts/refresh_instruments.py` (delta-aware, `refresh_from_nse()`), `scripts/seed_nifty100.py`, manual upserts for BSE-only stocks

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
- F2 (Chat 4): `target_price` is now consumed by sell-side scoring (`target_price_proximity` signal in `booking_opportunity` group). `stop_loss` will be wired by user direction (see Q3 in Chat 5 open items / TD6 — deferred to a later chat for new feature work).

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
- Key fields: `isin`, `status` (Literal `"tracking"/"passed"/"rejected"/"watchlist"`), `symbol`, `exchange`, `name`, `sector`, `industry`, `added_by`, `added_reason`, `added_at`, `thesis`, `conviction`, `conviction_history`, `target_buy_price`, `alert_above`, `alert_below`, `alert_on`, `tags`, `user_notes`, `last_reviewed_at`, `last_user_interest_at`, `acted_at`, `passed_at`, `rejected_at`, `last_feedback_action`, `last_feedback_at`, `last_feedback_note`, `created_at`, `updated_at`
- Chat 5 A1 SHIPPED: model schema now matches writer reality. Old `Literal["tracking", "promoted_to_holding", "dropped"]` was removed (no code ever wrote those values); `"watchlist"` was added ahead of F13. Feedback fields (`acted_at`/`passed_at`/`rejected_at`/`last_feedback_*`) declared on the model. `symbol` downgraded to optional default `""` (feedback writer doesn't have it; rich-entry paths will populate when they ship). Collections wiped during the A1 deploy (Q1 resolved: data was throwaway test data).
- INVARIANT (Chat 5 A1): writes go through `routers/suggestions.submit_feedback`, which constructs a `MonitoredStockFeedbackPatch(...)` Pydantic model and `$set`-s `patch.model_dump(exclude_none=True)`. The patch model has `ConfigDict(extra="forbid")` so any future drift (new status value, new action value) fails LOUDLY with `pydantic.ValidationError` at write time. `exclude_none=True` is intentional and load-bearing — `acted_at`/`passed_at`/`rejected_at` are mutually exclusive per call, and we want prior-action timestamps preserved across status flips (verified end-to-end in A1 smoke: passed→rejected on TCS preserved `passed_at` and set `rejected_at`).
- INVARIANT: `$setOnInsert` seeds `added_by="user_explicit"`, `added_reason="feedback action"`, `_schema_version=1`, `created_at=now` so freshly-upserted docs satisfy the `MonitoredStock` schema and round-trip cleanly through `MonitoredStock(**doc)`.
- INVARIANT (F10): every write is preceded by a `monitored_stocks_audit_service.log_change(...)` insert. Audit row lands BEFORE the `update_one` apply, so even if the apply crashes the intent is recorded. Same write-before-apply pattern as `transactions_audit`.
- Consumer: `suggestion_engine.get_excluded_isins()` returns three buckets at run-build time:
  - `rejected` — `status="rejected"` AND `rejected_at >= now - 90d`
  - `passed` — `status="passed"` for this run only (resurfaces next Sunday)
  - `acted` — `status="tracking"` AND `acted_at >= now - 30d` (F5b 30-day soft-exclude; naturally suppressed thereafter by the held filter if the trade landed, or resurfaces if it didn't)
- Consumer: `explainability._build_user_action()` at serialization time stamps each enriched candidate with `user_action` (null | "acted" | "passed" | "rejected") + the corresponding timestamp. This is the second of the two F6 exclusion mechanisms — see Section 14.
- F2 (Chat 4): direction-agnostic. A user rejecting a SELL suggestion for INFY also suppresses the next BUY for INFY for 90 days, and vice versa. Acceptable for v1; add a `direction` column if it bites (TD1).
- Indexes: `isin` unique (PARTIAL — `partialFilterExpression={"status": "tracking"}`), `(status, rejected_at)`. The partial index still semantically works post-A1: the writer continues to flip status away from `"tracking"` on passed/rejected, and the index now matches the Literal honestly. A14 is closed by A1.

#### `monitored_stocks_audit` (F10 — shipped Chat 3)
- Append-only audit log for `monitored_stocks` writes; one doc per `POST /suggestions/{isin}/feedback`
- Key fields: `isin`, `action` (`"acted"|"passed"|"rejected"`), `previous_status` (string or null), `new_status`, `note`, `performed_at`, `_schema_version` (1)
- INVARIANT: append-only. Writer (`monitored_stocks_audit_service.log_change`) is invoked BEFORE the corresponding `monitored_stocks.update_one` apply in `submit_feedback`, so intent survives even if the apply step crashes. Mirrors `transactions_audit` exactly.
- Indexes: `(performed_at desc)`, `(isin, performed_at desc)`
- Writer: `app/services/monitored_stocks_audit_service.py`
- Consumer: `GET /suggestions/{isin}/audit` (per-ISIN history), `GET /suggestions/feedback/audit/recent?limit=N` (cross-ISIN feed)

#### `instruments_fundamentals`
- One doc per ISIN per fundamentals refresh (so we have history)
- Key fields: `isin`, `symbol`, `as_of` (date), `fetched_at` (datetime), `market_cap`, `pe_ratio`, `pb_ratio`, `dividend_yield`, `return_on_equity`, `return_on_assets`, `operating_margin`, `debt_to_equity`, `earnings_growth_yoy`, `revenue_growth_yoy`, `beta`, `fifty_two_week_high`, `fifty_two_week_low`, `sector` (yfinance), `industry`, `source`, `source_raw` (full yfinance dict for replay), `fields_present`, `fields_missing`
- Indexes: `isin_latest_unique` (unique, latest only via `(isin, fetched_at desc)`), `fetched_at`
- Writer: `scripts/refresh_fundamentals.py` → `fundamentals_service.refresh_one`. F14: default universe is now NIFTY 100 ∪ active holdings.
- Consumer: `suggestion_engine` (scoring), `explainability.py` (raw values for UI rendering — currently fetches raw inputs from this collection as a workaround for the A3 bug)

#### `earnings_calendar` (F14 — shipped Chat 4)
- Upcoming + historical earnings events per ISIN. Source = yfinance `Ticker.calendar`, refreshed weekly alongside fundamentals.
- Key fields: `isin`, `symbol`, `exchange`, `earnings_date` (tz-naive datetime), `source` ("yfinance"), `source_raw` (sanitized yfinance calendar dict), `fetched_at`, `created_at`
- INVARIANT (refresh semantics): `refresh_earnings_for(isin, symbol, exchange)` deletes ALL future events for the ISIN (>= today) then re-inserts the freshly-fetched list. Past events are immutable history.
- INVARIANT (BSON sanitization): `_sanitize_for_bson` in `fundamentals_service.py` walks dicts/lists and coerces date→datetime, tz-aware→naive, Timestamp/numpy scalars→native, unknown→`str()`. Applied to `source_raw` before insert.
- Indexes: `(isin, earnings_date)` unique, `(earnings_date asc)`, `(isin)`, `(fetched_at desc)`
- Writer: `fundamentals_service.refresh_earnings_for` (single ISIN), `refresh_earnings_universe` (bulk)
- Consumer: `get_next_earnings_for_isin` / `get_next_earnings_bulk`; `suggestion_engine` (buy + sell); `scoring_service.evaluate_earnings_proximity_gate` (skip trades within 5 days of an event)

#### `news_articles`
- Classified news per article; one doc per URL with `$addToSet`-merged `entities_isins`
- Key fields: `url` (unique), `title`, `published_at`, `fetched_at`, `source`, `body` (purged after classification), `body_purged_at`, `entities_isins` (list), `themes` (`Literal[earnings|regulatory|corporate_action|management_commentary|sector_macro|noise]`), `sentiment` (positive/neutral/negative/mixed), `sentiment_confidence`, `severity` (low/medium/high), `classifier_summary`, `classified` (bool)
- Indexes: `url` unique, `(entities_isins, classified, fetched_at)`, `(classified, fetched_at)`
- Writer: `news_fetcher.py` (fetch) then `news_classifier.py` (classify in two-phase Haiku batches: `BATCH_SIZE=25` main pass, `RETRY_PASS_BATCH_SIZE=3` for stragglers)
- Consumer: `news_signals.py`, `dossier_service.py`
- NOTE (A16): the cron-default universe for `fetch_news_for_universe.py` excludes held stocks unless `--include-held` is passed. Verify EC2 crontab passes `--include-held` for sell-side coverage.

#### `suggestion_runs`
- Append-only history of every weekly run
- Key fields: `_id`, `_schema_version`, `run_date`, `run_date_ist`, `run_type` (scheduled/manual), `direction` (`"buy"`|`"sell"`, default `"buy"`), `status` (success/partial/failure), `started_at`, `finished_at`, `error`, `universe_size`, `excluded_held`, `excluded_rejected`, `excluded_passed` (F6), `excluded_acted` (F5b), `excluded_stale_data`, `candidates_considered`, `candidates_post_gates`, `config`, `top_candidates`, `all_candidates`, `top_k`, `notes` (JSON string containing dossiers array)
- INVARIANT: append-only; never updated; re-running creates a new doc
- INVARIANT: `top_candidates[*].user_action` is NOT in the persisted doc. Added at API serialization time by `enrich_run` only.
- INVARIANT (F2 / Chat 4): pre-F2 runs persisted without a `direction` key still load cleanly. Pydantic default = `"buy"` via `model_validate`. The router serializer (`_serialize_run`) also defensively defaults missing `direction` to `"buy"` for the raw-dict path, and `/runs` adds it to the projection.
- Indexes: `(run_date desc)`, `(run_date_ist, run_type)`, `(status)`

#### `suggestion_outcomes`
- One doc per top-K candidate per run; tracks actual stock + benchmark over 30/60/90/180-day windows
- Key fields: `isin`, `symbol`, `suggestion_run_id`, `suggested_at`, `suggested_at_price`, `suggested_rank`, `suggested_composite_score`, `tracking_status` (open/acted/passed/rejected/expired), `direction` (`"buy"`|`"sell"`, default `"buy"`), `price_at_30d/60d/90d/180d`, `nifty_at_30d/60d/90d/180d` (return percentages vs benchmark, equal-weighted NIFTY 100), `excess_return_30d/60d/90d/180d`, `user_action_at`, `user_action_note`, `created_at`, `updated_at`
- INVARIANT (changed in Commit A.5): snapshot eligibility is `tracking_status != "expired"`, NOT `tracking_status == "open"`.
- INVARIANT: outcomes only auto-flip to `"expired"` if still labeled `"open"` at day 180. User-set labels are never overwritten.
- INVARIANT (F2 / Chat 4): `compute_system_performance(direction="sell")` sign-flips `excess_return` per outcome before aggregating.
- Indexes: `(isin, suggested_at desc)`, `(suggested_at desc)`, `(tracking_status)`, `(suggestion_run_id)`
- Writer: `outcome_tracker.create_outcomes_for_run` at run time (stamps direction), `snapshot_open_outcomes` daily (direction-agnostic)

#### `tavily_quota`
- One doc per UTC day; counters incremented atomically
- Key fields: `date` (YYYY-MM-DD string), `total_calls`, `total_credits`, `per_use_case.<name>.calls`, `per_use_case.<name>.credits`
- Indexes: `date` unique
- Writer: `tavily_client.py` `$inc` updates with upsert
- INVARIANT: `TAVILY_DAILY_CALL_LIMIT` (default 200) enforced; raises `TavilyQuotaExceeded` when hit

#### `digest_deliveries`
- Audit log of weekly digest emails + ntfy pushes
- Key fields: `run_id`, `run_date_ist`, `sent_at`, `top_count`, `subject`, `email_ok`, `email_id`, `email_error`, `ntfy_ok`, `ntfy_status`, `ntfy_error`
- F2 (Chat 4): for combined-digest sends (`--direction=both` cron path), the row attaches to the BUY run id so one row per delivery is preserved.
- Indexes: `(sent_at desc)`, `(run_id)`
- Writer: `digest_delivery.send_weekly_digest` or `digest_delivery.send_combined_digest`. Chat 5 A2 part 1: `_send_email` now delegates to `notify.email()`; the audit row shape is preserved.

#### `cron_heartbeats` (F4 — shipped Chat 2)
- One doc per cron run with start/finish/status/error/metadata
- Key fields: `cron_name`, `started_at`, `finished_at`, `status` (`"success"|"failure"|"skipped"`), `error`, `metadata` (dict, per-cron stats), `_schema_version`
- INVARIANT: append-only. Wrapper writes exactly one doc per run on exit.
- INVARIANT: heartbeat write is best-effort.
- INVARIANT (Chat 4): the context manager yields a `_Heartbeat` object that exposes `.meta` as an ATTRIBUTE. Set via `ctx.meta = {...}` or `ctx.meta[key] = value`. `ctx["meta"] = ...` raises TypeError.
- `"skipped"` counts as healthy in the daily check.
- Indexes: `(cron_name, started_at desc)`, `(started_at desc)`, TTL on `started_at` (60 days)
- Consumer: `GET /cron/heartbeats` router; `scripts/cron_health_check.py`
- The expected cron schedule lives in code as `CRON_REGISTRY` in `cron_heartbeat_service.py` — keep `CRON_REGISTRY` and `crontab -l` in sync.

### `digests` / `alerts_log` / `conversations` / `macro_signals`
Scaffolds; not actively written by current code. `conversations` will be used for chat features (F1, F3). Reserved; do not delete.

### Future collections (planned, not yet created)
- None pending in the current plan. F11 is a read-only reformatter; F13 watchlist reuses `monitored_stocks` with `status="watchlist"`.

## Section 8: API endpoints (exhaustive)

(unchanged from prior version — Chat 5 touched only the writer implementation of `/suggestions/{isin}/feedback`, not its API contract)

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
GET    /transactions/search?symbol&type&from_date&to_date&skip&limit  {results, total}
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
GET    /suggestions/runs?direction=buy|sell&limit=N&skip=N  {runs, total, limit, skip}
GET    /suggestions/runs/{run_id}                    SuggestionRun + enrichment
GET    /suggestions/performance?direction=buy|sell   SuggestionPerformance with by_bucket
POST   /suggestions/{isin}/feedback                  {isin, action, status, previous_status}
                                                     Body: {action: "acted"|"passed"|"rejected", note?: string}
                                                     Chat 5 A1: writer migrated to typed
                                                     MonitoredStockFeedbackPatch; response shape
                                                     unchanged.
GET    /suggestions/{isin}/audit?limit=N             MonitoredStocksAuditEntry[]   (F10)
GET    /suggestions/feedback/audit/recent?limit=N    MonitoredStocksAuditEntry[]   (F10)
GET    /cron/heartbeats?limit=N                      {heartbeats, health_summary}
```

`/cron/heartbeats` response shape:
- `heartbeats`: newest-first list (default 200, max 1000)
- `health_summary`: per-cron rows with `cron_name`, `description`, `schedule`, `expected_today`, `min_runs_per_day`, `last_run_at`, `last_status`, `last_error`, `today_total`, `today_success`, `today_failure`, `today_skipped`, `healthy`
- `healthy = true` iff (not expected today) OR (`today_success + today_skipped >= min_runs_per_day` AND `today_failure == 0`)

F10 feedback-audit endpoint shape:
- Each row: `{_id, isin, action, previous_status, new_status, note, performed_at, _schema_version}`
- `/suggestions/{isin}/audit` is backed by the `(isin, performed_at desc)` compound index
- `/suggestions/feedback/audit/recent` is backed by the `(performed_at desc)` index
- The static-path `/feedback/audit/recent` route is declared BEFORE the dynamic `/{isin}/audit` route

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

## Section 9: Cron registry on EC2

Run `crontab -l` to see current state. Every script below is heartbeat-instrumented via `cron_run()` and writes to `cron_heartbeats`. The daily `cron_health_check` at 21:00 IST consumes those heartbeats.

`CRON_REGISTRY` in `cron_heartbeat_service.py` is the in-code mirror of this schedule — keep both in sync.

```cron
# Phase 1 crons (heartbeat-instrumented Chat 2)
0 3 * * * cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/refresh_instruments.py >> /home/ubuntu/cron-instruments.log 2>&1
0 19 * * 1-5 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/refresh_prices.py >> /home/ubuntu/cron-prices.log 2>&1
*/15 9-15 * * 1-5 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/refresh_prices_intraday.py >> /home/ubuntu/cron-prices-intraday.log 2>&1
30 19 * * 1-5 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/take_reconciliation_snapshot.py >> /home/ubuntu/cron-reconciliation.log 2>&1

# Phase 2 crons (registered Chat 2 via F5a — all heartbeat-instrumented)
0 6 * * 0 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/refresh_fundamentals.py >> /home/ubuntu/cron-fundamentals.log 2>&1
30 6 * * 0 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/fetch_news_for_universe.py >> /home/ubuntu/cron-news.log 2>&1
0 7 * * 0 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/run_weekly_suggestions.py --direction=both --notify --run-type scheduled >> /home/ubuntu/cron-suggestions.log 2>&1
45 19 * * 1-5 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/track_suggestion_outcomes.py >> /home/ubuntu/cron-outcomes.log 2>&1

# F4 cron health monitoring (added Chat 2)
0 21 * * * cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/cron_health_check.py >> /home/ubuntu/cron-health.log 2>&1

# Maintenance
0 0 * * 0 find /home/ubuntu -maxdepth 1 -name "cron-*.log" -size +10M -exec sh -c 'tail -10000 "$1" > "$1.tmp" && mv "$1.tmp" "$1"' _ {} \;
```

PENDING ONE-TIME EC2 STEPS (Chat 5):
- Confirm the Sunday 07:00 IST line uses `--direction=both --notify --run-type scheduled` (verify against EC2 `crontab -l`).
- Confirm Sunday 06:30 IST `fetch_news_for_universe.py` line includes `--include-held` (A16).
- Stop + disable the self-hosted private ntfy service (TD8): `sudo systemctl stop ntfy && sudo systemctl disable ntfy`. Confirm no remaining consumers first: `grep -r "push_private" app/`.

`CRON_REGISTRY` (in code) entries:
- `instruments_refresh`, `prices_eod`, `prices_intraday`, `reconciliation_auto`, `fundamentals_refresh`, `news_fetch`, `weekly_suggestions`, `track_outcomes`, `cron_health_check`
- `weekly_suggestions_sell` — kept in registry for the alternative deployment topology (two separate runs); current prod path is `--direction=both` under the `weekly_suggestions` umbrella heartbeat.

KNOWN REGISTRY DRIFT (A6):
- `weekly_suggestions` CronSpec `schedule_human="Sunday 06:00 IST"` but actual cron is 07:00 IST. Cosmetic only.

No silent failures: every cron registration must include log file paths AND heartbeat instrumentation AND a `CronSpec` entry. All three.

## Section 10: Settings and environment variables

Configured in `app/config/settings.py` via pydantic-settings. All required unless marked default.

### Anthropic
- `ANTHROPIC_API_KEY` (required)
- `ANTHROPIC_MODEL_PRIMARY` (default `"claude-sonnet-4-5"`)
- `ANTHROPIC_MODEL_FAST` (default `"claude-haiku-4-5"`)

### MongoDB
- `MONGODB_URL` (required) — URL-encode special chars in the password
- `MONGODB_DB_NAME` (required)

### Tavily
- `TAVILY_API_KEY` (required)
- `TAVILY_DAILY_CALL_LIMIT` (default 200)
- `TAVILY_SEARCH_DEPTH` (default `"basic"`)
- `TAVILY_MAX_RESULTS_PER_QUERY` (default 5)

### Email (Resend)
- `RESEND_API_KEY` (required)
- `RESEND_FROM` (e.g., `"advisor@your-domain.com"`)
- `RESEND_TO` (default recipient for `notify.email()` — used when caller omits `to=`)
- `DIGEST_TO` (digest recipient; may equal `RESEND_TO`)

### ntfy
- `NTFY_URL`, `NTFY_USER`, `NTFY_PASS` — private self-hosted, pending decommission (TD8)
- `NTFY_PUBLIC_URL` (default `"https://ntfy.sh"`)
- `NTFY_PUBLIC_TOPIC_PRICE`, `NTFY_PUBLIC_TOPIC_NEWS`, `NTFY_PUBLIC_TOPIC_ERRORS`, `NTFY_PUBLIC_TOPIC_DIGESTS`
- `NTFY_PUBLIC_TOPIC_DIGESTS` (F2b — REQUIRED, no default)
- All `NTFY_PUBLIC_TOPIC_*` values must be IDENTICAL on EC2 and Mac
- `push_public(channel)` signature: `channel: Literal["price", "news", "errors", "digests"]`
- `push_private(topic)` signature: `topic: Literal["digests", "errors"]` — currently unused after F2b

## Section 11: Phase 1 INVARIANTS — never violate

These come straight from `docs/data_flow.md` (the file is stale on Phase 2; the Phase 1 section is still authoritative). They are hard rules

- Transactions are immutable except through the audited PATCH/DELETE flow. Every PATCH/DELETE writes a `transactions_audit` entry BEFORE applying the change. The `reason` field is required.
- `recompute_holding(isin)` is the only authoritative writer to `holdings`. Idempotent. Recomputes from `transactions` from scratch using FIFO. Never write directly to `holdings`.
- `validate_replay(isin, simulated_transactions)` rejects any timeline producing negative quantity. Both PATCH and DELETE on `/transactions/{id}` call this before applying.
- `holdings.deleted_at = None` filter is universal. Deleted holdings preserve replay correctness.
- Cost basis is IT-Act-correct, not broker-nominal. The broker-nominal view is recoverable as `holdings.invested_amount + total_cost_basis_adjustment`.
- `prices_intraday` writes are append-only within a day.
- ICICI portfolio display shows TMPV ~₹813 and TMCV ~₹253 — cosmetically wrong vs our tax-correct numbers; does not affect actual money or tax filing.

## Section 12: Phase 2 INVARIANTS

- `suggestion_runs` are append-only.
- `tavily_quota` is one doc per UTC day with `$inc` counters. Hard ceiling enforced.
- Confidence score is deterministic, NOT LLM-generated.
- The dossier prompt requires narrative-only output. Forbids "buy"/"sell" imperatives and inventing facts.
- `gate_meta`, `group_meta`, `signal_meta`, `confidence_meta`, `feedback_meta`, `page_intro`, `user_action` are PRESENTATION metadata, added by `_serialize_run` via `enrich_run`. Never in the persistent model.
- Snapshot eligibility for `snapshot_open_outcomes` is `tracking_status != "expired"` (Commit A.5).
- Auto-expiry only flips `"open"` outcomes at day 180. User-set labels never overwritten (A.5).
- Feedback re-labels the MOST RECENT non-expired outcome for the ISIN (A.5.1).
- `suggestion_engine.get_excluded_isins()` returns three buckets: `rejected` (90d), `passed` (this run only), `acted` (30d soft-exclude, F5b). 90-day and 30-day constants are intentionally NOT env-configurable.
- F10 write-before-apply: every `POST /suggestions/{isin}/feedback` writes `monitored_stocks_audit` BEFORE the corresponding `monitored_stocks.update_one` apply.
- **Chat 5 A1**: `monitored_stocks` writes go through `MonitoredStockFeedbackPatch(...).model_dump(exclude_none=True)`. Constructing the patch model catches Literal drift (status, action) at write time with `pydantic.ValidationError`. `exclude_none=True` preserves prior-action `*_at` timestamps across status flips (verified end-to-end). `$setOnInsert` seeds `added_by="user_explicit"`, `added_reason="feedback action"`, `_schema_version=1`, `created_at=now` for new docs.
- The `notes` field on a `SuggestionRun` is a JSON string containing `{dossiers: [...]}`. The router parses it and exposes `dossiers` at the top level, then strips `notes` and `all_candidates` from the response (the persisted doc still has them).

### F2 / F14 invariants (Chat 4)
- `SuggestionDirection` literal = `"buy" | "sell"`. Both `SuggestionRun.direction` and `SuggestionOutcome.direction` default to `"buy"`.
- The router serializer (`_serialize_run`) and the `/runs` projection BOTH defensively default missing `direction` to `"buy"` on the raw-dict path.
- `compute_system_performance(direction="sell")` SIGN-FLIPS `excess_return` at aggregation time.
- `snapshot_open_outcomes` is DIRECTION-AGNOSTIC.
- `earnings_calendar` refresh: `refresh_earnings_for(isin, ...)` deletes all events for the ISIN with `earnings_date >= today` then re-inserts. Past events never touched.
- `_sanitize_for_bson` is applied to `Ticker.calendar` BEFORE inserting.
- F14 earnings-proximity gate is SHARED between buy and sell via `evaluate_earnings_proximity_gate`. Skips trades within 5 days of an event. `next_earnings is None` → `skipped=True, passed=True`.
- Sell-side scoring uses different groups (`booking_opportunity`/`valuation_stretch`/`risk`/`tax_concentration`) and different gates (`in_profit`/`min_position_age`/`earnings_proximity`).
- `CandidateScore` has FIXED buy-side group fields. Sell-side rows leave them at 0.0; sell-side group scores flow through `group_meta`. Display layer branches on direction.
- `monitored_stocks` is currently DIRECTION-AGNOSTIC.
- F2 combined-digest: `--direction=both` emits ONE email + ONE ntfy push via `send_combined_digest`. Delivery row attaches to the buy run id.

### Chat 5 A2 (in progress)
- `notify.email()` returns `{ok: bool, id: str|None, error: str|None}` and SWALLOWS Resend exceptions. Callers must check `result["ok"]` instead of relying on exceptions. The wrapper accepts an optional `text=` param for multipart/alternative.
- All Resend traffic in the backend flows through `notify.email()`. `digest_delivery._send_email` delegates here (A2 part 1 shipped). `reconciliation.notify_drift` has two call sites pending the same delegation pattern (A2 part 2).

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
- Commit A (backend explainability)
- Commit A.5 (feedback correctness)
- Commit A.5.1 (re-label correctness)
- Commit B (frontend explainability)

Chat 2 (F4 + F5a) — Cron observability shipped 2026-05-16:
- F4: `cron_heartbeats` collection, `cron_run()` context manager, `CRON_REGISTRY`, `GET /cron/heartbeats`, `scripts/cron_health_check.py` at 21:00 IST, `push_public("errors", ...)`, `NTFY_PUBLIC_TOPIC_ERRORS`.
- F5a: all four Phase 2 crons registered on EC2 with log files and heartbeat instrumentation.

Chat 3 (F6 + F5b + F10) — Stateful feedback shipped 2026-05-17:
- F6: replaces session-scoped vanish-on-click with persistent backend exclusion via two mechanisms (`get_excluded_isins` at run-build + `_build_user_action` at serialization).
- F5b: 30-day acted soft-exclude via `ACTED_EXCLUDE_WINDOW_DAYS`.
- F10: `monitored_stocks_audit` collection + `monitored_stocks_audit_service.py` + write-before-apply in `submit_feedback` + two new audit endpoints.

Chat 4 (F2b + F14 + F2 backend + F2 frontend) — Sell-side fully shipped 2026-05-17/18/20:
- F2b (ntfy public migration for digests) + `NTFY_PUBLIC_TOPIC_DIGESTS`
- F14 (earnings calendar foundation) + earnings_calendar collection + shared earnings-proximity gate
- F2 (sell-side backend): SuggestionDirection, direction-aware scoring, sell pipeline, sell dossiers, direction-aware outcomes/performance
- F2 (router + CLI + cron registry + combined digest): all four `/suggestions/*` read endpoints accept `?direction=`, `run_weekly_suggestions.py --direction=buy|sell|both`, `weekly_suggestions_sell` CronSpec, `send_combined_digest`
- F2 frontend (chunk 7): Buy/Sell tabs, direction-aware queries + copy + toast, `isSellSide` branch in suggestion-card
- F2b cosmetic (2026-05-20 / cea8eee): direction-aware `_format_score_breakdown`

Chat 5 (Audit + cleanup) — partial, in progress (2026-05-23):
- **A1 SHIPPED** — `MonitoredStock` model rewrite + writer migration to typed `MonitoredStockFeedbackPatch`. Old Literal `["tracking","promoted_to_holding","dropped"]` replaced with `["tracking","passed","rejected","watchlist"]` to match writer reality + add F13 forward-compatibility. Feedback fields declared on the model. `symbol` downgraded to optional. Writer uses `patch.model_dump(exclude_none=True)` so prior-action `*_at` timestamps survive status flips; `$setOnInsert` seeds identity fields so new docs satisfy the schema. Collections wiped during deploy (data was throwaway). 11/11 EC2 smoke checks passed, including end-to-end TCS passed→rejected (passed_at preserved) and negative test (invalid status raises ValidationError). Resolves A14 cleanly because the writer continues flipping status away from `"tracking"` and the index now matches the Literal honestly.
- **A8 SHIPPED** — deleted dead `app/models/news_article.py`. Zero importers verified across `app/` and `scripts/`. App boots cleanly.
- **A2 part 1 SHIPPED** — `notify.email()` extended with optional `text=` param for multipart; returns `{ok, id, error}` instead of raw resend dict; swallows exceptions. `digest_delivery._send_email` delegates to `notify.email()`; no more inline `import resend`. Verified end-to-end on EC2: real digest email arrived in inbox, `email_ok=True`, `email_id` populated, `ntfy_ok=True`. The "missing summary/verdict" in the smoke email was the documented `--skip-dossiers` flag behavior (Section 14 Chat 4 convention), not a regression.

### Open items in Chat 5 (priority order)

| # | Item | Status |
|---|---|---|
| A2 part 2 | `reconciliation.notify_drift` has two `email()` call sites (`email_critical`, `email_drift`) wrapping `email()` in a bare try with unconditional `sent.append(...)`. Post-A2 part 1, exceptions no longer fire, so `sent.append()` runs even when Resend returned `{ok: False}` — `notify_drift`'s return value lies about what got sent. Fix: check `result.get("ok")` before appending at both sites. | PENDING |
| A3 + A4 | `SignalScore.raw_value` writer fix (Chat 5 Q2 resolved: option (b), fix writer to store raw input, don't rename field). Bundled with A4 (persist news signal raw values). | PENDING |
| A5 | Delete stale `DEFAULT_CONFIG.gates` comment in `scoring_service.py` | PENDING |
| A6 | Fix `weekly_suggestions` `schedule_human` "06:00" → "07:00" | PENDING |
| A7 | Remove unused `SATURDAY = {5}` constant | PENDING |
| A13 | `refresh_instruments.py` docstring/comments "Zerodha Kite" → NSE EQUITY_L.csv | PENDING |
| A17 | Delete stale pre-chunk-6 comment in `_run_sell_pipeline` | PENDING |
| A18 | `enrich_run` `PAGE_INTRO_SELL` literal + branch for sell runs | PENDING |
| A19 | Three `Query(..., regex=...)` → `Query(..., pattern=...)` in `app/routers/suggestions.py` (lines 103, 138, 206). Pre-existing `FastAPIDeprecationWarning`s discovered during A8 verification. Cosmetic. | PENDING |
| A16 | Manual EC2 verify: `fetch_news_for_universe.py` cron line passes `--include-held` | PENDING |
| TD8 | Manual EC2 step: stop + disable self-hosted private ntfy (`sudo systemctl stop ntfy && sudo systemctl disable ntfy`); confirm no `push_private` consumers first | PENDING |

After all code fixes:
- `docs/data_flow.md` — full rewrite covering Phase 2 (currently 2026-05-09, Phase-1-only)
- Backend `README.md` rewrite
- Frontend `README.md` rewrite
- Final PROJECT_STATE refresh at chat close

Open questions RESOLVED in Chat 5:
- Q1 (A1 writer migration): WIPE existing throwaway data; migrate writer to typed `MonitoredStockFeedbackPatch` (load-bearing schema). DONE.
- Q2 (A3 raw_value shape): option (b) — fix writer to store raw input; do not rename field. Model already has both `raw_value` and `normalized_score` fields; the bug is purely a writer mistake.
- Q3 (`holdings.stop_loss`): WIRE it (intraday-cron alert when latest price crosses threshold). Deferred to a dedicated later chat as new feature work, NOT included in Chat 5 cleanup scope. Chat 5 stays cleanup-only.

#### Chat 6 — Chat features (F1 + F3)
F1 — Ad-hoc chat about suggestions; F3 — Ad-hoc chat about a specific holding. Share `conversations` collection scaffolding.

#### Chat 7 — Portfolio intelligence (F12 + F15)
F12 — `/portfolio/risk-summary`; F15 — tag-based portfolio views.

#### Chat 8 — Watchlist (F13)
`build_universe` becomes: NIFTY 100 ∪ watchlist ∪ held − excluded. `refresh_fundamentals.py` and `fetch_news_for_universe.py` must be extended to include watchlist ISINs.

#### Chat 9 — Pre-launch cleanup (F11 + realized P&L hide + stop_loss alerts)
F11 capital gains pack + realized P&L UI hide + stop_loss alert wiring (Chat 5 Q3 follow-through).

#### Chat 10 — GO LIVE (F7 one-time real data import)
Wipe + re-import via `refresh_from_icici.py` wrapper. Default behavior wipe-and-replace (only `transactions`, `transactions_staging`, `holdings`). Other Phase 2 collections preserved.

### Final chat split plan

| # | Chat | Scope | Status |
|---|---|---|---|
| 2 | Cron observability | F4 + F5a | SHIPPED 2026-05-16 |
| 3 | Stateful suggestions | F6 + F5b + F10 | SHIPPED 2026-05-17 |
| 4 | Sell-side suggestions | F2 + F2b + F14 + F2 frontend + F2b cosmetic | SHIPPED 2026-05-17/18/20 |
| 5 | Audit + cleanup | A1 (DONE), A8 (DONE), A2 part 1 (DONE); A2 part 2, A3+A4, A5-A19, TD8, data_flow.md, READMEs, PROJECT_STATE | IN PROGRESS 2026-05-20→ |
| 6 | Chat features | F1 + F3 | open |
| 7 | Portfolio intelligence | F12 + F15 | open |
| 8 | Watchlist | F13 | open |
| 9 | Pre-launch cleanup | F11 + realized P&L hide + stop_loss alerts | open |
| 10 | GO LIVE | F7 one-time real data import | open |

## Section 14: Conventions the assistant has repeatedly drifted on

The assistant has confused these multiple times. Memorize them.

- Port 8001 (Mac local), port 8000 (EC2). Always specify which.
- SSH-first for tests: every test block in chat MUST begin with `ssh ubuntu@100.112.20.41` and run curls against `localhost:8000`.
- Commit-block-after-code: every code/file delivery in chat MUST be followed by a paste-ready `git add .` + `git commit -m "..."` block in the project's commit-message style.
- Project_State.md is ALWAYS delivered as a complete full-file replacement, never as a patch, find-and-replace, or "rest unchanged".
- F6 two-mechanism feedback exclusion: `get_excluded_isins` at run-build time AND `_build_user_action` at serialization time. Both required.
- The 90-day rejected cooldown and 30-day acted soft-exclude constants are intentionally NOT env-configurable.
- F10 write-before-apply: `monitored_stocks_audit_service.log_change(...)` BEFORE `monitored_stocks.update_one(...)`.
- Secrets path on EC2 is `/etc/portfolio-advisor/secrets.env`.
- `lib/api.ts` is hand-typed; `lib/api-types.ts` is gitignored.
- Mutations in frontend use `refetchQueries` (synchronous).
- `cn` helper at `@/lib/utils`. Format helpers at `@/lib/format`.
- Collections accessor: `from app.db.client import Collections`.
- Decimal128 vs Decimal: helpers in `app/models/_common.py`.
- Datetimes: UTC-naive in Mongo. IST in UI. `utcnow()` from `app/models/_common.py`.
- Heredoc for multi-line Python: use `<<'EOF'` form.
- Original `SuggestionCard` takes parent-owned mutation. Do not redesign.
- `/suggestions` page uses shadcn Tabs.
- Original `SuggestionCard` has inline helpers `Section`, `DossierSection`, `GroupBar`. Keep or evolve, don't rename.
- Tailwind v4 + shadcn `.dark` class pickup is automatic.
- Every cron script: `cron_run()` wrapper AND `CronSpec` entry AND crontab line with log redirection.
- Direction-aware display layer: branch on direction at the display layer, not by forking the model. (`_format_score_breakdown`, `isSellSide`.)

### Chat 4 additions
- **DO NOT trust Glean snippets or memory for dataclass / Pydantic model field names.** BEFORE writing any patch that constructs `Foo(field=...)`, run `grep -B 2 -A 20 "class Foo" <file_path>` on the actual file on disk.
- **`cron_run()` yields a `_Heartbeat` object that exposes `.meta` as an ATTRIBUTE, not `__setitem__`.** Use `ctx.meta = {...}` or `ctx.meta[key] = value`. `ctx["meta"] = ...` raises TypeError.
- **The `/cron/heartbeats` endpoint returns `{heartbeats, health_summary}`**, not `{registry, recent}` or `{jobs}`.
- **`Collections.instruments_fundamentals()` is the accessor name** — NOT `Collections.fundamentals_snapshots()`.
- **`run_suggestions()` is SLOW by default** — generates Claude dossiers (~2-4 min). Use `--skip-dossiers` only for smoke tests. Production cron MUST NOT use `--skip-dossiers` — emails would have no summaries/verdicts (Chat 5 confirmed this is the documented behavior, not a regression).

### Chat 5 additions
- **ASK FOR THE CURRENT BACKEND (and frontend if relevant) SHA BEFORE PROPOSING ANY CODE CHANGE.** Then re-read the file at that SHA via Glean. Write find-and-replace blocks against the verbatim file text, NOT against snippet memory or earlier-read state. Multiple A2-part-2 proposals shipped with find-blocks that didn't match the on-disk file — the user had to halt three times. Standing rule: every code-change response begins by asking for the SHA if you don't already have a current one for this turn. NO EXCEPTIONS, even for "small" patches.
- **When a wrapper function's return shape or exception behavior changes (e.g., A2 changing `notify.email()` from raw dict + raises to `{ok,id,error}` + swallows), grep for ALL callers BEFORE shipping the change.** Then either (a) update each caller in the same commit, (b) add a compat shim, or (c) keep the old shape. The Chat 5 A2 part 1 commit shipped the wrapper change without updating `reconciliation.notify_drift`, which introduced a real bug (unconditional `sent.append` on Resend failures). This is the "wrapper-return-shape" trap.
- **`notify.email()` now returns `{ok: bool, id: str|None, error: str|None}`** and swallows Resend exceptions. Callers must check `result["ok"]` instead of `try/except`. Optional `text=` param enables multipart/alternative.

## Section 15: Anti-patterns the assistant has fallen into

- Full-file rewrites instead of additive patches. EXCEPTION: PROJECT_STATE.md is always full-file.
- Inventing parallel patterns.
- Trusting memory for function names / response shapes / paths. RE-READ AT HEAD before patching.
- Truncating code with "rest unchanged".
- Asking "is this OK?" without applying the edit.
- Micro-commits when meaningful units are expected.
- Assuming GitHub content is current. Always check commit SHA.
- Producing files significantly larger than originals.
- Inventing fields in API responses.
- Forgetting `enrich_run` from new `/suggestions/...` endpoints.
- Forgetting `holdings.deleted_at = None` is universal.
- Generating cron entries without log file paths or heartbeat monitoring.
- Designing UI/UX features that aren't requested.
- Shipping a code change without the paste-ready commit block.
- Shipping a test block without `ssh ubuntu@100.112.20.41` first line.
- Using `artifact_edit` on PROJECT_STATE.md instead of full-file artifact.
- Confusing the two F6 mechanisms.

### Chat 4 additions
- Guessing dataclass / model field names from Glean snippets without grep'ing the file first.
- Writing multi-chunk plans that span >3 chunks without re-reading every touched file at HEAD before each chunk.
- Writing the same test block with three different wrong API response shapes.

### Chat 5 additions
- **Trusting PROJECT_STATE.md as the source of truth for "what's open" without verifying against code.** Chat 5's first action was to re-read every file at the pinned SHAs. Five PROJECT_STATE-as-open items were actually shipped. PROJECT_STATE is updated end-of-chat; truncated chats produce drift. RULE: at start of every chat, after reading PROJECT_STATE, do a code audit of every "open" item against on-disk code at HEAD.
- **Writing find-and-replace blocks from snippet memory or stale file reads.** The most damaging mistake in Chat 5. The pattern: "I read the file (via Glean snippets, which are partial), then later wrote find-blocks against my mental model of what was in those snippets, not against the verbatim file text on disk." Snippets are CONTEXTUAL, not VERBATIM. The user halted three times in A2 because of this. THE FIX IS the Section 14 rule: ask for the SHA, re-read the file in full at that SHA, write find-blocks ONLY against bytes you can see in the current Glean output.
- **Changing a wrapper function's return shape or exception behavior without checking ALL callers first.** The A2 part 1 commit changed `notify.email()` semantics and broke `reconciliation.notify_drift`'s error-detection logic. The grep should have happened BEFORE the patch was proposed, not after the deploy.
- **Inferring return shape from documentation comments instead of from the actual function body.** The first A2 proposal assumed `notify.email()` returned `(bool, str)` because that's what an "obvious" wrapper signature looked like. The actual signature returned a raw resend dict. Always read the function body, not what you think it should be.

## Section 16: "I am losing context" — escalation protocol

When the assistant notices ANY trigger, say verbatim:

```
I AM LOSING CONTEXT
```

### Triggers (any one is sufficient)
- Cannot recall a specific file structure that was discussed earlier in the chat
- Conflating Phase 1 facts with Phase 2 facts
- Forgetting which Commit (A, A.5, A.5.1, B) shipped which behavior
- Forgetting which Chat (2, 3, 4, 5) shipped which feature
- Producing a file >1.5x the original line count without explicit reason
- Starting to use generic patterns instead of project conventions
- Forgetting the port difference between Mac and EC2
- Forgetting the SSH-first or commit-block-after-code convention
- Forgetting the secrets path
- Forgetting the chat split plan from Section 13
- The user has to correct the same drift twice in the same chat
- The assistant has called Glean reader or code_search >15 times without converging
- The "Truncation Notice" appears in the assistant's context
- About to produce a third large code artifact and unsure whether prior decisions still apply
- Chat 4 trigger: shipped two+ patches with WRONG field names
- Chat 4 trigger: shipped a test block with WRONG API response shape
- Chat 5 trigger: claimed "open" item is open without re-reading on-disk code
- **Chat 5 trigger: proposed a find-and-replace block whose `original_text` doesn't exist verbatim in the actual file at the current SHA.** This is what happened in A2 part 2. If the user says "those lines aren't in the code", say I AM LOSING CONTEXT immediately and switch chats — the failure mode tends to recur within the same chat.
- **Chat 5 trigger: changed a wrapper function's return shape or exception behavior without grep'ing for ALL callers first.** If you realize you've done this mid-chat, say I AM LOSING CONTEXT.

### What "switching chats" means
The user copies the Section 0 bootstrap into a fresh chat. The new chat reads PROJECT_STATE, both repos at HEAD, `data_flow.md`, READMEs. User states scope. Assistant summarizes. Then coding.

The new chat updates PROJECT_STATE at the end of its work as the last commit.

### What NOT to do
- Don't silently degrade.
- Don't "wing it" through context loss.
- Don't produce artifacts when uncertain about conventions.

## Section 17: "Am I hallucinating?" diagnostic questions

Without re-reading, the assistant should be able to answer all of these.

- "What's the backend port on Mac local?" → 8001
- "What's the backend port on EC2?" → 8000
- "How does the assistant SSH into EC2?" → `ssh ubuntu@100.112.20.41`
- "Where do secrets live on EC2?" → `/etc/portfolio-advisor/secrets.env`
- "Where do secrets live on Mac?" → `<repo>/.env`
- "What does `recompute_holding(isin)` do?" → only authoritative writer to `holdings`; idempotent; FIFO from scratch.
- "What's the gating filter on `snapshot_open_outcomes`?" → `tracking_status != "expired"`
- "Where does the dossier `plain_english_summary` field originate?" → `dossier_service.py` `_SYSTEM_PROMPT`, Sonnet, max 500 chars.
- "What is the universe filter in `build_universe`?" → NIFTY 100 ∪ watchlist (after F13) − held − excluded buckets from `get_excluded_isins`.
- "What are the two F6 mechanisms and why both?" → `get_excluded_isins` at run-build (saves Tavily+Sonnet) AND `_build_user_action` at serialization (stale-cache case). Both required.
- "What's the acted soft-exclude window? Env-configurable?" → 30 days. Not env-configurable.
- "What's the F10 write-before-apply rule?" → `log_change(...)` BEFORE `update_one(...)` in `submit_feedback`.
- "What's the Q/V/M/N weight breakdown?" → 30/25/25/20, version `"1.0.0-unit2"`.
- "Is `lib/api-types.ts` checked in?" → No.
- "refetchQueries or invalidateQueries?" → refetchQueries.
- "Sell endpoint response shape?" → full Holding (partial sell) OR `{message, realized_total}` (full exit).
- "Dividend tracking?" → No.
- "When does F7 run?" → Last (Chat 10).
- "How does a cron register?" → `cron_run()` wrapper + `CronSpec` entry + crontab line. All three.
- "Where do F4 cron failure alerts go?" → `push_public("errors", ...)` on public ntfy.sh, topic `NTFY_PUBLIC_TOPIC_ERRORS`.
- "Heartbeat schema?" → `{cron_name, started_at, finished_at, status, error, metadata, _schema_version: 1}`. TTL 60 days.
- "Healthy/unhealthy rule?" → Healthy iff (not expected today) OR (`success+skipped >= min` AND `failure == 0`).
- "How is PROJECT_STATE.md delivered?" → Always full-file canvas artifact.
- "What must accompany every code/file delivery?" → A paste-ready `git add .` + commit block.
- "How do test blocks start?" → `ssh ubuntu@100.112.20.41`, then curls against `localhost:8000`.

### Chat 4 additions
- "Fields on `CronSpec`?" → `cron_name`, `description`, `schedule_human`, `expected_weekdays` (IST weekday set), `min_runs_per_day` (default 1). NOT `name`, `job_name`, `schedule_cron`, `crontab`, `max_age_hours`.
- "How do you set metadata on `_Heartbeat`?" → `ctx.meta = {...}` or `ctx.meta[key] = value`. ATTRIBUTE, not `__setitem__`.
- "Response shape of `/cron/heartbeats`?" → `{heartbeats: [...], health_summary: [...]}`.
- "Collection name for fundamentals snapshots?" → `instruments_fundamentals`. Accessor `Collections.instruments_fundamentals()`.
- "Does `run_suggestions()` default to skipping dossiers?" → No. Dossiers ON by default (~2-4 min). `--skip-dossiers` only for smoke tests.
- "F2b ntfy topic for digests?" → `NTFY_PUBLIC_TOPIC_DIGESTS`, required.
- "F14 earnings-proximity gate threshold?" → 5 days. Shared between buy and sell.
- "Sell-side gate set?" → `in_profit`, `min_position_age`, `earnings_proximity`. NOT `high_severity_negative_news` (that's a signal).
- "How does `compute_system_performance(direction='sell')` handle excess_return?" → SIGN-FLIPS at aggregation time.

### Chat 5 additions
- "Is F2 frontend (Buy/Sell tabs + sell-side dossier rendering) shipped?" → Yes, verified at frontend SHA `e34e126`.
- "Is the Q/V/M/N=0 sell-digest cosmetic bug fixed?" → Yes, fixed 2026-05-20 commit `cea8eee`.
- "Is `target_price` consumed anywhere?" → Yes, F2 sell-side as `target_price_proximity` signal. `stop_loss` is open: Chat 5 Q3 resolved as "wire it, but as new feature work in Chat 9 — not in Chat 5 cleanup".
- "Has `digest_delivery._send_email` been reconciled with `notify.email()`?" → Yes (Chat 5 A2 part 1).
- "What does `notify.email()` return?" → `{ok: bool, id: str|None, error: str|None}`. Swallows Resend exceptions. Accepts optional `text=` for multipart.
- "What's the rule before proposing ANY code change?" → Ask for the current backend (and frontend if relevant) SHA. Re-read the file at that SHA. Write find-blocks against verbatim text. No exceptions.
- "What did A1 ship?" → `MonitoredStock` Literal aligned with writer (`tracking|passed|rejected|watchlist`), feedback fields declared, `MonitoredStockFeedbackPatch` typed wrapper, writer migrated to `patch.model_dump(exclude_none=True)`. Verified end-to-end on EC2 with 11/11 checks passing including passed→rejected timestamp preservation and negative ValidationError test.
- "What did A2 part 1 ship?" → `notify.email(subject, html, to=None, text=None)` returns `{ok, id, error}`, swallows exceptions. `digest_delivery._send_email` delegates. `reconciliation.notify_drift` STILL PENDING — has two call sites with bare try around `email()` and unconditional `sent.append`, now silently broken because exceptions never fire.
- "On-disk filename for this doc?" → `Project_State.md` (title case). GitHub paths are case-sensitive.

## Section 18: Tech debt registry

| ID | Item | Status | Chat target |
|---|---|---|---|
| A1 | `MonitoredStock` schema vs writer drift | SHIPPED Chat 5 (2026-05-23) | — |
| A2 | `digest_delivery._send_email` inline resend reconciliation | SHIPPED part 1 Chat 5 (2026-05-23). PART 2 PENDING — `reconciliation.notify_drift` two call sites need `result["ok"]` check (silently broken after part 1 changed exception behavior) | Chat 5 |
| A3 | `SignalScore.raw_value` writer stores normalized score instead of raw input | OPEN — Q2 resolved as option (b), fix writer | Chat 5 |
| A4 | News signal raw values not persisted post-run | OPEN — bundled with A3 | Chat 5 |
| A5 | Stale `DEFAULT_CONFIG.gates` comment | OPEN | Chat 5 |
| A6 | `weekly_suggestions` `schedule_human` says 06:00, actual 07:00 | OPEN | Chat 5 |
| A7 | `SATURDAY = {5}` weekday-set unused | OPEN | Chat 5 |
| A8 | Dead `app/models/news_article.py` | SHIPPED Chat 5 (2026-05-23) | — |
| A13 | `refresh_instruments.py` docstring "Zerodha Kite" → NSE EQUITY_L.csv | OPEN | Chat 5 |
| A14 | `monitored_stocks` partial unique index load-bearing on writer drift | CLOSED by A1 (writer now flips status away from `"tracking"` AND the Literal matches honestly) | — |
| A16 | `fetch_news_for_universe.py` cron line `--include-held` verification | OPEN | Chat 5 (manual EC2 step) |
| A17 | Stale pre-chunk-6 comment in `_run_sell_pipeline` | OPEN | Chat 5 |
| A18 | `enrich_run` page_intro buy-centric for sell runs | OPEN | Chat 5 (PAGE_INTRO_SELL + branch) |
| A19 | Three `Query(..., regex=...)` → `pattern=` in `routers/suggestions.py` (FastAPIDeprecationWarning) | OPEN — discovered during A8 verification | Chat 5 |
| TD1 | `monitored_stocks` direction-agnostic; rejection on SELL affects BUY suggestions and vice versa | DEFERRED | Decide post-launch |
| TD2 | `docs/data_flow.md` stale (Phase 1 only, 2026-05-09) | OPEN | Chat 5 (after bug fixes) |
| TD3 | `dossier_service.valuation_verdict` single-string split | DEFERRED | Future UI work |
| TD4 | Backend `README.md` stale | OPEN | Chat 5 (after bug fixes) |
| TD5 | Frontend `README.md` missing `/suggestions` route + Suggestions header button | OPEN | Chat 5 (after bug fixes) |
| TD6 | `holdings.stop_loss` orphan | OPEN — Chat 5 Q3 resolved as "wire it"; deferred to Chat 9 as new feature work | Chat 9 |
| TD7 | `CandidateScore` fixed buy-side group fields; sell-side leaves them 0.0 | DEFERRED | Post-launch |
| TD8 | EC2 self-hosted private ntfy service decommission | OPEN | Chat 5 (manual EC2 step) |

### Fixed in earlier chats (kept for posterity)
- **DIGEST SELL-SIDE Q/V/M/N BUG** — fixed 2026-05-20 in `cea8eee` via direction-aware `_format_score_breakdown`.
- **`track_suggestion_outcomes.py` docstring "Daily 18:30 IST"** — fixed; now generic.
- **`top_k` default in CLI docstring "--top-k 5"** — fixed via F2 chunk 6 rewrite of `run_weekly_suggestions.py`.
- **`holdings.target_price` unused** — half-fixed; now consumed by F2 sell-side `target_price_proximity` signal. `stop_loss` is TD6.
- **`MonitoredStock` schema vs writer drift** — fixed Chat 5 A1 (2026-05-23) via Literal alignment + typed `MonitoredStockFeedbackPatch`. Resolves A14 cleanly.
- **Dead `news_article.py`** — deleted Chat 5 A8 (2026-05-23).
- **`digest_delivery._send_email` inline Resend** — fixed part 1 Chat 5 A2 (2026-05-23); delegates to `notify.email()`. Part 2 still pending for `reconciliation.notify_drift`.

## Section 19: How to update this document

This file is updated at the end of every chat as the LAST commit. ALWAYS a complete full-file canvas artifact, never a patch.

What to update each chat:
- Section 13 — move shipped items; advance chat split plan
- Section 9 — update cron registry if entries added/changed
- Section 14 — add new conventions earned
- Section 15 — add new anti-patterns
- Section 16 — add new triggers
- Section 17 — add new diagnostic Q&A
- Section 18 — add/remove/reclassify tech debt
- Section 12 — new Phase 2 invariants
- Section 11 — new Phase 1 invariants (rare)
- Section 7 — collection schema changes
- Section 8 — endpoint changes
- Section 5/6 — file additions/deletions
- Section 4 — pin new last-verified SHAs

Commit message convention:
```
docs: update PROJECT_STATE.md after <chat scope>

- <bullet list of sections changed>
```

If the chat ended due to context loss, the LAST thing the assistant does before stopping is propose the PROJECT_STATE update. The user applies it manually.

Chat 5 added rule: when starting a new chat, after reading PROJECT_STATE, do a code audit of every "open" item against the actual on-disk code at HEAD before estimating work.

## Section 20: Trade-off rationale (decisions that might look weird)

- yfinance over Tijori/Screener Pro: free, works, `FundamentalsProvider` protocol supports swap.
- Confidence numeric 0-100 with deterministic deductions: bands hide info.
- Suggestions Sunday 07:00 IST (07:30 sell-only standalone): market closed, morning coffee, fundamentals+news refresh first.
- Top-K = 10.
- 90-day rejected cooldown: not env-configurable; one place in `suggestion_engine.py`.
- Zero cooldown for passed: market conditions change.
- 30-day acted soft-exclude: held filter catches the trade if it landed.
- Outcome snapshot ignores `tracking_status` for data collection (A.5).
- Session-scoped vanish replaced by persistent backend state (Chat 3 F6+F5b+F10).
- `digest_delivery.py` parallel Resend path: open as A2 (part 1 done Chat 5, part 2 pending).
- Schema drift on `monitored_stocks.status`: SHIPPED Chat 5 A1.
- `enrich_run` mutates dict in-place AND returns it: input is already a copy.
- Two-mechanism F6 exclusion: different jobs, both needed.
- F10 read endpoints shipped alongside write path.
- F10 static-path route declared before dynamic-path route.
- `valuation_verdict` one string: Sonnet finds it easier.
- Keep `all_candidates` persisted but strip from API: replay-ability.
- Dividend tracking dropped (F8).
- Realized P&L hidden UI but kept backend (Chat 9 cleanup).
- F7 sequenced last (Chat 10): test pollution becomes natural reset.
- F8 dropped: dividends auto-arrive in bank.
- F14 folded into F2: earnings proximity matters for sell timing and buy gating.
- Watchlist (F13) extends engine universe, not separate scoring path.
- F4 ntfy errors channel public over private: iOS APNs vs polling.
- F4 `CRON_REGISTRY` in code, not Mongo.
- F4 intraday strict per-slot heartbeats with `mark_skipped()` for inert cases.
- `cron_health_check.py` is itself a registered cron (excludes itself when scanning).
- F5a kept user's Sunday cron chain.

### Chat 4 additions
- F2b digests on public ntfy.sh.
- F14 shipped as gating signal, not UI feature.
- F14 refresh-future semantics.
- F14 + F2 sell-side: shared scoring pipeline via optional `group_signals_def`.
- F2 `CandidateScore` keeps fixed buy-side fields; sell-side flows through `group_meta`.
- F2 `--direction=both` as production cron path.
- F2 `compute_system_performance(direction='sell')` sign-flip at read time.
- F2 sell-side outcome direction stamping (denormalized for query efficiency).

### Chat 5 additions
- F2b display-layer direction branching (`_format_score_breakdown` + `isSellSide` both infer from data shape).
- Audit-then-fix Chat 5 ordering (rewrite PROJECT_STATE first as handoff insurance).
- **A1 typed PATCH model (`MonitoredStockFeedbackPatch`) instead of bare dict $set:** the existing `MonitoredStock` model has 30+ fields including aspirational ones (`thesis`, `conviction_history`, `target_buy_price`, etc.) that the feedback writer doesn't have. Using `MonitoredStock(...).model_dump()` would overwrite those rich fields with defaults on every feedback write. The typed patch model is a minimal contract that exactly matches what the writer touches — extras would be caught by `extra="forbid"` at write time. Compromise: writer reality is enforced; rich-entry paths (agent, watchlist seed) stay open. Q1 resolved to MIGRATE specifically because data was throwaway, so wipe-and-clean was safe.
- **A1 `$setOnInsert` seeding** for `added_by`/`added_reason`/`_schema_version`/`created_at`: lets the feedback path upsert without violating the required fields on `MonitoredStock`. Without this seeding, freshly-created docs from feedback would fail `MonitoredStock(**doc)` on any future read.
- **A2 part 1 wrapper return-shape change (`raw resend dict` → `{ok,id,error}`)**: justified because (a) makes failure handling explicit (callers can't ignore failures by accident), (b) matches what `digest_delivery._send_email` already returned to `_log_delivery`, (c) the catch-and-swallow inside `notify.email()` prevents one bad alert from crashing the whole notify path. Trade-off: existing callers (`reconciliation.notify_drift`) that relied on exception-based failure detection are now silently broken until A2 part 2 lands. This is exactly the wrapper-return-shape trap that earned the new Section 14 / 15 rules.

## Section 21: What is intentionally NOT included in this project

- Auto-trading. Never.
- Multi-user.
- Mutual funds, FDs, foreign equities, derivatives, crypto.
- Native mobile app.
- Tax filing (we inform; CA files).
- Dividend tracking (F8 dropped).
- Accounting or financial planning.
- Goal-based planning.
- Real-time tick data.
- Public-facing dashboard.
- Backtesting framework.
- Notification customization UI.
- Account aggregation.
- Social features.
- Technical indicator alerts.
- Options tracking.
- Index fund comparison page.
- Separate `/news` page.
- Heatmaps / pretty visualizations.
- Portfolio rebalancing recommender.
- Social sentiment tracking.
- Manual-clear endpoint for feedback (use mongosh as escape hatch).
- `/calendar` page.
- Loss-cutting sell pipeline (F2 is profit-booking only; `in_profit` gate enforces).

## Section 22: Glossary

- ISIN: 12-char NSE/BSE primary key.
- NSE / NIFTY 100 / FIFO / LTCG / STCG / Section 49(2C) / ICICI Direct / ICICI ZIP / TMPV / TMCV / EW NIFTY: see prior version.
- Composite score: 0-100, Q/V/M/N (buy) or booking_opportunity/valuation_stretch/risk/tax_concentration (sell).
- Confidence score: 0-100, deterministic.
- Dossier: Sonnet-generated per-candidate note.
- Outcome: `suggestion_outcomes` doc tracking stock vs benchmark.
- Bucket: outcome user-action label.
- Watchlist: F13 user-curated NSE/BSE stocks.
- `user_action`: per-candidate stamp at serialization time (F6).
- `direction` (F2): `"buy"|"sell"` on `SuggestionRun`/`SuggestionOutcome`.
- `monitored_stocks_audit`: F10 append-only audit collection.
- `earnings_calendar` (F14): cached yfinance earnings events.
- Combined digest (F2): ONE email + ONE ntfy via `send_combined_digest`.
- `isSellSide` (F2): frontend boolean from `groupMeta?.booking_opportunity`.
- `_format_score_breakdown` (F2b cea8eee): direction-aware digest helper.
- **`MonitoredStockFeedbackPatch` (Chat 5 A1)**: typed Pydantic model encapsulating the `$set` patch written by `/suggestions/{isin}/feedback`. `ConfigDict(extra="forbid")`. Catches Literal drift at write time. Field set must stay in sync with `submit_feedback`'s `$set` block.
- **`notify.email()` return contract (Chat 5 A2)**: `{ok: bool, id: str|None, error: str|None}`. Swallows Resend exceptions. Optional `text=` param enables multipart/alternative.

End of PROJECT_STATE.md.
