
# PROJECT_STATE.md

Living source of truth for the Personal AI Stock Advisor. Updated at the end of every chat. Bootstrap document for any new conversation — read top to bottom before doing anything. Do not skim, assume, or redesign.

Companion doc: `docs/master_todo.md` is the canonical ordered task list (WHAT TO DO NEXT). This file describes WHAT THE SYSTEM IS. Read both at the start of every chat.

**Compaction note (Chat 5.16):** This is the compacted edition. No actionable fact, invariant, convention, "NOT included" rule, open/deferred item, or cross-reference was removed. Closed history (A1–A19, SHIPPED TDs, per-chat narratives) was collapsed into one-line ledger entries in Section 13/18; verbatim-duplicated blocks were deduped. The full pre-compaction history lives in git: `git show <prior-sha>:docs/Project_State.md`.

## Section 0: How to start a new chat

Paste this verbatim at the top of any new chat:

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
  from the laptop). For frontend-only changes, tests run with `npm run build` /
  lint on EC2 via `~/deploy-ui.sh`.
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
  Chat 5.5; logged as TD14 and as master_todo #1. SHIPPED Chat 5.9. (See Section 14.)
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

**Filename casing:** the file on disk is `docs/Project_State.md` (title case). GitHub paths are case-sensitive; the all-caps `PROJECT_STATE.md` 404s.

**URL construction:** prefer `https://raw.githubusercontent.com/doshisahil95/<repo>/<sha>/<path>` over the GitHub blob URL — the blob URL frequently returns `LINK_NEEDS_AUTH` for Glean readers even on public repos. (Chat 5.5; reinforced 5.7.)

## Section 1: Project identity

Personal AI Stock Advisor. Single-user portfolio + research tool for Indian NSE equities. Built for and by Sahil Doshi (Senior Consulting Engineer, MongoDB, India).

**Strict design constraint overriding everything:** the system never executes trades. Sahil trades manually in ICICI Direct. The system records, analyzes, and advises only. Any feature that would auto-place an order is permanently out of scope.

Not regulatory advice. Dossiers/suggestions use phrasing like "the system flagged this because…", "this is a good buy/sell because…". The user decides; the user trades. Goal: maximise investments / grow money. Every feature is judged on whether it helps: **Buy better, Sell better, Avoid mistakes** (concentration, FOMO, panic sells, missed corporate actions), or **Reduce costs** (taxes, fees, dead-capital opportunity cost). Anything else is decoration and gets cut.

**Explicitly NOT a goal:** dividend tracking, accounting, financial planning, tax filing, goal-based planning. (Full exclusion list: Section 21.)

## Section 2: User communication preferences (apply to all chats)

* Honest, slightly contrarian opinions over fake agreement. Push back when you disagree.
* Build right, no shortcuts. No avoidable rework.
* Math accuracy and legal compliance matter — call out anything mathematically wrong or legally non-compliant immediately.
* Use existing project conventions; do not invent parallel patterns.
* Give full file contents OR exact find-and-replace. Never "rest unchanged" / "// existing code". Don't truncate important code.
* Prefer meaningful units of work — testable, not ping-pong-tiny.
* Concrete test commands when appropriate. Files → canvas artifacts; tests → chat fenced blocks.
* Every mapping table Action column: NEW FILE / REPLACE EXISTING / PATCH.
* User edits on Mac, commits, pushes. EC2 is for build/test/deploy/debug. Assistant produces artifacts the user pastes; never edits Mac files directly.
* Every code/file delivery → paste-ready `git add .` + `git commit -m` block in project commit-message style.
* Every test block → starts with `ssh ubuntu@100.112.20.41`, curls against `localhost:8000`. Never the Tailscale IP from the Mac. (Frontend-only: `~/deploy-ui.sh` + `npm run build`/lint on EC2.)
* Project_State.md AND master_todo.md are ALWAYS full-file replacements.
* ASK FOR CURRENT BACKEND SHA BEFORE PROPOSING ANY CODE CHANGE; re-read the file at that SHA before patching. (Chat 5.)
* Before documenting what a script does, read its body at HEAD; before documenting a cron line, verify argparse accepts the flags. (Chat 5.5.)
* AT NO POINT make code changes from memory — construct the GitHub URL and re-read from source. (Chat 5.7.)
* When continuing the master plan: read master_todo.md current-position pointer FIRST, confirm next item with the user, then proceed. (Chat 5.8.)

## Section 3: Tech stack

**Backend:** Python 3.12 · FastAPI · Pydantic v2 (routers use `pattern=` not `regex=` post Chat 5 A19; round-trip / `ge=0` hardening post 5.6; ISIN `Path()` params on the two `/suggestions/{isin}` endpoints carry `pattern=r"^[A-Z0-9]{12}$"` post 5.13 TD31) · MongoDB Atlas M10 (ap-south-1) · uv (package manager) · yfinance (prices/fundamentals/earnings, free tier) · Anthropic Claude SDK (Sonnet 4.5 dossiers, Haiku 4.5 classification) · Tavily (news search, free tier, **daily** quota enforced atomically as of 5.14 TD33) · Resend (transactional email — all via `notify.email()` as of Chat 5 A2; transient 5xx/429 retried once with 30s backoff as of 5.15 TD34) · ntfy (push — public `ntfy.sh` for all paths; self-hosted private decommissioned TD8).

**Frontend:** Next.js 16 (Turbopack) · React 19 · TypeScript strict · Tailwind v4 · shadcn/ui Nova preset · Recharts · TanStack Query (mutations use `refetchQueries`, synchronous; the two `invalidateQueries` outliers in notes-panel.tsx + refresh-button.tsx swapped in 5.13 TD28) · react-hook-form + zod · sonner · next-themes.

**Hosting:** AWS EC2 t3.micro (ap-south-1), Elastic IP 3.111.254.128 (whitelisted in Atlas) · Tailscale-only app traffic, no public ingress, no Caddy · MongoDB Atlas M10 (separate; access list = EC2 EIP + dev IPs).

## Section 4: Infrastructure paths and ports

**Network:** EC2 Tailscale IP `100.112.20.41` · EC2 Elastic IPv4 `3.111.254.128` · SSH `ssh ubuntu@100.112.20.41`. Backend port: **EC2 8000, Mac local 8001**. Frontend port: 3000 (both). Always specify which machine. Convention: "SSH into EC2 first, then curl localhost:8000."

**Repo paths — Mac:** `~/Projects/Personal/ai-stock-advisor/ai-stock-advisor-backend` and `.../ai-stock-advisor-frontend`. **EC2:** `/home/ubuntu/ai-stock-advisor-backend` (`~/ai-stock-advisor-backend`) and `.../ai-stock-advisor-frontend`.

**Secrets** (resolved in `app/config/settings.py`):
```
EC2_SECRETS = Path("/etc/portfolio-advisor/secrets.env")
LOCAL_SECRETS = Path(__file__).resolve().parents[2] / ".env"
SECRETS_FILE = EC2_SECRETS if EC2_SECRETS.exists() else LOCAL_SECRETS
```
EC2: `/etc/portfolio-advisor/secrets.env` (chmod 600, root). Mac: `<repo>/.env` (chmod 600, gitignored). Uses pydantic-settings `SettingsConfigDict(env_file=..., env_file_encoding="utf-8", case_sensitive=True, extra="ignore")` — reads the file directly into Settings; secrets are NOT exported to `os.environ`. If anyone suggests `~/secrets/secrets.env` on EC2, it's wrong. `NTFY_PUBLIC_TOPIC_DIGESTS` must be present (required, no default; subscribe iPhone ntfy app before cron). When rotating the Atlas password, update BOTH secrets files in one session; URL-encode special chars via `python3 -c "from urllib.parse import quote_plus; print(quote_plus('PASTE'))"`. `NTFY_URL/USER/PASS` removed from settings.py + secrets file (TD9, 5.5).

**Deploy scripts (EC2):** `~/deploy.sh` (pull backend, `uv sync`, restart `portfolio-advisor.service`) · `~/deploy-ui.sh` (pull frontend, `npm install --legacy-peer-deps`, `npm run gen-api`, `npm run build`, restart `portfolio-advisor-ui.service`). `gen-api` regenerates `lib/api-types.ts` (gitignored) against the running backend's OpenAPI; on Mac override `API_OPENAPI_URL=http://100.112.20.41:8000 npm run gen-api` or skip — `lib/api-types.ts` is not used at runtime; `lib/api.ts` is hand-typed.

**systemd (EC2):** `portfolio-advisor.service` — `uvicorn app.main:app --port 8000 --host 0.0.0.0`, user ubuntu, `PYTHONPATH=/home/ubuntu/ai-stock-advisor-backend`, `PYTHONUNBUFFERED=1`, journald, single process / single worker (no `--workers`). Because there's no `--workers` and handlers are `sync def`, concurrent requests run in Uvicorn's **threadpool** (threads within one process). This is why TD20 per-ISIN serialization uses a Mongo advisory-lock doc (cross-thread AND cross-process), not `asyncio.Lock`; why the Tavily check-then-act was a real TOCTOU race (TD33); and why the TD34 `time.sleep(30)` blocks ONE threadpool worker (anyio default 40-thread pool → acceptable on a single-user box). `portfolio-advisor-ui.service` — `next start` port 3000 with hardening (NoNewPrivileges, PrivateTmp, ProtectSystem=strict, ReadWritePaths = frontend dir + /tmp). Sudoers `/etc/sudoers.d/portfolio-advisor-systemctl` lets ubuntu restart both passwordless.

**Log rotation (2026-05-24):** `/etc/logrotate.d/portfolio-advisor` rotates all `/home/ubuntu/cron-*.log` weekly (rotate 4 · compress+delaycompress · notifempty+missingok · copytruncate · `su ubuntu ubuntu`). Daily via OS `/etc/cron.daily/logrotate`. Force: `sudo logrotate -f /etc/logrotate.d/portfolio-advisor`. The old `0 0 * * 0 find … -size +10M` truncation line was verified ABSENT and logrotate confirmed (TD10/#2, 5.9). The 02:30 IST `cron-news-purge.log` (TD27) is covered by the existing glob. The `cron-heartbeat-fallback.log` (TD38, 5.18) also matches the `cron-*.log` glob — no new rotation config.

**Repos:** backend `https://github.com/doshisahil95/ai-stock-advisor-backend` · frontend `https://github.com/doshisahil95/ai-stock-advisor-frontend`.

**Last verified SHAs (Chat A closed, 2026-06-14):**
* Backend: **`fae6edf446dab815982b767b8f9a15c2fe36e6b5`** (Chat A code/doc HEAD — the #48 doc-only commit; the Chat A `Project_State.md` + `master_todo.md` doc commit advances it further — pin next chat). Chat A shipped seven items across five commits: #34 + #35 (`bd52c6b`), #25 (`1340396`), #49 + #26 (`6032b64`), #47 (`4b638e6`), #48 (`fae6edf`). Opened at `c4b50364eb5dd12bca46649c702afcd00677eb5d` (the 5.19 doc commit). Backend + doc only.
* Frontend: **`f59958015b8b07b6e84e3add7b4a302d32b43490`** (unchanged since 5.13 — chats 5.14–5.19 and Chat A backend/doc-only).
* Prior code-HEAD closes: 5.19 `7fcda9e` (TD39 cron_health_check self-failure dual-transport alert) · 5.18 `0515fef` (TD38 fallback heartbeat log + dual-source health check) · 5.17 `1d627d7` (TD37 reject NaN in _to_decimal) · 5.16 `f4168b3` (TD35 explicit inserted_id flow) · 5.15 `7d77b9c` (TD34 notify retry) · 5.14 `4ac2c95` (TD33 atomic Tavily) · 5.13 backend `090d96c` (TD29/31/32), frontend `f59958` (TD28) · 5.12 `49bf33f` (TD26 then TD27) · 5.11 `a2806cd` (TD23/24/25) · 5.10 `b34721e` (final of 5 commits `17f9f94`→TD18→`5cf3087`→`fb23307`→`b34721e`).

## Section 5: Backend file map

Layout under `app/` and top-level (verified against tree at SHA `ce5e746`; subsequently touched files tagged with the chat/TD that changed them — pending `master_todo #N` notes are live work). Re-verified against the Chat A tree listing at backend HEAD `fae6edf` — no file additions/deletions this chat (all Chat A changes were edits to existing files).

```
app/
  main.py                     FastAPI bootstrap, router includes, lifespan
                              (lifespan pings Mongo + ensure_indexes; no scheduler). (done: #34 GET /health now returns 503 + {"status":"degraded","mongo":"fail"} on ping() failure, 200 + {"status":"ok","mongo":"ok"} on success — was hardcoding status=ok/200; yfinance deliberately NOT probed). master_todo #38: JSON-structured logging
  agents/__init__.py          empty package placeholder
  scheduler/__init__.py       empty placeholder (TD21: candidate home for registry-rendered schedule tooling)
  config/settings.py          pydantic-settings; loads secrets. F2b: NTFY_PUBLIC_TOPIC_DIGESTS (required). (done: TD9 NTFY_URL/USER/PASS removed)
  db/
    client.py                 Mongo client, get_db(), Collections accessor (incl. monitored_stocks_audit F10, earnings_calendar F14, recompute_locks TD20). NOTE: app DB name is `portfolio` (MONGODB_DB_NAME default), NOT `portfolio_advisor` (5.12 lesson)
    indexes.py                ensure_indexes() on startup. (done: TD20 recompute_locks acquired_at TTL 60s; TD26 prices_intraday captured_at_ttl ASC 90d alongside captured_at_desc). tavily_quota has unique date_unique on date_utc — the primitive the TD33 atomic claim relies on
  models/
    _common.py                utcnow(), Decimal128/ObjectId helpers. (done: #22/TD37 _to_decimal rejects NaN float (v != v) in the float branch -> ValueError("NaN not allowed"); surfaces as 422 via Money BeforeValidator)
    instrument.py             Instrument. (fix F20: populate_by_name + _id alias)
    holding.py                Holding (active position)
    transaction.py            Transaction (BUY/SELL/SPLIT/BONUS/DEMERGER). (5.6 ge=0; fix F29/F80/F82)
    fundamentals.py           InstrumentFundamentals (per-ISIN, per-refresh)
    earnings_event.py         F14 EarningsEvent (one doc per ISIN per earnings_date)
    suggestion.py             SuggestionRun, SuggestionOutcome, CandidateScore, SignalScore, GateResult. F2 direction; 5.6 round-trip. SuggestionRun.id = PyObjectId|None Field(default=None, alias="_id") — POPULATED post-insert by _persist_run since 5.16 (TD35). (TD7/#45 deferred)
    news.py                   NewsArticle (only news model). 5.12: bulky field is `body_text` (NOT `body`); `body_purged_at` stamped by purge cron (TD27)
    monitored_stock.py        MonitoredStock + MonitoredStockFeedbackPatch. (A1 Literal aligned). (TD1/#43 deferred: direction-aware — note: #26 added direction-aware RELABEL on the feedback payload/outcome filter, but monitored_stocks itself stays direction-agnostic)
    macro_signal.py           placeholder
    conversation.py           placeholder (Chat 6 / #27 — NEXT)
    reconciliation.py         ReconciliationSnapshot (fix F16/F17)
    cost_basis_adjustment.py  CostBasisAdjustment (fix F18/F19)
    alert_log.py              placeholder
    digest.py                 placeholder (delivery audit lives in `digest_deliveries`)
    price_daily.py            placeholder (collection writers use raw dicts)
    symbol_override.py        SymbolOverride (fix F79)
    user_profile.py           UserProfile (singleton, _id="sahil")
  routers/
    holdings.py               /portfolio/holdings*, /sell, /preview-sell, /history, /transactions. (done: #5 validate_replay on /sell; #6 dup list_transactions deleted, get_holding_transactions sole handler; #7 try/except around recompute_holding -> recorded_with_warning, module logger added; #15/TD29 dead `from pydoc import doc` removed)
    portfolio.py              /portfolio/summary.  master_todo #30: utcnow() sweep (line 43)
    transactions.py           /transactions/search, CRUD, audit. (fix F21 reason required). (done: #4 write-before-apply audit-then-apply; #18/TD32 dropped $options:i on search regex — line 113 {"$regex": f"^{escaped}"}, case-sensitive on purpose, uses (symbol, trade_date) index). master_todo #31: tz-aware datetime sweep
    reconciliation.py         /reconciliation/snapshot, /snapshots, /auto-snapshot
    instruments.py            /instruments (symbol_overrides CRUD)
    cost_basis.py             /cost-basis/adjustments
    suggestions.py            /suggestions/latest, /runs, /runs/{id}, /performance, /{isin}/feedback, /{isin}/audit, /feedback/audit/recent. F2 ?direction; A1 MonitoredStockFeedbackPatch; A19 Query() pattern=. (done: #17/TD31 ISIN pattern=r"^[A-Z0-9]{12}$" on the two /{isin} Path params, lines 240+260; #26 direction-aware feedback relabel — SuggestionFeedback gains direction: Literal["buy","sell"]="buy", outcome filter routes buy via {$or:[{direction:buy},{direction:{$exists:false}}]} and sell via {direction:"sell"}; does NOT close TD1/#43)
    cron.py                   /cron/heartbeats (F4)
  services/
    instrument_service.py     lookup_isin, bulk_lookup_isins, refresh
    yfinance_lookup.py        thin yfinance Ticker wrapper. (fetch_metadata swallows all exceptions -> safe-default dict; recompute on unknown symbol never throws)
    price_service.py          EOD+intraday fetch, bulk_get_latest_prices, annotate_with_current_price, get_previous_close. IST + _to_ist() helpers (TD23). (fix F7/F8 NaN guards). (done: #9/TD23 holiday guard in _intraday_row_from_df (latest-bar IST date != today -> None); #10/TD24 price_stale docstring aligned to code (6 calendar days canonical); #11/TD25 bulk_get_previous_closes rewritten to per-ISIN find_one; TD26 captured_at written as BSON Date so the TTL actually expires docs). master_todo #31: tz-aware sweep (line 155); #41 (Chat 9): stop_loss alert trigger
    holdings_service.py       recompute_holding (per-ISIN advisory-lock wrapper) + _recompute_holding_impl (read-replay-overwrite body) + _per_isin_recompute_lock (CM), validate_replay, preview_sell, _to_decimal. (5.6 preview_sell SPLIT/BONUS lot-walk fix). (done: #8/TD20 serialized per-ISIN via recompute_locks + 60s TTL)
    portfolio_service.py      compute_summary
    transactions_audit_service.py  log_change, get_audit_for_transaction. (5.10: log_change invoked BEFORE apply — TD16)
    monitored_stocks_audit_service.py  F10 log_change (write-before-apply)
    reconciliation.py         take_auto_snapshot, drift detection, _send_drift_alerts (ntfy + email), _send_auto_drift_alert (ntfy ONLY). (fix F1/F23). A2 part2 branches on notify.email() result["ok"] (unchanged after TD34 retry). (done: #25 take_auto_snapshot fires push_public("price",...) on invested drift > DRIFT_ALERT_THRESHOLD_INVESTED vs the last manual snapshot, ntfy ONLY, rising-edge deduped (fires only when this snapshot has drift AND the most recent prior auto snapshot did not), records drift_invested/has_drift/alerts_sent on the auto snapshot; current-value drift NOT alerted on the auto path). master_todo #31: tz-aware sweep (lines 78, ~138)
    cost_basis_service.py     get_active_adjustments, total_adjustment_amount
    fundamentals_service.py   yfinance provider, refresh_one, refresh_universe; F14 earnings refresh.  master_todo #30: utcnow() sweep (lines 370, 485, 505)
    tavily_client.py          quota-tracked wrapper, TavilyQuotaExceeded. (done: #19/TD33 quota guard is ONE atomic find_one_and_update in _increment_quota filtered on calls_today < TAVILY_DAILY_CALL_LIMIT (upsert); cap-hit via DuplicateKeyError on unique date_unique index; get_today_quota() pre-check in search() removed; added `from pymongo.errors import DuplicateKeyError`; cap calls-only; get_today_quota/get_quota_history kept read-only). master_todo #31: tz-aware sweep (lines 50, ~55)
    news_fetcher.py           fetch_for_instrument, fetch_for_universe. (imports tavily_client.search/TavilyError/TavilyQuotaExceeded — all preserved across TD33)
    news_classifier.py        Haiku batch classifier, retry pass. (fix F27). (TD27 purge cron reclaims body_text after classify)
    news_signals.py           compute_news_signals_for_isin, _bulk
    scoring_service.py        extract_signals, score_candidates, weights, gates. F14 earnings-proximity gate shared buy+sell; F2 sell-side scoring; A3+A4 composite_for_candidate writes raw_value.  master_todo #30: utcnow() sweep (lines 116, 813, 890)
    dossier_service.py        generate_dossiers_for_top_k, Sonnet. F2 sell-side prompt + position context. master_todo #30: utcnow() sweep (lines 166, 192). (TD3/#44 deferred)
    suggestion_engine.py      run_suggestions (full pipeline); get_excluded_isins (F6+F5b: rejected 90d, passed this-run, acted 30d). F2 direction. A17 stale comment refreshed. (done: #21/TD35 _persist_run sets run.id = result.inserted_id (line ~809) on EVERY persist path (success/zero-candidate/except), so run_suggestions returns a SuggestionRun carrying its persisted _id; the two standalone-path send_weekly_digest(run) calls pass run_id=run.id)
    outcome_tracker.py        create_outcomes_for_run, snapshot_open_outcomes, compute_system_performance. F2 direction stamp + read-time sign-flip. NOTE (#47): snapshot_open_outcomes returns its count under the key `active_outcomes` (NOT `open_outcomes`) — renamed in Commit A.5 when selection broadened from "open" to all non-expired; the track_suggestion_outcomes cron read the stale key and KeyError'd daily until Chat A fixed the consumer
    digest_delivery.py        send_weekly_digest, send_combined_digest. F2b ntfy push_public("digests",...); F2b cea8eee direction-aware breakdown; A2 part1 delegates to notify.email() (TD34 retry lives inside notify.email(); _send_email still branches on result["ok"]). (done: #21/TD35 send_combined_digest reads buy_run_id = buy_run.id (line ~565); internal find_one re-derivation DELETED; signature UNCHANGED (sole caller _do_both compatible); delivery row keys on BUY run id for combined digests; send_weekly_digest's run_id param now receives a value on the standalone path)
    explainability.py         SIGNAL_META, GROUP_META, GATE_META, FEEDBACK_META, PAGE_INTRO + PAGE_INTRO_SELL, enrich_run, enrich_candidate. F2 metas extended; fix F28; 5.5 TD11 raw-value fallback
    notify.py                 push_public, email. A2: email returns {ok,id,error}, optional text=. TD8 push_private/PrivateTopic removed. push_public RAISES on failure (_publish -> raise_for_status). (done: #20/TD34 email() retries once (2 attempts) on transient 429/5xx with 30s blocking backoff; 400s+no-status return immediately; added logging+time imports, _email_error_status(), _is_transient_email_error(), constants _EMAIL_MAX_ATTEMPTS=2, _EMAIL_RETRY_BACKOFF_SECONDS=30, _EMAIL_TRANSIENT_STATUSES; {ok,id,error} contract + no-raise UNCHANGED -> 3 callers untouched). NOTE: #25 + #35 both call push_public GUARDED (it raises on transport failure)
    cron_heartbeat_service.py F4 cron_run CM, CRON_REGISTRY, get_recent_heartbeats, ist_today_window_utc. A6/A6.5/A7 fixes. (done: TD14 registry entry renamed run_weekly_suggestions -> weekly_suggestions; TD27 purge_news_bodies CronSpec added; #23/TD38 _persist's except now calls _append_fallback(doc) (was `pass`) -> appends JSON-per-line heartbeat to _FALLBACK_LOG_PATH="/home/ubuntu/cron-heartbeat-fallback.log" (best-effort, never raises); new reader count_today_heartbeats_from_fallback() mirrors count_today_heartbeats (+_parse_fallback_dt ISO->naive-UTC, +_isoformat_or_none, +import json); #49/TD40 idle weekly_suggestions_sell CronSpec now expected_weekdays=set() so cron_health_check no longer sends a false Sunday MISSING — do NOT disturb _append_fallback / count_today_heartbeats_from_fallback / _persist)
scripts/
  __init__.py
  init_db.py
  refresh_instruments.py        (A13 docstring corrected to NSE EQUITY_L.csv)
  refresh_prices.py
  refresh_prices_intraday.py    (done: #35 insert_intraday_quotes wrapped in try/except -> GUARDED push_public("errors",...) on failure (market open by construction once rows non-empty) then re-raise so cron_run records the failure heartbeat). master_todo #41 (Chat 9): stop_loss alert
  take_reconciliation_snapshot.py
  seed_nifty100.py              CORRECTLY NAMED. Reads ind_nifty100list.csv. (TD12 resolved-as-doc-fix)
  seed_cost_basis_adjustments.py
  import_orderbooks.py          (calls recompute_holding -> now per-ISIN locked, TD20)
  reconcile_staging.py
  promote_staging.py            (calls recompute_holding -> now per-ISIN locked, TD20)
  add_manual_transactions.py    (done: #5 validate_replay on manual SELL path — aborts RuntimeError, no silent insert)
  refresh_fundamentals.py       F14 default universe NIFTY100 ∪ active holdings. (Chat 8/#29 will extend for watchlist)
  fetch_news_for_universe.py    (A16 --include-held on crontab). (Chat 8/#29 watchlist). Only prod path exercising Tavily quota guard (Sun 06:30 IST; TD33)
  run_weekly_suggestions.py     F2 --direction=buy|sell|both (default buy). argparse accepts ONLY --direction/--no-notify/--skip-dossiers (run_type hardcoded "scheduled"). (done: #1/TD14 bogus --notify --run-type scheduled crontab flags removed; #21/TD35 _do_both attaches outcomes via buy_run.id/sell_run.id (create_outcomes_for_run ~159/170); two find_one re-derivations + local `from app.db.client import Collections` import DROPPED)
  track_suggestion_outcomes.py  (done: #47/TD22 — was FAILING every weekday: main() read stats["open_outcomes"] but snapshot_open_outcomes() returns "active_outcomes"; KeyError at line 27 inside cron_run -> daily failure heartbeat -> 21:00 health email; now reads stats["active_outcomes"] + renamed metadata key/print label; safe rename, the heartbeat never persisted the old key)
  cron_health_check.py          F4 daily 21:00 IST; dual-transport (commit 8). Confirmed healthy 5.9. Email leg flows through notify.email() (TD34 retry). (done: #23/TD38 main() imports count_today_heartbeats_from_fallback and merges its counts into the Mongo counts per cron BEFORE the MISSING/FAILED eval; records metadata.fallback_heartbeats_merged; merge never double-counts (a run lands in one source)) (done: #24/TD39 main()'s per-cron heartbeat-read loop (the ONLY Mongo reads — the count_today_heartbeats calls) wrapped in try/except; on a Mongo-read failure fires an "anomaly: health-check itself failed" alert on BOTH transports (push_public("errors",...) GUARDED + notify.email()), then re-raises so cron_run records the run failed (heartbeat -> disk fallback); #23/TD38 merge loop preserved verbatim inside the wrap; module docstring extended). NOTE: the Sunday `weekly_suggestions_sell` false MISSING this script used to emit is GONE as of #49/TD40 (idle spec expected_weekdays=set())
  smoke_test.py                 (TD8 dropped push_private)
  purge_news_bodies.py          (done: #13/TD27 daily 02:30 IST; $unset body_text + stamp body_purged_at on classified news_articles with fetched_at >30d; --dry-run; cron_run("purge_news_bodies") heartbeat; mirrors refresh_prices_intraday.py)
tests/
  __init__.py                   placeholder.  master_todo #33: stand up pytest harness
docs/
  data_flow.md                  (5 deliverable; 5.5 TD12 universe corrected). (done: #48/TD36 Tavily "monthly" -> "daily (resets 00:00 UTC)"; also fixed "00:00 IST on the 1st" -> "00:00 UTC each day")
  Project_State.md              THIS FILE (Chat A doc commit; recovered from 5.8 truncation in 5.9 — Section 18 TD15)
  master_todo.md                canonical ordered task list (Chat 5.8 NEW)
pyproject.toml                  master_todo #32: pin requires-python upper bound (declares resend>=2.4 — SDK whose typed errors TD34 classifies)
uv.lock
README.md                       (5 deliverable; 5.5 §8/§11/§5). (done: #48/TD36 Tavily "monthly" -> "daily (resets 00:00 UTC)"; corrected non-existent env var TAVILY_MONTHLY_QUOTA -> TAVILY_DAILY_CALL_LIMIT, enforcement in tavily_client not news_fetcher)
```

## Section 6: Frontend file map

Verified against tree at SHA `4f31b49` (unchanged 5.10–5.12; 5.13 touched notes-panel.tsx + refresh-button.tsx → frontend HEAD `f59958`; 5.14–5.19 + Chat A backend/doc-only).

```
app/
  layout.tsx · page.tsx (dashboard) · providers.tsx (ThemeProvider + TanStack QueryClient + ReactQueryDevtools) · globals.css · favicon.ico
  holdings/[isin]/page.tsx    drill-down (Chat 9/#41: stop_loss edit field)
  reconciliation/page.tsx · cost-basis/page.tsx · transactions/page.tsx · transactions/audit/page.tsx
  suggestions/page.tsx        F6 user_action collapsed render; F2 shadcn Tabs buy/sell
components/
  ui/                         shadcn primitives (alert-dialog, badge, button, card, chart, dialog, dropdown-menu, input, label, popover, select, separator, sheet, skeleton, table, tabs, textarea, tooltip)
  holdings-table.tsx          (Chat 9/#40: hide realized P&L)
  buy-sheet.tsx
  sell-sheet.tsx              Phase-1 manual SELL sheet with FIFO preview. NOT the F2 sell-side surface. OPEN FOLLOW-UP (5.10, NOT actioned): discriminates on absence of _id; a TD19 recorded_with_warning response (no _id) falls through its non-holding branch. Rare path; frontend handling deferred (out of Phase-2 scope).
  transaction-edit-sheet.tsx
  holding-header.tsx          (Chat 9/#40: hide realized P&L)
  holding-stats.tsx           (Chat 9/#40 + #41: realized P&L hide + stop_loss edit field)
  price-chart.tsx · transactions-list.tsx
  notes-panel.tsx             (done: #14/TD28 two mutation onSuccess invalidateQueries -> refetchQueries; minimal name-swap)
  recent-activity-card.tsx · sector-breakdown.tsx · stat-card.tsx · top-movers.tsx
  totals-row.tsx              (Chat 9/#40: hide realized P&L)
  reconciliation-badge.tsx · theme-provider.tsx · theme-toggle.tsx
  refresh-button.tsx          (done: #14/TD28 three invalidateQueries in await Promise.all -> refetchQueries)
  suggestion-card.tsx         F6 CollapsedFeedbackRow when user_action != null; F2 isSellSide branch
  explain-popover.tsx · page-intro.tsx
lib/
  api.ts                      hand-typed API client; SINGLE SOURCE OF TRUTH; F2 direction param, BucketKey, by_bucket
  format.ts                   inr, pct, colorForChange, dateTime, nf, date
  utils.ts                    cn() (clsx + tailwind-merge)
public/                       static SVGs
README.md                     (5 deliverable at SHA 9edfc8f; TD13 per-page reference at 4f31b49 — 7 routes)
AGENTS.md · CLAUDE.md · components.json (Nova) · package.json · package-lock.json
next.config.ts (default) · postcss.config.mjs · tsconfig.json (strict; "@/*"; bundler) · .npmrc (legacy-peer-deps)
```
No `middleware.ts`, no `.env.example`, no custom next.config overrides at HEAD. Tailscale is the auth perimeter.

## Section 7: Database collections (exhaustive)

All in Atlas M10. DB name from env `MONGODB_DB_NAME`; **live value is `portfolio`, NOT `portfolio_advisor`** (5.12 lesson). Accessed via `Collections.<name>()`. Indexes ensured at startup via `app/db/indexes.py`.

**Phase 1:**
* **instruments** — NSE/BSE master, daily from NSE EQUITY_L.csv. Fields: exchange, symbol, isin, name, instrument_type, segment, lot_size, tick_size, source, last_seen_at, last_changed_at, in_nifty100, nifty100_marked_at. ~2,368 total; ~100 in_nifty100. Indexes: (exchange, symbol) unique, isin, last_seen_at, last_changed_at, in_nifty100.
* **symbol_overrides** — manual ISIN aliases. Fields: exchange, symbol, isin, reason, created_at.
* **holdings** — one doc per ISIN, soft-deleted on full exit. Fields: isin, symbol, exchange, name, sector, industry, quantity (Decimal128), avg_cost, invested_amount, realized_pnl, first_purchased_at, last_traded_at, thesis, notes, stop_loss, target_price, tags, deleted_at. **INVARIANT: every query MUST include `deleted_at: None`.** Indexes: isin unique (partial: deleted_at is None), (deleted_at, last_traded_at). Writer: `recompute_holding(isin)` is the ONLY authoritative writer; serialized per-ISIN via `recompute_locks` (TD20). `realized_pnl` structural but HIDDEN in UI (#40). F2: target_price consumed by sell-side scoring; stop_loss wired by #41.
* **transactions** — append-only ledger. Fields: isin, symbol, exchange, type (BUY/SELL/SPLIT/BONUS/DEMERGER), trade_date, quantity (Decimal128), price, total_fees, remaining_quantity, notes, source, corporate_action.{ratio_from,ratio_to}, fully_consumed_at, deleted_at. **INVARIANT: never directly UPDATE/DELETE; PATCH/DELETE require reason, write transactions_audit first, then apply, then recompute_holding** (#4/TD16 SHIPPED 5.10; validate_replay runs first so a rejected change writes no audit row). Indexes: (isin, trade_date), (symbol, trade_date), trade_date. 5.6 ge=0 validators. 5.13 (TD32): GET /transactions/search prefix-matches symbol with `{"$regex": f"^{escaped}"}` (NO $options:i; case-sensitive on purpose; uses (symbol, trade_date) index).
* **transactions_staging** — ICICI import holding area, same shape. 5.10 (TD17): add_manual_transactions.py replays per-ISIN timeline + proposed SELL via validate_replay and ABORTS (RuntimeError) rather than insert an impossible SELL.
* **transactions_audit** — append-only, one doc per edit/delete. Fields: transaction_id, action, reason, changed_fields, performed_at, symbol. **INVARIANT: written BEFORE the change is applied** (#4/TD16 SHIPPED 5.10).
* **recompute_locks** (TD20, NEW 5.10) — per-ISIN advisory locks. Fields: _id (== isin), acquired_at. **INVARIANT:** acquired via atomic insert_one (unique _id index = one winner); released via delete_one in finally; competing acquirer spin-waits on DuplicateKeyError until free or 10s timeout (timeout -> RuntimeError, degraded by TD19 try/except to recorded_with_warning). Indexes: default _id unique; TTL on acquired_at (expireAfterSeconds=60). Accessor `Collections.recompute_locks()`; holder `_per_isin_recompute_lock` CM. Covers API handlers AND out-of-process scripts.
* **prices_daily** — EOD OHLCV, ~5y. Fields: isin, date, OHLC, volume, source. Indexes: (isin, date) unique.
* **prices_intraday** — latest intraday quote every 15 min during market hours. Fields: isin, symbol, date, captured_at, OHLCV, source="yfinance_5m_latest". **INVARIANT: append-only within a day.** TTL: `captured_at_ttl` (ASC, expireAfterSeconds = 90*86400 = 7776000) SHIPPED 5.12 (TD26) — coexists with non-TTL `captured_at_desc` (DESC) because ASC vs DESC are different key patterns; works because captured_at is a BSON Date. Indexes: isin_captured_at_desc, captured_at_desc, captured_at_ttl. Writer: `refresh_prices_intraday.py` → `_intraday_row_from_df`. #9/TD23: holiday guard (latest-IST date != today -> None). #35 (Chat A): an `insert_intraday_quotes` exception now fires a guarded ntfy + re-raises (failure heartbeat recorded).
* **reconciliation_snapshots** — our totals vs ICICI Direct. Fields: type, taken_at, our_invested, our_current_value, our_day_gain, icici_*, drift_invested_pct, drift_current_pct, drift_alerts, notes, plus drift_invested/has_drift/alerts_sent (manual path; #25 now also stamps these on the auto path). #25 (Chat A): take_auto_snapshot fires push_public("price",...) on invested drift > threshold vs the last manual snapshot — ntfy ONLY, rising-edge deduped (was silent to Mongo only).
* **cost_basis_adjustments** — audit trail for TMPV/TMCV per IT Act Section 49(2C).
* **user_profile** — single doc, _id="sahil".

**Phase 2:**
* **monitored_stocks** — user-feedback state + watchlist (F13). Fields: isin, status (Literal tracking/passed/rejected/watchlist), symbol, exchange, name, sector, industry, added_by, added_reason, added_at, thesis, conviction, conviction_history, target_buy_price, alert_above, alert_below, alert_on, tags, user_notes, last_reviewed_at, last_user_interest_at, acted_at, passed_at, rejected_at, last_feedback_action, last_feedback_at, last_feedback_note, created_at, updated_at. (A1 schema aligned; MonitoredStockFeedbackPatch). **INVARIANT (F10): writes preceded by monitored_stocks_audit_service.log_change(...).** Indexes: isin unique (PARTIAL, partialFilterExpression={"status":"tracking"}), (status, rejected_at). TD1/#43 deferred: direction-aware (note: #26's direction-aware relabel filters the OUTCOME query by direction; it does not add a direction field to monitored_stocks itself).
* **monitored_stocks_audit** (F10) — append-only. Fields: isin, action, previous_status, new_status, note, performed_at, _schema_version. **INVARIANT: writer invoked BEFORE update_one.** Indexes: (performed_at desc), (isin, performed_at desc).
* **instruments_fundamentals** — one doc per ISIN per refresh. Indexes: isin_latest_unique, fetched_at. F14: universe NIFTY100 ∪ active holdings.
* **earnings_calendar** (F14) — upcoming + historical per ISIN (yfinance Ticker.calendar). Fields: isin, symbol, exchange, earnings_date, source, source_raw, fetched_at, created_at. **INVARIANT: refresh deletes future events then re-inserts.** Indexes: (isin, earnings_date) unique, (earnings_date asc), (isin), (fetched_at desc).
* **news_articles** — classified news, one doc per URL. Fields: url, title, published_at, fetched_at, source, body_text, body_purged_at, entities_isins, themes, sentiment, sentiment_confidence, severity, classifier_summary, classified. Indexes: url unique, (entities_isins, classified, fetched_at), (classified, fetched_at), body_purged_at. body_text purged daily (TD27, 5.12): on classified docs with fetched_at >30d (NOT nullable published_at), $unset body_text + stamp body_purged_at; idempotent. Bulky field is `body_text` NOT `body` ($unset {body:""} would no-op).
* **suggestion_runs** — append-only run history. Fields: _id, _schema_version, run_date, run_date_ist, run_type, direction, status, started_at, finished_at, error, universe_size, excluded_*, candidates_*, config, top_candidates, all_candidates, top_k, notes. **INVARIANTS:** append-only; legacy persisted runs missing newer optional fields round-trip cleanly (5.6). 5.16 (TD35): `_persist_run` sets `run.id = result.inserted_id` on the in-memory run on every persist path; the model field `id: PyObjectId|None = Field(default=None, alias="_id")` existed but was never populated post-insert. Carrying it lets `_do_both` and `send_combined_digest` read `run.id` instead of re-deriving via `find_one(..., sort=[("run_date",-1)])`. Persisted doc unchanged. Indexes: (run_date desc), (run_date_ist, run_type), (status).
* **suggestion_outcomes** — one doc per top-K candidate per run. Fields: isin, symbol, suggestion_run_id, suggested_at, suggested_at_price, suggested_rank, suggested_composite_score, tracking_status, direction, price_at_{30,60,90,180}d, nifty_at_{30,60,90,180}d, excess_return_*, user_action_at, user_action_note, created_at, updated_at. **INVARIANTS:** snapshot eligibility `tracking_status != "expired"`; auto-flip to expired only at day 180 for "open"; `compute_system_performance(direction="sell")` sign-flips at read time. 5.16 (TD35): create_outcomes_for_run in --direction=both called with buy_run.id / sell_run.id (carried ids), not re-derived. #26 (Chat A): submit_feedback relabels the most recent non-expired outcome FOR THE SAME DIRECTION — buy via {$or:[{direction:buy},{direction:{$exists:false}}]}, sell via {direction:"sell"}. NOTE (#47): snapshot_open_outcomes returns its count under `active_outcomes`, NOT `open_outcomes`.
* **tavily_quota** — one doc per UTC day. Fields: date_utc (YYYY-MM-DD), calls_today, credits_today, per_use_case.<uc>.{calls,credits}, first_call_at, last_call_at. **INVARIANT: TAVILY_DAILY_CALL_LIMIT (default 200) enforced as hard ceiling on calls_today per UTC day; credits_today tracked NOT capped; resets 00:00 UTC** (README/data_flow "monthly" wording was STALE — corrected to daily in Chat A, #48/TD36). Indexes: unique date_unique on date_utc. #19/TD33 (5.14): quota guard is a SINGLE atomic find_one_and_update — `_increment_quota` filters `{date_utc: today, calls_today: {$lt: TAVILY_DAILY_CALL_LIMIT}}` upsert=True return_document=AFTER with existing $inc/$setOnInsert/$set; over the cap the existing doc no longer matches, the upsert attempts a second same-day insert, the unique index raises DuplicateKeyError -> TavilyQuotaExceeded (no credit on refusal). The get_today_quota() pre-check in search() removed (the TOCTOU window).
* **digest_deliveries** — audit log of weekly digests. Fields: run_id, run_date_ist, sent_at, top_count, subject, email_*, ntfy_*. F2: combined-digest sends attach to BUY run id. #21/TD35 (5.16): run_id sourced explicitly, not re-derived — combined digest writes `run_id = buy_run.id` (carried by _persist_run; old internal find_one deleted); standalone digest writes the real run_id via `send_weekly_digest(run, run_id=run.id)` (was writing None). TD14 IMPACT (RESOLVED 5.9): no rows written by Sunday cron while bogus flags live; after fix the --direction=both run writes one row per combined digest again (#1).
* **cron_heartbeats** (F4) — Fields: cron_name, started_at, finished_at, status, error, metadata, _schema_version. **INVARIANTS:** append-only, best-effort WITH DISK FALLBACK (5.18 #23/TD38: when the Mongo insert raises, `_persist` appends the heartbeat as JSON-per-line to `/home/ubuntu/cron-heartbeat-fallback.log` via `_append_fallback`, which never raises; `cron_health_check.main` merges Mongo + `count_today_heartbeats_from_fallback` counts so an insert lost to a transient Mongo outage is NOT a false MISSING — a run lands in at most one source, so no double-count); `_Heartbeat.meta` is an ATTRIBUTE (`ctx.meta = {...}`). 5.9 TD14: Sunday run writes cron_name="weekly_suggestions" (NOT run_weekly_suggestions); CRON_REGISTRY matches. 5.12 TD27: purge writes cron_name="purge_news_bodies". 5.19 #24/TD39: when `cron_health_check.main`'s OWN Mongo reads fail (Atlas unreachable), the health-check run is recorded `status="failure"` (its heartbeat falls to the same disk fallback) and a dedicated self-failure alert fires — see Section 9. Chat A #47: `track_suggestion_outcomes` now records SUCCESS (was a daily real failure from a KeyError in its own body — TD22, now fixed); #49 removed the idle `weekly_suggestions_sell` Sunday false MISSING. Indexes: (cron_name, started_at desc), (started_at desc), TTL on started_at (60 days).

**Scaffold (not actively written):** digests, alerts_log, conversations (Chat 6/#27 — NEXT), macro_signals.
**Future:** none pending. F11 read-only reformatter; F13 watchlist reuses monitored_stocks status="watchlist".

## Section 8: API endpoints (exhaustive)

**Phase 1**
```
GET    /health                                       (done #34: pings Mongo; 200 {"status":"ok","mongo":"ok"} or 503 {"status":"degraded","mongo":"fail"})
GET    /portfolio/holdings                           Holding[]
GET    /portfolio/holdings/{isin}                    Holding
POST   /portfolio/holdings                           Holding (BUY)            (#7: recorded_with_warning on recompute fail)
PATCH  /portfolio/holdings/{isin}                    Holding (notes/thesis/stop_loss/target_price/tags only)
POST   /portfolio/holdings/{isin}/sell               Holding OR {message, realized_total}   (#5 validate_replay; #7 recorded_with_warning)
POST   /portfolio/holdings/{isin}/preview-sell       SellPreview
GET    /portfolio/holdings/{isin}/history?days=N     PriceBar[]
GET    /portfolio/holdings/{isin}/transactions       Transaction[]            (#6 dup handler deleted)
GET    /portfolio/summary                            PortfolioSummary
GET    /transactions/search?...                      {results, total}         (#18 dropped $options:i; case-sensitive prefix uses index)
GET    /transactions/{id}                            Transaction
PATCH  /transactions/{id}                            Transaction (requires reason)   (#4 write-before-apply)
DELETE /transactions/{id}                            {deleted: true} (requires reason) (#4 write-before-apply)
GET    /transactions/audit/recent?limit=N            AuditEntry[]
GET    /transactions/{id}/audit                      AuditEntry[]
POST   /reconciliation/snapshot                      ReconciliationSnapshot (manual)
GET    /reconciliation/snapshots                     ReconciliationSnapshot[]
POST   /reconciliation/auto-snapshot                 ReconciliationSnapshot (cron)   (done #25: fires ntfy push_public("price",...) on invested drift > threshold vs last manual snapshot, rising-edge deduped)
GET    /cost-basis/adjustments                       CostBasisAdjustment[]
GET    /instruments                                  symbol_overrides list
POST   /instruments                                  symbol_overrides upsert
DELETE /instruments/{exchange}/{symbol}              delete override
```

**Phase 2**
```
GET    /suggestions/latest?direction=buy|sell        SuggestionRun + enrichment
GET    /suggestions/runs?direction=buy|sell&...      {runs, total, limit, skip}
GET    /suggestions/runs/{run_id}                    SuggestionRun + enrichment
GET    /suggestions/performance?direction=buy|sell   SuggestionPerformance with by_bucket
POST   /suggestions/{isin}/feedback                  {isin, action, status, previous_status}   (#17 ISIN pattern; done #26: SuggestionFeedback has direction:Literal["buy","sell"]="buy", outcome relabel filters by direction)
GET    /suggestions/{isin}/audit?limit=N             MonitoredStocksAuditEntry[] (F10)         (#17 ISIN pattern)
GET    /suggestions/feedback/audit/recent?limit=N    MonitoredStocksAuditEntry[] (F10)
GET    /cron/heartbeats?limit=N                      {heartbeats, health_summary}
```
`/cron/heartbeats` shape: `heartbeats` newest-first (default 200, max 1000); `health_summary` per-cron rows {cron_name, description, schedule, expected_today, min_runs_per_day, last_run_at, last_status, last_error, today_total, today_success, today_failure, today_skipped, healthy}. `healthy = true iff (not expected today) OR (today_success + today_skipped >= min_runs_per_day AND today_failure == 0)`.

**Future (planned, see master_todo):**
```
POST   /chat/suggestions          (F1 / Chat 6 / #27 — NEXT)
POST   /chat/holdings/{isin}       (F3 / Chat 6 / #27 — NEXT)
GET    /portfolio/risk-summary     (F12 / Chat 7 / #28)
GET    /portfolio/by-tag?tag=X     (F15 / Chat 7 / #28)
POST   /watchlist/{isin}           (F13 / Chat 8 / #29)
DELETE /watchlist/{isin}           (F13 / Chat 8 / #29)
GET    /watchlist                  (F13 / Chat 8 / #29)
GET    /tax/capital-gains?fy=YYYY-YY (F11 / Chat 9 / #39)
POST   /admin/recompute/{isin}     (Ops gap / #36)
```

**Sell endpoint response shape (critical, often confused):** `POST /portfolio/holdings/{isin}/sell` returns one of: (a) full updated Holding (partial sell), (b) `{message: "Position fully exited", realized_total: "<string Decimal>"}` (full exit), (c) `{status:"recorded_with_warning", isin, warning}` (TD19 — SELL persisted but recompute_holding raised; holding may be stale). Frontend discriminates via type guard on `_id`. OPEN follow-up (5.10): the recorded_with_warning shape has no `_id`, so SellSheet treats it like full-exit — rare path, deferred.

## Section 9: Cron registry on EC2

`crontab -l` for current state. Every script is heartbeat-instrumented via `cron_run()`; the daily `cron_health_check` (21:00 IST) consumes them. `CRON_REGISTRY` in `cron_heartbeat_service.py` is the in-code mirror — keep both in sync.

**Live crontab (10 lines; verified 5.9 for 9, 5.12 added the 02:30 purge):**
```
# Phase 1 (heartbeat-instrumented Chat 2)
0 3 * * *     ... scripts/refresh_instruments.py        >> cron-instruments.log 2>&1
0 19 * * 1-5  ... scripts/refresh_prices.py             >> cron-prices.log 2>&1
30 19 * * 1-5 ... scripts/take_reconciliation_snapshot.py >> cron-reconciliation.log 2>&1
*/15 9-15 * * 1-5 ... scripts/refresh_prices_intraday.py >> cron-prices-intraday.log 2>&1
# Phase 2 (registered Chat 2 via F5a)
0 6 * * 0     ... scripts/refresh_fundamentals.py       >> cron-fundamentals.log 2>&1
30 6 * * 0    ... scripts/fetch_news_for_universe.py --include-held >> cron-news.log 2>&1
# Sunday 07:00 IST — weekly suggestions, combined buy+sell digest (TD14 SHIPPED 5.9)
0 7 * * 0     ... scripts/run_weekly_suggestions.py --direction=both >> cron-suggestions.log 2>&1
45 19 * * 1-5 ... scripts/track_suggestion_outcomes.py  >> cron-outcomes.log 2>&1
# F4 cron health (Chat 2; dual-transport Chat 5 commit 8)
0 21 * * *    ... scripts/cron_health_check.py          >> cron-health.log 2>&1
# Daily news body purge — 02:30 IST (TD27, SHIPPED 5.12)
30 2 * * *    ... scripts/purge_news_bodies.py          >> cron-news-purge.log 2>&1
```
(Each line is `cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python <script>`.)

**CRON_REGISTRY (11 entries, 5.12):** refresh_instruments, refresh_prices, refresh_prices_intraday, take_reconciliation_snapshot, refresh_fundamentals, fetch_news_for_universe, weekly_suggestions (renamed from run_weekly_suggestions, 5.9 TD14), track_suggestion_outcomes, cron_health_check, purge_news_bodies (NEW 5.12, daily, WEEKDAYS_ALL), weekly_suggestions_sell (idle; kept for topology flexibility — as of Chat A #49/TD40 its CronSpec carries `expected_weekdays=set()` so `is_expected_today()` is always False and `cron_health_check` no longer emits the false Sunday `MISSING: weekly_suggestions_sell`; the umbrella `weekly_suggestions --direction=both` cron covers both directions. Restore to `{6}` ONLY if you split the crontab into a standalone sell-side job that logs its own heartbeat under this cron_name).

**No silent failures:** every cron = log file path AND heartbeat instrumentation AND a CronSpec entry. All three. AND the CronSpec.cron_name MUST equal the string the script passes to `cron_run()` — a mismatch produces a permanent phantom MISSING even after the cron is fixed (5.9 TD14; re-confirmed 5.12 for purge_news_bodies). 5.18 (#23/TD38) closed a related gap: a heartbeat whose Mongo INSERT fails (Mongo unreachable at finish) used to vanish (`except Exception: pass`) → false MISSING for a cron that actually ran; it now falls back to `/home/ubuntu/cron-heartbeat-fallback.log` and `cron_health_check` reads both. This hardens heartbeat PERSISTENCE only — a cron whose own body throws is still a real failure and is correctly reported. Chat A #47 fixed exactly such a real-failure case: `track_suggestion_outcomes` was failing daily on a `KeyError('open_outcomes')` in its own body (`snapshot_open_outcomes` returns `active_outcomes`) — now reads the correct key and records SUCCESS.

**Health-check self-resilience (5.19 #24/TD39):** `cron_health_check.main`'s ONLY Mongo reads are the per-cron `count_today_heartbeats` calls in the registry loop. That loop is now wrapped in `try/except`; if those reads raise (e.g. Atlas unreachable) the script cannot evaluate any cron and the normal anomaly path is unreachable, so it fires a dedicated "anomaly: health-check itself failed — could not read cron heartbeats from MongoDB" alert on BOTH transports — `push_public(channel="errors", priority="urgent", ...)` GUARDED in its own try/except (because `push_public` RAISES on failure, so a failed self-failure push must not block the email leg or mask the original error) + `notify.email(...)` — then RE-RAISES so `cron_run` records the run as a `failure` (its heartbeat → the #23 disk fallback since Mongo is down) and tomorrow's check re-evaluates. The pure `ist_today_window_utc()` (time math), disk-only `count_today_heartbeats_from_fallback()`, and in-memory `get_registry()` stay outside the wrap, and the #23 dual-source merge loop is preserved verbatim INSIDE the wrap. Hardens the health-check script itself; does NOT touch the failing-cron-body case (that was TD22/#47, fixed Chat A).

**Dual transport (commit 8):** cron_health_check.py sends every anomaly batch on TWO transports — `push_public("errors",...)` + `notify.email(subject, html, text)` — and raises (run marked failed) ONLY when BOTH fail. Confirmed healthy 5.9. The email leg now retries a transient Resend 5xx/429 once (30s) inside notify.email() (TD34) — the "raise only when BOTH fail" logic is unchanged (still reads result["ok"]). The 5.19 self-failure path (above) reuses the same two transports but, because no anomalies can be computed when Mongo is unreachable, it re-raises unconditionally rather than only-when-both-fail.

**Coverage notes:** TD33 Tavily guard has no HTTP surface (only the Sunday 06:30 fetch_news_for_universe.py path) → regression-covered at deploy via import graph + boot. TD35 explicit-id flow is exercised only by the Sunday `run_weekly_suggestions.py --direction=both` path (production caller of send_combined_digest); no HTTP surface → covered at deploy via import graph + a monkeypatched harness. TD38 (#23) fallback heartbeat path likewise has no HTTP surface → covered at deploy via landed-greps + import graph + a temp-file harness with a forced-Mongo-failure tripwire + the live `cron_health_check.py` running end-to-end through the merge loop. TD39 (#24) self-failure path likewise has no HTTP surface → covered at deploy via landed-greps + a hermetic tripwire + a live-transport variant + the live happy-path run exiting 0. Chat A: #25 (auto-drift ntfy) and #35 (intraday-insert ntfy) and #47 (outcomes cron) have no HTTP surface either → each covered by a hermetic harness on EC2 (rising-edge dedupe / captured guarded push + re-raise / pre-fix-repro + post-fix success heartbeat) plus #47's live pre-fix reproduction; #34 (/health) IS HTTP-surfaced → covered by a live curl (200 ok/ok) + a forced-ping()-False TestClient probe (503 degraded); #49 covered by an `is_expected_today` assertion across all 7 weekdays.

**Open scheduling work:** TD21/#46 registry-generated crontab migration (deferred; CRON_REGISTRY gains a parseable cron expr → `scripts/render_crontab.py` renders a committed `ops/crontab` → deploy.sh installs it + a drift-validation step. Chosen over in-process APScheduler — on the 1 GB t3.micro the ~5-min Sunday dossier run would compete with the live API and die on every restart. Its own dedicated chat). TD22/#47 (track_suggestion_outcomes daily failure) and TD40/#49 (weekly_suggestions_sell false Sunday MISSING) are both CLOSED as of Chat A.

## Section 10: Settings and environment variables

In `app/config/settings.py` via pydantic-settings. All required unless marked default.

* **Anthropic:** ANTHROPIC_API_KEY (req) · ANTHROPIC_MODEL_PRIMARY (default "claude-sonnet-4-5") · ANTHROPIC_MODEL_FAST (default "claude-haiku-4-5").
* **MongoDB:** MONGODB_URI (req; URL-encode special chars in password). Code uses `MONGODB_URI` not `MONGODB_URL` (#16/TD30 confirmed at HEAD 090d96c). MONGODB_DB_NAME (req) — live value `portfolio` (default `"portfolio"`); mongosh verification must `getSiblingDB("portfolio")`.
* **Tavily:** TAVILY_API_KEY (req) · TAVILY_DAILY_CALL_LIMIT (default 200) — hard ceiling on calls_today per UTC day, enforced atomically (TD33); DAILY resets 00:00 UTC (README/data_flow prose corrected to daily in Chat A — #48/TD36; there is NO `TAVILY_MONTHLY_QUOTA` env var, the README that named one was wrong) · TAVILY_SEARCH_DEPTH (default "basic") · TAVILY_MAX_RESULTS_PER_QUERY (default 5).
* **Email (Resend):** RESEND_API_KEY (req) · RESEND_FROM · RESEND_TO (default recipient for notify.email()) · DIGEST_TO (may equal RESEND_TO). No new env for the TD34 retry — retry count/backoff/transient-status set are module-level constants in notify.py (project convention: operational constants live in code, not settings).
* **ntfy:** NTFY_PUBLIC_URL (default "https://ntfy.sh") · NTFY_PUBLIC_TOPIC_PRICE/NEWS/ERRORS/DIGESTS · NTFY_PUBLIC_TOPIC_DIGESTS (F2b — REQUIRED, no default). All NTFY_PUBLIC_TOPIC_* must be IDENTICAL on EC2 and Mac. `push_public(channel)` signature: `channel: Literal["price","news","errors","digests"]`. `push_private(topic)` REMOVED (Chat 5 commit 7b). `NTFY_URL/USER/PASS` REMOVED (5.5 TD9).

## Section 11: Phase 1 INVARIANTS — never violate

From `docs/data_flow.md`. Hard rules.
1. Transactions are immutable except through the audited PATCH/DELETE flow. Every PATCH/DELETE writes transactions_audit BEFORE applying; reason required. (RESOLVED 5.10 #4/TD16: audit-then-apply, validate_replay first so a rejected change writes no audit row.)
2. `recompute_holding(isin)` is the only authoritative writer to holdings. Idempotent. FIFO from scratch. Never write directly. Serialized per-ISIN via recompute_locks (TD20/#8); lock at service layer, covers API + scripts; different ISINs never contend.
3. `validate_replay(transactions)` rejects any timeline producing negative quantity. Takes the FULL per-ISIN timeline (existing non-deleted + proposed). Both PATCH and DELETE call it before applying. (RESOLVED 5.10 #5/TD17: /sell and add_manual_transactions.py SELL now call it — a backdated negative SELL 400s/aborts BEFORE the ledger write.)
4. `holdings.deleted_at = None` filter is universal.
5. Cost basis is IT-Act-correct, not broker-nominal.
6. prices_intraday writes are append-only within a day. (5.11 #9/TD23: holiday-stale bar dropped. 5.12 TD26: 90-day captured_at_ttl bounds it; works because captured_at is a BSON Date. Chat A #35: an insert exception fires a guarded ntfy + re-raises.)
7. Symbol search (GET /transactions/search) is case-sensitive by construction: input uppercased, symbols stored uppercase, prefix regex carries NO $options:i and uses the (symbol, trade_date) index. (5.13 #18/TD32 dropped the redundant "i"; do not reintroduce it — it disables the index.)
8. ICICI portfolio display shows TMPV ~₹813 and TMCV ~₹253 — cosmetically wrong vs our tax-correct numbers; does not affect actual money or tax filing.
9. preview_sell correctly folds SPLIT/BONUS adjustments into the lot walk (5.6).

## Section 12: Phase 2 INVARIANTS

* suggestion_runs are append-only.
* The persisted run `_id` is carried on the in-memory SuggestionRun (5.16/TD35): `_persist_run` sets `run.id = result.inserted_id` on every persist path, so callers (`_do_both`, `send_combined_digest`, standalone `send_weekly_digest`) read `run.id` directly. Do NOT re-derive a run id with `find_one(..., sort=[("run_date",-1)])` — that couples the consumer to "whichever run for that direction is newest" instead of the run actually just created. send_combined_digest's signature is unchanged (reads buy_run.id); its digest_deliveries audit row keys on the BUY run id for combined digests.
* tavily_quota: one doc per UTC day, $inc counters. Hard ceiling on calls_today (credits tracked, not capped). 5.14 (#19/TD33): enforced ATOMICALLY via a single find_one_and_update guarded by `calls_today < TAVILY_DAILY_CALL_LIMIT`; cap-hit detected by DuplicateKeyError on the unique date_unique index; surfaced as TavilyQuotaExceeded. No TOCTOU; the prior check-then-act pre-check in search() removed.
* Confidence score is deterministic, NOT LLM-generated.
* The dossier prompt requires narrative-only output. Forbids "buy"/"sell" imperatives and inventing facts.
* gate_meta/group_meta/signal_meta/confidence_meta/feedback_meta/page_intro/user_action are PRESENTATION metadata added by `_serialize_run` via `enrich_run`. Never in the persistent model.
* Snapshot eligibility for snapshot_open_outcomes is `tracking_status != "expired"` (A.5). Auto-expiry only flips "open" outcomes at day 180; user-set labels never overwritten (A.5). Feedback re-labels the MOST RECENT non-expired outcome for the ISIN (A.5.1) — as of Chat A #26, FOR THE SAME DIRECTION (buy includes legacy/no-direction docs via {$or:[{direction:buy},{direction:{$exists:false}}]}; sell is bare {direction:"sell"}). snapshot_open_outcomes returns its count under `active_outcomes` (NOT `open_outcomes` — #47).
* `get_excluded_isins()` returns three buckets: rejected (90d), passed (this run only), acted (30d soft-exclude, F5b). Constants intentionally NOT env-configurable.
* F10 write-before-apply: every POST /suggestions/{isin}/feedback writes monitored_stocks_audit BEFORE update_one.
* A1: monitored_stocks writes go through `MonitoredStockFeedbackPatch(...).model_dump(exclude_none=True)`. `extra="forbid"` catches drift. (SuggestionFeedback also uses `extra="forbid"` — #26 added a `direction` field to it with a "buy" default so the current frontend keeps working.)
* The `notes` field on a SuggestionRun is a JSON string `{dossiers: [...]}`; the router parses it and exposes dossiers at top level.
* 5.6 round-trip: every Phase-2 Pydantic model loads cleanly from any historical persisted doc.
* 5.13 (#17/TD31): the ISIN Path() params on GET /suggestions/{isin}/audit and POST /suggestions/{isin}/feedback carry `pattern=r"^[A-Z0-9]{12}$"` → a malformed ISIN 422s at the boundary.

**F2 / F14 invariants (Chat 4):**
* SuggestionDirection literal = "buy" | "sell". Defaults "buy". Router serializer + /runs projection both defensively default missing direction to "buy" on the raw-dict path.
* `compute_system_performance(direction="sell")` SIGN-FLIPS excess_return at aggregation time. snapshot_open_outcomes is DIRECTION-AGNOSTIC.
* earnings_calendar refresh deletes future events then re-inserts; past never touched. `_sanitize_for_bson` applied to Ticker.calendar before insert.
* F14 earnings-proximity gate SHARED buy+sell, 5-day threshold. next_earnings None → skipped=True, passed=True.
* Sell-side uses different groups (booking_opportunity/valuation_stretch/risk/tax_concentration) and gates (in_profit/min_position_age/earnings_proximity). CandidateScore has FIXED buy-side group fields; sell-side group scores flow through group_meta (TD7/#45 deferred). monitored_stocks currently direction-agnostic (TD1/#43 deferred; #26 added direction-aware relabel on the OUTCOME query only).
* F2 combined-digest: --direction=both emits ONE email + ONE ntfy. 5.16 (TD35): the combined digest's digest_deliveries.run_id keys on buy_run.id, not a re-derived latest-buy-run id.

**Chat 5 A2 (CLOSED):** notify.email() returns `{ok, id, error}` and SWALLOWS Resend exceptions. All Resend traffic flows through it. #20/TD34 (5.15): retries ONCE (2 attempts) on transient HTTP 429/5xx with a 30s blocking backoff; 400s and any other client/no-status error return immediately. Contract + swallow/no-raise UNCHANGED — the retry is internal — so digest_delivery._send_email, reconciliation._send_drift_alerts, cron_health_check dual-transport are untouched. Transient classified by `_is_transient_email_error()` reading the SDK exception's int status (.code/.status_code, with error_type=="rate_limit_exceeded"→429 fallback); 429 + 5xx retry, everything else does not. Constants NOT env-configurable. push_public, by contrast, RAISES on failure — #25 (auto-drift) and #35 (intraday-insert) both guard it.

**Chat 5.16 TD35 (CLOSED):** digest_delivery.send_combined_digest and run_weekly_suggestions._do_both read the persisted _id off `run.id`, NOT via find_one re-derivation. send_combined_digest signature UNCHANGED (Option 1, model-carried id), so its sole caller _do_both is API-compatible. Standalone `send_weekly_digest(run, run_id=run.id)` writes the real run_id (was None).

**Other CLOSED Phase-2 facts:** A3+A4: SignalScore.raw_value carries the RAW input that fed normalization. 5.5 TD11: explainability._build_signal_meta falls back to `_to_float(sig["raw_value"])` via `_format_raw(meta["formatter_kind"], raw)` when fundamentals_field is None AND available. Commit 8: cron-health dual transport raises only when BOTH fail (confirmed healthy 5.9).

## Section 13: Shipped vs Open

**Phase 1 (all shipped, locked):** Holdings dashboard w/ day-gain coloring · FIFO cost basis w/ fee allocation + precision · ICICI Order Book import→staging→reconcile→promote · Manual entry for IPOs/demergers/bonuses/splits (5.10 manual SELL validate_replay-guarded) · Transaction edit/delete w/ mandatory reason + audit (5.10 audit-then-apply, #4) · Transaction search (5.13 case-sensitive prefix index, #18) · Preview-sell (5.6 SPLIT/BONUS) · Reconciliation snapshots (manual+auto) w/ drift detection (Chat A #25: auto-snapshot fires ntfy on threshold drift) · Cost basis adjustments (TMPV/TMCV seeded) · EOD+intraday price refresh (5.11 holiday-guarded #9; 5.12 90-day TTL #12; Chat A #35 intraday-insert ntfy on failure) · Tax vs broker view in summary · Single-holding drill-down (chart, transactions, notes; 5.13 refetchQueries #14) · Audit log page · Dark mode · Reconciliation badge · Recent activity card · Global refresh button (5.13 refetchQueries #14) · `/health` honest Mongo readiness probe (Chat A #34).

**Phase 2 Suggestions Engine:** Unit 1 foundations · Unit 2 news fetch + Haiku classify + Sonnet dossier · Unit 3 outcomes/performance/frontend · Commit A (backend explainability) · A.5 (feedback correctness) · A.5.1 (re-label correctness; Chat A #26 made relabel direction-aware) · Commit B (frontend explainability) · Feedback/audit endpoints (5.13 ISIN charset pattern #17) · Tavily quota tracking (5.14 daily ceiling atomic #19) · Weekly digest delivery (5.16 explicit persisted-run-id flow #21) · Outcome-tracking cron (Chat A #47 fixed the daily KeyError failure).

**Cross-cutting:** Transactional email via notify.email() (Chat 5 A2; 5.15 transient retry #20) · Cron observability (Chat 2 F4+F5a; 5.18 heartbeat disk fallback #23; 5.19 health-check self-failure dual-transport alert #24; Chat A #49 removed the weekly_suggestions_sell false Sunday MISSING) · Stateful feedback (Chat 3 F6+F5b+F10) · Sell-side fully shipped (Chat 4 F2b+F14+F2) · Model-layer NaN guard in _to_decimal (5.17 #22/TD37).

**Per-chat ledger (compacted):**

| Chat | Date | Shipped | Code SHA / note |
|---|---|---|---|
| 2 | 2026-05-16 | F4 + F5a cron observability | — |
| 3 | 2026-05-17 | F6 + F5b + F10 stateful feedback | — |
| 4 | 2026-05-17/18/20 | F2b + F14 + F2 backend + F2 frontend (sell-side) | — |
| 5 | 2026-05-24 | Audit + cleanup (8 commits, 2 manual EC2, 1 infra, 4 doc deliverables; A1–A19, TD8) | baked into c6b1437b / 4f31b49 |
| 5.5 | 2026-05-24 | TD9 + TD11 + TD12 (TD10/TD14 carried) | — |
| 5.6 | — | Pydantic round-trip + ge=0 + SPLIT/BONUS preview + TD13 | c6b1437b / 4f31b49 |
| 5.7 | — | Project_State full-file refresh, file-map repairs, URL-at-SHA rule | — |
| 5.8 | — | Code review (28 findings: 5 P1/14 P2/9 P3); master_todo.md created. **Doc commit 8f74b50 silently truncated 655 lines — recovered 5.9** | — |
| 5.9 | 2026-06-02 | #1/TD14 (crontab flags + CRON_REGISTRY rename c097b473), #2/TD10 (verified absent), #3/TD15 (F-number registry), DOC RECOVERY, filed TD21/#46 + TD22/#47 | — |
| 5.10 | 2026-06-06 | #4/TD16 (17f9f94 audit-then-apply), #6/TD18 (dup-handler delete), #5/TD17 (5cf3087 validate_replay), #7/TD19 (fb23307 warning-flag), #8/TD20 (b34721e per-ISIN lock) | b34721e |
| 5.11 | 2026-06-08 | #9/TD23 + #10/TD24 + #11/TD25 (all price_service.py) | a2806cd |
| 5.12 | 2026-06-08 | #12/TD26 (prices_intraday TTL) + #13/TD27 (purge_news_bodies) + crontab line | 49bf33f |
| 5.13 | 2026-06-08 | #14/TD28 (frontend f59958) + #15/TD29 + #16/TD30 + #17/TD31 + #18/TD32 | backend 090d96c / frontend f59958 |
| 5.14 | 2026-06-09 | #19/TD33 atomic Tavily quota | 4ac2c95 |
| 5.15 | 2026-06-12 | #20/TD34 notify.email() transient retry | 7d77b9c |
| 5.16 | 2026-06-12 | #21/TD35 explicit inserted_id flow; filed #48/TD36 (no code) | f4168b3 |
| 5.17 | 2026-06-12 | #22/TD37 reject NaN in _to_decimal (float branch) | 1d627d7 |
| 5.18 | 2026-06-12 | #23/TD38 fallback heartbeat log + dual-source health check | 0515fef |
| 5.19 | 2026-06-14 | #24/TD39 cron_health_check self-failure dual-transport alert (wraps main's Mongo reads); filed #49/TD40 | 7fcda9e |
| A | 2026-06-14 | Ops & alerting quick-wins bundle (7 items): #34 + #35 (Ops gaps; `/health` 503-on-degraded + intraday-insert ntfy) `bd52c6b`; #25/P2-7 (auto-snapshot ntfy on drift, rising-edge deduped) `1340396`; #49/TD40 (weekly_suggestions_sell expected_weekdays=set()) + #26/P2-6 (direction-aware feedback relabel) `6032b64`; #47/TD22 (track_suggestion_outcomes KeyError 'open_outcomes'→'active_outcomes') `4b638e6`; #48/TD36 (Tavily monthly→daily doc fix, DOC-ONLY) `fae6edf`. Phase 7 COMPLETE. | code/doc HEAD fae6edf / frontend f59958 |

The Chat 5.10 SellSheet recorded_with_warning follow-up remains OPEN and untouched through Chat A (out of each phase's scope).

**Chat split plan — SOURCE OF TRUTH is `docs/master_todo.md`.** Snapshot:

| Phase | Items | Focus | Status |
|---|---|---|---|
| 1 | #1-3 | Ops unblock + doc reconciliation | SHIPPED (5.9) |
| 2 | #4-8 | Transactions/holdings/audit invariants | SHIPPED (5.10) |
| 3 | #9-11 | Intraday & price correctness | SHIPPED (5.11) |
| 4 | #12-13 | Storage hygiene | SHIPPED (5.12) |
| 5 | #14-18 | Frontend correctness + quick wins | SHIPPED (5.13) |
| 6 | #19-24 | External-service hardening | COMPLETE — #19 (5.14), #20 (5.15), #21 (5.16), #22 (5.17), #23 (5.18), #24 (5.19) all SHIPPED |
| 7 | #25-26 | Reconciliation alerting + feedback direction | COMPLETE — #25 + #26 SHIPPED (Chat A) |
| 8 | #27-29 | Chat 6 (F1+F3), Chat 7 (F12+F15), Chat 8 (F13 watchlist) | OPEN — #27 NEXT |
| 9 | #30-38 | Cross-cutting cleanup before GO LIVE | PARTIAL — #34 + #35 SHIPPED (Chat A); #30-33, #36-38 OPEN |
| 10 | #39-41 | Chat 9 pre-launch cleanup (F11 + realized P&L hide + stop_loss) | OPEN |
| 11 | #42 | Chat 10 GO LIVE (F7 real data import) | OPEN |
| 12 | #43-45 | Deferred TDs (TD1, TD3, TD7) | DEFERRED |
| — | #46-49 | TD21 scheduler migration (OPEN), TD22 outcomes-cron failure (SHIPPED Chat A), TD36 Tavily doc cleanup (SHIPPED Chat A), TD40 weekly_suggestions_sell Sunday false MISSING (SHIPPED Chat A) | #46 OPEN; #47/#48/#49 SHIPPED |

**Chat-bundle overlay (added 5.19, source of truth = master_todo.md "Chat bundles").** To cut the number of chats to open, the remaining OPEN rows are grouped (NOT renumbered/moved) into chats: **Chat A** (#25, #26, #34, #35, #47, #48, #49 — ops & alerting quick-wins — COMPLETE, all SHIPPED 2026-06-14), **Chat B** (#30, #31, #32, #33, #36, #37, #38 — Phase 9 hygiene sweep), **Chat C** (#40, #41 — UI cleanup), **Chat D** (#43, #44, #45 — deferred TDs), and six standalone large items kept one-per-chat to avoid Section-16 context loss: #27 (Chat 6 — NEXT), #28 (Chat 7), #29 (Chat 8), #39 (Chat 9), #42 (Chat 10 GO LIVE), #46 (scheduler). Bundles never override a per-row gating dependency; each row is still marked SHIPPED individually.

**Open items carried past Chat A** (tracked in master_todo.md with stable numbers; pointer now at #27):
* **#27 (Chat 6 / F1 + F3, NEXT):** ad-hoc chat about suggestions (F1) + about a specific holding (F3); shared `conversations` scaffolding, `POST /chat/suggestions` + `POST /chat/holdings/{isin}`, frontend chat surface. Standalone large feature.
* **#28 (Chat 7 / F12 + F15):** `/portfolio/risk-summary` + `/portfolio/by-tag`.
* **#29 (Chat 8 / F13):** watchlist (extends the engine universe).
* **#30–#33, #36–#38 (Phase 9 / Chat B):** datetime sweeps, Python ceiling, pytest harness, admin recompute endpoint, restore rehearsal, JSON logging.
* **#39 (Chat 9 / F11), #40 + #41 (Chat C):** capital-gains pack; realized-P&L UI hide + stop_loss wiring.
* **#42 (Chat 10 / F7):** GO LIVE real ICICI import.
* **#43–#45 (Chat D, DEFERRED):** TD1/TD3/TD7. Note TD1/#43: #26 added direction-aware relabel on the outcome query, but monitored_stocks stays direction-agnostic — revisit whether the practical pain is gone.
* **#46 (TD21):** registry-generated crontab migration; dedicated chat.

## Section 14: Conventions the assistant has repeatedly drifted on

Memorize these.
* Port 8001 (Mac local), 8000 (EC2). Always specify which.
* SSH-first for tests: every test block begins `ssh ubuntu@100.112.20.41` and curls `localhost:8000`. (Frontend-only: `~/deploy-ui.sh` + `npm run build`/lint on EC2.)
* Commit-block-after-code: every code/file delivery followed by paste-ready `git add .` + `git commit -m`.
* Project_State.md AND master_todo.md are ALWAYS complete full-file replacements.
* F6 two-mechanism feedback exclusion: `get_excluded_isins` at run-build AND `_build_user_action` at serialization. Both required.
* 90-day rejected cooldown and 30-day acted soft-exclude are intentionally NOT env-configurable.
* F10 write-before-apply: `monitored_stocks_audit_service.log_change(...)` BEFORE `monitored_stocks.update_one(...)`. Transactions invariant now satisfied too (#4 SHIPPED 5.10).
* Secrets path on EC2: `/etc/portfolio-advisor/secrets.env`.
* `lib/api.ts` hand-typed; `lib/api-types.ts` gitignored.
* Mutations use `refetchQueries` (synchronous), NOT `invalidateQueries`. The two outliers (notes-panel + refresh-button) swapped 5.13 (TD28/#14); convention now holds project-wide.
* `cn` at `@/lib/utils`. Format helpers at `@/lib/format`.
* Collections accessor: `from app.db.client import Collections`.
* Decimal128 vs Decimal: helpers in `app/models/_common.py`.
* Datetimes: UTC-naive in Mongo, IST in UI. `utcnow()` from `app/models/_common.py`. Mixed tz-aware usage exists — #30 + #31 will sweep.
* Heredoc for multi-line Python: `<<'EOF'` form.
* Original SuggestionCard takes parent-owned mutation. Do not redesign. /suggestions page uses shadcn Tabs. Tailwind v4 + shadcn `.dark` pickup is automatic.
* Every cron script: `cron_run()` wrapper AND CronSpec entry AND crontab line w/ log redirection. AND CronSpec.cron_name MUST equal the name passed to `cron_run()` (5.9 TD14; re-confirmed 5.12).
* Direction-aware display layer: branch on direction at the display layer, not by forking the model.
* Symbol search regex is case-sensitive on purpose (input uppercased, symbols stored uppercase); NO $options:i (it disables the (symbol, trade_date) index). (5.13 TD32.)
* ISIN Path() params validate charset with `pattern=r"^[A-Z0-9]{12}$"` in addition to min_length/max_length=12. (5.13 TD31.)
* Tavily daily quota enforced ATOMICALLY: one find_one_and_update guarded by `calls_today < TAVILY_DAILY_CALL_LIMIT`, cap-hit caught via DuplicateKeyError on the unique date_unique index. NO check-then-act pre-check. Cap calls-only; credits tracked not capped. DAILY (resets 00:00 UTC), not monthly — README/data_flow prose corrected in Chat A (#48/TD36); there is NO `TAVILY_MONTHLY_QUOTA` env var. (5.14 TD33 + Chat A TD36.)
* notify.email() retries a TRANSIENT Resend failure (429 + 5xx) ONCE (2 attempts) with a 30s blocking backoff; 400s and no-status errors return immediately. INTERNAL — {ok,id,error} contract + swallow/no-raise unchanged, callers keep branching on result["ok"]. Transient classified by `_is_transient_email_error()` (SDK int status off .code/.status_code, fallback error_type=="rate_limit_exceeded"). Constants NOT env-configurable. Do not convert to a raised-exception path. push_public, by contrast, RAISES on failure — guard it whenever a failed push must not crash the caller (#24, #25, #35 all do). (5.15 TD34.)
* The persisted SuggestionRun._id is carried on the in-memory run by `_persist_run` (`run.id = result.inserted_id`); callers read `run.id`. Do NOT re-derive via `find_one(..., sort=[("run_date",-1)])`. (5.16 TD35.)
* `_to_decimal` (app/models/_common.py) rejects a NaN float (`v != v`) in its existing `float` branch with `raise ValueError("NaN not allowed")` — ValueError (not TypeError) so the Money validator surfaces a 422. Scoped to the float ingress path ONLY; Decimal/Decimal128-NaN read-path guards deliberately out of scope. (5.17 TD37.)
* Cron heartbeats are best-effort WITH a disk fallback: when the Mongo insert raises, `cron_heartbeat_service._persist` appends the heartbeat as JSON-per-line to `_FALLBACK_LOG_PATH = "/home/ubuntu/cron-heartbeat-fallback.log"` via `_append_fallback` (NEVER raises); `cron_health_check.main` merges Mongo + `count_today_heartbeats_from_fallback` counts before evaluating MISSING/FAILED. A run lands in at most one source, so the merge never double-counts. Do NOT make `_append_fallback` raise, and do NOT drop the Mongo path in favour of the file. (5.18 TD38.)
* `cron_health_check.main`'s ONLY Mongo reads are the per-cron `count_today_heartbeats` calls in the registry loop — that loop is wrapped in try/except so an unreachable Atlas fires a dedicated "anomaly: health-check itself failed" alert on BOTH transports (ntfy `push_public("errors",...)` GUARDED + `notify.email()`) and then RE-RAISES instead of returning 0. Do NOT widen the wrap to include the pure/disk/in-memory calls; do NOT leave the self-failure `push_public` unguarded; do NOT disturb the #23 merge loop inside the wrap; do NOT return success after the reads fail. (5.19 TD39.)
* (Chat A) `/health` must reflect Mongo reachability in the STATUS CODE, not just a JSON field — 503 + `{"status":"degraded","mongo":"fail"}` on a failed `ping()`, 200 + `{"status":"ok","mongo":"ok"}` on success. Do NOT probe yfinance (or any slow rate-limited external) on the hot health path — a throttle would cause false 503s; price-source health lives in the `refresh_prices*` cron heartbeats. (#34.)
* (Chat A) `take_auto_snapshot` (the daily reconciliation cron) alerts ntfy ONLY — the manual `_send_drift_alerts` keeps its dual ntfy+email transport, but the daily auto path would make email noise. Alert on INVESTED drift vs the last manual snapshot (current-value drift is dominated by live-price movement over a multi-day gap — do NOT alert on it). RISING-EDGE dedupe: fire only when this snapshot has drift AND the most recent prior auto snapshot did not, so a standing divergence does not re-push daily; a fresh manual snapshot resets the baseline and re-arms. Evolve the existing alerting (new `_send_auto_drift_alert` mirroring only the ntfy half), do NOT add a parallel alerter. The `/reconciliation/auto-snapshot` route returns `_serialize(dict)` with no `response_model`, and the model already declares `drift_invested`/`has_drift`/`alerts_sent` optional, so stamping them on the auto snapshot is no shape break. (#25.)
* (Chat A) An "add `payload.X` to a filter" instruction can reference a field the payload model does NOT have — grep the Pydantic model (`extra="forbid"` means it would 422, not silently ignore) before referencing `payload.X`. #26 had to ADD `direction: Literal["buy","sell"]="buy"` to `SuggestionFeedback` (default "buy" so the current frontend, which sends only `{action,note}`, keeps working — a required field would 422 every existing submit). When filtering outcomes by direction, use the repo's existing back-compat guard for buy (`{$or:[{direction:"buy"},{direction:{$exists:false}}]}`, matching `get_latest_run`/`compute_system_performance`) so pre-F2 docs still match — a bare `{direction:"buy"}` would silently miss them. This does NOT close TD1/#43. (#26.)
* (Chat A) Before documenting/patching a cron consumer, grep the PRODUCER's return dict for the exact key names — `snapshot_open_outcomes()` returns `active_outcomes` (renamed from "open" when selection broadened in Commit A.5); the consumer read the stale `open_outcomes` and KeyError'd inside `cron_run` every weekday (the failure heartbeat recorded; `cron-outcomes.log` empty because the traceback hit stderr before any result line flushed). A "1 failure/day" health email + an empty log = the cron's own body throwing (a real failure), NOT a persistence/false-MISSING problem. (#47/TD22.)
* (Chat A) An idle/placeholder CronSpec kept "for topology flexibility" must carry `expected_weekdays=set()` (so `is_expected_today()` is always False and `cron_health_check` skips it) UNLESS a real crontab line logs a heartbeat under its exact `cron_name`. The umbrella `weekly_suggestions --direction=both` covers both directions; `weekly_suggestions_sell` is idle — `{6}` made it emit a false Sunday MISSING. (#49/TD40.)
* (Chat A) Before "fixing monthly→daily" wording, read the code for the ACTUAL boundary and the ACTUAL env-var name — the Tavily quota resets 00:00 UTC keyed on `date_utc` (NOT "00:00 IST on the 1st"), enforced via `TAVILY_DAILY_CALL_LIMIT` in `tavily_client` (NOT a non-existent `TAVILY_MONTHLY_QUOTA` in `news_fetcher`). Docs drift on more than the one word you were sent to fix. (#48/TD36.)

**Chat 4 additions:** Don't trust Glean snippets/memory for dataclass/Pydantic field names — grep first. `cron_run()` yields `_Heartbeat`; `.meta` is an ATTRIBUTE. /cron/heartbeats returns `{heartbeats, health_summary}`. Accessor is `Collections.instruments_fundamentals()`. `run_suggestions()` is SLOW by default; `--skip-dossiers` only for smoke tests.

**Chat 5 additions:** ASK FOR THE CURRENT BACKEND (and frontend if relevant) SHA BEFORE PROPOSING ANY CODE CHANGE. When a wrapper's return shape or exception behavior changes, grep ALL callers BEFORE shipping. notify.email() returns {ok,id,error} and swallows Resend exceptions. GitHub raw-URL caching is a real failure mode — use SSH+sed as ground truth.

**Chat 5 closure:** Doc rewrites cross-check every cron/registry/file claim against on-disk state. Project_State.md structure is load-bearing — NEVER restructure. Cron-health observability needs redundant transports. EC2 cron log retention uses logrotate since 2026-05-24.

**Chat 5.5:** Read the script body at HEAD before documenting what it does; verify argparse accepts the flags before documenting a cron line. For settings cleanup touching both settings.py and secrets.env, ship BOTH in ONE atomic commit + restart. Glean snippet-mode line-wraps at sentence boundaries; prefer raw.githubusercontent.com URLs.

**Chat 5.7:** Never make code changes from memory — construct GitHub URLs from owner=doshisahil95, repo, user-supplied SHA, file path from tree listing. Ask the user to run the canonical tree-listing command at the start of every chat. When updating Sections 5/6, diff the prior file map against ls-tree line-by-line.

**Chat 5.8:** master_todo.md is the canonical task list. After reading Project_State.md, also read master_todo.md and confirm the current-position pointer with the user. When you ship an item, update master_todo.md status + advance pointer in the SAME commit as the code. New mid-stream bug/TD/feature → append to the appropriate phase (don't renumber). Cross-references use `master_todo #N` (stable, safe to grep).

**Chat 5.9:** A doc-update commit must NEVER shorten Project_State.md without an explicit stated reason — verify it ends with the sentinel `End of PROJECT_STATE.md.` and line count >= prior. Recovery: `git show <prior-sha>:docs/Project_State.md`. In-code F-numbers live in TWO colliding namespaces (feature-F vs fix-Chat-5.5+-F) — read each `# FN` comment verbatim at HEAD; never assume. An "ops-only" item can hide a code bug (TD14's registry rename) — re-read the relevant service. Don't trust a prior chat's count estimate — grep at HEAD.

**Chat 5.10:** Transactions PATCH/DELETE is now LIVE audit-then-apply; mirror it for any future ledger-mutating route (log_change BEFORE update_one, validate_replay BEFORE the audit; for PATCH audit a computed `{**before, **update_fields}` after-state, then apply, then re-read). `validate_replay(transactions: list[dict]) -> (bool, str|None)` takes the FULL per-ISIN timeline; reads qty/price via _to_decimal; `{"deleted_at": None}` filter also matches docs where the field is absent. Every holdings handler is `sync def` under sync Uvicorn — `asyncio.Lock` does NOT serialize them; use a Mongo advisory-lock doc (cross-thread+process) or threading.Lock (in-process). `recompute_holding` returning None is a legitimate full-exit success — never conflate with a failure. `fetch_metadata` swallows all exceptions → safe-default dict. When a test grabs "the newest BUY" it can land on an exited holding — seed from an ACTIVE holding, use DISTINCT trade dates.

**Chat 5.11:** India has no DST — IST is fixed UTC+5:30 (`timezone(timedelta(hours=5, minutes=30))`), NOT zoneinfo. Reuse module-level `IST` + `_to_ist()` in price_service.py. The module's tz convention is "treat tz-naive as UTC first, then convert" — match it. NSE intraday bars sit inside one IST calendar day → `.date()`-level holiday guard is robust; don't over-engineer. `bulk_get_previous_closes` now delegates to per-ISIN `get_previous_close` (TD25) — do NOT revert to a $push-everything pipeline (the ~34k-doc regression). A green /health + green dashboard endpoints do NOT prove a code change landed — assert the specific new symbol exists/behaves AND confirm deploy pulled the expected SHA.

**Chat 5.12:** A TTL index silently no-ops on a non-Date field — confirm the field is a BSON Date before adding `expireAfterSeconds`. A same-field TTL + non-TTL index coexist only when key DIRECTION differs (ASC TTL + DESC non-TTL); keep ensure_all_indexes additive (no drop). App DB is `portfolio` — mongosh must `getSiblingDB("portfolio")`. news_articles' bulky field is `body_text` not `body`. Age-based purge keys on `fetched_at` (always present) not nullable `published_at`.

**Chat 5.13:** A "~line N" pointer is a hint, not ground truth — re-anchor at HEAD. Use `grep -F` for literal strings (a metacharacter-bearing grep can be self-defeating; an empty grep is not proof of absence if the pattern is malformed). A pass/fail test must DISCRIMINATE the change from pre-existing behaviour (the discriminating ISIN input is 12-char with a lowercase/illegal char). A both-repos phase needs a per-repo deploy + landed-assertion (a green /health proves nothing). Keep min_length/max_length when ADDING pattern (additive, clearer 422s).

**Chat 5.14:** The atomic compare-and-increment idiom on Mongo is "guard in the filter + unique index catches the over-cap upsert" — express the limit in the find_one_and_update filter with upsert=True; the UNIQUE index on the partition key raises DuplicateKeyError = the "exhausted" signal. No transaction, no lock, one round-trip. Verify the unique index exists at HEAD first. A check-then-act guard is a TOCTOU race even on single-process sync Uvicorn (threadpool). When docs disagree with code, anchor to the source body at HEAD (Tavily "monthly" vs daily). A behaviour-preserving race fix must NOT silently add a new cap.

**Chat 5.15:** A retry inside a `{ok,id,error}` swallow-exceptions wrapper must keep returning that dict (never raise) — re-read every result["ok"] caller at HEAD before patching. Classify transient-vs-permanent off the SDK exception's HTTP status, not the message string. Only 429 + 5xx retry; a no-status error returns immediately. A blocking `time.sleep` in notify.email() blocks ONE threadpool worker (anyio default 40), acceptable on a single-user box; chose 1 retry + 30s fixed. Verify a behaviour-preserving change with a monkeypatched harness (stub `resend.Emails.send` + `time.sleep`), not a live send. Retry count/backoff/transient-status are module constants, NOT env-configurable.

**Chat 5.16:** A "persist BEFORE consume" scope can be half-true — re-anchor on the actual control flow at HEAD before deciding what the fix is (the run was already persisted; the bug was the id being re-derived). Prefer carrying state on an existing model field over adding a parameter when both work (SuggestionRun.id existed — no signature change → sole caller untouched, no caller-grep risk). `find_one(..., sort=[("<date>",-1)])` to recover "the row I just inserted" is a latent correctness bug, not a perf nit — thread the real inserted_id. send_combined_digest has exactly ONE caller (_do_both) — still grep before trusting. A cron-path change with no HTTP surface is verified by deploy + import-graph + a monkeypatched harness with a tripwire (a stubbed find_one that RAISES) + landed-greps, not curls. When you delete the last use of an import, delete the import too.

**Chat 5.17:** A validator that must reject bad input via Pydantic raises `ValueError` (or AssertionError) so Pydantic v2 converts it to a ValidationError → 422; raising `TypeError` from a BeforeValidator escapes as a 500 instead. NaN is detected as `v != v` (the only float not equal to itself). A guard placed on the float ingress path does NOT touch Mongo reads (those deserialize through the Decimal128 branch) — so no read-path regression, and broadening to Decimal/Decimal128-NaN was deliberately left out of #22's scope. The cached `master_todo.md` blob lagged HEAD by two chats — Project_State.md read at the user-supplied SHA + a `git show` paste are ground truth, NOT the blob read; confirm the pointer against the SHA-pinned file, not the cache.

**Chat 5.18:** "Heartbeat errors" splits into two distinct failure modes — distinguish them before acting: (a) heartbeat PERSISTENCE failure (the Mongo insert raises; the run actually succeeded) → false MISSING, the gap #23/TD38 closes via the disk fallback; (b) the cron's OWN body throwing (recorded faithfully as `status="failure"`) → a real bug, NOT something #23 touches. A `1 failure(s) today` line PROVES the heartbeat machinery worked (the failure row reached Mongo), so it is never the persistence bug — it's TD22/#47 (fixed Chat A). Mirror an existing reader/writer exactly when adding a fallback. The fallback timestamp is stored ISO-8601 and must be normalized tz-aware→naive-UTC (`_parse_fallback_dt`) to compare against the naive-UTC window. A best-effort sink must swallow ALL its own errors and contribute zero. Verify a no-HTTP-surface change with a temp-file harness + a forced-Mongo-failure tripwire + landed-greps + the live health check running through the merge loop — not curls. A docstring that misspells its own constant still gets fixed before the audit trail.

**Chat 5.19:** `cron_health_check.main`'s ONLY Mongo reads are the per-cron `count_today_heartbeats` calls — wrap THAT loop (not pure/disk/in-memory calls) in try/except so an unreachable Atlas fires a dedicated "anomaly: health-check itself failed" alert instead of crashing silently. Mirror the normal anomaly path's dual transport (ntfy + email, both Mongo-independent), but GUARD the ntfy leg — `push_public` RAISES on failure. Then RE-RAISE (don't return 0) so `cron_run` records the run as a failure. The #23/TD38 fallback-merge loop stays verbatim INSIDE the wrap. Verify with TWO harnesses: a hermetic tripwire AND a live variant. A health-check self-failure alert and a normal anomaly alert are DIFFERENT alerts — and a test harness's stubbed `[stub] push_public` / `[stub] email` lines are NOT missing real deliveries, they ARE the stubs firing.

**Chat A:** A bundle of "small independent items" is a chat-grouping, not a single work item — ship in meaningful units (#34+#35, then #25, then #49+#26, then #47, then #48), mark each SHIPPED individually, ask for the new SHA before EACH unit, and re-read each touched file at that SHA. Re-confirm the pointer + bundle mapping against the SHA-pinned master_todo BEFORE starting (the Glean blob was stale, two chats behind). An "add `payload.X`" instruction can reference a non-existent payload field — grep the model. A "monthly→daily" doc fix can hide further doc bugs (wrong reset boundary + a non-existent env var) — read the code. A cron failing daily with an empty log is the cron's own body throwing before stdout flushes (#47), distinct from heartbeat persistence (#23) and health-check self-failure (#24). Guard `push_public` (it raises) in every new alert path (#25, #35). #49 touched the SAME file #23/TD38 hardened — re-read it and leave `_append_fallback`/`count_today_heartbeats_from_fallback`/`_persist` untouched.

## Section 15: Anti-patterns the assistant has fallen into

(Deduped — Section 14 carries the corresponding positive convention.)
* Full-file rewrites instead of additive patches. EXCEPTION: Project_State.md and master_todo.md are always full-file.
* Inventing parallel patterns. Trusting memory for function names / response shapes / paths — RE-READ AT HEAD. Truncating code with "rest unchanged". Asking "is this OK?" without applying the edit. Micro-commits when meaningful units are expected. Assuming GitHub content is current. Producing files significantly larger than originals. Inventing fields in API responses. Forgetting `enrich_run` from new /suggestions endpoints. Forgetting `holdings.deleted_at = None` is universal. Cron entries without log paths / heartbeat monitoring. Designing unrequested UI/UX. Shipping code without the commit block. Shipping a test block without `ssh ubuntu@100.112.20.41` first. Using artifact_edit on Project_State.md / master_todo.md instead of full-file. Confusing the two F6 mechanisms.
* (Chat 4) Guessing model field names without grep'ing; multi-chunk plans without re-reading every touched file at HEAD; the same test block with three different wrong API response shapes.
* (Chat 5) Trusting Project_State.md for "what's open" without verifying code; find-and-replace from snippet memory / stale reads; changing a wrapper's return shape / exception behavior without checking ALL callers.
* (Chat 5 closure) Restructuring Project_State.md when told preserve structure; inventing/removing cron entries in doc rewrites; describing a script without reading its main() + the actual crontab; skipping Section 0 when delivering Project_State.md.
* (5.5) Script rename from a summary without reading the body; cron-line flags without --help; nested triple-backticks in an artifact.
* (5.7) Trusting the file map as ground truth for what's on disk; listing files that don't exist; capturing F-numbers in code without mirroring into Project_State.
* (5.8) Treating Project_State.md as a TODO list (ownership moved to master_todo.md); starting a chat without confirming the pointer; shipping code without updating master_todo.md status in the same commit; auditing against memory instead of master_todo.md + Section 18.
* (5.9) Letting the end-of-chat doc commit truncate the file; mapping F-refs from memory/estimate; treating an "ops-only" item as code-free.
* (5.10) Piping `curl -w "...HTTP=%{http_code}"` into jq (trailing line isn't JSON); asserting on guessed response field names; same-timestamp BUY+SELL in a replay test; pasting a long Python heredoc into SSH (write to file then run); building a full-file doc from Glean's sentence-wrapped read (anchor on a user-pasted `git show`).
* (5.11) Trusting green dashboard endpoints as proof a change deployed; skipping `git pull` / running a curl block before `./deploy.sh`; reverting bulk_get_previous_closes toward $push-everything.
* (5.12) TTL on a non-Date field; dropping a same-field non-TTL index to "replace" with a TTL; mongosh against the wrong DB name; $unset a guessed field name (body vs body_text); purge filtered on nullable published_at.
* (5.13) Trusting a "~line N" pointer; verification grep with regex metacharacters; validator "verified" by a test the pre-existing constraint already explains; both-repos phase declared done on one repo's deploy / green /health.
* (5.14) Replacing a check-then-act race with a lock/transaction when a single conditional find_one_and_update + unique index suffices; adding a new cap during a behaviour-preserving race fix; trusting README prose over code; designing the atomic update from doc-described field names instead of names read at HEAD.
* (5.15) Turning a swallowed-error wrapper into a raised-exception path; classifying off message string instead of HTTP status; retrying EVERY exception instead of 429+5xx; verifying with a live side-effecting trigger; adding env knobs for an operational constant.
* (5.16) Taking the scope's framing at face value instead of reading control flow; re-querying "the latest row" to recover a just-inserted id; adding a parameter when an existing model field carries the value; leaving an orphaned import after deleting its last use; verifying a re-derivation was removed by a passing import alone (use a tripwire + landed-grep).
* (5.17) Raising `TypeError` from a Pydantic validator path where a `ValueError` is needed for a 422 (TypeError escapes as 500); broadening a scoped float-NaN guard to the Decimal/Decimal128 read paths unasked; trusting a cached/stale `master_todo.md` blob over Project_State.md at the user-supplied SHA when confirming the pointer.
* (5.18) Conflating a heartbeat PERSISTENCE failure (false MISSING; #23 fixes) with a cron whose OWN body fails (real bug; TD22 — fixed Chat A); assuming a "fix the heartbeat error" item will silence a `1 failure(s)` alert; making a best-effort fallback sink raise instead of swallowing its own errors; comparing an ISO fallback timestamp to a naive-UTC window without normalizing tz; verifying a no-HTTP-surface fallback path without a forced-failure tripwire; leaving a misspelled constant in a docstring because "tests pass."
* (5.19) Returning 0 (success) from `cron_health_check.main` after the Mongo reads fail; leaving the self-failure ntfy unguarded; wrapping more than the per-cron read loop; disturbing the #23/TD38 merge loop while re-indenting; mistaking a test harness's stubbed `[stub]` lines for missing real notifications; folding the separate `weekly_suggestions_sell` Sunday false-MISSING (#49) or the `track_suggestion_outcomes` body failure (#47) into #24's scope.
* (Chat A) Adding `payload.direction` to a filter without grep'ing the payload model (it had no such field → would AttributeError; the model also had `extra="forbid"`); filtering outcomes with a bare `{direction:"buy"}` that silently misses pre-F2 docs instead of the repo's `{$or:[…,{$exists:false}]}` guard; making `/health` a richer JSON body but leaving the 200 status code so monitors still see "healthy"; probing yfinance on the hot health path; firing a new alert via an UNGUARDED `push_public` (it raises) so a transport blip crashes the cron before the heartbeat records; "fixing" only the literal "monthly" word while leaving the wrong reset boundary + a non-existent env var in the same doc; touching the #23/TD38-hardened heartbeat file and disturbing `_append_fallback`/`_persist`; declaring #47 fixed without first REPRODUCING the failure live at the pre-fix SHA; treating the Glean master_todo blob as the pointer source instead of the SHA-pinned file.

## Section 16: "I am losing context" — escalation protocol

When any trigger fires, say verbatim: **`I AM LOSING CONTEXT`**

**Triggers (any one suffices):** Cannot recall a file structure discussed earlier · Conflating Phase 1 vs Phase 2 facts · Forgetting which Commit (A, A.5, A.5.1, B) shipped which behavior · Forgetting which Chat shipped which feature · Producing a file >1.5x original line count without explicit reason · Generic patterns instead of project conventions · Forgetting the Mac/EC2 port difference, SSH-first/commit-block conventions, or the secrets path · Forgetting master_todo.md is canonical (5.8) · The user corrects the same drift twice in one chat · >15 Glean reader / code_search calls without converging · The "Truncation Notice" appears · About to produce a third large code artifact unsure whether prior decisions apply.

**Specific triggers:** (4) shipped 2+ patches with WRONG field names · shipped a test block with WRONG API response shape. (5) claimed "open" item open without re-reading on-disk code · find-and-replace whose original_text doesn't exist verbatim · changed a wrapper's return shape without grep'ing callers · about to publish a doc rewrite with unverified cron/registry/file claims · about to restructure Project_State.md. (5.5) script rename from a summary without reading the body · document a cron line without --help. (5.7) patch a file whose existence isn't confirmed via tree listing · construct a GitHub URL with a SHA not supplied this chat. (5.8) ship code without updating master_todo.md status in the same commit · start a code chat without confirming the pointer. (5.9) about to commit a Project_State.md that does NOT end with `End of PROJECT_STATE.md.` · write a Section-18 F-row from a bare `# FN` comment without reading it verbatim at HEAD. (5.10) ship a 3rd code change without re-reading the function body at current HEAD · a test block not starting with `ssh ubuntu@100.112.20.41` / curling the Tailscale IP · recommend asyncio.Lock for a sync-def handler · update master_todo.md status without the matching Section 18 + Section 13 in the same doc commit. (5.11) declare a deployed change verified on a 200/green dashboard without a positive existence/behaviour assertion + SHA confirmation · use a DST-aware tz lookup for IST / ignore the price_service naive→UTC convention. (5.12) add a TTL without grepping the writer for a BSON Date · add a cron whose CronSpec.cron_name != the cron_run() string · mongosh against portfolio_advisor · $unset/$set a field name not confirmed against the model at HEAD. (5.13) find-and-replace anchored on a "~line N" without grepping at HEAD · declare a change verified on a metacharacter grep / a test the pre-existing constraint explains · declare a both-repos phase done on one repo's deploy. (5.14) design an atomic compare-and-increment relying on a unique index without confirming it exists at HEAD · change behaviour because README prose says X without reading code at HEAD. (5.15) change notify.email() so a transient failure RAISES · retry every Resend exception instead of 429+5xx off the SDK int status · verify with a live email send / real time.sleep. (5.16) "fix" a persist-then-consume task per the scope framing without reading the call path at HEAD · recover a just-inserted id via find_one(sort date desc) · change send_combined_digest's (or any wrapper's) signature without grepping ALL callers · declare a re-derivation removed on a green import alone. (5.17) raise TypeError (500) instead of ValueError (422) from a validator guard · broaden #22's float-NaN guard to the Decimal/Decimal128 read paths without being asked · confirm the master_todo pointer from a cached blob instead of Project_State.md at the user-supplied SHA · build a full-file doc replacement from a terminal-wrapped paste without flagging the wrap risk + a git-diff gate. (5.18) tell the user a heartbeat-persistence fix (#23) will silence a cron whose own body fails (TD22) · make `_append_fallback` (or any best-effort sink) raise · compare an ISO fallback timestamp to a naive-UTC window without `_parse_fallback_dt` normalization · declare the fallback path verified without a forced-Mongo-failure tripwire + landed-greps · merge fallback + Mongo counts in a way that could double-count a single run. (5.19) about to return 0 from cron_health_check.main on a Mongo-read failure instead of re-raising · leave the self-failure push_public unguarded · wrap pure/disk/in-memory calls in the Mongo try/except · disturb the #23 merge loop while re-indenting · declare the self-failure path verified without BOTH a hermetic tripwire and a live-transport variant · fold #49/TD40 or TD22/#47 into a #24-class scope. (Chat A) reference `payload.X` without grepping the payload model · filter outcomes by a bare direction equality that misses pre-F2/no-direction docs · ship a new push_public alert path unguarded · change `/health`'s JSON without changing its status code · "fix" doc wording without reading the code for the real boundary/env-var · touch `cron_heartbeat_service.py` and modify `_append_fallback`/`count_today_heartbeats_from_fallback`/`_persist` · declare #47 fixed without reproducing it live at the pre-fix SHA · start a bundle chat without re-confirming the pointer + bundle mapping against the SHA-pinned master_todo.

**What "switching chats" means:** the user copies the Section 0 bootstrap into a fresh chat, which reads Project_State.md + master_todo.md + both repos at HEAD + data_flow.md + READMEs, the user states scope, the assistant summarizes back per the Section 0 acknowledgement contract and WAITS for confirmation before doing anything. Work resumes from the master_todo.md pointer. The previous chat's last act (if it ended on context loss) was to deliver the full-file Project_State.md + master_todo.md update, so the fresh chat starts from a verified-complete state.

## Section 17: "Am I hallucinating?" diagnostic questions

* Backend port Mac local → **8001**. Backend port EC2 → **8000**. SSH → **`ssh ubuntu@100.112.20.41`**.
* Secrets on EC2 → **`/etc/portfolio-advisor/secrets.env`**. On Mac → **`<repo>/.env`**.
* `recompute_holding(isin)` → only authoritative writer to holdings; idempotent; FIFO from scratch; serialized per-ISIN via a recompute_locks advisory doc (TD20).
* Gating filter on snapshot_open_outcomes → `tracking_status != "expired"`. And the key it returns its count under → `active_outcomes` (NOT `open_outcomes` — #47/TD22).
* dossier plain_english_summary origin → dossier_service.py `_SYSTEM_PROMPT`, Sonnet, max 500 chars.
* Universe filter in build_universe → NIFTY 100 ∪ watchlist (after F13) − held − excluded buckets from get_excluded_isins.
* Two F6 mechanisms & why both → get_excluded_isins at run-build (saves Tavily+Sonnet) AND _build_user_action at serialization (stale-cache case). Both required.
* Acted soft-exclude window / env-configurable → 30 days / No.
* F10 write-before-apply rule → log_change(...) BEFORE update_one(...) in submit_feedback.
* Q/V/M/N weight breakdown → 30/25/25/20, version "1.0.0-unit2".
* Is lib/api-types.ts checked in → No.
* refetchQueries or invalidateQueries → refetchQueries (the two outliers swapped 5.13 TD28; holds everywhere).
* Sell endpoint response shape → full Holding (partial) OR {message, realized_total} (full exit) OR {status:"recorded_with_warning", isin, warning} (TD19).
* Dividend tracking → No. When does F7 run → Last (Chat 10).
* How does a cron register → cron_run() wrapper + CronSpec entry + crontab line. All three. AND CronSpec.cron_name must equal the name passed to cron_run() (5.9 TD14).
* Where do F4 cron failure alerts go → Both push_public("errors",...) on public ntfy.sh (NTFY_PUBLIC_TOPIC_ERRORS) AND notify.email(...) (dual-transport, commit 8). Raises only when BOTH fail.
* **Heartbeat schema → `{cron_name, started_at, finished_at, status, error, metadata, _schema_version: 1}`. TTL 60 days.**
* Healthy/unhealthy rule → Healthy iff (not expected today) OR (success+skipped >= min AND failure == 0).
* How is PROJECT_STATE.md delivered → Always full-file canvas artifact, verified to end with `End of PROJECT_STATE.md.`.
* What accompanies every code/file delivery → a paste-ready `git add .` + commit block.
* How do test blocks start → `ssh ubuntu@100.112.20.41`, then curls against localhost:8000. (Frontend-only: `~/deploy-ui.sh` + npm build/lint.)
* Is the transactions/search regex case-insensitive → No. Input uppercased, symbols stored uppercase; NO $options:i (5.13 TD32).
* Do the /suggestions/{isin} Path params validate charset → Yes — `pattern=r"^[A-Z0-9]{12}$"` plus min/max_length=12 (5.13 TD31).
* What does notify.email() do on a transient Resend error → retries ONCE (2 attempts) on 429/5xx with a 30s blocking backoff, then returns {ok,id,error} (never raises). 400s + no-status return immediately. Internal; contract unchanged (5.15 TD34). And push_public on failure → RAISES (guard it where a failed push must not crash the caller — #24, #25, #35 all guard it).
* How does a just-created run's _id reach send_combined_digest / _do_both → carried on `run.id`, set by `_persist_run` (`run.id = result.inserted_id`). Read run.id; do NOT re-derive via find_one(sort run_date desc). (5.16 TD35.)
* What does `_to_decimal` do with a NaN float → raises `ValueError("NaN not allowed")` (NaN detected as `v != v`) inside the float branch, surfaced as a 422 via the Money BeforeValidator; float ingress only (5.17 TD37).
* What happens when a cron heartbeat's Mongo insert fails → `_persist` appends it to `/home/ubuntu/cron-heartbeat-fallback.log` (JSON-per-line, via `_append_fallback`, never raises); `cron_health_check.main` merges both counters so it's NOT a false MISSING. A run lands in one source only → no double-count (5.18 TD38).
* What does cron_health_check.main do when its OWN Mongo reads fail → wraps the per-cron count_today_heartbeats loop in try/except; fires an 'anomaly: health-check itself failed' alert on BOTH transports (GUARDED push_public('errors',...) + notify.email()), then RE-RAISES so cron_run records the run failed (heartbeat → disk fallback). The #23 merge loop is preserved inside the wrap (5.19 TD39).
* What does GET /health return → pings Mongo via `ping()`; on success 200 `{"status":"ok","mongo":"ok"}`, on ping failure 503 `{"status":"degraded","mongo":"fail"}`. yfinance is NOT probed (Chat A #34).
* What does take_auto_snapshot do on drift → fires `push_public("price",...)` (ntfy ONLY) when invested drift vs the last manual snapshot exceeds `DRIFT_ALERT_THRESHOLD_INVESTED`, rising-edge deduped (only when this snapshot has drift AND the most recent prior auto snapshot did not); current-value drift NOT alerted; manual path keeps dual ntfy+email (Chat A #25).
* What happens when insert_intraday_quotes raises → a GUARDED `push_public("errors",...)` fires then the exception re-raises so cron_run records the failure heartbeat (market is open by construction once rows are non-empty) (Chat A #35).
* Does submit_feedback's outcome relabel consider direction → Yes (Chat A #26) — `SuggestionFeedback` has `direction: Literal["buy","sell"]="buy"`; the relabel query filters buy via `{$or:[{direction:"buy"},{direction:{$exists:false}}]}` and sell via `{direction:"sell"}`. Does NOT close TD1/#43.
* Why did the Sunday `weekly_suggestions_sell` false MISSING stop → Chat A #49 set the idle spec's `expected_weekdays=set()` so `is_expected_today()` is always False; the umbrella `weekly_suggestions --direction=both` covers both directions.
* Why was track_suggestion_outcomes failing daily, and is it fixed → it read `stats["open_outcomes"]` but `snapshot_open_outcomes()` returns `active_outcomes` → KeyError in its own body every weekday; fixed Chat A #47 (reads `active_outcomes`).
* Is the Tavily quota monthly or daily → DAILY, resets 00:00 UTC keyed on `date_utc`, limit `TAVILY_DAILY_CALL_LIMIT` (default 200), calls-only cap; there is NO `TAVILY_MONTHLY_QUOTA` env var (README/data_flow corrected Chat A #48).

**Chat 4 diagnostics:** CronSpec fields → cron_name, description, schedule_human, expected_weekdays, min_runs_per_day (default 1). Set heartbeat metadata → `ctx.meta = {...}` or `ctx.meta[key]=value` (ATTRIBUTE). /cron/heartbeats shape → {heartbeats, health_summary}. Fundamentals accessor → instruments_fundamentals. run_suggestions() defaults to skipping dossiers → No. F2b digest ntfy topic → NTFY_PUBLIC_TOPIC_DIGESTS (required). F14 earnings-proximity threshold → 5 days, shared buy+sell. Sell-side gate set → in_profit, min_position_age, earnings_proximity. compute_system_performance(direction='sell') → SIGN-FLIPS excess_return at aggregation.

**Chat 5+ diagnostics:** F2 frontend shipped → Yes (frontend SHA e34e126; README at 9edfc8f; unchanged at HEAD 4f31b49 / f59958). Q/V/M/N=0 sell-digest cosmetic bug → fixed 2026-05-20 cea8eee. target_price consumed → Yes, F2 sell-side target_price_proximity (stop_loss deferred Chat 9 TD6). On-disk filename → Project_State.md (title case). A2 part 1 → notify.email() returns {ok,id,error}; digest_delivery._send_email delegates. A3+A4 → composite_for_candidate writes raw input to SignalScore.raw_value. TD8 → self-hosted ntfy stopped 2026-05-18; cleanup 7a+7b. Commit 8 → cron_health_check dual-transport, raises only when both fail. logrotate manages /home/ubuntu/cron-*.log weekly rotate-4 copytruncate. TD9 → settings + secrets NTFY_URL/USER/PASS removed atomically. TD11 → _build_signal_meta raw_value fallback; _format_raw new kinds score_signed/count. TD12 → seed_nifty100.py correctly named; doc-only fix. App DB name → portfolio.

## Section 18: Tech debt registry

**Closed audit rows (Chat 5 + earlier — all SHIPPED, kept for posterity):** A1 (MonitoredStock schema↔writer drift), A2 (digest_delivery/_send_drift_alerts callers; part 1+2), A3 (SignalScore.raw_value writer), A4 (news signal raw values), A5 (stale DEFAULT_CONFIG.gates comment), A6/A6.5/A7 (weekly_suggestions 06:00→07:00 schedule_human / refresh_instruments "Zerodha Kite" desc / unused SATURDAY set), A8 (dead news_article.py deleted), A13 (refresh_instruments docstring → NSE EQUITY_L.csv), A14 (CLOSED by A1), A16 (fetch_news_for_universe --include-held crontab), A17 (stale _run_sell_pipeline comment), A18 (CLOSED — page_intro already shipped, verified d3f307a), A19 (three Query regex= → pattern=). TD2 (data_flow.md), TD4 (backend README), TD5 (frontend README + per-page ref via TD13), TD8 (self-hosted ntfy decommission + cleanup 7a/7b).

**SHIPPED TDs (one line each — full verification prose in git history):**

| TD | master_todo | Description | Shipped |
|---|---|---|---|
| TD9 | — | Orphan NTFY_URL/USER/PASS removed from settings.py + secrets.env (one atomic commit) | 5.5 |
| TD10 | #2 | Redundant `find -size +10M` crontab line verified absent; logrotate confirmed | 5.9 |
| TD11 | — | explainability._build_signal_meta reads sig["raw_value"]; new _format_raw kinds | 5.5 |
| TD12 | — | seed_nifty100.py correctly named — doc-only fix in 4 locations | 5.5 |
| TD13 | — | Frontend per-page reference doc (7 routes) | 5.6 |
| TD14 | #1 | Sunday crontab flags removed (Part A) + CRON_REGISTRY rename run_weekly_suggestions→weekly_suggestions (Part B, c097b473) | 5.9 |
| TD15 | #3 | F-number fix registry authored (25 unique, two namespaces); recovered truncated Sections 16-tail–22 | 5.9 |
| TD16 | #4 | PATCH/DELETE /transactions/{id} flipped to audit-then-apply (17f9f94) | 5.10 |
| TD17 | #5 | validate_replay on /sell + add_manual_transactions.py SELL (5cf3087) | 5.10 |
| TD18 | #6 | Duplicate list_transactions handler deleted | 5.10 |
| TD19 | #7 | add_buy/sell wrap recompute_holding → recorded_with_warning (fb23307) | 5.10 |
| TD20 | #8 | recompute_holding serialized per-ISIN via recompute_locks advisory doc + 60s TTL (b34721e) | 5.10 |
| TD23 | #9 | Holiday guard in _intraday_row_from_df (IST date != today → None) (a2806cd) | 5.11 |
| TD24 | #10 | price_stale docstring aligned to code (6 calendar days canonical) (a2806cd) | 5.11 |
| TD25 | #11 | bulk_get_previous_closes rewritten to per-ISIN find_one (a2806cd) | 5.11 |
| TD26 | #12 | prices_intraday.captured_at 90-day TTL (captured_at_ttl ASC) | 5.12 |
| TD27 | #13 | purge_news_bodies.py daily cron 02:30 IST ($unset body_text, age on fetched_at) (49bf33f) | 5.12 |
| TD28 | #14 | invalidateQueries → refetchQueries in notes-panel + refresh-button (frontend f59958) | 5.13 |
| TD29 | #15 | Dead `from pydoc import doc` removed | 5.13 |
| TD30 | #16 | MONGODB_URI doc-drift confirmation (no code) | 5.13 |
| TD31 | #17 | ISIN `pattern=r"^[A-Z0-9]{12}$"` on the two /suggestions/{isin} Path params | 5.13 |
| TD32 | #18 | Dropped `$options:i` on transactions/search regex (restores index) | 5.13 |
| TD33 | #19 | Atomic Tavily quota claim (conditional find_one_and_update + unique date_unique) (4ac2c95) | 5.14 |
| TD34 | #20 | notify.email() transient-5xx/429 retry (1 retry, 30s backoff; contract unchanged) (7d77b9c) | 5.15 |
| TD35 | #21 | Explicit persisted-run-id flow (_persist_run sets run.id; find_one re-derivations removed; signature unchanged) (f4168b3) | 5.16 |
| TD37 | #22 | Reject NaN in `_to_decimal` — float branch raises `ValueError("NaN not allowed")` (`v != v`); surfaces as 422 via the Money BeforeValidator; other paths unchanged (1d627d7) | 5.17 |
| TD38 | #23 | Fallback heartbeat log — `_persist` appends JSON-per-line to `/home/ubuntu/cron-heartbeat-fallback.log` on Mongo-insert failure; `count_today_heartbeats_from_fallback` mirrors the Mongo counter; `cron_health_check` merges both (no double-count). Hardens persistence only (0515fef) | 5.18 |
| TD39 | #24 | cron_health_check.main self-failure alert — wraps the per-cron Mongo-read loop in try/except; on failure fires "anomaly: health-check itself failed" on BOTH transports (GUARDED ntfy + email) then RE-RAISES; #23 merge loop preserved inside. LAST Phase 6 item → Phase 6 COMPLETE (7fcda9e) | 5.19 |
| — | #34 | GET /health returns 503 + degraded on Mongo ping failure (was hardcoded 200/ok); yfinance NOT probed (Ops gap, no TD number) (bd52c6b) | A |
| — | #35 | refresh_prices_intraday: insert_intraday_quotes wrapped → GUARDED ntfy on failure (market open by construction) + re-raise (Ops gap, no TD number) (bd52c6b) | A |
| — | #25 | take_auto_snapshot fires ntfy push_public("price",...) on invested drift > threshold vs last manual snapshot, ntfy ONLY, rising-edge deduped (P2-7, no TD number) (1340396) | A |
| — | #26 | Direction-aware feedback relabel — SuggestionFeedback gains direction:Literal["buy","sell"]="buy"; outcome filter routes buy via {$or:[…,{$exists:false}]} / sell via {direction:"sell"}; does NOT close TD1/#43 (P2-6) (6032b64) | A |
| TD22 | #47 | track_suggestion_outcomes daily failure root-caused + fixed — read stale `open_outcomes` (producer returns `active_outcomes`) → KeyError in its own body every weekday; now reads `active_outcomes` + renamed metadata key/print label; safe rename (heartbeat never persisted the old key) (4b638e6) | A |
| TD36 | #48 | Tavily doc cleanup — "monthly"→"daily (resets 00:00 UTC)" in README + data_flow; also fixed "00:00 IST on the 1st"→"00:00 UTC each day" and a non-existent env var TAVILY_MONTHLY_QUOTA→TAVILY_DAILY_CALL_LIMIT (enforced in tavily_client). DOC-ONLY (fae6edf) | A |
| TD40 | #49 | weekly_suggestions_sell idle CronSpec set expected_weekdays=set() → no more false Sunday MISSING; #23/TD38 fallback paths left untouched (6032b64) | A |

**OPEN / DEFERRED TDs (full):**

| TD | master_todo | Item | Status |
|---|---|---|---|
| TD1 | #43 | Make monitored_stocks direction-aware (add direction field, dual rows per ISIN). Reconcile with #26. **Chat A note: #26 added direction-aware RELABEL on the feedback payload + outcome query, but monitored_stocks itself stays direction-agnostic — revisit whether the practical pain is gone.** | DEFERRED — post-launch |
| TD3 | #44 | Split dossier_service.valuation_verdict single string → {verdict, rationale} for cleaner UI. | DEFERRED — future UI |
| TD6 | #41 | Wire holdings.stop_loss (reader + writer + alerts; ntfy when intraday price crosses below; frontend edit field). Chat 5 resolved as "wire it". | OPEN — Chat 9 |
| TD7 | #45 | Refactor CandidateScore so sell-side groups are first-class fields instead of flowing through group_meta. | DEFERRED — post-launch |
| TD21 | #46 | Registry-generated crontab migration (parseable cron expr per CronSpec → scripts/render_crontab.py → committed ops/crontab installed by deploy.sh + drift validation). Chosen over in-process APScheduler. Update the F4 "no silent failures" triad when it lands. | OPEN — dedicated chat |

**F-number fix registry (TD15 deliverable, grepped at backend HEAD c097b473; app/ + scripts/ only).** 25 unique numbers across TWO namespaces: **Feature** (roadmap tickets) and **Fix-5.5+** (robustness tags from the 5.6 pass). They COLLIDE on F1, F2, F3, F4, F5, F7, F8, F12, F14 — a bare `# FN` comment is ambiguous until read verbatim.

| F# | Kind | File(s):line (HEAD c097b473) | Description |
|---|---|---|---|
| F1 | Feature | models/monitored_stock.py:4,14,70 | Ad-hoc chat for suggestions (Chat 6/#27) |
| F1 | Fix-5.5+ | services/reconciliation.py:197 | utcnow() returns tz-naive UTC to match Mongo writes |
| F2 | Feature | models/suggestion.py:31,117,123,174,183; routers/suggestions.py; scripts/run_weekly_suggestions.py:3,127 (+~40 sites) | Sell-side direction (SuggestionDirection, --direction, sign-flip, combined digest) |
| F2 | Fix-5.5+ | services/holdings_service.py:344,351,357 | recompute_holding deletes stale soft-deleted holding docs |
| F3 | Feature | models/monitored_stock.py:4,14,70 | Ad-hoc chat for a single holding (Chat 6/#27) |
| F3 | Fix-5.5+ | services/holdings_service.py:82,429,501 | preview_sell/validate_replay apply SPLIT/BONUS to lot qty |
| F4 | Feature | settings.py:46; db/client.py:156; db/indexes.py:322; routers/cron.py:1; services/cron_heartbeat_service.py:1,125; services/notify.py:5,67; services/holdings_service.py:82,605,661; scripts/cron_health_check.py:1,150 | Cron observability (heartbeats, CRON_REGISTRY, /cron/heartbeats, dual-transport) |
| F4 | Fix-5.5+ | services/holdings_service.py:82,605,661 | validate_replay applies SPLIT/BONUS to lot qty |
| F5 | Feature | services/suggestion_engine.py get_excluded_isins | F5a cron registration; F5b 30-day acted soft-exclude |
| F5 | Fix-5.5+ | services/holdings_service.py:434,470,516; routers/holdings.py:281 | Per-lot realized P&L fee normalization; preview passes total_fees |
| F6 | Feature | models/monitored_stock.py:32,104; routers/suggestions.py:3; services/explainability.py:779,783,814,829,890; services/suggestion_engine.py:120,125,210 | Stateful feedback exclusion (two-mechanism) |
| F7 | Feature | (roadmap) | Real ICICI data import — last (Chat 10/#42) |
| F7 | Fix-5.5+ | services/price_service.py:161 | Revived dead NaN-guard branch |
| F8 | Feature | (roadmap) | Dividend tracking — DROPPED |
| F8 | Fix-5.5+ | services/price_service.py:533 | NaN drop covers Open/High/Low, not just Close |
| F10 | Feature | db/client.py:121; db/indexes.py:236; routers/suggestions.py:8,220,229,243,268; services/monitored_stocks_audit_service.py:1 | monitored_stocks write-before-apply audit + read endpoints |
| F12 | Feature | (roadmap) | Portfolio risk-summary / concentration (Chat 7/#28) |
| F12 | Fix-5.5+ | routers/holdings.py:325 | Fully-exited SELL response includes realized_total |
| F13 | Feature | models/monitored_stock.py:5,9,14,83 | Watchlist (reuses monitored_stocks status="watchlist") (Chat 8/#29) |
| F14 | Feature | models/earnings_event.py:1; services/scoring_service.py:30,109,157,265,571; services/suggestion_engine.py:5,472,507; services/fundamentals_service.py:318; services/explainability.py:318 | Earnings calendar + shared earnings-proximity gate |
| F14 | Fix-5.5+ | routers/holdings.py:46,63; models/transaction.py:125 | Positivity validators (gt=0) → malformed payloads 422 |
| F16 | Fix-5.5+ | models/reconciliation.py:32,50 | Money alias → Decimal128↔Decimal on model_validate |
| F17 | Fix-5.5+ | models/reconciliation.py:51 | _schema_version alias so it persists |
| F18 | Fix-5.5+ | models/cost_basis_adjustment.py:47,59 | amount Money alias → Decimal128 round-trip |
| F19 | Fix-5.5+ | models/cost_basis_adjustment.py:48,73 | _schema_version leading-underscore alias |
| F20 | Fix-5.5+ | models/instrument.py:16,25 | populate_by_name + _id alias |
| F21 | Fix-5.5+ | routers/transactions.py:63,79 | reason field REQUIRED on PATCH/DELETE |
| F23 | Fix-5.5+ | services/reconciliation.py:190 | Write Decimal128 (not float) into Mongo |
| F27 | Fix-5.5+ | services/news_classifier.py:106,198 | Caller no longer pre-merges id; dropped positional fallback |
| F28 | Fix-5.5+ | services/explainability.py:645,755,811 | _build_group_meta accepts direction |
| F29 | Fix-5.5+ | models/transaction.py:23,58,112 | Money fields ge=0 + zero-qty BUY/SELL rejects |
| F79 | Fix-5.5+ | models/symbol_override.py:16,24 | populate_by_name + _id alias |
| F80 | Fix-5.5+ | models/transaction.py:13 | Three manual-prefixed source enum values |
| F82 | Fix-5.5+ | models/transaction.py:80 | Broker reference fields (ICICI ref) |

Notes: F11 (capital-gains pack, Chat 9/#39) and F15 (tag views, Chat 7/#28) are feature tickets with no in-code reference yet — intentionally absent from the in-code table. Feature-F rows for colliding numbers are for disambiguation only; authoritative descriptions live in Sections 5/7/8/12/13/17.

**Fixed in earlier chats (posterity):** Digest sell-side Q/V/M/N bug (cea8eee, 2026-05-20). track_suggestion_outcomes docstring "Daily 18:30 IST" (NOTE: the daily RUN was FAILING — TD22, now FIXED Chat A). CLI docstring "--top-k 5" (F2 chunk 6). holdings.target_price unused (half-fixed; F2 target_price_proximity; stop_loss is TD6). MonitoredStock schema↔writer drift (A1). Dead news_article.py (A8). digest_delivery._send_email inline Resend (A2 part 1). All Chat 5 A2–A19 + TD8 (2026-05-23/24).

## Section 19: How to update this document

Updated at the end of every chat as the LAST commit — ALWAYS a complete full-file canvas artifact, never a patch.

**Update each chat:** Sec 13 (move shipped; advance chat split plan — preserve rows, modify Status / add chat rows in order) · Sec 9 (cron registry if changed) · Sec 14/15/16/17 (new conventions / anti-patterns / triggers / diagnostics) · Sec 18 (add/remove/reclassify TD) · Sec 12/11 (new invariants) · Sec 7 (collection schema) · Sec 8 (endpoint or notable internal-data changes) · Sec 5/6 (file additions/deletions — diff against the Section-0 tree listing line-by-line) · Sec 4 (pin new last-verified SHAs).

**Commit message:** `docs: update PROJECT_STATE.md after <chat scope>` + a bullet list of sections changed.

If the chat ended due to context loss, the LAST thing the assistant does is propose the Project_State + master_todo update; the user applies it manually.

**Standing doc rules:**
* On starting a new chat, after reading Project_State, audit every "open" item against on-disk code at HEAD before estimating work.
* Project_State.md structure is immutable: Section 0 at top, numbered Sections 1-22 in order. New sub-items go INSIDE existing sections, never as new top-level sections.
* When reading this file for a full-file refresh, prefer the SHA-pinned `raw.githubusercontent.com` URL over the blob URL (blob frequently `LINK_NEEDS_AUTH`). If both fail, have the user `ssh ubuntu@100.112.20.41 && cat ~/ai-stock-advisor-backend/docs/Project_State.md` and paste the bytes — Glean's raw reader sentence-wraps, so never reconstruct a full-file replacement from a wrapped read; anchor on a user-pasted byte-exact source (`git show <sha>:docs/Project_State.md`). NOTE (5.17): a `git show` paste through a narrow terminal can ITSELF hard-wrap mid-word — when reconstructing from such a paste, un-wrap carefully and gate the result with a `git diff` review so no unchanged line drifts. (Re-confirmed Chat A: the user's `git show` paste of both docs had mid-word wraps like "shownis"/"atomicTavily"/"weekly_sugg estions"/"suubuntu" — un-wrapped during reconstruction; gate with `git diff`.)
* The tree-listing command (Section 0) MUST be the first thing run in every new chat, before scope. Every file-read URL uses a SHA the user supplied this chat and a path verified in the tree listing.
* The end-of-chat full-file artifact MUST end with the sentinel `End of PROJECT_STATE.md.` and have a line count >= the prior commit's (or explicitly state why it shrank) BEFORE the user commits. (5.8's doc commit silently truncated 655 lines.)
* Update master_todo.md status AND the matching Section 18 TD row AND Section 13 in the SAME end-of-chat doc commit as the code; pin each commit SHA next to its TD row.

## Section 20: Trade-off rationale (decisions that might look weird)

* yfinance over Tijori/Screener Pro: free, works, FundamentalsProvider protocol supports swap. Confidence numeric 0-100 with deterministic deductions (bands hide info). Suggestions Sunday 07:00 IST (market closed, fundamentals+news refreshed first). Top-K = 10. 90-day rejected cooldown + 30-day acted soft-exclude + zero passed cooldown — not env-configurable. Outcome snapshot ignores tracking_status for data collection (A.5). Persistent backend feedback state (Chat 3) replaced session-scoped vanish. Two-mechanism F6 exclusion. enrich_run mutates a copy in-place AND returns it. valuation_verdict one string (Sonnet finds it easier). all_candidates persisted but stripped from API (replay-ability). Dividend tracking dropped (F8). Realized P&L hidden UI, kept backend. F7 last (Chat 10) — test pollution becomes a natural reset. Watchlist (F13) extends the engine universe, not a separate scoring path. F4 ntfy errors public over private (iOS APNs vs polling); CRON_REGISTRY in code not Mongo; intraday strict per-slot heartbeats w/ mark_skipped(); cron_health_check.py is itself a registered cron (excludes itself).
* (Chat 4) F2b digests on public ntfy.sh; F14 as gating signal not UI; F14+F2 shared scoring pipeline; CandidateScore fixed buy-side fields, sell-side via group_meta; --direction=both as production cron; sell-side sign-flip at read time; outcome direction stamped (denormalized).
* (Chat 5) F2b display-layer direction branching; audit-then-fix ordering; A1 typed PATCH model + $setOnInsert; A2 wrapper return-shape change; A3+A4 fixed via writer change not field rename; TD8 in two commits; commit 8 raises only when BOTH transports fail; logrotate over hand-rolled truncation.
* (5.5) TD9 atomic settings+secrets cleanup; TD11 minimum-invasive wiring; TD12 doc-only; TD14 tracked (manual EC2); raw URL at SHA.
* (5.7) Tree-listing-first workflow; reconcile via TD15 not invented mappings; mark TD13 SHIPPED only after verifying README at HEAD.
* (5.9) TD14 fixed build-right (registry rename + flags); TD21 registry-crontab over APScheduler; scheduler migration sequenced after restoring the digest; Project_State recovered from c6b1437b not memory; TD15 scoped before mapping 25 refs.
* (5.10) TD19 warning-flag over M10 transactions (per-step session latency); TD20 advisory-lock doc over threading/asyncio.Lock; lock at service layer; TD16 audits a computed after-state; validate_replay first; #6 done early to reduce line drift.
* (5.11) TD24 code canonical over docstring; TD25 per-ISIN find_one over aggregation; TD23 fixed UTC+5:30 + defensive bar-tz; all three in one commit.
* (5.12) TD26 ASC TTL alongside DESC (additive, no drop); TD27 keys on fetched_at not published_at; 02:30 IST quiet slot; --dry-run on a destructive job; verification re-run against the correct DB.
* (5.13) TD28 minimal name-swap (reorder declined); TD31 pattern alongside length; TD32 also fixed the false comment; per-repo deploy/test boundary; TD30 closed as confirmation.
* (5.14) #19 atomic find_one_and_update + unique-index collision over transaction/lock; cap kept calls-only; pointer advanced normally.
* (5.15) #20 retry kept inside email() preserving {ok,id,error}; 1 retry + 30s fixed over 2/60s/Retry-After; transient off the SDK int status; constants in code; monkeypatched harness over a live send.
* (5.16) #21 Option 1 (model-carried id, no signature change) over adding a param; standalone send_weekly_digest fix folded in (user-confirmed); Tavily monthly→daily filed (#48/TD36) not fixed; verified via grep + monkeypatched tripwire over a live Sunday run.
* (5.17) #22 NaN guard nested in the existing float branch (one isinstance check) over a separate clause; ValueError (not TypeError) for the 422 path; scoped to float ingress — Decimal/Decimal128-NaN read-path guards deliberately out of scope; verified via landed-grep + in-box harness.
* (5.18) #23 disk-file fallback (JSON-per-line) over a second Mongo collection / queue — the sink must not depend on Mongo; reader mirrors `count_today_heartbeats` 1:1 in the same module; merge-counts (no double-count) via the at-most-one-source invariant; no new logrotate; scoped to persistence only; verified via temp-file + forced-failure tripwire harness.
* (5.19) #24 wrapped ONLY the per-cron `count_today_heartbeats` loop; dual-transport (ntfy + email) mirroring the normal anomaly path (user-confirmed) over ntfy-only as literally specced; RE-RAISE after alerting over returning 0; the ntfy leg guarded because `push_public` raises; filed the `weekly_suggestions_sell` Sunday false MISSING as #49/TD40 rather than folding it into #24; verified via a hermetic tripwire + a live-transport variant.
* (Chat A) Bundle worked in meaningful units (#34+#35 / #25 / #49+#26 / #47 / #48), each SHIPPED individually, SHA re-requested per unit. #34: 503 status code (not just a JSON field) on degraded Mongo + yfinance deliberately NOT on the hot path (avoid false 503s) over a richer multi-dependency probe. #25: ntfy-ONLY auto-drift alert via a new `_send_auto_drift_alert` (mirroring only the ntfy half of `_send_drift_alerts`) over parameterizing the dual-transport helper — the message wording genuinely differs (manual = our-vs-ICICI point-in-time; auto = our-now vs our-at-last-manual over time); rising-edge dedupe + invested-only over alert-every-day / current-value (live-price noise). #26: added a defaulted `direction` field to the payload (default "buy" for frontend back-compat) over a required field (would 422 existing submits) + the repo's `$or`/`$exists:false` buy guard over a bare equality (would miss pre-F2 docs); explicitly does NOT close TD1/#43. #47: investigation-first — REPRODUCED the failure live at the pre-fix SHA before fixing; renamed the consumer key to the producer's `active_outcomes` (the producer is the canonical side). #49: option 1 (`expected_weekdays=set()` on the idle spec) over excluding umbrella-covered entries from the MISSING check — more contained, uses existing semantics, leaves the #23/TD38 paths untouched. #48: fixed the wider doc drift (reset boundary + non-existent env var) the code check surfaced, not just the one "monthly" word.

## Section 21: What is intentionally NOT included

So future chats don't accidentally add these:
* Auto-trading (never). Multi-user. Mutual funds, FDs, foreign equities, derivatives, crypto. Native mobile app. Tax filing (we inform; CA files). Dividend tracking (F8 dropped). Accounting / financial planning / goal-based planning. Real-time tick data. Public-facing dashboard. Backtesting framework. Notification customization UI. Account aggregation. Social features. Technical indicator alerts. Options tracking. Index fund comparison page. Separate /news page. Heatmaps / pretty visualizations. Portfolio rebalancing recommender. Social sentiment tracking. Manual-clear endpoint for feedback (use mongosh as escape hatch). /calendar page. Loss-cutting sell pipeline (F2 is profit-booking only; in_profit gate enforces).
* **In-process application scheduler (APScheduler/lifespan jobs).** Schedule stays in crontab; TD21 will version-control it via a registry-rendered ops/crontab, NOT by moving execution into the API process (process isolation + deploy safety on the t3.micro).
* **Mongo multi-document (M10) transactions on the synchronous write path.** Rejected for TD19 — the immutable ledger is the source of truth; a recompute failure is surfaced via recorded_with_warning, not rolled back. (5.14 re-affirmed for the Tavily quota: atomicity comes from a conditional find_one_and_update + the unique index, NOT a transaction.)
* **DST-aware timezone handling for IST.** India has no DST; IST is fixed UTC+5:30 (`timezone(timedelta(hours=5, minutes=30))`). Codified in `price_service.IST` (5.11) — do not introduce zoneinfo/DST.
* **Dropping/replacing a same-field index to add a TTL** when an ASC-vs-DESC split lets both coexist (5.12). ensure_all_indexes stays additive.
* **Case-insensitive symbol search.** Symbols uppercased on input + stored uppercase; GET /transactions/search uses a case-sensitive prefix regex with NO $options:i (5.13 TD32) — "i" would disable the index. Do not reintroduce.
* **A credits_today ceiling on Tavily.** Only calls_today is capped; credits tracked for visibility (5.14). No credit limit without an explicit decision.
* **A lock or M10 transaction around the Tavily quota increment** (5.14 TD33 enforces atomically via conditional find_one_and_update + unique index). Do not "harden" further.
* **A raised-exception path or env-configurable knobs for notify.email().** 5.15 TD34 added an internal transient retry that PRESERVES the {ok,id,error} swallow contract; do not convert to raise; do not add RESEND_RETRY_* settings — constants by convention. No Retry-After parsing without an explicit decision.
* **A `find_one(sort run_date desc)` re-derivation to recover "the run just created."** 5.16 TD35 carries the persisted _id on run.id; do not reintroduce a latest-run lookup.
* **A signature change to send_combined_digest.** 5.16 kept it `(buy_run, sell_run)` (Option 1, model-carried id); if you ever DO change it, grep ALL callers first (exactly one: _do_both).
* **Broadening the #22 NaN guard to the Decimal/Decimal128 read paths.** 5.17 TD37 scoped the guard to the float ingress branch only; do not change `_to_decimal` to raise `TypeError` for NaN — it must stay `ValueError` for the 422 path.
* **Widening the #24 try/except beyond `cron_health_check.main`'s per-cron Mongo-read loop**, or converting its self-failure path to return success. 5.19 TD39 wraps ONLY the `count_today_heartbeats` loop, dual-transports the self-failure alert (guarded ntfy + email), and RE-RAISES. Do not pull the pure/disk/in-memory calls into the try, do not leave the self-failure push_public unguarded, and do not change the re-raise to `return 0`.
* **(Chat A) yfinance (or any slow/rate-limited external) on the `/health` hot path.** #34 deliberately probes Mongo only; price-source health lives in the `refresh_prices*` cron heartbeats. A Yahoo throttle must not produce false 503s.
* **(Chat A) Email on the daily `take_auto_snapshot` drift alert.** #25 is ntfy ONLY — the manual `_send_drift_alerts` keeps dual ntfy+email, but the daily auto cron would make email noise; do not add the email leg to the auto path. Do not alert on current-value drift on the auto path (live-price noise), and keep the rising-edge dedupe (no re-pushing a standing divergence daily).
* **(Chat A) A parallel reconciliation alerter.** #25 evolved the existing alerting (a new `_send_auto_drift_alert` beside `_send_drift_alerts`); do not introduce a second alerting subsystem.
* **(Chat A) Closing TD1/#43 via #26.** #26 made the feedback RELABEL direction-aware (payload field + outcome-query filter) but deliberately did NOT make `monitored_stocks` direction-aware (dual rows per ISIN). TD1/#43 stays DEFERRED.
* **(Chat A) Restoring `weekly_suggestions_sell` `expected_weekdays={6}`** without a real crontab line that logs a heartbeat under that exact `cron_name`. #49 set it to `set()` because the umbrella `weekly_suggestions --direction=both` covers both directions and the spec is idle.

## Section 22: Glossary

ISIN: 12-char NSE/BSE primary key. NSE / NIFTY 100 / FIFO / LTCG / STCG / Section 49(2C) / ICICI Direct / ICICI ZIP / TMPV / TMCV / EW NIFTY: see prior version. Composite score: 0-100, Q/V/M/N (buy) or booking_opportunity/valuation_stretch/risk/tax_concentration (sell). Confidence score: 0-100, deterministic. Dossier: Sonnet per-candidate note. Outcome: suggestion_outcomes doc tracking stock vs benchmark. Bucket: outcome user-action label. Watchlist: F13 user-curated stocks. user_action: per-candidate serialization-time stamp (F6). direction (F2): "buy"|"sell". monitored_stocks_audit: F10 audit collection. earnings_calendar (F14): cached yfinance earnings events. Combined digest (F2): ONE email + ONE ntfy via send_combined_digest. isSellSide (F2): frontend boolean from `groupMeta?.booking_opportunity`. _format_score_breakdown (F2b cea8eee): direction-aware digest helper. MonitoredStockFeedbackPatch (A1): typed Pydantic patch model, `ConfigDict(extra="forbid")`. SuggestionFeedback (#26): feedback payload model, `extra="forbid"`; fields `action`, `note`, and (Chat A) `direction: Literal["buy","sell"]="buy"`. notify.email() return contract (A2): `{ok, id, error}`, swallows Resend exceptions, optional text= (5.15 TD34: retries transient 429/5xx once with 30s backoff — contract unchanged). push_public: ntfy push, RAISES on failure (`_publish` → `raise_for_status`) — guard it where a failed push must not crash the caller (#24, #25, #35). /health (#34): pings Mongo; 200 {"status":"ok","mongo":"ok"} or 503 {"status":"degraded","mongo":"fail"}; yfinance not probed. _send_auto_drift_alert (#25): reconciliation helper, ntfy ONLY, fired by take_auto_snapshot on invested drift > DRIFT_ALERT_THRESHOLD_INVESTED vs the last manual snapshot, rising-edge deduped. Explicit inserted_id flow (TD35, 5.16): _persist_run sets run.id; callers read run.id; both find_one re-derivations removed; signature unchanged. _to_decimal NaN guard (TD37, 5.17): float branch raises ValueError("NaN not allowed") on `v != v`; 422 via the Money BeforeValidator; float ingress only. Fallback heartbeat log (TD38, 5.18): `/home/ubuntu/cron-heartbeat-fallback.log`, JSON-per-line, written by `_append_fallback` when the Mongo heartbeat insert raises (never raises); read by `count_today_heartbeats_from_fallback` and merged by `cron_health_check.main`. Health-check self-failure alert (TD39, 5.19): when `cron_health_check.main`'s per-cron Mongo reads raise, fires a dual-transport "anomaly: health-check itself failed" alert (GUARDED push_public + email) then RE-RAISES. active_outcomes (#47/TD22): the key `snapshot_open_outcomes()` returns its count under (renamed from "open" in Commit A.5); the track_suggestion_outcomes cron read the stale `open_outcomes` and KeyError'd daily until Chat A. weekly_suggestions_sell (#49/TD40): idle CronSpec now `expected_weekdays=set()` so cron_health_check no longer emits a false Sunday MISSING; the umbrella `weekly_suggestions --direction=both` covers both directions. Tavily quota (#48/TD36): DAILY, resets 00:00 UTC keyed on date_utc, `TAVILY_DAILY_CALL_LIMIT` (default 200), calls-only cap; README/data_flow "monthly"/"00:00 IST"/`TAVILY_MONTHLY_QUOTA` wording corrected Chat A. _send_drift_alerts (A2 part 2): reconciliation helper; ntfy+email dual emit (manual path); `sent.append("email")` gated on result["ok"]. composite_for_candidate (A3+A4): wires raw signal inputs into SignalScore.raw_value. _format_raw kinds (5.5 TD11): percent_decimal, percent_already, ratio, multiple, currency_inr_cr, score_only + score_signed (`f"{raw:+.1f}"`), count (`f"{int(raw)}"`).

End of PROJECT_STATE.md.
