
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
- Every test block in chat MUST start with `ssh ubuntu@100.112.20.41` and run subsequent curls against `localhost:8000`. Do not give curls against the Tailscale IP from the Mac. (Frontend-only changes test via `~/deploy-ui.sh` + `npm run build`/lint on EC2.)
- Project_State.md AND master_todo.md are ALWAYS delivered as complete full-file replacements, never patches/diffs/find-and-replace. No exceptions.
- ASK FOR CURRENT BACKEND SHA BEFORE PROPOSING ANY CODE CHANGE. Re-read the file at that SHA before writing the patch. (Chat 5 standing convention; see Section 14.)
- BEFORE documenting what a script does, read its body at HEAD; before documenting a cron line, verify the script's argparse accepts the flags. (Chat 5.5 standing conventions; see Section 14.)
- AT NO POINT make code changes while relying on memory. Construct the GitHub URL of the file you need (owner=`doshisahil95`, repo, commit SHA the user supplied, file path from the Section-0 tree listing) and re-read from source. (Chat 5.7 standing convention; see Section 14.)
- WHEN CONTINUING THE MASTER PLAN: read `master_todo.md` current-position pointer FIRST, confirm the next item with the user, then proceed. (Chat 5.8.)

## Section 3: Tech stack

### Backend
- Python 3.12
- FastAPI
- Pydantic v2 (every Query() in routers uses `pattern=` not `regex=` post Chat 5 A19; round-trip / `ge=0` validator hardening across models post Chat 5.6; ISIN `Path()` params on the two `/suggestions/{isin}` endpoints carry `pattern=r"^[A-Z0-9]{12}$"` post Chat 5.13 TD31)
- MongoDB Atlas, M10 cluster, ap-south-1 region
- uv (package manager — replaces pip/poetry)
- yfinance (price + fundamentals + earnings calendar data; free tier)
- Anthropic Claude SDK (Sonnet 4.5 for dossiers, Haiku 4.5 for classification)
- Tavily (news search; free tier, daily quota enforced — atomically as of Chat 5.14 TD33)
- Resend (transactional email for digests, drift alerts, smoke tests, cron-health alerts — all routed through `notify.email()` as of Chat 5 A2; transient 5xx/429 retried once with 30s backoff as of Chat 5.15 TD34)
- ntfy (push notifications — public ntfy.sh for all paths; self-hosted private service decommissioned TD8)

### Frontend
- Next.js 16 (Turbopack)
- React 19
- TypeScript strict mode
- Tailwind v4
- shadcn/ui Nova preset
- Recharts (price charts)
- TanStack Query (server state — mutations use `refetchQueries`, synchronous; the two `invalidateQueries` outliers in `notes-panel.tsx` + `refresh-button.tsx` were swapped to `refetchQueries` in Chat 5.13 TD28)
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
- `portfolio-advisor.service` — runs `uvicorn app.main:app --port 8000 --host 0.0.0.0` as user `ubuntu`, with `Environment="PYTHONPATH=/home/ubuntu/ai-stock-advisor-backend"`, `Environment="PYTHONUNBUFFERED=1"`. Logs to journald. Single process, single worker (no `--workers`). NOTE (Chat 5.10): because there is no `--workers` and the route handlers are sync `def`, concurrent requests run in Uvicorn's threadpool — i.e. THREADS within one process. This is why TD20's per-ISIN serialization uses a Mongo advisory-lock doc (cross-thread AND cross-process), not `asyncio.Lock` (event-loop-only, useless for sync handlers). (Chat 5.14: this same threadpool concurrency is why the Tavily check-then-act was a real TOCTOU race even on this single-process box — TD33. Chat 5.15: the TD34 retry's blocking `time.sleep(30)` therefore blocks ONE threadpool worker, not the whole process — anyio's default pool is 40 threads, so on a single-user box this is acceptable.)
- `portfolio-advisor-ui.service` — runs `node /home/ubuntu/ai-stock-advisor-frontend/node_modules/next/dist/bin/next start` on port 3000 with hardening (`NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict`, `ReadWritePaths` includes the frontend dir and `/tmp`).

A sudoers entry at `/etc/sudoers.d/portfolio-advisor-systemctl` lets `ubuntu` restart these services without password.

### Log rotation (Chat 5 SHIPPED 2026-05-24)
`/etc/logrotate.d/portfolio-advisor` rotates all `/home/ubuntu/cron-*.log` weekly:
- `rotate 4` · `compress` + `delaycompress` · `notifempty` + `missingok` · `copytruncate` · `su ubuntu ubuntu`

Daily logrotate cron is the OS-provided `/etc/cron.daily/logrotate`. Force-rotate any time with `sudo logrotate -f /etc/logrotate.d/portfolio-advisor`.

TD10 / master_todo #2 (SHIPPED Chat 5.9, 2026-06-02): the pre-existing `0 0 * * 0 find ... -size +10M ...` truncation line was verified ABSENT from the live EC2 crontab and logrotate confirmed working — the rotation trail `cron-*.log.1` (dated 2026-05-31 00:00 IST) + `cron-*.log.2.gz` (dated 2026-05-24) exists for all 10 logs. No crontab edit was needed; the redundant line was already gone. The end state TD10 wanted (logrotate is the sole rotation mechanism) is satisfied.

Chat 5.12 note: the daily 02:30 IST `purge_news_bodies` cron (TD27) writes to `/home/ubuntu/cron-news-purge.log`, which the existing `cron-*.log` logrotate glob already covers — no logrotate change needed.

### Repos
- Backend: https://github.com/doshisahil95/ai-stock-advisor-backend
- Frontend: https://github.com/doshisahil95/ai-stock-advisor-frontend

Last verified SHAs (Chat 5.15 closed, 2026-06-12):
- Backend: `7d77b9cbee9f3155f22c86057b20640f21599ee9` (Chat 5.15 Phase-6 #20 close: deployed code HEAD after ONE backend code commit — TD34 transient-5xx/429 retry in `app/services/notify.py` `email()` (a 1-retry / 2-attempt loop with a 30s blocking backoff on HTTP 429 + 5xx; 400s and no-status errors return immediately; `{ok,id,error}` contract + no-raise guarantee unchanged so the three `result["ok"]` callers are untouched). HEAD advances after this Chat 5.15 doc commit — pin in next chat). Chat 5.15 opened at `582cd18d5d50d90b1ae4d1174a22a59799d69ca0` (the Chat 5.14 doc commit). Backend-only chat.
- Frontend: `f59958015b8b07b6e84e3add7b4a302d32b43490` (unchanged since Chat 5.13 — Chat 5.14 and Chat 5.15 were backend-only).
- Backend (Chat 5.14 close): `4ac2c955782490818eefa6024c9daead92b0b0eb` (Chat 5.14 Phase-6 #19 close: deployed code HEAD after ONE backend code commit — TD33 atomic Tavily quota claim in `app/services/tavily_client.py` (the `get_today_quota()` pre-check + separate `_increment_quota()` `$inc` collapsed into one conditional `find_one_and_update` guarded by `calls_today < TAVILY_DAILY_CALL_LIMIT`; cap-hit detected via `DuplicateKeyError` on the unique `date_unique` index). Chat 5.14 opened at `5ab01ef0df2ebb3c3d1d0aba26cdce9be17c17fe` (the Chat 5.13 doc commit). Backend-only chat.
- Backend (Chat 5.13 close): `090d96c0042e7d5ccd154dcaf6329a0bba57ebb7` (Chat 5.13 Phase-5 close: deployed code HEAD after THREE backend code commits — TD29 dead-import removal in `app/routers/holdings.py`, TD31 ISIN `pattern=` on the two `/suggestions/{isin}` Path params in `app/routers/suggestions.py`, TD32 `$options:i` drop on the transactions/search regex in `app/routers/transactions.py`). Chat 5.13 opened at `07d9a413b39d330e3ea9047dec4e38917a446449` (the Chat 5.12 doc commit).
- Frontend (Chat 5.13 close): `f59958015b8b07b6e84e3add7b4a302d32b43490` (Chat 5.13 Phase-5 close: ONE frontend code commit — TD28 `invalidateQueries` → `refetchQueries` swap in `components/notes-panel.tsx` + `components/refresh-button.tsx`). Chat 5.13 opened at `4f31b49b103f92ea5b4721f9728156041e908f49` (unchanged through Chats 5.6–5.12).
- Backend (Chat 5.12 close): `49bf33f` (deployed code HEAD after TWO code commits — TD26 `prices_intraday.captured_at` TTL on `app/db/indexes.py`, then TD27 `scripts/purge_news_bodies.py` + the `purge_news_bodies` `CronSpec` on `app/services/cron_heartbeat_service.py`; the crontab line was added on EC2 separately). Chat 5.12 opened at `8cf2ae8e0e94fa29b78b015d21b148c1e1e924e5` (the Chat 5.11 doc commit).
- Backend (Chat 5.11 close): `a2806cd` (the single TD23–TD25 code commit). Chat 5.11 opened at `f22eb9a4719422e238d4c462534c5b45164f6e78` (the Chat 5.10 doc commit) and shipped ONE code commit `a2806cd` carrying all three Phase-3 items (TD23 holiday guard + TD24 price_stale alignment + TD25 bulk_get_previous_closes rewrite). The prior Chat 5.10 close was `b34721e8251bb21ad59c0f111f1c8022528844b6` (TD20 advisory-lock); Chat 5.10 shipped five code commits in master_todo order: `17f9f94` (TD16 write-before-apply) → TD18 dup-handler delete → `5cf3087` (TD17 validate_replay on /sell + manual import) → `fb23307` (TD19 recompute warning-flag) → `b34721e` (TD20 per-ISIN recompute lock).

## Section 5: Backend file map

Directory layout under `app/` and top-level (verified against backend tree at SHA `ce5e746`; recompute_locks accessor + impl rename landed Chat 5.10 at `b34721e`; Chat 5.11 touched only price_service.py at `a2806cd`; Chat 5.12 touched indexes.py + cron_heartbeat_service.py + new purge_news_bodies.py, code HEAD `49bf33f`; Chat 5.13 touched holdings.py + suggestions.py + transactions.py, code HEAD `090d96c`; Chat 5.14 touched only tavily_client.py, code HEAD `4ac2c95`; Chat 5.15 touched only notify.py, code HEAD `7d77b9c`):
```
app/
  main.py                     FastAPI bootstrap, router includes, lifespan
                              (lifespan pings Mongo + ensure_indexes; no scheduler)
  agents/__init__.py          empty package placeholder
  scheduler/__init__.py       empty package placeholder
                              (TD21: candidate home for registry-rendered schedule tooling)
  config/
    settings.py               pydantic-settings; loads secrets file
                              F2b: NTFY_PUBLIC_TOPIC_DIGESTS (required)
                              TD9 SHIPPED: NTFY_URL/USER/PASS field declarations removed
  db/
    client.py                 Mongo client, get_db(), Collections accessor class
                              (incl. monitored_stocks_audit — F10, earnings_calendar — F14,
                              recompute_locks — TD20 / master_todo #8 advisory locks, Chat 5.10)
                              NOTE: app DB name is `portfolio` (MONGODB_DB_NAME default),
                              NOT `portfolio_advisor` (Chat 5.12 verification lesson)
    indexes.py                ensure_indexes() called on startup
                              Chat 5.10: recompute_locks acquired_at TTL index (60s) — TD20
                              Chat 5.12 (TD26 / master_todo #12): prices_intraday
                              captured_at_ttl (ASC, expireAfterSeconds=90*86400) added
                              alongside captured_at_desc (additive; no drop)
                              tavily_quota carries a unique date_unique index on date_utc —
                              the primitive the Chat 5.14 atomic quota claim relies on (TD33)
  models/
    _common.py                utcnow(), Decimal128 helpers, ObjectId helpers
                              (master_todo #22: reject NaN in _to_decimal)
    instrument.py             Instrument (NSE master record)
                              F20 (fix): populate_by_name + _id alias for model_validate
    holding.py                Holding (active position)
    transaction.py            Transaction (BUY/SELL/SPLIT/BONUS/DEMERGER)
                              Chat 5.6: ge=0 validators on quantity / price / total_fees
                              F29/F80/F82 (fix): ge=0 + zero-qty reject, source enum, broker refs
    fundamentals.py           InstrumentFundamentals (per-ISIN, per-refresh)
    earnings_event.py         F14: EarningsEvent (one doc per ISIN per earnings_date)
    suggestion.py             SuggestionRun, SuggestionOutcome, CandidateScore,
                              SignalScore, GateResult
                              F2 direction field; Chat 5.6 round-trip hardening
                              (TD7 / master_todo #45 deferred: sell-side groups as
                              first-class fields)
    news.py                   NewsArticle (live model — the only news model)
                              Chat 5.12: bulky body field is `body_text` (NOT `body`);
                              `body_purged_at` stamped by the purge cron (TD27)
    monitored_stock.py        MonitoredStock + MonitoredStockFeedbackPatch
                              Chat 5 A1 SHIPPED — MonitoringStatus Literal aligned
                              (in-code feature-F1/F3/F13 refs — see Section 18 registry)
                              (TD1 / master_todo #43 deferred: direction-aware)
    macro_signal.py           placeholder
    conversation.py           placeholder (Chat 6 / master_todo #27 will use)
    reconciliation.py         ReconciliationSnapshot
                              F16/F17 (fix): Money alias + _schema_version alias
    cost_basis_adjustment.py  CostBasisAdjustment
                              F18/F19 (fix): Money alias + _schema_version alias
    alert_log.py              placeholder
    digest.py                 placeholder (delivery audit lives in `digest_deliveries`)
    price_daily.py            placeholder (collection writers use raw dicts)
    symbol_override.py        SymbolOverride (manual ISIN aliases)
                              F79 (fix): populate_by_name + _id alias
    user_profile.py           UserProfile (singleton, _id="sahil")
  routers/
    holdings.py               /portfolio/holdings*, /sell, /preview-sell,
                              /history, /transactions
                              F5/F12/F14 (fix) refs — see Section 18 registry
                              master_todo #5 SHIPPED (Chat 5.10): validate_replay on /sell
                              master_todo #6 SHIPPED (Chat 5.10): duplicate list_transactions
                              handler deleted; get_holding_transactions is sole handler
                              master_todo #7 SHIPPED (Chat 5.10): try/except around
                              recompute_holding -> recorded_with_warning
                              Chat 5.10: `import logging` + module `log` added
                              master_todo #15 SHIPPED (Chat 5.13, TD29): dead
                              `from pydoc import doc` (line 6) removed
    portfolio.py              /portfolio/summary
                              master_todo #30: utcnow() sweep (line 43)
    transactions.py           /transactions/search, CRUD, audit endpoints
                              F21 (fix): `reason` required on PATCH/DELETE
                              master_todo #4 SHIPPED (Chat 5.10): write-before-apply on
                              PATCH/DELETE (audit-then-apply)
                              master_todo #18 SHIPPED (Chat 5.13, TD32): dropped
                              $options:i on the search regex (now line 113
                              query["symbol"]={"$regex": f"^{escaped}"}); input is
                              uppercased + symbols stored uppercase, so case-sensitive
                              on purpose and the (symbol, trade_date) index is used
                              master_todo #31: tz-aware datetime sweep
    reconciliation.py         /reconciliation/snapshot, /snapshots, /auto-snapshot
    instruments.py            /instruments (symbol_overrides CRUD)
    cost_basis.py             /cost-basis/adjustments
    suggestions.py            /suggestions/latest, /runs, /runs/{id}, /performance,
                              /{isin}/feedback, /{isin}/audit, /feedback/audit/recent
                              F2: ?direction=buy|sell on read endpoints
                              Chat 5 A1: writer uses MonitoredStockFeedbackPatch
                              Chat 5 A19: Query() pattern= migration
                              master_todo #17 SHIPPED (Chat 5.13, TD31): ISIN
                              pattern=r"^[A-Z0-9]{12}$" added (alongside
                              min_length/max_length=12) to the Path params on
                              get_feedback_audit_for_isin (line 240, /audit) and
                              submit_feedback (line 260, /feedback)
                              master_todo #26: direction-aware feedback relabel
    cron.py                   /cron/heartbeats (F4)
  services/
    instrument_service.py     lookup_isin, bulk_lookup_isins, refresh
    yfinance_lookup.py        thin yfinance Ticker wrapper for sector/industry/long-name
                              enrichment when NSE master is sparse
                              (Chat 5.10: fetch_metadata swallows all exceptions ->
                              safe-default dict; a recompute on an unknown symbol never
                              throws through yfinance)
    price_service.py          EOD + intraday fetch, bulk_get_latest_prices,
                              annotate_with_current_price, get_previous_close
                              IST + _to_ist() helpers (TD23 / master_todo #9, Chat 5.11)
                              F7/F8 (fix): NaN-guard revival + multi-column NaN drop
                              master_todo #9 SHIPPED (Chat 5.11, TD23): holiday guard in
                              _intraday_row_from_df (latest bar IST date != today -> None)
                              master_todo #10 SHIPPED (Chat 5.11, TD24): price_stale
                              docstring aligned to code (6 calendar days canonical)
                              master_todo #11 SHIPPED (Chat 5.11, TD25): bulk_get_previous_closes
                              rewritten to per-ISIN find_one (delegates to get_previous_close)
                              Chat 5.12 (TD26): _intraday_row_from_df writes captured_at as a
                              BSON Date (datetime.now(timezone.utc)) -> the prices_intraday TTL
                              actually expires docs
                              master_todo #31: tz-aware datetime sweep (line 155)
    holdings_service.py       recompute_holding (per-ISIN advisory-lock wrapper) +
                              _recompute_holding_impl (the read-replay-overwrite body) +
                              _per_isin_recompute_lock (CM), validate_replay, preview_sell,
                              _to_decimal helper
                              F2/F3/F4/F5 (fix) refs — see Section 18 registry
                              Chat 5.6: preview_sell SPLIT/BONUS lot-walk fix
                              master_todo #8 SHIPPED (Chat 5.10): recompute_holding
                              serialized per-ISIN via recompute_locks advisory doc + 60s TTL
    portfolio_service.py      compute_summary
    transactions_audit_service.py  log_change, get_audit_for_transaction
                              (Chat 5.10: log_change is now invoked BEFORE the apply in
                              the transactions PATCH/DELETE handlers — TD16)
    monitored_stocks_audit_service.py  F10: log_change (write-before-apply)
    reconciliation.py         take_auto_snapshot, drift detection,
                              _send_drift_alerts (helper sends ntfy + email)
                              F1/F23 (fix): utcnow tz-naive + Decimal128 write
                              Chat 5 A2 part 2: branches on notify.email() result["ok"]
                              (still branches on result["ok"] after the Chat 5.15 TD34
                              retry — contract unchanged)
                              master_todo #25: fire ntfy push on threshold drift
                              master_todo #31: tz-aware datetime sweep (lines 78, ~138)
    cost_basis_service.py     get_active_adjustments, total_adjustment_amount
    fundamentals_service.py   yfinance provider, refresh_one, refresh_universe, etc.
                              F14: earnings calendar refresh
                              master_todo #30: utcnow() sweep (lines 370, 485, 505)
    tavily_client.py          quota-tracked wrapper, TavilyQuotaExceeded
                              master_todo #19 SHIPPED (Chat 5.14, TD33): quota guard
                              is now ONE atomic find_one_and_update in _increment_quota
                              filtered on calls_today < TAVILY_DAILY_CALL_LIMIT (upsert);
                              cap-hit detected via DuplicateKeyError on the unique
                              date_unique index, surfaced as TavilyQuotaExceeded. The
                              get_today_quota() pre-check in search() was removed (it was
                              the TOCTOU window). Added `from pymongo.errors import
                              DuplicateKeyError`. Cap stays calls-only (credits tracked,
                              not capped). get_today_quota/get_quota_history kept (read-only)
                              master_todo #31: tz-aware datetime sweep (lines 50, ~55)
    news_fetcher.py           fetch_for_instrument, fetch_for_universe
                              (imports tavily_client.search / TavilyError /
                              TavilyQuotaExceeded — all preserved across the Chat 5.14
                              TD33 internal refactor; no caller change)
    news_classifier.py        Haiku batch classifier, retry pass
                              F27 (fix): caller id merge + positional fallback removed
                              Chat 5.12 (TD27 / master_todo #13): news body purge cron
                              (scripts/purge_news_bodies.py) reclaims body_text after classify
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
                              (the Chat 5.15 TD34 retry lives inside notify.email(), so
                              _send_email still just branches on result["ok"] — untouched)
                              master_todo #21: persist run_id BEFORE digest formatting — NEXT
    explainability.py         SIGNAL_META, GROUP_META, GATE_META, FEEDBACK_META,
                              PAGE_INTRO + PAGE_INTRO_SELL, enrich_run, enrich_candidate
                              F2: SIGNAL/GROUP/GATE_META extended; _GROUP_TO_SIGNALS extended
                              F28 (fix): _build_group_meta accepts direction
                              Chat 5.5 TD11: _build_signal_meta raw-value fallback
    notify.py                 push_public, email
                              Chat 5 A2 part 1: email returns {ok,id,error}, optional text=
                              Chat 5 TD8: push_private / PrivateTopic removed
                              master_todo #20 SHIPPED (Chat 5.15, TD34): email() retries
                              once (2 attempts total) on transient HTTP 429/5xx with a
                              blocking 30s backoff; 400s + no-status errors return
                              immediately. Added `import logging` + `import time` + module
                              logger, `_email_error_status()` (status off .code/.status_code,
                              fallback error_type=="rate_limit_exceeded"->429) and
                              `_is_transient_email_error()` (429 + 5xx only), plus constants
                              `_EMAIL_MAX_ATTEMPTS=2`, `_EMAIL_RETRY_BACKOFF_SECONDS=30`,
                              `_EMAIL_TRANSIENT_STATUSES`. {ok,id,error} contract + no-raise
                              guarantee UNCHANGED -> all three result["ok"] callers untouched
    cron_heartbeat_service.py F4: cron_run context manager, CRON_REGISTRY,
                              get_recent_heartbeats, ist_today_window_utc
                              Chat 5 A6/A6.5/A7 fixes
                              Chat 5.9 TD14: CRON_REGISTRY entry renamed
                              `run_weekly_suggestions` -> `weekly_suggestions` to match
                              the heartbeat the script writes
                              Chat 5.12 TD27: purge_news_bodies CronSpec added to
                              CRON_REGISTRY (daily, WEEKDAYS_ALL; cron_name ==
                              cron_run() string)
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
  import_orderbooks.py          (calls into recompute_holding -> now per-ISIN locked, TD20)
  reconcile_staging.py
  promote_staging.py            (calls into recompute_holding -> now per-ISIN locked, TD20)
  add_manual_transactions.py    master_todo #5 SHIPPED (Chat 5.10): validate_replay on
                                manual SELL path (aborts RuntimeError, no silent insert)
  refresh_fundamentals.py       F14: default universe NIFTY 100 ∪ active holdings
                                Chat 8 / master_todo #29 will extend for watchlist
  fetch_news_for_universe.py    Chat 5 A16: --include-held on EC2 crontab
                                Chat 8 / master_todo #29 will extend for watchlist
                                (the only production path that exercises the Tavily quota
                                guard — Sunday 06:30 IST; TD33 atomic claim, Chat 5.14)
  run_weekly_suggestions.py     F2: --direction=buy|sell|both (default "buy")
                                argparse accepts ONLY --direction / --no-notify /
                                --skip-dossiers (run_type hardcoded "scheduled")
                                TD14 / master_todo #1 SHIPPED Chat 5.9: bogus
                                `--notify --run-type scheduled` crontab flags removed
  track_suggestion_outcomes.py  Chat 5.9: FAILING every weekday in prod (TD22 /
                                master_todo #47) — surfaced in 21:00 IST health email
  cron_health_check.py          F4: daily 21:00 IST; dual-transport Chat 5 commit 8
                                (confirmed healthy Chat 5.9 — email + ntfy both arriving;
                                the email leg flows through notify.email(), which now
                                retries transient 5xx/429 once — TD34, Chat 5.15)
                                master_todo #24: try/except around Mongo reads
                                master_todo #23: read fallback log too
  smoke_test.py                 Chat 5 TD8: dropped push_private references
  purge_news_bodies.py          Chat 5.12 (TD27 / master_todo #13): daily 02:30 IST cron;
                                $unset body_text + stamp body_purged_at on classified
                                news_articles with fetched_at older than 30 days; --dry-run;
                                cron_run("purge_news_bodies") heartbeat; mirrors
                                refresh_prices_intraday.py
tests/
  __init__.py                   empty package placeholder
                                master_todo #33: stand up pytest harness
docs/
  data_flow.md                  Chat 5 doc deliverable 1/4 SHIPPED
                                Chat 5.5 TD12: universe paragraph corrected
                                (Chat 5.14 NOTE: its Tavily "monthly" wording is STALE —
                                the code is daily; flagged, not yet corrected)
  Project_State.md              THIS FILE (Chat 5.15 doc commit; recovered from
                                Chat 5.8 truncation in Chat 5.9 — see Section 18 TD15)
  master_todo.md                Chat 5.8 NEW — canonical ordered task list
pyproject.toml                  master_todo #32: pin requires-python upper bound
                                (declares resend>=2.4 — the SDK whose typed errors the
                                Chat 5.15 TD34 retry classifies)
uv.lock
README.md                       Chat 5 doc deliverable 2/4 SHIPPED
                                Chat 5.5 TD12: §8 + §11 + §5 corrections
                                (Chat 5.14 NOTE: its Tavily "monthly" wording is STALE —
                                the code is daily; flagged, not yet corrected)
```

(Frontend file map in Section 6.)

## Section 6: Frontend file map

Verified against frontend tree at SHA `4f31b49` (unchanged Chat 5.10–5.12; Chat 5.13 touched notes-panel.tsx + refresh-button.tsx, frontend HEAD `f59958`; Chat 5.14 + Chat 5.15 were backend-only — frontend unchanged):
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
                              OPEN FOLLOW-UP (Chat 5.10, NOT actioned): discriminates on
                              absence of `_id`; a TD19 `recorded_with_warning` response
                              (no `_id`) falls through its non-holding branch. Rare
                              failure path; frontend handling deferred (out of Phase-2 scope).
  transaction-edit-sheet.tsx
  holding-header.tsx          (Chat 9 / master_todo #40: hide realized P&L)
  holding-stats.tsx           (Chat 9 / master_todo #40 + #41: realized P&L hide +
                              stop_loss edit field)
  price-chart.tsx
  transactions-list.tsx
  notes-panel.tsx             master_todo #14 SHIPPED (Chat 5.13, TD28): the two
                              mutation onSuccess invalidateQueries (holding + dashboard
                              keys) swapped to refetchQueries (synchronous). Minimal
                              name-swap, no async/await reorder.
  recent-activity-card.tsx
  sector-breakdown.tsx
  stat-card.tsx
  top-movers.tsx
  totals-row.tsx              (Chat 9 / master_todo #40: hide realized P&L)
  reconciliation-badge.tsx
  theme-provider.tsx
  theme-toggle.tsx
  refresh-button.tsx          master_todo #14 SHIPPED (Chat 5.13, TD28): the three
                              invalidateQueries inside the existing await Promise.all
                              (dashboard + reconciliation + cost-basis keys) swapped to
                              refetchQueries.
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

All collections live in MongoDB Atlas M10. DB name set by env (`MONGODB_DB_NAME`; the live value is `portfolio` — NOT `portfolio_advisor`, a Chat 5.12 verification lesson). All collections accessed via `Collections.<name>()` from `app.db.client`. Indexes ensured at startup via `app/db/indexes.py`.

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
- Writer: `recompute_holding(isin)` in `holdings_service.py` is the ONLY authoritative writer. Chat 5.10 (TD20): recompute is now serialized per-ISIN via a `recompute_locks` advisory doc so concurrent same-ISIN writes can't interleave their read-replay-overwrite cycles.
- Note: `realized_pnl` is structural (FIFO computes it) but is HIDDEN in UI per master_todo #40
- F2: `target_price` consumed by sell-side scoring. `stop_loss` wired by master_todo #41

#### `transactions`
- Append-only ledger
- Key fields: `isin`, `symbol`, `exchange`, `type` (BUY/SELL/SPLIT/BONUS/DEMERGER), `trade_date`, `quantity` (Decimal128), `price`, `total_fees`, `remaining_quantity`, `notes`, `source`, `corporate_action.ratio_from`, `corporate_action.ratio_to`, `fully_consumed_at`, `deleted_at`
- INVARIANT: never directly UPDATEd or DELETEd; PATCH/DELETE require reason, write to `transactions_audit` first, then apply, then `recompute_holding`. **master_todo #4 / TD16 SHIPPED Chat 5.10: order flipped to audit-then-apply; `validate_replay` still runs first so a rejected change writes no audit row.**
- Indexes: `(isin, trade_date)`, `(symbol, trade_date)`, `trade_date`
- Chat 5.6: `ge=0` validators on quantity / price / total_fees; SPLIT/BONUS preview covered in `preview_sell`
- Chat 5.13 (TD32 / master_todo #18): `GET /transactions/search` prefix-matches `symbol` with `{"$regex": f"^{escaped}"}` (NO `$options:i`). Input is `symbol.upper()` and symbols are stored uppercase, so the match is case-sensitive on purpose and the `(symbol, trade_date)` index is used (an `"i"` flag would disable it).

#### `transactions_staging`
- Holding area for ICICI order book imports. Same shape as `transactions`.
- Chat 5.10 (TD17): `add_manual_transactions.py` now replays the per-ISIN staging timeline + the proposed manual SELL via `validate_replay` and ABORTS (RuntimeError) rather than silently inserting an impossible SELL.

#### `transactions_audit`
- Append-only audit log; one doc per edit/delete
- Key fields: `transaction_id`, `action` (edit/delete), `reason`, `changed_fields`, `performed_at`, `symbol`
- INVARIANT (per Section 11): written BEFORE the actual change is applied. **master_todo #4 / TD16 SHIPPED Chat 5.10 — invariant now satisfied in the transactions router (was previously apply-then-audit).**

#### `recompute_locks` (TD20 / master_todo #8, NEW Chat 5.10)
- Per-ISIN advisory locks serializing `recompute_holding`. One doc per in-flight recompute.
- Key fields: `_id` (== isin), `acquired_at`
- INVARIANT: acquired via an atomic `insert_one` (the unique `_id` index makes exactly one holder win); released via `delete_one` in a `finally`; a competing acquirer spin-waits on `DuplicateKeyError` until free or a 10s timeout (timeout -> `RuntimeError`, which the TD19 try/except degrades to `recorded_with_warning`).
- Indexes: default `_id` unique (the mutual-exclusion primitive); TTL on `acquired_at` (`expireAfterSeconds=60`) reclaims a lock if a holder process crashes mid-recompute. 60s is ~1000x a typical <50ms recompute.
- Accessor: `Collections.recompute_locks()`. Writer/holder: `_per_isin_recompute_lock` CM in `holdings_service.py`. Covers the API handlers AND out-of-process scripts (manual import, order-book promote, reconciliation) since the lock lives at the service layer.

#### `prices_daily`
- EOD OHLCV; ~5 years history. Key fields: `isin`, `date`, OHLC, `volume`, `source`. Indexes: `(isin, date)` unique.

#### `prices_intraday`
- Latest intraday quote captured every 15 min during market hours
- Key fields: `isin`, `symbol`, `date`, `captured_at`, OHLCV, `source="yfinance_5m_latest"`
- INVARIANT: append-only within a day
- **TTL: `captured_at_ttl` (ASC, `expireAfterSeconds = 90 * 86400 = 7776000`) — SHIPPED Chat 5.12 (TD26 / master_todo #12).** Bounds this append-only collection (~28 snapshots/holding/day) before Chat 10 GO LIVE. Lives ALONGSIDE the non-TTL `captured_at_desc` (DESC) and `isin_captured_at_desc`; ASC vs DESC are different key patterns, so the TTL and the desc index coexist (mirrors `cron_heartbeats` `started_at_ttl` + `started_at_desc`). The TTL actually expires docs because `captured_at` is written as a BSON Date (`datetime.now(timezone.utc)` in `_intraday_row_from_df`, threaded through `insert_intraday_quotes`) — a TTL silently no-ops on a string/Decimal field.
- Indexes: `isin_captured_at_desc` (isin ASC, captured_at DESC), `captured_at_desc` (captured_at DESC), `captured_at_ttl` (captured_at ASC, 90-day TTL — Chat 5.12)
- Writer: `scripts/refresh_prices_intraday.py` → `_intraday_row_from_df`. master_todo #9 / TD23 SHIPPED Chat 5.11: holiday guard added — a bar whose latest-IST date != today returns None, so a holiday-stale bar never lands here (nor becomes a bogus "current price" via the intraday read path).

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
- Key fields: `url`, `title`, `published_at`, `fetched_at`, `source`, `body_text`, `body_purged_at`, `entities_isins`, `themes`, `sentiment`, `sentiment_confidence`, `severity`, `classifier_summary`, `classified`
- Indexes: `url` unique, `(entities_isins, classified, fetched_at)`, `(classified, fetched_at)`, `body_purged_at`
- **`body_text` purged daily — SHIPPED Chat 5.12 (TD27 / master_todo #13).** `scripts/purge_news_bodies.py` runs daily 02:30 IST: on classified docs whose `fetched_at` is older than 30 days (keyed on `fetched_at`, NOT the nullable `published_at`) it `$unset`s `body_text` and stamps `body_purged_at`. Idempotent (already-purged docs excluded via `body_purged_at:None`). The classification fields (sentiment/themes/severity/classifier_summary) are kept; only the raw body, which has already served the Haiku classifier, is reclaimed. NOTE: the bulky field is `body_text`, NOT `body` — a `$unset {body:""}` would silently no-op (Chat 5.12 lesson).

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
- One doc per UTC day; counters incremented. Key fields: `date_utc` (YYYY-MM-DD), `calls_today`, `credits_today`, `per_use_case.<uc>.calls|credits`, `first_call_at`, `last_call_at`
- INVARIANT: `TAVILY_DAILY_CALL_LIMIT` (default 200) enforced as a hard ceiling on `calls_today` per UTC day; `credits_today` is tracked, NOT capped. Resets 00:00 UTC (the README/data_flow "monthly" wording is STALE — the code is daily).
- Indexes: unique `date_unique` on `date_utc` (the mutual-exclusion primitive the atomic claim relies on)
- **master_todo #19 SHIPPED Chat 5.14 (TD33): the quota guard is now a SINGLE atomic `find_one_and_update`.** `_increment_quota` filters on `{date_utc: today, calls_today: {$lt: TAVILY_DAILY_CALL_LIMIT}}` with `upsert=True, return_document=AFTER` and the existing `$inc`/`$setOnInsert`/`$set` blocks. Under the cap (or on the day's first call) the filter matches/upserts and the `$inc` applies atomically; at/over the cap the existing same-day doc no longer matches, so the upsert attempts a second `date_utc==today` insert and the unique `date_unique` index raises `DuplicateKeyError`, which is caught and surfaced as `TavilyQuotaExceeded` (no credit consumed on refusal). The old `get_today_quota()` pre-check in `search()` was removed — it was the TOCTOU window where two callers at `calls_today == limit-1` could both pass and push the counter past the ceiling.

#### `digest_deliveries`
- Audit log of weekly digests
- Key fields: `run_id`, `run_date_ist`, `sent_at`, `top_count`, `subject`, `email_*`, `ntfy_*`
- F2: combined-digest sends attach to BUY run id
- master_todo #21: persist run_id before formatting
- **TD14 IMPACT (now RESOLVED Chat 5.9): no rows were written by the Sunday cron while the bogus flags were live; after the TD14 fix the Sunday `--direction=both` run writes one row per combined digest again — master_todo #1**

#### `cron_heartbeats` (F4)
- Key fields: `cron_name`, `started_at`, `finished_at`, `status`, `error`, `metadata`, `_schema_version`
- INVARIANT: append-only; best-effort. **master_todo #23: fallback log on insert failure**
- INVARIANT (Chat 4): `_Heartbeat.meta` is an ATTRIBUTE; `ctx.meta = {...}`
- Chat 5.9 TD14: the Sunday run writes its heartbeat under `cron_name="weekly_suggestions"` (NOT `run_weekly_suggestions`); `CRON_REGISTRY` now matches.
- Chat 5.12 TD27: the daily purge writes its heartbeat under `cron_name="purge_news_bodies"`, matching its `CronSpec`.
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
                                                     (master_todo #7 SHIPPED Chat 5.10:
                                                      recorded_with_warning on recompute fail)
PATCH  /portfolio/holdings/{isin}                    Holding (notes/thesis/stop_loss/target_price/tags only)
POST   /portfolio/holdings/{isin}/sell               Holding OR {message, realized_total}
                                                     (master_todo #5 SHIPPED Chat 5.10: validate_replay)
                                                     (master_todo #7 SHIPPED Chat 5.10:
                                                      recorded_with_warning on recompute fail)
POST   /portfolio/holdings/{isin}/preview-sell       SellPreview
GET    /portfolio/holdings/{isin}/history?days=N     PriceBar[]
GET    /portfolio/holdings/{isin}/transactions       Transaction[]
                                                     (master_todo #6 SHIPPED Chat 5.10: dup handler deleted)
GET    /portfolio/summary                            PortfolioSummary
GET    /transactions/search?...                      {results, total}
                                                     (master_todo #18 SHIPPED Chat 5.13: dropped $options:i;
                                                      case-sensitive prefix uses the (symbol, trade_date) index)
GET    /transactions/{id}                            Transaction
PATCH  /transactions/{id}                            Transaction (requires reason)
                                                     (master_todo #4 SHIPPED Chat 5.10: write-before-apply)
DELETE /transactions/{id}                            {deleted: true} (requires reason)
                                                     (master_todo #4 SHIPPED Chat 5.10: write-before-apply)
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
                                                     (master_todo #17 SHIPPED Chat 5.13: ISIN pattern validator)
                                                     (master_todo #26: direction-aware relabel)
GET    /suggestions/{isin}/audit?limit=N             MonitoredStocksAuditEntry[]   (F10)
                                                     (master_todo #17 SHIPPED Chat 5.13: ISIN pattern validator)
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
- `{status: "recorded_with_warning", isin, warning}` (TD19, Chat 5.10 — the SELL persisted to the ledger but `recompute_holding` raised; the derived holding may be stale)

The frontend discriminates via type guard on the `_id` field. NOTE (Chat 5.10 open follow-up): the `recorded_with_warning` shape has no `_id`, so the SellSheet currently treats it like the full-exit branch — rare path, frontend handling deferred (out of Phase-2 scope).

## Section 9: Cron registry on EC2

Run `crontab -l` to see current state. Every script below is heartbeat-instrumented via `cron_run()`. The daily `cron_health_check` at 21:00 IST consumes those heartbeats. `CRON_REGISTRY` in `cron_heartbeat_service.py` is the in-code mirror of this schedule — keep both in sync.

Current live crontab (verified 2026-06-02, Chat 5.9 — 9 active lines; Chat 5.12 added a 10th line, the daily news purge at 02:30 IST):

```cron
# Phase 1 crons (heartbeat-instrumented Chat 2)
0 3 * * * cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/refresh_instruments.py >> /home/ubuntu/cron-instruments.log 2>&1
0 19 * * 1-5 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/refresh_prices.py >> /home/ubuntu/cron-prices.log 2>&1
30 19 * * 1-5 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/take_reconciliation_snapshot.py >> /home/ubuntu/cron-reconciliation.log 2>&1
*/15 9-15 * * 1-5 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/refresh_prices_intraday.py >> /home/ubuntu/cron-prices-intraday.log 2>&1

# Phase 2 crons (registered Chat 2 via F5a)
0 6 * * 0 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/refresh_fundamentals.py >> /home/ubuntu/cron-fundamentals.log 2>&1
30 6 * * 0 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/fetch_news_for_universe.py --include-held >> /home/ubuntu/cron-news.log 2>&1

# Sunday 07:00 IST — weekly suggestions, combined buy+sell digest (TD14 SHIPPED Chat 5.9)
0 7 * * 0 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/run_weekly_suggestions.py --direction=both >> /home/ubuntu/cron-suggestions.log 2>&1

45 19 * * 1-5 cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/track_suggestion_outcomes.py >> /home/ubuntu/cron-outcomes.log 2>&1

# F4 cron health monitoring (Chat 2; dual-transport Chat 5 commit 8)
0 21 * * * cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/cron_health_check.py >> /home/ubuntu/cron-health.log 2>&1

# Daily news body purge — 02:30 IST (storage hygiene; master_todo #13 / TD27, SHIPPED Chat 5.12)
30 2 * * * cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/purge_news_bodies.py >> /home/ubuntu/cron-news-purge.log 2>&1
```

CHAT 5.9 CLOSED ONE-TIME EC2 STEPS:
- **TD14 / master_todo #1 SHIPPED**: Part A — the Sunday 07:00 IST line no longer carries `--notify --run-type scheduled` (verified via `crontab -l` on the box; argparse accepts only `--direction` / `--no-notify` / `--skip-dossiers`). Part B — `CRON_REGISTRY` entry renamed `run_weekly_suggestions` → `weekly_suggestions` (commit `c097b473`) so the heartbeat the script writes is actually tracked and the phantom Sunday MISSING alert stops. Optional immediate-recovery digest: `PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/run_weekly_suggestions.py --direction=both` (records as `run_type="scheduled"` — the script hardcodes it).
- **TD10 / master_todo #2 SHIPPED**: the `0 0 * * 0 find ... -size +10M ...` truncation line was verified ABSENT from the live crontab; logrotate confirmed via rotation trail. No edit needed.

CHAT 5.12 CLOSED ONE-TIME EC2 STEP:
- **TD27 / master_todo #13 SHIPPED**: the `30 2 * * *` daily news-purge line was added via `crontab -e` (verified via `crontab -l | grep purge_news_bodies`), redirecting to `/home/ubuntu/cron-news-purge.log`. The script's `CronSpec` is registered in `CRON_REGISTRY` and a manual run was verified against the real `portfolio` DB (purged 1 sentinel, success heartbeat).

`CRON_REGISTRY` (in code) entries (11 total as of Chat 5.12):
- `refresh_instruments`, `refresh_prices`, `refresh_prices_intraday`, `take_reconciliation_snapshot`, `refresh_fundamentals`, `fetch_news_for_universe`, `weekly_suggestions` (renamed from `run_weekly_suggestions` — Chat 5.9 TD14), `track_suggestion_outcomes`, `cron_health_check`, `purge_news_bodies` (NEW Chat 5.12 TD27 — daily 02:30 IST, `expected_weekdays=WEEKDAYS_ALL`), `weekly_suggestions_sell` (idle; kept for topology flexibility)

No silent failures: every cron registration must include log file paths AND heartbeat instrumentation AND a `CronSpec` entry. All three. **Chat 5.9 lesson: the registry name MUST equal the `cron_name` the script writes — a mismatch produces a permanent phantom MISSING even after the cron itself is fixed. Chat 5.12 re-confirmed: `purge_news_bodies`' `CronSpec.cron_name` is byte-identical to the `cron_run("purge_news_bodies")` string the script passes.**

Cron-health dual transport (Chat 5 commit 8): `cron_health_check.py` sends every anomaly batch on TWO independent transports — `push_public("errors", ...)` + `notify.email(subject, html, text)` — and raises (so `cron_run` marks the run as failed) ONLY when BOTH fail. **Chat 5.9 confirmed healthy by inspection: the 21:00 IST email + ntfy are both arriving daily, so there is no second silent failure in dual-transport.** Chat 5.15 note: the email leg now retries a transient Resend 5xx/429 once (30s backoff) inside `notify.email()` before returning `{ok:false}` (TD34) — the dual-transport "raise only when BOTH fail" logic is unchanged because it still reads `result["ok"]`.

Chat 5.14 note: the Tavily daily quota guard (TD33) is exercised in production ONLY through the Sunday 06:30 IST `fetch_news_for_universe.py` run (and any ad-hoc news fetch). It has no HTTP surface, so it is regression-covered at deploy time via the import graph (`/health` boot + the `/suggestions` endpoints that import `news_fetcher` → `tavily_client`), not via a curl against the guard itself.

### Open scheduling work (NEW Chat 5.9 — tracked in master_todo)
- **TD21 / master_todo #46 (registry-generated crontab migration)**: deferred scheduler architecture work. `CRON_REGISTRY` gains a parseable cron expression per `CronSpec` → `scripts/render_crontab.py` renders a committed `ops/crontab` → `deploy.sh` installs it + a drift-validation step (`crontab -l` diff vs rendered). Version-controls the schedule and makes TD14-class drift structurally impossible, while keeping process isolation + deploy-safety (chosen over in-process APScheduler, which on the t3.micro's 1 GB RAM would let the ~5-min Sunday dossier run compete with the live API and die on every `systemctl restart`). Update the F4 "no silent failures" triad above when it lands. Its own dedicated chat.
- **TD22 / master_todo #47 (`track_suggestion_outcomes` daily FAILURE)**: this weekday 19:45 IST cron has been FAILING every day (0 success / 1 failure), which is what fires the 21:00 IST health email every evening — separate from TD14. Root-cause + fix pending in a future ops chat.

## Section 10: Settings and environment variables

Configured in `app/config/settings.py` via pydantic-settings. All required unless marked default.

### Anthropic
- `ANTHROPIC_API_KEY` (required)
- `ANTHROPIC_MODEL_PRIMARY` (default `"claude-sonnet-4-5"`)
- `ANTHROPIC_MODEL_FAST` (default `"claude-haiku-4-5"`)

### MongoDB
- `MONGODB_URI` (required) — URL-encode special chars in the password
  - **Note (master_todo #16, SHIPPED Chat 5.13 / TD30):** earlier versions of this section said `MONGODB_URL`. Code uses `MONGODB_URI`. Confirmed at HEAD `090d96c` and the master_todo row closed.
- `MONGODB_DB_NAME` (required) — the live value is `portfolio` (NOT `portfolio_advisor`). Confirmed Chat 5.12 at HEAD (`settings.MONGODB_DB_NAME: str = "portfolio"`); a mongosh verification must `getSiblingDB("portfolio")`.

### Tavily
- `TAVILY_API_KEY` (required)
- `TAVILY_DAILY_CALL_LIMIT` (default 200) — hard ceiling on `calls_today` per UTC day. Enforced atomically as of Chat 5.14 (TD33); see Section 7 `tavily_quota` + Section 12.
- `TAVILY_SEARCH_DEPTH` (default `"basic"`)
- `TAVILY_MAX_RESULTS_PER_QUERY` (default 5)

### Email (Resend)
- `RESEND_API_KEY` (required)
- `RESEND_FROM` (e.g., `"advisor@your-domain.com"`)
- `RESEND_TO` (default recipient for `notify.email()`)
- `DIGEST_TO` (digest recipient; may equal `RESEND_TO`)
- (No new env for the Chat 5.15 TD34 retry — the retry count / backoff / transient-status set are module-level constants in `notify.py`, not env-configurable, mirroring the project's "constants intentionally not env-configurable" convention.)

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
  - **RESOLVED Chat 5.10 (master_todo #4 / TD16):** the transactions router now does audit-then-apply (`log_change` before `update_one`), with `validate_replay` run first so a rejected change writes no audit row.
- `recompute_holding(isin)` is the only authoritative writer to `holdings`. Idempotent. Recomputes from `transactions` from scratch using FIFO. Never write directly to `holdings`.
- `recompute_holding(isin)` is serialized per-ISIN via a `recompute_locks` advisory doc (TD20 / master_todo #8, Chat 5.10) so concurrent same-ISIN writes can't interleave their read-replay-overwrite cycles. The lock lives at the service layer, covering API handlers AND out-of-process scripts. Different ISINs never contend.
- `validate_replay(transactions)` rejects any timeline producing negative quantity. It takes the FULL per-ISIN timeline (existing non-deleted transactions + the proposed one). Both PATCH and DELETE on `/transactions/{id}` call this before applying.
  - **RESOLVED Chat 5.10 (master_todo #5 / TD17):** `/portfolio/holdings/{isin}/sell` and the `add_manual_transactions.py` SELL path now call `validate_replay`; a backdated SELL that would go negative mid-timeline 400s (API) / aborts with RuntimeError (script) BEFORE the ledger write, instead of being only logged as an oversell warning by `_fifo_replay`.
- `holdings.deleted_at = None` filter is universal.
- Cost basis is IT-Act-correct, not broker-nominal.
- `prices_intraday` writes are append-only within a day. **Chat 5.11 (master_todo #9 / TD23): `_intraday_row_from_df` now drops a holiday-stale bar (latest 5m bar's IST date != today's IST date → return None), so a market-holiday quote never gets written or surfaced as a "current price".** Chat 5.12 (TD26): a 90-day `captured_at_ttl` now bounds this append-only collection; it works because `captured_at` is written as a BSON Date.
- Symbol search (`GET /transactions/search`) is case-sensitive by construction: the input is uppercased (`symbol.upper()`) and symbols are stored uppercase, so the prefix regex carries NO `$options:i` and uses the `(symbol, trade_date)` index. **Chat 5.13 (master_todo #18 / TD32): the redundant `"i"` flag was dropped; do not reintroduce it (it disables the index).**
- ICICI portfolio display shows TMPV ~₹813 and TMCV ~₹253 — cosmetically wrong vs our tax-correct numbers; does not affect actual money or tax filing.
- Chat 5.6 robustness: `preview_sell` correctly folds SPLIT/BONUS adjustments into the lot walk.

## Section 12: Phase 2 INVARIANTS

- `suggestion_runs` are append-only.
- `tavily_quota` is one doc per UTC day with `$inc` counters. Hard ceiling on `calls_today` enforced (`credits_today` tracked, not capped). **Chat 5.14 (master_todo #19 / TD33): enforced ATOMICALLY via a single `find_one_and_update` guarded by `calls_today < TAVILY_DAILY_CALL_LIMIT`; the cap-hit is detected by a `DuplicateKeyError` on the unique `date_unique` index (the upsert can't insert a second same-day doc) and surfaced as `TavilyQuotaExceeded`. No TOCTOU window; the prior check-then-act pre-check in `search()` was removed.**
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
- **Chat 5.13 (master_todo #17 / TD31)**: the ISIN `Path()` params on `GET /suggestions/{isin}/audit` and `POST /suggestions/{isin}/feedback` carry `pattern=r"^[A-Z0-9]{12}$"` alongside `min_length=12, max_length=12`, so a malformed ISIN 422s at the boundary before reaching `monitored_stocks` / the audit collection.

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
- All Resend traffic flows through `notify.email()`. **master_todo #20 SHIPPED Chat 5.15 (TD34): `email()` now retries ONCE (2 attempts total) on a transient HTTP 429/5xx with a 30s blocking backoff before returning; 400s and any other client/no-status error return immediately (no retry). The `{ok, id, error}` return contract and the swallow-exceptions / no-raise guarantee are UNCHANGED — the retry is purely internal — so every caller that branches on `result["ok"]` (`digest_delivery._send_email`, `reconciliation._send_drift_alerts`, `cron_health_check` dual-transport) is untouched. Transient is classified by `_is_transient_email_error()` reading the Resend SDK exception's int status (`.code`/`.status_code`, with `error_type=="rate_limit_exceeded"`→429 fallback); 429 + 5xx retry, everything else (incl. no-status errors like a bare connection reset) does not. Retry count (1) / backoff (30s) / transient-status set are module constants, NOT env-configurable.**

### Chat 5 A3+A4 (CLOSED)
- `SignalScore.raw_value` carries the RAW input that fed normalization.

### Chat 5.5 TD11 (CLOSED)
- `explainability._build_signal_meta` falls back to `_to_float(sig["raw_value"])` rendered via `_format_raw(meta["formatter_kind"], raw)` when `fundamentals_field is None` AND `available is True`.

### Chat 5 commit 8 (CLOSED) — cron-health dual transport
- Dual-transport ntfy + email. Raises only when BOTH fail. Confirmed healthy Chat 5.9. (Chat 5.15: the email leg inherits the TD34 transient retry; "raise only when both fail" still reads `result["ok"]`, unchanged.)

## Section 13: Shipped vs Open

### Shipped through this point

Phase 1 (all shipped, all locked):
- Holdings dashboard with day-gain coloring
- FIFO cost basis with fee allocation and precision
- ICICI Order Book import → staging → reconcile → promote pipeline
- Manual transaction entry for IPOs, demergers, bonuses, splits (Chat 5.10: manual SELL path now validate_replay-guarded)
- Transaction edit/delete with mandatory reason + audit log (Chat 5.10: reordered to write-before-apply / audit-then-apply, master_todo #4)
- Transaction search (Chat 5.13: case-sensitive prefix uses the (symbol, trade_date) index, master_todo #18)
- Preview-sell endpoint (Chat 5.6 hardened SPLIT/BONUS handling)
- Reconciliation snapshots (manual + auto) with drift detection
- Cost basis adjustments (TMPV/TMCV demerger seeded)
- EOD + intraday price refresh (Chat 5.11: intraday holiday-guarded, master_todo #9; Chat 5.12: 90-day TTL on prices_intraday, master_todo #12)
- Tax view vs broker view in portfolio summary
- Single-holding drill-down page with chart, transactions, notes panel (Chat 5.13: notes-panel mutations use refetchQueries, master_todo #14)
- Audit log page
- Dark mode toggle
- Reconciliation badge in header
- Recent activity card
- Global refresh button (Chat 5.13: uses refetchQueries, master_todo #14)

Phase 2 Suggestions Engine:
- Unit 1: foundations
- Unit 2: news fetch + Haiku classify, Sonnet dossier generator
- Unit 3: outcomes, performance, frontend page
- Commit A (backend explainability)
- Commit A.5 (feedback correctness)
- Commit A.5.1 (re-label correctness)
- Commit B (frontend explainability)
- Suggestions feedback/audit endpoints (Chat 5.13: ISIN charset pattern validators, master_todo #17)
- Tavily news-search quota tracking (Chat 5.14: daily call ceiling enforced atomically, master_todo #19)

Cross-cutting infrastructure:
- Transactional email via `notify.email()` (Chat 5 A2; Chat 5.15: transient 5xx/429 retried once with 30s backoff, master_todo #20)

Chat 2 (F4 + F5a) — Cron observability shipped 2026-05-16.
Chat 3 (F6 + F5b + F10) — Stateful feedback shipped 2026-05-17.
Chat 4 (F2b + F14 + F2 backend + F2 frontend) — Sell-side fully shipped 2026-05-17/18/20.
Chat 5 (Audit + cleanup) — fully SHIPPED 2026-05-24. Eight commits + two manual EC2 steps + one infra step + four doc deliverables.
Chat 5.5 (Small TD cleanup) — TD9 + TD11 + TD12 SHIPPED 2026-05-24; TD10, TD14 carried.
Chat 5.6 (Robustness pass) — Pydantic round-trip + ge=0 + SPLIT/BONUS preview + TD13 doc. Baked into HEAD `c6b1437b` / `4f31b49`.
Chat 5.7 (Doc reconciliation) — Project_State.md full-file refresh, file-map repairs, new URL-at-SHA rule. SHIPPED.
Chat 5.8 (Review + master plan) — comprehensive code review (28 findings: 5 P1, 14 P2, 9 P3); master_todo.md created as canonical task list. SHIPPED. NOTE: the Chat 5.8 doc commit (`8f74b50`) silently truncated Project_State.md by 655 lines (Sections 16-tail through 22) — recovered Chat 5.9.
Chat 5.9 (Phase 1 ops + docs) — SHIPPED 2026-06-02:
- TD14 / master_todo #1: Sunday crontab flag fix (Part A, manual EC2) + `CRON_REGISTRY` rename `run_weekly_suggestions` → `weekly_suggestions` (Part B, commit `c097b473`). Restores the weekly digest and stops the phantom Sunday MISSING alert. Dual-transport health alerts confirmed healthy by inspection.
- TD10 / master_todo #2: verified already satisfied — the redundant `find -size +10M` line was absent from the live crontab and logrotate confirmed working. No edit needed.
- TD15 / master_todo #3: F-number fix registry authored as a new subsection of Section 18 (25 unique in-code F-numbers across two namespaces).
- DOC RECOVERY: restored Section 16 tail + Sections 17–22 that the Chat 5.8 doc commit truncated, from `c6b1437b`.
- Two new items filed: TD21 / master_todo #46 (registry-generated crontab migration), TD22 / master_todo #47 (`track_suggestion_outcomes` daily failure).
Chat 5.10 (Phase 2 — transactions/holdings/audit consistency) — SHIPPED 2026-06-06. Five code commits, all verified on EC2 against localhost:8000:
- TD16 / master_todo #4 (commit `17f9f94`): PATCH + DELETE `/transactions/{id}` flipped to audit-then-apply (`log_change` BEFORE `update_one`). PATCH audits a computed `{**before, **update_fields}` after-state then applies then re-reads for the response. `validate_replay` still runs first, so a rejected edit/delete writes no audit row. Verified: notes PATCH on an active holding returns 200 + 1 audit row (before+after populated); an impossible edit 400s with the audit count unchanged.
- TD18 / master_todo #6 (committed after `17f9f94`, before `5cf3087`): deleted the shadowed EOF `list_transactions` handler in `holdings.py`; `get_holding_transactions` (now ~line 204) is the sole handler for `GET /portfolio/holdings/{isin}/transactions`. Behaviour-neutral. Verified: 0 hits for `def list_transactions`, route returns 200.
- TD17 / master_todo #5 (commit `5cf3087`): `validate_replay` added to `/portfolio/holdings/{isin}/sell` (replays `existing_txns + [proposed_sell]`, 400 before the ledger write) and to `scripts/add_manual_transactions.py` SELL inserts (aborts with RuntimeError). Existing point-in-time `held_qty` check kept for the clearer common-case message. Verified: a backdated SELL on an active holding 400s with the replay reason, holding quantity unchanged, no 2000-dated SELL written.
- TD19 / master_todo #7 (commit `fb23307`): `add_buy` + `sell` wrap `recompute_holding` in try/except; on exception they `log.exception(...)` and return 2xx `{status:"recorded_with_warning", isin, warning}` so the persisted ledger write isn't masked by a recompute failure. `recompute_holding` returning None stays a legitimate full-exit success outside the except. Warning-flag chosen over Mongo M10 multi-doc transactions (user-confirmed: avoids per-step session latency on the single-user box). Verified via fault injection on BOTH paths: ledger row persists despite a forced recompute crash and the caller gets a 2xx warning, not a 500.
- TD20 / master_todo #8 (commit `b34721e`): `recompute_holding` serialized per-ISIN via a `recompute_locks` advisory doc (atomic `insert_one`, `finally` release, 60s TTL reclaim); body renamed `_recompute_holding_impl`. Chosen over `asyncio.Lock` (user-confirmed) because every holdings handler is sync `def` under sync Uvicorn (confirmed at HEAD) and a `threading.Lock` would be blind to the out-of-process scripts. Added `Collections.recompute_locks()` + `acquired_at` TTL index. Verified: 8 concurrent recomputes of one ISIN → exactly 1 correct holding, no thread errors, no leaked lock; lock primitive enforces mutual exclusion (second acquire raises DuplicateKeyError).
- No frontend work. One open follow-up noted (NOT actioned): the SellSheet discriminates on absence of `_id`, so a `recorded_with_warning` response (no `_id`) falls through its non-holding branch — rare failure path, deferred.
Chat 5.11 (Phase 3 — intraday & price correctness) — SHIPPED 2026-06-08. ONE backend code commit `a2806cd`; all three items verified on EC2 against localhost:8000; all touch only `app/services/price_service.py`:
- TD23 / master_todo #9 (P1-4): holiday guard in `_intraday_row_from_df`. The function now reads the latest 5m bar's index timestamp and returns None when its IST date != today's IST date (yfinance `period="1d"` returns the prior trading day's bars on an NSE holiday — a stale bar). Added module-level `IST = timezone(UTC+5:30)` (India has no DST) + `_to_ist()` helper (tz-aware → `astimezone`; tz-naive → treated as UTC first, matching the existing `_df_to_rows` / `annotate_with_current_price` naive→UTC convention); "today" derives from the passed-in `captured_at`. Verified: a today-dated synthetic bar returns a dict, a yesterday-dated bar returns None.
- TD24 / master_todo #10 (P2-14): `price_stale` docstring aligned to code. CODE (`timedelta(days=6)`) chosen canonical (user-delegated); docstring "more than 4 trading days old" → "more than 6 calendar days old" + inline comment noting 6 calendar days ≈ 4 NSE trading days across a weekend. Doc-/comment-only; zero behaviour change.
- TD25 / master_todo #11 (P2-13): `bulk_get_previous_closes` rewritten to per-ISIN `find_one`, delegating to the existing single-ISIN `get_previous_close` (indexed point-query per ISIN) instead of `$push`-ing every price doc per ISIN into an in-memory array and filtering in Python. Eliminates the ~34k-doc pull per dashboard request; Decimal128/Decimal normalization stays in one place. Chosen over an aggregation-pipeline rewrite (evolves existing code, no new query pattern). Verified: bulk result byte-identical to per-ISIN `get_previous_close` for all held ISINs.
- No frontend work. The Chat 5.10 SellSheet `recorded_with_warning` follow-up remains open and untouched (out of Phase-3 scope).
Chat 5.12 (Phase 4 — storage hygiene) — SHIPPED 2026-06-08. Two backend code commits + one EC2 crontab line; both items verified on EC2 against the real `portfolio` DB:
- TD26 / master_todo #12 (P2-3): TTL index on `prices_intraday.captured_at`. Confirmed at HEAD that `_intraday_row_from_df` writes `captured_at` as a BSON Date (`datetime.now(timezone.utc)`), so the TTL actually expires docs. Added `captured_at_ttl` (ASC, `expireAfterSeconds = 90*86400 = 7776000`) alongside the existing non-TTL `captured_at_desc` (ASC vs DESC coexist — mirrors `cron_heartbeats` `started_at_ttl` + `started_at_desc`); `ensure_all_indexes` stays additive. Verified: `getIndexes()` shows the TTL on `{captured_at:1}` with `expireAfterSeconds:7776000`; all four indexes intact.
- TD27 / master_todo #13 (P2-4): new `scripts/purge_news_bodies.py` daily cron (02:30 IST). Corrected the spec — `$unset {body_text:""}` (NOT `body`), age on `fetched_at` (NOT the nullable `published_at`); idempotent filter excludes already-purged docs; stamps `body_purged_at`. Mirrors `refresh_prices_intraday.py` (`cron_run("purge_news_bodies")` heartbeat + `mark_skipped`); adds `--dry-run`. Registered the F4 triad: `CronSpec(cron_name="purge_news_bodies", expected_weekdays=WEEKDAYS_ALL)` (name == `cron_run()` string, TD14 contract) + crontab line `30 2 * * *` with `>> cron-news-purge.log 2>&1`. Verified on EC2 against `portfolio` (a first pass mistakenly seeded `portfolio_advisor` and proved nothing — the app DB is `portfolio`): dry-run 1 candidate, live run purged 1, sentinel `body_text` absent + `body_purged_at` a Date, success heartbeat `metadata.purged:1`, `/cron/heartbeats` `healthy:true`.
- No frontend work. The Chat 5.10 SellSheet `recorded_with_warning` follow-up remains open and untouched (out of Phase-4 scope).
Chat 5.13 (Phase 5 — frontend correctness + quick wins) — SHIPPED 2026-06-08. Spanned BOTH repos: one frontend code commit (frontend HEAD `f59958`) + three backend code commits (deployed code HEAD `090d96c`); all verified on EC2:
- TD28 / master_todo #14 (P2-2): `invalidateQueries` → `refetchQueries` swap in `components/notes-panel.tsx` (the two mutation `onSuccess` calls — `["holding", holding.isin]` + `["dashboard"]`) and `components/refresh-button.tsx` (the three calls inside the existing `await Promise.all([...])` — `["dashboard"]` + `["reconciliation"]` + `["cost-basis"]`). At HEAD the notes-panel calls were lines 42 + 45, the refresh-button calls lines 17-19. Minimal name-swap only (no `async`/`await` reorder — kept to the master_todo text). Aligns these two outliers with the project-wide synchronous-refetch convention. Verified on frontend HEAD `f59958`: `grep invalidateQueries` → 0; `refetchQueries` counts notes-panel:2 + refresh-button:3 = 5; `~/deploy-ui.sh` build clean.
- TD29 / master_todo #15 (P3-3): removed the dead `from pydoc import doc` import (line 6) in `app/routers/holdings.py` — immediately shadowed by local `doc` variables in the serializer helpers. Behaviour-neutral. Verified on backend HEAD `090d96c`: `grep "from pydoc import doc"` → empty.
- TD30 / master_todo #16 (P3-6): doc-drift confirmation — Project_State Section 10 already read `MONGODB_URI` (the correction landed in the Chat 5.12 Project_State, with the explicit master_todo #16 note). Row closed; no code/doc edit beyond stamping SHIPPED.
- TD31 / master_todo #17 (P3-7): added `pattern=r"^[A-Z0-9]{12}$"` (alongside the existing `min_length=12, max_length=12`) to the ISIN `Path()` params on `get_feedback_audit_for_isin` (line 240, GET `/suggestions/{isin}/audit`) and `submit_feedback` (line 260, POST `/suggestions/{isin}/feedback`) in `app/routers/suggestions.py`. `/runs/{run_id}` left alone (ObjectId, not ISIN). Verified on backend HEAD `090d96c`: `grep -F 'pattern=r"^[A-Z0-9]{12}$"'` → 2 matches; 12-char lowercase `INE002a01018` → 422 (pattern, not length); valid `INE002A01018` → 200.
- TD32 / master_todo #18 (P3-8): dropped `"$options": "i"` from the `transactions/search` regex in `app/routers/transactions.py` (the regex was at lines 91-92, not the ~102-115 date-bound block) and corrected the now-false "(case-insensitive)" inline comment. Input is `symbol.upper()` and symbols are stored uppercase, so the match is case-sensitive on purpose and the `(symbol, trade_date)` index is restored. Verified on backend HEAD `090d96c`: `grep '$options'` → empty; clean regex at line 113; `GET /transactions/search?symbol=tr` → `total: 20` (parity).
- No frontend work beyond TD28. The Chat 5.10 SellSheet `recorded_with_warning` follow-up remains open and untouched (out of Phase-5 scope). Optional non-scope touches (notes-panel `async`/`await` reorder; the stale `symbol` `Query(description=… case-insensitive)` wording) were considered and NOT applied — minimal-only.
Chat 5.14 (Phase 6 — external-service hardening, #19) — SHIPPED 2026-06-09. ONE backend code commit `4ac2c95`; backend-only, single file `app/services/tavily_client.py`; verified on EC2 against localhost:8000:
- TD33 / master_todo #19 (P2-5): replaced the Tavily quota check-then-act with an atomic `find_one_and_update`. Collapsed the `get_today_quota()` pre-check + the separate `_increment_quota()` `$inc` into ONE conditional `find_one_and_update` filtered on `{date_utc: today, calls_today: {$lt: TAVILY_DAILY_CALL_LIMIT}}` with `upsert=True`. Under the cap (or first call of the day) the filter matches/upserts and the `$inc` applies atomically; at/over the cap the existing same-day doc no longer matches the filter, so the upsert attempts a second `date_utc==today` insert and the unique `date_unique` index raises `DuplicateKeyError`, caught and surfaced as `TavilyQuotaExceeded` (no credit consumed on refusal). Added `from pymongo.errors import DuplicateKeyError`; removed the now-redundant pre-check block in `search()`. Cap stays calls-only (`credits_today` tracked, not capped) — race fix, not a new ceiling (user-delegated). Callers untouched (`news_fetcher.py` imports only `search`/`TavilyError`/`TavilyQuotaExceeded`, all preserved). Verified on EC2 at backend HEAD `4ac2c95`: `/health` ok/ok (clean Pydantic boot → the new import + refactor loaded), `/suggestions/latest?direction=buy` + `?direction=sell` + `/cron/heartbeats` all 200 (the `tavily_client` import chain via `news_fetcher` is intact). The quota guard has no HTTP surface (only reachable through the Sunday `fetch_news_for_universe.py` cron path), so the curl coverage is deploy + import-graph + boot regression.
- No frontend work (backend-only chat). The Chat 5.10 SellSheet `recorded_with_warning` follow-up remains open and untouched (out of Phase-6 #19 scope).
Chat 5.15 (Phase 6 — external-service hardening, #20) — SHIPPED 2026-06-12. ONE backend code commit `7d77b9c`; backend-only, single file `app/services/notify.py`; verified on EC2 against localhost:8000:
- TD34 / master_todo #20 (P3-4): added a 1-retry (2 attempts total) loop inside `email()` on a transient Resend HTTP 429/5xx with a blocking 30s backoff; 400s and any other client/no-status error return immediately (no retry). Added module-level `import logging` + `import time` + a module logger, two helpers — `_email_error_status()` (reads the SDK exception's int status off `.code`/`.status_code`, falls back to `error_type=="rate_limit_exceeded"`→429) and `_is_transient_email_error()` (True only for 429 + 5xx) — and three module constants (`_EMAIL_MAX_ATTEMPTS=2`, `_EMAIL_RETRY_BACKOFF_SECONDS=30`, `_EMAIL_TRANSIENT_STATUSES`). The `{ok, id, error}` return contract and the no-raise / swallow-exceptions guarantee are UNCHANGED — the retry is purely internal — so all three callers that branch on `result["ok"]` (`digest_delivery._send_email`, `reconciliation._send_drift_alerts`, `cron_health_check` dual-transport) are untouched (re-read all three at HEAD before patching to confirm). `_publish()` / `push_public()` reproduced byte-faithful and unchanged. Retry count (1) / backoff (30s) / blocking-`time.sleep` acceptability were user-delegated; chose the conservative end of the 30–60s window (all real callers are cron paths + the rare manual-reconciliation request; anyio's default 40-thread pool absorbs the single blocked worker on the single-user box). No `Retry-After` parsing (out of scope). Verified on EC2 at backend HEAD `7d77b9c`: `/health` ok/ok + an in-box monkeypatched harness (no real email, no real sleep) — transient 503 → 2 attempts + exactly one 30s backoff → `{ok:false}`; permanent 400 → 1 attempt, no backoff; success → `{ok:true,id,error:null}`; classifier retries 429/500/502/503/504, refuses 400/422 + no-status errors. The probe confirmed the installed `resend>=2.4` raises typed errors (`RateLimitError`/`ApplicationError`/`ResendError`/`ValidationError`/…) carrying status on `.code`.
- No frontend work (backend-only chat). The Chat 5.10 SellSheet `recorded_with_warning` follow-up remains open and untouched (out of Phase-6 #20 scope).

### Chat split plan — SOURCE OF TRUTH is `docs/master_todo.md`

The chat split plan now lives in `docs/master_todo.md`. The table below is a snapshot for context; refer to master_todo.md for the live ordering and status.

| Phase | Items | Chat focus | Status |
|---|---|---|---|
| 1 | master_todo #1-3 | Ops unblock + doc reconciliation (TD14, TD10, TD15) | SHIPPED (Chat 5.9) |
| 2 | master_todo #4-8 | Transactions/holdings/audit invariants (TD16-TD20) | SHIPPED (Chat 5.10) |
| 3 | master_todo #9-11 | Intraday & price correctness (TD23-TD25) | SHIPPED (Chat 5.11) |
| 4 | master_todo #12-13 | Storage hygiene (TD26-TD27) | SHIPPED (Chat 5.12) |
| 5 | master_todo #14-18 | Frontend correctness + quick wins (TD28-TD32) | SHIPPED (Chat 5.13) |
| 6 | master_todo #19-24 | External-service hardening | IN PROGRESS — #19 SHIPPED (Chat 5.14), #20 SHIPPED (Chat 5.15); #21–24 OPEN |
| 7 | master_todo #25-26 | Reconciliation alerting + feedback direction | OPEN |
| 8 | master_todo #27-29 | Chat 6 (F1+F3), Chat 7 (F12+F15), Chat 8 (F13 watchlist) | OPEN |
| 9 | master_todo #30-38 | Cross-cutting cleanup before GO LIVE | OPEN |
| 10 | master_todo #39-41 | Chat 9 pre-launch cleanup (F11 + realized P&L hide + stop_loss) | OPEN |
| 11 | master_todo #42 | Chat 10 GO LIVE (F7 real data import) | OPEN |
| 12 | master_todo #43-45 | Deferred TDs (TD1, TD3, TD7) | DEFERRED |
| — | master_todo #46-47 | NEW Chat 5.9: TD21 scheduler migration, TD22 outcomes-cron failure | OPEN |

### Open items CARRIED FORWARD past Chat 5.15

All open items are tracked in `docs/master_todo.md` with stable item numbers. Cross-references in this file (Sections 5, 6, 7, 8, 9, 11, 12, 18) use the `master_todo #N` form so the next chat can grep across both files.

The highest-priority items per master_todo current position (Phases 1 + 2 + 3 + 4 + 5 closed, Phase 6 #19 SHIPPED Chat 5.14 + #20 SHIPPED Chat 5.15; pointer now at #21):
- **master_todo #21 (P3-5):** persist the suggestion run BEFORE digest formatting; pass `inserted_id` explicitly to `send_combined_digest` (`app/services/digest_delivery.py`). Phase 6 external-service hardening — next.
- **master_todo #22-24:** reject NaN in `_to_decimal`; fallback log on heartbeat-insert failure; harden `cron_health_check.main` against Mongo being unreachable. Phase 6.

## Section 14: Conventions the assistant has repeatedly drifted on

The assistant has confused these multiple times. Memorize them.

- Port 8001 (Mac local), port 8000 (EC2). Always specify which.
- SSH-first for tests: every test block MUST begin with `ssh ubuntu@100.112.20.41` and run curls against `localhost:8000`. (Frontend-only changes test via `~/deploy-ui.sh` + `npm run build`/lint on EC2.)
- Commit-block-after-code: every code/file delivery MUST be followed by a paste-ready `git add .` + `git commit -m` block.
- Project_State.md AND master_todo.md are ALWAYS complete full-file replacements.
- F6 two-mechanism feedback exclusion: `get_excluded_isins` at run-build AND `_build_user_action` at serialization. Both required.
- The 90-day rejected cooldown and 30-day acted soft-exclude are intentionally NOT env-configurable.
- F10 write-before-apply: `monitored_stocks_audit_service.log_change(...)` BEFORE `monitored_stocks.update_one(...)`. **The corresponding invariant for transactions is now satisfied too — master_todo #4 SHIPPED Chat 5.10.**
- Secrets path on EC2 is `/etc/portfolio-advisor/secrets.env`.
- `lib/api.ts` is hand-typed; `lib/api-types.ts` is gitignored.
- Mutations in frontend use `refetchQueries` (synchronous), NOT `invalidateQueries`. **The two known outliers (notes-panel + refresh-button) were swapped to `refetchQueries` in Chat 5.13 (TD28 / master_todo #14); the convention now holds project-wide.**
- `cn` helper at `@/lib/utils`. Format helpers at `@/lib/format`.
- Collections accessor: `from app.db.client import Collections`.
- Decimal128 vs Decimal: helpers in `app/models/_common.py`.
- Datetimes: UTC-naive in Mongo. IST in UI. `utcnow()` from `app/models/_common.py`. **Mixed tz-aware usage exists — master_todo #30 + #31 will sweep.**
- Heredoc for multi-line Python: use `<<'EOF'` form.
- Original `SuggestionCard` takes parent-owned mutation. Do not redesign.
- `/suggestions` page uses shadcn Tabs.
- Tailwind v4 + shadcn `.dark` class pickup is automatic.
- Every cron script: `cron_run()` wrapper AND `CronSpec` entry AND crontab line with log redirection. **AND the `CronSpec.cron_name` MUST equal the `cron_name` the script passes to `cron_run()` (Chat 5.9 TD14; re-confirmed Chat 5.12 for `purge_news_bodies`).**
- Direction-aware display layer: branch on direction at the display layer, not by forking the model.
- Symbol search regex is case-sensitive on purpose (input uppercased, symbols stored uppercase); NO `$options:i` (it disables the `(symbol, trade_date)` index). (Chat 5.13 TD32.)
- ISIN `Path()` params validate charset with `pattern=r"^[A-Z0-9]{12}$"` in addition to `min_length/max_length=12`. (Chat 5.13 TD31.)
- Tavily daily quota is enforced ATOMICALLY: one `find_one_and_update` guarded by `calls_today < TAVILY_DAILY_CALL_LIMIT`, cap-hit caught via `DuplicateKeyError` on the unique `date_unique` index. NO check-then-act pre-check. Cap is calls-only; `credits_today` is tracked, not capped. The quota is DAILY (resets 00:00 UTC), not monthly — the README/data_flow prose is stale. (Chat 5.14 TD33.)
- `notify.email()` retries a TRANSIENT Resend failure (HTTP 429 + 5xx) ONCE (2 attempts total) with a 30s blocking backoff; 400s and any no-status error return immediately. The retry is INTERNAL — the `{ok, id, error}` return contract and the swallow-exceptions/no-raise guarantee are unchanged, so callers keep branching on `result["ok"]`. Transient is classified by `_is_transient_email_error()` (reads the SDK exception's int status off `.code`/`.status_code`, fallback `error_type=="rate_limit_exceeded"`). Retry count / backoff / transient-status set are module constants, NOT env-configurable. Do not convert this into a raised-exception path. (Chat 5.15 TD34.)

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

### Chat 5.9 additions
- **A doc-update commit must NEVER shorten Project_State.md without an explicit, stated reason.** The Chat 5.8 doc commit (`8f74b50`) silently truncated the file from 1708 → 1053 lines, amputating the Section 16 tail and Sections 17–22 (including the tech-debt registry TD15 needed). It went undetected for a full chat cycle. Before committing the file, verify it ends with the sentinel `End of PROJECT_STATE.md.` and that the line count is >= the prior commit's (or explain the reduction). Recovery path: `git show <prior-sha>:docs/Project_State.md`.
- **In-code F-numbers live in TWO namespaces that COLLIDE on low numbers.** Feature-F (roadmap tickets: F1 ad-hoc chat, F2 sell-side, F4 cron observability, F14 earnings, …) and "fix (Chat 5.5+)" robustness-F (F1–F82 fix tags) reuse the same integers (F1, F2, F3, F4, F5, F7, F8, F12, F14 all collide). Section 18's F-number fix registry disambiguates via a `Kind` column. NEVER assume a bare `# F2 fix` comment means feature-F2 — read the comment verbatim at HEAD.
- **An "ops-only" item can hide a code bug — fix build-right.** TD14 looked like a one-line crontab edit; fixing the flags alone would have left a permanent phantom MISSING alert because `CRON_REGISTRY` named the job `run_weekly_suggestions` while the script writes `weekly_suggestions`. The registry rename was the other, code-side half.
- **Don't trust a prior chat's count estimate.** Chat 5.7 estimated "~20" F-refs; the real unique in-code count was 25 (the fix-registry subset was 21). Always grep at HEAD before mapping.

### Chat 5.10 additions
- **The transactions PATCH/DELETE write-before-apply order is now LIVE (audit-then-apply).** Mirror it for any future ledger-mutating route: `log_change(...)` BEFORE `update_one(...)`, and run `validate_replay` BEFORE the audit so a rejected change writes no audit row. For PATCH, audit a computed `{**before, **update_fields}` after-state (Decimal128/Decimal stringify identically), then apply, then re-read for the response.
- **`validate_replay` signature is `validate_replay(transactions: list[dict]) -> tuple[bool, str | None]`** — it takes the FULL per-ISIN timeline (existing non-deleted txns + the proposed one), not `(isin, sims)`. It reads qty/price via `_to_decimal`, so mixing a raw proposed dict with stored Decimal128 docs is safe; the `{"deleted_at": None}` filter also matches docs where the field is absent.
- **Every holdings route handler is sync `def` under sync Uvicorn** — confirmed at HEAD. `asyncio.Lock` does NOT serialize sync handlers (they run in threadpool threads). For cross-request mutual exclusion use a Mongo advisory-lock doc (works across threads AND processes) or `threading.Lock` (in-process only). The advisory doc is preferred when out-of-process scripts share the path.
- **`recompute_holding` returning None is a legitimate success (full exit)** — never conflate it with a recompute failure. TD19's try/except catches only exceptions; the `if not holding`/`if not new_holding` None-branch stays outside it.
- **`fetch_metadata` (yfinance_lookup) swallows all exceptions** and returns a safe-default dict, so a first-time recompute on an unknown symbol won't throw through yfinance — useful when constructing deterministic happy-path tests on fake ISINs.
- **When a test grabs "the newest BUY" it can land on an exited/soft-deleted holding** — `validate_replay` then rejects even a notes-only edit (the timeline replays to 0). Seed test data from an ACTIVE holding (`/portfolio/holdings` then its `/transactions`), and use DISTINCT trade dates for BUY-before-SELL so a same-instant ordering ambiguity doesn't false-trip `validate_replay`.

### Chat 5.11 additions
- **India has no DST — IST is a fixed UTC+5:30.** For any IST conversion in backend code use `timezone(timedelta(hours=5, minutes=30))`, NOT a DST-aware zoneinfo lookup. Chat 5.11 added module-level `IST` + `_to_ist()` to `price_service.py`; reuse them rather than re-deriving the offset.
- **`price_service.py`'s tz convention is "treat tz-naive datetimes as UTC first, then convert."** `_df_to_rows`, `annotate_with_current_price`, and now `_to_ist` all follow it. When you add any new tz-aware comparison in this module, match that convention (tz-aware → `astimezone`; tz-naive → `.replace(tzinfo=utc)` first) so the master_todo #31 sweep doesn't have to special-case your code.
- **NSE intraday bars (09:15–15:30 IST) sit comfortably inside one IST calendar day**, so the TD23 `.date()`-level holiday guard is robust even if yfinance's naive-tz interpretation were slightly off — the date comparison can't flip within a single session. Don't over-engineer it into a timestamp-tolerance check.
- **`bulk_get_previous_closes` now delegates to `get_previous_close` per ISIN (TD25).** It is NO LONGER a single aggregation; do not "optimize" it back into a `$push`-everything pipeline — that was the ~34k-doc regression we removed. If you need a true bulk pipeline later, push the `date < latest` filter into Mongo (`$lookup`/`$facet` per ISIN), never pull full per-ISIN history into memory.
- **Deploy lesson (process, not code): a green `/health` + green dashboard endpoints do NOT prove a code change landed.** In Chat 5.11 the dashboard curls returned 200 with populated `day_gain`/`price_stale` while the patch wasn't on the box yet (the deploy `git pull` had been skipped / the change wasn't committed). The only check that actually probed the change was `hasattr(ps, "_to_ist")`. Always include a positive existence/behaviour assertion for the specific new symbol, and confirm `deploy.sh` actually pulled the expected SHA, before trusting "all green."

### Chat 5.12 additions
- A TTL index silently no-ops on a non-Date field. Before adding `expireAfterSeconds`, confirm the target field is written as a BSON Date (a Python `datetime` → pymongo UTC Date), NOT a string or Decimal128. `prices_intraday.captured_at` qualifies because `_intraday_row_from_df` stores `datetime.now(timezone.utc)`. Grep the writer at HEAD before shipping the index.
- A single-field TTL index and a same-field non-TTL index coexist only when their key DIRECTION differs. `captured_at_ttl` is ASC; the pre-existing `captured_at_desc` is DESC — different key patterns, so Mongo keeps both. This is the in-repo precedent (`cron_heartbeats` `started_at_ttl` ASC + `started_at_desc` DESC). Don't drop the desc index to add a TTL; add the ASC TTL alongside it and keep `ensure_all_indexes` purely additive (it has no `drop_index` anywhere).
- The app DB is `portfolio`, NOT `portfolio_advisor`. `settings.MONGODB_DB_NAME` defaults to `"portfolio"`; `Collections.*()` → `get_db()` → `client["portfolio"]`. A mongosh verification MUST `getSiblingDB("portfolio")` — seeding `portfolio_advisor` writes to an empty phantom DB the app never reads (it cost a wasted #13 verification pass this chat). Tell: `cron_heartbeats` was `[]` in `portfolio_advisor` while `/cron/heartbeats` (which reads through the app) showed the runs.
- `news_articles`' bulky field is `body_text`, not `body`. `$unset {body:""}` would silently no-op. Always read the model (`app/models/news.py`) for the real field name before writing a purge/update.
- For a "older than N days" purge, key on `fetched_at` (always present via `default_factory=utcnow`), not `published_at` (nullable). Age-by-published strands every doc with a null publisher date forever.

### Chat 5.13 additions
- **A "~line N" pointer in the scope is a hint, not ground truth — re-read and re-anchor at HEAD.** Every Phase-5 line pointer was off: the `notes-panel` `invalidateQueries` were at 42/45 (scope said 43/46), the `transactions/search` regex was at 91-92 (scope said ~102-115, which is actually the date-bound block), and the two `/suggestions` ISIN Path params were at 240/260. Always grep the real lines before writing a find-and-replace whose `original_text` must match on-disk bytes.
- **A grep that contains regex metacharacters can be self-defeating — use `grep -F` for literal strings.** The first #17 verification used `grep -n 'pattern=r"\^[A-Z0-9]{12}\$"'`; in BRE the `[A-Z0-9]` in the SEARCH pattern matches a single alphanumeric, but the file's character after `^` is a literal `[`, so the grep could never match. The empty result proved nothing. `grep -Fn 'pattern=r"^[A-Z0-9]{12}$"'` returned the true 2 matches.
- **A pass/fail test must DISCRIMINATE the thing under test from pre-existing behaviour.** The first #17 curls (`inE0001a010` 11 chars, `INE0001A01` 10 chars) both 422'd on the pre-existing `min_length=12` — they could not distinguish the new `pattern` from the old length check. The discriminating input is a 12-char string with a lowercase/illegal char (`INE002a01018` → 422 means the pattern landed; 200 would mean only length is enforced).
- **`pydoc.doc` is a real importable name** — `from pydoc import doc` is valid Python that silently shadows nothing harmful but is dead. Don't assume an odd-looking import is a typo; confirm it's unused (immediately reassigned local `doc` vars here) before deleting.
- **Phase boundaries can span both repos.** Phase 5 had #14 in the frontend repo and #15/#17/#18 in the backend repo. Ask for BOTH HEAD SHAs up front, deploy/test each repo with its own harness (`~/deploy-ui.sh` + `npm run build` for frontend; `~/deploy.sh` + `curl localhost:8000` for backend), and assert the specific change landed in each (a green `/health` proves nothing).
- **Keep `min_length`/`max_length` when ADDING `pattern`.** The charset `pattern=r"^[A-Z0-9]{12}$"` already constrains length to exactly 12, but leaving the explicit `min_length=12, max_length=12` is additive (clearer 422 messages, no behaviour change) and matches "evolve existing code, don't redesign." Don't strip the length constraints in the name of dedup.

### Chat 5.14 additions
- **The atomic compare-and-increment idiom on Mongo is "guard in the filter + unique index catches the over-cap upsert."** For a per-period counter with a hard ceiling, express the limit in the `find_one_and_update` filter (`{partition_key: today, counter: {$lt: limit}}`) with `upsert=True`. Under the cap it matches/upserts and `$inc`s atomically; at the cap the existing doc no longer matches, the upsert tries to insert a duplicate partition key, and the UNIQUE index on that key raises `DuplicateKeyError` — which IS the "exhausted" signal. This needs no transaction and no second round-trip. It only works because `tavily_quota` already had a unique `date_unique` index on `date_utc`; verify the unique index exists before relying on this pattern.
- **A check-then-act guard (`find_one` → compare → separate `$inc`) is a TOCTOU race even on a single-process sync-Uvicorn box** — sync handlers run in a threadpool, and any future parallelism (Chat 8 watchlist multiplies fetch volume) makes it exploitable. Collapse read+guard+write into ONE conditional update; don't "fix" it by adding a lock.
- **Docs drifted from code on the Tavily quota: README + data_flow said "monthly", the code is daily.** Project_State Section 7/12 (daily, `TAVILY_DAILY_CALL_LIMIT`, `date_utc`) matched the code; the READMEs did not. When docs disagree, anchor to the source body at HEAD (the read of `tavily_client.py` + `settings.py` + `indexes.py` settled it), and treat the stale doc as a separate cleanup, not a reason to change behaviour.
- **Cap semantics confirmed calls-only:** `calls_today < TAVILY_DAILY_CALL_LIMIT` is the only ceiling; `credits_today` is tracked but uncapped. A hardening/race-fix commit must NOT silently introduce a new credit ceiling — that would be scope creep on a behaviour-preserving change.

### Chat 5.15 additions
- **A retry added "inside" an existing wrapper must preserve the wrapper's return contract AND its exception behaviour — never convert a swallowed error into a raised one.** `notify.email()` already returns `{ok,id,error}` and swallows Resend exceptions; the TD34 retry loops on the transient case but the FINAL outcome is still the same `{ok,id,error}` dict, so the three `result["ok"]` callers (`digest_delivery._send_email`, `reconciliation._send_drift_alerts`, `cron_health_check` dual-transport) needed zero changes. Per the standing convention, all three were re-read at HEAD before patching to confirm they branch on `result["ok"]` (not on a raised exception).
- **Classify transient-vs-permanent off the SDK exception's HTTP status, not the message string.** The installed `resend>=2.4` raises typed errors (`RateLimitError` 429, `ApplicationError`/`ResendError` 5xx+base, `ValidationError`/`MissingRequiredFieldsError` 4xx) carrying the status on `.code`. `_email_error_status()` reads `.code` then `.status_code`, with a string `error_type=="rate_limit_exceeded"`→429 fallback. Only 429 + 5xx retry; a no-status error (e.g. a bare connection reset) is treated as non-transient and returns immediately — staying strictly inside the "transient 5xx/429" scope rather than blindly retrying every exception.
- **A blocking `time.sleep` in `notify.email()` blocks ONE threadpool worker, not the whole app.** Under sync Uvicorn the sync handlers run in anyio's threadpool (default 40 threads), and the real callers are cron paths plus the rare manual-reconciliation request, so a single 30s backoff on the single-user box is acceptable. Chose 1 retry + 30s fixed (conservative end of the 30–60s window) over 2 retries / 60s — a genuine Resend outage isn't saved by a second retry (the `{ok:false}` is logged + the next cron run re-sends), and a longer/extra sleep only blocks a worker longer for marginal coverage.
- **For a destructive-free behaviour-preserving change, prove it with a monkeypatched harness, not a live send.** The #20 verification stubbed `resend.Emails.send` (to raise 503 / 400 / succeed) and `time.sleep` (to record calls without waiting), so the test asserted attempt-count + backoff-count + return shape with no real email and no real 30s wait. A monkeypatch harness is the right tool when the code path has no HTTP surface and a live trigger is expensive/side-effecting (mirrors the Chat 5.14 import-graph coverage reasoning).
- **The retry count / backoff seconds / transient-status set are module constants, NOT env-configurable** — matching the project's standing "operational constants live in code, not settings" convention (the 90-day rejected cooldown, the 30-day acted soft-exclude, the Tavily limit defaulting in code). Don't add `RESEND_RETRY_*` env keys without an explicit decision.

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
- Shipping a test block without `ssh ubuntu@100.112.20.41` first.
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

### Chat 5.9 additions
- **Letting the end-of-chat Project_State.md "update" commit truncate the file.** The single most damaging doc anti-pattern to date: the very commit meant to UPDATE the doc amputated 655 lines. The full-file artifact MUST be verified complete (ends with the sentinel line, line count not silently shrinking) before the user commits it.
- **Mapping F-references from memory or from a prior chat's estimate instead of grepping at HEAD.** Two F-namespaces collide; only a verbatim read of each in-code comment resolves which one a given `# FN` means.
- **Treating an "ops-only / manual EC2" item as code-free.** TD14 carried a hidden code-side half (the registry rename). Re-read the relevant service before declaring an ops item done.

### Chat 5.10 additions
- **Piping `curl -w "\nHTTP=%{http_code}\n"` straight into `jq`** — the trailing `HTTP=...` line isn't JSON and `jq` errors on it (even though it prints the object correctly first). Write the body with `-o /tmp/x.json` and the status via `-w`, then `jq` the file.
- **Asserting on guessed response field names** (e.g. `realized_total`/`status` on the SELL happy path) instead of dumping the raw body first to read the real keys.
- **Same-timestamp BUY+SELL in a replay test** — the ambiguous chronological sort can place the SELL at/before the BUY, so `validate_replay` reports "0 available" and TD17 rejects a path you meant to exercise. Use distinct dates.
- **Pasting a long Python heredoc into an SSH session and having it truncate mid-block** — write the script to a file (`cat > /tmp/x.py <<'PY' … PY`) then run the file, rather than streaming a 30-line heredoc through the terminal.
- **Building a full-file Project_State.md / master_todo.md from Glean's sentence-wrapped raw read** — Section 19 guard: anchor on a user-pasted `git show` byte-exact source.

### Chat 5.11 additions
- **Trusting green dashboard endpoints as proof a code change deployed.** In Chat 5.11 the first test run looked partly green (`/health` ok, `/portfolio/holdings` 200 with populated `day_gain`/`price_stale`) but the patch wasn't on the box — those endpoints exercise the OLD code paths and prove nothing about the change. The `AttributeError: no attribute '_to_ist'` was the only honest signal. Always assert the specific new symbol exists / behaves, and verify the deploy actually pulled the expected SHA.
- **Skipping `git pull` (or running a curl block before `./deploy.sh`).** A redeploy that doesn't pull leaves stale code with a green health check. Lead every post-deploy test with a SHA / symbol-existence check, not a 200.
- **Reverting `bulk_get_previous_closes` toward a `$push`-everything aggregation in the name of "one query."** That single aggregation WAS the ~34k-doc perf bug (TD25). N indexed point-queries via `get_previous_close` is the intended shape on this single-user box; don't undo it.

### Chat 5.12 additions
- Adding a TTL index without first confirming the target field is written as a BSON Date (it silently no-ops on a string/Decimal).
- Dropping a same-field non-TTL index to "replace" it with a TTL when an ASC-vs-DESC direction split lets both coexist.
- Running a mongosh verification against the wrong database name (`portfolio_advisor` instead of the real `portfolio`) and concluding the code is broken when the test harness was.
- `$unset`-ing a guessed field name (`body`) instead of the real model field (`body_text`).
- Filtering a time-based purge on a nullable date field (`published_at`) instead of the always-present `fetched_at`.

### Chat 5.13 additions
- **Trusting a "~line N" pointer instead of grepping the real line at HEAD.** Every Phase-5 line pointer was off; a find-and-replace anchored on the wrong line would have failed silently or matched the wrong block.
- **Writing a verification grep with regex metacharacters when a literal match is intended.** `grep -n 'pattern=r"\^[A-Z0-9]{12}\$"'` can never match the on-disk line; `grep -Fn` (literal) is the correct tool and returned the true 2 matches. An empty grep is NOT proof of absence when the search pattern itself is malformed.
- **Declaring a validator verified with a test that the pre-existing constraint already explains.** Both first-pass #17 curls 422'd on `min_length=12` alone — they could not distinguish the new charset `pattern`. The discriminating input is a 12-char string with a lowercase/illegal character.
- **Treating a green `/health` (or a single repo's deploy) as proof for a both-repos phase.** Phase 5 spanned both repos; each needed its own deploy + landed-assertion (`grep` for the specific change + a discriminating functional curl/build).

### Chat 5.14 additions
- Replacing a check-then-act race with a lock or a transaction when a single conditional `find_one_and_update` + an existing unique index expresses the same guarantee in one round-trip.
- Adding a new cap (e.g. a credit ceiling) during a race-fix commit that was supposed to be behaviour-preserving.
- Trusting README/data_flow prose ("monthly") over the code (daily) when designing a change to that subsystem.
- Designing the atomic update from the doc-described field names instead of the field names read from the writer at HEAD (`date_utc`, `calls_today`, `credits_today`, `per_use_case.<uc>`).

### Chat 5.15 additions
- **Turning a swallowed-error wrapper into a raised-exception path "while we're in there."** The whole point of `notify.email()`'s `{ok,id,error}` contract is that callers never try/except it. A retry must keep returning that dict on the terminal failure, not start raising — otherwise the three `result["ok"]` callers silently break.
- **Classifying a Resend failure off the exception's message string instead of its HTTP status.** Read the status off the typed SDK exception (`.code`/`.status_code`); the string `error_type` is only a fallback for `rate_limit_exceeded`. A message-substring match ("rate limit", "503") is brittle across SDK versions.
- **Retrying EVERY exception instead of only the transient ones.** A 400 (validation), a missing-API-key error, or a no-status connection error must NOT be retried — a 400 will fail identically on attempt 2 (wasting a 30s sleep), and silently retrying a permanent error hides a real misconfiguration. Scope the retry to 429 + 5xx only.
- **Verifying a behaviour-preserving change with a live side-effecting trigger.** Don't send a real email or wait a real 30s to test the retry; monkeypatch `resend.Emails.send` and `time.sleep` and assert attempt-count + backoff-count + return shape.
- **Adding env knobs for an operational constant.** Retry count / backoff / transient statuses are module constants in `notify.py`, consistent with the project's "constants live in code" convention; don't introduce `RESEND_RETRY_*` settings without an explicit decision.

## Section 16: "I am losing context" — escalation protocol

When the assistant notices ANY trigger, say verbatim:
```
I AM LOSING CONTEXT
```

### Triggers (any one is sufficient)
- Cannot recall a specific file structure that was discussed earlier in the chat
- Conflating Phase 1 facts with Phase 2 facts
- Forgetting which Commit (A, A.5, A.5.1, B) shipped which behavior
- Forgetting which Chat (2, 3, 4, 5, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10, 5.11, 5.12, 5.13, 5.14, 5.15) shipped which feature
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
- **Chat 5.9 trigger: about to commit a Project_State.md full-file artifact that does NOT end with `End of PROJECT_STATE.md.` (silent truncation — the exact failure that lost Sections 17–22 in Chat 5.8).**
- **Chat 5.9 trigger: about to write a Section-18 F-row from a bare in-code `# FN` comment without having read that comment verbatim at HEAD (feature-F vs fix-F namespace collision).**
- **Chat 5.10 trigger: about to ship a 3rd code change in a chat without having re-read the relevant function body at the CURRENT HEAD SHA.**
- **Chat 5.10 trigger: about to write a test block that doesn't start with `ssh ubuntu@100.112.20.41`, or that curls the Tailscale IP instead of `localhost:8000`.**
- **Chat 5.10 trigger: about to recommend `asyncio.Lock` for a sync-`def` handler under sync Uvicorn.**
- **Chat 5.10 trigger: about to update master_todo.md status without also updating the matching Project_State.md Section 18 TD row + Section 13 in the same doc commit.**
- **Chat 5.11 trigger: about to declare a deployed code change verified on the strength of a 200 / green dashboard endpoint, WITHOUT a positive existence/behaviour assertion for the specific new symbol AND a confirmation that the deploy pulled the expected SHA.**
- **Chat 5.11 trigger: about to use a DST-aware tz lookup for IST instead of the fixed UTC+5:30 offset, or about to add a tz comparison in `price_service.py` that ignores the module's naive→UTC convention.**
- **Chat 5.12 trigger: about to add a TTL index without having grepped the writer at HEAD to confirm the field is written as a BSON Date.**
- **Chat 5.12 trigger: about to add a cron whose `CronSpec.cron_name` != the string the script passes to `cron_run()` (TD14 contract).**
- **Chat 5.12 trigger: about to run a mongosh verification against `portfolio_advisor` instead of the real app DB `portfolio`.**
- **Chat 5.12 trigger: about to `$unset` or `$set` a field name not confirmed against the model at HEAD (e.g. `body` vs `body_text`).**
- **Chat 5.13 trigger: about to write a find-and-replace anchored on a "~line N" pointer without having grepped the real line at the current HEAD SHA.**
- **Chat 5.13 trigger: about to declare a change verified on a grep that contains regex metacharacters (use `grep -F` for literals) or on a functional test that the pre-existing constraint already explains.**
- **Chat 5.13 trigger: about to declare a both-repos phase done on the strength of one repo's deploy / a green `/health` without a per-repo landed-assertion.**
- **Chat 5.14 trigger: about to design an atomic Mongo compare-and-increment that relies on a unique index catching the over-cap upsert WITHOUT having confirmed that unique index exists at HEAD (`db.<coll>.getIndexes()` / `app/db/indexes.py`).**
- **Chat 5.14 trigger: about to change a subsystem's behaviour because the README/data_flow prose says X, without having read the code body at HEAD to confirm X (docs drift — Tavily "monthly" vs daily).**
- **Chat 5.15 trigger: about to change `notify.email()` so that a transient failure RAISES instead of returning `{ok:false}` (breaks the three `result["ok"]` callers — re-read them at HEAD first).**
- **Chat 5.15 trigger: about to retry every Resend exception (including 400s / no-status errors) instead of scoping the retry to 429 + 5xx classified off the SDK exception's int status.**
- **Chat 5.15 trigger: about to verify a behaviour-preserving notify change with a live email send / a real `time.sleep` instead of a monkeypatched harness.**

### What "switching chats" means
The user copies the Section 0 bootstrap into a fresh chat. The new chat reads Project_State.md, master_todo.md, both repos at HEAD, `data_flow.md`, READMEs. User states scope. Assistant summarizes back per the Section 0 acknowledgement contract — project understanding, shipped-vs-open per Section 13 + the master_todo current-position pointer, the exact scope of the chat, and any uncertainties — and then WAITS for the user to confirm accuracy before doing anything else. Work resumes from the `master_todo.md` current-position pointer. The previous chat's last act (if it ended on context loss) was to deliver the full-file Project_State.md + master_todo.md update, so the fresh chat always starts from a consistent, verified-complete state.

## Section 17: "Am I hallucinating?" diagnostic questions

Without re-reading, the assistant should be able to answer all of these.

- "What's the backend port on Mac local?" → 8001
- "What's the backend port on EC2?" → 8000
- "How does the assistant SSH into EC2?" → `ssh ubuntu@100.112.20.41`
- "Where do secrets live on EC2?" → `/etc/portfolio-advisor/secrets.env`
- "Where do secrets live on Mac?" → `<repo>/.env`
- "What does `recompute_holding(isin)` do?" → only authoritative writer to `holdings`; idempotent; FIFO from scratch; serialized per-ISIN via a recompute_locks advisory doc (TD20).
- "What's the gating filter on `snapshot_open_outcomes`?" → `tracking_status != "expired"`
- "Where does the dossier `plain_english_summary` field originate?" → `dossier_service.py` `_SYSTEM_PROMPT`, Sonnet, max 500 chars.
- "What is the universe filter in `build_universe`?" → NIFTY 100 ∪ watchlist (after F13) − held − excluded buckets from `get_excluded_isins`.
- "What are the two F6 mechanisms and why both?" → `get_excluded_isins` at run-build (saves Tavily+Sonnet) AND `_build_user_action` at serialization (stale-cache case). Both required.
- "What's the acted soft-exclude window? Env-configurable?" → 30 days. Not env-configurable.
- "What's the F10 write-before-apply rule?" → `log_change(...)` BEFORE `update_one(...)` in `submit_feedback`.
- "What's the Q/V/M/N weight breakdown?" → 30/25/25/20, version `"1.0.0-unit2"`.
- "Is `lib/api-types.ts` checked in?" → No.
- "refetchQueries or invalidateQueries?" → refetchQueries (the two notes-panel + refresh-button outliers were swapped in Chat 5.13 TD28; convention now holds everywhere).
- "Sell endpoint response shape?" → full Holding (partial sell) OR `{message, realized_total}` (full exit) OR `{status:"recorded_with_warning", isin, warning}` (TD19 recompute-failed).
- "Dividend tracking?" → No.
- "When does F7 run?" → Last (Chat 10).
- "How does a cron register?" → `cron_run()` wrapper + `CronSpec` entry + crontab line. All three. AND the `CronSpec.cron_name` must equal the name the script passes to `cron_run()` (Chat 5.9 TD14).
- "Where do F4 cron failure alerts go?" → Both `push_public("errors", ...)` on public ntfy.sh (topic `NTFY_PUBLIC_TOPIC_ERRORS`) AND `notify.email(...)` (dual-transport, Chat 5 commit 8). Raises only when BOTH fail.
- "Heartbeat schema?" → `{cron_name, started_at, finished_at, status, error, metadata, _schema_version: 1}`. TTL 60 days.
- "Healthy/unhealthy rule?" → Healthy iff (not expected today) OR (`success+skipped >= min` AND `failure == 0`).
- "How is PROJECT_STATE.md delivered?" → Always full-file canvas artifact, verified to end with `End of PROJECT_STATE.md.`
- "What must accompany every code/file delivery?" → A paste-ready `git add .` + commit block.
- "How do test blocks start?" → `ssh ubuntu@100.112.20.41`, then curls against `localhost:8000`. (Frontend-only changes: `~/deploy-ui.sh` + `npm run build`/lint.)
- "Is the transactions/search regex case-insensitive?" → No. Input is uppercased, symbols stored uppercase; NO `$options:i` (Chat 5.13 TD32) — it would disable the `(symbol, trade_date)` index.
- "Do the `/suggestions/{isin}` Path params validate charset?" → Yes — `pattern=r"^[A-Z0-9]{12}$"` plus `min_length/max_length=12` (Chat 5.13 TD31).
- "What does `notify.email()` do on a transient Resend error?" → retries ONCE (2 attempts total) on HTTP 429/5xx with a 30s blocking backoff, then returns `{ok,id,error}` as always (never raises). 400s + no-status errors return immediately. Internal retry; contract unchanged (Chat 5.15 TD34).

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
- "Is F2 frontend shipped?" → Yes, verified at frontend SHA `e34e126`; README rewrite at `9edfc8f`; unchanged at HEAD `4f31b49` (Chat 5.13 touched only notes-panel + refresh-button → `f59958`).
- "Is the Q/V/M/N=0 sell-digest cosmetic bug fixed?" → Yes, 2026-05-20 commit `cea8eee`.
- "Is `target_price` consumed anywhere?" → Yes, F2 sell-side `target_price_proximity`. `stop_loss` deferred to Chat 9 (TD6).
- "Has `digest_delivery._send_email` been reconciled with `notify.email()`?" → Yes (Chat 5 A2 part 1).
- "What does `notify.email()` return?" → `{ok: bool, id: str|None, error: str|None}`. Swallows exceptions. Optional `text=`. (Chat 5.15: retries transient 429/5xx once before returning — contract unchanged.)
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
- "What is TD14 and why does it matter?" → Sunday 07:00 IST `run_weekly_suggestions.py` crontab line passed `--notify --run-type scheduled`. NEITHER flag exists on the script's argparse. argparse rejected every Sunday run with a usage error. Cause of missing Sunday digests. SHIPPED Chat 5.9: flags removed (Part A) + `CRON_REGISTRY` renamed `run_weekly_suggestions` → `weekly_suggestions` (Part B) so the heartbeat is tracked and the phantom MISSING stops.
- "Where do `cron-*.log` files live and what happens at 10MB?" → `/home/ubuntu/cron-*.log`. Pre-2026-05-24 a weekly `find ... -size +10M` cron tail-truncated them. Now `/etc/logrotate.d/portfolio-advisor` rotates weekly regardless of size (rotate 4 + compress). The legacy line was TD10; verified already absent + logrotate confirmed Chat 5.9.
- "Why didn't TD12 become a rename?" → Because reading `scripts/seed_nifty100.py` at HEAD showed it does what its name says — downloads `ind_nifty100list.csv` from NSE and marks ~100 instruments. The "top 250" claim was a doc-side hallucination. Lesson encoded in Section 14.

### Chat 5.7 additions
- "What did Chat 5.6 ship?" → A cross-cutting robustness pass at HEAD `64d5ae3`: Pydantic round-trip hardening on Phase-2 models, `ge=0` validators on `Transaction` numeric fields, `holdings_service.preview_sell` SPLIT/BONUS lot-walk fix, and TD13 frontend per-page reference at frontend HEAD `4f31b49`. Cross-cutting F-number references in code comments are tracked as TD15 for reconciliation.
- "What did TD13 ship?" → Frontend README Section 13 — per-page reference for all 7 routes (Dashboard, Holdings drill-down, Transactions, Audit, Reconciliation, Cost Basis, Suggestions) with TanStack Query keys owned, mutations and their fan-out targets, exact backend endpoints, key shadcn primitives, and dark-mode behaviour. Generated at SHA `9edfc8f`, unchanged at HEAD `4f31b49`.
- "What's the canonical tree-listing command and when is it run?" → The block in Section 0 (`git -C <repo> rev-parse HEAD && git ls-tree -r --name-only HEAD` for both repos). The user runs it once per chat immediately after pasting Section 0 and before describing scope.
- "How do you construct a GitHub URL to read a file from source?" → `https://raw.githubusercontent.com/doshisahil95/<repo>/<sha>/<path>`, where `<repo>` is one of the two repo names, `<sha>` is the SHA the user supplied this chat, and `<path>` came from the tree listing. Never the blob URL (`LINK_NEEDS_AUTH` failure mode).

### Chat 5.9 additions
- "What registry name does the Sunday run's heartbeat use?" → `weekly_suggestions` (NOT `run_weekly_suggestions`; renamed Chat 5.9 TD14 to match what the script writes).
- "What flags does `run_weekly_suggestions.py` argparse accept?" → `--direction {buy,sell,both}`, `--no-notify`, `--skip-dossiers`. NOT `--notify` or `--run-type` — `run_type` is hardcoded `"scheduled"`. notify defaults to True.
- "Did the TD14 fix stop the daily 21:00 IST health-email alert?" → No. That daily alert is a SEPARATE failure of `track_suggestion_outcomes` (TD22 / master_todo #47). TD14 only stops the Sunday phantom-MISSING for `weekly_suggestions`.
- "How many in-code F-numbers exist and in how many namespaces?" → 25 unique (app/ + scripts/), in TWO namespaces — feature-F and fix-(Chat 5.5+)-F — disambiguated in the Section 18 F-number fix registry. 9 numbers collide (F1, F2, F3, F4, F5, F7, F8, F12, F14).
- "What's the recovery source if Project_State.md is truncated?" → the prior doc commit via `git show <prior-sha>:docs/Project_State.md`; the last known-complete copy before the Chat 5.8 truncation was `c6b1437b` (1708 lines).
- "Is dual-transport cron-health actually delivering?" → Yes — confirmed Chat 5.9: the 21:00 IST email + ntfy both arrive daily.

### Chat 5.10 additions
- "What order do PATCH/DELETE /transactions/{id} write the audit?" → audit-then-apply (`log_change` BEFORE `update_one`), with `validate_replay` run first. SHIPPED Chat 5.10 (TD16). A rejected edit/delete writes no audit row.
- "Signature of `validate_replay`?" → `validate_replay(transactions: list[dict]) -> tuple[bool, str|None]`; takes the full per-ISIN timeline including the proposed txn.
- "Does `/sell` call `validate_replay`?" → Yes, since Chat 5.10 (TD17), before the ledger write; the `add_manual_transactions.py` SELL path does too (aborts with RuntimeError).
- "What does add_buy/sell return if `recompute_holding` throws?" → 2xx `{status:"recorded_with_warning", isin, warning}` — the ledger write is preserved (TD19). None return is a separate legitimate full-exit success.
- "How is `recompute_holding` serialized?" → per-ISIN advisory doc in `recompute_locks` (`_id==isin`, atomic insert, `finally` release, 60s TTL). NOT asyncio.Lock (handlers are sync). TD20.
- "Are the holdings handlers async or sync?" → sync `def` (confirmed Chat 5.10).
- "New collection added Chat 5.10?" → `recompute_locks` (TD20 advisory locks).

### Chat 5.11 additions
- "What guards `_intraday_row_from_df` against market-holiday bars?" → It reads the latest 5m bar's index timestamp, converts to IST via `_to_ist`, and returns None if that date != today's IST date (TD23 / master_todo #9). yfinance `period="1d"` returns the prior trading day's bars on an NSE holiday.
- "How does `price_service.py` get IST and what's the offset?" → module-level `IST = timezone(timedelta(hours=5, minutes=30))` (fixed; India has no DST) + `_to_ist()` helper (tz-aware → astimezone; tz-naive → treated as UTC first). Added Chat 5.11 (TD23).
- "What's canonical for `price_stale` — docstring or code?" → CODE (`timedelta(days=6)`); the docstring was wrong ("4 trading days") and was aligned to "6 calendar days" Chat 5.11 (TD24). 6 calendar days ≈ 4 NSE trading days across a weekend.
- "How does `bulk_get_previous_closes` work now?" → per-ISIN `get_previous_close` (indexed `find_one({date:{$lt:latest}})` point-query), NOT the old `$push`-everything aggregation that pulled ~34k docs per dashboard load. TD25 / master_todo #11, Chat 5.11.
- "Did Chat 5.11 touch the frontend or any non-price file?" → No. One backend commit `a2806cd`, only `app/services/price_service.py`.
- "How many code commits did Chat 5.11 ship and what SHA?" → ONE, `a2806cd`, carrying all of TD23/TD24/TD25.

### Chat 5.12 additions
- "What's the TTL on `prices_intraday`?" → `captured_at_ttl`, ASC, `expireAfterSeconds = 90*86400 = 7776000` (90 days). Coexists with `captured_at_desc` (DESC). SHIPPED Chat 5.12 (TD26).
- "Why can a TTL and a non-TTL index live on the same field?" → because the key directions differ (ASC TTL vs DESC). Same precedent as `cron_heartbeats` `started_at_ttl` + `started_at_desc`.
- "What makes the `prices_intraday` TTL actually work?" → `captured_at` is a BSON Date (`datetime.now(timezone.utc)`). A TTL no-ops on a string/Decimal field.
- "What's the app's Mongo DB name?" → `portfolio` (`MONGODB_DB_NAME` default). NOT `portfolio_advisor`.
- "Which field does `purge_news_bodies.py` unset and on what age key?" → `$unset {body_text:""}` (NOT `body`) on classified docs whose `fetched_at` (NOT `published_at`) is older than 30 days; stamps `body_purged_at`. Idempotent.
- "What's `purge_news_bodies`'s schedule and heartbeat name?" → daily 02:30 IST (`30 2 * * *`); `cron_run("purge_news_bodies")` with a matching `CronSpec(cron_name="purge_news_bodies")`.

### Chat 5.13 additions
- "refetchQueries or invalidateQueries — any outliers left?" → No outliers. The two known `invalidateQueries` (notes-panel + refresh-button) were swapped to `refetchQueries` in Chat 5.13 (TD28); the convention holds project-wide.
- "Is the transactions/search regex case-insensitive?" → No (Chat 5.13 TD32). Input uppercased + symbols stored uppercase; NO `$options:i` so the `(symbol, trade_date)` index is used. `GET /transactions/search?symbol=tr` returns the same result as uppercase.
- "What validates the ISIN on the two `/suggestions/{isin}` endpoints?" → `pattern=r"^[A-Z0-9]{12}$"` plus `min_length=12, max_length=12` on the `Path()` params of `get_feedback_audit_for_isin` (audit) and `submit_feedback` (feedback) (Chat 5.13 TD31). A 12-char lowercase ISIN 422s.
- "Was the dead `from pydoc import doc` import removed?" → Yes, from `app/routers/holdings.py` line 6 (Chat 5.13 TD29).
- "Was the Section 10 `MONGODB_URL` doc drift fixed?" → Yes — Section 10 reads `MONGODB_URI`; the correction landed in the Chat 5.12 Project_State and the master_todo #16 row was closed as TD30 in Chat 5.13.
- "What SHAs did Chat 5.13 close at?" → frontend code HEAD `f59958` (TD28), backend code HEAD `090d96c` (TD29 + TD31 + TD32); the doc commit advances both past those.

### Chat 5.14 additions
- "How is the Tavily daily quota enforced now?" → A SINGLE atomic `find_one_and_update` in `_increment_quota` filtered on `{date_utc: today, calls_today: {$lt: TAVILY_DAILY_CALL_LIMIT}}` with `upsert=True`. Cap-hit is detected via `DuplicateKeyError` on the unique `date_unique` index and surfaced as `TavilyQuotaExceeded`. No pre-check, no TOCTOU window (Chat 5.14 TD33).
- "Is the Tavily quota daily or monthly?" → DAILY, resets 00:00 UTC. `TAVILY_DAILY_CALL_LIMIT` default 200. The README/data_flow "monthly" wording is stale.
- "Does the Tavily quota cap credits?" → No. Only `calls_today` is capped; `credits_today` is tracked but uncapped (Chat 5.14).
- "What index makes the atomic Tavily claim safe?" → the unique `date_unique` index on `tavily_quota.date_utc` — the upsert can't insert a second same-day doc, so the over-cap path collides instead of double-counting.
- "Did Chat 5.14 touch the frontend or any other file?" → No. ONE backend commit `4ac2c95`, only `app/services/tavily_client.py`.

### Chat 5.15 additions
- "How many attempts does `notify.email()` make, and on what?" → up to 2 (1 retry) on a transient Resend HTTP 429/5xx, with a 30s blocking backoff between them; 400s and no-status errors make exactly 1 attempt. Module constants `_EMAIL_MAX_ATTEMPTS=2`, `_EMAIL_RETRY_BACKOFF_SECONDS=30` (Chat 5.15 TD34).
- "Does the TD34 retry change `notify.email()`'s return contract or raise?" → No. Still `{ok,id,error}`, still swallows exceptions, never raises — the retry is purely internal, so the three `result["ok"]` callers are untouched.
- "How does `email()` decide a Resend error is transient?" → `_is_transient_email_error()` reads the SDK exception's int status off `.code` then `.status_code` (fallback `error_type=="rate_limit_exceeded"`→429); only 429 + 5xx are transient.
- "Is the email retry blocking, and is that OK?" → Yes, a `time.sleep(30)`; it blocks ONE anyio threadpool worker (default pool 40), and real callers are cron paths + the rare manual reconciliation, so it's acceptable on the single-user box.
- "Are the retry count / backoff env-configurable?" → No — module constants in `notify.py`, matching the project's "operational constants live in code" convention.
- "Did Chat 5.15 touch the frontend or any other file?" → No. ONE backend commit `7d77b9c`, only `app/services/notify.py`.

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
| TD1 | `monitored_stocks` direction-agnostic | DEFERRED (master_todo #43) | Decide post-launch |
| TD2 | `docs/data_flow.md` stale | SHIPPED Chat 5 doc deliverable 1/4 (2026-05-23 + 2026-05-24 corrections + Chat 5.5 commit 3 TD12 corrections) | — |
| TD3 | `dossier_service.valuation_verdict` single-string split | DEFERRED (master_todo #44) | Future UI work |
| TD4 | Backend `README.md` stale | SHIPPED Chat 5 doc deliverable 2/4 (2026-05-23 + 2026-05-24 corrections + Chat 5.5 commit 3 TD12 corrections) | — |
| TD5 | Frontend `README.md` missing `/suggestions` route + Suggestions header button | SHIPPED Chat 5 doc deliverable 3/4 (2026-05-23 at frontend SHA `9edfc8f`); per-page reference shipped as TD13 | — |
| TD6 | `holdings.stop_loss` orphan | OPEN — Chat 5 Q3 resolved as "wire it"; deferred to Chat 9 (master_todo #41) | Chat 9 |
| TD7 | `CandidateScore` fixed buy-side group fields | DEFERRED (master_todo #45) | Post-launch |
| TD8 | EC2 self-hosted private ntfy service decommission + code cleanup | SHIPPED — service stopped 2026-05-18; code cleanup commits 7a + 7b (2026-05-23) | — |
| TD9 | Orphan `NTFY_URL` / `NTFY_USER` / `NTFY_PASS` cleanup from `settings.py` + `/etc/portfolio-advisor/secrets.env` | SHIPPED Chat 5.5 commit 1 (2026-05-24) | — |
| TD10 | Remove redundant `0 0 * * 0 log truncation` crontab line (logrotate replaces it as of 2026-05-24) | SHIPPED Chat 5.9 (2026-06-02): verified the `find -size +10M` line was already ABSENT from the live crontab; logrotate confirmed via rotation trail (`cron-*.log.1` 2026-05-31 + `cron-*.log.2.gz` 2026-05-24 for all 10 logs). No crontab edit needed. (master_todo #2) | — |
| TD11 | Wire `explainability._build_signal_meta` to read `sig["raw_value"]` for momentum/news signals + refresh stale comment + reassign news formatter kinds | SHIPPED Chat 5.5 commit 2 (2026-05-24) | — |
| TD12 | Rename `scripts/seed_nifty100.py` (file map flagged as misnamed) | SHIPPED-AS-DOC-FIX Chat 5.5 commit 3 (2026-05-24): the script is correctly named; "top 250" was a hallucination. All four locations corrected. No rename, no code change. | — |
| TD13 | Frontend per-page reference doc (TanStack Query keys, mutation refetch patterns, endpoint-per-route mapping) | SHIPPED Chat 5.6 at frontend SHA `4f31b49` (content generated at `9edfc8f`, unchanged at HEAD). All 7 routes covered in frontend README §13. | — |
| TD14 | Sunday 07:00 IST crontab line passed `--notify --run-type scheduled` to `run_weekly_suggestions.py`; NEITHER flag exists on the script's argparse, so argparse rejected every Sunday run before the heartbeat block — no digest, no heartbeat. AND `CRON_REGISTRY` named the job `run_weekly_suggestions` while the script writes `weekly_suggestions`, producing a phantom Sunday MISSING. | SHIPPED Chat 5.9 (2026-06-02): Part A — bogus flags removed from the Sunday crontab line (manual EC2; verified via `crontab -l`). Part B — `CRON_REGISTRY` entry renamed `run_weekly_suggestions` → `weekly_suggestions` (commit `c097b473`). Dual-transport health alerts confirmed healthy by inspection. (master_todo #1) | — |
| TD15 | F-number fix registry reconciliation. The Chat-5.6 robustness pass left in-code F-references with no row in Section 18. | SHIPPED Chat 5.9 (2026-06-02): authored the "F-number fix registry" subsection below. 25 unique in-code F-numbers (app/ + scripts/, grepped at HEAD `c097b473`) reconciled across two namespaces (feature-F vs fix-Chat-5.5+-F). Chat 5.7's "~20" estimate was low; the fix-registry subset is 21. (master_todo #3) | — |
| TD16 | PATCH/DELETE `/transactions/{id}` was apply-then-audit; must write `transactions_audit` BEFORE applying (mirror the suggestions feedback handler / F10 pattern). | SHIPPED Chat 5.10 (2026-06-06): both handlers now `log_change(...)` BEFORE `update_one(...)`; PATCH audits a computed `{**before, **update_fields}` after-state then applies then re-reads for the response; `validate_replay` still runs first so a rejected edit/delete writes no audit row. Verified on EC2 (200 + 1 audit row on a valid notes edit; impossible edit 400s with audit count unchanged). Commit `17f9f94`. (master_todo #4) | — |
| TD17 | `/portfolio/holdings/{isin}/sell` AND `scripts/add_manual_transactions.py` lacked `validate_replay`; backdated SELLs producing negative quantity were only logged as oversell warnings, not rejected. | SHIPPED Chat 5.10 (2026-06-06): `/sell` replays `existing_txns + [proposed_sell]` and 400s before the ledger write; the manual-import SELL path replays the staging timeline + the proposed SELL and aborts with RuntimeError. Existing point-in-time `held_qty` check kept for the clearer common-case message. Verified: backdated SELL 400s with the replay reason, holding qty unchanged, no row written. Commit `5cf3087`. (master_todo #5) | — |
| TD18 | Duplicate route handler `list_transactions` in `holdings.py`; keep `get_holding_transactions`, delete the dup. | SHIPPED Chat 5.10 (2026-06-06): deleted the shadowed EOF `list_transactions` handler; `get_holding_transactions` (now ~line 204) is the sole handler for `GET /portfolio/holdings/{isin}/transactions`. Behaviour-neutral. Verified: 0 hits for `def list_transactions`, route returns 200. Committed after `17f9f94`, before `5cf3087`. (master_todo #6) | — |
| TD19 | add_buy / sell non-atomic path: a `recompute_holding` failure 500'd the request even though the ledger write had committed. | SHIPPED Chat 5.10 (2026-06-06): both handlers wrap `recompute_holding` in try/except; on exception they `log.exception(...)` and return 2xx `{status:"recorded_with_warning", isin, warning}` so the persisted ledger write isn't masked. None return stays a legitimate full-exit success outside the except. Warning-flag chosen over Mongo M10 multi-doc transactions (user-confirmed: avoids per-step session latency on a single-user box). Added module logger. Verified via fault injection on both BUY and SELL paths (ledger persists, 2xx warning, not 500). Commit `fb23307`. (master_todo #7) | — |
| TD20 | Serialize `recompute_holding` per-ISIN (concurrent same-ISIN writes could interleave their read-replay-overwrite cycles). | SHIPPED Chat 5.10 (2026-06-06): per-ISIN advisory lock — a doc in the new `recompute_locks` collection keyed `_id==isin`, acquired via atomic `insert_one` (unique `_id` index = exactly one winner), released in `finally`, TTL-reclaimed after 60s. Body renamed `_recompute_holding_impl`; the public `recompute_holding` is now the lock wrapper. Chosen over `asyncio.Lock` (user-confirmed) because every holdings handler is sync `def` under sync Uvicorn (confirmed at HEAD) and `threading.Lock` would be blind to the out-of-process scripts. Added `Collections.recompute_locks()` + `acquired_at` TTL index. Verified: 8 concurrent recomputes of one ISIN → exactly 1 correct holding, no leaked lock; mutual exclusion enforced (2nd acquire raises DuplicateKeyError). Commit `b34721e`. (master_todo #8) | — |
| TD21 | Registry-generated crontab migration (NEW Chat 5.9). `CRON_REGISTRY` gains a parseable cron expr → `scripts/render_crontab.py` → committed `ops/crontab` installed by `deploy.sh` + drift validation. Version-controls the schedule, makes TD14-class drift structurally impossible, keeps process isolation + deploy-safety (chosen over in-process APScheduler on the 1 GB t3.micro). Update the F4 "no silent failures" triad in Section 9 when it lands. | OPEN (NEW Chat 5.9) | dedicated chat (master_todo #46) |
| TD22 | `track_suggestion_outcomes` cron FAILS every weekday (19:45 IST; 0 success / 1 failure), firing the 21:00 IST health email daily. Separate from TD14. Root-cause + fix pending. | OPEN (NEW Chat 5.9) | next ops chat (master_todo #47) |
| TD23 | `_intraday_row_from_df` did not guard against yfinance returning the prior trading day's bars on an NSE market holiday (a stale bar) — a holiday-stale quote could be written to `prices_intraday` and surface as a bogus "current price". | SHIPPED Chat 5.11 (2026-06-08): the function now reads the latest 5m bar's index timestamp and returns None when its IST date != today's IST date. Added module-level `IST = timezone(UTC+5:30)` (India has no DST) + `_to_ist()` helper (tz-aware → `astimezone`; tz-naive → treated as UTC first, matching the existing `_df_to_rows` / `annotate_with_current_price` convention); "today" derives from the passed-in `captured_at`. Verified on EC2: today-dated synthetic bar → dict; yesterday-dated bar → None. Commit `a2806cd`. (master_todo #9 / P1-4) | — |
| TD24 | `price_stale` docstring/code mismatch — docstring said "more than 4 trading days old" while the code used `timedelta(days=6)`. | SHIPPED Chat 5.11 (2026-06-08): CODE chosen canonical (user-delegated); kept `timedelta(days=6)` and aligned the docstring "more than 4 trading days old" → "more than 6 calendar days old" + added an inline comment (6 calendar days ≈ 4 NSE trading days across a weekend). Doc-/comment-only; zero behaviour change. Verified `/portfolio/holdings` still returns `price_stale` correctly. Commit `a2806cd`. (master_todo #10 / P2-14) | — |
| TD25 | `bulk_get_previous_closes` `$push`-ed every `{date, close}` for every requested ISIN into an in-memory array (no date filter/limit) then filtered in Python — ~34k price docs pulled per dashboard request. | SHIPPED Chat 5.11 (2026-06-08): rewrote the body to delegate to the existing single-ISIN `get_previous_close` (indexed `find_one({"date": {"$lt": latest}}, sort=[("date",-1)])` point-query per ISIN). Eliminates the ~34k-doc pull; keeps Decimal128/Decimal normalization in one place. Chosen over an aggregation-pipeline rewrite (evolves existing code, no new query pattern; index makes each a point-query). Verified on EC2: bulk result byte-identical to per-ISIN `get_previous_close` for all held ISINs. Commit `a2806cd`. (master_todo #11 / P2-13) | — |
| TD26 | `prices_intraday` had no TTL — an append-only intraday collection (~28 snapshots/holding/day) that would grow unbounded once real ICICI data lands at Chat 10 GO LIVE. | SHIPPED Chat 5.12 (2026-06-08): added `captured_at_ttl` (ASC, `expireAfterSeconds = 90*86400 = 7776000`) to the `prices_intraday` index list in `app/db/indexes.py`. Confirmed at HEAD that `_intraday_row_from_df` writes `captured_at` as a BSON Date (`datetime.now(timezone.utc)` threaded through `insert_intraday_quotes`), so the TTL actually expires docs — a TTL silently no-ops on a string/Decimal field. Kept the existing non-TTL `captured_at_desc` (ASC vs DESC are different key patterns, so both coexist — mirrors `cron_heartbeats` `started_at_ttl` + `started_at_desc`); `ensure_all_indexes` stays purely additive (no drop). Verified on EC2: `db.prices_intraday.getIndexes()` shows `captured_at_ttl` on `{captured_at:1}` with `expireAfterSeconds:7776000`; all four indexes intact. Commit shipped Chat 5.12 (the indexes.py commit preceding deployed HEAD `49bf33f`). (master_todo #12 / P2-3) | — |
| TD27 | `news_articles.body_text` was never purged — the raw article body (only needed until the Haiku classifier has run) would accumulate unbounded. | SHIPPED Chat 5.12 (2026-06-08): new `scripts/purge_news_bodies.py` daily cron (02:30 IST). Field corrections vs the original spec — the bulky field is `body_text` (NOT `body`), and age keys on `fetched_at` (always present via `default_factory=utcnow`; `published_at` is nullable and would strand undated docs). Filter `{classified:True, fetched_at:{$lt: now-30d}, body_purged_at:None, body_text:{$nin:["",None]}}`; write `{$unset:{body_text:""}, $set:{body_purged_at: now}}` (idempotent — re-runs are no-ops). Mirrors `refresh_prices_intraday.py` (`cron_run("purge_news_bodies")` heartbeat, `hb.metadata[...]`, `hb.mark_skipped("no_expired_bodies")`); adds `--dry-run` count-only mode. Registered the F4 triad: `CronSpec(cron_name="purge_news_bodies", ..., expected_weekdays=WEEKDAYS_ALL)` in `CRON_REGISTRY` (name byte-identical to the `cron_run()` string — TD14 contract) + crontab line `30 2 * * *` with `>> cron-news-purge.log 2>&1`. Verified on EC2 against the real `portfolio` DB (NOT `portfolio_advisor` — the app DB is `portfolio`; a first test pass seeded the wrong DB and proved nothing): dry-run reported 1 candidate, live run purged 1, sentinel returned `body_text` absent + `body_purged_at` a Date, success heartbeat `metadata.purged:1`, `/cron/heartbeats` shows `healthy:true, expected_today:true`. Commit `49bf33f` (script + CronSpec) + the EC2 crontab line. (master_todo #13 / P2-4) | — |
| TD28 | `notes-panel.tsx` + `refresh-button.tsx` used lazy `invalidateQueries` instead of the project-wide synchronous `refetchQueries` convention — the two known outliers (Section 14). | SHIPPED Chat 5.13 (2026-06-08): swapped both `invalidateQueries` in `components/notes-panel.tsx` (mutation `onSuccess` — `["holding", holding.isin]` line 42 + `["dashboard"]` line 45) and all three in `components/refresh-button.tsx` (inside the existing `await Promise.all([...])` — `["dashboard"]`/`["reconciliation"]`/`["cost-basis"]` lines 17-19) to `refetchQueries`. Minimal name-swap only (no `async`/`await` reorder — kept to the master_todo text). Verified on frontend HEAD `f59958`: `grep invalidateQueries` → 0; `refetchQueries` counts notes-panel:2 + refresh-button:3 = 5; `~/deploy-ui.sh` build clean. (master_todo #14 / P2-2) | — |
| TD29 | Dead `from pydoc import doc` import in `app/routers/holdings.py` (line 6), immediately shadowed by local `doc` variables in the serializer helpers. | SHIPPED Chat 5.13 (2026-06-08): removed the import. Behaviour-neutral. Verified on backend HEAD `090d96c`: `grep "from pydoc import doc"` → empty. (master_todo #15 / P3-3) | — |
| TD30 | Doc drift — Project_State Section 10 historically said `MONGODB_URL` while the code uses `MONGODB_URI`. | SHIPPED Chat 5.13 (2026-06-08): confirmed at HEAD `090d96c` that the code reads `MONGODB_URI` and that Section 10 already reflected this (the correction landed in the Chat 5.12 Project_State, with the explicit master_todo #16 note). Row closed; doc-only confirmation, no further edit. (master_todo #16 / P3-6) | — |
| TD31 | The two `/suggestions/{isin}` ISIN `Path()` params (`get_feedback_audit_for_isin`, `submit_feedback`) constrained only length (`min_length=12, max_length=12`), not charset — a malformed 12-char ISIN reached Mongo. | SHIPPED Chat 5.13 (2026-06-08): added `pattern=r"^[A-Z0-9]{12}$"` alongside the existing length constraints on both Path params (lines 240 + 260) in `app/routers/suggestions.py`. `/runs/{run_id}` left untouched (ObjectId, not ISIN). Now a malformed ISIN 422s at the boundary. Verified on backend HEAD `090d96c`: `grep -Fn 'pattern=r"^[A-Z0-9]{12}$"'` → 2 matches; 12-char lowercase `INE002a01018` → 422 (charset, not length); valid `INE002A01018` → 200. (master_todo #17 / P3-7) | — |
| TD32 | `GET /transactions/search` prefix regex carried `"$options": "i"` even though the input is uppercased (`symbol.upper()`) and symbols are stored uppercase — the redundant flag disabled the `(symbol, trade_date)` index (forced a COLLSCAN). | SHIPPED Chat 5.13 (2026-06-08): dropped the flag (`query["symbol"] = {"$regex": f"^{escaped}"}`, line 113) in `app/routers/transactions.py` and corrected the now-false "(case-insensitive)" inline comment. The regex was at lines 91-92 (NOT the ~102-115 date-bound block). Case-sensitive on purpose; index restored. Behaviour-neutral for callers. Verified on backend HEAD `090d96c`: `grep '$options'` → empty; clean regex at line 113; `GET /transactions/search?symbol=tr` → `total: 20` (parity). (master_todo #18 / P3-8) | — |
| TD33 | Tavily quota guard was check-then-act: a `get_today_quota()` `find_one` pre-check in `search()` followed by a SEPARATE `_increment_quota()` `$inc` upsert — a TOCTOU window where two callers at `calls_today == limit-1` could both pass the pre-check and push the counter past `TAVILY_DAILY_CALL_LIMIT`. | SHIPPED Chat 5.14 (2026-06-09): collapsed the pre-check + `$inc` into ONE conditional `find_one_and_update` in `_increment_quota` filtered on `{date_utc: today, calls_today: {$lt: TAVILY_DAILY_CALL_LIMIT}}` with `upsert=True, return_document=AFTER` and the existing `$inc`/`$setOnInsert`/`$set` blocks. Under the cap (or the day's first call) the filter matches/upserts and the `$inc` applies atomically; at/over the cap the existing same-day doc no longer matches, the upsert attempts a second `date_utc==today` insert, and the unique `date_unique` index raises `DuplicateKeyError`, caught and surfaced as `TavilyQuotaExceeded` (no credit consumed on refusal). Added `from pymongo.errors import DuplicateKeyError`; removed the redundant pre-check block in `search()`. Cap stays calls-only (`credits_today` tracked, not capped) — race fix, not a new ceiling (user-delegated). Callers untouched. Verified on EC2 at backend HEAD `4ac2c95`: `/health` ok/ok + `/suggestions/latest?direction=buy|sell` + `/cron/heartbeats` all 200 (import chain intact; the guard has no HTTP surface, so coverage is deploy + import-graph + boot regression). Commit `4ac2c955782490818eefa6024c9daead92b0b0eb`. (master_todo #19 / P2-5) | — |
| TD34 | `notify.email()` did not retry transient Resend failures — a one-off 429/5xx (rate-limit / upstream blip) returned `{ok:false}` immediately, so a digest / drift alert / cron-health email could be lost to a momentary glitch that a single retry would have cleared. | SHIPPED Chat 5.15 (2026-06-12): added a 1-retry (2 attempts total) loop inside `email()` on a transient HTTP 429/5xx with a 30s blocking backoff; 400s and any other client/no-status error return immediately. Added `import logging` + `import time` + a module logger, `_email_error_status()` (status off `.code`/`.status_code`, fallback `error_type=="rate_limit_exceeded"`→429), `_is_transient_email_error()` (429 + 5xx only), and constants `_EMAIL_MAX_ATTEMPTS=2`, `_EMAIL_RETRY_BACKOFF_SECONDS=30`, `_EMAIL_TRANSIENT_STATUSES`. The `{ok,id,error}` contract + swallow-exceptions/no-raise guarantee are UNCHANGED, so the three `result["ok"]` callers (`digest_delivery._send_email`, `reconciliation._send_drift_alerts`, `cron_health_check` dual-transport) are untouched (re-read all three at HEAD first). Retry count / backoff / blocking-sleep user-delegated → chose 1 retry + 30s fixed (conservative; real callers are cron paths, anyio's 40-thread pool absorbs one blocked worker). Constants are NOT env-configurable (project convention). Verified on EC2 at backend HEAD `7d77b9c`: `/health` ok/ok + a monkeypatched harness (stubbed `resend.Emails.send` + `time.sleep`, no real email / no real wait) — transient 503 → 2 attempts + one 30s backoff → `{ok:false}`; permanent 400 → 1 attempt, no backoff; success → `{ok:true,id,error:null}`; classifier retries 429/500/502/503/504, refuses 400/422 + no-status. Probe confirmed `resend>=2.4` raises typed errors carrying status on `.code`. Commit `7d77b9cbee9f3155f22c86057b20640f21599ee9`. (master_todo #20 / P3-4) | — |

### F-number fix registry (TD15 deliverable — Chat 5.9)

Reconciles every in-code F-reference grepped at backend HEAD `c097b473` (`app/` + `scripts/` only; `docs/` excluded). 25 unique numbers across TWO namespaces:
- **Feature** — roadmap feature tickets (already documented across Sections 5/7/8/12/13/17/20/22).
- **Fix-5.5+** — "fix (Chat 5.5+)" robustness tags from the Chat 5.6 pass. These REUSE low integers, so they collide with feature numbers on F1, F2, F3, F4, F5, F7, F8, F12, F14.

A bare `# FN` comment is ambiguous until you read it verbatim — use the file:line + Kind below to disambiguate.

| F# | Kind | File(s):line (HEAD c097b473) | One-line description |
|---|---|---|---|
| F1 | Feature | models/monitored_stock.py:4,14,70 | Ad-hoc chat path for suggestions (future Chat 6 / master_todo #27) |
| F1 | Fix-5.5+ | services/reconciliation.py:197 | `utcnow()` helper returns tz-naive UTC to match Mongo write sites |
| F2 | Feature | models/suggestion.py:31,117,123,174,183; routers/suggestions.py; scripts/run_weekly_suggestions.py:3,127 (+~40 sites) | Sell-side direction: `SuggestionDirection`, `--direction`, sign-flip, combined digest |
| F2 | Fix-5.5+ | services/holdings_service.py:344,351,357 | recompute_holding deletes stale soft-deleted holding docs (legacy duplicate-holding bug) |
| F3 | Feature | models/monitored_stock.py:4,14,70 | Ad-hoc chat path for a single holding (future Chat 6 / master_todo #27) |
| F3 | Fix-5.5+ | services/holdings_service.py:82,429,501 | preview_sell/validate_replay apply SPLIT/BONUS to lot qty in place |
| F4 | Feature | settings.py:46; db/client.py:156; db/indexes.py:322; routers/cron.py:1; services/cron_heartbeat_service.py:1,125; services/notify.py:5,67; services/holdings_service.py:82,605,661; scripts/cron_health_check.py:1,150 | Cron observability: heartbeats, CRON_REGISTRY, `/cron/heartbeats`, dual-transport health |
| F4 | Fix-5.5+ | services/holdings_service.py:82,605,661 | validate_replay applies SPLIT/BONUS to lot quantities in place |
| F5 | Feature | (F5a cron registration / F5b acted soft-exclude) services/suggestion_engine.py get_excluded_isins | F5a Phase-2 cron registration; F5b 30-day acted soft-exclude bucket |
| F5 | Fix-5.5+ | services/holdings_service.py:434,470,516; routers/holdings.py:281 | Per-lot realized P&L fee normalization; preview passes `total_fees` through |
| F6 | Feature | models/monitored_stock.py:32,104; routers/suggestions.py:3; services/explainability.py:779,783,814,829,890; services/suggestion_engine.py:120,125,210 | Stateful feedback exclusion (two-mechanism: get_excluded_isins + _build_user_action) |
| F7 | Feature | (roadmap) | Real ICICI data import — sequenced last (Chat 10 / master_todo #42) |
| F7 | Fix-5.5+ | services/price_service.py:161 | Revived dead NaN-guard branch (`hasattr(p,"isnan")` never matched) |
| F8 | Feature | (roadmap) | Dividend tracking — DROPPED (dividends auto-arrive in bank) |
| F8 | Fix-5.5+ | services/price_service.py:533 | NaN drop now covers Open/High/Low, not just Close |
| F10 | Feature | db/client.py:121; db/indexes.py:236; routers/suggestions.py:8,220,229,243,268; services/monitored_stocks_audit_service.py:1 | monitored_stocks write-before-apply audit collection + read endpoints |
| F12 | Feature | (roadmap) | Portfolio risk-summary / concentration (Chat 7 / master_todo #28) |
| F12 | Fix-5.5+ | routers/holdings.py:325 | Fully-exited SELL response includes `realized_total` |
| F13 | Feature | models/monitored_stock.py:5,9,14,83 | Watchlist (reuses monitored_stocks with status="watchlist") (Chat 8 / master_todo #29) |
| F14 | Feature | models/earnings_event.py:1; services/scoring_service.py:30,109,157,265,571; services/suggestion_engine.py:5,472,507; services/fundamentals_service.py:318; services/explainability.py:318 | Earnings calendar + shared earnings-proximity gate (5-day) |
| F14 | Fix-5.5+ | routers/holdings.py:46,63; models/transaction.py:125 | Positivity validators (gt=0) so malformed payloads 422 |
| F16 | Fix-5.5+ | models/reconciliation.py:32,50 | Money alias on money fields → Decimal128↔Decimal on model_validate |
| F17 | Fix-5.5+ | models/reconciliation.py:51 | `_schema_version` BaseDoc-style alias so it actually persists |
| F18 | Fix-5.5+ | models/cost_basis_adjustment.py:47,59 | `amount` Money alias → Decimal128 round-trips via model_validate |
| F19 | Fix-5.5+ | models/cost_basis_adjustment.py:48,73 | `_schema_version` leading-underscore alias (was silently dropped) |
| F20 | Fix-5.5+ | models/instrument.py:16,25 | `populate_by_name=True` + `_id` alias for model_validate(mongo_doc) |
| F21 | Fix-5.5+ | routers/transactions.py:63,79 | `reason` field REQUIRED on PATCH/DELETE |
| F23 | Fix-5.5+ | services/reconciliation.py:190 | Write Decimal128 (not `float(delta_invested)`) into Mongo |
| F27 | Fix-5.5+ | services/news_classifier.py:106,198 | Caller no longer pre-merges id; dropped positional fallback |
| F28 | Fix-5.5+ | services/explainability.py:645,755,811 | `_build_group_meta` accepts direction → emits only that direction's groups |
| F29 | Fix-5.5+ | models/transaction.py:23,58,112 | Money fields `ge=0` + zero-quantity BUY/SELL rejects |
| F79 | Fix-5.5+ | models/symbol_override.py:16,24 | `populate_by_name=True` + `_id` alias |
| F80 | Fix-5.5+ | models/transaction.py:13 | Added three manual-prefixed `source` enum values |
| F82 | Fix-5.5+ | models/transaction.py:80 | Broker reference fields (ICICI ref) written by import |

Notes:
- **F11** (read-only reformatter / capital-gains pack, Chat 9 / master_todo #39) appears only in `docs/`, not in `app/` or `scripts/` at this HEAD — it is a feature ticket with no in-code reference yet, so it is intentionally absent from the in-code table above.
- **F15** (tag views, Chat 7 / master_todo #28) likewise has no in-code reference yet.
- Feature-F rows for the colliding numbers are included for disambiguation only; their authoritative descriptions live in Sections 5/7/8/12/13/17/20/22.

### Fixed in earlier chats (kept for posterity)
- **DIGEST SELL-SIDE Q/V/M/N BUG** — fixed 2026-05-20 in `cea8eee` via direction-aware `_format_score_breakdown`.
- **`track_suggestion_outcomes.py` docstring "Daily 18:30 IST"** — fixed; now generic. (NOTE: the script's daily RUN is currently FAILING — TD22, distinct from this docstring fix.)
- **`top_k` default in CLI docstring "--top-k 5"** — fixed via F2 chunk 6 rewrite of `run_weekly_suggestions.py`.
- **`holdings.target_price` unused** — half-fixed; F2 sell-side `target_price_proximity` signal. `stop_loss` is TD6.
- **`MonitoredStock` schema vs writer drift** — fixed Chat 5 A1 (2026-05-23).
- **Dead `news_article.py`** — deleted Chat 5 A8 (2026-05-23).
- **`digest_delivery._send_email` inline Resend** — fixed Chat 5 A2 part 1 (2026-05-23).
- **All Chat 5 audit items A2-A19 + TD8** — closed Chat 5 2026-05-23/24.
- **Chat 5.5 TD9 + TD11 + TD12** — closed Chat 5.5 2026-05-24 (commits 1, 2, 3).
- **Chat 5.6 robustness pass** — Pydantic round-trip + ge=0 + SPLIT/BONUS preview + TD13. Baked into HEAD `64d5ae3` (backend) / `4f31b49` (frontend). F-number registry reconciled Chat 5.9 (TD15).
- **Chat 5.8 Project_State.md truncation** — the Chat 5.8 doc commit `8f74b50` silently dropped Sections 16-tail through 22 (655 lines); recovered Chat 5.9 from `c6b1437b`. Lesson encoded in Sections 14/15/16/19.
- **Chat 5.10 Phase 2** — TD16 (write-before-apply), TD17 (validate_replay on /sell + manual import), TD18 (dup-handler delete), TD19 (recompute warning-flag), TD20 (per-ISIN recompute lock). All SHIPPED + EC2-verified 2026-06-06. Commits `17f9f94` → `5cf3087` → `fb23307` → `b34721e`.
- **Chat 5.11 Phase 3** — TD23 (intraday holiday guard), TD24 (price_stale docstring alignment), TD25 (bulk_get_previous_closes per-ISIN rewrite). All SHIPPED + EC2-verified 2026-06-08 in one commit `a2806cd`.
- **Chat 5.12 Phase 4** — TD26 (prices_intraday.captured_at 90-day TTL), TD27 (purge_news_bodies daily cron). Both SHIPPED + EC2-verified 2026-06-08. Two code commits (TD26 indexes.py, then TD27 `49bf33f`) + an EC2 crontab line.
- **Chat 5.13 Phase 5** — TD28 (refetchQueries swap, frontend `f59958`), TD29 (dead pydoc import removal), TD30 (MONGODB_URI doc-drift confirmation), TD31 (ISIN charset pattern on the two /suggestions Path params), TD32 ($options:i drop on transactions/search). All SHIPPED + verified 2026-06-08. One frontend commit (`f59958`) + three backend commits (deployed code HEAD `090d96c`).
- **Chat 5.14 Phase 6 (#19)** — TD33 (atomic Tavily quota claim via conditional `find_one_and_update` + unique `date_unique` index catching the over-cap upsert). SHIPPED + EC2-verified 2026-06-09. One backend commit `4ac2c95`, only `app/services/tavily_client.py`.
- **Chat 5.15 Phase 6 (#20)** — TD34 (transient-5xx/429 retry in `notify.email()` — 1 retry / 2 attempts, 30s blocking backoff, 400s + no-status errors not retried; `{ok,id,error}` contract + no-raise guarantee unchanged so the three `result["ok"]` callers are untouched). SHIPPED + EC2-verified 2026-06-12. One backend commit `7d77b9c`, only `app/services/notify.py`.

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
- Section 5/6 — file additions/deletions (diff against the Section-0 tree listing line-by-line)
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

Chat 5.7 added rule: the canonical tree-listing command (embedded in Section 0) MUST be the very first thing run in every new chat, before scope description. The assistant requests it in the acknowledgement message. Every URL the assistant constructs for a file-read MUST use a SHA the user has supplied this chat (not a memory-resident SHA) and a path verified to exist in the tree listing. The URL form is `https://raw.githubusercontent.com/doshisahil95/<repo>/<sha>/<path>`.

Chat 5.9 added rule: the end-of-chat Project_State.md full-file artifact MUST end with the sentinel line `End of PROJECT_STATE.md.` and its line count MUST be >= the prior commit's (or the assistant explicitly states why it shrank) BEFORE the user commits. The Chat 5.8 doc commit silently truncated 655 lines (Sections 16-tail through 22) and it went undetected for a full chat cycle. When a truncation is discovered, recover the lost content from the prior doc commit via `git show <prior-sha>:docs/Project_State.md` (Glean's raw read sentence-wraps long lines — for byte-faithful recovery have the user paste the `git show` output) rather than re-authoring from memory. Since Glean's raw reader wraps, never reconstruct a full-file replacement from a wrapped read; anchor on a user-pasted byte-exact source.

Chat 5.10 added rule: update master_todo.md status AND the matching Project_State.md Section 18 TD row AND Section 13 in the SAME end-of-chat doc commit as the code — never advance one without the others. When a chat ships multiple code commits, the doc commit pins each commit SHA next to its TD row so the audit trail survives. Continue to verify the sentinel + non-shrinking line count (the byte-exact source for this update was the user-pasted `git show b34721e:docs/Project_State.md`, per the Chat 5.9 guard).

Chat 5.11 added rule: the byte-exact source for this doc rebuild was the user-pasted full text of both files (Glean's document reader returns a sentence-wrapped view, which the Section 19 guard forbids anchoring on). When the sandbox/canvas tooling is unavailable mid-rebuild, the full-file replacement is still delivered as a canvas (.md) artifact built from the user-pasted byte-exact source — never from a wrapped read, and never as a patch. All Chat 5.11 doc changes were strictly additive (new TD23–TD25 rows, new Section 13 Chat-5.11 entry, new Chat-5.11 subsections in Sections 14–17 + 20 + 22, price_service annotations in Section 5, the prices_intraday writer note in Section 7, and the Phase-1 intraday invariant in Section 11), so the line count grows vs the prior commit; the sentinel below is preserved.

Chat 5.12 added rule: the byte-exact source for this doc rebuild was the user-pasted full text of both files (Glean's document reader returns a sentence-wrapped view, which the Section 19 guard forbids anchoring on). All Chat 5.12 doc changes were strictly additive (new TD26–TD27 rows, new Section 13 Chat-5.12 entry, new Chat-5.12 subsections in Sections 14–17 + 20 + 22, the indexes.py + cron_heartbeat_service.py + purge_news_bodies.py annotations in Section 5, the prices_intraday TTL + news_articles `body_text` purge notes in Section 7, the 02:30 IST crontab line + 11-entry registry count in Section 9, the `MONGODB_DB_NAME=portfolio` note in Section 10, and the prices_intraday TTL note in Section 11), so the line count grows vs the prior commit; the sentinel below is preserved. Storage-hygiene lessons encoded for posterity: a TTL no-ops on a non-Date field; a same-field TTL and non-TTL index coexist only when their key direction differs; a mongosh verification must target the real app DB `portfolio` (NOT `portfolio_advisor`); the bulky news field is `body_text` (NOT `body`); and a time-based purge keys on `fetched_at` (NOT the nullable `published_at`).

Chat 5.13 added rule: the byte-exact source for this doc rebuild was the user-pasted full text of both files (Glean's document reader returns a sentence-wrapped view, which the Section 19 guard forbids anchoring on). Phase 5 spanned BOTH repos, so Section 4 now pins TWO close SHAs (backend code HEAD `090d96c`, frontend code HEAD `f59958`) and the doc commit advances both. All Chat 5.13 doc changes were strictly additive (new TD28–TD32 rows, new Section 13 Chat-5.13 entry, new Chat-5.13 subsections in Sections 14–17 + 20 + 22, the holdings.py/suggestions.py/transactions.py annotations in Section 5, the notes-panel/refresh-button annotations in Section 6, the transactions search-regex note in Section 7, the /transactions/search + /suggestions endpoint notes in Section 8, the MONGODB_URI TD30 note in Section 10, the case-sensitive-search invariant in Section 11, and the ISIN-pattern invariant in Section 12), so the line count grows vs the prior commit; the sentinel below is preserved. Verification lessons encoded for posterity: a "~line N" pointer is a hint, re-anchor at HEAD; `grep -F` for literal strings (a metacharacter-bearing grep can be self-defeating); a pass/fail test must DISCRIMINATE the change under test from pre-existing constraints; and a both-repos phase needs a per-repo deploy + landed-assertion (a green `/health` proves nothing).

Chat 5.14 added rule: the byte-exact source for this doc rebuild was the user-pasted full text of both files (Glean's document reader returns a sentence-wrapped view, which the Section 19 guard forbids anchoring on). Chat 5.14 was backend-only, so Section 4 pins a new backend close SHA (`4ac2c95`) while the frontend SHA is unchanged. All Chat 5.14 doc changes were strictly additive (new TD33 row, new Section 13 Chat-5.14 entry, new Chat-5.14 subsections in Sections 14–17 + 20 + 22, the tavily_client.py annotation in Section 5, the `tavily_quota` atomic-claim notes in Sections 7 + 12, the Tavily-guard cron note in Section 9, the `TAVILY_DAILY_CALL_LIMIT` note in Section 10), so the line count grows vs the prior commit; the sentinel below is preserved. Lesson encoded for posterity: a per-period hard-ceiling counter is enforced atomically by expressing the limit in the `find_one_and_update` filter and letting a UNIQUE index on the partition key catch the over-cap upsert (`DuplicateKeyError`) — no transaction, no lock, one round-trip; verify the unique index exists at HEAD before relying on it. And when README/data_flow prose contradicts the code (Tavily "monthly" vs daily), anchor to the code body at HEAD.

Chat 5.15 added rule: the byte-exact source for this doc rebuild was the user-pasted `git show HEAD:docs/Project_State.md` + `git show HEAD:docs/master_todo.md` output (Glean's document reader returns a sentence-wrapped view, which the Section 19 guard forbids anchoring on; the blob URL also `LINK_NEEDS_AUTH`'d this chat — the raw URL succeeded for the read, the user paste anchored the rebuild). Chat 5.15 was backend-only, so Section 4 pins a new backend close SHA (`7d77b9c`) while the frontend SHA is unchanged. All Chat 5.15 doc changes were strictly additive (new TD34 row, new Section 13 Chat-5.15 entry + the cross-cutting `notify.email()` shipped bullet, new Chat-5.15 subsections in Sections 14–17 + 20 + 22, the notify.py annotation + the `_send_email`/`cron_health_check`/`reconciliation` "still branches on result['ok']" notes in Section 5, the A2 retry note in Section 12, the dual-transport retry note in Section 9, the "no new env" note in Section 10, the threadpool-blocking note in Section 4 systemd), so the line count grows vs the prior commit; the sentinel below is preserved. Lesson encoded for posterity: a retry added inside a `{ok,id,error}` swallow-exceptions wrapper must keep returning that dict (never raise) so callers branching on `result["ok"]` stay untouched — re-read every caller at HEAD before patching; classify transient off the SDK exception's HTTP status (not the message); scope the retry to 429 + 5xx only; verify a behaviour-preserving change with a monkeypatched harness, not a live side-effecting trigger.

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
- **TD11 minimum-invasive wiring** (vs writing a parallel "raw display layer"): the existing `_format_raw` already had five formatter kinds with a consistent signature. Adding `score_signed` and `count` extends that pattern by ~6 lines total instead of forking a new render path. Total diff: ~30 lines in one file. No frontend change. No model change. No endpoint shape change.
- **TD12 doc-only resolution** (vs rename): reading `seed_nifty100.py` at HEAD showed it does exactly what its name says. The "top 250" claim was a Chat-5 file-map summary hallucination that propagated into four docs. The DOC-ONLY fix preserves the correct name and corrects every wrong claim in one commit.
- **TD14 flagged as a tracked open item rather than silently fixed in Chat 5.5**: the bogus crontab flags are a manual EC2 `crontab -e` change. The assistant cannot edit the live crontab; the user must. Logged so it wasn't lost — SHIPPED Chat 5.9.
- **Project_State.md fetched via raw.githubusercontent.com at SHA** rather than the GitHub blob URL.

### Chat 5.7 additions
- **Tree-listing-first workflow over recall-based file referencing**: Chat 5.7 found the file map listed files that did not exist and omitted files that did. Embedding the canonical `git ls-tree` block in Section 0 eliminates this drift class permanently.
- **Capturing the Chat-5.6 robustness pass in Section 13 + flagging F-number reconciliation as TD15 rather than inventing F-mappings**: inventing entries would have polluted the registry with hallucinated descriptions. Reconciled against ground truth Chat 5.9.
- **Marking TD13 SHIPPED only after verifying the frontend README at HEAD contained the per-page reference**.

### Chat 5.9 additions
- **TD14 fixed build-right (registry rename + crontab flags together) rather than flags-only**: the user explicitly chose "fix it completely." Fixing only the crontab flags would have restored the digest but left a permanent phantom Sunday MISSING alert, because `CRON_REGISTRY` named the job `run_weekly_suggestions` while the script writes `weekly_suggestions`. The rename is the code-side half.
- **Registry-generated crontab (TD21) chosen over in-process APScheduler**: both satisfy "version-control the schedule, stop it being an out-of-band thing." But on the t3.micro's 1 GB RAM, an in-process scheduler would let the ~5-min Sunday dossier run compete with the live API (OOM risk) and would die on every `systemctl restart` deploy. The registry-rendered `ops/crontab` + drift validation keeps process isolation and deploy-safety while making TD14-class drift structurally impossible.
- **Scheduler migration sequenced AFTER restoring the broken digest**: ship the TD14 2-line fix on a working baseline first, then do TD21 as its own chat on top of it — rather than blocking the digest restoration behind a larger architecture change.
- **Project_State.md recovered from `c6b1437b` rather than re-authored from memory**: the Chat 5.8 commit truncated the file mid-word at `Assistant summariz`. Git history (`git log -- docs/Project_State.md` with per-commit line counts) located the last complete copy; the byte-exact tail was recovered from a user-pasted `git show` rather than from the sentence-wrapping raw reader.
- **TD15 mapped only after grepping at HEAD and stopping to scope when the count exceeded the agreed cap**: the count came in at 25 unique (over the 12-item cap), so the assistant reported the count + locations and got an explicit "map all 25" decision before building the table.

### Chat 5.10 additions
- **TD19 warning-flag over Mongo M10 multi-doc transactions**: a `with_transaction` wrapper would add a session + per-step round-trip latency on every synchronous add_buy/sell step, for a failure mode (recompute crash after a committed ledger write) that a 2xx warning surfaces just as safely on a single-user box. The immutable ledger is already the source of truth; the holding is a derived rebuild. (User-confirmed: "multi doc transaction adds latency since each step is synchronous.")
- **TD20 Mongo advisory-lock doc over `threading.Lock` / `asyncio.Lock`**: asyncio.Lock is out (handlers are sync `def` under sync Uvicorn — confirmed at HEAD). threading.Lock would serialize the API process only and is blind to the out-of-process scripts (manual import, order-book promote, reconciliation) that also call recompute_holding. The advisory doc serializes across threads AND processes; the 60s TTL self-heals a crashed holder.
- **TD20 lock placed at the service layer (inside recompute_holding), not the API layer**: covers every caller for free — API handlers AND scripts — with one code site, by renaming the body to `_recompute_holding_impl` and making the public function the lock wrapper.
- **TD16 PATCH audits a computed `{**before, **update_fields}` after-state rather than the DB re-read**: writing the audit BEFORE the apply means the post-apply re-read doesn't exist yet; the computed after-state serializes identically and the response still re-reads from the DB after applying.
- **TD16/TD17 ordering kept validate_replay FIRST (before the audit)**: a rejected edit/delete/sell isn't a real change and must not generate an audit row or a ledger write — so validate → audit → apply.
- **Phase 2 items worked in master_todo order with #6 (dup-handler delete) done right after #4**: the smallest, lowest-risk change cleaned up `holdings.py` before #5 and #7 also edited it, reducing stale line-number drift between reads (user approved the sequencing implicitly by letting each item proceed).

### Chat 5.11 additions
- **TD24: code chosen canonical over the docstring**: `timedelta(days=6)` is what production has run on; "6 calendar days" ≈ "4 trading days" across a weekend was clearly the original intent, so aligning the docstring to the code is the zero-risk, zero-behaviour-change fix. Switching to true trading-day counting would be over-engineering a staleness boolean (rejected).
- **TD25: per-ISIN `find_one` over an aggregation pipeline**: it evolves existing code (delegates to the already-correct `get_previous_close`), the `(isin, date)` index makes each call a single-doc point-query, and the Decimal128/Decimal normalization stays in one place. On a single-user box the N point-queries are trivially cheap; a `$facet`/`$lookup` pipeline would be a new query pattern for no benefit (rejected).
- **TD23: IST resolved as fixed UTC+5:30 with bar-timestamp tz handled defensively**: "today" derives from `captured_at` in IST; the bar timestamp is `astimezone`-converted if tz-aware and treated as UTC-first if tz-naive (the module convention). Because NSE intraday bars sit inside one IST calendar day, the `.date()` comparison is robust to the tz ambiguity — no timestamp-tolerance logic needed.
- **All three Phase-3 items shipped in ONE commit** (`a2806cd`) since they all touch the same file and are individually tiny; the holiday guard + helper, the docstring/comment alignment, and the bulk rewrite were read-at-HEAD then patched together, with a single EC2 verification pass (the `_to_ist` existence check + #11 parity check + dashboard 200s).

### Chat 5.12 additions
- **TD26 ASC TTL kept alongside the existing DESC index, rather than dropping/replacing it** (user-delegated "follow what is the best idea"): `indexes.py` is a create-only, idempotent `ensure_all_indexes` with no `drop_index` anywhere. An ASC TTL and a DESC non-TTL coexist (different key patterns), so the additive path matches the in-repo `cron_heartbeats` precedent (`started_at_ttl` ASC + `started_at_desc` DESC) and avoids introducing the first drop into that function for a marginal write-throughput gain.
- **TD27 purge keys on `fetched_at`, not `published_at`** (user-delegated "figure it out"): `fetched_at` is always present (`default_factory=utcnow`) and monotonic; `published_at` is nullable, so age-by-published would strand undated docs forever. Body purge is about when WE ingested the body, not when the publisher dated it.
- **TD27 scheduled at 02:30 IST** (user-delegated): a quiet pre-dawn slot clear of the 03:00 instruments job and the 19:00–21:00 weekday cluster; nothing else competes for Mongo at that hour.
- **TD27 adds a `--dry-run` count-only mode** despite `refresh_prices_intraday.py` having no argparse: the job is destructive, so a preview path is worth the small divergence from the mirrored script (README convention is "most scripts support `--dry-run`").
- **TD27 verification re-run against the correct DB after the first pass seeded `portfolio_advisor`**: the green path is only meaningful against the real app DB `portfolio`. The contradiction (empty `cron_heartbeats` in `portfolio_advisor` while `/cron/heartbeats` showed the runs) was the tell that exposed the wrong-DB harness bug — fixed by `getSiblingDB("portfolio")`, not by changing code.

### Chat 5.13 additions
- **TD28 minimal name-swap over the `async`/`await`-before-toast reorder** (offered, declined-by-omission): the master_todo text said "swap invalidateQueries → refetchQueries," nothing more. The canonical `/suggestions` pattern makes `onSuccess` async and awaits the refetch before the toast, but adding that here would exceed the item's scope and change toast timing. Kept it to the literal swap; the reorder is noted as an available follow-up, not shipped.
- **TD31 added `pattern` alongside `min_length`/`max_length`, not in place of them**: the charset regex already implies length 12, but leaving the explicit length constraints is additive (clearer 422s, zero behaviour change) and matches "evolve, don't redesign." Stripping them for dedup would have been a needless redesign.
- **TD32 also corrected the inline "(case-insensitive)" comment, not just the flag**: leaving a now-false comment is a future-drift trap. The one-line comment fix rode in the same minimal commit as the `$options` drop.
- **Phase 5 grouped into a per-repo deploy/test boundary**: one frontend commit tested via `~/deploy-ui.sh` + `npm run build`; three backend commits (one per item) deployed together and tested in a single EC2 pass with a discriminating landed-assertion per item — rather than four separate deploy cycles.
- **TD30 closed as a confirmation, not an edit**: the `MONGODB_URL`→`MONGODB_URI` correction had already landed in the Chat 5.12 Project_State; re-editing would have been churn. Verified at HEAD and closed the row.

### Chat 5.14 additions
- **#19 atomic `find_one_and_update` + unique-index collision over a transaction or a lock**: the unique `date_unique` index already existed, so the over-cap path can be made to collide (`DuplicateKeyError`) instead of double-counting — one round-trip, no session latency, no new pattern. An M10 transaction (rejected project-wide for the sync write path, Section 21) or an advisory lock (TD20-style) would both be heavier for a guarantee the existing index already affords.
- **Cap kept calls-only (user-delegated)**: enforcing only `calls_today < TAVILY_DAILY_CALL_LIMIT` preserves the exact boundary the system runs today (200 calls/UTC-day; 201st refused). Adding a `credits_today` ceiling would be a new behaviour smuggled into a race-fix — declined.
- **Pointer advanced to #20 normally, no out-of-band annotation**: the initial acknowledgement was built on a stale cache that showed the pointer at #12; the byte-exact paste confirmed #1–#18 SHIPPED and the pointer already at #19, so #19 was in-order and the bookkeeping is a plain advance to #20.

### Chat 5.15 additions
- **#20 retry kept INSIDE `email()`, preserving `{ok,id,error}`, over a new raised-exception path or a caller-side retry**: the three callers (`digest_delivery`, `reconciliation._send_drift_alerts`, `cron_health_check` dual-transport) already branch on `result["ok"]`; an internal retry leaves all of them untouched, whereas raising would force try/except into every caller and a caller-side retry would duplicate the logic three times. Re-read all three at HEAD to confirm before patching (standing wrapper-contract convention).
- **1 retry + 30s fixed blocking sleep over 2 retries / 60s / `Retry-After` parsing** (all user-delegated): real callers are cron paths plus the rare manual reconciliation, and a transient blip clears on one retry; a genuine outage isn't saved by a second attempt (the `{ok:false}` is logged + the next cron run re-sends), and `Retry-After` parsing is logic the scope didn't ask for. 30s is the conservative end of the 30–60s window; the blocking sleep only stalls one anyio threadpool worker (default 40) on a single-user box.
- **Transient classified off the SDK exception's int HTTP status, not the message**: `_email_error_status()` reads `.code`/`.status_code` (fallback `error_type=="rate_limit_exceeded"`→429); only 429 + 5xx retry. A no-status error (bare connection reset) is treated as non-transient and returns immediately — staying strictly inside the "transient 5xx/429" scope rather than retrying everything.
- **Retry constants in code, not env** (`_EMAIL_MAX_ATTEMPTS`, `_EMAIL_RETRY_BACKOFF_SECONDS`, `_EMAIL_TRANSIENT_STATUSES`): matches the project's "operational constants live in code" convention (90-day cooldown, 30-day soft-exclude, Tavily limit defaulting in code).
- **Verified with a monkeypatched harness (stubbed `resend.Emails.send` + `time.sleep`) over a live send**: the change is behaviour-preserving and the path has no HTTP surface; stubbing lets the test assert attempt-count + backoff-count + return shape with no real email and no real 30s wait (mirrors the Chat 5.14 import-graph coverage reasoning).

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
- In-process application scheduler (APScheduler/lifespan jobs). The schedule stays in crontab; TD21 will version-control it via a registry-rendered `ops/crontab`, NOT by moving job execution into the API process (process-isolation + deploy-safety on the t3.micro).
- Mongo multi-document (M10) transactions on the synchronous write path. Considered and rejected for TD19 — the immutable ledger is the source of truth and a recompute failure is surfaced via a `recorded_with_warning` flag, not rolled back, to avoid per-step session latency on a single-user box. (Chat 5.14 re-affirmed for the Tavily quota: the atomic guarantee comes from a conditional `find_one_and_update` + the unique `date_unique` index, NOT a transaction.)
- DST-aware timezone handling for IST. India observes no DST; IST is a fixed UTC+5:30 (`timezone(timedelta(hours=5, minutes=30))`). Chat 5.11 codified this in `price_service.IST` — do not introduce a zoneinfo/DST lookup.
- Dropping/replacing a same-field index to add a TTL when an ASC-vs-DESC direction split lets both coexist. Chat 5.12 added `captured_at_ttl` (ASC) ALONGSIDE `captured_at_desc` (DESC); `ensure_all_indexes` stays additive with no `drop_index`.
- Case-insensitive symbol search. Symbols are uppercased on input and stored uppercase, so `GET /transactions/search` uses a case-sensitive prefix regex with NO `$options:i` (Chat 5.13 TD32) — an `"i"` flag would disable the `(symbol, trade_date)` index. Do not reintroduce it.
- A `credits_today` ceiling on Tavily. Only `calls_today` is capped (`TAVILY_DAILY_CALL_LIMIT`); credits are tracked for visibility, not enforced. Chat 5.14 deliberately kept the cap calls-only when making the guard atomic — do not add a credit limit without an explicit decision.
- A lock or M10 transaction around the Tavily quota increment. Chat 5.14 (TD33) enforces the ceiling atomically with a single conditional `find_one_and_update` whose over-cap path collides on the unique `date_unique` index; do not "harden" it further with a lock.
- A raised-exception path or env-configurable knobs for `notify.email()`. Chat 5.15 (TD34) added an internal transient-5xx/429 retry that PRESERVES the `{ok,id,error}` swallow-exceptions contract; do not convert it to raise (it would break the three `result["ok"]` callers) and do not add `RESEND_RETRY_*` settings — the retry count (1) / backoff (30s) / transient-status set are module constants by convention.
- `Retry-After`-header-aware backoff for the email retry. Chat 5.15 used a fixed 30s sleep deliberately (scope was "30-60s backoff"); honoring `Retry-After` is extra parsing the scope didn't ask for — add only on an explicit decision.

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
- **`notify.email()` return contract (Chat 5 A2)**: `{ok: bool, id: str|None, error: str|None}`. Swallows Resend exceptions. Optional `text=` for multipart. (Chat 5.15 TD34: retries a transient 429/5xx once with a 30s backoff before returning — contract + no-raise guarantee unchanged.)
- **`notify.email()` transient retry (TD34, Chat 5.15)**: an internal 1-retry / 2-attempt loop on a transient Resend HTTP 429/5xx with a 30s blocking `time.sleep` backoff; 400s + no-status errors return immediately. Transient classified by `_is_transient_email_error()` reading the SDK exception status off `.code`/`.status_code` (fallback `error_type=="rate_limit_exceeded"`→429). Module constants `_EMAIL_MAX_ATTEMPTS=2`, `_EMAIL_RETRY_BACKOFF_SECONDS=30`, `_EMAIL_TRANSIENT_STATUSES`. Purely internal — the `{ok,id,error}` return contract and no-raise guarantee are unchanged, so all `result["ok"]` callers are untouched.
- **`_send_drift_alerts` (Chat 5 A2 part 2)**: `reconciliation.py` helper; ntfy + email dual emit; `sent.append("email")` gated on `result["ok"]`. (Unaffected by the Chat 5.15 retry — still reads `result["ok"]`.)
- **`composite_for_candidate` (Chat 5 A3+A4)**: scoring helper with optional `candidate_signals_for_isin` that wires raw signal inputs into `SignalScore.raw_value`.
- **TD8 ntfy decommission (Chat 5 commits 7a+7b)**: self-hosted ntfy stopped 2026-05-18; `push_private` + `PrivateTopic` + `_NTFY_AUTH` + `b64encode` import + `smoke_test.py` private block all removed 2026-05-23.
- **Cron-health dual transport (Chat 5 commit 8)**: ntfy + email; raises only when BOTH fail. Confirmed delivering daily Chat 5.9. (Chat 5.15: the email leg inherits the TD34 transient retry; "raise only when both fail" is unchanged.)
- **Logrotate (Chat 5 2026-05-24)**: weekly with rotate-4, copytruncate, su ubuntu ubuntu.
- **`_format_raw` formatter kinds (Chat 5.5 TD11)**: existing kinds — `percent_decimal`, `percent_already`, `ratio`, `multiple`, `currency_inr_cr`, `score_only`. NEW kinds — `score_signed` (`f"{raw:+.1f}"`), `count` (`f"{int(raw)}"`).
- **TD9 / TD10 / TD11 / TD12 / TD13 / TD14 / TD15 (Chat 5.5–5.9)**: see Section 18. TD9 / TD11 / TD12 SHIPPED 2026-05-24; TD13 SHIPPED Chat 5.6; TD10 / TD14 / TD15 SHIPPED Chat 5.9.
- **TD16 / TD17 / TD18 / TD19 / TD20 (Chat 5.10)**: see Section 18. All SHIPPED 2026-06-06. TD16 write-before-apply on transactions PATCH/DELETE; TD17 validate_replay on /sell + manual import; TD18 dup-handler delete; TD19 recompute warning-flag; TD20 per-ISIN recompute lock.
- **TD23 / TD24 / TD25 (Chat 5.11)**: see Section 18. All SHIPPED 2026-06-08 in one commit `a2806cd`. TD23 intraday holiday guard (`_intraday_row_from_df`); TD24 `price_stale` docstring aligned to code (6 calendar days canonical); TD25 `bulk_get_previous_closes` rewritten to per-ISIN `find_one`.
- **TD26 / TD27 (Chat 5.12)**: see Section 18. Both SHIPPED 2026-06-08. TD26 `prices_intraday.captured_at` 90-day TTL (`captured_at_ttl`); TD27 `scripts/purge_news_bodies.py` daily cron.
- **TD28 / TD29 / TD30 / TD31 / TD32 (Chat 5.13)**: see Section 18. All SHIPPED 2026-06-08. TD28 `refetchQueries` swap (frontend `f59958`); TD29 dead `pydoc` import removal; TD30 `MONGODB_URI` doc-drift confirmation; TD31 ISIN charset `pattern` on the two `/suggestions/{isin}` Path params; TD32 `$options:i` drop on `transactions/search`.
- **TD33 (Chat 5.14)**: see Section 18. SHIPPED 2026-06-09 in one backend commit `4ac2c95`. Replaced the Tavily quota check-then-act with an atomic `find_one_and_update` in `_increment_quota` (filter `calls_today < TAVILY_DAILY_CALL_LIMIT`, `upsert`), cap-hit detected via `DuplicateKeyError` on the unique `date_unique` index → `TavilyQuotaExceeded`.
- **TD34 (Chat 5.15)**: see Section 18. SHIPPED 2026-06-12 in one backend commit `7d77b9c`. Added a transient-5xx/429 retry (1 retry / 2 attempts, 30s blocking backoff) inside `notify.email()`; 400s + no-status errors not retried; `{ok,id,error}` contract + no-raise guarantee unchanged.
- **`captured_at_ttl` (TD26, Chat 5.12)**: ASC TTL index on `prices_intraday.captured_at`, `expireAfterSeconds = 90*86400 = 7776000`. Coexists with the DESC `captured_at_desc` (different key directions). Works because `captured_at` is written as a BSON Date.
- **Atomic Tavily quota claim (TD33, Chat 5.14)**: `_increment_quota` is a single `find_one_and_update` filtered on `{date_utc: today, calls_today: {$lt: TAVILY_DAILY_CALL_LIMIT}}` with `upsert=True`; under the cap it matches/upserts and `$inc`s atomically, at/over the cap the upsert collides with the unique `date_unique` index (`DuplicateKeyError`) and is surfaced as `TavilyQuotaExceeded`. No pre-check, no TOCTOU window, calls-only cap.
- **`purge_news_bodies` (TD27, Chat 5.12)**: daily 02:30 IST cron (`scripts/purge_news_bodies.py`) that `$unset`s `body_text` and stamps `body_purged_at` on classified `news_articles` whose `fetched_at` is older than 30 days. `cron_run("purge_news_bodies")` heartbeat + matching `CronSpec`. `--dry-run` count-only mode. Idempotent.
- **ISIN charset pattern (TD31, Chat 5.13)**: `pattern=r"^[A-Z0-9]{12}$"` on the `Path()` params of `GET /suggestions/{isin}/audit` (`get_feedback_audit_for_isin`) and `POST /suggestions/{isin}/feedback` (`submit_feedback`), alongside `min_length/max_length=12`. A malformed 12-char ISIN 422s at the boundary.
- **Case-sensitive transaction search (TD32, Chat 5.13)**: `GET /transactions/search` prefix-matches `symbol` with `{"$regex": f"^{escaped}"}` (NO `$options:i`); input is `symbol.upper()` and symbols are stored uppercase, so the `(symbol, trade_date)` index is used.
- **`portfolio` (app DB name)**: the application's MongoDB database is `portfolio` (`MONGODB_DB_NAME` default), NOT `portfolio_advisor`. mongosh verifications must `getSiblingDB("portfolio")`. (Chat 5.12 lesson.)
- **`IST` / `_to_ist()` (Chat 5.11, TD23)**: module-level `IST = timezone(timedelta(hours=5, minutes=30))` (fixed UTC+5:30; India has no DST) and `_to_ist()` helper in `price_service.py` (tz-aware → `astimezone`; tz-naive → treated as UTC first). Used by the intraday holiday guard.
- **`recompute_locks` (TD20, Chat 5.10)**: per-ISIN advisory-lock collection; `_id==isin`, `acquired_at` with 60s TTL; serializes `recompute_holding`. Acquired via atomic `insert_one`, released in `finally`. Accessor `Collections.recompute_locks()`; holder `_per_isin_recompute_lock`.
- **`recorded_with_warning` (TD19, Chat 5.10)**: 2xx status returned by add_buy/sell when `recompute_holding` raises after the ledger write committed. Body `{status, isin, warning}`, no `_id`.
- **`_recompute_holding_impl` (TD20, Chat 5.10)**: the original read-replay-overwrite body of `recompute_holding`, renamed; the public `recompute_holding` is now the per-ISIN lock wrapper around it.
- **`weekly_suggestions` (CRON_REGISTRY name, Chat 5.9 TD14)**: the heartbeat job name the Sunday `run_weekly_suggestions.py` run writes (for both `buy` and `--direction=both`). Renamed from `run_weekly_suggestions` so the health check tracks it. The crontab COMMAND is still `run_weekly_suggestions.py`; only the in-code registry/heartbeat NAME is `weekly_suggestions`.
- **F-number fix registry (Section 18, Chat 5.9 TD15)**: unified table disambiguating the two F-namespaces — feature-F (roadmap) vs fix-(Chat 5.5+)-F (robustness) — which collide on F1/F2/F3/F4/F5/F7/F8/F12/F14.
- **Registry-generated crontab (TD21, NEW Chat 5.9)**: planned schedule-from-CRON_REGISTRY rendering → committed `ops/crontab` + `deploy.sh` install + drift validation. Keeps process isolation; not an in-process scheduler.
- **Chat 5.6 robustness pass**: cross-cutting Pydantic round-trip hardening + `ge=0` validators + `preview_sell` SPLIT/BONUS lot-walk fix + frontend per-page reference. Baked into HEAD `64d5ae3` / `4f31b49`. F-number cross-refs reconciled Chat 5.9 (TD15).
- **Chat 5.7**: Project_State.md doc reconciliation pass — Section 0 URL-construction rule, file-map repairs in Sections 5 + 6, Chat 5.6 capture in Section 13, TD13 SHIPPED, TD15 added.
- **Chat 5.8**: comprehensive code review (28 findings) + `master_todo.md` created as canonical task list. NOTE: its doc commit silently truncated this file (recovered Chat 5.9).
- **Chat 5.9**: Phase 1 ops + docs — TD14 (crontab flags + CRON_REGISTRY rename), TD10 (verified already satisfied), TD15 (F-number fix registry authored). Recovered Sections 16-tail + 17–22 truncated by the Chat 5.8 commit. Filed TD21 (registry-generated crontab) + TD22 (track_suggestion_outcomes daily failure).
- **Chat 5.10**: Phase 2 closed — TD16 (write-before-apply on PATCH/DELETE), TD18 (dup handler delete), TD17 (validate_replay on /sell + manual import), TD19 (recompute warning-flag), TD20 (per-ISIN recompute lock). Five code commits `17f9f94` → `5cf3087` → `fb23307` → `b34721e`. No frontend work; one open SellSheet follow-up noted in Section 6.
- **Chat 5.11**: Phase 3 closed — TD23 (intraday holiday guard + IST/_to_ist helpers), TD24 (price_stale docstring aligned to code), TD25 (bulk_get_previous_closes per-ISIN rewrite). ONE code commit `a2806cd`, only `app/services/price_service.py`. No frontend work; the Chat 5.10 SellSheet follow-up remains open.
- **Chat 5.12**: Phase 4 closed — TD26 (`prices_intraday.captured_at` 90-day TTL in `app/db/indexes.py`), TD27 (`scripts/purge_news_bodies.py` daily 02:30 IST cron + `CronSpec`). Two code commits (TD26 indexes.py, then TD27 `49bf33f`) + an EC2 crontab line. No frontend work; the Chat 5.10 SellSheet follow-up remains open. Lessons: a TTL no-ops on a non-Date field; the app DB is `portfolio` not `portfolio_advisor`; the bulky news field is `body_text` not `body`; purge age keys on `fetched_at` not `published_at`.
- **Chat 5.13**: Phase 5 closed — TD28 (`refetchQueries` swap in `notes-panel.tsx` + `refresh-button.tsx`, frontend `f59958`), TD29 (dead `from pydoc import doc` removal in `holdings.py`), TD30 (`MONGODB_URI` doc-drift confirmation), TD31 (ISIN charset `pattern` on the two `/suggestions/{isin}` Path params in `suggestions.py`), TD32 (`$options:i` drop on `transactions/search` in `transactions.py`). One frontend commit (`f59958`) + three backend commits (deployed code HEAD `090d96c`). No frontend work beyond TD28; the Chat 5.10 SellSheet follow-up remains open. Lessons: a "~line N" pointer is a hint (re-anchor at HEAD); use `grep -F` for literal verification strings; a pass/fail test must discriminate the change from pre-existing constraints; a both-repos phase needs a per-repo deploy + landed-assertion.
- **Chat 5.14**: Phase 6 opened — #19 (TD33) atomic Tavily quota claim in `app/services/tavily_client.py` (`get_today_quota()` pre-check + separate `_increment_quota()` `$inc` collapsed into one conditional `find_one_and_update` guarded by `calls_today < TAVILY_DAILY_CALL_LIMIT`; cap-hit via `DuplicateKeyError` on the unique `date_unique` index → `TavilyQuotaExceeded`). ONE backend commit `4ac2c95`, backend-only. Cap kept calls-only (`credits_today` tracked, not capped). No frontend work; the Chat 5.10 SellSheet follow-up remains open. Lessons: a per-period hard-ceiling counter is enforced atomically by guarding in the `find_one_and_update` filter and letting a unique index catch the over-cap upsert (no lock, no transaction, one round-trip); README/data_flow "monthly" wording is stale (code is daily) — anchor to the code body at HEAD when docs drift.
- **Chat 5.15 (THIS commit)**: Phase 6 continued — #20 (TD34) transient-5xx/429 retry inside `app/services/notify.py` `email()` (1 retry / 2 attempts, 30s blocking backoff; 400s + no-status errors not retried; `_email_error_status()` + `_is_transient_email_error()` helpers + module constants; `{ok,id,error}` contract + no-raise guarantee unchanged so the three `result["ok"]` callers are untouched). ONE backend commit `7d77b9c`, backend-only. Retry count / backoff / blocking-sleep user-delegated → 1 retry + 30s fixed. No frontend work; the Chat 5.10 SellSheet follow-up remains open. Lessons: a retry inside a swallow-exceptions `{ok,id,error}` wrapper must keep returning that dict (never raise) so `result["ok"]` callers stay untouched — re-read all callers at HEAD first; classify transient off the SDK exception's HTTP status (not the message); scope the retry to 429 + 5xx only (no-status errors are non-transient); verify with a monkeypatched harness, not a live send.
- **Tree-listing command (Section 0)**: the canonical `git rev-parse HEAD && git ls-tree -r --name-only HEAD` block for both repos. Run once per chat immediately after the bootstrap; the assistant uses its output as the source of truth for every file path and URL it constructs.
- **`raw.githubusercontent.com` URL form**: `https://raw.githubusercontent.com/doshisahil95/<repo>/<sha>/<path>`. The blob URL (`/blob/<sha>/`) frequently returns `LINK_NEEDS_AUTH` for Glean readers even on public repos. Standing convention since Chat 5.5, reinforced Chat 5.7.

End of PROJECT_STATE.md.
