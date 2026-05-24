
# PROJECT_STATE.md

Living source of truth for the Personal AI Stock Advisor. Updated at the end of every chat.

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
- Hand me full file contents OR exact find-and-replace. Never "rest unchanged".
- Use canvas artifacts for files. Use chat for tests.
- Project_State.md is ALWAYS delivered as a complete full-file replacement,
  never as a patch, find-and-replace, or "rest unchanged". No exceptions,
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
- BEFORE writing any patch that documents what a script does, READ THE
  SCRIPT BODY at HEAD. File-map / README / data_flow summaries can drift
  away from the actual code (TD12 in Chat 5.5 was exactly this: the script
  was correctly named all along; three docs all claimed "actually seeds
  top 250" — a hallucination that originated in a Chat-5 file-map summary
  and propagated). (See Section 14.)
- BEFORE documenting a cron line, verify the script's argparse accepts the
  flags. The Sunday 07:00 IST `run_weekly_suggestions.py` crontab line had
  `--notify --run-type scheduled` for weeks; neither flag exists on the
  script. argparse rejected every Sunday run, no digest fired. Caught
  Chat 5.5; logged as TD14. (See Section 14.)
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

The goal of the system is to maximise the investments.

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
- Project_State.md is ALWAYS delivered as a complete full-file replacement, never a patch or diff or find-and-replace. No exceptions.
- ASK FOR CURRENT BACKEND SHA BEFORE PROPOSING ANY CODE CHANGE. Re-read the file at that SHA before writing the patch. (Chat 5 standing convention; see Section 14.)
- BEFORE documenting what a script does, read its body at HEAD; before documenting a cron line, verify the script's argparse accepts the flags. (Chat 5.5 standing conventions; see Section 14.)

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
- Resend (transactional email for digests, drift alerts, smoke tests, cron-health alerts — all routed through `notify.email()` as of Chat 5 A2; cron-health email transport added Chat 5 commit 8)
- ntfy (push notifications — public ntfy.sh for all paths; self-hosted private service stopped 2026-05-18 during F2b deploy and code removed Chat 5 commits 7a/7b 2026-05-23, TD8 SHIPPED; the three orphan `NTFY_URL` / `NTFY_USER` / `NTFY_PASS` settings + secrets-file keys removed Chat 5.5 commit 1 2026-05-24, TD9 SHIPPED)

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

This Mac vs EC2 port difference is a real, recurring source of confusion for assistants. The assistant has gotten this wrong multiple times. Always specify which machine when giving test commands.

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

The `Settings` class uses pydantic-settings with `model_config = SettingsConfigDict(env_file=str(SECRETS_FILE), env_file_encoding="utf-8", case_sensitive=True, extra="ignore")`. Pydantic-settings reads the file directly into the `Settings` object — secrets are NOT exported to `os.environ`.

If the assistant ever suggests `~/secrets/secrets.env` on EC2, it is wrong. That path was a transient debug artifact.

F2b addition (Chat 4): `NTFY_PUBLIC_TOPIC_DIGESTS` must be present in `/etc/portfolio-advisor/secrets.env` — required (no default). If missing, app startup fails with a Pydantic validation error. Subscribe the iPhone ntfy app to the topic value before running cron.

Chat 5 reminder: when rotating the Atlas password, update BOTH `secrets.env` files (EC2 and Mac) in the same session. URL-encode any password containing `@ : / ? # [ ] ! % & = +` via `python3 -c "from urllib.parse import quote_plus; print(quote_plus('PASTE'))"`. Atlas shows the new password only once after generation; losing it forces another rotation.

Chat 5.5 TD9 SHIPPED (commit 1, 2026-05-24): `NTFY_URL`, `NTFY_USER`, `NTFY_PASS` were orphan post-TD8. Both sides cleaned up in one atomic commit + restart: settings.py fields removed AND the four lines (`# ntfy` header + the three KEY=VALUE lines at lines 10-13) sed-deleted from `/etc/portfolio-advisor/secrets.env`. Backup written to `secrets.env.bak.<timestamp>` before sed. Verified: `/health` ok, no Pydantic validation error in journald, smoke_test all green.

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

### Log rotation (Chat 5 SHIPPED 2026-05-24)

`/etc/logrotate.d/portfolio-advisor` rotates all `/home/ubuntu/cron-*.log` weekly:
- `rotate 4` — keep 4 weeks of history
- `compress` + `delaycompress` — gzip rotated files (newest rotation stays uncompressed for grep-friendliness)
- `notifempty` + `missingok` — silent on empty / missing logs
- `copytruncate` — required because the cron `>>` redirects don't reopen file handles
- `su ubuntu ubuntu` — required because target dir is `/home/ubuntu` (not root-owned)

Daily logrotate cron is the OS-provided `/etc/cron.daily/logrotate` (no project-side cron entry needed). Force-rotate any time with `sudo logrotate -f /etc/logrotate.d/portfolio-advisor`.

The pre-existing `0 0 * * 0 find ... -size +10M ... tail -10000 ...` crontab line still exists alongside logrotate. It is now redundant (logrotate runs weekly regardless of size and is more thorough). Removal scheduled as TD10 — gated on confirming one full weekly logrotate cycle through `/etc/cron.daily/logrotate` (next trigger: Sunday 2026-05-31 00:00 IST window; verify week of 2026-06-01 then drop the line via `crontab -e`).

### Repos
- Backend: https://github.com/doshisahil95/ai-stock-advisor-backend
- Frontend: https://github.com/doshisahil95/ai-stock-advisor-frontend

GitHub is the source of truth for code. GitHub may serve cached content via Glean's reader. When in doubt, find the latest commit SHA and read at that SHA explicitly. Chat 5 lesson: when the raw URL also serves cached content, `ssh ubuntu@100.112.20.41 'sed -n "1,30p" <path>'` is the verification of last resort.

Last verified SHAs (Chat 5.5 closed, 2026-05-24):
- Backend: `b8228380e4236bdc947c419a09fd6a44e81f4d69` (post-Chat-5.5 commits 1-3: TD9 settings cleanup + TD11 explainability wire + TD12 doc correction; will advance after this PROJECT_STATE commit lands — pin in Chat 6's first read)
- Frontend: `9edfc8f12a2071744c4d445d679811b1cde62058` (Chat 5 doc deliverable 3/4 — frontend README rewrite; per-page reference TD13 still OPEN)

## Section 5: Backend file map

Directory layout under `app/`:

```
app/
  main.py                     FastAPI bootstrap, router includes, lifespan
  config/
    settings.py               pydantic-settings, loads secrets file
                              F2b: NTFY_PUBLIC_TOPIC_DIGESTS (required)
                              Chat 5.5 TD9 SHIPPED (commit 1, 2026-05-24):
                              NTFY_URL, NTFY_USER, NTFY_PASS field
                              declarations removed in lockstep with the
                              EC2 secrets-file cleanup. No remaining
                              callers (push_private + PrivateTopic removed
                              TD8 commits 7a/7b).
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
                              time via pydantic ValidationError). See Section 12.
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
                              flips. $setOnInsert seeds added_by,
                              added_reason, _schema_version.
                              Chat 5 A19 SHIPPED (commit 6, 2026-05-23) —
                              three Query() calls migrated from regex=
                              to pattern= (Pydantic v2 deprecation).
                              Behaviour unchanged.
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
    reconciliation.py         take_auto_snapshot, drift detection,
                              _send_drift_alerts (helper sends ntfy + email)
                              Chat 5 A2 part 2 SHIPPED (commit 1, 2026-05-23):
                              _send_drift_alerts now branches on
                              notify.email() result["ok"] before
                              sent.append("email"). The dead try/except
                              around the now-non-raising wrapper is gone.
                              Also passes text=body_text for proper
                              multipart/alternative.
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
                              Chat 5 A3+A4 SHIPPED (commit 2, 2026-05-23):
                              composite_for_candidate now accepts optional
                              candidate_signals_for_isin and writes the RAW
                              input from extract_signals into
                              SignalScore.raw_value. Both buy
                              (score_candidates) and sell
                              (score_sell_candidates) call sites updated
                              in the same commit. News raw values
                              (net_sentiment*100, story_velocity,
                              story_count) now land in SignalScore.raw_value
                              as a side effect — closes A4. Back-compat
                              fallback preserves historic (incorrect)
                              behaviour when no raw_signals dict is passed.
                              Chat 5 A5 SHIPPED (commit 2, 2026-05-23):
                              stale DEFAULT_CONFIG.gates comment refreshed
                              to describe current shared buy+sell behaviour.
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
                              Chat 5 A17 SHIPPED (commit 5, 2026-05-23):
                              stale pre-chunk-6 NOTE in _run_sell_pipeline
                              refreshed to describe current --direction=both
                              vs standalone --direction=sell behaviour.
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
                              Chat 5 TD8 follow-up (commit 7a, 2026-05-23):
                              F2b docstring updated to reflect that
                              push_private was removed from notify.py (was:
                              "push_private remains for future use").
    explainability.py         SIGNAL_META, GROUP_META, GATE_META, FEEDBACK_META,
                              PAGE_INTRO + PAGE_INTRO_SELL, enrich_run,
                              enrich_candidate;
                              _load_monitored_bulk + _build_user_action (F6)
                              F2: SIGNAL_META extended (unrealized_gain_pct,
                              target_price_proximity, portfolio_weight_pct,
                              is_ltcg_eligible, high_severity_negative_count).
                              GROUP_META extended (booking_opportunity,
                              valuation_stretch, risk, tax_concentration).
                              GATE_META extended (earnings_proximity,
                              in_profit, min_position_age).
                              _GROUP_TO_SIGNALS extended for sell groups.
                              Chat 5 A18 NOTE: shipped before Chat 5 (verified
                              at SHA d3f307a during the Chat 5 audit) —
                              BUY_PAGE_INTRO / SELL_PAGE_INTRO + direction
                              branch in enrich_run are present.
                              Chat 5.5 TD11 SHIPPED (commit 2, 2026-05-24):
                              _build_signal_meta now falls back to
                              sig["raw_value"] (parsed via _to_float, rendered
                              via _format_raw) when meta["fundamentals_field"]
                              is None and sig["available"] is True. Stale
                              line-116 comment "News signals (raw values not
                              persisted post-run; we show normalized only)"
                              refreshed to describe post-A3+A4 reality.
                              SIGNAL_META formatter_kind switched: news_net_
                              sentiment → score_signed (signed 1-decimal),
                              news_story_velocity → ratio, news_story_count
                              → count (integer), high_severity_negative_count
                              → count. is_ltcg_eligible deliberately kept on
                              score_only (binary semantic; dossier carries
                              meaningful value). Two new _format_raw kinds
                              added: score_signed (`f"{raw:+.1f}"`) and
                              count (`f"{int(raw)}"`).
    notify.py                 push_public, email
                              Chat 5 A2 part 1 SHIPPED: email() now accepts
                              optional `text=` param for multipart, returns
                              {ok, id, error} instead of raw resend dict.
                              All Resend traffic in the backend flows
                              through this wrapper. Callers:
                              digest_delivery._send_email (delegates),
                              reconciliation._send_drift_alerts (Chat 5 A2
                              part 2 wired correctly to result["ok"]),
                              cron_health_check.main (Chat 5 commit 8 —
                              dual-transport alongside push_public),
                              scripts/smoke_test.py (uses .get('id')).
                              PublicChannel = "price" | "news" | "errors" |
                              "digests".
                              Chat 5 TD8 SHIPPED (commits 7a + 7b,
                              2026-05-23): push_private function +
                              PrivateTopic Literal + _NTFY_AUTH constant +
                              `from base64 import b64encode` import all
                              removed. Self-hosted ntfy service was stopped
                              on EC2 2026-05-18T11:01:12 IST during F2b
                              deploy; commits 7a/7b cleaned up the orphan
                              code 2026-05-23.
    cron_heartbeat_service.py F4: cron_run context manager, CRON_REGISTRY,
                              get_recent_heartbeats, get_latest_per_cron,
                              count_today_heartbeats, ist_today_window_utc,
                              is_expected_today
                              F2: CRON_REGISTRY includes
                              "weekly_suggestions_sell" CronSpec (idle in
                              current --direction=both deployment;
                              retained for topology flexibility).
                              CONVENTION (Section 14): CronSpec fields are
                              (cron_name, description, schedule_human,
                              expected_weekdays, min_runs_per_day=1). Three
                              field-name drifts in Chat 4 produced this rule.
                              Chat 5 A6 SHIPPED (commit 3, 2026-05-23):
                              weekly_suggestions CronSpec schedule_human
                              now "Sunday 07:00 IST" (was 06:00, drifted
                              from the actual `0 7 * * 0` crontab).
                              Chat 5 A6.5 SHIPPED (commit 3, 2026-05-23):
                              refresh_instruments CronSpec description now
                              "Refresh NSE master from NSE EQUITY_L.csv"
                              (was "Zerodha Kite"; same drift as A13).
                              Chat 5 A7 SHIPPED (commit 3, 2026-05-23):
                              unused SATURDAY = {5} constant removed.
scripts/
  init_db.py
  refresh_instruments.py        Chat 5 A13 SHIPPED (commits 4 + 4b,
                                2026-05-23): docstring rewritten to
                                describe NSE EQUITY_L.csv source via
                                refresh_from_nse(). The first attempt
                                (commit 4) included a "does not use
                                Zerodha Kite Connect" disclaimer that
                                tripped grep-based audits looking for
                                stale Kite references; commit 4b
                                removed the disclaimer for cleanliness.
  refresh_prices.py
  refresh_prices_intraday.py
  take_reconciliation_snapshot.py
  seed_nifty100.py              CORRECTLY NAMED. Reads NSE's official
                                ind_nifty100list.csv from nsearchives,
                                marks matched NSE instruments with
                                in_nifty100=True + nifty100_marked_at,
                                backfills 5y EOD price history for
                                newly-tagged ISINs. No CLI flags
                                (--dry-run / --replace never existed).
                                Chat 5.5 TD12 RESOLVED-as-doc-fix (commit
                                3, 2026-05-24): the "actually seeds top
                                250 NSE by market cap" claim was a doc
                                hallucination that propagated into the
                                Chat-5 file-map summary, README §8 entry,
                                README §11 gotcha #1, and data_flow.md
                                "Universe + fundamentals refresh"
                                paragraph. All four locations corrected;
                                no rename, no code change.
  seed_cost_basis_adjustments.py
  import_orderbooks.py
  reconcile_staging.py
  promote_staging.py
  add_manual_transactions.py
  refresh_fundamentals.py        F14: default universe is NIFTY 100 ∪
                                 active holdings (held stocks outside
                                 NIFTY 100 also need fresh fundamentals
                                 for F2 sell-side scoring); folds
                                 earnings refresh into the same Sunday
                                 cron via refresh_earnings_universe.
                                 --holdings-only and --symbols overrides
                                 preserved.
  fetch_news_for_universe.py     Chat 5 A16 SHIPPED MANUAL (2026-05-24):
                                 EC2 crontab line now passes
                                 --include-held. Verified via
                                 `crontab -l | grep fetch_news_for_universe`.
                                 The CLI flag itself was already
                                 implemented; the cron line was missing it,
                                 which silently produced thin sell-side
                                 news signals for held names.
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
                                 TD14 (Chat 5.5, OPEN): the EC2 crontab
                                 line currently passes `--notify --run-type
                                 scheduled` — NEITHER flag exists on this
                                 script's argparse. argparse rejects the
                                 line every Sunday with usage error;
                                 cron-suggestions.log is 221 bytes (just
                                 the error). Sunday digest has not fired
                                 in weeks. Fix: `crontab -e` and delete
                                 the two bogus flags. See Section 9
                                 PENDING + Section 18 TD14.
  track_suggestion_outcomes.py   Runs Mon-Fri 19:45 IST per cron (NOT
                                 "on demand" as earlier doc claimed).
                                 Outcome snapshot lookup for the
                                 /suggestions/performance endpoint.
  cron_health_check.py           F4: daily 21:00 IST; reads CRON_REGISTRY +
                                 today's heartbeats; fires a batched alert
                                 on TWO independent transports if any
                                 expected cron is missing/failed.
                                 Chat 5 commit 8 SHIPPED (2026-05-23):
                                 dual-transport (push_public("errors",...)
                                 + notify.email()); raises only when BOTH
                                 transports fail. Original "raise so
                                 cron_run records failure for tomorrow"
                                 intent preserved. The script ITSELF
                                 writes a heartbeat via
                                 cron_run("cron_health_check") (it IS a
                                 producer, not consumer-only — earlier
                                 backend README claimed otherwise; that
                                 was wrong and was corrected post-commit).
  smoke_test.py                  end-to-end smoke: Anthropic ping, ntfy
                                 public, Resend. Uses email_resp.get('id')
                                 so safe under both old and new
                                 notify.email() return shapes.
                                 Chat 5 TD8 follow-up (commit 7a,
                                 2026-05-23): dropped push_private import
                                 + private-ntfy test block + iPhone
                                 expectation bullet that referenced the
                                 private channel.
docs/
  data_flow.md                  Chat 5 doc deliverable 1/4 SHIPPED
                                (2026-05-23) — full rewrite covering
                                Phase 1 + Phase 2. Replaces the prior
                                2026-05-09 Phase-1-only version. Doc
                                corrections (cron table + logrotate notes
                                + track_suggestion_outcomes schedule)
                                followed in a second commit 2026-05-24.
                                Chat 5.5 TD12 SHIPPED (commit 3,
                                2026-05-24): "Universe + fundamentals
                                refresh" paragraph corrected — the
                                buy-side universe is NIFTY 100 ∪ active
                                holdings, NOT "top 250 by market cap".
  Project_State.md              THIS FILE
pyproject.toml
README.md                       Chat 5 doc deliverable 2/4 SHIPPED
                                (2026-05-23) — full operator manual
                                rewrite (~600 lines, 12 sections).
                                Post-Chat-5 corrections (heartbeat-self,
                                track_suggestion_outcomes schedule,
                                cron_health_check dual-transport, logrotate
                                step) followed in a second commit 2026-05-24.
                                Chat 5.5 TD12 SHIPPED (commit 3,
                                2026-05-24): §8 entries for
                                seed_nifty100.py + refresh_fundamentals.py
                                + §11 gotcha #1 + §5 orphan-NTFY
                                subsection corrected for post-Chat-5.5
                                reality.
```

(Frontend file map unchanged from prior version; no frontend code touched in Chat 5 beyond the README rewrite — see Section 6 + Chat 5.5 status in Section 13. TD13 frontend per-page reference still OPEN, deferred pending route-file reads at SHA.)

## Section 6: Frontend file map

Directory layout (unchanged from prior version — no frontend code touches in Chat 5 or Chat 5.5; the only frontend deliverable was a full README.md rewrite at SHA `9edfc8f`; TD13 per-page section still OPEN):

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
README.md                     Chat 5 doc deliverable 3/4 SHIPPED (2026-05-23,
                              frontend SHA 9edfc8f) — operator manual rewrite
                              (~220 lines, 12 sections). Per-page reference
                              section intentionally DEFERRED to TD13 because
                              Glean reads of the route files failed during
                              the doc pass; would have required guessing
                              TanStack Query keys + mutation refetch patterns.
```

## Section 7: Database collections (exhaustive)

All collections live in MongoDB Atlas M10. The DB name is set by env (`MONGODB_DB_NAME`). All collections accessed via `Collections.<name>()` from `app.db.client`. Indexes ensured at startup via `app/db/indexes.py`.

### Phase 1 collections

#### `instruments`
- Master NSE/BSE instrument list, refreshed daily from NSE's official `EQUITY_L.csv`
- Key fields: `exchange`, `symbol`, `isin`, `name`, `instrument_type`, `segment`, `lot_size`, `tick_size`, `source`, `last_seen_at`, `last_changed_at`, `in_nifty100`, `nifty100_marked_at`
- Count: ~2,368 total; ~100 with `in_nifty100=True` (NIFTY 100 constituents per NSE's official `ind_nifty100list.csv`)
- Indexes: `(exchange, symbol)` unique, `isin`, `last_seen_at`, `last_changed_at`, `in_nifty100`
- Writer: `scripts/refresh_instruments.py` (delta-aware, `refresh_from_nse()`), `scripts/seed_nifty100.py` (sets `in_nifty100=True` on matched ISINs), manual upserts for BSE-only stocks

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
- F2 (Chat 4): `target_price` is now consumed by sell-side scoring (`target_price_proximity` signal in `booking_opportunity` group). `stop_loss` will be wired by user direction (TD6 — deferred to Chat 9 as new feature work).

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
- Count: ~115,791 docs across ~100 NIFTY 100 ISINs (~1,158 per stock), plus held ISINs outside NIFTY 100
- Indexes: `(isin, date)` unique
- Writer: `scripts/refresh_prices.py` (yfinance); also seeded for newly-tagged NIFTY 100 ISINs by `scripts/seed_nifty100.py` (5y backfill on first mark)

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
- Chat 5 A1 SHIPPED: model schema now matches writer reality. Old `Literal["tracking", "promoted_to_holding", "dropped"]` was removed; `"watchlist"` added ahead of F13. Feedback fields declared on the model. `symbol` downgraded to optional default `""`. Collections wiped during the A1 deploy (Q1 resolved: data was throwaway test data).
- INVARIANT (Chat 5 A1): writes go through `routers/suggestions.submit_feedback`, which constructs a `MonitoredStockFeedbackPatch(...)` Pydantic model with `ConfigDict(extra="forbid")` and `$set`-s `patch.model_dump(exclude_none=True)`. `$setOnInsert` seeds `added_by="user_explicit"`, `added_reason="feedback action"`, `_schema_version=1`, `created_at=now`.
- INVARIANT (F10): every write is preceded by `monitored_stocks_audit_service.log_change(...)`. Audit row lands BEFORE the `update_one` apply.
- Consumer: `suggestion_engine.get_excluded_isins()` (renamed Chat 3) returns three buckets: `rejected` (90d), `passed` (this run only), `acted` (30d soft-exclude, F5b).
- Consumer: `explainability._build_user_action()` at serialization time stamps each enriched candidate with `user_action` + timestamp.
- F2 (Chat 4): direction-agnostic. Acceptable for v1; add a `direction` column if it bites in practice (TD1).
- Indexes: `isin` unique (PARTIAL — `partialFilterExpression={"status": "tracking"}`), `(status, rejected_at)`. A14 closed by A1.

#### `monitored_stocks_audit` (F10 — shipped Chat 3)
- Append-only audit log for `monitored_stocks` writes; one doc per `POST /suggestions/{isin}/feedback`
- Key fields: `isin`, `action` (`"acted"|"passed"|"rejected"`), `previous_status` (string or null), `new_status`, `note`, `performed_at`, `_schema_version` (1)
- INVARIANT: append-only. Writer (`monitored_stocks_audit_service.log_change`) invoked BEFORE the corresponding `monitored_stocks.update_one`.
- Indexes: `(performed_at desc)`, `(isin, performed_at desc)`
- Writer: `app/services/monitored_stocks_audit_service.py`
- Consumer: `GET /suggestions/{isin}/audit`, `GET /suggestions/feedback/audit/recent?limit=N`

#### `instruments_fundamentals`
- One doc per ISIN per fundamentals refresh (so we have history)
- Key fields: `isin`, `symbol`, `as_of` (date), `fetched_at` (datetime), `market_cap`, `pe_ratio`, `pb_ratio`, `dividend_yield`, `return_on_equity`, `return_on_assets`, `operating_margin`, `debt_to_equity`, `earnings_growth_yoy`, `revenue_growth_yoy`, `beta`, `fifty_two_week_high`, `fifty_two_week_low`, `sector` (yfinance), `industry`, `source`, `source_raw` (full yfinance dict for replay), `fields_present`, `fields_missing`
- Indexes: `isin_latest_unique` (unique, latest only via `(isin, fetched_at desc)`), `fetched_at`
- Writer: `scripts/refresh_fundamentals.py` → `fundamentals_service.refresh_one`. F14: default universe is NIFTY 100 ∪ active holdings.
- Consumer: `suggestion_engine` (scoring), `explainability.py` (post-TD11: still primary source for signals with `meta["fundamentals_field"]` populated; momentum/news/sell-side-holding signals now fall back to `sig["raw_value"]` via the Chat-5.5 commit-2 wire)

#### `earnings_calendar` (F14 — shipped Chat 4)
- Upcoming + historical earnings events per ISIN. Source = yfinance `Ticker.calendar`, refreshed weekly alongside fundamentals.
- Key fields: `isin`, `symbol`, `exchange`, `earnings_date` (tz-naive datetime), `source` ("yfinance"), `source_raw` (sanitized yfinance calendar dict), `fetched_at`, `created_at`
- INVARIANT (refresh semantics): `refresh_earnings_for(isin, symbol, exchange)` deletes ALL future events (>= today) then re-inserts. Past events immutable.
- INVARIANT (BSON sanitization): `_sanitize_for_bson` coerces date→datetime, tz-aware→naive, Timestamp/numpy scalars→native, unknown→`str()`. Applied to `source_raw` before insert.
- Indexes: `(isin, earnings_date)` unique, `(earnings_date asc)`, `(isin)`, `(fetched_at desc)`
- Writer: `fundamentals_service.refresh_earnings_for` (single ISIN), `refresh_earnings_universe` (bulk)
- Consumer: `get_next_earnings_for_isin` / `get_next_earnings_bulk`; `suggestion_engine` (buy + sell); `scoring_service.evaluate_earnings_proximity_gate` (skip trades within 5 days of an event)

#### `news_articles`
- Classified news per article; one doc per URL with `$addToSet`-merged `entities_isins`
- Key fields: `url` (unique), `title`, `published_at`, `fetched_at`, `source`, `body` (purged after classification), `body_purged_at`, `entities_isins` (list), `themes` (Literal), `sentiment`, `sentiment_confidence`, `severity`, `classifier_summary`, `classified` (bool)
- Indexes: `url` unique, `(entities_isins, classified, fetched_at)`, `(classified, fetched_at)`
- Writer: `news_fetcher.py` (fetch) then `news_classifier.py` (classify; `BATCH_SIZE=25`, `RETRY_PASS_BATCH_SIZE=3`)
- Consumer: `news_signals.py`, `dossier_service.py`
- Chat 5 A16 SHIPPED MANUAL: EC2 crontab now passes `--include-held` so sell-side coverage works.

#### `suggestion_runs`
- Append-only history of every weekly run
- Key fields: `_id`, `_schema_version`, `run_date`, `run_date_ist`, `run_type` (scheduled/manual), `direction` (`"buy"`|`"sell"`, default `"buy"`), `status` (success/partial/failure), `started_at`, `finished_at`, `error`, `universe_size`, `excluded_held`, `excluded_rejected`, `excluded_passed` (F6), `excluded_acted` (F5b), `excluded_stale_data`, `candidates_considered`, `candidates_post_gates`, `config`, `top_candidates`, `all_candidates`, `top_k`, `notes` (JSON string containing dossiers array)
- INVARIANT: append-only; never updated.
- INVARIANT: `top_candidates[*].user_action` is NOT in the persisted doc. Added at API serialization time by `enrich_run` only.
- INVARIANT (F2): pre-F2 runs persisted without a `direction` key still load cleanly via Pydantic default = `"buy"`.
- Indexes: `(run_date desc)`, `(run_date_ist, run_type)`, `(status)`

#### `suggestion_outcomes`
- One doc per top-K candidate per run; tracks actual stock + benchmark over 30/60/90/180-day windows
- Key fields: `isin`, `symbol`, `suggestion_run_id`, `suggested_at`, `suggested_at_price`, `suggested_rank`, `suggested_composite_score`, `tracking_status` (open/acted/passed/rejected/expired), `direction`, `price_at_30d/60d/90d/180d`, `nifty_at_30d/60d/90d/180d`, `excess_return_30d/60d/90d/180d`, `user_action_at`, `user_action_note`, `created_at`, `updated_at`
- INVARIANT (A.5): snapshot eligibility is `tracking_status != "expired"`.
- INVARIANT: auto-flip to `"expired"` only at day 180 if still labeled `"open"`. User-set labels never overwritten.
- INVARIANT (F2): `compute_system_performance(direction="sell")` sign-flips `excess_return` at aggregation.
- Indexes: `(isin, suggested_at desc)`, `(suggested_at desc)`, `(tracking_status)`, `(suggestion_run_id)`
- Writer: `outcome_tracker.create_outcomes_for_run` (stamps direction), `snapshot_open_outcomes` daily (direction-agnostic)

#### `tavily_quota`
- One doc per UTC day; counters incremented atomically
- Key fields: `date` (YYYY-MM-DD string), `total_calls`, `total_credits`, `per_use_case.<name>.calls`, `per_use_case.<name>.credits`
- Indexes: `date` unique
- Writer: `tavily_client.py` `$inc` updates with upsert
- INVARIANT: `TAVILY_DAILY_CALL_LIMIT` (default 200) enforced; raises `TavilyQuotaExceeded` when hit

#### `digest_deliveries`
- Audit log of weekly digest emails + ntfy pushes
- Key fields: `run_id`, `run_date_ist`, `sent_at`, `top_count`, `subject`, `email_ok`, `email_id`, `email_error`, `ntfy_ok`, `ntfy_status`, `ntfy_error`
- F2 (Chat 4): for combined-digest sends (`--direction=both` cron path), the row attaches to the BUY run id.
- Indexes: `(sent_at desc)`, `(run_id)`
- Writer: `digest_delivery.send_weekly_digest` or `digest_delivery.send_combined_digest`. Chat 5 A2 part 1: `_send_email` now delegates to `notify.email()`.
- TD14 IMPACT (Chat 5.5, OPEN): no rows have been written by the Sunday cron in weeks because `run_weekly_suggestions.py --notify --run-type scheduled` fails argparse before any code runs. See Section 18 TD14.

#### `cron_heartbeats` (F4 — shipped Chat 2)
- One doc per cron run with start/finish/status/error/metadata
- Key fields: `cron_name`, `started_at`, `finished_at`, `status`, `error`, `metadata`, `_schema_version`
- INVARIANT: append-only. Wrapper writes exactly one doc per run on exit.
- INVARIANT: heartbeat write is best-effort.
- INVARIANT (Chat 4): the context manager yields a `_Heartbeat` object that exposes `.meta` as an ATTRIBUTE. Set via `ctx.meta = {...}` or `ctx.meta[key] = value`.
- `"skipped"` counts as healthy in the daily check.
- Indexes: `(cron_name, started_at desc)`, `(started_at desc)`, TTL on `started_at` (60 days)
- Consumer: `GET /cron/heartbeats` router; `scripts/cron_health_check.py`
- TD14 IMPACT (Chat 5.5, OPEN): the `weekly_suggestions` heartbeat has not been written since the bogus crontab flags were added. `cron_health_check` should be flagging this nightly via dual-transport (Chat 5 commit 8). If the alert is silently being lost, that's a SECOND bug worth investigating.

### `digests` / `alerts_log` / `conversations` / `macro_signals`
Scaffolds; not actively written by current code. `conversations` will be used for chat features (F1, F3). Reserved; do not delete.

### Future collections (planned, not yet created)
- None pending. F11 is a read-only reformatter; F13 watchlist reuses `monitored_stocks` with `status="watchlist"`.

## Section 8: API endpoints (exhaustive)

(unchanged from prior version — Chat 5 + Chat 5.5 touched only writer implementations, response-shape internals (TD11 changes the rendered raw_value strings inside `signal_meta[*]`), Pydantic v2 migration, and doc text. No endpoint paths, methods, or top-level response shapes changed.)

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

Chat 5.5 TD11 IMPACT (no schema change, internal-data change only):
- `signal_meta[]` rows with `meta["fundamentals_field"] is None` (momentum / news / sell-side holding-specific) now carry `raw_value_formatted` rendered from `sig["raw_value"]` via `meta["formatter_kind"]`. Previously always `"—"`.
- Frontend `explain-popover.tsx` consumes `raw_value_formatted` directly; no frontend change needed.
- `is_ltcg_eligible` deliberately still renders `"—"` (formatter_kind kept as `score_only`); the dossier surface conveys LTCG eligibility meaningfully.

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

Run `crontab -l` to see current state. Every script below is heartbeat-instrumented via `cron_run()` and writes to `cron_heartbeats`. The daily `cron_health_check` at 21:00 IST consumes those heartbeats. `CRON_REGISTRY` in `cron_heartbeat_service.py` is the in-code mirror of this schedule — keep both in sync.

```cron
# Phase 1 crons (heartbeat-instrumented Chat 2)
0 3 * * * cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/refresh_instruments.py >> /home/ubuntu/cron-instruments.log 2>&1
0 19 * * 1-5 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/refresh_prices.py >> /home/ubuntu/cron-prices.log 2>&1
*/15 9-15 * * 1-5 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/refresh_prices_intraday.py >> /home/ubuntu/cron-prices-intraday.log 2>&1
30 19 * * 1-5 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/take_reconciliation_snapshot.py >> /home/ubuntu/cron-reconciliation.log 2>&1

# Phase 2 crons (registered Chat 2 via F5a — all heartbeat-instrumented)
0 6 * * 0 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/refresh_fundamentals.py >> /home/ubuntu/cron-fundamentals.log 2>&1
30 6 * * 0 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/fetch_news_for_universe.py --include-held >> /home/ubuntu/cron-news.log 2>&1
# TD14 (Chat 5.5, OPEN): the line below currently has `--notify --run-type scheduled` ON EC2, both of
# which fail argparse. Remove them via `crontab -e`. The line documented HERE is the CORRECT version
# (defaults: --notify is already implicit; --run-type was never a real flag); also `--no-notify` is
# the opposite-of-default opt-out for smoke tests.
0 7 * * 0 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/run_weekly_suggestions.py --direction=both >> /home/ubuntu/cron-suggestions.log 2>&1
45 19 * * 1-5 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/track_suggestion_outcomes.py >> /home/ubuntu/cron-outcomes.log 2>&1

# F4 cron health monitoring (added Chat 2; dual-transport Chat 5 commit 8)
0 21 * * * cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/cron_health_check.py >> /home/ubuntu/cron-health.log 2>&1

# Maintenance (legacy — superseded by /etc/logrotate.d/portfolio-advisor as of 2026-05-24)
# TD10 (Chat 5.5, OPEN): remove this line once logrotate-based retention is verified across one full
# cycle. First scheduled rotation: Sun 2026-05-31 00:00 IST window via /etc/cron.daily/logrotate.
# Verify week of 2026-06-01, then drop the line.
0 0 * * 0 find /home/ubuntu -maxdepth 1 -name "cron-*.log" -size +10M -exec sh -c 'tail -10000 "$1" > "$1.tmp" && mv "$1.tmp" "$1"' _ {} \;
```

CHAT 5 PENDING ONE-TIME EC2 STEPS (all closed 2026-05-24):
- Sunday 07:00 IST line uses `--direction=both --notify --run-type scheduled`: CONFIRMED via `crontab -l` — but those last two flags are TD14, see below.
- Sunday 06:30 IST `fetch_news_for_universe.py` line includes `--include-held` (A16): SHIPPED 2026-05-24.
- Self-hosted private ntfy service stopped + disabled (TD8): SHIPPED 2026-05-18 / code cleanup 2026-05-23.
- `/etc/logrotate.d/portfolio-advisor` installed: SHIPPED 2026-05-24.

CHAT 5.5 PENDING ONE-TIME EC2 STEPS:
- **TD10**: remove the `0 0 * * 0 find ... -size +10M ...` line via `crontab -e` AFTER the first full logrotate cycle completes (next: 2026-05-31; verify 2026-06-01).
- **TD14**: remove the bogus `--notify --run-type scheduled` flags from the Sunday 07:00 IST line via `crontab -e`. NEITHER flag exists on `run_weekly_suggestions.py` argparse. argparse rejects every Sunday run with a usage error. cron-suggestions.log is 221 bytes (just the error). No digest has fired in weeks. Fix: open `crontab -e`, change the line to the version documented in the block above (drop the two bogus flags). Optional recovery to send a digest now (rather than waiting for next Sunday):
  ```bash
  ssh ubuntu@100.112.20.41
  cd /home/ubuntu/ai-stock-advisor-backend
  PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/run_weekly_suggestions.py --direction=both 2>&1 | tee -a /home/ubuntu/cron-suggestions.log
  ```
  Expect ~3-5 min (Sonnet dossiers); the digest email + ntfy push fire at the end.

`CRON_REGISTRY` (in code) entries (10 total):
- `refresh_instruments`, `refresh_prices`, `refresh_prices_intraday`, `take_reconciliation_snapshot`, `refresh_fundamentals`, `fetch_news_for_universe`, `run_weekly_suggestions`, `track_suggestion_outcomes`, `cron_health_check`
- `weekly_suggestions_sell` — kept in registry for the alternative two-cron topology; current prod path is `--direction=both`, so `weekly_suggestions_sell` is idle.

No silent failures: every cron registration must include log file paths AND heartbeat instrumentation AND a `CronSpec` entry. All three.

Cron-health dual transport (Chat 5 commit 8): `cron_health_check.py` sends every anomaly batch on TWO independent transports — `push_public("errors", ...)` + `notify.email(subject, html, text)` — and raises (so `cron_run` marks the run as failed) ONLY when BOTH fail. Motivated by a 2026-05-23 missing-iPhone-push incident.

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
- `NTFY_PUBLIC_URL` (default `"https://ntfy.sh"`)
- `NTFY_PUBLIC_TOPIC_PRICE`, `NTFY_PUBLIC_TOPIC_NEWS`, `NTFY_PUBLIC_TOPIC_ERRORS`, `NTFY_PUBLIC_TOPIC_DIGESTS`
- `NTFY_PUBLIC_TOPIC_DIGESTS` (F2b — REQUIRED, no default)
- All `NTFY_PUBLIC_TOPIC_*` values must be IDENTICAL on EC2 and Mac
- `push_public(channel)` signature: `channel: Literal["price", "news", "errors", "digests"]`
- `push_private(topic)` — REMOVED Chat 5 commit 7b along with `PrivateTopic` Literal and `_NTFY_AUTH`. No callers remain in `app/` or `scripts/`.
- `NTFY_URL` / `NTFY_USER` / `NTFY_PASS` — REMOVED Chat 5.5 commit 1 (TD9 SHIPPED 2026-05-24). Both `settings.py` field declarations AND the `# ntfy` header + three KEY=VALUE lines in `/etc/portfolio-advisor/secrets.env` were removed in one atomic deploy + restart so a Pydantic v2 boot validation error couldn't mask itself between sides. Backup of secrets.env written before sed.

## Section 11: Phase 1 INVARIANTS — never violate

These come straight from `docs/data_flow.md` (rewritten Chat 5 doc deliverable 1/4 — Phase 1 sections refreshed for post-Chat-5 reality). They are hard rules.

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
- **Chat 5 A1**: `monitored_stocks` writes go through `MonitoredStockFeedbackPatch(...).model_dump(exclude_none=True)`. `extra="forbid"` catches Literal drift at write time. `exclude_none=True` preserves prior-action `*_at` timestamps. `$setOnInsert` seeds `added_by`, `added_reason`, `_schema_version`, `created_at`.
- The `notes` field on a `SuggestionRun` is a JSON string containing `{dossiers: [...]}`. The router parses it and exposes `dossiers` at the top level, then strips `notes` and `all_candidates`.

### F2 / F14 invariants (Chat 4)
- `SuggestionDirection` literal = `"buy" | "sell"`. Both `SuggestionRun.direction` and `SuggestionOutcome.direction` default to `"buy"`.
- The router serializer (`_serialize_run`) and the `/runs` projection BOTH defensively default missing `direction` to `"buy"` on the raw-dict path.
- `compute_system_performance(direction="sell")` SIGN-FLIPS `excess_return` at aggregation time.
- `snapshot_open_outcomes` is DIRECTION-AGNOSTIC.
- `earnings_calendar` refresh: `refresh_earnings_for(isin, ...)` deletes all events with `earnings_date >= today` then re-inserts. Past events never touched.
- `_sanitize_for_bson` is applied to `Ticker.calendar` BEFORE inserting.
- F14 earnings-proximity gate is SHARED between buy and sell via `evaluate_earnings_proximity_gate`. Skips trades within 5 days. `next_earnings is None` → `skipped=True, passed=True`.
- Sell-side scoring uses different groups (`booking_opportunity`/`valuation_stretch`/`risk`/`tax_concentration`) and gates (`in_profit`/`min_position_age`/`earnings_proximity`).
- `CandidateScore` has FIXED buy-side group fields. Sell-side rows leave them at 0.0; sell-side group scores flow through `group_meta`. Display layer branches on direction.
- `monitored_stocks` is currently DIRECTION-AGNOSTIC (TD1).
- F2 combined-digest: `--direction=both` emits ONE email + ONE ntfy push via `send_combined_digest`. Delivery row attaches to the buy run id.

### Chat 5 A2 (CLOSED)
- `notify.email()` returns `{ok: bool, id: str|None, error: str|None}` and SWALLOWS Resend exceptions. Callers must check `result["ok"]`. Optional `text=` param enables multipart/alternative.
- All Resend traffic flows through `notify.email()`. `digest_delivery._send_email` delegates (A2 part 1). `reconciliation._send_drift_alerts` branches on `result["ok"]` (A2 part 2 — Chat 5 commit 1).

### Chat 5 A3+A4 (CLOSED)
- `SignalScore.raw_value` carries the RAW input that fed normalization (raw fundamental ratio, raw momentum %, news scaled-sentiment / velocity / count) — NOT the normalized 0-100 score. Normalized score lives in `SignalScore.normalized_score`. Holds from Chat 5 commit 2 onward.
- Legacy runs predating commit 2 have `raw_value=f"{normalized:.2f}"` and should be regenerated if accuracy matters. Post-TD11 the UI now READS `sig["raw_value"]` for momentum / news / sell-side-holding signals, so legacy runs will render an oddly-formatted-but-non-fatal value in those signal slots until they age out.

### Chat 5.5 TD11 (CLOSED)
- `explainability._build_signal_meta` falls back to `_to_float(sig["raw_value"])` when `meta["fundamentals_field"] is None` AND `sig["available"] is True`. The parsed float is then rendered via `_format_raw(meta["formatter_kind"], raw)`.
- News signals reassigned to formatters that render the parsed raw correctly: `news_net_sentiment` → `score_signed` (`f"{raw:+.1f}"`, e.g. `+74.4`), `news_story_velocity` → `ratio` (`f"{raw:.2f}"`), `news_story_count` → `count` (`f"{int(raw)}"`). `high_severity_negative_count` also → `count`. `is_ltcg_eligible` deliberately kept on `score_only` — binary semantic, dossier conveys meaning.
- `_format_raw` extended with two new formatter kinds: `score_signed` and `count`. All existing formatters unchanged.
- Stale comment on line ~116 ("News signals (raw values not persisted post-run; we show normalized only)") refreshed to describe post-A3+A4 reality.
- Unavailable signals (`sig["available"] is False`) still render `"—"`. No frontend changes; `explain-popover.tsx` consumes `raw_value_formatted` directly.

### Chat 5 commit 8 (CLOSED) — cron-health dual transport
- `cron_health_check.py` sends every anomaly batch on TWO independent transports: `push_public("errors", ...)` and `notify.email(subject, html, text)`.
- The script raises (so `cron_run` records the run as failed) ONLY when BOTH transports fail. Single-transport failure degrades gracefully.
- Happy path is unchanged: if no anomalies, neither transport fires.

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

Chat 2 (F4 + F5a) — Cron observability shipped 2026-05-16.

Chat 3 (F6 + F5b + F10) — Stateful feedback shipped 2026-05-17.

Chat 4 (F2b + F14 + F2 backend + F2 frontend) — Sell-side fully shipped 2026-05-17/18/20.

Chat 5 (Audit + cleanup) — fully SHIPPED 2026-05-24. Eight commits + two manual EC2 steps + one infra step + four doc deliverables.

Chat 5.5 (Small TD cleanup) — partially SHIPPED 2026-05-24, three TDs OPEN (TD10, TD13, TD14):

| # | Commit / step | Items closed | Date |
|---|---|---|---|
| 1 | settings.py `NTFY_URL/USER/PASS` field removal + EC2 secrets.env sed | TD9 | 2026-05-24 |
| 2 | `explainability.py` _build_signal_meta raw_value fallback + formatter additions + comment refresh | TD11 | 2026-05-24 |
| 3 | `README.md` + `docs/data_flow.md` doc corrections (the script `seed_nifty100.py` is CORRECTLY NAMED; "top 250" was a doc hallucination) | TD12 | 2026-05-24 |
| 4 | `Project_State.md` refresh (this commit) | docs | 2026-05-24 |
| 5 | Frontend `README.md` per-page reference (TD13) | (deferred — needs route files at SHA) | OPEN |
| 6 | EC2 `crontab -e` removal of `0 0 * * 0` log truncation line (TD10) | (deferred — gated on first logrotate cycle 2026-05-31) | OPEN |
| 7 | EC2 `crontab -e` removal of bogus `--notify --run-type scheduled` flags from Sunday 07:00 line (TD14, discovered Chat 5.5) | (deferred — manual EC2 step) | OPEN |

Open items CARRIED FORWARD past Chat 5.5:
- TD10 — remove redundant `0 0 * * 0 log truncation` crontab line. Verify 2026-06-01 then drop.
- TD13 — frontend per-page reference doc. Needs frontend HEAD SHA + ability to read route files at that SHA.
- TD14 — remove bogus `--notify --run-type scheduled` from Sunday 07:00 IST crontab line (NEITHER flag exists on `run_weekly_suggestions.py` argparse). Cause of missing Sunday digests since the flags were added.

### Final chat split plan

| # | Chat | Scope | Status |
|---|---|---|---|
| 2 | Cron observability | F4 + F5a | SHIPPED 2026-05-16 |
| 3 | Stateful suggestions | F6 + F5b + F10 | SHIPPED 2026-05-17 |
| 4 | Sell-side suggestions | F2 + F2b + F14 + F2 frontend + F2b cosmetic | SHIPPED 2026-05-17/18/20 |
| 5 | Audit + cleanup | A1-A19 + TD8 + dual-transport + logrotate + 4 doc deliverables | SHIPPED 2026-05-23/24 |
| 5.5 | Small TD cleanup | TD9 + TD11 + TD12 SHIPPED 2026-05-24; TD10 + TD13 + TD14 OPEN | partially SHIPPED |
| 6 | Chat features | F1 + F3 | open |
| 7 | Portfolio intelligence | F12 + F15 | open |
| 8 | Watchlist | F13 | open |
| 9 | Pre-launch cleanup | F11 + realized P&L hide + stop_loss alerts (Q3 follow-through, TD6) | open |
| 10 | GO LIVE | F7 one-time real data import | open |

#### Chat 6 — Chat features (F1 + F3)
F1 — Ad-hoc chat about suggestions; F3 — Ad-hoc chat about a specific holding. Share `conversations` collection scaffolding.

#### Chat 7 — Portfolio intelligence (F12 + F15)
F12 — `/portfolio/risk-summary`; F15 — tag-based portfolio views.

#### Chat 8 — Watchlist (F13)
`build_universe` becomes: NIFTY 100 ∪ watchlist ∪ held − excluded. `refresh_fundamentals.py` and `fetch_news_for_universe.py` must be extended to include watchlist ISINs.

#### Chat 9 — Pre-launch cleanup (F11 + realized P&L hide + stop_loss alerts)
F11 capital gains pack + realized P&L UI hide + stop_loss alert wiring (Chat 5 Q3 follow-through; TD6).

#### Chat 10 — GO LIVE (F7 one-time real data import)
Wipe + re-import via `refresh_from_icici.py` wrapper. Default behavior wipe-and-replace (only `transactions`, `transactions_staging`, `holdings`). Other Phase 2 collections preserved.

## Section 14: Conventions the assistant has repeatedly drifted on

The assistant has confused these multiple times. Memorize them.

- Port 8001 (Mac local), port 8000 (EC2). Always specify which.
- SSH-first for tests: every test block MUST begin with `ssh ubuntu@100.112.20.41` and run curls against `localhost:8000`.
- Commit-block-after-code: every code/file delivery MUST be followed by a paste-ready `git add .` + `git commit -m "..."` block.
- Project_State.md is ALWAYS a complete full-file replacement, never a patch or "rest unchanged".
- F6 two-mechanism feedback exclusion: `get_excluded_isins` at run-build AND `_build_user_action` at serialization. Both required.
- The 90-day rejected cooldown and 30-day acted soft-exclude are intentionally NOT env-configurable.
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
- Direction-aware display layer: branch on direction at the display layer, not by forking the model.

### Chat 4 additions
- **DO NOT trust Glean snippets or memory for dataclass / Pydantic model field names.** BEFORE writing any patch that constructs `Foo(field=...)`, run `grep -B 2 -A 20 "class Foo" <file_path>` on the actual file on disk.
- **`cron_run()` yields a `_Heartbeat` object that exposes `.meta` as an ATTRIBUTE, not `__setitem__`.** Use `ctx.meta = {...}` or `ctx.meta[key] = value`. `ctx["meta"] = ...` raises TypeError.
- **The `/cron/heartbeats` endpoint returns `{heartbeats, health_summary}`**, not `{registry, recent}` or `{jobs}`.
- **`Collections.instruments_fundamentals()` is the accessor name** — NOT `Collections.fundamentals_snapshots()`.
- **`run_suggestions()` is SLOW by default** (~2-4 min for Sonnet dossiers). Use `--skip-dossiers` only for smoke tests. Production cron MUST NOT use `--skip-dossiers`.

### Chat 5 additions
- **ASK FOR THE CURRENT BACKEND (and frontend if relevant) SHA BEFORE PROPOSING ANY CODE CHANGE.** Then re-read the file at that SHA via Glean. Write find-and-replace blocks against the verbatim file text, NOT against snippet memory or earlier-read state. NO EXCEPTIONS.
- **When a wrapper function's return shape or exception behavior changes, grep for ALL callers BEFORE shipping the change.**
- **`notify.email()` now returns `{ok: bool, id: str|None, error: str|None}`** and swallows Resend exceptions.
- **GitHub raw-URL caching is a real failure mode.** Use `ssh ubuntu@100.112.20.41 'sed -n "<line>,<line>p" <path>'` as the ground truth.

### Chat 5 closure additions
- **Doc rewrites must cross-check every cron/registry/file claim against actual on-disk state.** RULE: for any cron description, paste `crontab -l` AND read the script's `cron_run(...)` name before publishing. For any function description, read the function body in full at HEAD before publishing.
- **Project_State.md structure is load-bearing. NEVER restructure it.** Section 0 stays. Numbered Sections 1-22 stay in order. Insertions of new sub-items go inside existing sections.
- **Cron-health observability needs redundant transports.**
- **EC2 cron log retention uses `/etc/logrotate.d/portfolio-advisor`** since 2026-05-24.

### Chat 5.5 additions
- **BEFORE writing any patch that documents what a script does (file map blurb, README entry, data_flow paragraph), READ THE SCRIPT BODY at HEAD.** TD12 was scoped as a rename based on "actually seeds top 250" — turned out the script was correctly named all along and three docs had picked up a Chat-5 file-map hallucination. The script body is the ground truth, never the upstream summary.
- **BEFORE documenting or trusting a cron line, verify the script's argparse accepts the flags.** TD14: the Sunday 07:00 IST line passed `--notify --run-type scheduled` for weeks; neither flag existed. argparse rejected every Sunday run; no digest fired. The fix is to run `python scripts/<name>.py --help` and compare against `crontab -l`. Do this BEFORE adding a new cron line and BEFORE publishing a doc that quotes the line.
- **For settings-side cleanup that touches both `settings.py` and `/etc/portfolio-advisor/secrets.env` (orphan-key removal post-decommission), ship BOTH sides in ONE atomic commit + restart.** Touching `settings.py` alone risks masking a Pydantic v2 validation error on boot if the model and the env file drift to incompatible states. TD9 pattern: backup secrets.env first (`secrets.env.bak.<timestamp>`), sed-delete the matching lines, restart, verify with `/health` + `journalctl` grep for `error|valid|ntfy`.
- **Glean's snippet-mode rendering of long Markdown files line-wraps at sentence boundaries, NOT at file-line boundaries.** Reconstructing a long source file from snippets risks corrupting paragraph structure (e.g., bullet items spanning multiple snippet lines). For canvas full-file artifacts of Project_State.md, prefer reading via `raw.githubusercontent.com/<repo>/<sha>/<path>` (which preserves line structure) over the GitHub blob URL or other Glean-snippet paths. If the raw URL also returns snippets, ask the user for an EC2 `cat` paste.

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
- **Trusting PROJECT_STATE.md as the source of truth for "what's open" without verifying against code.**
- **Writing find-and-replace blocks from snippet memory or stale file reads.**
- **Changing a wrapper function's return shape or exception behavior without checking ALL callers first.**
- **Inferring return shape from documentation comments instead of from the actual function body.**

### Chat 5 closure additions
- **Restructuring Project_State.md when the user said "preserve structure".**
- **Inventing cron entries / removing real ones in doc rewrites.**
- **Describing a script as "consumer only" / "not cron-scheduled" / "ntfy-only" without reading the script's main() and the actual crontab.**
- **Skipping Section 0 when delivering Project_State.md.**

### Chat 5.5 additions
- **Proposing a script rename based on a file-map summary without reading the script body.** TD12 was originally scoped as "rename seed_nifty100.py because it actually seeds top 250" — the script body showed it seeds NIFTY 100 exactly as the name claims. Three docs had picked up the same hallucination from the Chat-5 file-map summary. Cost: a whole chat-turn investigating before the user could approve the doc-only fix. RULE: when a TD scope says "X is misnamed because it actually does Y", FIRST read X at HEAD before agreeing.
- **Adding cron-line flags without running the script's `--help` first.** TD14: someone added `--notify --run-type scheduled` to the Sunday 07:00 line at some point; neither flag existed. argparse rejected every run; cron-suggestions.log was a 221-byte error message every Sunday; no digest fired; user noticed only when manually testing TD9. RULE: when adding ANY flag to a cron line, run `python scripts/<name>.py --help` first. When reading an existing cron line to document it, do the same — if the docs show flags that `--help` doesn't list, the cron is broken.
- **Rendering an artifact that includes nested triple-backtick fences and assuming canvas display will work.** First Chat-5.5 attempt at Project_State.md rendered inline in chat instead of as canvas. The Section 0 bootstrap is itself wrapped in triple-backticks, which is necessary fidelity but can confuse renderers. RULE: keep the artifact's source structure faithful to the on-disk file (don't switch fences to indented code blocks); if canvas fails to render, deliver as a sandbox file (`/home/user/output/...`) with a download link as fallback.

## Section 16: "I am losing context" — escalation protocol

When the assistant notices ANY trigger, say verbatim:

```
I AM LOSING CONTEXT
```

### Triggers (any one is sufficient)
- Cannot recall a specific file structure that was discussed earlier in the chat
- Conflating Phase 1 facts with Phase 2 facts
- Forgetting which Commit (A, A.5, A.5.1, B) shipped which behavior
- Forgetting which Chat (2, 3, 4, 5, 5.5) shipped which feature
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
- **Chat 5 trigger: proposed a find-and-replace block whose `original_text` doesn't exist verbatim in the actual file at the current SHA.**
- **Chat 5 trigger: changed a wrapper function's return shape or exception behavior without grep'ing for ALL callers first.**
- **Chat 5 closure trigger: about to publish a doc rewrite that contains a cron / registry / file claim you haven't verified against `crontab -l` / `CRON_REGISTRY` / `sed -n`** — stop and verify first.
- **Chat 5 closure trigger: about to restructure Project_State.md when the user has asked you to preserve structure.**
- **Chat 5.5 trigger: about to propose a rename of a script based on a file-map summary without having read the script body at HEAD.** Switch chats if you catch yourself doing this.
- **Chat 5.5 trigger: about to document a cron line without having run the script's `--help` to verify the flags exist.** Switch chats.

### What "switching chats" means

The user copies the Section 0 bootstrap into a fresh chat. The new chat reads PROJECT_STATE, both repos at HEAD, `data_flow.md`, READMEs. User states scope. Assistant summarizes. Then coding. The new chat updates PROJECT_STATE at the end of its work as the last commit.

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
- "Where do F4 cron failure alerts go?" → Both `push_public("errors", ...)` on public ntfy.sh (topic `NTFY_PUBLIC_TOPIC_ERRORS`) AND `notify.email(...)` (dual-transport, Chat 5 commit 8). Raises only when BOTH fail.
- "Heartbeat schema?" → `{cron_name, started_at, finished_at, status, error, metadata, _schema_version: 1}`. TTL 60 days.
- "Healthy/unhealthy rule?" → Healthy iff (not expected today) OR (`success+skipped >= min` AND `failure == 0`).
- "How is PROJECT_STATE.md delivered?" → Always full-file canvas artifact.
- "What must accompany every code/file delivery?" → A paste-ready `git add .` + commit block.
- "How do test blocks start?" → `ssh ubuntu@100.112.20.41`, then curls against `localhost:8000`.

### Chat 4 additions
- "Fields on `CronSpec`?" → `cron_name`, `description`, `schedule_human`, `expected_weekdays`, `min_runs_per_day` (default 1).
- "How do you set metadata on `_Heartbeat`?" → `ctx.meta = {...}` or `ctx.meta[key] = value`. ATTRIBUTE.
- "Response shape of `/cron/heartbeats`?" → `{heartbeats: [...], health_summary: [...]}`.
- "Collection name for fundamentals snapshots?" → `instruments_fundamentals`.
- "Does `run_suggestions()` default to skipping dossiers?" → No. `--skip-dossiers` only for smoke tests.
- "F2b ntfy topic for digests?" → `NTFY_PUBLIC_TOPIC_DIGESTS`, required.
- "F14 earnings-proximity gate threshold?" → 5 days. Shared between buy and sell.
- "Sell-side gate set?" → `in_profit`, `min_position_age`, `earnings_proximity`. NOT `high_severity_negative_news` (signal).
- "How does `compute_system_performance(direction='sell')` handle excess_return?" → SIGN-FLIPS at aggregation time.

### Chat 5 additions
- "Is F2 frontend shipped?" → Yes, verified at frontend SHA `e34e126`; README rewrite at `9edfc8f`.
- "Is the Q/V/M/N=0 sell-digest cosmetic bug fixed?" → Yes, 2026-05-20 commit `cea8eee`.
- "Is `target_price` consumed anywhere?" → Yes, F2 sell-side `target_price_proximity`. `stop_loss` deferred to Chat 9 (TD6).
- "Has `digest_delivery._send_email` been reconciled with `notify.email()`?" → Yes (Chat 5 A2 part 1).
- "What does `notify.email()` return?" → `{ok: bool, id: str|None, error: str|None}`. Swallows exceptions. Optional `text=`.
- "What's the rule before proposing ANY code change?" → Ask for the current backend SHA. Re-read at that SHA. No exceptions.
- "What did A1 ship?" → `MonitoredStock` Literal aligned; `MonitoredStockFeedbackPatch` typed wrapper; writer migrated.
- "What did A2 part 1 ship?" → `notify.email(...)` returns `{ok,id,error}`; `digest_delivery._send_email` delegates.
- "On-disk filename for this doc?" → `Project_State.md` (title case). GitHub paths are case-sensitive.

### Chat 5 closure additions
- "What did A2 part 2 ship?" → `reconciliation._send_drift_alerts` branches on `result["ok"]`; passes `text=`.
- "What did A3+A4 ship?" → `composite_for_candidate` writes raw input into `SignalScore.raw_value`. Both buy and sell call sites updated.
- "What did TD8 ship?" → Self-hosted ntfy service stopped 2026-05-18; code cleanup commits 7a/7b 2026-05-23.
- "What did commit 8 ship?" → `cron_health_check.py` dual-transport; raises only when both fail.
- "What does logrotate manage on EC2?" → `/home/ubuntu/cron-*.log`, weekly, rotate 4, compress, copytruncate, su ubuntu.
- "Did `cron_health_check.py` write its own heartbeat before Chat 5?" → Yes. Always has.
- "What's `track_suggestion_outcomes.py`'s schedule?" → `45 19 * * 1-5` (Mon-Fri 19:45 IST).

### Chat 5.5 additions
- "What did TD9 ship?" → `settings.NTFY_URL` / `NTFY_USER` / `NTFY_PASS` field declarations removed AND the matching `# ntfy` header + three KEY=VALUE lines (10-13) removed from `/etc/portfolio-advisor/secrets.env`. One atomic commit + restart so Pydantic v2 boot validation couldn't drift. Backup at `secrets.env.bak.<timestamp>`.
- "What did TD11 ship?" → `explainability._build_signal_meta` falls back to `_to_float(sig["raw_value"])` rendered via `_format_raw(meta["formatter_kind"], raw)` when `fundamentals_field is None` AND `available is True`. News signals reassigned to new formatter kinds (`score_signed` / `ratio` / `count`); `high_severity_negative_count` → `count`. `is_ltcg_eligible` kept on `score_only` (binary). Two new `_format_raw` kinds added.
- "What did TD12 ship?" → DOC-only fix in `README.md` + `docs/data_flow.md`. The script `seed_nifty100.py` is CORRECTLY NAMED — the "actually seeds top 250" claim was a Chat-5 file-map hallucination that propagated into 3-4 docs. No rename, no code change.
- "What is TD14 and why does it matter?" → Sunday 07:00 IST `run_weekly_suggestions.py` crontab line passes `--notify --run-type scheduled`. NEITHER flag exists on the script's argparse. argparse rejects every Sunday run with a usage error. Cause of missing Sunday digests. Fix is `crontab -e` and delete the two flags.
- "Where do `cron-*.log` files live and what happens at 10MB?" → `/home/ubuntu/cron-*.log`. Pre-2026-05-24 a weekly `find ... -size +10M` cron tail-truncated them. Now `/etc/logrotate.d/portfolio-advisor` rotates weekly regardless of size (rotate 4 + compress). The legacy line is TD10, scheduled for removal post-2026-05-31.
- "Why didn't TD12 become a rename?" → Because reading `scripts/seed_nifty100.py` at HEAD showed it does what its name says — downloads `ind_nifty100list.csv` from NSE and marks ~100 instruments. The "top 250" claim was a doc-side hallucination. Lesson encoded in Section 14.

## Section 18: Tech debt registry

| ID | Item | Status | Chat target |
|---|---|---|---|
| A1 | `MonitoredStock` schema vs writer drift | SHIPPED Chat 5 (2026-05-23) | — |
| A2 | `digest_delivery._send_email` inline resend + `reconciliation._send_drift_alerts` callers | SHIPPED Chat 5: part 1 (2026-05-23), part 2 commit 1 (2026-05-23) | — |
| A3 | `SignalScore.raw_value` writer stores normalized score instead of raw input | SHIPPED Chat 5 commit 2 (2026-05-23) | — |
| A4 | News signal raw values not persisted post-run | SHIPPED Chat 5 commit 2 as side effect of A3 (2026-05-23) | — |
| A5 | Stale `DEFAULT_CONFIG.gates` comment | SHIPPED Chat 5 commit 2 (2026-05-23) | — |
| A6 | `weekly_suggestions` `schedule_human` says 06:00, actual 07:00 | SHIPPED Chat 5 commit 3 (2026-05-23) | — |
| A6.5 | `refresh_instruments` CronSpec description claims "Zerodha Kite" | SHIPPED Chat 5 commit 3 (2026-05-23) | — |
| A7 | `SATURDAY = {5}` weekday-set unused | SHIPPED Chat 5 commit 3 (2026-05-23) | — |
| A8 | Dead `app/models/news_article.py` | SHIPPED Chat 5 (2026-05-23) | — |
| A13 | `refresh_instruments.py` docstring "Zerodha Kite" → NSE EQUITY_L.csv | SHIPPED Chat 5 commits 4 + 4b (2026-05-23) | — |
| A14 | `monitored_stocks` partial unique index load-bearing on writer drift | CLOSED by A1 | — |
| A16 | `fetch_news_for_universe.py` cron line `--include-held` | SHIPPED Chat 5 manual EC2 step (2026-05-24) | — |
| A17 | Stale pre-chunk-6 comment in `_run_sell_pipeline` | SHIPPED Chat 5 commit 5 (2026-05-23) | — |
| A18 | `enrich_run` page_intro buy-centric for sell runs | CLOSED — already shipped pre-Chat-5; verified at SHA `d3f307a` | — |
| A19 | Three `Query(..., regex=...)` → `pattern=` in `routers/suggestions.py` | SHIPPED Chat 5 commit 6 (2026-05-23) | — |
| TD1 | `monitored_stocks` direction-agnostic | DEFERRED | Decide post-launch |
| TD2 | `docs/data_flow.md` stale | SHIPPED Chat 5 doc deliverable 1/4 (2026-05-23 + 2026-05-24 corrections + Chat 5.5 commit 3 TD12 corrections) | — |
| TD3 | `dossier_service.valuation_verdict` single-string split | DEFERRED | Future UI work |
| TD4 | Backend `README.md` stale | SHIPPED Chat 5 doc deliverable 2/4 (2026-05-23 + 2026-05-24 corrections + Chat 5.5 commit 3 TD12 corrections) | — |
| TD5 | Frontend `README.md` missing `/suggestions` route + Suggestions header button | SHIPPED Chat 5 doc deliverable 3/4 (2026-05-23 at frontend SHA `9edfc8f`); per-page reference deferred to TD13 | — |
| TD6 | `holdings.stop_loss` orphan | OPEN — Chat 5 Q3 resolved as "wire it"; deferred to Chat 9 | Chat 9 |
| TD7 | `CandidateScore` fixed buy-side group fields | DEFERRED | Post-launch |
| TD8 | EC2 self-hosted private ntfy service decommission + code cleanup | SHIPPED — service stopped 2026-05-18; code cleanup commits 7a + 7b (2026-05-23) | — |
| TD9 | Orphan `NTFY_URL` / `NTFY_USER` / `NTFY_PASS` cleanup from `settings.py` + `/etc/portfolio-advisor/secrets.env` | SHIPPED Chat 5.5 commit 1 (2026-05-24) | — |
| TD10 | Remove redundant `0 0 * * 0 log truncation` crontab line (logrotate replaces it as of 2026-05-24) | OPEN | Chat 5.5 (verify first logrotate cycle 2026-05-31; remove 2026-06-01) |
| TD11 | Wire `explainability._build_signal_meta` to read `sig["raw_value"]` for momentum/news signals + refresh stale comment + reassign news formatter kinds | SHIPPED Chat 5.5 commit 2 (2026-05-24) | — |
| TD12 | Rename `scripts/seed_nifty100.py` (file map flagged as misnamed) | SHIPPED-AS-DOC-FIX Chat 5.5 commit 3 (2026-05-24): the script is correctly named; "top 250" was a hallucination in the Chat-5 file-map summary that propagated into 3 docs. All four locations corrected (file map in this file, README §8 entries for seed_nifty100 + refresh_fundamentals, README §11 gotcha #1, data_flow.md "Universe + fundamentals refresh"). No rename, no code change. | — |
| TD13 | Frontend per-page reference doc (TanStack Query keys, mutation refetch patterns, endpoint-per-route mapping) | OPEN — deferred from Chat 5 doc deliverable 3/4; not unblocked in Chat 5.5 (need frontend HEAD SHA + ability to read route files at that SHA) | Chat 5.5 (carry) |
| TD14 | Sunday 07:00 IST crontab line passes `--notify --run-type scheduled` to `run_weekly_suggestions.py`; NEITHER flag exists on the script's argparse. argparse rejects every Sunday run with a usage error. cron-suggestions.log is 221 bytes (just the error). No digest has fired in weeks. Discovered Chat 5.5 2026-05-24 while investigating "no digest received Sunday 6:28 PM IST". Fix: `crontab -e` on EC2 and delete the two bogus flags. Optional immediate-recovery: run the script manually with `--direction=both` to fire a one-off digest. | OPEN — manual EC2 step | Chat 5.5 (carry) |

### Fixed in earlier chats (kept for posterity)
- **DIGEST SELL-SIDE Q/V/M/N BUG** — fixed 2026-05-20 in `cea8eee` via direction-aware `_format_score_breakdown`.
- **`track_suggestion_outcomes.py` docstring "Daily 18:30 IST"** — fixed; now generic.
- **`top_k` default in CLI docstring "--top-k 5"** — fixed via F2 chunk 6 rewrite of `run_weekly_suggestions.py`.
- **`holdings.target_price` unused** — half-fixed; F2 sell-side `target_price_proximity` signal. `stop_loss` is TD6.
- **`MonitoredStock` schema vs writer drift** — fixed Chat 5 A1 (2026-05-23).
- **Dead `news_article.py`** — deleted Chat 5 A8 (2026-05-23).
- **`digest_delivery._send_email` inline Resend** — fixed Chat 5 A2 part 1 (2026-05-23).
- **All Chat 5 audit items A2-A19 + TD8** — closed Chat 5 2026-05-23/24.
- **Chat 5.5 TD9 + TD11 + TD12** — closed Chat 5.5 2026-05-24 (commits 1, 2, 3).

## Section 19: How to update this document

This file is updated at the end of every chat as the LAST commit. ALWAYS a complete full-file canvas artifact, never a patch.

What to update each chat:
- Section 13 — move shipped items; advance chat split plan (preserve existing rows; only modify Status / add new chat rows in numbered order)
- Section 9 — update cron registry if entries added/changed
- Section 14 — add new conventions earned
- Section 15 — add new anti-patterns
- Section 16 — add new triggers
- Section 17 — add new diagnostic Q&A
- Section 18 — add/remove/reclassify tech debt
- Section 12 — new Phase 2 invariants
- Section 11 — new Phase 1 invariants (rare)
- Section 7 — collection schema changes
- Section 8 — endpoint changes (or notable internal-data changes, as TD11 noted under Section 8)
- Section 5/6 — file additions/deletions
- Section 4 — pin new last-verified SHAs

Commit message convention:

```
docs: update PROJECT_STATE.md after <chat scope>
- <bullet list of sections changed>
```

If the chat ended due to context loss, the LAST thing the assistant does before stopping is propose the PROJECT_STATE update. The user applies it manually.

Chat 5 added rule: when starting a new chat, after reading PROJECT_STATE, do a code audit of every "open" item against the actual on-disk code at HEAD before estimating work.

Chat 5 closure added rule: Project_State.md structure is immutable. Section 0 stays at top. Numbered Sections 1-22 stay in order. New sub-items go INSIDE the existing sections, never as new top-level sections.

Chat 5.5 added rule: when reading Project_State.md via Glean for the purpose of producing a full-file canvas refresh, prefer the SHA-pinned `raw.githubusercontent.com` URL over the GitHub blob URL — the blob URL frequently returns `LINK_NEEDS_AUTH` even on public repos. If both URLs fail, ask the user to `ssh ubuntu@100.112.20.41 && cat ~/ai-stock-advisor-backend/docs/Project_State.md` and paste the bytes.

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
- `digest_delivery.py` parallel Resend path: open as A2 (CLOSED Chat 5).
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
- **A1 typed PATCH model (`MonitoredStockFeedbackPatch`) instead of bare dict $set**.
- **A1 `$setOnInsert` seeding**.
- **A2 part 1 wrapper return-shape change** (`raw resend dict` → `{ok,id,error}`): CLOSED Chat 5 commit 1.

### Chat 5 closure additions
- **A3+A4 fixed via writer change (option b) rather than field rename (option a)**.
- **TD8 code removed in two commits (7a + 7b) rather than one**.
- **Cron-health dual transport (commit 8) raises only when BOTH transports fail**.
- **Logrotate over hand-rolled find/tail truncation**.
- **Project_State.md as the durable Chat-5-close artifact**.

### Chat 5.5 additions
- **TD9 atomic settings.py + secrets.env cleanup** (vs single-sided): touching `settings.py` alone risks masking a Pydantic v2 boot validation error if the model and env file drift. Touching only `secrets.env` would leave orphan field declarations. One commit + one restart + one backup catches every drift state immediately on `journalctl`. Verified post-deploy with `/health` + `journalctl -n 50 | grep -iE 'error|valid|ntfy'`.
- **TD11 minimum-invasive wiring** (vs writing a parallel "raw display layer"): the existing `_format_raw` already had five formatter kinds with a consistent signature. Adding `score_signed` and `count` extends that pattern by ~6 lines total instead of forking a new render path. News signal `formatter_kind` reassignment is one-line-per-signal in `SIGNAL_META`. `_build_signal_meta` fallback is one elif-branch addition. Total diff: ~30 lines in one file. No frontend change. No model change. No endpoint shape change.
- **TD12 doc-only resolution** (vs rename): reading `seed_nifty100.py` at HEAD showed it does exactly what its name says — fetches NIFTY 100 from NSE archives. The "actually seeds top 250 by market cap" claim was a Chat-5 file-map summary hallucination that propagated into README §8 + README §11 + data_flow.md + this file. Renaming the (correctly named) script to match the (incorrect) claim would have broken back-references and required redoing the docs anyway. The DOC-ONLY fix preserves the correct name and corrects every wrong claim in one commit.
- **TD14 flagged as a tracked open item rather than silently fixed in this commit**: the bogus `--notify --run-type scheduled` crontab flags are a manual EC2 `crontab -e` change. The assistant cannot edit the live crontab; the user must. Logging it as TD14 ensures it doesn't get lost and gives the user the exact recovery commands. Two action items for the user: (1) `crontab -e` and remove the flags; (2) optionally `python scripts/run_weekly_suggestions.py --direction=both` to fire a one-off recovery digest immediately.
- **Project_State.md fetched via raw.githubusercontent.com at SHA** rather than the GitHub blob URL: Chat 5.5 spent a turn discovering that the blob URL returns `LINK_NEEDS_AUTH` on a public repo. The raw URL with explicit SHA returns clean line-preserved content. Standing convention encoded in Section 19.

## Section 21: What is intentionally NOT included in this project

So future chats don't accidentally try to add these:

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
- **`MonitoredStockFeedbackPatch` (Chat 5 A1)**: typed Pydantic model for the `$set` patch. `ConfigDict(extra="forbid")`. Catches Literal drift at write time.
- **`notify.email()` return contract (Chat 5 A2)**: `{ok: bool, id: str|None, error: str|None}`. Swallows Resend exceptions. Optional `text=` for multipart.
- **`_send_drift_alerts` (Chat 5 A2 part 2)**: `reconciliation.py` helper; ntfy + email dual emit; `sent.append("email")` gated on `result["ok"]`.
- **`composite_for_candidate` (Chat 5 A3+A4)**: scoring helper with optional `candidate_signals_for_isin` that wires raw signal inputs into `SignalScore.raw_value`.
- **TD8 ntfy decommission (Chat 5 commits 7a+7b)**: self-hosted ntfy stopped 2026-05-18; `push_private` + `PrivateTopic` + `_NTFY_AUTH` + `b64encode` import + `smoke_test.py` private block all removed 2026-05-23.
- **Cron-health dual transport (Chat 5 commit 8)**: ntfy + email; raises only when BOTH fail.
- **Logrotate (Chat 5 2026-05-24)**: weekly with rotate-4, copytruncate, su ubuntu ubuntu.
- **`_format_raw` formatter kinds (Chat 5.5 TD11)**: existing kinds — `percent_decimal`, `percent_already`, `ratio`, `multiple`, `currency_inr_cr`, `score_only`. NEW kinds — `score_signed` (`f"{raw:+.1f}"`, e.g. `+74.4` for news net sentiment), `count` (`f"{int(raw)}"`, e.g. `54` for news story count).
- **TD9 / TD10 / TD11 / TD12 / TD13 / TD14 (Chat 5.5)**: see Section 18. TD9/TD11/TD12 SHIPPED 2026-05-24; TD10/TD13/TD14 OPEN.

End of PROJECT_STATE.md.
