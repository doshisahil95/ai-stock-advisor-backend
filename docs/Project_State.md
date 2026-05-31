
# PROJECT_STATE.md

Living source of truth for the Personal AI Stock Advisor. Updated at the end of every chat.

This file is the bootstrap document for any new conversation with an AI assistant. If you (the assistant) are reading this for the first time in a new chat: read it top to bottom before doing anything. Do not skim. Do not assume. Do not redesign. The prior chat hit context limits or context drift — that's why we're here.

**Companion doc:** `docs/master_todo.md` is the canonical ordered task list for everything left to do. Project_State.md describes WHAT THE SYSTEM IS; master_todo.md describes WHAT TO DO NEXT. Read both at the start of every chat.

## Section 0: How to start a new chat

Paste this verbatim at the top of any new chat with an AI assistant working on this project:

```
I need you to continue work on a project called Personal AI Stock Advisor.

Before you do ANYTHING else, read the following in order:
1. https://github.com/doshisahil95/ai-stock-advisor-backend/blob/main/docs/Project_State.md
2. https://github.com/doshisahil95/ai-stock-advisor-backend/blob/main/docs/master_todo.md
3. The current HEAD commit of both repos:
   - https://github.com/doshisahil95/ai-stock-advisor-backend
   - https://github.com/doshisahil95/ai-stock-advisor-frontend
4. https://github.com/doshisahil95/ai-stock-advisor-backend/blob/main/docs/data_flow.md
5. Both repo READMEs.

GitHub content may be cached. Whenever you read a file, capture the commit
SHA you read at, and re-read if the user tells you they have pushed since.

Today's scope is: <DESCRIBE THE FEATURE OR FIX FOR THIS CHAT, or say
"work the next item from master_todo.md" if continuing the master plan>

Hard rules:
- Do not invent parallel patterns. Evolve existing code, don't redesign.
- Re-read files at HEAD before patching them. Do not trust memory. At no
  point will you make code changes while relying on memory. You will
  construct the github urls of the files you need and read them always
  from source. For constructing the github url you need:
    owner:      doshisahil95
    repo:       ai-stock-advisor-backend OR ai-stock-advisor-frontend
    commit SHA: the user will provide (asked for explicitly per the rule below)
    file path:  obtained from the tree-listing command below
  The user will run the tree-listing command immediately after pasting this
  Section 0 bootstrap and BEFORE describing scope, so you always have an
  accurate file inventory. Re-request the command at any point a SHA advances.
  Tree-listing command (request this in your acknowledgement message):
    cd ~/Projects/Personal/ai-stock-advisor
    echo "===== BACKEND HEAD =====" && git -C ai-stock-advisor-backend rev-parse HEAD && \
    echo "===== BACKEND TREE =====" && git -C ai-stock-advisor-backend ls-tree -r --name-only HEAD && \
    echo "===== FRONTEND HEAD =====" && git -C ai-stock-advisor-frontend rev-parse HEAD && \
    echo "===== FRONTEND TREE =====" && git -C ai-stock-advisor-frontend ls-tree -r --name-only HEAD
- ASK ME FOR THE CURRENT BACKEND (and frontend if relevant) SHA BEFORE
  PROPOSING ANY CODE CHANGE. Re-read the actual file at that SHA before
  writing any find-and-replace block. Find-blocks written from snippet
  memory or earlier-read state cause silent failures. Standing convention
  from Chat 5; see Section 14. NO EXCEPTIONS.
- Hand me full file contents OR exact find-and-replace. Never "rest unchanged".
- Use canvas artifacts for files. Use chat for tests.
- Project_State.md AND master_todo.md are ALWAYS delivered as complete
  full-file replacements, never as patches, find-and-replace, or
  "rest unchanged". No exceptions, no matter how small the edit.
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
- BEFORE writing any patch that documents what a script does, READ THE
  SCRIPT BODY at HEAD. File-map / README / data_flow summaries can drift
  away from the actual code (TD12 in Chat 5.5 was exactly this). (See
  Section 14.)
- BEFORE documenting a cron line, verify the script's argparse accepts the
  flags. The Sunday 07:00 IST `run_weekly_suggestions.py` crontab line had
  `--notify --run-type scheduled` for weeks; neither flag exists on the
  script. argparse rejected every Sunday run, no digest fired. Caught
  Chat 5.5; logged as TD14 and as master_todo #1. (See Section 14.)
- If you start hallucinating, drifting, or forgetting facts, say
  "I AM LOSING CONTEXT" so I can switch to a new chat.

Acknowledge by summarizing back to me:
- What you understood about the project from Project_State.md
- What's already shipped vs open (per Section 13 + master_todo.md current
  position)
- The exact scope of today's chat (which master_todo item(s) if continuing
  the plan)
- Any uncertainty you have before starting

Do not start coding until I confirm your summary is accurate.
```

Note on filename casing: the file on disk is `docs/Project_State.md` (title case). GitHub paths are case-sensitive. Earlier copies of this bootstrap used `PROJECT_STATE.md` (all-caps) and `404`'d.

Note on URL construction: prefer `https://raw.githubusercontent.com/doshisahil95/<repo>/<sha>/<path>` over the GitHub blob URL — the blob URL frequently returns `LINK_NEEDS_AUTH` for Glean readers even on public repos. Standing convention from Chat 5.5; reinforced Chat 5.7.

## Section 1: Project identity

Personal AI Stock Advisor. Single-user portfolio + research tool for Indian NSE equities. Built for and by Sahil Doshi (Senior Consulting Engineer, MongoDB, India).

Strict design constraint that overrides everything else: the system never executes trades. Sahil trades manually in ICICI Direct. The system records, analyzes, and advises only. Any feature that would auto-place an order is out of scope, permanently.

The system is also not regulatory advice. Dossiers and suggestions must use phrasing like "the system flagged this because..." and "this is a good buy because..." or "this is a good sell because...". The user decides; the user trades. The goal of the system is to maximise the investments.

Goal of the tool: grow money. Every feature is judged on whether it helps with one of:
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
- Project_State.md AND master_todo.md are ALWAYS delivered as complete full-file replacements, never patches/diffs/find-and-replace. No exceptions.
- ASK FOR CURRENT BACKEND SHA BEFORE PROPOSING ANY CODE CHANGE. Re-read the file at that SHA before writing the patch. (Chat 5 standing convention; see Section 14.)
- BEFORE documenting what a script does, read its body at HEAD; before documenting a cron line, verify the script's argparse accepts the flags. (Chat 5.5 standing conventions; see Section 14.)
- AT NO POINT make code changes while relying on memory. Construct the GitHub URL of the file you need (owner=`doshisahil95`, repo, commit SHA the user supplied, file path from the Section-0 tree listing) and re-read from source. (Chat 5.7 standing convention; see Section 14.)
- WHEN CONTINUING THE MASTER PLAN: read `master_todo.md` current-position pointer FIRST, confirm the next item with the user, then proceed. (Chat 5.8.)

## Section 3: Tech stack

### Backend
- Python 3.12
- FastAPI
- Pydantic v2 (every Query() in routers uses `pattern=` not `regex=` post Chat 5 A19; round-trip / `ge=0` validator hardening across models post Chat 5.6)
- MongoDB Atlas, M10 cluster, ap-south-1 region
- uv (package manager — replaces pip/poetry)
- yfinance (price + fundamentals + earnings calendar data; free tier)
- Anthropic Claude SDK (Sonnet 4.5 for dossiers, Haiku 4.5 for classification)
- Tavily (news search; free tier, daily quota enforced)
- Resend (transactional email for digests, drift alerts, smoke tests, cron-health alerts — all routed through `notify.email()` as of Chat 5 A2)
- ntfy (push notifications — public ntfy.sh for all paths; self-hosted private service decommissioned TD8)

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

This Mac vs EC2 port difference is a real, recurring source of confusion for assistants. Always specify which machine when giving test commands. Standing convention: "SSH into EC2 first, then curl localhost:8000."

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
- On EC2 the file is `/etc/portfolio-advisor/secrets.env` (chmod 600, owned by root)
- On Mac the file is `<repo>/.env` (chmod 600, gitignored)

`Settings` uses pydantic-settings with `model_config = SettingsConfigDict(env_file=str(SECRETS_FILE), env_file_encoding="utf-8", case_sensitive=True, extra="ignore")`. Pydantic-settings reads the file directly into the `Settings` object — secrets are NOT exported to `os.environ`.

If the assistant ever suggests `~/secrets/secrets.env` on EC2, it is wrong.

F2b addition (Chat 4): `NTFY_PUBLIC_TOPIC_DIGESTS` must be present in `/etc/portfolio-advisor/secrets.env` — required (no default). Subscribe the iPhone ntfy app to the topic value before running cron.

Chat 5 reminder: when rotating the Atlas password, update BOTH `secrets.env` files (EC2 and Mac) in the same session. URL-encode any password containing `@ : / ? # [ ] ! % & = +` via `python3 -c "from urllib.parse import quote_plus; print(quote_plus('PASTE'))"`. Atlas shows the new password only once after generation.

Chat 5.5 TD9 SHIPPED (commit 1, 2026-05-24): `NTFY_URL`, `NTFY_USER`, `NTFY_PASS` removed from both `settings.py` AND the secrets file in one atomic commit + restart. Backup written to `secrets.env.bak.<timestamp>` before sed.

### Deploy scripts
On EC2:
- `~/deploy.sh` — pulls backend, runs `uv sync`, restarts `portfolio-advisor.service`
- `~/deploy-ui.sh` — pulls frontend, runs `npm install --legacy-peer-deps`, runs `npm run gen-api`, runs `npm run build`, restarts `portfolio-advisor-ui.service`

The `gen-api` step regenerates `lib/api-types.ts` against the running backend's OpenAPI spec. That file is gitignored. On Mac, override URL since backend is on 8001:
```
API_OPENAPI_URL=http://100.112.20.41:8000 npm run gen-api
```
or skip — `lib/api-types.ts` is not used at runtime; `lib/api.ts` is hand-typed.

### systemd units on EC2
- `portfolio-advisor.service` — runs `uvicorn app.main:app --port 8000 --host 0.0.0.0` as user `ubuntu`, with `Environment="PYTHONPATH=/home/ubuntu/ai-stock-advisor-backend"`, `Environment="PYTHONUNBUFFERED=1"`. Logs to journald.
- `portfolio-advisor-ui.service` — runs `node /home/ubuntu/ai-stock-advisor-frontend/node_modules/next/dist/bin/next start` on port 3000 with hardening (`NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict`, `ReadWritePaths` includes the frontend dir and `/tmp`).

A sudoers entry at `/etc/sudoers.d/portfolio-advisor-systemctl` lets `ubuntu` restart these services without password.

### Log rotation (Chat 5 SHIPPED 2026-05-24)
`/etc/logrotate.d/portfolio-advisor` rotates all `/home/ubuntu/cron-*.log` weekly:
- `rotate 4` · `compress` + `delaycompress` · `notifempty` + `missingok` · `copytruncate` · `su ubuntu ubuntu`

Daily logrotate cron is the OS-provided `/etc/cron.daily/logrotate`. Force-rotate any time with `sudo logrotate -f /etc/logrotate.d/portfolio-advisor`.

The pre-existing `0 0 * * 0 find ... -size +10M ... tail -10000 ...` crontab line still exists alongside logrotate. Removal scheduled as TD10 / master_todo #2.

### Repos
- Backend: https://github.com/doshisahil95/ai-stock-advisor-backend
- Frontend: https://github.com/doshisahil95/ai-stock-advisor-frontend

Last verified SHAs (Chat 5.8 closed, 2026-05-29):
- Backend: `c6b1437b90c9555ab9090657af74ab550cf6e1cd` (post-Chat-5.7 Project_State.md commit; advances after this Chat 5.8 doc commit — pin in next chat's first read).
- Frontend: `4f31b49b103f92ea5b4721f9728156041e908f49` (unchanged through Chats 5.6-5.8; TD13 per-page reference shipped at this SHA).

## Section 5: Backend file map

Directory layout under `app/` and top-level (verified against backend tree at SHA `c6b1437b`):
```
app/
  main.py                     FastAPI bootstrap, router includes, lifespan
  agents/__init__.py          empty package placeholder
  scheduler/__init__.py       empty package placeholder
  config/
    settings.py               pydantic-settings; loads secrets file
                              F2b: NTFY_PUBLIC_TOPIC_DIGESTS (required)
                              TD9 SHIPPED: NTFY_URL/USER/PASS field declarations removed
  db/
    client.py                 Mongo client, get_db(), Collections accessor class
                              (incl. monitored_stocks_audit — F10, earnings_calendar — F14)
    indexes.py                ensure_indexes() called on startup
                              (TODO: TTL on prices_intraday — master_todo #12)
  models/
    _common.py                utcnow(), Decimal128 helpers, ObjectId helpers
                              (master_todo #22: reject NaN in _to_decimal)
    instrument.py             Instrument (NSE master record)
    holding.py                Holding (active position)
    transaction.py            Transaction (BUY/SELL/SPLIT/BONUS/DEMERGER)
                              Chat 5.6: ge=0 validators on quantity / price / total_fees
    fundamentals.py           InstrumentFundamentals (per-ISIN, per-refresh)
    earnings_event.py         F14: EarningsEvent (one doc per ISIN per earnings_date)
    suggestion.py             SuggestionRun, SuggestionOutcome, CandidateScore,
                              SignalScore, GateResult
                              F2 direction field; Chat 5.6 round-trip hardening
                              (TD7 / master_todo #45 deferred: sell-side groups as
                              first-class fields)
    news.py                   NewsArticle (live model — the only news model)
    monitored_stock.py        MonitoredStock + MonitoredStockFeedbackPatch
                              Chat 5 A1 SHIPPED — MonitoringStatus Literal aligned
                              (TD1 / master_todo #43 deferred: direction-aware)
    macro_signal.py           placeholder
    conversation.py           placeholder (Chat 6 / master_todo #27 will use)
    reconciliation.py         ReconciliationSnapshot
    cost_basis_adjustment.py  CostBasisAdjustment
    alert_log.py              placeholder
    digest.py                 placeholder (delivery audit lives in `digest_deliveries`)
    price_daily.py            placeholder (collection writers use raw dicts)
    symbol_override.py        SymbolOverride (manual ISIN aliases)
    user_profile.py           UserProfile (singleton, _id="sahil")
  routers/
    holdings.py               /portfolio/holdings*, /sell, /preview-sell,
                              /history, /transactions
                              master_todo #5: add validate_replay to /sell
                              master_todo #6: delete duplicate list_transactions handler
                              master_todo #7: try/except around recompute_holding
                              master_todo #15: remove `from pydoc import doc`
    portfolio.py              /portfolio/summary
                              master_todo #30: utcnow() sweep (line 43)
    transactions.py           /transactions/search, CRUD, audit endpoints
                              master_todo #4: write-before-apply on PATCH/DELETE
                              master_todo #18: drop $options:i on regex
                              master_todo #31: tz-aware datetime sweep
    reconciliation.py         /reconciliation/snapshot, /snapshots, /auto-snapshot
    instruments.py            /instruments (symbol_overrides CRUD)
    cost_basis.py             /cost-basis/adjustments
    suggestions.py            /suggestions/latest, /runs, /runs/{id}, /performance,
                              /{isin}/feedback, /{isin}/audit, /feedback/audit/recent
                              F2: ?direction=buy|sell on read endpoints
                              Chat 5 A1: writer uses MonitoredStockFeedbackPatch
                              Chat 5 A19: Query() pattern= migration
                              master_todo #17: ISIN pattern validator on Path
                              master_todo #26: direction-aware feedback relabel
    cron.py                   /cron/heartbeats (F4)
  services/
    instrument_service.py     lookup_isin, bulk_lookup_isins, refresh
    yfinance_lookup.py        thin yfinance Ticker wrapper for sector/industry/long-name
                              enrichment when NSE master is sparse
    price_service.py          EOD + intraday fetch, bulk_get_latest_prices,
                              annotate_with_current_price, get_previous_close
                              master_todo #9: holiday guard in _intraday_row_from_df
                              master_todo #10: align price_stale docstring vs code
                              master_todo #11: rewrite bulk_get_previous_closes
                              master_todo #31: tz-aware datetime sweep (line 155)
    holdings_service.py       recompute_holding, validate_replay, preview_sell,
                              _to_decimal helper
                              Chat 5.6: preview_sell SPLIT/BONUS lot-walk fix
                              master_todo #8: serialize recompute_holding per-ISIN
    portfolio_service.py      compute_summary
    transactions_audit_service.py  log_change, get_audit_for_transaction
    monitored_stocks_audit_service.py  F10: log_change (write-before-apply)
    reconciliation.py         take_auto_snapshot, drift detection,
                              _send_drift_alerts (helper sends ntfy + email)
                              Chat 5 A2 part 2: branches on notify.email() result["ok"]
                              master_todo #25: fire ntfy push on threshold drift
                              master_todo #31: tz-aware datetime sweep (lines 78, ~138)
    cost_basis_service.py     get_active_adjustments, total_adjustment_amount
    fundamentals_service.py   yfinance provider, refresh_one, refresh_universe, etc.
                              F14: earnings calendar refresh
                              master_todo #30: utcnow() sweep (lines 370, 485, 505)
    tavily_client.py          quota-tracked wrapper, TavilyQuotaExceeded
                              master_todo #19: atomic find_one_and_update for quota
                              master_todo #31: tz-aware datetime sweep (lines 50, ~55)
    news_fetcher.py           fetch_for_instrument, fetch_for_universe
    news_classifier.py        Haiku batch classifier, retry pass
                              (master_todo #13: news body purge cron pairs with this)
    news_signals.py           compute_news_signals_for_isin, _bulk
    scoring_service.py        extract_signals, score_candidates, weights, gates
                              F14: earnings-proximity gate shared buy + sell
                              F2: sell-side scoring (DEFAULT_SELL_CONFIG, etc.)
                              Chat 5 A3+A4: composite_for_candidate writes raw_value
                              master_todo #30: utcnow() sweep (lines 116, 813, 890)
    dossier_service.py        generate_dossiers_for_top_k, Sonnet
                              F2: sell-side prompt + position context
                              master_todo #30: utcnow() sweep (lines 166, 192)
                              (TD3 / master_todo #44 deferred: split valuation_verdict)
    suggestion_engine.py      run_suggestions (full pipeline);
                              get_excluded_isins (F6+F5b: rejected 90d,
                              passed this-run, acted 30d)
                              F2: run_suggestions(direction="buy"|"sell")
                              Chat 5 A17: stale comment refreshed
    outcome_tracker.py        create_outcomes_for_run, snapshot_open_outcomes,
                              compute_system_performance
                              F2: direction stamping + sign-flip at read time
    digest_delivery.py        send_weekly_digest, send_combined_digest
                              F2b: ntfy via push_public("digests", ...)
                              F2b cea8eee: _format_score_breakdown direction-aware
                              Chat 5 A2 part 1: delegates to notify.email()
                              master_todo #21: persist run_id BEFORE digest formatting
    explainability.py         SIGNAL_META, GROUP_META, GATE_META, FEEDBACK_META,
                              PAGE_INTRO + PAGE_INTRO_SELL, enrich_run, enrich_candidate
                              F2: SIGNAL/GROUP/GATE_META extended; _GROUP_TO_SIGNALS extended
                              Chat 5.5 TD11: _build_signal_meta raw-value fallback
    notify.py                 push_public, email
                              Chat 5 A2 part 1: email returns {ok,id,error}, optional text=
                              Chat 5 TD8: push_private / PrivateTopic removed
                              master_todo #20: retry on transient 5xx/429 in email()
    cron_heartbeat_service.py F4: cron_run context manager, CRON_REGISTRY,
                              get_recent_heartbeats, ist_today_window_utc
                              Chat 5 A6/A6.5/A7 fixes
                              master_todo #23: fallback log file on heartbeat-insert failure
scripts/
  __init__.py
  init_db.py
  refresh_instruments.py        Chat 5 A13: docstring corrected to NSE EQUITY_L.csv
  refresh_prices.py
  refresh_prices_intraday.py    master_todo #35: ntfy push on insert exception
  take_reconciliation_snapshot.py
  seed_nifty100.py              CORRECTLY NAMED. Reads ind_nifty100list.csv from NSE.
                                Chat 5.5 TD12 RESOLVED-as-doc-fix
  seed_cost_basis_adjustments.py
  import_orderbooks.py
  reconcile_staging.py
  promote_staging.py
  add_manual_transactions.py    master_todo #5: validate_replay on manual SELL path
  refresh_fundamentals.py       F14: default universe NIFTY 100 ∪ active holdings
                                Chat 8 / master_todo #29 will extend for watchlist
  fetch_news_for_universe.py    Chat 5 A16: --include-held on EC2 crontab
                                Chat 8 / master_todo #29 will extend for watchlist
  run_weekly_suggestions.py     F2: --direction=buy|sell|both (default "buy")
                                TD14 / master_todo #1: crontab line has bogus flags
  track_suggestion_outcomes.py
  cron_health_check.py          F4: daily 21:00 IST; dual-transport Chat 5 commit 8
                                master_todo #24: try/except around Mongo reads
                                master_todo #23: read fallback log too
  smoke_test.py                 Chat 5 TD8: dropped push_private references
  (NEW master_todo #13: purge_news_bodies.py — daily news body cleanup)
tests/
  __init__.py                   empty package placeholder
                                master_todo #33: stand up pytest harness
docs/
  data_flow.md                  Chat 5 doc deliverable 1/4 SHIPPED
                                Chat 5.5 TD12: universe paragraph corrected
  Project_State.md              THIS FILE (Chat 5.8 doc commit)
  master_todo.md                Chat 5.8 NEW — canonical ordered task list
pyproject.toml                  master_todo #32: pin requires-python upper bound
uv.lock
README.md                       Chat 5 doc deliverable 2/4 SHIPPED
                                Chat 5.5 TD12: §8 + §11 + §5 corrections
```

(Frontend file map in Section 6.)

## Section 6: Frontend file map

Verified against frontend tree at SHA `4f31b49`:
```
app/
  layout.tsx                  root layout, fonts, ThemeProvider, Query Provider
  page.tsx                    dashboard
  providers.tsx               combines ThemeProvider + TanStack QueryClient +
                              ReactQueryDevtools into one Providers component
  globals.css                 Tailwind v4, font variable mappings, shadcn .dark class
  favicon.ico
  holdings/[isin]/page.tsx    single holding drill-down
                              (Chat 9 / master_todo #41: stop_loss edit field)
  reconciliation/page.tsx
  cost-basis/page.tsx
  transactions/page.tsx
  transactions/audit/page.tsx
  suggestions/page.tsx        F6: user_action stamp drives collapsed render
                              F2 SHIPPED: shadcn Tabs for buy/sell
components/
  ui/                         shadcn primitives — alert-dialog, badge, button,
                              card, chart, dialog, dropdown-menu, input, label,
                              popover, select, separator, sheet, skeleton,
                              table, tabs, textarea, tooltip
  holdings-table.tsx          (Chat 9 / master_todo #40: hide realized P&L)
  buy-sheet.tsx
  sell-sheet.tsx              Phase-1 manual SELL transaction sheet with FIFO
                              preview. NOT the F2 sell-side suggestion surface.
  transaction-edit-sheet.tsx
  holding-header.tsx          (Chat 9 / master_todo #40: hide realized P&L)
  holding-stats.tsx           (Chat 9 / master_todo #40 + #41: realized P&L hide +
                              stop_loss edit field)
  price-chart.tsx
  transactions-list.tsx
  notes-panel.tsx             master_todo #14: refetchQueries (lines 43, 46)
  recent-activity-card.tsx
  sector-breakdown.tsx
  stat-card.tsx
  top-movers.tsx
  totals-row.tsx              (Chat 9 / master_todo #40: hide realized P&L)
  reconciliation-badge.tsx
  theme-provider.tsx
  theme-toggle.tsx
  refresh-button.tsx          master_todo #14: refetchQueries (lines 17-19)
  suggestion-card.tsx         F6: CollapsedFeedbackRow when user_action != null
                              F2 SHIPPED: isSellSide branch
  explain-popover.tsx
  page-intro.tsx
lib/
  api.ts                      hand-typed API client; SINGLE SOURCE OF TRUTH;
                              F2 SHIPPED: direction param, BucketKey, by_bucket
  format.ts                   inr, pct, colorForChange, dateTime, nf, date
  utils.ts                    cn() (clsx + tailwind-merge)
public/                       static SVGs (file, globe, next, vercel, window)
README.md                     Chat 5 doc deliverable 3/4 SHIPPED at frontend SHA
                              9edfc8f; TD13 per-page reference at HEAD 4f31b49.
                              Covers Dashboard, Holdings drill-down, Transactions,
                              Audit, Reconciliation, Cost Basis, Suggestions.
AGENTS.md                     Four-line note: read node_modules/next/dist/docs/
CLAUDE.md                     One-line file referencing @AGENTS.md
components.json               shadcn config (Nova preset)
package.json
package-lock.json
next.config.ts                Default config; no custom rewrites/middleware
postcss.config.mjs            Tailwind v4 PostCSS plugin
tsconfig.json                 strict mode; "@/*" alias; bundler resolution
.npmrc                        npm config (legacy-peer-deps used in deploy-ui.sh)
```

There is no `middleware.ts`, no `.env.example`, no custom `next.config.*` overrides at HEAD. Tailscale is the auth perimeter.

## Section 7: Database collections (exhaustive)

All collections live in MongoDB Atlas M10. DB name set by env (`MONGODB_DB_NAME`). All collections accessed via `Collections.<name>()` from `app.db.client`. Indexes ensured at startup via `app/db/indexes.py`.

### Phase 1 collections

#### `instruments`
- Master NSE/BSE list, refreshed daily from NSE's official `EQUITY_L.csv`
- Key fields: `exchange`, `symbol`, `isin`, `name`, `instrument_type`, `segment`, `lot_size`, `tick_size`, `source`, `last_seen_at`, `last_changed_at`, `in_nifty100`, `nifty100_marked_at`
- Count: ~2,368 total; ~100 with `in_nifty100=True`
- Indexes: `(exchange, symbol)` unique, `isin`, `last_seen_at`, `last_changed_at`, `in_nifty100`

#### `symbol_overrides`
- Manual ISIN aliases. Key fields: `exchange`, `symbol`, `isin`, `reason`, `created_at`

#### `holdings`
- Active positions, one doc per ISIN; soft-deleted on full exit
- Key fields: `isin`, `symbol`, `exchange`, `name`, `sector`, `industry`, `quantity` (Decimal128), `avg_cost`, `invested_amount`, `realized_pnl`, `first_purchased_at`, `last_traded_at`, `thesis`, `notes`, `stop_loss`, `target_price`, `tags`, `deleted_at`
- INVARIANT: every query MUST include `deleted_at: None`
- Indexes: `isin` unique (partial: only where `deleted_at` is None), `(deleted_at, last_traded_at)`
- Writer: `recompute_holding(isin)` in `holdings_service.py` is the ONLY authoritative writer
- Note: `realized_pnl` is structural (FIFO computes it) but is HIDDEN in UI per master_todo #40
- F2: `target_price` consumed by sell-side scoring. `stop_loss` wired by master_todo #41

#### `transactions`
- Append-only ledger
- Key fields: `isin`, `symbol`, `exchange`, `type` (BUY/SELL/SPLIT/BONUS/DEMERGER), `trade_date`, `quantity` (Decimal128), `price`, `total_fees`, `remaining_quantity`, `notes`, `source`, `corporate_action.ratio_from`, `corporate_action.ratio_to`, `fully_consumed_at`, `deleted_at`
- INVARIANT: never directly UPDATEd or DELETEd; PATCH/DELETE require reason, write to `transactions_audit` first, then apply, then `recompute_holding`. **master_todo #4: order is currently apply-then-audit; needs flip.**
- Indexes: `(isin, trade_date)`, `(symbol, trade_date)`, `trade_date`
- Chat 5.6: `ge=0` validators on quantity / price / total_fees; SPLIT/BONUS preview covered in `preview_sell`

#### `transactions_staging`
- Holding area for ICICI order book imports. Same shape as `transactions`.

#### `transactions_audit`
- Append-only audit log; one doc per edit/delete
- Key fields: `transaction_id`, `action` (edit/delete), `reason`, `changed_fields`, `performed_at`, `symbol`
- INVARIANT (per Section 11): written BEFORE the actual change is applied. **Currently violated in transactions router — master_todo #4.**

#### `prices_daily`
- EOD OHLCV; ~5 years history. Key fields: `isin`, `date`, OHLC, `volume`, `source`. Indexes: `(isin, date)` unique.

#### `prices_intraday`
- Latest intraday quote captured every 15 min during market hours
- Key fields: `isin`, `symbol`, `date`, `captured_at`, OHLCV, `source="yfinance_5m_latest"`
- INVARIANT: append-only within a day
- **No TTL configured yet — master_todo #12 will add 90-day TTL**
- Writer: `scripts/refresh_prices_intraday.py`. master_todo #9: needs holiday guard.

#### `reconciliation_snapshots`
- Daily comparisons of our totals vs ICICI Direct
- Key fields: `type`, `taken_at`, `our_invested`, `our_current_value`, `our_day_gain`, `icici_*`, `drift_invested_pct`, `drift_current_pct`, `drift_alerts`, `notes`
- master_todo #25: auto-snapshot should fire ntfy on threshold drift (currently silent to Mongo only)

#### `cost_basis_adjustments`
- Audit trail for TMPV/TMCV-style adjustments per IT Act Section 49(2C)

#### `user_profile`
- Single doc, `_id="sahil"`

### Phase 2 collections

#### `monitored_stocks`
- User-feedback state + watchlist (F13)
- Key fields: `isin`, `status` (Literal `"tracking"/"passed"/"rejected"/"watchlist"`), `symbol`, `exchange`, `name`, `sector`, `industry`, `added_by`, `added_reason`, `added_at`, `thesis`, `conviction`, `conviction_history`, `target_buy_price`, `alert_above`, `alert_below`, `alert_on`, `tags`, `user_notes`, `last_reviewed_at`, `last_user_interest_at`, `acted_at`, `passed_at`, `rejected_at`, `last_feedback_action`, `last_feedback_at`, `last_feedback_note`, `created_at`, `updated_at`
- Chat 5 A1 SHIPPED: schema aligned to writer; `MonitoredStockFeedbackPatch` typed wrapper
- INVARIANT (F10): writes preceded by `monitored_stocks_audit_service.log_change(...)`
- Indexes: `isin` unique (PARTIAL — `partialFilterExpression={"status": "tracking"}`), `(status, rejected_at)`
- **TD1 / master_todo #43 deferred: direction-aware schema (currently direction-agnostic)**

#### `monitored_stocks_audit` (F10)
- Append-only audit log
- Key fields: `isin`, `action`, `previous_status`, `new_status`, `note`, `performed_at`, `_schema_version`
- INVARIANT: writer invoked BEFORE corresponding `update_one`
- Indexes: `(performed_at desc)`, `(isin, performed_at desc)`

#### `instruments_fundamentals`
- One doc per ISIN per refresh. Indexes: `isin_latest_unique`, `fetched_at`. F14: universe is NIFTY 100 ∪ active holdings.

#### `earnings_calendar` (F14)
- Upcoming + historical earnings per ISIN. yfinance `Ticker.calendar`
- Key fields: `isin`, `symbol`, `exchange`, `earnings_date`, `source`, `source_raw`, `fetched_at`, `created_at`
- INVARIANT: `refresh_earnings_for(isin, ...)` deletes future events then re-inserts
- Indexes: `(isin, earnings_date)` unique, `(earnings_date asc)`, `(isin)`, `(fetched_at desc)`

#### `news_articles`
- Classified news; one doc per URL
- Key fields: `url`, `title`, `published_at`, `fetched_at`, `source`, `body`, `body_purged_at`, `entities_isins`, `themes`, `sentiment`, `sentiment_confidence`, `severity`, `classifier_summary`, `classified`
- Indexes: `url` unique, `(entities_isins, classified, fetched_at)`, `(classified, fetched_at)`
- **`body` never purged — master_todo #13 will add daily purge script**

#### `suggestion_runs`
- Append-only history of every weekly run
- Key fields: `_id`, `_schema_version`, `run_date`, `run_date_ist`, `run_type`, `direction`, `status`, `started_at`, `finished_at`, `error`, `universe_size`, `excluded_*`, `candidates_*`, `config`, `top_candidates`, `all_candidates`, `top_k`, `notes`
- INVARIANT: append-only
- INVARIANT (Chat 5.6 round-trip): legacy persisted runs missing newer optional fields round-trip cleanly
- Indexes: `(run_date desc)`, `(run_date_ist, run_type)`, `(status)`

#### `suggestion_outcomes`
- One doc per top-K candidate per run
- Key fields: `isin`, `symbol`, `suggestion_run_id`, `suggested_at`, `suggested_at_price`, `suggested_rank`, `suggested_composite_score`, `tracking_status`, `direction`, `price_at_{30,60,90,180}d`, `nifty_at_{30,60,90,180}d`, `excess_return_*`, `user_action_at`, `user_action_note`, `created_at`, `updated_at`
- INVARIANT (A.5): snapshot eligibility `tracking_status != "expired"`. Auto-flip to expired only at day 180 for `"open"`.
- INVARIANT (F2): `compute_system_performance(direction="sell")` sign-flips at read time.
- master_todo #26: feedback relabel should filter by direction (currently doesn't)

#### `tavily_quota`
- One doc per UTC day; counters incremented
- INVARIANT: `TAVILY_DAILY_CALL_LIMIT` enforced
- **master_todo #19: replace check-then-act with atomic find_one_and_update**

#### `digest_deliveries`
- Audit log of weekly digests
- Key fields: `run_id`, `run_date_ist`, `sent_at`, `top_count`, `subject`, `email_*`, `ntfy_*`
- F2: combined-digest sends attach to BUY run id
- master_todo #21: persist run_id before formatting
- **TD14 IMPACT: no rows written by Sunday cron since bogus flags landed — master_todo #1**

#### `cron_heartbeats` (F4)
- Key fields: `cron_name`, `started_at`, `finished_at`, `status`, `error`, `metadata`, `_schema_version`
- INVARIANT: append-only; best-effort. **master_todo #23: fallback log on insert failure**
- INVARIANT (Chat 4): `_Heartbeat.meta` is an ATTRIBUTE; `ctx.meta = {...}`
- Indexes: `(cron_name, started_at desc)`, `(started_at desc)`, TTL on `started_at` (60 days)

### Scaffold collections (not actively written)
`digests`, `alerts_log`, `conversations` (Chat 6 / master_todo #27 will use), `macro_signals`.

### Future collections (planned)
- None pending. F11 is read-only reformatter; F13 watchlist reuses `monitored_stocks` with `status="watchlist"`.

## Section 8: API endpoints (exhaustive)

### Phase 1
```
GET    /health                                       (master_todo #34: actually ping Mongo)
GET    /portfolio/holdings                           Holding[]
GET    /portfolio/holdings/{isin}                    Holding
POST   /portfolio/holdings                           Holding (BUY)
PATCH  /portfolio/holdings/{isin}                    Holding (notes/thesis/stop_loss/target_price/tags only)
POST   /portfolio/holdings/{isin}/sell               Holding OR {message, realized_total}
                                                     (master_todo #5: add validate_replay)
POST   /portfolio/holdings/{isin}/preview-sell       SellPreview
GET    /portfolio/holdings/{isin}/history?days=N     PriceBar[]
GET    /portfolio/holdings/{isin}/transactions       Transaction[]
                                                     (master_todo #6: dup handler to delete)
GET    /portfolio/summary                            PortfolioSummary
GET    /transactions/search?...                      {results, total}
                                                     (master_todo #18: drop $options:i)
GET    /transactions/{id}                            Transaction
PATCH  /transactions/{id}                            Transaction (requires reason)
                                                     (master_todo #4: write-before-apply order)
DELETE /transactions/{id}                            {deleted: true} (requires reason)
                                                     (master_todo #4: write-before-apply order)
GET    /transactions/audit/recent?limit=N            AuditEntry[]
GET    /transactions/{id}/audit                      AuditEntry[]
POST   /reconciliation/snapshot                      ReconciliationSnapshot (manual)
GET    /reconciliation/snapshots                     ReconciliationSnapshot[]
POST   /reconciliation/auto-snapshot                 ReconciliationSnapshot (cron)
                                                     (master_todo #25: ntfy on threshold drift)
GET    /cost-basis/adjustments                       CostBasisAdjustment[]
GET    /instruments                                  symbol_overrides list
POST   /instruments                                  symbol_overrides upsert
DELETE /instruments/{exchange}/{symbol}              delete override
```

### Phase 2
```
GET    /suggestions/latest?direction=buy|sell        SuggestionRun + enrichment
GET    /suggestions/runs?direction=buy|sell&...      {runs, total, limit, skip}
GET    /suggestions/runs/{run_id}                    SuggestionRun + enrichment
GET    /suggestions/performance?direction=buy|sell   SuggestionPerformance with by_bucket
POST   /suggestions/{isin}/feedback                  {isin, action, status, previous_status}
                                                     (master_todo #17: ISIN pattern validator)
                                                     (master_todo #26: direction-aware relabel)
GET    /suggestions/{isin}/audit?limit=N             MonitoredStocksAuditEntry[]   (F10)
                                                     (master_todo #17: ISIN pattern validator)
GET    /suggestions/feedback/audit/recent?limit=N    MonitoredStocksAuditEntry[]   (F10)
GET    /cron/heartbeats?limit=N                      {heartbeats, health_summary}
```

`/cron/heartbeats` response shape:
- `heartbeats`: newest-first list (default 200, max 1000)
- `health_summary`: per-cron rows with `cron_name`, `description`, `schedule`, `expected_today`, `min_runs_per_day`, `last_run_at`, `last_status`, `last_error`, `today_total`, `today_success`, `today_failure`, `today_skipped`, `healthy`
- `healthy = true` iff (not expected today) OR (`today_success + today_skipped >= min_runs_per_day` AND `today_failure == 0`)

### Future endpoints (planned, see master_todo)
```
POST   /chat/suggestions                             ad-hoc chat (F1 / Chat 6 / master_todo #27)
POST   /chat/holdings/{isin}                         ad-hoc chat (F3 / Chat 6 / master_todo #27)
GET    /portfolio/risk-summary                       concentration & risk (F12 / Chat 7 / master_todo #28)
GET    /portfolio/by-tag?tag=X                       tag views (F15 / Chat 7 / master_todo #28)
POST   /watchlist/{isin}                             add (F13 / Chat 8 / master_todo #29)
DELETE /watchlist/{isin}                             remove (F13 / Chat 8 / master_todo #29)
GET    /watchlist                                    list (F13 / Chat 8 / master_todo #29)
GET    /tax/capital-gains?fy=YYYY-YY                 capital gains pack (F11 / Chat 9 / master_todo #39)
POST   /admin/recompute/{isin}                       ops recovery (Ops gap / master_todo #36)
```

### Sell endpoint response shape (critical, often confused)
`POST /portfolio/holdings/{isin}/sell` returns one of:
- The full updated `Holding` doc (partial sell, position still active)
- `{message: "Position fully exited", realized_total: "<string Decimal>"}` (full exit)

The frontend discriminates via type guard on the `_id` field.

## Section 9: Cron registry on EC2

Run `crontab -l` to see current state. Every script below is heartbeat-instrumented via `cron_run()`. The daily `cron_health_check` at 21:00 IST consumes those heartbeats. `CRON_REGISTRY` in `cron_heartbeat_service.py` is the in-code mirror of this schedule — keep both in sync.

```cron
# Phase 1 crons (heartbeat-instrumented Chat 2)
0 3 * * * cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/refresh_instruments.py >> /home/ubuntu/cron-instruments.log 2>&1
0 19 * * 1-5 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/refresh_prices.py >> /home/ubuntu/cron-prices.log 2>&1
*/15 9-15 * * 1-5 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/refresh_prices_intraday.py >> /home/ubuntu/cron-prices-intraday.log 2>&1
30 19 * * 1-5 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/take_reconciliation_snapshot.py >> /home/ubuntu/cron-reconciliation.log 2>&1

# Phase 2 crons (registered Chat 2 via F5a)
0 6 * * 0 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/refresh_fundamentals.py >> /home/ubuntu/cron-fundamentals.log 2>&1
30 6 * * 0 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/fetch_news_for_universe.py --include-held >> /home/ubuntu/cron-news.log 2>&1

# TD14 / master_todo #1 — current EC2 line has bogus `--notify --run-type scheduled` flags
# that argparse rejects every Sunday. Documented line below is the CORRECT version.
0 7 * * 0 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/run_weekly_suggestions.py --direction=both >> /home/ubuntu/cron-suggestions.log 2>&1

45 19 * * 1-5 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/track_suggestion_outcomes.py >> /home/ubuntu/cron-outcomes.log 2>&1

# F4 cron health monitoring (Chat 2; dual-transport Chat 5 commit 8)
0 21 * * * cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/cron_health_check.py >> /home/ubuntu/cron-health.log 2>&1

# Maintenance — TD10 / master_todo #2: remove after first logrotate cycle verified
0 0 * * 0 find /home/ubuntu -maxdepth 1 -name "cron-*.log" -size +10M -exec sh -c 'tail -10000 "$1" > "$1.tmp" && mv "$1.tmp" "$1"' _ {} \;

# NEW (planned, master_todo #13): daily news body purge
# 0 4 * * * cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/purge_news_bodies.py >> /home/ubuntu/cron-purge-news.log 2>&1
```

CHAT 5.5 PENDING ONE-TIME EC2 STEPS (carried into Chat 5.8):
- **TD10 / master_todo #2**: remove the `0 0 * * 0 find ... -size +10M ...` line via `crontab -e` AFTER the first full logrotate cycle completes (next: 2026-05-31; verify 2026-06-01).
- **TD14 / master_todo #1**: remove the bogus `--notify --run-type scheduled` flags from the Sunday 07:00 IST line via `crontab -e`. Optional immediate-recovery:

```bash
ssh ubuntu@100.112.20.41
cd /home/ubuntu/ai-stock-advisor-backend
PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/run_weekly_suggestions.py --direction=both 2>&1 | tee -a /home/ubuntu/cron-suggestions.log
```

`CRON_REGISTRY` (in code) entries (10 total, 11 after master_todo #13 lands):
- `refresh_instruments`, `refresh_prices`, `refresh_prices_intraday`, `take_reconciliation_snapshot`, `refresh_fundamentals`, `fetch_news_for_universe`, `run_weekly_suggestions`, `track_suggestion_outcomes`, `cron_health_check`, `weekly_suggestions_sell` (idle; kept for topology flexibility)

No silent failures: every cron registration must include log file paths AND heartbeat instrumentation AND a `CronSpec` entry. All three.

Cron-health dual transport (Chat 5 commit 8): `cron_health_check.py` sends every anomaly batch on TWO independent transports — `push_public("errors", ...)` + `notify.email(subject, html, text)` — and raises (so `cron_run` marks the run as failed) ONLY when BOTH fail.

## Section 10: Settings and environment variables

Configured in `app/config/settings.py` via pydantic-settings. All required unless marked default.

### Anthropic
- `ANTHROPIC_API_KEY` (required)
- `ANTHROPIC_MODEL_PRIMARY` (default `"claude-sonnet-4-5"`)
- `ANTHROPIC_MODEL_FAST` (default `"claude-haiku-4-5"`)

### MongoDB
- `MONGODB_URI` (required) — URL-encode special chars in the password
  - **Note (master_todo #16):** earlier versions of this section said `MONGODB_URL`. Code uses `MONGODB_URI`.
- `MONGODB_DB_NAME` (required)

### Tavily
- `TAVILY_API_KEY` (required)
- `TAVILY_DAILY_CALL_LIMIT` (default 200)
- `TAVILY_SEARCH_DEPTH` (default `"basic"`)
- `TAVILY_MAX_RESULTS_PER_QUERY` (default 5)

### Email (Resend)
- `RESEND_API_KEY` (required)
- `RESEND_FROM` (e.g., `"advisor@your-domain.com"`)
- `RESEND_TO` (default recipient for `notify.email()`)
- `DIGEST_TO` (digest recipient; may equal `RESEND_TO`)

### ntfy
- `NTFY_PUBLIC_URL` (default `"https://ntfy.sh"`)
- `NTFY_PUBLIC_TOPIC_PRICE`, `NTFY_PUBLIC_TOPIC_NEWS`, `NTFY_PUBLIC_TOPIC_ERRORS`, `NTFY_PUBLIC_TOPIC_DIGESTS`
- `NTFY_PUBLIC_TOPIC_DIGESTS` (F2b — REQUIRED, no default)
- All `NTFY_PUBLIC_TOPIC_*` values must be IDENTICAL on EC2 and Mac
- `push_public(channel)` signature: `channel: Literal["price", "news", "errors", "digests"]`
- `push_private(topic)` — REMOVED Chat 5 commit 7b
- `NTFY_URL` / `NTFY_USER` / `NTFY_PASS` — REMOVED Chat 5.5 commit 1 (TD9 SHIPPED)

## Section 11: Phase 1 INVARIANTS — never violate

From `docs/data_flow.md`. Hard rules.

- Transactions are immutable except through the audited PATCH/DELETE flow. Every PATCH/DELETE writes a `transactions_audit` entry BEFORE applying the change. The `reason` field is required.
  - **CURRENT VIOLATION:** transactions router does apply-then-audit. master_todo #4 will fix.
- `recompute_holding(isin)` is the only authoritative writer to `holdings`. Idempotent. Recomputes from `transactions` from scratch using FIFO. Never write directly to `holdings`.
- `validate_replay(isin, simulated_transactions)` rejects any timeline producing negative quantity. Both PATCH and DELETE on `/transactions/{id}` call this before applying.
  - **CURRENT GAP:** `/portfolio/holdings/{isin}/sell` does NOT call validate_replay. master_todo #5 will fix.
- `holdings.deleted_at = None` filter is universal.
- Cost basis is IT-Act-correct, not broker-nominal.
- `prices_intraday` writes are append-only within a day.
- ICICI portfolio display shows TMPV ~₹813 and TMCV ~₹253 — cosmetically wrong vs our tax-correct numbers; does not affect actual money or tax filing.
- Chat 5.6 robustness: `preview_sell` correctly folds SPLIT/BONUS adjustments into the lot walk.

## Section 12: Phase 2 INVARIANTS

- `suggestion_runs` are append-only.
- `tavily_quota` is one doc per UTC day with `$inc` counters. Hard ceiling enforced. **master_todo #19: currently check-then-act, race-prone.**
- Confidence score is deterministic, NOT LLM-generated.
- The dossier prompt requires narrative-only output. Forbids "buy"/"sell" imperatives and inventing facts.
- `gate_meta`, `group_meta`, `signal_meta`, `confidence_meta`, `feedback_meta`, `page_intro`, `user_action` are PRESENTATION metadata, added by `_serialize_run` via `enrich_run`. Never in the persistent model.
- Snapshot eligibility for `snapshot_open_outcomes` is `tracking_status != "expired"` (A.5).
- Auto-expiry only flips `"open"` outcomes at day 180. User-set labels never overwritten (A.5).
- Feedback re-labels the MOST RECENT non-expired outcome for the ISIN (A.5.1).
- `suggestion_engine.get_excluded_isins()` returns three buckets: `rejected` (90d), `passed` (this run only), `acted` (30d soft-exclude, F5b). Constants intentionally NOT env-configurable.
- F10 write-before-apply: every `POST /suggestions/{isin}/feedback` writes `monitored_stocks_audit` BEFORE the corresponding `monitored_stocks.update_one` apply.
- **Chat 5 A1**: `monitored_stocks` writes go through `MonitoredStockFeedbackPatch(...).model_dump(exclude_none=True)`. `extra="forbid"` catches drift.
- The `notes` field on a `SuggestionRun` is a JSON string containing `{dossiers: [...]}`. The router parses it and exposes `dossiers` at the top level.
- **Chat 5.6 round-trip invariant**: every Phase-2 Pydantic model loads cleanly from any historical persisted doc.

### F2 / F14 invariants (Chat 4)
- `SuggestionDirection` literal = `"buy" | "sell"`. Defaults to `"buy"`.
- The router serializer (`_serialize_run`) and the `/runs` projection BOTH defensively default missing `direction` to `"buy"` on the raw-dict path.
- `compute_system_performance(direction="sell")` SIGN-FLIPS `excess_return` at aggregation time.
- `snapshot_open_outcomes` is DIRECTION-AGNOSTIC.
- `earnings_calendar` refresh: deletes future events then re-inserts. Past events never touched.
- `_sanitize_for_bson` applied to `Ticker.calendar` before insert.
- F14 earnings-proximity gate is SHARED between buy and sell. 5 days threshold. `next_earnings is None` → `skipped=True, passed=True`.
- Sell-side uses different groups (`booking_opportunity`/`valuation_stretch`/`risk`/`tax_concentration`) and gates (`in_profit`/`min_position_age`/`earnings_proximity`).
- `CandidateScore` has FIXED buy-side group fields. Sell-side group scores flow through `group_meta`. **TD7 / master_todo #45 deferred: refactor for symmetry.**
- `monitored_stocks` is currently DIRECTION-AGNOSTIC. **TD1 / master_todo #43 deferred.**
- F2 combined-digest: `--direction=both` emits ONE email + ONE ntfy push.

### Chat 5 A2 (CLOSED)
- `notify.email()` returns `{ok: bool, id: str|None, error: str|None}` and SWALLOWS Resend exceptions.
- All Resend traffic flows through `notify.email()`. **master_todo #20: add 1-2 attempt retry.**

### Chat 5 A3+A4 (CLOSED)
- `SignalScore.raw_value` carries the RAW input that fed normalization.

### Chat 5.5 TD11 (CLOSED)
- `explainability._build_signal_meta` falls back to `_to_float(sig["raw_value"])` rendered via `_format_raw(meta["formatter_kind"], raw)` when `fundamentals_field is None` AND `available is True`.

### Chat 5 commit 8 (CLOSED) — cron-health dual transport
- Dual-transport ntfy + email. Raises only when BOTH fail.

## Section 13: Shipped vs Open

### Shipped through this point

Phase 1 (all shipped, all locked):
- Holdings dashboard with day-gain coloring
- FIFO cost basis with fee allocation and precision
- ICICI Order Book import → staging → reconcile → promote pipeline
- Manual transaction entry for IPOs, demergers, bonuses, splits
- Transaction edit/delete with mandatory reason + audit log (master_todo #4 will reorder)
- Preview-sell endpoint (Chat 5.6 hardened SPLIT/BONUS handling)
- Reconciliation snapshots (manual + auto) with drift detection
- Cost basis adjustments (TMPV/TMCV demerger seeded)
- EOD + intraday price refresh
- Tax view vs broker view in portfolio summary
- Single-holding drill-down page with chart, transactions, notes panel
- Audit log page
- Dark mode toggle
- Reconciliation badge in header
- Recent activity card

Phase 2 Suggestions Engine:
- Unit 1: foundations
- Unit 2: news fetch + Haiku classify, Sonnet dossier generator
- Unit 3: outcomes, performance, frontend page
- Commit A (backend explainability)
- Commit A.5 (feedback correctness)
- Commit A.5.1 (re-label correctness)
- Commit B (frontend explainability)

Chat 2 (F4 + F5a) — Cron observability shipped 2026-05-16.
Chat 3 (F6 + F5b + F10) — Stateful feedback shipped 2026-05-17.
Chat 4 (F2b + F14 + F2 backend + F2 frontend) — Sell-side fully shipped 2026-05-17/18/20.
Chat 5 (Audit + cleanup) — fully SHIPPED 2026-05-24. Eight commits + two manual EC2 steps + one infra step + four doc deliverables.
Chat 5.5 (Small TD cleanup) — TD9 + TD11 + TD12 SHIPPED 2026-05-24; TD10, TD14 carried.
Chat 5.6 (Robustness pass) — Pydantic round-trip + ge=0 + SPLIT/BONUS preview + TD13 doc. Baked into HEAD `c6b1437b` / `4f31b49`.
Chat 5.7 (Doc reconciliation) — Project_State.md full-file refresh, file-map repairs, new URL-at-SHA rule. SHIPPED.
Chat 5.8 (Review + master plan) — comprehensive code review (28 findings: 5 P1, 14 P2, 9 P3); master_todo.md created as canonical task list. SHIPPED (THIS commit).

### Chat split plan — SOURCE OF TRUTH is `docs/master_todo.md`

The chat split plan now lives in `docs/master_todo.md`. The table below is a snapshot for context; refer to master_todo.md for the live ordering and status.

| Phase | Items | Chat focus | Status |
|---|---|---|---|
| 1 | master_todo #1-3 | Ops unblock + doc reconciliation (TD14, TD10, TD15) | OPEN |
| 2 | master_todo #4-8 | Transactions/holdings/audit invariants | OPEN |
| 3 | master_todo #9-11 | Intraday & price correctness | OPEN |
| 4 | master_todo #12-13 | Storage hygiene | OPEN |
| 5 | master_todo #14-18 | Frontend correctness + quick wins | OPEN |
| 6 | master_todo #19-24 | External-service hardening | OPEN |
| 7 | master_todo #25-26 | Reconciliation alerting + feedback direction | OPEN |
| 8 | master_todo #27-29 | Chat 6 (F1+F3), Chat 7 (F12+F15), Chat 8 (F13 watchlist) | OPEN |
| 9 | master_todo #30-38 | Cross-cutting cleanup before GO LIVE | OPEN |
| 10 | master_todo #39-41 | Chat 9 pre-launch cleanup (F11 + realized P&L hide + stop_loss) | OPEN |
| 11 | master_todo #42 | Chat 10 GO LIVE (F7 real data import) | OPEN |
| 12 | master_todo #43-45 | Deferred TDs (TD1, TD3, TD7) | DEFERRED |

### Open items CARRIED FORWARD past Chat 5.8

All open items are tracked in `docs/master_todo.md` with stable item numbers. Cross-references in this file (Sections 5, 6, 7, 8, 9, 11, 12, 18) use the `master_todo #N` form so the next chat can grep across both files.

The three highest-priority items per master_todo current position:
- **master_todo #1 (TD14):** Sunday cron flag fix. Operational. Restores weekly digest.
- **master_todo #2 (TD10):** Remove redundant log-truncation crontab line. Operational.
- **master_todo #3 (TD15):** F-number registry reconciliation. Pure docs. Should land before any code chat to avoid hallucination against unmapped F-references.

## Section 14: Conventions the assistant has repeatedly drifted on

The assistant has confused these multiple times. Memorize them.

- Port 8001 (Mac local), port 8000 (EC2). Always specify which.
- SSH-first for tests: every test block MUST begin with `ssh ubuntu@100.112.20.41` and run curls against `localhost:8000`.
- Commit-block-after-code: every code/file delivery MUST be followed by a paste-ready `git add .` + `git commit -m "..."` block.
- Project_State.md AND master_todo.md are ALWAYS complete full-file replacements.
- F6 two-mechanism feedback exclusion: `get_excluded_isins` at run-build AND `_build_user_action` at serialization. Both required.
- The 90-day rejected cooldown and 30-day acted soft-exclude are intentionally NOT env-configurable.
- F10 write-before-apply: `monitored_stocks_audit_service.log_change(...)` BEFORE `monitored_stocks.update_one(...)`. **The corresponding invariant for transactions is currently violated — master_todo #4.**
- Secrets path on EC2 is `/etc/portfolio-advisor/secrets.env`.
- `lib/api.ts` is hand-typed; `lib/api-types.ts` is gitignored.
- Mutations in frontend use `refetchQueries` (synchronous), NOT `invalidateQueries`. **Two outliers exist — master_todo #14.**
- `cn` helper at `@/lib/utils`. Format helpers at `@/lib/format`.
- Collections accessor: `from app.db.client import Collections`.
- Decimal128 vs Decimal: helpers in `app/models/_common.py`.
- Datetimes: UTC-naive in Mongo. IST in UI. `utcnow()` from `app/models/_common.py`. **Mixed tz-aware usage exists — master_todo #30 + #31 will sweep.**
- Heredoc for multi-line Python: use `<<'EOF'` form.
- Original `SuggestionCard` takes parent-owned mutation. Do not redesign.
- `/suggestions` page uses shadcn Tabs.
- Tailwind v4 + shadcn `.dark` class pickup is automatic.
- Every cron script: `cron_run()` wrapper AND `CronSpec` entry AND crontab line with log redirection.
- Direction-aware display layer: branch on direction at the display layer, not by forking the model.

### Chat 4 additions
- DO NOT trust Glean snippets or memory for dataclass / Pydantic model field names. Grep first.
- `cron_run()` yields `_Heartbeat`; `.meta` is an ATTRIBUTE.
- `/cron/heartbeats` returns `{heartbeats, health_summary}`.
- `Collections.instruments_fundamentals()` is the accessor name.
- `run_suggestions()` is SLOW by default; `--skip-dossiers` only for smoke tests.

### Chat 5 additions
- ASK FOR THE CURRENT BACKEND (and frontend if relevant) SHA BEFORE PROPOSING ANY CODE CHANGE. NO EXCEPTIONS.
- When a wrapper function's return shape or exception behavior changes, grep for ALL callers BEFORE shipping.
- `notify.email()` now returns `{ok, id, error}` and swallows Resend exceptions.
- GitHub raw-URL caching is a real failure mode. Use SSH+sed as ground truth.

### Chat 5 closure additions
- Doc rewrites must cross-check every cron/registry/file claim against actual on-disk state.
- Project_State.md structure is load-bearing. NEVER restructure it.
- Cron-health observability needs redundant transports.
- EC2 cron log retention uses logrotate since 2026-05-24.

### Chat 5.5 additions
- BEFORE writing any patch that documents what a script does, READ THE SCRIPT BODY at HEAD.
- BEFORE documenting or trusting a cron line, verify the script's argparse accepts the flags.
- For settings-side cleanup that touches both `settings.py` and `/etc/portfolio-advisor/secrets.env`, ship BOTH sides in ONE atomic commit + restart.
- Glean's snippet-mode rendering line-wraps at sentence boundaries; prefer `raw.githubusercontent.com` URLs.

### Chat 5.7 additions
- AT NO POINT make code changes while relying on memory. Construct GitHub URLs from `owner=doshisahil95`, `repo`, user-supplied SHA, `file_path` from tree listing.
- Ask the user to run the canonical tree-listing command at the start of every chat.
- When updating the file map (Sections 5 / 6), diff the previous file map against `ls-tree` output line-by-line.

### Chat 5.8 additions
- **`master_todo.md` is now the canonical task list.** Project_State.md describes WHAT THE SYSTEM IS; master_todo.md describes WHAT TO DO NEXT.
- **At the start of every chat, after reading Project_State.md, also read master_todo.md and confirm the current-position pointer with the user.** If today's scope says "work the next item", the next item is by definition the lowest-numbered OPEN row in master_todo.md.
- **When you ship an item, update master_todo.md status column AND advance the current-position pointer in the same commit as the code change.** Don't batch master_todo updates across chats — drift will return.
- **When a chat discovers a new bug/TD/feature mid-stream**, append it to the appropriate phase in master_todo.md (don't renumber existing items) so the next chat picks it up.
- **Cross-references from Project_State.md to master_todo.md use the form `master_todo #N`.** Stable across renames; safe to grep.

## Section 15: Anti-patterns the assistant has fallen into

- Full-file rewrites instead of additive patches. EXCEPTION: Project_State.md and master_todo.md are always full-file.
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
- Using `artifact_edit` on Project_State.md/master_todo.md instead of full-file artifact.
- Confusing the two F6 mechanisms.

### Chat 4 additions
- Guessing dataclass / model field names from Glean snippets without grep'ing.
- Writing multi-chunk plans without re-reading every touched file at HEAD before each chunk.
- Writing the same test block with three different wrong API response shapes.

### Chat 5 additions
- Trusting Project_State.md as the source of truth for "what's open" without verifying against code.
- Writing find-and-replace blocks from snippet memory or stale file reads.
- Changing a wrapper function's return shape or exception behavior without checking ALL callers first.

### Chat 5 closure additions
- Restructuring Project_State.md when the user said "preserve structure".
- Inventing cron entries / removing real ones in doc rewrites.
- Describing a script without reading its `main()` and the actual crontab.
- Skipping Section 0 when delivering Project_State.md.

### Chat 5.5 additions
- Proposing a script rename based on a file-map summary without reading the script body.
- Adding cron-line flags without running the script's `--help` first.
- Rendering an artifact with nested triple-backticks and assuming canvas display will work.

### Chat 5.7 additions
- Trusting the file map in Project_State.md as the source of truth for what exists on disk.
- Listing files in Sections 5/6 that don't exist.
- Capturing fix-ticket references (F-numbers) in code without mirroring them into Project_State.md.

### Chat 5.8 additions
- **Treating Project_State.md as a TODO list.** TODO ownership moved to master_todo.md in Chat 5.8. If a future chat lists open items inline in Project_State.md instead of master_todo.md, it has duplicated state and the two will drift.
- **Starting a chat without confirming the master_todo.md current-position pointer.** The user may want to skip ahead, work multiple items in parallel, or change phase order — confirm before assuming "next OPEN row" is correct.
- **Shipping code changes without also updating master_todo.md status in the same commit.** Status drift in master_todo.md is the #1 risk to long-term plan integrity.
- **Auditing code against memory of "what's open" instead of against master_todo.md + Project_State.md Section 18.** The Chat 5.8 code review surfaced 28 findings precisely because the prior assumption-based audits missed them.

## Section 16: "I am losing context" — escalation protocol

When the assistant notices ANY trigger, say verbatim:
```
I AM LOSING CONTEXT
```

### Triggers (any one is sufficient)
- Cannot recall a specific file structure that was discussed earlier in the chat
- Conflating Phase 1 facts with Phase 2 facts
- Forgetting which Commit (A, A.5, A.5.1, B) shipped which behavior
- Forgetting which Chat (2, 3, 4, 5, 5.5, 5.6, 5.7, 5.8) shipped which feature
- Producing a file >1.5x the original line count without explicit reason
- Starting to use generic patterns instead of project conventions
- Forgetting the port difference between Mac and EC2
- Forgetting the SSH-first or commit-block-after-code convention
- Forgetting the secrets path
- Forgetting that master_todo.md is the canonical task list (Chat 5.8)
- The user has to correct the same drift twice in the same chat
- The assistant has called Glean reader or code_search >15 times without converging
- The "Truncation Notice" appears in the assistant's context
- About to produce a third large code artifact and unsure whether prior decisions still apply
- Chat 4 trigger: shipped two+ patches with WRONG field names
- Chat 4 trigger: shipped a test block with WRONG API response shape
- Chat 5 trigger: claimed "open" item is open without re-reading on-disk code
- Chat 5 trigger: proposed a find-and-replace block whose `original_text` doesn't exist verbatim
- Chat 5 trigger: changed a wrapper function's return shape without grep'ing for callers
- Chat 5 closure trigger: about to publish a doc rewrite with unverified cron/registry/file claims
- Chat 5 closure trigger: about to restructure Project_State.md
- Chat 5.5 trigger: about to propose a script rename based on a summary without reading the body
- Chat 5.5 trigger: about to document a cron line without running `--help`
- Chat 5.7 trigger: about to patch a file whose existence on disk isn't confirmed via tree listing
- Chat 5.7 trigger: about to construct a GitHub URL using a SHA not supplied this chat
- **Chat 5.8 trigger: about to ship code without updating master_todo.md status in the same commit.**
- **Chat 5.8 trigger: starting a code chat without having confirmed master_todo.md current-position pointer with the user.**

### What "switching chats" means
The user copies the Section 0 bootstrap into a fresh chat. The new chat reads Project_State.md, master_todo.md, both repos at HEAD, `data_flow.md`, READMEs. User states scope. Assistant summariz