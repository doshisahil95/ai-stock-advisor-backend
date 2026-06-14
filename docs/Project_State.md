
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

**Backend:** Python 3.12 · FastAPI · Pydantic v2 (routers use `pattern=` not `regex=` post Chat 5 A19; round-trip / `ge=0` hardening post 5.6; ISIN `Path()` params on the two `/suggestions/{isin}` endpoints AND the `/chat/holdings/{isin}` endpoint carry `pattern=r"^[A-Z0-9]{12}$"` post 5.13 TD31 / Chat 6; the `/portfolio/by-tag` endpoint validates `tag` via `Query(..., min_length=1)` post Chat 7) · MongoDB Atlas M10 (ap-south-1) · uv (package manager) · yfinance (prices/fundamentals/earnings, free tier) · Anthropic Claude SDK (Sonnet 4.5 dossiers + ad-hoc chat, Haiku 4.5 classification) · Tavily (news search, free tier, **daily** quota enforced atomically as of 5.14 TD33) · Resend (transactional email — all via `notify.email()` as of Chat 5 A2; transient 5xx/429 retried once with 30s backoff as of 5.15 TD34) · ntfy (push — public `ntfy.sh` for all paths; self-hosted private decommissioned TD8).

**Frontend:** Next.js 16 (Turbopack) · React 19 · TypeScript strict · Tailwind v4 · shadcn/ui Nova preset · Recharts · TanStack Query (mutations use `refetchQueries`, synchronous; the two `invalidateQueries` outliers in notes-panel.tsx + refresh-button.tsx swapped in 5.13 TD28) · react-hook-form + zod · sonner · next-themes. NO markdown-rendering dependency — LLM markdown (e.g. chat answers) is rendered by a self-contained `MarkdownLite` inside `components/chat-panel.tsx` (Chat 6).

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

**systemd (EC2):** `portfolio-advisor.service` — `uvicorn app.main:app --port 8000 --host 0.0.0.0`, user ubuntu, `PYTHONPATH=/home/ubuntu/ai-stock-advisor-backend`, `PYTHONUNBUFFERED=1`, journald, single process / single worker (no `--workers`). Because there's no `--workers` and handlers are `sync def`, concurrent requests run in Uvicorn's **threadpool** (threads within one process). This is why TD20 per-ISIN serialization uses a Mongo advisory-lock doc (cross-thread AND cross-process), not `asyncio.Lock`; why the Tavily check-then-act was a real TOCTOU race (TD33); why the TD34 `time.sleep(30)` blocks ONE threadpool worker (anyio default 40-thread pool → acceptable on a single-user box); and why a cold-name chat turn (#27 on-demand enrichment: yfinance + Tavily + Haiku + Sonnet) ties up ONE threadpool worker for several seconds without blocking the loop. `portfolio-advisor-ui.service` — `next start` port 3000 with hardening (NoNewPrivileges, PrivateTmp, ProtectSystem=strict, ReadWritePaths = frontend dir + /tmp). Sudoers `/etc/sudoers.d/portfolio-advisor-systemctl` lets ubuntu restart both passwordless.

**Log rotation (2026-05-24):** `/etc/logrotate.d/portfolio-advisor` rotates all `/home/ubuntu/cron-*.log` weekly (rotate 4 · compress+delaycompress · notifempty+missingok · copytruncate · `su ubuntu ubuntu`). Daily via OS `/etc/cron.daily/logrotate`. Force: `sudo logrotate -f /etc/logrotate.d/portfolio-advisor`. The old `0 0 * * 0 find … -size +10M` truncation line was verified ABSENT and logrotate confirmed (TD10/#2, 5.9). The 02:30 IST `cron-news-purge.log` (TD27) is covered by the existing glob. The `cron-heartbeat-fallback.log` (TD38, 5.18) also matches the `cron-*.log` glob — no new rotation config.

**Repos:** backend `https://github.com/doshisahil95/ai-stock-advisor-backend` · frontend `https://github.com/doshisahil95/ai-stock-advisor-frontend`.

**Last verified SHAs (Chat 7 closed, 2026-06-15):**
* Backend: **`803e6610ec21a8bad9a56840abc059cf92db5890`** (Chat 7 code HEAD — #28 Unit 2 F15 by-tag; the Chat 7 `Project_State.md` + `master_todo.md` doc commit advances it further — pin next chat). Chat 7 shipped #28 across two backend code commits: Unit 1 risk-summary (`97041621eedd94947a2ce2c1843d23f317b1b31b` — `_annotate_holdings` extraction + `compute_risk_summary` + `GET /portfolio/risk-summary`) and Unit 2 by-tag (`803e6610` — `GET /portfolio/by-tag`). Opened at `5e787c9` (Chat 6 code HEAD; the Chat 6 doc commit `a104993` was the actual open base for the file re-reads).
* Frontend: **`e14d6a750f802dae941d512837ff1788a7a3a0f0`** (Chat 7 — Unit 3 `components/risk-summary-card.tsx` + `lib/api.ts` RiskSummary/HoldingsByTag bindings + `app/page.tsx` risk card mount + Tags nav, then Unit 4 `app/tags/page.tsx`; no new npm dependency). Opened at `6093f6342e6a6ddb1ecf0c8a1b7fa2239d825c7d`.
* Prior code-HEAD closes: Chat 6 backend `5e787c9` (#27 F1+F3 ad-hoc chat across five commits — Unit 1 data layer off open base `4403bb5`, Unit 2 enrichment `c407985`, Unit 3 chat service + endpoints `15ea9c0`→`dd82636`, route-shadow fix `5e787c9`), frontend `6093f63` (Unit 4 chat UI) · Chat A `fae6edf` (ops & alerting bundle, backend+doc only; frontend `f59958`) · 5.19 `7fcda9e` (TD39 cron_health_check self-failure dual-transport alert) · 5.18 `0515fef` (TD38 fallback heartbeat log + dual-source health check) · 5.17 `1d627d7` (TD37 reject NaN in _to_decimal) · 5.16 `f4168b3` (TD35 explicit inserted_id flow) · 5.15 `7d77b9c` (TD34 notify retry) · 5.14 `4ac2c95` (TD33 atomic Tavily) · 5.13 backend `090d96c` (TD29/31/32), frontend `f59958` (TD28) · 5.12 `49bf33f` (TD26 then TD27) · 5.11 `a2806cd` (TD23/24/25) · 5.10 `b34721e`.

## Section 5: Backend file map

Layout under `app/` and top-level (verified against tree at SHA `ce5e746`; subsequently touched files tagged with the chat/TD that changed them — pending `master_todo #N` notes are live work). Re-verified against the Chat 6 tree listing at backend HEAD `4403bb5` (open) — Chat 6 ADDED `app/routers/conversations.py` + `app/services/conversation_service.py` and edited `app/models/conversation.py`, `app/services/instrument_service.py`, `app/routers/instruments.py`, `app/db/indexes.py`, `app/main.py`. Re-verified against the Chat 7 tree listing at backend HEAD `a104993` (open) — Chat 7 edited only `app/services/portfolio_service.py` + `app/routers/portfolio.py` (no new backend files; no collection/index changes).

```
app/
  main.py                     FastAPI bootstrap, router includes, lifespan
                              (lifespan pings Mongo + ensure_indexes; no scheduler). (done: #34 GET /health now returns 503 + degraded on ping failure, 200 + ok on success; done: #27 includes conversations.router). master_todo #38: JSON-structured logging
  agents/__init__.py          empty package placeholder
  scheduler/__init__.py       empty placeholder (TD21: candidate home for registry-rendered schedule tooling)
  config/settings.py          pydantic-settings; loads secrets. F2b: NTFY_PUBLIC_TOPIC_DIGESTS (required). (done: TD9 NTFY_URL/USER/PASS removed)
  db/
    client.py                 Mongo client, get_db(), Collections accessor (incl. monitored_stocks_audit F10, earnings_calendar F14, recompute_locks TD20, conversations — actively written as of #27). NOTE: app DB name is `portfolio` (MONGODB_DB_NAME default), NOT `portfolio_advisor` (5.12 lesson)
    indexes.py                ensure_indexes() on startup. (done: TD20 recompute_locks acquired_at TTL 60s; TD26 prices_intraday captured_at_ttl ASC 90d; #27 conversations scope_created_desc (scope ASC, created_at DESC) added alongside the existing created_at_desc / intent_created_desc / isins_created_desc / related_holding). tavily_quota has unique date_unique on date_utc — the primitive the TD33 atomic claim relies on. (Chat 7 #28: NO index changes — risk-summary + by-tag read the existing holdings + prices_daily indexes.)
  models/
    _common.py                BaseDoc (to_mongo() = model_dump(by_alias=True, exclude_none=True) + Decimal→Decimal128; extra="forbid"), Money, PyObjectId, utcnow(), Decimal128/ObjectId helpers. (done: #22/TD37 _to_decimal rejects NaN float (v != v) in the float branch -> ValueError("NaN not allowed"); surfaces as 422 via Money BeforeValidator)
    instrument.py             Instrument. (fix F20: populate_by_name + _id alias)
    holding.py                Holding (active position). Carries `tags: list[str]` (default_factory=list) — the field F15/#28 `GET /portfolio/by-tag` filters on (Mongo array-membership)
    transaction.py            Transaction (BUY/SELL/SPLIT/BONUS/DEMERGER). (5.6 ge=0; fix F29/F80/F82)
    fundamentals.py           InstrumentFundamentals (per-ISIN, per-refresh). yfinance field map keys: market_cap, pe_ratio, pb_ratio, return_on_equity, return_on_assets, operating_margin, debt_to_equity, earnings_growth_yoy, revenue_growth_yoy, dividend_yield, beta, current_price, fifty_two_week_high/low, sector, industry. (#51 OPEN: dividend_yield unit inconsistency — some rows stored already-as-percent, _fmt_pct multiplies by 100)
    earnings_event.py         F14 EarningsEvent (one doc per ISIN per earnings_date)
    suggestion.py             SuggestionRun, SuggestionOutcome, CandidateScore, SignalScore, GateResult. F2 direction; 5.6 round-trip. SuggestionRun.id POPULATED post-insert by _persist_run since 5.16 (TD35). (TD7/#45 deferred)
    news.py                   NewsArticle (only news model). 5.12: bulky field is `body_text` (NOT `body`); `body_purged_at` stamped by purge cron (TD27). Classified fields: sentiment, sentiment_confidence, themes, severity, classifier_summary. (#50 OPEN: entities_isins can carry the wrong ISIN — over-broad tagging upstream in news_fetcher/classifier)
    monitored_stock.py        MonitoredStock + MonitoredStockFeedbackPatch. (A1 Literal aligned). (TD1/#43 deferred: direction-aware — #26 added direction-aware RELABEL on the feedback payload/outcome filter, but monitored_stocks itself stays direction-agnostic)
    macro_signal.py           placeholder
    conversation.py           Conversation(BaseDoc) — ACTIVE write model as of #27 (was placeholder). Fields: query, response, intent (QueryIntent 9-value Literal), scope (ConversationScope Literal["suggestions","holding"]|None — ADDED #27, surface discriminator distinct from intent), sentiment_overlay (cautious|neutral|aggressive), related_entities_isins, related_holding_id, related_monitored_id, cited_news_ids/cited_macro_signal_ids/cited_digest_ids/cited_transaction_ids, model_used, input_tokens, output_tokens, cost_usd (Money), duration_ms, user_action, user_action_at, follow_up_conversation_ids (UNUSED — threading reserved for a future unit), created_at
    reconciliation.py         ReconciliationSnapshot (fix F16/F17)
    cost_basis_adjustment.py  CostBasisAdjustment (fix F18/F19)
    alert_log.py              placeholder
    digest.py                 placeholder (delivery audit lives in `digest_deliveries`)
    price_daily.py            placeholder (collection writers use raw dicts)
    symbol_override.py        SymbolOverride (fix F79)
    user_profile.py           UserProfile (singleton, _id="sahil")
  routers/
    holdings.py               /portfolio/holdings*, /sell, /preview-sell, /history, /transactions. (done: #5 validate_replay on /sell; #6 dup list_transactions deleted; #7 try/except around recompute_holding -> recorded_with_warning; #15/TD29 dead `from pydoc import doc` removed). NOTE: `list_holdings` is the canonical annotate path (bulk_get_latest_prices + bulk_get_previous_closes + annotate_with_current_price + _doc_to_response) that F15/#28 `/portfolio/by-tag` reuses verbatim
    portfolio.py              /portfolio/summary + /portfolio/risk-summary (F12/#28) + /portfolio/by-tag (F15/#28). _serialize recursive Decimal/Decimal128->str, ObjectId->str, datetime->ISO. (done #28: GET /risk-summary mirrors the /summary skeleton -> compute_risk_summary; GET /by-tag?tag=X required Query(min_length=1)->422, find({"deleted_at":None,"tags":tag}) exact case-sensitive array match, annotated via the list_holdings path, tag-scoped totals via the imported portfolio_service._to_dec, unknown tag -> zeroed 200). master_todo #30: utcnow() sweep (line ~43 in the empty-portfolio branch of /summary)
    transactions.py           /transactions/search, CRUD, audit. (fix F21 reason required). (done: #4 write-before-apply audit-then-apply; #18/TD32 dropped $options:i on search regex). master_todo #31: tz-aware datetime sweep
    reconciliation.py         /reconciliation/snapshot, /snapshots, /auto-snapshot
    instruments.py            /instruments (symbol_overrides CRUD) + /instruments/search/{symbol_prefix} + /instruments/{exchange}/{symbol}. (done #27 route-shadow fix: the STATIC /search/{symbol_prefix} route is now declared BEFORE the dynamic /{exchange}/{symbol} route — FastAPI matches in registration order, so the dynamic route was capturing /instruments/search/INFY as exchange=search,symbol=INFY and 404'ing; search was unreachable over HTTP. NOTE comment added so the ordering isn't reintroduced.)
    cost_basis.py             /cost-basis/adjustments
    suggestions.py            /suggestions/latest, /runs, /runs/{id}, /performance, /{isin}/feedback, /{isin}/audit, /feedback/audit/recent. F2 ?direction; A1 MonitoredStockFeedbackPatch; A19 Query() pattern=. (done: #17/TD31 ISIN pattern on the two /{isin} Path params; #26 direction-aware feedback relabel)
    conversations.py          NEW (#27). Ad-hoc chat: POST /chat/suggestions (F1), POST /chat/holdings/{isin} (F3, ISIN pattern=r"^[A-Z0-9]{12}$", 404 on unknown instrument), GET /chat/history?scope=&isin=&limit=. Thin HTTP layer: validate (ChatRequest, extra="forbid", query 1..2000, optional sentiment_overlay) -> delegate to conversation_service -> serialize. _jsonable/_serialize_conversation mirror routers/suggestions.py decimal-to-jsonable. APIRouter(prefix="/chat", tags=["chat"]).
    cron.py                   /cron/heartbeats (F4)
  services/
    instrument_service.py     lookup_isin, lookup_metadata, bulk_lookup_isins, refresh_from_nse (NOTE: docstring still says refresh_from_kite — doc drift, harmless). (done #27: lookup_by_isin(isin) — reverse lookup ISIN -> instrument dict, NSE-preferred then any-exchange; backed by the existing instruments.isin index)
    yfinance_lookup.py        thin yfinance Ticker wrapper. fetch_metadata(symbol, exchange) lru-cached, swallows exceptions -> safe-default dict. (symbol-keyed; cannot resolve from an ISIN alone — why #27 returns a clean 404 for an unknown ISIN rather than a yfinance rescue)
    price_service.py          EOD+intraday fetch, bulk_get_latest_prices, bulk_get_previous_closes(isin_to_latest_date: dict[str,datetime]), annotate_with_current_price(holding_doc, latest_price_doc, previous_close=None), get_previous_close. IST + _to_ist() helpers (TD23). (done: #9/TD23 holiday guard; #10/TD24 docstring; #11/TD25 per-ISIN find_one; TD26 captured_at BSON Date). (Chat 7 #28: annotate_with_current_price + bulk_get_previous_closes are the shared annotate primitives F15 by-tag reuses; unchanged.) master_todo #31: tz-aware sweep (line 155); #41 (Chat 9): stop_loss alert trigger
    holdings_service.py       recompute_holding (per-ISIN advisory-lock wrapper) + _recompute_holding_impl + _per_isin_recompute_lock (CM), validate_replay, preview_sell, _to_decimal. (done: #8/TD20 serialized per-ISIN via recompute_locks + 60s TTL)
    portfolio_service.py      compute_summary + _annotate_holdings + compute_risk_summary (F12/#28). (done #28: extracted _annotate_holdings(holdings, latest_prices) -> (annotated, accum) from compute_summary — behaviour-preserving, the per-holding value/P&L loop + running totals; compute_summary now calls it. compute_risk_summary(holdings, latest_prices) calls the SAME helper (no parallel aggregation): concentration_by_holding (every priced holding desc by %), concentration_by_sector, two-tier alerts from module constants SINGLE_HOLDING_CONCENTRATION_WARN_PCT=10.0 / HIGH_PCT=20.0, SECTOR_CONCENTRATION_WARN_PCT=30.0 / HIGH_PCT=50.0 (the TOP_MOVERS_LIMIT / CONCENTRATION_LIMIT operational-constant-in-code pattern), plus a low-severity stale_price data-quality note over the existing price_stale/missing-price flag.) _to_dec helper is imported by routers/portfolio.py for the by-tag totals math (no parallel converter)
    transactions_audit_service.py  log_change, get_audit_for_transaction. (5.10: log_change invoked BEFORE apply — TD16)
    monitored_stocks_audit_service.py  F10 log_change (write-before-apply)
    reconciliation.py         take_auto_snapshot, drift detection, _send_drift_alerts (ntfy + email), _send_auto_drift_alert (ntfy ONLY). (fix F1/F23). (done: #25 take_auto_snapshot fires push_public("price",...) on invested drift, rising-edge deduped). master_todo #31: tz-aware sweep
    cost_basis_service.py     get_active_adjustments, total_adjustment_amount
    fundamentals_service.py   yfinance provider; get_latest_for_isin, is_fresh(doc, max_age_days=14) (DEFAULT_FRESHNESS_DAYS=14), refresh_one(isin,symbol,exchange="NSE") (returns persisted doc or None), refresh_universe; F14 refresh_earnings_for(isin,symbol,exchange="NSE") + get_next_earnings_for_isin(isin). (#27 ensure_stock_context reuses get_latest_for_isin/is_fresh/refresh_one/refresh_earnings_for/get_next_earnings_for_isin verbatim).  master_todo #30: utcnow() sweep (lines 370, 485, 505); #51: dividend_yield unit
    tavily_client.py          quota-tracked wrapper, TavilyQuotaExceeded. (done: #19/TD33 atomic find_one_and_update quota claim). master_todo #31: tz-aware sweep
    news_fetcher.py           fetch_for_instrument(isin, symbol, name, days=30, use_case="suggestions_news") (Tavily; persists news_articles classified=False; may raise TavilyQuotaExceeded), fetch_for_universe. (#27 ensure_stock_context calls fetch_for_instrument on a cold/stale name). #50 OPEN: this + classifier attach the entities_isins that can be wrong
    news_classifier.py        Haiku batch classifier classify_unclassified(limit=None, isin_filter=None, only_recent_days=35), retry pass. (fix F27). (#27 ensure_stock_context calls classify_unclassified(isin_filter=[isin], only_recent_days=35) on freshly-fetched articles). #50 OPEN
    news_signals.py           compute_news_signals_for_isin, _bulk
    scoring_service.py        extract_signals, score_candidates, weights, gates. F14 earnings-proximity gate; F2 sell-side scoring.  master_todo #30: utcnow() sweep (lines 116, 813, 890)
    dossier_service.py        generate_dossiers_for_top_k, Sonnet. _generate_one (lazy Anthropic import, ANTHROPIC_MODEL_PRIMARY, system + messages, range(2) retry, collect block.text, JSON parse + fallback) — the wiring #27 mirrors. _build_user_prompt closures + _format_news_summaries + _to_float + _build_position_context_block (LTCG>365d / near-LTCG<=30d / weight=close*qty/PV; coupled to CandidateScore). #27 imports _to_float + _format_news_summaries from here; reimplements the position block (CandidateScore-free) + the Sonnet call. F2 sell-side prompt. master_todo #30: utcnow() sweep (lines 166, 192). (TD3/#44 deferred); #51: _fmt_pct ×100 dividend_yield
    conversation_service.py   NEW (#27). Two layers: (1) ENRICHMENT — ensure_stock_context(isin): _resolve_identity via instrument_service.lookup_by_isin (None -> {"resolved":False} -> router 404; no yfinance rescue), _ensure_fundamentals (14d freshness -> refresh_one), _ensure_earnings (get_next_earnings_for_isin -> refresh_earnings_for, gated by a recent-refresh check on earnings_calendar.fetched_at), _ensure_news (count classified last-30d -> fetch_for_instrument + classify_unclassified if stale; TavilyQuotaExceeded + failures degrade to cached). Freshness gates: FUNDAMENTALS_MAX_AGE_DAYS=14, NEWS_LOOKBACK_DAYS=30, NEWS_REFETCH_AFTER_DAYS=7, NEWS_DISPLAY_LIMIT=8, EARNINGS_REFRESH_AFTER_DAYS=14. Writes ONLY Phase-2 reference collections (fundamentals/earnings/news), never Phase-1. (2) CHAT — chat_about_holding(isin, query, sentiment) (F3: ensure_stock_context -> _held_overlay (holdings find_one deleted_at:None + bulk_get_latest_prices + get_active_holdings_full + compute_portfolio_value) -> _build_holding_prompt (buy-research framing if not held, position/tax overlay if held) -> _call_sonnet -> persist; returns None -> 404 if unknown ISIN) and chat_about_suggestions(query, sentiment) (F1: _build_suggestions_context from get_latest_run("buy"/"sell") top_candidates + dossiers from run.notes -> _call_sonnet -> persist). _call_sonnet mirrors dossier_service._generate_one ({answer,intent} JSON envelope, range(2) retry, graceful fallback). _compute_cost: Sonnet $3/$15 per MTok constants -> Decimal -> Money cost_usd. _persist_conversation inserts then RE-READS the doc (router serializes POST + history through one dict path). Reuses dossier_service._to_float/_format_news_summaries, suggestion_engine.get_latest_run/get_active_holdings_full/compute_portfolio_value, price_service.bulk_get_latest_prices.
    suggestion_engine.py      run_suggestions (full pipeline); get_excluded_isins; get_latest_run(direction); get_active_holdings_full(); compute_portfolio_value(holdings, prices). F2 direction. (done: #21/TD35 _persist_run sets run.id). (#27 chat F1 + held overlay reuse get_latest_run / get_active_holdings_full / compute_portfolio_value)
    outcome_tracker.py        create_outcomes_for_run, snapshot_open_outcomes (returns count under `active_outcomes` — NOT `open_outcomes`; #47), compute_system_performance. F2 direction stamp + read-time sign-flip
    digest_delivery.py        send_weekly_digest, send_combined_digest. F2b ntfy; A2 part1 delegates to notify.email(). (done: #21/TD35 reads buy_run.id; internal find_one re-derivation deleted)
    explainability.py         SIGNAL_META, GROUP_META, GATE_META, FEEDBACK_META, PAGE_INTRO + PAGE_INTRO_SELL, enrich_run, enrich_candidate
    notify.py                 push_public, email. A2: email returns {ok,id,error}, optional text=. push_public RAISES on failure. (done: #20/TD34 email() retries once on transient 429/5xx with 30s backoff; contract unchanged). NOTE: #25 + #35 call push_public GUARDED
    cron_heartbeat_service.py F4 cron_run CM, CRON_REGISTRY, get_recent_heartbeats, ist_today_window_utc. (done: TD14 registry rename; TD27 purge CronSpec; #23/TD38 _append_fallback + count_today_heartbeats_from_fallback; #49/TD40 idle weekly_suggestions_sell expected_weekdays=set() — do NOT disturb the TD38 fallback paths)
scripts/
  __init__.py
  init_db.py                    calls ensure_all_indexes() generically (so #27's scope_created_desc was picked up with no edit) + seeds user_profile
  refresh_instruments.py        (A13 docstring corrected to NSE EQUITY_L.csv)
  refresh_prices.py
  refresh_prices_intraday.py    (done: #35 insert_intraday_quotes wrapped -> GUARDED push_public("errors",...) + re-raise). master_todo #41 (Chat 9): stop_loss alert
  take_reconciliation_snapshot.py
  seed_nifty100.py              CORRECTLY NAMED. Reads ind_nifty100list.csv. (TD12 resolved-as-doc-fix)
  seed_cost_basis_adjustments.py
  import_orderbooks.py          (calls recompute_holding -> per-ISIN locked, TD20)
  reconcile_staging.py
  promote_staging.py            (calls recompute_holding -> per-ISIN locked, TD20)
  add_manual_transactions.py    (done: #5 validate_replay on manual SELL path)
  refresh_fundamentals.py       F14 default universe NIFTY100 ∪ active holdings. (Chat 8/#29 will extend for watchlist)
  fetch_news_for_universe.py    (A16 --include-held). (Chat 8/#29 watchlist). Only prod path exercising Tavily quota guard (Sun 06:30 IST; TD33). #50: universe-scoped tagging is where wrong entities_isins likely originate
  run_weekly_suggestions.py     F2 --direction=buy|sell|both. (done: #1/TD14 crontab flags; #21/TD35 _do_both via buy_run.id/sell_run.id)
  track_suggestion_outcomes.py  (done: #47/TD22 — reads stats["active_outcomes"] (was "open_outcomes" -> KeyError daily))
  cron_health_check.py          F4 daily 21:00 IST; dual-transport. (done: #23/TD38 merges fallback counts; #24/TD39 self-failure dual-transport alert + re-raise)
  smoke_test.py                 (TD8 dropped push_private)
  purge_news_bodies.py          (done: #13/TD27 daily 02:30 IST; $unset body_text + stamp body_purged_at; --dry-run)
tests/
  __init__.py                   placeholder.  master_todo #33: stand up pytest harness
docs/
  data_flow.md                  (5 deliverable; 5.5 TD12 universe corrected). (done: #48/TD36 Tavily "monthly" -> "daily (resets 00:00 UTC)")
  Project_State.md              THIS FILE (Chat 7 doc commit; recovered from 5.8 truncation in 5.9 — Section 18 TD15)
  master_todo.md                canonical ordered task list (Chat 5.8 NEW)
pyproject.toml                  master_todo #32: pin requires-python upper bound (declares resend>=2.4 + anthropic)
uv.lock
README.md                       (5 deliverable; 5.5 §8/§11/§5). (done: #48/TD36 Tavily monthly -> daily; TAVILY_MONTHLY_QUOTA -> TAVILY_DAILY_CALL_LIMIT)
```

## Section 6: Frontend file map

Verified against tree at SHA `4f31b49` (unchanged 5.10–5.12; 5.13 touched notes-panel.tsx + refresh-button.tsx → `f59958`; 5.14–5.19 + Chat A backend/doc-only; Chat 6 → `6093f63` ADDED chat-panel.tsx + stock-research-panel.tsx, edited lib/api.ts + suggestions page + holdings drill-down). Re-verified against the Chat 7 tree listing at frontend HEAD `6093f63` (open) — Chat 7 → `e14d6a75` ADDED `components/risk-summary-card.tsx` + `app/tags/page.tsx`, edited `lib/api.ts` + `app/page.tsx`.

```
app/
  layout.tsx · page.tsx (dashboard) · providers.tsx (ThemeProvider + TanStack QueryClient + ReactQueryDevtools) · globals.css · favicon.ico
  page.tsx                   dashboard. (done #28: mounts <RiskSummaryCard> (F12) as a full-width section below the Sector/Top-Movers grid via an independent useQuery(["dashboard","risk"] -> api.getRiskSummary) so a risk-endpoint failure doesn't block the main dashboard; added a "Tags" header nav link -> /tags)
  tags/page.tsx              NEW (#28). F15 tag view. Derives the tag universe from api.getHoldings().tags, renders a tag-pill selector; on selection useQuery(["tags","by-tag",tag] -> api.getHoldingsByTag, enabled only when a tag is picked) -> tag-scoped totals row + the existing <HoldingsTable> reused wholesale. Back-link to / ; lucide Tag/ArrowLeft.
  holdings/[isin]/page.tsx    drill-down. (done #27: embeds <ChatPanel> for the held stock — F3). (Chat 9/#41: stop_loss edit field)
  reconciliation/page.tsx · cost-basis/page.tsx · transactions/page.tsx · transactions/audit/page.tsx
  suggestions/page.tsx        F6 user_action collapsed render; F2 shadcn Tabs buy/sell. (done #27: embeds <ChatPanel scope="suggestions"> (F1) + <StockResearchPanel> for not-held buy research)
components/
  ui/                         shadcn primitives (alert-dialog, badge, button, card, chart, dialog, dropdown-menu, input, label, popover, select, separator, sheet, skeleton, table, tabs, textarea, tooltip)
  holdings-table.tsx          HoldingsTable({holdings: Holding[]}) — self-contained (own search/sort, row -> /holdings/{isin}). Reused as-is by the /tags page (#28). (Chat 9/#40: hide realized P&L)
  buy-sheet.tsx
  sell-sheet.tsx              Phase-1 manual SELL sheet with FIFO preview. NOT the F2 sell-side surface. OPEN FOLLOW-UP (5.10): discriminates on absence of _id; a TD19 recorded_with_warning response (no _id) falls through its non-holding branch. Deferred.
  transaction-edit-sheet.tsx
  holding-header.tsx          (Chat 9/#40: hide realized P&L)
  holding-stats.tsx           (Chat 9/#40 + #41: realized P&L hide + stop_loss edit field)
  price-chart.tsx · transactions-list.tsx
  notes-panel.tsx             (done: #14/TD28 invalidateQueries -> refetchQueries)
  recent-activity-card.tsx · sector-breakdown.tsx · stat-card.tsx · top-movers.tsx
  totals-row.tsx              (Chat 9/#40: hide realized P&L)
  reconciliation-badge.tsx · theme-provider.tsx · theme-toggle.tsx
  refresh-button.tsx          (done: #14/TD28 invalidateQueries -> refetchQueries)
  suggestion-card.tsx         F6 CollapsedFeedbackRow; F2 isSellSide branch. (renders LLM text as plain strings — the house pattern that confirmed #27 needed its own markdown renderer)
  explain-popover.tsx · page-intro.tsx
  chat-panel.tsx              NEW (#27). Reusable chat surface: props {title, description, placeholder, historyParams:{scope,isin?}, send}. useQuery(["chat",scope,isin] -> api.getChatHistory) renders the transcript oldest-first; useMutation(send) onSuccess refetchQueries (synchronous, per convention) the same key; composer (Textarea, cmd/ctrl+Enter), sentiment toggle (cautious|neutral|aggressive), pending state; ApiError detail surfaced via sonner toast. Includes MarkdownLite — a self-contained renderer for the subset Sonnet emits (h1-h3, **bold**, -/* + numbered lists, ---, paragraphs) because the project has NO markdown dependency (keeps deploy a plain npm run build). lucide icons: MessageSquare/Send/Loader2.
  stock-research-panel.tsx    NEW (#27). Not-held buy-research entry point on /suggestions. Input -> useQuery(["instrument-search",prefix] -> api.searchInstruments, enabled prefix>=2) -> pick a result (filters to rows with isin) -> renders <ChatPanel scope="holding" isin=...> bound to api.chatHolding. lucide: Search/X.
  risk-summary-card.tsx       NEW (#28). F12 dashboard card. Props {data?: RiskSummary, isLoading, error}. Renders the alerts array (severity-colored rows: high->destructive, warn->secondary, info->outline Badge; empty -> "within thresholds" reassurance), top-5 concentration_by_holding (links to /holdings/{isin}) and concentration_by_sector. Reuses inr/pct from lib/format + shadcn Card/Badge/Skeleton. lucide: ShieldAlert/AlertTriangle/Info/ShieldCheck. Module const TOP_CONCENTRATION_ROWS=5 (the API returns the full list).
lib/
  api.ts                      hand-typed API client; SINGLE SOURCE OF TRUTH; F2 direction param, BucketKey, by_bucket. (done #27: ChatScope/SentimentOverlay/ChatConversation/ChatRequestPayload/InstrumentSearchResult types + chatSuggestions, chatHolding, getChatHistory, searchInstruments wrappers). (done #28: RiskSummary/RiskConcentrationHolding/RiskConcentrationSector/RiskAlert/RiskAlertSeverity + HoldingsByTag/TagTotals types + getRiskSummary, getHoldingsByTag wrappers. NOTE: the existing ConcentrationItem/SectorBucket types did NOT match the risk-summary shapes — new types, not reuse.)
  format.ts                   inr, pct, colorForChange, dateTime, nf, date (+ inrSigned). (#28 risk card + tags page reuse inr/pct/inrSigned/colorForChange)
  utils.ts                    cn() (clsx + tailwind-merge)
public/                       static SVGs
README.md                     (5 deliverable at SHA 9edfc8f; TD13 per-page reference at 4f31b49 — 7 routes + the chat embeds; #28 adds the /tags route — README per-page reference now describes 8 routes' worth of surface, chat embeds on existing pages)
AGENTS.md · CLAUDE.md · components.json (Nova) · package.json · package-lock.json
next.config.ts (default) · postcss.config.mjs · tsconfig.json (strict; "@/*"; bundler) · .npmrc (legacy-peer-deps)
```
No `middleware.ts`, no `.env.example`, no custom next.config overrides at HEAD. Tailscale is the auth perimeter. No markdown library in package.json — `MarkdownLite` is self-contained (Chat 6). #28 added NO new npm dependency and NO new shadcn primitive (risk card + tags page use only existing Card/Badge/Button/Table/Skeleton).

## Section 7: Database collections (exhaustive)

All in Atlas M10. DB name from env `MONGODB_DB_NAME`; **live value is `portfolio`, NOT `portfolio_advisor`** (5.12 lesson). Accessed via `Collections.<name>()`. Indexes ensured at startup via `app/db/indexes.py`.

**Phase 1:**
* **instruments** — NSE/BSE master, daily from NSE EQUITY_L.csv. Fields: exchange, symbol, isin, name, instrument_type, segment, lot_size, tick_size, source, last_seen_at, last_changed_at, in_nifty100, nifty100_marked_at. ~2,368 total; ~100 in_nifty100. Indexes: (exchange, symbol) unique, isin, last_seen_at, last_changed_at, in_nifty100. (#27 `lookup_by_isin` reverse-resolves via the `isin` index, NSE-preferred.)
* **symbol_overrides** — manual ISIN aliases. Fields: exchange, symbol, isin, reason, created_at.
* **holdings** — one doc per ISIN, soft-deleted on full exit. Fields: isin, symbol, exchange, name, sector, industry, quantity (Decimal128), avg_cost, invested_amount, realized_pnl, first_purchased_at, last_traded_at, thesis, notes, stop_loss, target_price, tags, deleted_at. **INVARIANT: every query MUST include `deleted_at: None`.** Indexes: isin unique (partial: deleted_at is None), (deleted_at, last_traded_at). Writer: `recompute_holding(isin)` is the ONLY authoritative writer; serialized per-ISIN via `recompute_locks` (TD20). `realized_pnl` structural but HIDDEN in UI (#40). (#27 chat reads holdings read-only for the F3 position/tax overlay; it NEVER writes holdings. #28 `/portfolio/risk-summary` + `/portfolio/by-tag` read holdings read-only — by-tag filters `{"deleted_at":None,"tags":<tag>}` via Mongo array-membership on the existing `tags` field; no new index needed for the single-user volume.)
* **transactions** — append-only ledger. Fields: isin, symbol, exchange, type (BUY/SELL/SPLIT/BONUS/DEMERGER), trade_date, quantity (Decimal128), price, total_fees, remaining_quantity, notes, source, corporate_action.{ratio_from,ratio_to}, fully_consumed_at, deleted_at. **INVARIANT: never directly UPDATE/DELETE; PATCH/DELETE require reason, write transactions_audit first, then apply, then recompute_holding** (#4/TD16 SHIPPED 5.10). Indexes: (isin, trade_date), (symbol, trade_date), trade_date. 5.13 (TD32): GET /transactions/search prefix-matches symbol with `{"$regex": f"^{escaped}"}` (NO $options:i; uses (symbol, trade_date) index).
* **transactions_staging** — ICICI import holding area, same shape. 5.10 (TD17): add_manual_transactions.py replays per-ISIN timeline + proposed SELL via validate_replay and ABORTS (RuntimeError) rather than insert an impossible SELL.
* **transactions_audit** — append-only, one doc per edit/delete. Fields: transaction_id, action, reason, changed_fields, performed_at, symbol. **INVARIANT: written BEFORE the change is applied** (#4/TD16 SHIPPED 5.10).
* **recompute_locks** (TD20, NEW 5.10) — per-ISIN advisory locks. Fields: _id (== isin), acquired_at. **INVARIANT:** acquired via atomic insert_one (unique _id index = one winner); released via delete_one in finally; competing acquirer spin-waits on DuplicateKeyError until free or 10s timeout. Indexes: default _id unique; TTL on acquired_at (expireAfterSeconds=60). Accessor `Collections.recompute_locks()`; holder `_per_isin_recompute_lock` CM.
* **prices_daily** — EOD OHLCV, ~5y. Fields: isin, date, OHLC, volume, source. Indexes: (isin, date) unique. (#28 risk-summary + by-tag read latest + previous close via the existing bulk_get_latest_prices / bulk_get_previous_closes point-queries on this index.)
* **prices_intraday** — latest intraday quote every 15 min during market hours. Fields: isin, symbol, date, captured_at, OHLCV, source="yfinance_5m_latest". **INVARIANT: append-only within a day.** TTL: `captured_at_ttl` (ASC, expireAfterSeconds = 90*86400 = 7776000) SHIPPED 5.12 (TD26) — coexists with non-TTL `captured_at_desc` (DESC). Indexes: isin_captured_at_desc, captured_at_desc, captured_at_ttl. Writer: `refresh_prices_intraday.py` → `_intraday_row_from_df`. #9/TD23: holiday guard. #35 (Chat A): an `insert_intraday_quotes` exception fires a guarded ntfy + re-raises.
* **reconciliation_snapshots** — our totals vs ICICI Direct. Fields: type, taken_at, our_invested, our_current_value, our_day_gain, icici_*, drift_invested_pct, drift_current_pct, drift_alerts, notes, plus drift_invested/has_drift/alerts_sent. #25 (Chat A): take_auto_snapshot fires push_public("price",...) on invested drift > threshold vs the last manual snapshot — ntfy ONLY, rising-edge deduped.
* **cost_basis_adjustments** — audit trail for TMPV/TMCV per IT Act Section 49(2C).
* **user_profile** — single doc, _id="sahil".

**Phase 2:**
* **monitored_stocks** — user-feedback state + watchlist (F13). Fields: isin, status (Literal tracking/passed/rejected/watchlist), symbol, exchange, name, sector, industry, added_by, added_reason, added_at, thesis, conviction, conviction_history, target_buy_price, alert_above, alert_below, alert_on, tags, user_notes, last_reviewed_at, last_user_interest_at, acted_at, passed_at, rejected_at, last_feedback_action, last_feedback_at, last_feedback_note, created_at, updated_at. **INVARIANT (F10): writes preceded by monitored_stocks_audit_service.log_change(...).** Indexes: isin unique (PARTIAL, partialFilterExpression={"status":"tracking"}), (status, rejected_at). TD1/#43 deferred.
* **monitored_stocks_audit** (F10) — append-only. Fields: isin, action, previous_status, new_status, note, performed_at, _schema_version. **INVARIANT: writer invoked BEFORE update_one.** Indexes: (performed_at desc), (isin, performed_at desc).
* **instruments_fundamentals** — one doc per ISIN per refresh. Indexes: isin_latest_unique, fetched_at. F14: universe NIFTY100 ∪ active holdings. (#27 ensure_stock_context refreshes a cold/stale ISIN on demand via fundamentals_service.refresh_one — the same writer the weekly cron uses; not a Phase-1 write. #51 OPEN: dividend_yield unit inconsistency.)
* **earnings_calendar** (F14) — upcoming + historical per ISIN (yfinance Ticker.calendar). Fields: isin, symbol, exchange, earnings_date, source, source_raw, fetched_at, created_at. **INVARIANT: refresh deletes future events then re-inserts.** Indexes: (isin, earnings_date) unique, (earnings_date asc), (isin), (fetched_at desc). (#27 ensure_stock_context refreshes on demand via refresh_earnings_for, gated by a recent-refresh check on fetched_at.)
* **news_articles** — classified news, one doc per URL. Fields: url, title, published_at, fetched_at, source, body_text, body_purged_at, entities_isins, themes, sentiment, sentiment_confidence, severity, classifier_summary, classified. Indexes: url unique, (entities_isins, classified, fetched_at), (classified, fetched_at), body_purged_at. body_text purged daily (TD27). (#27 ensure_stock_context fetches+classifies a cold/stale ISIN on demand; the F3 chat reads classified last-30d articles for the ISIN. #50 OPEN: entities_isins can carry the wrong ISIN — the HDFCBANK chat surfaced TCS/Kenya articles tagged with HDFC's ISIN; defect is upstream in news_fetcher/classifier tagging.)
* **suggestion_runs** — append-only run history. Fields: _id, _schema_version, run_date, run_date_ist, run_type, direction, status, started_at, finished_at, error, universe_size, excluded_*, candidates_*, config, top_candidates, all_candidates, top_k, notes. **INVARIANTS:** append-only; legacy round-trips cleanly. 5.16 (TD35): `_persist_run` sets `run.id = result.inserted_id`. notes is a JSON string `{dossiers:[...]}`. Indexes: (run_date desc), (run_date_ist, run_type), (status). (#27 chat F1 reads get_latest_run("buy"/"sell").top_candidates + parses dossiers from notes — read-only.)
* **suggestion_outcomes** — one doc per top-K candidate per run. Fields: isin, symbol, suggestion_run_id, suggested_at, suggested_at_price, suggested_rank, suggested_composite_score, tracking_status, direction, price_at_{30,60,90,180}d, nifty_at_{30,60,90,180}d, excess_return_*, user_action_at, user_action_note, created_at, updated_at. **INVARIANTS:** snapshot eligibility `tracking_status != "expired"`; auto-flip at day 180 for "open"; sell sign-flips at read time. snapshot_open_outcomes returns its count under `active_outcomes` (#47).
* **tavily_quota** — one doc per UTC day. Fields: date_utc, calls_today, credits_today, per_use_case.<uc>.{calls,credits}, first_call_at, last_call_at. **INVARIANT: TAVILY_DAILY_CALL_LIMIT (default 200) hard ceiling on calls_today per UTC day; credits tracked NOT capped; resets 00:00 UTC** (#48/TD36). Indexes: unique date_unique on date_utc. #19/TD33 atomic find_one_and_update. (#27 on-demand news fetch consumes this quota; TavilyQuotaExceeded degrades the chat to cached news.)
* **digest_deliveries** — audit log of weekly digests. Fields: run_id, run_date_ist, sent_at, top_count, subject, email_*, ntfy_*. #21/TD35 (5.16): run_id sourced explicitly via run.id.
* **cron_heartbeats** (F4) — Fields: cron_name, started_at, finished_at, status, error, metadata, _schema_version. **INVARIANTS:** append-only, best-effort WITH DISK FALLBACK (5.18 #23/TD38). 5.9 TD14 cron_name="weekly_suggestions". 5.19 #24/TD39 self-failure path. Chat A #47 track_suggestion_outcomes now SUCCESS; #49 removed weekly_suggestions_sell Sunday false MISSING. Indexes: (cron_name, started_at desc), (started_at desc), TTL on started_at (60 days).
* **conversations** (#27 — ACTIVELY WRITTEN; was scaffold) — one doc per ad-hoc chat exchange. Model: `Conversation(BaseDoc)` (Section 5). Fields: query, response, intent (QueryIntent), scope (suggestions|holding), sentiment_overlay, related_entities_isins, related_holding_id, related_monitored_id, cited_news_ids/cited_macro_signal_ids/cited_digest_ids/cited_transaction_ids, model_used, input_tokens, output_tokens, cost_usd (Money/Decimal128), duration_ms, user_action, user_action_at, follow_up_conversation_ids (UNUSED — threading reserved), created_at. **INVARIANTS:** written ONLY by conversation_service._persist_conversation (insert then re-read); chat is read-only on Phase-1 portfolio data and on suggestion runs (it only writes conversations + on-demand refreshes shared Phase-2 reference collections). Indexes (all pre-existing except scope_created_desc): created_at_desc, intent_created_desc (intent, created_at desc), isins_created_desc (related_entities_isins, created_at desc), related_holding (related_holding_id), scope_created_desc (scope ASC, created_at DESC — NEW #27).

**Scaffold (not actively written):** digests, alerts_log, macro_signals.
**Future:** none pending. F11 read-only reformatter; F13 watchlist reuses monitored_stocks status="watchlist". (#28 F12/F15 needed NO new collection — both read existing holdings + prices_daily.)

## Section 8: API endpoints (exhaustive)

**Phase 1**
```
GET    /health                                       (done #34: pings Mongo; 200 ok/ok or 503 degraded/fail)
GET    /portfolio/holdings                           Holding[]
GET    /portfolio/holdings/{isin}                    Holding
POST   /portfolio/holdings                           Holding (BUY)            (#7: recorded_with_warning on recompute fail)
PATCH  /portfolio/holdings/{isin}                    Holding (notes/thesis/stop_loss/target_price/tags only)
POST   /portfolio/holdings/{isin}/sell               Holding OR {message, realized_total}   (#5 validate_replay; #7 recorded_with_warning)
POST   /portfolio/holdings/{isin}/preview-sell       SellPreview
GET    /portfolio/holdings/{isin}/history?days=N     PriceBar[]
GET    /portfolio/holdings/{isin}/transactions       Transaction[]            (#6 dup handler deleted)
GET    /portfolio/summary                            PortfolioSummary
GET    /portfolio/risk-summary                       RiskSummary              (done #28 F12: concentration_by_holding + concentration_by_sector + two-tier alerts; read-only; reuses the /summary annotation path via _annotate_holdings)
GET    /portfolio/by-tag?tag=X                       {tag, holdings, totals}  (done #28 F15: tag required (min_length=1)->422; find({"deleted_at":None,"tags":tag}) exact case-sensitive; holdings annotated same shape as /portfolio/holdings; tag-scoped totals; unknown tag -> empty + zeroed 200)
GET    /transactions/search?...                      {results, total}         (#18 dropped $options:i)
GET    /transactions/{id}                            Transaction
PATCH  /transactions/{id}                            Transaction (requires reason)   (#4 write-before-apply)
DELETE /transactions/{id}                            {deleted: true} (requires reason) (#4 write-before-apply)
GET    /transactions/audit/recent?limit=N            AuditEntry[]
GET    /transactions/{id}/audit                      AuditEntry[]
POST   /reconciliation/snapshot                      ReconciliationSnapshot (manual)
GET    /reconciliation/snapshots                     ReconciliationSnapshot[]
POST   /reconciliation/auto-snapshot                 ReconciliationSnapshot (cron)   (done #25: ntfy on drift)
GET    /cost-basis/adjustments                       CostBasisAdjustment[]
GET    /instruments                                  symbol_overrides list
POST   /instruments                                  symbol_overrides upsert
GET    /instruments/search/{symbol_prefix}?limit=N   [{exchange, symbol, isin, name}]  (done #27: now declared BEFORE /{exchange}/{symbol} so it is reachable — see route-shadow fix; backs the not-held research entry point)
GET    /instruments/{exchange}/{symbol}              full instrument metadata
DELETE /instruments/{exchange}/{symbol}              delete override
```

`GET /portfolio/risk-summary` shape (F12/#28): `{as_of (iso), total_current_value (string), concentration_by_holding: [{isin, symbol, sector, current_value (string), pct_of_portfolio (float)}] (every priced holding, desc by pct), concentration_by_sector: [{sector, stock_count, current_value (string), pct_of_portfolio}], alerts: [{type, severity, message, ...}]}`. Alert types: `single_holding_concentration` (+ isin, symbol, pct_of_portfolio, threshold; severity warn>10% / high>20%), `sector_concentration` (+ sector, pct_of_portfolio, threshold; severity warn>30% / high>50%), `stale_price` (+ count, isins[], symbols[]; severity info — holdings with stale/missing prices are excluded from the % denominator, so weights are understated). Thresholds are the four module constants in `portfolio_service.py` (NOT env-configurable; the TOP_MOVERS_LIMIT pattern). Decimals as strings.

`GET /portfolio/by-tag?tag=X` shape (F15/#28): `{tag, holdings: [<annotated holding, SAME shape as GET /portfolio/holdings>], totals: {count, invested (string), current_value (string), unrealized_pnl (string), unrealized_pnl_pct (float)}}`. invested counts every matched holding; current_value/unrealized only count priced holdings (an unpriced holding's current_value is null) so the totals reconcile with what the table renders. Tag match exact + case-sensitive. Missing/empty tag → 422; unknown tag → empty holdings + zeroed totals (200).

**Phase 2**
```
GET    /suggestions/latest?direction=buy|sell        SuggestionRun + enrichment
GET    /suggestions/runs?direction=buy|sell&...      {runs, total, limit, skip}
GET    /suggestions/runs/{run_id}                    SuggestionRun + enrichment
GET    /suggestions/performance?direction=buy|sell   SuggestionPerformance with by_bucket
POST   /suggestions/{isin}/feedback                  {isin, action, status, previous_status}   (#17 ISIN pattern; #26 direction-aware)
GET    /suggestions/{isin}/audit?limit=N             MonitoredStocksAuditEntry[] (F10)         (#17 ISIN pattern)
GET    /suggestions/feedback/audit/recent?limit=N    MonitoredStocksAuditEntry[] (F10)
GET    /cron/heartbeats?limit=N                      {heartbeats, health_summary}
```
`/cron/heartbeats` shape: `heartbeats` newest-first (default 200, max 1000); `health_summary` per-cron rows {cron_name, description, schedule, expected_today, min_runs_per_day, last_run_at, last_status, last_error, today_total, today_success, today_failure, today_skipped, healthy}. `healthy = true iff (not expected today) OR (today_success + today_skipped >= min_runs_per_day AND today_failure == 0)`.

**Chat (F1 + F3 / Chat 6 / #27 — LIVE)**
```
POST   /chat/suggestions                             ChatConversation   (F1: chat about the latest weekly buy+sell runs; body {query, sentiment_overlay?})
POST   /chat/holdings/{isin}                         ChatConversation   (F3: chat about a specific stock — HELD or researched not-yet-owned; ISIN pattern=r"^[A-Z0-9]{12}$"; 404 if not a known NSE instrument; on-demand enrichment)
GET    /chat/history?scope=&isin=&limit=             ChatConversation[] (newest-first; scope in {suggestions,holding}; isin pattern-validated; limit 1..100 default 20)
```
ChatConversation serialized shape: {id, query, response, intent, scope, sentiment_overlay, related_entities_isins, related_holding_id, model_used, input_tokens, output_tokens, cost_usd (string), duration_ms, created_at}. The persisted Conversation carries more (cited_* id lists, follow_up_conversation_ids) — intentionally not in the API response.

**Future (planned, see master_todo):**
```
POST   /watchlist/{isin}           (F13 / Chat 8 / #29 — NEXT)
DELETE /watchlist/{isin}           (F13 / Chat 8 / #29 — NEXT)
GET    /watchlist                  (F13 / Chat 8 / #29 — NEXT)
GET    /tax/capital-gains?fy=YYYY-YY (F11 / Chat 9 / #39)
POST   /admin/recompute/{isin}     (Ops gap / #36)
```

**Sell endpoint response shape (critical, often confused):** `POST /portfolio/holdings/{isin}/sell` returns one of: (a) full updated Holding (partial sell), (b) `{message: "Position fully exited", realized_total: "<string Decimal>"}` (full exit), (c) `{status:"recorded_with_warning", isin, warning}` (TD19). Frontend discriminates via type guard on `_id`. OPEN follow-up (5.10): the recorded_with_warning shape has no `_id`, so SellSheet treats it like full-exit — rare path, deferred.

## Section 9: Cron registry on EC2

`crontab -l` for current state. Every script is heartbeat-instrumented via `cron_run()`; the daily `cron_health_check` (21:00 IST) consumes them. `CRON_REGISTRY` in `cron_heartbeat_service.py` is the in-code mirror — keep both in sync. (Chat 6 added no crons — the chat feature is request-driven, not scheduled. Chat 7 added no crons — risk-summary + by-tag are request-driven read endpoints.)

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

**CRON_REGISTRY (11 entries, 5.12):** refresh_instruments, refresh_prices, refresh_prices_intraday, take_reconciliation_snapshot, refresh_fundamentals, fetch_news_for_universe, weekly_suggestions (renamed 5.9 TD14), track_suggestion_outcomes, cron_health_check, purge_news_bodies (5.12), weekly_suggestions_sell (idle; `expected_weekdays=set()` as of Chat A #49/TD40 so `cron_health_check` no longer emits the false Sunday MISSING; restore to `{6}` ONLY if you split the crontab into a standalone sell-side job that logs its own heartbeat under this cron_name).

**No silent failures:** every cron = log file path AND heartbeat instrumentation AND a CronSpec entry. AND the CronSpec.cron_name MUST equal the string the script passes to `cron_run()` (5.9 TD14; re-confirmed 5.12). 5.18 (#23/TD38) closed a related gap: a heartbeat whose Mongo INSERT fails now falls back to `/home/ubuntu/cron-heartbeat-fallback.log` and `cron_health_check` reads both. Chat A #47 fixed a real-failure case (track_suggestion_outcomes KeyError).

**Health-check self-resilience (5.19 #24/TD39):** `cron_health_check.main`'s ONLY Mongo reads are the per-cron `count_today_heartbeats` calls in the registry loop, now wrapped in `try/except`; on a Mongo-read failure it fires a dedicated "anomaly: health-check itself failed" alert on BOTH transports (GUARDED ntfy + email) then RE-RAISES. The #23 merge loop is preserved verbatim INSIDE the wrap.

**Dual transport (commit 8):** cron_health_check.py sends every anomaly batch on `push_public("errors",...)` + `notify.email(...)` and raises (run marked failed) ONLY when BOTH fail. The email leg retries a transient Resend 5xx/429 once (30s) inside notify.email() (TD34). The 5.19 self-failure path reuses the same two transports but re-raises unconditionally.

**Coverage notes:** TD33/TD35/TD38/TD39 + Chat A items each have no HTTP surface → covered at deploy via import graph + hermetic harnesses (details in git history). #34 (/health) IS HTTP-surfaced → live curl + forced-ping()-False probe. Chat 6 #27 IS HTTP-surfaced → covered by live curls on EC2 (F1/F3 held/F3 not-held/404/422/history) + the route-shadow regression curl. Chat 7 #28 IS HTTP-surfaced → covered by live curls on EC2 (risk-summary payload + the /summary regression curl-diff proving the _annotate_holdings refactor is behaviour-preserving; by-tag payload + shape-parity diff vs /portfolio/holdings + unknown-tag + missing/empty-tag 422) + frontend `npm run build`/lint via ~/deploy-ui.sh.

**Open scheduling work:** TD21/#46 registry-generated crontab migration (deferred; its own dedicated chat). TD22/#47 and TD40/#49 CLOSED Chat A.

## Section 10: Settings and environment variables

In `app/config/settings.py` via pydantic-settings. All required unless marked default.

* **Anthropic:** ANTHROPIC_API_KEY (req) · ANTHROPIC_MODEL_PRIMARY (default "claude-sonnet-4-5") · ANTHROPIC_MODEL_FAST (default "claude-haiku-4-5"). (#27 chat uses ANTHROPIC_MODEL_PRIMARY for the single structured chat call.)
* **MongoDB:** MONGODB_URI (req; URL-encode special chars in password). Code uses `MONGODB_URI` not `MONGODB_URL` (#16/TD30). MONGODB_DB_NAME (req) — live value `portfolio` (default `"portfolio"`).
* **Tavily:** TAVILY_API_KEY (req) · TAVILY_DAILY_CALL_LIMIT (default 200) — hard ceiling on calls_today per UTC day, enforced atomically (TD33); DAILY resets 00:00 UTC (#48/TD36; there is NO `TAVILY_MONTHLY_QUOTA` env var) · TAVILY_SEARCH_DEPTH (default "basic") · TAVILY_MAX_RESULTS_PER_QUERY (default 5).
* **Email (Resend):** RESEND_API_KEY (req) · RESEND_FROM · RESEND_TO · DIGEST_TO. No new env for the TD34 retry — constants in notify.py. (No new env for #27 — Sonnet pricing constants ($3/$15 per MTok) live in conversation_service.py, project convention: operational constants in code.)
* **ntfy:** NTFY_PUBLIC_URL (default "https://ntfy.sh") · NTFY_PUBLIC_TOPIC_PRICE/NEWS/ERRORS/DIGESTS · NTFY_PUBLIC_TOPIC_DIGESTS (F2b — REQUIRED, no default). All NTFY_PUBLIC_TOPIC_* identical on EC2 and Mac. `push_public(channel)` signature: `channel: Literal["price","news","errors","digests"]`. `NTFY_URL/USER/PASS` REMOVED (5.5 TD9).

(No new env for #28 — the risk-summary thresholds are module constants in `portfolio_service.py`, same convention: operational constants in code, not env/settings.)

## Section 11: Phase 1 INVARIANTS — never violate

From `docs/data_flow.md`. Hard rules.
1. Transactions are immutable except through the audited PATCH/DELETE flow. (RESOLVED 5.10 #4/TD16.)
2. `recompute_holding(isin)` is the only authoritative writer to holdings. Idempotent. FIFO from scratch. Serialized per-ISIN via recompute_locks (TD20/#8).
3. `validate_replay(transactions)` rejects any timeline producing negative quantity. (RESOLVED 5.10 #5/TD17.)
4. `holdings.deleted_at = None` filter is universal. (#27 F3 held-overlay reads `holdings.find_one({"isin": isin, "deleted_at": None})`. #28 risk-summary + by-tag both filter `{"deleted_at": None, ...}`.)
5. Cost basis is IT-Act-correct, not broker-nominal.
6. prices_intraday writes are append-only within a day. (5.11 #9/TD23; 5.12 TD26 TTL; Chat A #35.)
7. Symbol search (GET /transactions/search) is case-sensitive by construction; NO $options:i (5.13 TD32). (Distinct from GET /instruments/search/{symbol_prefix}, which uppercases its prefix and matches `^PREFIX` — case-sensitive by the same convention; the route just had to be declared before /{exchange}/{symbol}, Chat 6. GET /portfolio/by-tag matches `tags` exact + case-sensitive, same family, Chat 7.)
8. ICICI portfolio display shows TMPV ~₹813 and TMCV ~₹253 — cosmetically wrong vs our tax-correct numbers; does not affect actual money or tax filing.
9. preview_sell correctly folds SPLIT/BONUS adjustments into the lot walk (5.6).

## Section 12: Phase 2 INVARIANTS

* suggestion_runs are append-only.
* The persisted run `_id` is carried on the in-memory SuggestionRun (5.16/TD35): callers read `run.id`. Do NOT re-derive with `find_one(..., sort=[("run_date",-1)])`.
* tavily_quota: one doc per UTC day, $inc counters. Hard ceiling on calls_today (credits tracked, not capped). 5.14 (#19/TD33) enforced ATOMICALLY. (#27 on-demand news fetch shares this guard; TavilyQuotaExceeded degrades chat to cached news.)
* Confidence score is deterministic, NOT LLM-generated.
* The dossier prompt requires narrative-only output. Forbids "buy"/"sell" imperatives and inventing facts. **The #27 chat system prompt carries the SAME constraint** (narrative only, never say buy/sell, don't invent numbers; "limited data" honesty when context is thin) — for a not-yet-owned stock it takes a buy-research framing but still never issues a buy/sell imperative.
* gate_meta/group_meta/signal_meta/confidence_meta/feedback_meta/page_intro/user_action are PRESENTATION metadata via `_serialize_run`. Never in the persistent model.
* Snapshot eligibility for snapshot_open_outcomes is `tracking_status != "expired"`. snapshot_open_outcomes returns its count under `active_outcomes` (#47).
* `get_excluded_isins()` returns three buckets: rejected (90d), passed (this run only), acted (30d). NOT env-configurable.
* F10 write-before-apply: every POST /suggestions/{isin}/feedback writes monitored_stocks_audit BEFORE update_one.
* A1: monitored_stocks writes go through `MonitoredStockFeedbackPatch(...).model_dump(exclude_none=True)`. SuggestionFeedback uses `extra="forbid"` (#26 added a `direction` field with a "buy" default).
* The `notes` field on a SuggestionRun is a JSON string `{dossiers: [...]}`. (#27 chat F1 parses it the same way the router does, defensively.)
* 5.6 round-trip: every Phase-2 Pydantic model loads cleanly from any historical persisted doc.
* 5.13 (#17/TD31): ISIN Path() params carry `pattern=r"^[A-Z0-9]{12}$"`. (#27 reuses the same pattern on POST /chat/holdings/{isin} and GET /chat/history?isin=.)

**Portfolio read-aggregation INVARIANTS (Chat 7 / #28):**
* `compute_summary` and `compute_risk_summary` share ONE annotation path — `_annotate_holdings(holdings, latest_prices) -> (annotated, accum)`. Do NOT build a parallel aggregation for risk; evolve the helper. The extraction is behaviour-preserving and is gated by a `/portfolio/summary` curl-diff (minus the volatile `as_of`) that must print `OK: /summary unchanged`.
* The risk-summary concentration figures are by construction identical to `/portfolio/summary`'s (same helper) — the cross-check `risk.concentration_by_holding[0] == summary.concentration[0]` must hold.
* Risk thresholds are module constants in `portfolio_service.py` (SINGLE_HOLDING WARN 10 / HIGH 20, SECTOR WARN 30 / HIGH 50), NOT env-configurable — the TOP_MOVERS_LIMIT / CONCENTRATION_LIMIT "operational constant in code" convention.
* Holdings with no price are excluded from the % denominator (same as compute_summary) and surface in the low-severity `stale_price` alert so the understatement is visible.
* `GET /portfolio/by-tag` reuses the `holdings.list_holdings` annotate path (bulk_get_latest_prices + bulk_get_previous_closes + annotate_with_current_price) verbatim so by-tag rows are byte-shape-identical to `GET /portfolio/holdings` and render in the existing HoldingsTable. Tag match is exact + case-sensitive Mongo array-membership on `holdings.tags`. Missing/empty tag → 422; unknown tag → empty + zeroed totals (200). The router imports `portfolio_service._to_dec` for the totals math rather than defining a parallel converter.

**Chat (F1 + F3) INVARIANTS (Chat 6 / #27):**
* Chat is READ-ONLY on the user's portfolio (holdings/transactions) and on suggestion runs. It only WRITES the `conversations` collection. On-demand enrichment may REFRESH shared Phase-2 reference collections (instruments_fundamentals, earnings_calendar, news_articles) via the SAME service functions the weekly cron uses — this is not a Phase-1 write and does not violate "Phase 2 is read-only on Phase 1."
* The chat LLM call is a SINGLE Sonnet call (ANTHROPIC_MODEL_PRIMARY) returning a structured `{answer, intent}` JSON envelope, mirroring `dossier_service._generate_one` (lazy import, system + messages, collect block.text over message.content, parse + one retry + graceful fallback). intent is validated against the 9-value QueryIntent set (invalid -> "other"). No second Haiku classify call is added.
* `scope` discriminates the surface (suggestions|holding), kept distinct from `intent` (which classifies the question). Persist via BaseDoc.to_mongo(); `cost_usd` is `Money` (Decimal -> Decimal128) computed from module-level Sonnet price constants ($3 in / $15 out per MTok).
* `_persist_conversation` inserts then RE-READS the doc so the router serializes POST responses and GET /chat/history rows through one dict path.
* The per-stock endpoint resolves ANY known NSE instrument via `instrument_service.lookup_by_isin`; an unknown ISIN returns None -> the router returns 404 (no yfinance rescue — yfinance is symbol-keyed and the instruments master holds the full NSE list). Held -> full position/tax overlay; not held -> buy-research framing (fundamentals + classified news, position block omitted).
* `follow_up_conversation_ids` on the model is intentionally UNUSED (each turn is independent); threading is a clean future add.

**F2 / F14 invariants (Chat 4):**
* SuggestionDirection literal = "buy" | "sell". Defaults "buy".
* `compute_system_performance(direction="sell")` SIGN-FLIPS excess_return at aggregation. snapshot_open_outcomes is DIRECTION-AGNOSTIC.
* earnings_calendar refresh deletes future events then re-inserts.
* F14 earnings-proximity gate SHARED buy+sell, 5-day threshold.
* Sell-side uses different groups and gates. CandidateScore has FIXED buy-side group fields; sell-side scores flow through group_meta (TD7/#45 deferred). (This coupling is why #27 reimplements the position/tax block instead of calling `_build_position_context_block`.)
* F2 combined-digest: --direction=both emits ONE email + ONE ntfy; run_id keys on buy_run.id.

**Chat 5 A2 (CLOSED):** notify.email() returns `{ok, id, error}` and SWALLOWS Resend exceptions. #20/TD34 (5.15): retries ONCE on transient 429/5xx with 30s backoff; contract unchanged. push_public RAISES on failure — #24, #25, #35 guard it.

**Chat 5.16 TD35 (CLOSED):** digest_delivery + run_weekly_suggestions read the persisted _id off `run.id`. send_combined_digest signature UNCHANGED.

**Other CLOSED Phase-2 facts:** A3+A4 SignalScore.raw_value; 5.5 TD11 explainability fallback; commit 8 dual transport.

## Section 13: Shipped vs Open

**Phase 1 (all shipped, locked):** Holdings dashboard · FIFO cost basis · ICICI import→staging→reconcile→promote · Manual entry · Transaction edit/delete w/ audit (5.10 #4) · Transaction search (5.13 #18) · Preview-sell (5.6) · Reconciliation snapshots (Chat A #25) · Cost basis adjustments · EOD+intraday price refresh (5.11 #9; 5.12 #12; Chat A #35) · Tax vs broker view · Single-holding drill-down (5.13 #14; Chat 6 #27 embeds the F3 chat) · Audit log page · Dark mode · Reconciliation badge · Recent activity card · Global refresh button (5.13 #14) · `/health` honest Mongo readiness probe (Chat A #34) · `/instruments/search` reachable over HTTP (Chat 6 #27 route-shadow fix) · `/portfolio/risk-summary` concentration & risk alerts (Chat 7 #28) · `/portfolio/by-tag` tag views + dashboard risk card + `/tags` page (Chat 7 #28).

**Phase 2 Suggestions Engine:** Unit 1-3 · Commit A · A.5 / A.5.1 (Chat A #26 direction-aware relabel) · Commit B · Feedback/audit endpoints (5.13 #17) · Tavily quota (5.14 #19) · Weekly digest (5.16 #21) · Outcome-tracking cron (Chat A #47).

**Phase 8 New features:** **Chat 6 #27 ad-hoc chat (F1 + F3) SHIPPED** — `conversations` model + scope + index + `lookup_by_isin` (Unit 1), `ensure_stock_context` on-demand enrichment (Unit 2), chat service + `/chat/suggestions` + `/chat/holdings/{isin}` + `/chat/history` (Unit 3), `ChatPanel` + `StockResearchPanel` + `lib/api.ts` + page embeds (Unit 4), plus the `/instruments/search` route-shadow fix. **Chat 7 #28 risk-summary + tag views (F12 + F15) SHIPPED** — `_annotate_holdings` extraction (behaviour-preserving) + `compute_risk_summary` + `GET /portfolio/risk-summary` (Unit 1), `GET /portfolio/by-tag` reusing the list_holdings annotate path (Unit 2), `RiskSummaryCard` + api bindings + Tags nav (Unit 3), dedicated `/tags` page (Unit 4). Both read-only; no new collections/indexes/deps. **Only #29 (Chat 8 / F13 watchlist) remains OPEN in Phase 8.**

**Cross-cutting:** Transactional email via notify.email() (Chat 5 A2; 5.15 #20) · Cron observability (Chat 2; 5.18 #23; 5.19 #24; Chat A #49) · Stateful feedback (Chat 3) · Sell-side (Chat 4) · Model-layer NaN guard (5.17 #22).

**Per-chat ledger (compacted):**

| Chat | Date | Shipped | Code SHA / note |
|---|---|---|---|
| 2 | 2026-05-16 | F4 + F5a cron observability | — |
| 3 | 2026-05-17 | F6 + F5b + F10 stateful feedback | — |
| 4 | 2026-05-17/18/20 | F2b + F14 + F2 backend + F2 frontend (sell-side) | — |
| 5 | 2026-05-24 | Audit + cleanup (A1–A19, TD8) | c6b1437b / 4f31b49 |
| 5.5 | 2026-05-24 | TD9 + TD11 + TD12 | — |
| 5.6 | — | Pydantic round-trip + ge=0 + SPLIT/BONUS preview + TD13 | c6b1437b / 4f31b49 |
| 5.7 | — | Project_State full-file refresh, file-map repairs, URL-at-SHA rule | — |
| 5.8 | — | Code review (28 findings); master_todo.md created. **Doc commit 8f74b50 truncated 655 lines — recovered 5.9** | — |
| 5.9 | 2026-06-02 | #1/TD14, #2/TD10, #3/TD15, DOC RECOVERY, filed TD21/#46 + TD22/#47 | c097b473 |
| 5.10 | 2026-06-06 | #4/TD16, #6/TD18, #5/TD17, #7/TD19, #8/TD20 | b34721e |
| 5.11 | 2026-06-08 | #9/TD23 + #10/TD24 + #11/TD25 | a2806cd |
| 5.12 | 2026-06-08 | #12/TD26 + #13/TD27 + crontab line | 49bf33f |
| 5.13 | 2026-06-08 | #14/TD28 (frontend) + #15/TD29 + #16/TD30 + #17/TD31 + #18/TD32 | backend 090d96c / frontend f59958 |
| 5.14 | 2026-06-09 | #19/TD33 atomic Tavily quota | 4ac2c95 |
| 5.15 | 2026-06-12 | #20/TD34 notify.email() transient retry | 7d77b9c |
| 5.16 | 2026-06-12 | #21/TD35 explicit inserted_id flow; filed #48/TD36 | f4168b3 |
| 5.17 | 2026-06-12 | #22/TD37 reject NaN in _to_decimal | 1d627d7 |
| 5.18 | 2026-06-12 | #23/TD38 fallback heartbeat log + dual-source health check | 0515fef |
| 5.19 | 2026-06-14 | #24/TD39 cron_health_check self-failure dual-transport alert; filed #49/TD40 | 7fcda9e |
| A | 2026-06-14 | Ops & alerting quick-wins bundle (7 items): #34+#35 `bd52c6b`; #25 `1340396`; #49+#26 `6032b64`; #47 `4b638e6`; #48 `fae6edf`. Phase 7 COMPLETE. | code/doc HEAD fae6edf / frontend f59958 |
| 6 | 2026-06-14 | #27 F1+F3 ad-hoc chat (Phase 8). Unit 1 data layer (open base `4403bb5`) → Unit 2 enrichment `c407985` → Unit 3 chat service + endpoints (`15ea9c0`→`dd82636`) → `/instruments/search` route-shadow fix `5e787c9`. Frontend Unit 4 `6093f63`. Filed #50 (news entity mis-tagging) + #51 (dividend_yield ×100 formatting). | backend `5e787c9` / frontend `6093f63` |
| 7 | 2026-06-15 | #28 F12 risk-summary + F15 by-tag (Phase 8). Backend Unit 1 `97041621` (_annotate_holdings extraction + compute_risk_summary + GET /portfolio/risk-summary) → Unit 2 `803e6610` (GET /portfolio/by-tag). Frontend Unit 3 (RiskSummaryCard + api bindings + Tags nav) → Unit 4 (/tags page) `e14d6a75`. Read-only; no new collections/indexes/deps; no new TD/follow-ups. | backend `803e6610` / frontend `e14d6a75` |

The Chat 5.10 SellSheet recorded_with_warning follow-up remains OPEN and untouched through Chat 7.

**Chat split plan — SOURCE OF TRUTH is `docs/master_todo.md`.** Snapshot:

| Phase | Items | Focus | Status |
|---|---|---|---|
| 1 | #1-3 | Ops unblock + doc reconciliation | SHIPPED (5.9) |
| 2 | #4-8 | Transactions/holdings/audit invariants | SHIPPED (5.10) |
| 3 | #9-11 | Intraday & price correctness | SHIPPED (5.11) |
| 4 | #12-13 | Storage hygiene | SHIPPED (5.12) |
| 5 | #14-18 | Frontend correctness + quick wins | SHIPPED (5.13) |
| 6 | #19-24 | External-service hardening | COMPLETE (5.14–5.19) |
| 7 | #25-26 | Reconciliation alerting + feedback direction | COMPLETE — Chat A |
| 8 | #27-29 | Chat 6 (F1+F3), Chat 7 (F12+F15), Chat 8 (F13 watchlist) | #27 SHIPPED Chat 6; #28 SHIPPED Chat 7; #29 NEXT |
| 9 | #30-38 | Cross-cutting cleanup before GO LIVE | PARTIAL — #34 + #35 SHIPPED (Chat A); #30-33, #36-38 OPEN |
| 10 | #39-41 | Chat 9 pre-launch cleanup | OPEN |
| 11 | #42 | Chat 10 GO LIVE (F7 real data import) | OPEN |
| 12 | #43-45 | Deferred TDs (TD1, TD3, TD7) | DEFERRED |
| — | #46-51 | TD21 scheduler (OPEN), TD22 (SHIPPED A), TD36 (SHIPPED A), TD40 (SHIPPED A), #50 news entity mis-tagging (OPEN, Chat 6), #51 dividend_yield ×100 (OPEN, Chat 6) | #46/#50/#51 OPEN; #47/#48/#49 SHIPPED |

**Chat-bundle overlay (added 5.19, source of truth = master_todo.md "Chat bundles").** Remaining OPEN rows are grouped (NOT renumbered) into chats: **Chat A** (#25, #26, #34, #35, #47, #48, #49 — COMPLETE), **Chat 6** (#27 — COMPLETE), **Chat 7** (#28 — COMPLETE), **Chat B** (#30, #31, #32, #33, #36, #37, #38), **Chat C** (#40, #41), **Chat D** (#43, #44, #45), and standalone large items kept one-per-chat: #29 (Chat 8 — NEXT), #39 (Chat 9), #42 (Chat 10 GO LIVE), #46 (scheduler). Bundles never override a per-row gating dependency.

**Open items carried past Chat 7** (tracked in master_todo.md; pointer now at #29):
* **#29 (Chat 8 / F13, NEXT):** watchlist (extends the engine universe; must come last among the Phase-8 features because it multiplies data volume).
* **#30–#33, #36–#38 (Phase 9 / Chat B):** datetime sweeps, Python ceiling, pytest harness, admin recompute endpoint, restore rehearsal, JSON logging.
* **#39 (Chat 9 / F11), #40 + #41 (Chat C):** capital-gains pack; realized-P&L UI hide + stop_loss wiring.
* **#42 (Chat 10 / F7):** GO LIVE real ICICI import.
* **#43–#45 (Chat D, DEFERRED):** TD1/TD3/TD7.
* **#46 (TD21):** registry-generated crontab migration; dedicated chat.
* **#50 (Chat 6):** news entity mis-tagging in `news_articles.entities_isins` (upstream of chat; degrades news_score + dossier + chat).
* **#51 (Chat 6):** `dividend_yield` ×100 formatting shared by `dossier_service._fmt_pct` + the chat formatter (pre-existing yfinance unit inconsistency).

## Section 14: Conventions the assistant has repeatedly drifted on

Memorize these.
* Port 8001 (Mac local), 8000 (EC2). Always specify which.
* SSH-first for tests: every test block begins `ssh ubuntu@100.112.20.41` and curls `localhost:8000`. (Frontend-only: `~/deploy-ui.sh` + `npm run build`/lint on EC2.)
* Commit-block-after-code: every code/file delivery followed by paste-ready `git add .` + `git commit -m`.
* Project_State.md AND master_todo.md are ALWAYS complete full-file replacements.
* F6 two-mechanism feedback exclusion: both `get_excluded_isins` (run-build) AND `_build_user_action` (serialization) required.
* 90-day rejected cooldown and 30-day acted soft-exclude are NOT env-configurable.
* F10 write-before-apply: `log_change(...)` BEFORE `update_one(...)`.
* Secrets path on EC2: `/etc/portfolio-advisor/secrets.env`.
* `lib/api.ts` hand-typed; `lib/api-types.ts` gitignored.
* Mutations use `refetchQueries` (synchronous), NOT `invalidateQueries`. (Chat 6 `ChatPanel` + Chat 7 `/tags` page + dashboard risk query follow this.)
* `cn` at `@/lib/utils`. Format helpers at `@/lib/format`.
* Collections accessor: `from app.db.client import Collections`.
* Decimal128 vs Decimal: helpers in `app/models/_common.py`. BaseDoc.to_mongo() = model_dump(by_alias=True, exclude_none=True) + Decimal→Decimal128; extra="forbid" (so a new field like #27's `scope` MUST be declared on the model to be storable).
* Datetimes: UTC-naive in Mongo, IST in UI. `utcnow()` from `app/models/_common.py`. (#27 uses utcnow() for the freshness-gate cutoffs.)
* Heredoc for multi-line Python: `<<'EOF'` form.
* Original SuggestionCard takes parent-owned mutation. /suggestions page uses shadcn Tabs.
* Every cron script: `cron_run()` + CronSpec + crontab line. AND CronSpec.cron_name == the name passed to `cron_run()` (5.9 TD14).
* Direction-aware display layer: branch at the display layer, not by forking the model.
* Symbol search regex is case-sensitive on purpose; NO $options:i (5.13 TD32).
* ISIN Path() params validate charset with `pattern=r"^[A-Z0-9]{12}$"` plus min/max_length. (5.13 TD31; reused on /chat/holdings/{isin} + /chat/history, Chat 6.)
* Tavily daily quota enforced ATOMICALLY (5.14 TD33). DAILY (resets 00:00 UTC), not monthly (Chat A TD36).
* notify.email() retries a TRANSIENT Resend failure (429+5xx) ONCE with 30s backoff; contract unchanged. push_public RAISES on failure — guard it (#24, #25, #35). (5.15 TD34.)
* The persisted SuggestionRun._id is carried on `run.id`; read run.id, don't re-derive. (5.16 TD35.)
* `_to_decimal` rejects a NaN float with `ValueError("NaN not allowed")` in the float branch (422 via Money validator); float ingress only. (5.17 TD37.)
* Cron heartbeats are best-effort WITH a disk fallback (5.18 TD38); do NOT make `_append_fallback` raise, do NOT drop the Mongo path.
* `cron_health_check.main`'s per-cron Mongo-read loop is wrapped to fire a dual-transport self-failure alert and RE-RAISE (5.19 TD39); do NOT widen the wrap, do NOT leave the self-failure push_public unguarded, do NOT return 0.
* (Chat A) `/health` reflects Mongo reachability in the STATUS CODE (503 degraded / 200 ok); do NOT probe yfinance on the hot path. (#34.)
* (Chat A) `take_auto_snapshot` alerts ntfy ONLY, on INVESTED drift vs the last manual snapshot, rising-edge deduped; evolve the existing alerting, no parallel alerter. (#25.)
* (Chat A) An "add `payload.X`" instruction can reference a non-existent payload field — grep the model (`extra="forbid"`). Use the repo's `{$or:[…,{$exists:false}]}` buy guard. (#26.)
* (Chat A) Grep the PRODUCER's return dict for exact key names before documenting/patching a cron consumer (`active_outcomes` not `open_outcomes`). (#47/TD22.)
* (Chat A) An idle/placeholder CronSpec must carry `expected_weekdays=set()` unless a real crontab line logs a heartbeat under its `cron_name`. (#49/TD40.)
* (Chat A) Before "fixing monthly→daily" wording, read the code for the ACTUAL boundary + env-var name. (#48/TD36.)
* **(Chat 6) FastAPI matches routes in REGISTRATION ORDER — a STATIC route (`/search/{prefix}`) MUST be declared BEFORE a sibling DYNAMIC route (`/{exchange}/{symbol}`), or the dynamic one greedily captures the static path and 404s it. Latent until something calls it over HTTP (scripts use the service layer; the chat research panel was the first HTTP caller of `/instruments/search`). (#27.)**
* **(Chat 6) The ad-hoc chat LLM call is a SINGLE Sonnet call returning a `{answer, intent}` JSON envelope, mirroring `dossier_service._generate_one` verbatim (lazy import, system + messages, collect block.text, parse + one retry + graceful fallback). Do NOT add a second Haiku intent-classify call — Sonnet self-labels `intent` from the fixed 9-value set (invalid -> "other"), exactly as the dossier prompt constrains its verdict label. The chat answer carries the dossier's hard constraint: narrative only, never say buy/sell, don't invent numbers, say "limited data" when context is thin. (#27.)**
* **(Chat 6) The chat is READ-ONLY on portfolio + suggestion data and writes only `conversations`; on-demand enrichment (`ensure_stock_context`) may REFRESH shared Phase-2 reference collections (fundamentals/earnings/news) via the SAME cron-path service functions — that is not a Phase-1 write and does not break "Phase 2 is read-only on Phase 1." Freshness-gate every external call so a warm turn is call-free; degrade gracefully (TavilyQuotaExceeded + failures -> cached). (#27.)**
* **(Chat 6) The per-stock chat endpoint resolves ANY known NSE instrument via `instrument_service.lookup_by_isin`; an unknown ISIN -> 404 (NO yfinance rescue — yfinance is symbol-keyed, the instruments master holds the full NSE list). Held -> position/tax overlay; not held -> buy-research framing. The `_build_position_context_block` helper is CandidateScore-coupled, so the chat REIMPLEMENTS the LTCG>365d / near-LTCG / weight math rather than calling it — flag this as the deliberate evolve-not-call line. (#27.)**
* **(Chat 6) The frontend has NO markdown dependency and the house pattern renders LLM text as plain strings — so a markdown LLM answer is rendered by a self-contained `MarkdownLite` inside the chat feature, keeping deploy a plain `npm run build` (no `npm install`/lockfile churn on the t3.micro). Do NOT add `react-markdown` without an explicit decision. (#27.)**
* **(Chat 7) A new read-aggregation endpoint EVOLVES `compute_summary` — extract the shared annotation into `_annotate_holdings(holdings, latest_prices) -> (annotated, accum)` and have BOTH `compute_summary` and `compute_risk_summary` call it; do NOT build a parallel risk aggregation. Prove the extraction is behaviour-preserving with a `/portfolio/summary` curl-diff (minus `as_of`) that prints `OK: /summary unchanged` BEFORE trusting the refactor. (#28 / F12.)**
* **(Chat 7) Risk/alert thresholds are MODULE CONSTANTS in `portfolio_service.py` (the TOP_MOVERS_LIMIT / CONCENTRATION_LIMIT "operational constant in code" pattern), NOT env/settings. Two-tier severity (warn/high). Holdings with no price are excluded from the % denominator and surfaced in a low-severity `stale_price` note so the understatement is visible. (#28 / F12.)**
* **(Chat 7) `GET /portfolio/by-tag` REUSES the `holdings.list_holdings` annotate path (bulk_get_latest_prices + bulk_get_previous_closes + annotate_with_current_price) so by-tag rows are byte-shape-identical to `GET /portfolio/holdings` and render in the existing HoldingsTable. Tag match is exact + case-sensitive Mongo array-membership on `holdings.tags`; required `Query(min_length=1)` -> 422; unknown tag -> empty + zeroed 200. Import `portfolio_service._to_dec` for the totals — no parallel converter. (#28 / F15.)**
* **(Chat 7) A new dashboard data surface gets its OWN independent `useQuery` (e.g. `["dashboard","risk"]`) so its failure doesn't block the main dashboard; new response shapes get NEW `lib/api.ts` types when the existing ones (ConcentrationItem/SectorBucket) don't match — do NOT force-fit. The `/tags` page REUSES `<HoldingsTable>` wholesale and derives its tag universe from `holdings.tags`. No new shadcn primitive, no new npm dependency. (#28.)**

**Chat 4 additions:** Don't trust Glean snippets/memory for field names — grep first. `cron_run()` yields `_Heartbeat`; `.meta` is an ATTRIBUTE. /cron/heartbeats returns `{heartbeats, health_summary}`. Accessor `Collections.instruments_fundamentals()`. `run_suggestions()` SLOW by default.

**Chat 5 additions:** ASK FOR THE CURRENT SHA BEFORE PROPOSING ANY CODE CHANGE. When a wrapper's return shape/exception behavior changes, grep ALL callers. notify.email() returns {ok,id,error}. GitHub raw-URL caching is real — use SSH+sed as ground truth.

**Chat 5 closure:** Doc rewrites cross-check every cron/registry/file claim against on-disk state. Project_State.md structure is load-bearing — NEVER restructure. Cron-health needs redundant transports. logrotate since 2026-05-24.

**Chat 5.5:** Read the script body at HEAD before documenting it; verify argparse before documenting a cron line. Settings+secrets changes ship in ONE atomic commit. Prefer raw.githubusercontent.com URLs.

**Chat 5.7:** Never change code from memory — construct GitHub URLs from owner/repo/SHA/path. Tree-listing first. Diff file maps line-by-line.

**Chat 5.8:** master_todo.md is canonical. Read it after Project_State.md, confirm the pointer. Ship code + master_todo status in the same commit. Append new items, don't renumber.

**Chat 5.9:** A doc-update commit must NEVER shorten Project_State.md without a stated reason — verify the sentinel + line count. In-code F-numbers span TWO colliding namespaces. An "ops-only" item can hide a code bug. Grep at HEAD.

**Chat 5.10:** Transactions PATCH/DELETE is audit-then-apply. validate_replay takes the FULL timeline. Every holdings handler is sync def — use a Mongo advisory-lock doc, not asyncio.Lock. recompute_holding returning None is a full-exit success. Heredoc-to-file for long Python over SSH.

**Chat 5.11:** India has no DST — IST fixed UTC+5:30. The module's tz convention is "naive→UTC first". Don't revert bulk_get_previous_closes. Green endpoints don't prove a change landed — assert the new symbol + confirm SHA.

**Chat 5.12:** TTL no-ops on a non-Date field. ASC TTL + DESC non-TTL coexist. App DB is `portfolio`. news bulky field is `body_text`. Purge keys on `fetched_at`.

**Chat 5.13:** A "~line N" pointer is a hint — re-anchor at HEAD. `grep -F` for literal strings. A pass/fail test must DISCRIMINATE the change. Both-repos phase needs per-repo deploy.

**Chat 5.14:** Atomic compare-and-increment = guard in the filter + unique index catches the over-cap upsert. Verify the unique index at HEAD. check-then-act is a TOCTOU race even on threadpool sync Uvicorn. Anchor to code, not docs.

**Chat 5.15:** A retry inside a {ok,id,error} swallow wrapper must keep returning the dict. Classify transient off the SDK HTTP status. Only 429+5xx retry. Verify with a monkeypatched harness.

**Chat 5.16:** Re-anchor on actual control flow. Carry state on an existing model field over adding a param. `find_one(sort date desc)` to recover a just-inserted id is a latent bug. Delete the import when you delete its last use.

**Chat 5.17:** A validator rejects bad input via ValueError (422), not TypeError (500). NaN is `v != v`. A float-ingress guard doesn't touch Mongo reads. The cached master_todo blob lagged HEAD — confirm the pointer against the SHA-pinned file.

**Chat 5.18:** Distinguish heartbeat PERSISTENCE failure (#23) from a cron's OWN body failing (TD22). A `1 failure(s)` line proves the machinery worked. A best-effort sink swallows all its own errors. Normalize the ISO fallback timestamp to naive-UTC.

**Chat 5.19:** Wrap ONLY the per-cron Mongo-read loop. Dual-transport the self-failure alert, GUARD the ntfy leg, RE-RAISE. Preserve the #23 merge loop inside. Stubbed `[stub]` lines ARE the stubs firing.

**Chat A:** A bundle is a chat-grouping — ship in units, ask for the SHA before EACH unit, re-read each touched file. Re-confirm the pointer against the SHA-pinned master_todo (the Glean blob was stale). An "add payload.X" can reference a non-existent field. A "monthly→daily" fix can hide further doc bugs. A cron failing daily with an empty log is its own body throwing (#47). Guard push_public (#25, #35). #49 touched the SAME file #23/TD38 hardened — leave its paths untouched.

**Chat 6:** FastAPI matches routes in registration order — declare a static route before a sibling dynamic one, or the dynamic one captures it (latent until the first HTTP caller; #27's research panel was it for `/instruments/search`). The ad-hoc chat is ONE Sonnet `{answer,intent}` call mirroring `dossier_service._generate_one` — no second Haiku call; carry the dossier's narrative-only / never-buy-sell / don't-invent-numbers constraint into the chat prompt. Chat writes only `conversations`; on-demand enrichment refreshes shared Phase-2 reference collections via the SAME cron-path services (not a Phase-1 write) and freshness-gates every external call. The per-stock endpoint generalizes to any known NSE instrument (held -> position/tax overlay; not held -> buy-research framing); unknown ISIN -> 404, no yfinance rescue. `_build_position_context_block` is CandidateScore-coupled, so reimplement the LTCG/weight math rather than call it. No markdown dependency in the frontend — use a self-contained `MarkdownLite`, keep deploy a plain build. Verify a request-driven feature E2E with live curls (F1/F3 held/F3 not-held/404/422/history) + a regression curl for the route fix. Two pre-existing data issues surfaced (filed #50 news entity mis-tagging, #51 dividend_yield ×100) — don't silently fix outside scope; the chat formatter must stay byte-consistent with `dossier_service._fmt_pct`.

**Chat 7:** A new read-aggregation endpoint EVOLVES `compute_summary` via a shared `_annotate_holdings` helper — never a parallel aggregation; gate the behaviour-preserving extraction with a `/portfolio/summary` curl-diff that prints `OK: /summary unchanged`. Risk thresholds are module constants (the TOP_MOVERS_LIMIT pattern), two-tier (warn/high); unpriced holdings drop out of the % denominator and surface in a low-severity `stale_price` note. `GET /portfolio/by-tag` reuses the `list_holdings` annotate path so rows are shape-identical to `/portfolio/holdings` and render in the existing HoldingsTable; tag match exact + case-sensitive array-membership on `holdings.tags`; required tag -> 422, unknown tag -> empty + zeroed 200; import `_to_dec`, no parallel converter. A new dashboard surface gets its own independent `useQuery` so its failure doesn't block the dashboard; add NEW api.ts types when existing ones don't match (don't force-fit ConcentrationItem/SectorBucket); the `/tags` page reuses `<HoldingsTable>` wholesale; no new shadcn primitive or npm dependency. A design proposal was approved before any code on a large feature, per the user's standing expectation. No new TD filed.

## Section 15: Anti-patterns the assistant has fallen into

(Deduped — Section 14 carries the corresponding positive convention.)
* Full-file rewrites instead of additive patches. EXCEPTION: Project_State.md and master_todo.md are always full-file.
* Inventing parallel patterns. Trusting memory for function names / response shapes / paths — RE-READ AT HEAD. Truncating code with "rest unchanged". Asking "is this OK?" without applying the edit. Micro-commits. Assuming GitHub content is current. Producing files significantly larger than originals. Inventing fields in API responses. Forgetting `enrich_run`. Forgetting `holdings.deleted_at = None`. Cron entries without log paths / heartbeat monitoring. Designing unrequested UI/UX. Shipping code without the commit block. Shipping a test block without `ssh ubuntu@100.112.20.41`. Using artifact_edit on the two docs instead of full-file. Confusing the two F6 mechanisms.
* (Chat 4) Guessing model field names without grep; multi-chunk plans without re-reading every touched file at HEAD.
* (Chat 5) Trusting Project_State.md for "what's open" without verifying code; find-and-replace from snippet memory; changing a wrapper's shape without checking ALL callers.
* (Chat 5 closure) Restructuring Project_State.md when told preserve structure; inventing/removing cron entries; describing a script without reading its main(); skipping Section 0.
* (5.5) Script rename from a summary; cron-line flags without --help; nested triple-backticks.
* (5.7) Trusting the file map as ground truth; listing files that don't exist.
* (5.8) Treating Project_State.md as a TODO list; starting a chat without confirming the pointer; shipping code without master_todo status in the same commit.
* (5.9) Letting the doc commit truncate the file; mapping F-refs from memory; treating an "ops-only" item as code-free.
* (5.10) Piping curl -w HTTP code into jq; asserting on guessed field names; same-timestamp BUY+SELL in a replay test; pasting a long heredoc into SSH.
* (5.11) Trusting green endpoints as proof of deploy; reverting bulk_get_previous_closes.
* (5.12) TTL on a non-Date field; mongosh against the wrong DB; $unset a guessed field name.
* (5.13) Trusting a "~line N" pointer; verification grep with metacharacters; both-repos done on one repo.
* (5.14) Replacing a check-then-act race with a lock when a conditional find_one_and_update + unique index suffices; trusting README over code.
* (5.15) Turning a swallowed-error wrapper into a raised path; classifying off message string; retrying every exception; verifying with a live send.
* (5.16) Taking the scope framing at face value; re-querying "the latest row" for a just-inserted id; adding a param when a model field carries it; leaving an orphaned import.
* (5.17) Raising TypeError (500) where ValueError (422) is needed; broadening a scoped guard; trusting a cached blob over the SHA-pinned file.
* (5.18) Conflating persistence failure (#23) with a cron body failure (TD22); a best-effort sink that raises; comparing ISO to naive-UTC without normalizing; verifying without a forced-failure tripwire.
* (5.19) Returning 0 after Mongo reads fail; leaving the self-failure ntfy unguarded; wrapping more than the read loop; mistaking stubbed lines for missing notifications.
* (Chat A) Adding `payload.direction` without grepping the payload model; a bare `{direction:"buy"}` that misses pre-F2 docs; a richer `/health` JSON but unchanged status code; probing yfinance on the hot path; an UNGUARDED push_public alert; "fixing" only the literal word; disturbing the TD38 heartbeat paths; declaring #47 fixed without reproducing it; treating the Glean blob as the pointer source.
* (Chat 6) Declaring a route "wired" without testing it over HTTP (the `/instruments/search` shadow was invisible to service-layer callers); adding a second Haiku classify call when one Sonnet `{answer,intent}` call suffices; calling `_build_position_context_block` (CandidateScore-coupled) from the chat path instead of reimplementing the math; adding `react-markdown` (an npm install + lockfile churn) when a self-contained renderer suffices; rebuilding a full-file doc from a terminal-wrapped `git show` paste without un-wrapping mid-word breaks + a `git diff` gate; "silently fixing" the dividend-yield ×100 across the dossier + chat formatters unasked (filed #51 instead); treating the wrong-ISIN news as a chat bug rather than upstream tagging (filed #50).
* (Chat 7) Building a parallel risk aggregation instead of extracting a shared `_annotate_holdings` from `compute_summary`; trusting a behaviour-preserving refactor without the `/summary` curl-diff gate; putting risk thresholds in env/settings instead of module constants; counting unpriced holdings in the % denominator (or hiding the understatement instead of a `stale_price` note); building a parallel annotate path for by-tag instead of reusing `list_holdings`'; defining a parallel `_to_dec` in the router; case-insensitive tag matching; force-fitting ConcentrationItem/SectorBucket when the risk shapes differ; mounting the risk card on the shared dashboard query so its failure blocks the page; adding a markdown/shadcn/npm dependency for a card that needs none.

## Section 16: "I am losing context" — escalation protocol

When any trigger fires, say verbatim: **`I AM LOSING CONTEXT`**

**Triggers (any one suffices):** Cannot recall a file structure discussed earlier · Conflating Phase 1 vs Phase 2 facts · Forgetting which Commit/Chat shipped which behavior · Producing a file >1.5x original line count without explicit reason · Generic patterns instead of project conventions · Forgetting the Mac/EC2 port difference, SSH-first/commit-block conventions, or the secrets path · Forgetting master_todo.md is canonical (5.8) · The user corrects the same drift twice in one chat · >15 Glean reader / code_search calls without converging · The "Truncation Notice" appears · About to produce a third large code artifact unsure whether prior decisions apply.

**Specific triggers:** (4) shipped 2+ patches with WRONG field names · WRONG API response shape. (5) claimed "open" without re-reading code · find-and-replace whose original_text doesn't exist verbatim · changed a wrapper's shape without grep'ing callers · about to restructure Project_State.md. (5.5) script rename from a summary · cron line without --help. (5.7) patch a file not confirmed via tree listing · a GitHub URL with a SHA not supplied this chat. (5.8) ship code without master_todo status in the same commit · start a code chat without confirming the pointer. (5.9) commit a Project_State.md without the sentinel · a Section-18 F-row from a bare comment. (5.10) ship a 3rd patch without re-reading the body · a test block not SSH-first · asyncio.Lock for a sync-def handler. (5.11) declare a change verified on green endpoints without a positive assertion + SHA · DST-aware IST. (5.12) TTL without a BSON Date · CronSpec.cron_name != cron_run() string · mongosh against portfolio_advisor. (5.13) anchor on a "~line N" without grepping · declare a both-repos phase done on one repo. (5.14) atomic update relying on an unconfirmed unique index · change behaviour off README prose. (5.15) make a transient email failure RAISE · retry every exception · verify with a live send. (5.16) recover a just-inserted id via find_one(sort date desc) · change a wrapper signature without grepping callers. (5.17) raise TypeError instead of ValueError from a validator · confirm the pointer from a cached blob. (5.18) tell the user #23 silences a cron-body failure · make `_append_fallback` raise. (5.19) return 0 from cron_health_check.main on a Mongo-read failure · leave the self-failure push_public unguarded. (Chat A) reference `payload.X` without grepping the model · filter outcomes by a bare direction equality · ship a new push_public alert unguarded · change `/health` JSON without the status code · "fix" doc wording without reading the code · touch `cron_heartbeat_service.py` and modify the TD38 paths · declare #47 fixed without reproducing it · start a bundle without re-confirming the pointer. (Chat 6) declare a route working without an HTTP test · add a second Haiku call for chat intent when one Sonnet call self-labels it · call `_build_position_context_block` from the chat path · add a markdown npm dependency without a decision · build a full-file doc from a wrapped `git show` paste without un-wrapping + a `git diff` gate · silently fix #51 (dividend_yield ×100) across both formatters · diverge the chat formatter from `dossier_service._fmt_pct` · treat the wrong-ISIN news (#50) as a chat-layer bug. (Chat 7) build a parallel risk aggregation instead of extracting `_annotate_holdings` · skip the `/summary` curl-diff gate on the refactor · put risk thresholds in env/settings · count unpriced holdings in the % denominator · build a parallel by-tag annotate path instead of reusing `list_holdings`' · define a parallel `_to_dec` · case-insensitive tag matching · force-fit ConcentrationItem/SectorBucket · mount the risk card on the shared dashboard query.

**What "switching chats" means:** the user copies the Section 0 bootstrap into a fresh chat, which reads Project_State.md + master_todo.md + both repos at HEAD + data_flow.md + READMEs, the user states scope, the assistant summarizes back per the Section 0 acknowledgement contract and WAITS for confirmation before doing anything. Work resumes from the master_todo.md pointer.

## Section 17: "Am I hallucinating?" diagnostic questions

* Backend port Mac local → **8001**. EC2 → **8000**. SSH → **`ssh ubuntu@100.112.20.41`**.
* Secrets on EC2 → **`/etc/portfolio-advisor/secrets.env`**. On Mac → **`<repo>/.env`**.
* `recompute_holding(isin)` → only authoritative writer to holdings; idempotent; FIFO; serialized per-ISIN via recompute_locks (TD20).
* Gating filter on snapshot_open_outcomes → `tracking_status != "expired"`; returns its count under `active_outcomes` (#47/TD22).
* Universe filter in build_universe → NIFTY 100 ∪ watchlist (after F13) − held − excluded.
* Two F6 mechanisms & why both → get_excluded_isins (run-build) AND _build_user_action (serialization).
* Acted soft-exclude window / env-configurable → 30 days / No.
* Q/V/M/N weight breakdown → 30/25/25/20, version "1.0.0-unit2".
* refetchQueries or invalidateQueries → refetchQueries (the two outliers swapped 5.13; ChatPanel + the /tags page + the dashboard risk query follow it, Chat 6/7).
* Sell endpoint response shape → full Holding (partial) OR {message, realized_total} (full exit) OR {status:"recorded_with_warning", isin, warning} (TD19).
* How does a cron register → cron_run() + CronSpec + crontab line; CronSpec.cron_name == cron_run() name (5.9 TD14).
* Where do F4 cron failure alerts go → push_public("errors",...) + notify.email(...) (dual-transport, commit 8). Raises only when BOTH fail.
* **Heartbeat schema → `{cron_name, started_at, finished_at, status, error, metadata, _schema_version: 1}`. TTL 60 days.**
* Healthy rule → (not expected today) OR (success+skipped >= min AND failure == 0).
* How is PROJECT_STATE.md delivered → Always full-file canvas artifact, ending with `End of PROJECT_STATE.md.`.
* What does notify.email() do on a transient Resend error → retries ONCE on 429/5xx with 30s backoff, returns {ok,id,error} (never raises). push_public RAISES (guard it — #24, #25, #35).
* What does `_to_decimal` do with a NaN float → raises `ValueError("NaN not allowed")` (5.17 TD37).
* What happens when a cron heartbeat's Mongo insert fails → `_persist` appends to `/home/ubuntu/cron-heartbeat-fallback.log`; cron_health_check merges both (5.18 TD38).
* What does cron_health_check.main do when its OWN Mongo reads fail → dual-transport self-failure alert (guarded ntfy + email) then RE-RAISE (5.19 TD39).
* What does GET /health return → 200 `{"status":"ok","mongo":"ok"}` or 503 `{"status":"degraded","mongo":"fail"}`; yfinance NOT probed (Chat A #34).
* What does take_auto_snapshot do on drift → ntfy ONLY, invested drift vs last manual snapshot, rising-edge deduped (Chat A #25).
* Does submit_feedback's outcome relabel consider direction → Yes (Chat A #26); buy via `{$or:[…,{$exists:false}]}`, sell bare. Does NOT close TD1/#43.
* Is the Tavily quota monthly or daily → DAILY, resets 00:00 UTC, `TAVILY_DAILY_CALL_LIMIT`; no `TAVILY_MONTHLY_QUOTA` (Chat A #48).
* **What are the chat endpoints → POST /chat/suggestions (F1), POST /chat/holdings/{isin} (F3, ISIN-validated, 404 on unknown instrument), GET /chat/history?scope=&isin=&limit= (Chat 6 #27).**
* **What LLM does the chat use, and how many calls → ONE Sonnet (ANTHROPIC_MODEL_PRIMARY) call returning a `{answer, intent}` JSON envelope, mirroring dossier_service._generate_one. No second Haiku call (Chat 6 #27).**
* **Is the chat read-only → Read-only on the portfolio (holdings/transactions) and on suggestion runs; it writes only `conversations`. On-demand enrichment may refresh shared Phase-2 reference collections (fundamentals/earnings/news) via the cron-path services — not a Phase-1 write (Chat 6 #27).**
* **What does the per-stock chat do for a stock you don't own → resolves any known NSE instrument via lookup_by_isin; not-held -> buy-research framing (fundamentals + classified news, no position block); held -> position/tax overlay; unknown ISIN -> 404 (no yfinance rescue) (Chat 6 #27).**
* **Why was /instruments/search 404'ing before Chat 6 → the dynamic /{exchange}/{symbol} route was registered before the static /search/{symbol_prefix}, so FastAPI captured /instruments/search/INFY as exchange=search,symbol=INFY. Reordered search-before-dynamic (#27 route-shadow fix).**
* **How does the frontend render a chat markdown answer → a self-contained MarkdownLite in components/chat-panel.tsx (the project has no markdown dependency); deploy stays a plain npm run build (Chat 6 #27).**
* **What does GET /portfolio/risk-summary return → concentration_by_holding (every priced holding desc by %), concentration_by_sector, and a two-tier alerts array (single_holding warn>10/high>20, sector warn>30/high>50, + a low-severity stale_price note); read-only; reuses the /summary annotation path via _annotate_holdings; thresholds are module constants (Chat 7 #28).**
* **How does risk-summary avoid drifting from /summary → both call the SAME `_annotate_holdings(holdings, latest_prices)` helper extracted from compute_summary; the extraction is behaviour-preserving, gated by a /summary curl-diff; risk.concentration_by_holding[0] == summary.concentration[0] (Chat 7 #28).**
* **What does GET /portfolio/by-tag return → {tag, holdings (same shape as /portfolio/holdings, annotated via the list_holdings path), totals}; tag required (min_length=1) -> 422; exact case-sensitive array-membership on holdings.tags; unknown tag -> empty + zeroed 200 (Chat 7 #28).**
* **Where does the F12 frontend live → a RiskSummaryCard mounted full-width on the dashboard via an independent useQuery(["dashboard","risk"]); F15 lives on a dedicated /tags page that reuses <HoldingsTable>; new RiskSummary/HoldingsByTag types in lib/api.ts (ConcentrationItem/SectorBucket didn't match); no new npm/shadcn dependency (Chat 7 #28).**

**Chat 4 diagnostics:** CronSpec fields → cron_name, description, schedule_human, expected_weekdays, min_runs_per_day (default 1). Set heartbeat metadata → `ctx.meta = {...}` (ATTRIBUTE). /cron/heartbeats shape → {heartbeats, health_summary}. Fundamentals accessor → instruments_fundamentals. F2b digest ntfy topic → NTFY_PUBLIC_TOPIC_DIGESTS. F14 earnings-proximity threshold → 5 days. compute_system_performance(direction='sell') → SIGN-FLIPS.

**Chat 5+ diagnostics:** F2 frontend shipped → Yes (frontend HEAD f59958 → 6093f63 Chat 6 → e14d6a75 Chat 7). target_price consumed → Yes (stop_loss deferred Chat 9 TD6). On-disk filename → Project_State.md. App DB name → portfolio. TD8 → self-hosted ntfy decommissioned. Commit 8 → cron_health_check dual-transport.

## Section 18: Tech debt registry

**Closed audit rows (Chat 5 + earlier — all SHIPPED, kept for posterity):** A1–A19 (see prior versions), TD2, TD4, TD5, TD8. (Descriptions unchanged from the 5.16 compaction.)

**SHIPPED TDs (one line each — full verification prose in git history):**

| TD | master_todo | Description | Shipped |
|---|---|---|---|
| TD9 | — | Orphan NTFY_URL/USER/PASS removed from settings.py + secrets.env (one atomic commit) | 5.5 |
| TD10 | #2 | Redundant `find -size +10M` crontab line verified absent; logrotate confirmed | 5.9 |
| TD11 | — | explainability._build_signal_meta reads sig["raw_value"]; new _format_raw kinds | 5.5 |
| TD12 | — | seed_nifty100.py correctly named — doc-only fix in 4 locations | 5.5 |
| TD13 | — | Frontend per-page reference doc (7 routes) | 5.6 |
| TD14 | #1 | Sunday crontab flags removed + CRON_REGISTRY rename run_weekly_suggestions→weekly_suggestions (c097b473) | 5.9 |
| TD15 | #3 | F-number fix registry authored; recovered truncated Sections 16-tail–22 | 5.9 |
| TD16 | #4 | PATCH/DELETE /transactions/{id} flipped to audit-then-apply (17f9f94) | 5.10 |
| TD17 | #5 | validate_replay on /sell + add_manual_transactions.py SELL (5cf3087) | 5.10 |
| TD18 | #6 | Duplicate list_transactions handler deleted | 5.10 |
| TD19 | #7 | add_buy/sell wrap recompute_holding → recorded_with_warning (fb23307) | 5.10 |
| TD20 | #8 | recompute_holding serialized per-ISIN via recompute_locks + 60s TTL (b34721e) | 5.10 |
| TD23 | #9 | Holiday guard in _intraday_row_from_df (a2806cd) | 5.11 |
| TD24 | #10 | price_stale docstring aligned to code (a2806cd) | 5.11 |
| TD25 | #11 | bulk_get_previous_closes rewritten to per-ISIN find_one (a2806cd) | 5.11 |
| TD26 | #12 | prices_intraday.captured_at 90-day TTL (captured_at_ttl ASC) | 5.12 |
| TD27 | #13 | purge_news_bodies.py daily cron 02:30 IST (49bf33f) | 5.12 |
| TD28 | #14 | invalidateQueries → refetchQueries in notes-panel + refresh-button (f59958) | 5.13 |
| TD29 | #15 | Dead `from pydoc import doc` removed | 5.13 |
| TD30 | #16 | MONGODB_URI doc-drift confirmation (no code) | 5.13 |
| TD31 | #17 | ISIN `pattern=r"^[A-Z0-9]{12}$"` on the two /suggestions/{isin} Path params | 5.13 |
| TD32 | #18 | Dropped `$options:i` on transactions/search regex | 5.13 |
| TD33 | #19 | Atomic Tavily quota claim (4ac2c95) | 5.14 |
| TD34 | #20 | notify.email() transient-5xx/429 retry (7d77b9c) | 5.15 |
| TD35 | #21 | Explicit persisted-run-id flow (f4168b3) | 5.16 |
| TD37 | #22 | Reject NaN in `_to_decimal` (1d627d7) | 5.17 |
| TD38 | #23 | Fallback heartbeat log (0515fef) | 5.18 |
| TD39 | #24 | cron_health_check.main self-failure alert (7fcda9e) — LAST Phase 6 item, Phase 6 COMPLETE | 5.19 |
| — | #34 | GET /health 503 + degraded on Mongo ping failure (bd52c6b) | A |
| — | #35 | refresh_prices_intraday GUARDED ntfy on insert failure + re-raise (bd52c6b) | A |
| — | #25 | take_auto_snapshot ntfy on invested drift, rising-edge deduped (1340396) | A |
| — | #26 | Direction-aware feedback relabel (6032b64) — does NOT close TD1/#43 | A |
| TD22 | #47 | track_suggestion_outcomes daily KeyError 'open_outcomes'→'active_outcomes' (4b638e6) | A |
| TD36 | #48 | Tavily doc cleanup monthly→daily + non-existent env var (fae6edf) — DOC-ONLY | A |
| TD40 | #49 | weekly_suggestions_sell idle spec expected_weekdays=set() (6032b64) | A |
| — | #27 | F1+F3 ad-hoc chat: conversation model+scope+index+lookup_by_isin / ensure_stock_context enrichment / chat service + /chat/{suggestions,holdings/{isin},history} + main.py / ChatPanel+StockResearchPanel+lib/api.ts + embeds; + /instruments/search route-shadow fix (Chat 6, no TD number) — backend `5e787c9`, frontend `6093f63` | 6 |
| — | #28 | F12+F15: _annotate_holdings extraction (behaviour-preserving) + compute_risk_summary + GET /portfolio/risk-summary / GET /portfolio/by-tag reusing the list_holdings annotate path / RiskSummaryCard + lib/api.ts RiskSummary+HoldingsByTag bindings + Tags nav / dedicated /tags page (Chat 7, no TD number) — backend Unit 1 `97041621`, Unit 2 `803e6610`; frontend `e14d6a75` | 7 |

**OPEN / DEFERRED TDs (full):**

| TD | master_todo | Item | Status |
|---|---|---|---|
| TD1 | #43 | Make monitored_stocks direction-aware (dual rows per ISIN). Reconcile with #26. **#26 added direction-aware RELABEL on the feedback payload + outcome query, but monitored_stocks itself stays direction-agnostic — revisit whether the practical pain is gone.** | DEFERRED — post-launch |
| TD3 | #44 | Split dossier_service.valuation_verdict → {verdict, rationale}. | DEFERRED — future UI |
| TD6 | #41 | Wire holdings.stop_loss (reader + writer + alerts; frontend edit field). | OPEN — Chat 9 |
| TD7 | #45 | Refactor CandidateScore so sell-side groups are first-class fields. (The coupling is why #27 reimplemented the position/tax block instead of calling `_build_position_context_block`.) | DEFERRED — post-launch |
| TD21 | #46 | Registry-generated crontab migration. Chosen over in-process APScheduler. Its own dedicated chat. | OPEN — dedicated chat |
| — | #50 | News entity mis-tagging in `news_articles.entities_isins` — the #27 HDFCBANK chat returned TCS/Kenya articles tagged with HDFC's ISIN. Defect is upstream in news_fetcher/classifier tagging; degrades news_score + dossier news block + chat. Investigation-first. (Chat 6, no TD number) | OPEN — Chat 6 filed |
| — | #51 | `dividend_yield` ×100 formatting — Reliance chat showed "46%". The chat `_fmt_pct` is byte-consistent with `dossier_service._fmt_pct` (`f"{v*100:.2f}%"`), so this is a pre-existing app-wide yfinance unit inconsistency (some rows stored already-as-percent). Decide the canonical unit and fix at ingest and/or both formatters consistently — do NOT diverge the chat formatter from the dossier. (Chat 6, no TD number) | OPEN — Chat 6 filed |

**F-number fix registry (TD15 deliverable, grepped at backend HEAD c097b473; app/ + scripts/ only).** 25 unique numbers across TWO namespaces: **Feature** (roadmap tickets) and **Fix-5.5+** (robustness tags). They COLLIDE on F1, F2, F3, F4, F5, F7, F8, F12, F14 — a bare `# FN` comment is ambiguous until read verbatim.

| F# | Kind | File(s):line (HEAD c097b473) | Description |
|---|---|---|---|
| F1 | Feature | models/monitored_stock.py:4,14,70 | Ad-hoc chat for suggestions (Chat 6/#27 — SHIPPED) |
| F1 | Fix-5.5+ | services/reconciliation.py:197 | utcnow() returns tz-naive UTC to match Mongo writes |
| F2 | Feature | models/suggestion.py:31,117,123,174,183; routers/suggestions.py; scripts/run_weekly_suggestions.py:3,127 (+~40 sites) | Sell-side direction |
| F2 | Fix-5.5+ | services/holdings_service.py:344,351,357 | recompute_holding deletes stale soft-deleted holding docs |
| F3 | Feature | models/monitored_stock.py:4,14,70 | Ad-hoc chat for a single holding (Chat 6/#27 — SHIPPED) |
| F3 | Fix-5.5+ | services/holdings_service.py:82,429,501 | preview_sell/validate_replay apply SPLIT/BONUS to lot qty |
| F4 | Feature | settings.py:46; db/client.py:156; db/indexes.py:322; routers/cron.py:1; services/cron_heartbeat_service.py:1,125; services/notify.py:5,67; services/holdings_service.py:82,605,661; scripts/cron_health_check.py:1,150 | Cron observability |
| F4 | Fix-5.5+ | services/holdings_service.py:82,605,661 | validate_replay applies SPLIT/BONUS to lot qty |
| F5 | Feature | services/suggestion_engine.py get_excluded_isins | F5a cron registration; F5b 30-day acted soft-exclude |
| F5 | Fix-5.5+ | services/holdings_service.py:434,470,516; routers/holdings.py:281 | Per-lot realized P&L fee normalization |
| F6 | Feature | models/monitored_stock.py:32,104; routers/suggestions.py:3; services/explainability.py:779,783,814,829,890; services/suggestion_engine.py:120,125,210 | Stateful feedback exclusion (two-mechanism) |
| F7 | Feature | (roadmap) | Real ICICI data import — last (Chat 10/#42) |
| F7 | Fix-5.5+ | services/price_service.py:161 | Revived dead NaN-guard branch |
| F8 | Feature | (roadmap) | Dividend tracking — DROPPED |
| F8 | Fix-5.5+ | services/price_service.py:533 | NaN drop covers Open/High/Low, not just Close |
| F10 | Feature | db/client.py:121; db/indexes.py:236; routers/suggestions.py:8,220,229,243,268; services/monitored_stocks_audit_service.py:1 | monitored_stocks write-before-apply audit + read endpoints |
| F12 | Feature | (roadmap) | Portfolio risk-summary / concentration (Chat 7/#28 — SHIPPED; lives in routers/portfolio.py + services/portfolio_service.py with their own #28 references) |
| F12 | Fix-5.5+ | routers/holdings.py:325 | Fully-exited SELL response includes realized_total |
| F13 | Feature | models/monitored_stock.py:5,9,14,83 | Watchlist (Chat 8/#29) |
| F14 | Feature | models/earnings_event.py:1; services/scoring_service.py:30,109,157,265,571; services/suggestion_engine.py:5,472,507; services/fundamentals_service.py:318; services/explainability.py:318 | Earnings calendar + shared earnings-proximity gate |
| F14 | Fix-5.5+ | routers/holdings.py:46,63; models/transaction.py:125 | Positivity validators (gt=0) |
| F16 | Fix-5.5+ | models/reconciliation.py:32,50 | Money alias → Decimal128↔Decimal |
| F17 | Fix-5.5+ | models/reconciliation.py:51 | _schema_version alias |
| F18 | Fix-5.5+ | models/cost_basis_adjustment.py:47,59 | amount Money alias |
| F19 | Fix-5.5+ | models/cost_basis_adjustment.py:48,73 | _schema_version leading-underscore alias |
| F20 | Fix-5.5+ | models/instrument.py:16,25 | populate_by_name + _id alias |
| F21 | Fix-5.5+ | routers/transactions.py:63,79 | reason field REQUIRED on PATCH/DELETE |
| F23 | Fix-5.5+ | services/reconciliation.py:190 | Write Decimal128 (not float) into Mongo |
| F27 | Fix-5.5+ | services/news_classifier.py:106,198 | Caller no longer pre-merges id |
| F28 | Fix-5.5+ | services/explainability.py:645,755,811 | _build_group_meta accepts direction |
| F29 | Fix-5.5+ | models/transaction.py:23,58,112 | Money fields ge=0 + zero-qty rejects |
| F79 | Fix-5.5+ | models/symbol_override.py:16,24 | populate_by_name + _id alias |
| F80 | Fix-5.5+ | models/transaction.py:13 | Three manual-prefixed source enum values |
| F82 | Fix-5.5+ | models/transaction.py:80 | Broker reference fields (ICICI ref) |

Notes: F11 (capital-gains pack, Chat 9/#39) is a feature ticket with no in-code reference yet — intentionally absent. F15 (tag views, Chat 7/#28) was likewise absent until Chat 7 SHIPPED it; the implementation lives in `routers/portfolio.py` (`GET /portfolio/by-tag`) + the frontend `/tags` page, carrying their own #28 references rather than a `# F15` comment. Feature-F rows for colliding numbers are for disambiguation only. (F1/F3 feature rows are SHIPPED via #27, and the F12 feature row is SHIPPED via #28, but the in-code `# F1`/`# F3` comments still live on `models/monitored_stock.py` as scaffolding markers — the #27 implementation lives in `routers/conversations.py` + `services/conversation_service.py`, and the #28 implementation in `routers/portfolio.py` + `services/portfolio_service.py`, which carry their own references.)

**Fixed in earlier chats (posterity):** Digest sell-side Q/V/M/N bug (cea8eee). track_suggestion_outcomes daily failure (TD22, FIXED Chat A). holdings.target_price half-fixed (stop_loss is TD6). MonitoredStock schema↔writer drift (A1). Dead news_article.py (A8). All Chat 5 A2–A19 + TD8.

## Section 19: How to update this document

Updated at the end of every chat as the LAST commit — ALWAYS a complete full-file canvas artifact, never a patch.

**Update each chat:** Sec 13 (move shipped; advance chat split plan — preserve rows) · Sec 9 (cron registry if changed) · Sec 14/15/16/17 (new conventions / anti-patterns / triggers / diagnostics) · Sec 18 (add/remove/reclassify TD) · Sec 12/11 (new invariants) · Sec 7 (collection schema) · Sec 8 (endpoint changes) · Sec 5/6 (file additions/deletions — diff against the Section-0 tree listing line-by-line) · Sec 4 (pin new last-verified SHAs).

**Commit message:** `docs: update PROJECT_STATE.md after <chat scope>` + a bullet list of sections changed.

If the chat ended due to context loss, the LAST thing the assistant does is propose the Project_State + master_todo update; the user applies it manually.

**Standing doc rules:**
* On starting a new chat, after reading Project_State, audit every "open" item against on-disk code at HEAD before estimating work.
* Project_State.md structure is immutable: Section 0 at top, numbered Sections 1-22 in order. New sub-items go INSIDE existing sections, never as new top-level sections.
* When reading this file for a full-file refresh, prefer the SHA-pinned `raw.githubusercontent.com` URL over the blob URL (blob frequently `LINK_NEEDS_AUTH`). If both fail, have the user `ssh ubuntu@100.112.20.41 && cat ~/ai-stock-advisor-backend/docs/Project_State.md` and paste the bytes — Glean's raw reader sentence-wraps, so never reconstruct a full-file replacement from a wrapped read; anchor on a user-pasted byte-exact source (`git show <sha>:docs/Project_State.md`). NOTE (5.17): a `git show` paste through a narrow terminal can ITSELF hard-wrap mid-word — when reconstructing from such a paste, un-wrap carefully and gate the result with a `git diff` review so no unchanged line drifts. (Re-confirmed Chat A, Chat 6 AND Chat 7: the user's `git show` paste had mid-word wraps like "shownis"/"atomicTavily"/"weekly_sugg estions"/"Itemnumbers"/"directi on"/"vsthe"/"thelast"/"HE AD"/"Markdo wnLite"/"con versation_service"/"po sition"/"fil ed" — un-wrapped during reconstruction; gate with `git diff`.)
* The tree-listing command (Section 0) MUST be the first thing run in every new chat, before scope. Every file-read URL uses a SHA the user supplied this chat and a path verified in the tree listing.
* The end-of-chat full-file artifact MUST end with the sentinel `End of PROJECT_STATE.md.` and have a line count >= the prior commit's (or explicitly state why it shrank) BEFORE the user commits. (5.8's doc commit silently truncated 655 lines.)
* Update master_todo.md status AND the matching Section 18 TD row AND Section 13 in the SAME end-of-chat doc commit as the code; pin each commit SHA next to its TD row.

## Section 20: Trade-off rationale (decisions that might look weird)

* yfinance over Tijori/Screener Pro: free, swappable. Confidence numeric 0-100 deterministic. Suggestions Sunday 07:00 IST. Top-K = 10. 90-day rejected cooldown + 30-day acted soft-exclude + zero passed cooldown — not env-configurable. Persistent backend feedback state (Chat 3). Two-mechanism F6 exclusion. valuation_verdict one string. Dividend tracking dropped (F8). Realized P&L hidden UI, kept backend. F7 last (Chat 10). Watchlist (F13) extends the engine universe. F4 ntfy errors public over private; CRON_REGISTRY in code; cron_health_check.py is itself a registered cron.
* (Chat 4) F2b digests on public ntfy.sh; F14 as gating signal; shared scoring pipeline; CandidateScore fixed buy-side fields; --direction=both as production cron; sell-side sign-flip at read time.
* (Chat 5) F2b display-layer direction branching; audit-then-fix ordering; A2 wrapper return-shape change; TD8 in two commits; commit 8 raises only when BOTH transports fail; logrotate over hand-rolled truncation.
* (5.5–5.19) See per-chat rationale lines in prior versions (TD9/TD11/TD12 minimal-invasive; TD14 build-right registry rename; TD19 warning-flag over M10 transactions; TD20 advisory-lock doc over asyncio.Lock; TD23 fixed UTC+5:30; TD25 per-ISIN find_one over aggregation; TD26 ASC TTL alongside DESC; TD28 minimal name-swap; TD33 atomic find_one_and_update over lock; TD34 retry inside email() preserving contract; TD35 model-carried id; TD37 ValueError for 422; TD38 disk-file fallback; TD39 wrap only the read loop + re-raise).
* (Chat A) Bundle worked in meaningful units (#34+#35 / #25 / #49+#26 / #47 / #48). #34: 503 status code + no yfinance on the hot path. #25: ntfy-ONLY auto-drift via a new `_send_auto_drift_alert` + rising-edge dedupe. #26: defaulted `direction` field + `$or`/`$exists:false` buy guard; does NOT close TD1/#43. #47: reproduced live before fixing; renamed the consumer key. #49: option 1 (`expected_weekdays=set()`). #48: fixed the wider doc drift the code check surfaced.
* (Chat 6) #27 built in 4 units + 1 fix, SHA re-requested per unit. **Path-2 (full on-demand enrichment) over graceful-degradation** (user-chosen "if it's in the todo, build it completely") — so a not-yet-owned, out-of-universe ticker gets the same news-backed buy analysis as a held/candidate name. **Generalized the per-stock endpoint** (held -> position/tax overlay; not held -> buy-research framing) over a strict held-only F3 — but **kept the documented `/chat/holdings/{isin}` path** (honors §8 contract) rather than renaming to `/chat/stock/{isin}`. **Single Sonnet `{answer,intent}` call** over a separate Haiku intent-classify call — cheapest/simplest, self-labels intent, and is the consistent JSON house style; Haiku stays where it earns its place (news classification). **`scope` field** added over overloading `intent` (surface vs question). **Reimplemented the position/tax block** rather than calling the CandidateScore-coupled `_build_position_context_block` (evolve-not-call). **Embedded chat on existing /suggestions + /holdings/[isin] surfaces** over a new `/chat` route (don't overcomplicate; §21 anti-standalone-page stance). **Self-contained `MarkdownLite`** over adding `react-markdown` (no npm install / lockfile churn on the t3.micro; keeps deploy a plain build). **Unknown ISIN -> clean 404** over a yfinance rescue (yfinance is symbol-keyed; the master holds the full NSE list). **Route-shadow fixed by reordering** (static before dynamic) + a NOTE, over a route-prefix workaround. Surfaced issues filed as #50/#51 rather than silently fixed outside scope.
* (Chat 7) #28 built in 2 backend + 2 frontend units, SHA re-requested per unit, design approved before code. **Shared `_annotate_holdings` extraction** over a parallel risk aggregation — guarantees risk concentration == /summary concentration; the refactor is behaviour-preserving and gated by a `/summary` curl-diff. **Two-tier alert thresholds (warn/high) as module constants** over env/settings or single-tier — actionable signal on a ~28-name book, the TOP_MOVERS_LIMIT pattern. **concentration_by_holding returns EVERY priced holding** (not just top-5) so the frontend can slice; the dashboard card shows the top 5. **`stale_price` low-severity note** included (free, reuses the existing flag) but **stop_loss/target gaps deliberately EXCLUDED** (that brushes #41/Chat 9). **by-tag reuses the `list_holdings` annotate path** so rows render in the existing HoldingsTable; **exact case-sensitive tag match** (the symbol-search convention family); **unknown tag -> zeroed 200, missing/empty -> 422**. **F12 frontend as a full-width dashboard card with its OWN useQuery** (failure-isolated) over a 3rd grid cell; **F15 on a dedicated `/tags` page** over a dashboard widget (lower-risk, reuses HoldingsTable wholesale). **NEW lib/api.ts types** because ConcentrationItem/SectorBucket didn't match — no force-fit. **No new npm/shadcn dependency.** No new TD filed.

## Section 21: What is intentionally NOT included

So future chats don't accidentally add these:
* Auto-trading (never). Multi-user. Mutual funds, FDs, foreign equities, derivatives, crypto. Native mobile app. Tax filing. Dividend tracking (F8 dropped). Accounting / financial planning / goal-based planning. Real-time tick data. Public-facing dashboard. Backtesting framework. Notification customization UI. Account aggregation. Social features. Technical indicator alerts. Options tracking. Index fund comparison page. Separate /news page. Heatmaps. Portfolio rebalancing recommender. Social sentiment tracking. Manual-clear endpoint for feedback (use mongosh). /calendar page. Loss-cutting sell pipeline (F2 is profit-booking only).
* **In-process application scheduler (APScheduler/lifespan jobs).** Schedule stays in crontab; TD21 will version-control it via a registry-rendered ops/crontab.
* **Mongo multi-document (M10) transactions on the synchronous write path.** Rejected for TD19; atomicity for the Tavily quota comes from a conditional find_one_and_update + unique index.
* **DST-aware timezone handling for IST.** India has no DST; IST is fixed UTC+5:30.
* **Dropping/replacing a same-field index to add a TTL** when an ASC-vs-DESC split lets both coexist (5.12).
* **Case-insensitive symbol search.** Symbols uppercased + stored uppercase; NO $options:i (5.13 TD32). (Same convention applies to GET /instruments/search/{symbol_prefix}, Chat 6, AND to GET /portfolio/by-tag tag matching, Chat 7 — exact + case-sensitive.)
* **A credits_today ceiling on Tavily.** Only calls_today is capped (5.14).
* **A lock or M10 transaction around the Tavily quota increment** (5.14 TD33).
* **A raised-exception path or env-configurable knobs for notify.email()** (5.15 TD34).
* **A `find_one(sort run_date desc)` re-derivation to recover "the run just created"** (5.16 TD35).
* **A signature change to send_combined_digest** (5.16).
* **Broadening the #22 NaN guard to the Decimal/Decimal128 read paths** (5.17 TD37).
* **Widening the #24 try/except beyond the per-cron Mongo-read loop, or returning success after the reads fail** (5.19 TD39).
* **(Chat A) yfinance (or any slow external) on the `/health` hot path** (#34).
* **(Chat A) Email on the daily `take_auto_snapshot` drift alert; current-value drift on the auto path; a parallel reconciliation alerter** (#25).
* **(Chat A) Closing TD1/#43 via #26** — #26 made the RELABEL direction-aware but NOT `monitored_stocks` itself.
* **(Chat A) Restoring `weekly_suggestions_sell` `expected_weekdays={6}`** without a real crontab line under that cron_name (#49).
* **(Chat 6) A second LLM call (Haiku intent-classify) on the chat path** — one Sonnet call returns `{answer, intent}`; do NOT add an intent-classify hop (#27).
* **(Chat 6) A standalone `/chat` frontend route** — the chat embeds on the existing /suggestions and /holdings/[isin] surfaces (#27).
* **(Chat 6) `react-markdown` (or any markdown npm dependency)** — the self-contained `MarkdownLite` handles the Sonnet subset; adding a package means an `npm install` + lockfile churn in deploy (#27). Add it only with an explicit decision.
* **(Chat 6) Calling `_build_position_context_block` from the chat path** — it is CandidateScore-coupled; the chat reimplements the LTCG/weight math (#27). (Fixing the coupling is TD7/#45, deferred.)
* **(Chat 6) A yfinance rescue for an unknown ISIN on the per-stock chat** — yfinance is symbol-keyed; an ISIN miss is a clean 404 (#27).
* **(Chat 6) Diverging the chat `_fmt_pct` from `dossier_service._fmt_pct`** — they stay byte-consistent; the dividend-yield ×100 unit fix (#51) lands at the source / both formatters together, not by forking one.
* **(Chat 6) Using the `conversations.follow_up_conversation_ids` field for threading right now** — each chat turn is independent; threading is a clean future add, intentionally unwired (#27).
* **(Chat 7) A parallel risk aggregation path** — risk-summary EVOLVES `compute_summary` via the shared `_annotate_holdings` helper; do not duplicate the annotation (#28).
* **(Chat 7) Risk/alert thresholds in env or settings** — they are module constants in `portfolio_service.py`, the TOP_MOVERS_LIMIT pattern (#28).
* **(Chat 7) stop_loss/target-gap alerts in risk-summary** — that is #41 (Chat 9); risk-summary covers only concentration + a stale-price data note (#28).
* **(Chat 7) A parallel by-tag annotate path or a parallel `_to_dec`** — by-tag reuses the `list_holdings` annotate path and imports `portfolio_service._to_dec` (#28).
* **(Chat 7) Case-insensitive tag matching** — exact + case-sensitive array-membership, same family as symbol search (#28).
* **(Chat 7) A new npm/shadcn dependency or a new `/chat`-style standalone for F12** — the risk card uses existing primitives on the dashboard; F15 gets a `/tags` page reusing `<HoldingsTable>` (#28).

## Section 22: Glossary

ISIN: 12-char NSE/BSE primary key. NSE / NIFTY 100 / FIFO / LTCG / STCG / Section 49(2C) / ICICI Direct / ICICI ZIP / TMPV / TMCV / EW NIFTY: see prior version. Composite score: 0-100, Q/V/M/N (buy) or booking_opportunity/valuation_stretch/risk/tax_concentration (sell). Confidence score: 0-100, deterministic. Dossier: Sonnet per-candidate note. Outcome: suggestion_outcomes doc. Bucket: outcome user-action label. Watchlist: F13. user_action: per-candidate serialization-time stamp (F6). direction (F2): "buy"|"sell". monitored_stocks_audit: F10. earnings_calendar (F14). Combined digest (F2). isSellSide (F2). MonitoredStockFeedbackPatch (A1). SuggestionFeedback (#26): feedback payload, `extra="forbid"`; fields action, note, direction:Literal["buy","sell"]="buy". notify.email() return contract (A2): `{ok, id, error}`, swallows exceptions (5.15 TD34 internal retry). push_public: ntfy push, RAISES on failure — guard it (#24, #25, #35). /health (#34): 200 ok/ok or 503 degraded/fail; yfinance not probed. _send_auto_drift_alert (#25): ntfy ONLY, invested drift vs last manual snapshot, rising-edge deduped. Explicit inserted_id flow (TD35). _to_decimal NaN guard (TD37). Fallback heartbeat log (TD38). Health-check self-failure alert (TD39). active_outcomes (#47/TD22). weekly_suggestions_sell (#49/TD40): idle, expected_weekdays=set(). Tavily quota (#48/TD36): DAILY, resets 00:00 UTC, TAVILY_DAILY_CALL_LIMIT. **Conversation (#27): conversations write model, BaseDoc; query/response/intent (QueryIntent 9-value)/scope (suggestions|holding)/sentiment_overlay/cited_* id lists/model_used/tokens/cost_usd (Money)/duration_ms/follow_up_conversation_ids (unused). ConversationScope (#27): Literal["suggestions","holding"], the surface discriminator distinct from intent. ensure_stock_context (#27): conversation_service orchestrator — freshness-gated on-demand fundamentals/earnings/news enrichment via the cron-path services; writes only Phase-2 reference collections. lookup_by_isin (#27): instrument_service reverse lookup ISIN -> instrument (NSE-preferred). MarkdownLite (#27): self-contained chat-panel.tsx markdown renderer (no npm dependency). Chat endpoints (#27): POST /chat/suggestions (F1), POST /chat/holdings/{isin} (F3, generalized to any known NSE instrument, 404 on unknown, ISIN-validated), GET /chat/history. Route-shadow rule (#27): a static FastAPI route must be declared before a sibling dynamic route or the dynamic one captures it (the /instruments/search 404).** **_annotate_holdings (#28): portfolio_service helper extracted from compute_summary returning (annotated, accum); shared by compute_summary + compute_risk_summary so risk concentration never drifts from /summary. compute_risk_summary (#28): concentration_by_holding (every priced holding desc by %) + concentration_by_sector + two-tier alerts (single_holding warn>10/high>20, sector warn>30/high>50, + low-severity stale_price). Risk thresholds (#28): four module constants in portfolio_service.py (SINGLE_HOLDING_CONCENTRATION_WARN_PCT/HIGH_PCT, SECTOR_CONCENTRATION_WARN_PCT/HIGH_PCT), not env-configurable. Portfolio endpoints (#28): GET /portfolio/risk-summary (F12), GET /portfolio/by-tag?tag=X (F15, required tag->422, exact case-sensitive array-membership on holdings.tags, annotated via the list_holdings path, unknown tag->zeroed 200). RiskSummaryCard (#28): dashboard F12 card, own useQuery(["dashboard","risk"]). /tags page (#28): F15 frontend, reuses HoldingsTable.**

End of PROJECT_STATE.md.
