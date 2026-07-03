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
* When the user explicitly directs a roadmap change (e.g. add/insert a stage), apply it as a real numbered row + phase and thread it through every ordering/summary/bundle view. (Chat 8: added Phase 10.5 USER ACCEPTANCE REVIEW / #52.)

## Section 3: Tech stack

**Backend:** Python 3.12 · FastAPI · Pydantic v2 (routers use `pattern=` not `regex=` post Chat 5 A19; round-trip / `ge=0` hardening post 5.6; ISIN `Path()` params on the two `/suggestions/{isin}` endpoints AND the `/chat/holdings/{isin}` endpoint AND the `/watchlist/{isin}` endpoints carry `pattern=r"^[A-Z0-9]{12}$"` post 5.13 TD31 / Chat 6 / Chat 8; the `/portfolio/by-tag` endpoint validates `tag` via `Query(..., min_length=1)` post Chat 7) · MongoDB Atlas M10 (ap-south-1) · uv (package manager) · yfinance (prices/fundamentals/earnings, free tier) · Anthropic Claude SDK (Sonnet 4.5 dossiers + ad-hoc chat, Haiku 4.5 classification) · Tavily (news search, free tier, **daily** quota enforced atomically as of 5.14 TD33) · Resend (transactional email — all via `notify.email()` as of Chat 5 A2; transient 5xx/429 retried once with 30s backoff as of 5.15 TD34) · ntfy (push — public `ntfy.sh` for all paths; self-hosted private decommissioned TD8). **CORS:** `CORSMiddleware allow_methods` is an explicit list — `["GET","POST","PUT","PATCH","DELETE","OPTIONS"]` as of Chat 8 (PUT added for the `/watchlist/{isin}` upsert; a missing method 503s the browser preflight even though curl-from-box works). **Tests:** pytest>=8.3 in the `dev` dependency-group; `[tool.pytest.ini_options] pythonpath=["."]`; the `tests/*` harness (Chat B #33) is hermetic (in-memory `FakeCollection` + a `fake_db` fixture that monkeypatches the `Collections.*` accessors) — run via `uv run python -m pytest`.

**Frontend:** Next.js 16 (Turbopack) · React 19 · TypeScript strict · Tailwind v4 · shadcn/ui Nova preset · Recharts · TanStack Query (mutations use `refetchQueries`, synchronous; the two `invalidateQueries` outliers in notes-panel.tsx + refresh-button.tsx swapped in 5.13 TD28) · react-hook-form + zod · sonner · next-themes. NO markdown-rendering dependency — LLM markdown (e.g. chat answers) is rendered by a self-contained `MarkdownLite` inside `components/chat-panel.tsx` (Chat 6).

**Hosting:** AWS EC2 t3.micro (ap-south-1), Elastic IP 3.111.254.128 (whitelisted in Atlas) · Tailscale-only app traffic, no public ingress, no Caddy · MongoDB Atlas M10 (separate; access list = EC2 EIP + dev IPs).

## Section 4: Infrastructure paths and ports

**Network:** EC2 Tailscale IP `100.112.20.41` · EC2 Elastic IPv4 `3.111.254.128` · SSH `ssh ubuntu@100.112.20.41`. Backend port: **EC2 8000, Mac local 8001**. Frontend port: 3000 (both). Always specify which machine. Convention: "SSH into EC2 first, then curl localhost:8000."

**Repo paths — Mac:** `~/Projects/Personal/ai-stock-advisor/ai-stock-advisor-backend` and `.../ai-stock-advisor-frontend`. **EC2:** `/home/ubuntu/ai-stock-advisor-backend` (`~/ai-stock-advisor-backend`) and `.../ai-stock-advisor-frontend`.

**Script invocation (EC2):** run scripts as MODULES from the repo root — `cd ~/ai-stock-advisor-backend && uv run python -m scripts.<name>` (or `PYTHONPATH=. uv run python scripts/<name>.py`). Running `uv run python scripts/<name>.py` by file path puts `scripts/` on `sys.path[0]` and `import app` fails with `ModuleNotFoundError: No module named 'app'` — this is an invocation-path error, NOT a code bug (Chat 8 lesson; cron lines already use `PYTHONPATH=.`). Heredoc `uv run python - <<PY` works because cwd is on the path. **Tests:** `uv run python -m pytest` (pyproject pins `pythonpath=["."]`, so `import app` resolves; Chat B #33).

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

**Backup → fresh-DB restore rehearsal (#37, 2026-07-01):** Surgical per-collection backup→restore drill for the three collections GO-LIVE (#42) must PRESERVE when it wipes `transactions`/`transactions_staging`/`holdings` — `monitored_stocks`, `suggestion_outcomes`, `digest_deliveries`. Rehearsed on EC2 against prod Atlas; prod `portfolio` is never written (the restore lands in a throwaway scratch DB that is then dropped). NOTE: this `mongodump` (100.17.0) does NOT accept `--nsInclude` (that flag is `mongorestore`-side) — dump per-collection with `--db/--collection`. The Atlas user `portfolio_app` CAN create a second DB (no Unauthorized), so the `--nsFrom/--nsTo` cross-DB remap is the canonical rehearsal path. Run from EC2 with `MONGODB_URI` sourced from `/etc/portfolio-advisor/secrets.env`:
* **(1) BACKUP** — dump each collection (rehearsal counts: `monitored_stocks` 2, `suggestion_outcomes` 155, `digest_deliveries` 10):
  * `mongodump --uri "$MONGODB_URI" --db=portfolio --collection=monitored_stocks   --out ~/atlas-backup-rehearsal/dump`
  * `mongodump --uri "$MONGODB_URI" --db=portfolio --collection=suggestion_outcomes --out ~/atlas-backup-rehearsal/dump`
  * `mongodump --uri "$MONGODB_URI" --db=portfolio --collection=digest_deliveries   --out ~/atlas-backup-rehearsal/dump`
* **(2) RESTORE** — into a FRESH scratch DB, prod untouched (`--drop` only clears the scratch namespace; the benign `don't know what to do with file ... prelude.json, skipping` line is expected):
  * `mongorestore --uri "$MONGODB_URI" --nsFrom 'portfolio.*' --nsTo 'portfolio_restore_test.*' --drop ~/atlas-backup-rehearsal/dump`
* **(3) VERIFY** — restored counts must equal prod (rehearsal: all three `OK`):
  * `mongosh "$MONGODB_URI" --quiet --eval 'const s=db.getSiblingDB("portfolio"),d=db.getSiblingDB("portfolio_restore_test");["monitored_stocks","suggestion_outcomes","digest_deliveries"].forEach(c=>print(\`${c}: prod=${s[c].countDocuments({})} restored=${d[c].countDocuments({})}\`));'`
* **(4) CLEANUP** — drop the scratch DB + local dump so nothing lingers:
  * `mongosh "$MONGODB_URI" --quiet --eval 'db.getSiblingDB("portfolio_restore_test").dropDatabase()'`
  * `rm -rf ~/atlas-backup-rehearsal`

For a REAL recovery INTO prod, replace step (2) with `mongorestore --uri "$MONGODB_URI" --nsInclude 'portfolio.<collection>' --drop ~/atlas-backup-rehearsal/dump` (no namespace remap — `--nsInclude` IS valid on `mongorestore`). Atlas Cloud Backup snapshots remain the whole-cluster disaster-recovery layer; this drill proves the surgical per-collection path.

**Repos:** backend `https://github.com/doshisahil95/ai-stock-advisor-backend` · frontend `https://github.com/doshisahil95/ai-stock-advisor-frontend`.

**Last verified SHAs (Chat 9 closed, 2026-07-01):**
* Backend (Chat C close): code HEAD **`eb964cc8d416d8e817f326501319fa19218b0d59`** — Chat C shipped Phase-10 #40 (realized-P&L UI hide, frontend-only, `16fab5ae`) then #41 (wire `holdings.stop_loss` — intraday stop-loss breach alert), a single logical unit. #41 backend: NEW `app/services/price_service.evaluate_stop_loss_alerts(rows)` on the EXISTING intraday write path — `scripts/refresh_prices_intraday.py` calls it (guarded) right after `insert_intraday_quotes` on the SAME fetched rows (no parallel price-fetch loop); rising-edge fire-once-on-cross-below with success-gated dedup (only a DELIVERED `stop_loss_hit` Alert suppresses re-fires; re-arm when a later tick shows price back at/above `stop_loss`); evaluated only for holdings with `stop_loss` set AND `"stop_loss" in alert_on`; ntfy-only via `push_public("price", ...)`; persists `Alert(alert_type="stop_loss_hit", channel="ntfy_public_price", severity="high")` to `alerts_log` — #41 is the FIRST writer of `alerts_log`; NEW dedup index `alerts_log isin_type_sent_desc` (isin, alert_type, sent_at desc). NO `routers/holdings.py` change (PATCH whitelist + `get_holding` already carried `stop_loss`). #41 frontend: `components/holding-stats.tsx` REPLACED to add a read-only stop-loss strip (value + cushion % vs current price, red when breached) — editing stays in `components/notes-panel.tsx`; no `lib/api.ts` change. Backend `eb964cc8`, frontend `a4b27bd7`. Verified on EC2: 49 pytest passed, hygiene guard PASSED, `init_db` shows `alerts_log` 5 indexes incl. `isin_type_sent_desc`, functional fire->suppress->re-arm = 1/0/1 with two `delivery_status=="sent"` audit rows, `~/deploy-ui.sh` build+lint clean. Closes TD6; Phase 10 is now fully SHIPPED. The Chat C `Project_State.md` + `master_todo.md` doc commit advances HEAD further. Chat C opened at backend `cec11ab3` + frontend `16fab5ae`.
* Backend (Chat 9 close): code HEAD **`32088c938ecdfb9f58d40783f9ecf6da45819fe2`** — Chat 9 shipped Phase-10 #39 (F11 capital-gains pack) across two commits: backend Unit 1 (NEW `app/services/tax_service.py` + NEW `app/routers/tax.py`, `holdings_service._fifo_replay` extended to emit per-disposal `_realized_lots`, `main.py` includes `tax.router`, NEW `tests/test_tax_service.py`) on `32088c938ecdfb9f58d40783f9ecf6da45819fe2`, frontend Unit 2 (NEW `app/tax/page.tsx` + `lib/api.ts` capital-gains types/binding + `app/page.tsx` Tax nav) on `747ae4f29e0e0074b21eb3f34a3114a769e32752`. READ-ONLY over the Phase-1 ledger — replays via `_fifo_replay` (single FIFO source of truth, NO parallel path), classifies STCG/LTCG at a strict >12-calendar-month boundary, §49(2C) honored via the `manual_demerger` BUY rows in the ledger (`cost_basis_adjustments` NOT re-applied). Verified on EC2: 49 pytest passed, hygiene guard PASSED, `/tax/capital-gains` live + `/tax` → 200. Frontend HEAD **`16fab5aef77c2b1884b7ec70667032f39876c265`** (Chat C #40 realized-P&L UI hide — frontend-only; prior Chat 9 close was `747ae4f29e0e0074b21eb3f34a3114a769e32752`). The Chat 9 `Project_State.md` + `master_todo.md` doc commit advances HEAD further. Chat 9 opened at backend `9e78d5b` + frontend `c5bb1a34` (the Chat B doc-commit HEADs).
* Backend (Chat B close — backend + doc-only chat): code HEAD **`8127c6f071a127e76a0c1cc6afd8a686bcf0cb7c`** — Chat B shipped Phase 9 #30 (11 `datetime.utcnow()`->`utcnow()` sites / 5 files), #31 (tree-wide tz-aware `datetime.now(timezone.utc)` Mongo-write sweep -> `utcnow()` + 19 `# tz-ok:` annotations + NEW `scripts/check_datetime_hygiene.py` tokenize-based lint guard), and #32 (`requires-python = ">=3.12,<3.14"` pin + `uv lock` relock) on `025b8a0688a67d181f09ed800b6692f574fdb9bc` (2026-06-15), then #33 (hermetic `tests/*` pytest harness — 28 tests across 6 targets; `tests/_fakes.py` FakeCollection + `tests/conftest.py` fake_db fixture; recompute_holding full DB idempotency; no new deps) on `04fd970` (2026-06-26), then #36 (NEW `app/routers/admin.py` — `POST /admin/recompute/{isin}` Tailscale-only, delegates to `recompute_holding` TD20, registered in `main.py`) on `1ef0eadf4e95349fdce12156fc2c37d90bc3719d` (2026-07-01), then #37 (Atlas backup → fresh-DB restore rehearsal — DOC + OPS only, runbook added to Section 4; no `app/` code, so code HEAD stays `1ef0ead`) on 2026-07-01, then #38 (JSON-structured logging — `app/main.py` `logging.basicConfig` -> stdlib `JsonLogFormatter` + `_configure_logging()` over root + `uvicorn`/`uvicorn.error`/`uvicorn.access` with `propagate=False`; one single-line JSON object per record to stdout/journald; no new dependency, no `uv.lock` change) on `8127c6f071a127e76a0c1cc6afd8a686bcf0cb7c` (2026-07-01), CLOSING Chat B / Phase 9. Frontend HEAD `c5bb1a34d09dfc6d6879a3b2264310e4a9771c24` — ADVANCED since Chat 8 by ONE docs-only commit `c5bb1a3` (frontend README per-page reference + nav cover /watchlist, #29 — the carried-forward doc note landing), NOT a code change (was recorded `58bf6369`). The Chat B `Project_State.md` + `master_todo.md` doc commit advances HEAD further. Chat B opened at backend `0b6e1147` (the Chat 8 doc-commit HEAD).
* Backend: **`67704025650bed4cbce9549ea45a064bae892c12`** (Chat 8 code HEAD — #29 CORS fix; the Chat 8 `Project_State.md` + `master_todo.md` doc commit advances it further). Chat 8 shipped #29 (F13 watchlist) across four commits: Unit 1 write-model + universe (`34ff906d7cf6b2c8d1e1ccc210810023f069f7aa` — `MonitoredStockWatchlistPatch` + `build_universe` = NIFTY 100 ∪ watchlist + `get_watchlist_isins`), Unit 2 `/watchlist` CRUD (`a250d00189c67ddc073715affc9175b9fc68383d` — new `routers/watchlist.py` + widened audit-action Literal + `main.py` include), Unit 3 cron coverage (`9857570b8e1799c274d2ce422b44bef419f17d11` — `refresh_fundamentals.py` + `fetch_news_for_universe.py` fold in watchlist ISINs), CORS fix (`67704025` — `main.py` allow_methods += PUT). Opened at `803e6610` (Chat 7 code HEAD; the Chat 7 doc commit `c162d9c2` was the actual open base for the file re-reads).
* Frontend: **`58bf6369e73916c26e534fc517ac92f2f3dfedb5`** (Chat 8 — Unit 4: `lib/api.ts` watchlist types + bindings, new `app/watchlist/page.tsx`, `app/page.tsx` Watchlist nav link; no new npm dependency). Advanced in Chat B to `c5bb1a34d09dfc6d6879a3b2264310e4a9771c24` via ONE docs-only commit `c5bb1a3` (frontend README per-page reference + nav cover /watchlist, #29 — the carried-forward doc note landing; NOT code). Opened at `e14d6a750f802dae941d512837ff1788a7a3a0f0`.
* Prior code-HEAD closes: Chat 7 backend `803e6610` (#28 F12 risk-summary `97041621` + F15 by-tag `803e6610`), frontend `e14d6a75` · Chat 6 backend `5e787c9` (#27 F1+F3 ad-hoc chat across five commits — Unit 1 data layer off open base `4403bb5`, Unit 2 enrichment `c407985`, Unit 3 chat service + endpoints `15ea9c0`→`dd82636`, route-shadow fix `5e787c9`), frontend `6093f63` (Unit 4 chat UI) · Chat A `fae6edf` (ops & alerting bundle, backend+doc only; frontend `f59958`) · 5.19 `7fcda9e` (TD39 cron_health_check self-failure dual-transport alert) · 5.18 `0515fef` (TD38 fallback heartbeat log + dual-source health check) · 5.17 `1d627d7` (TD37 reject NaN in _to_decimal) · 5.16 `f4168b3` (TD35 explicit inserted_id flow) · 5.15 `7d77b9c` (TD34 notify retry) · 5.14 `4ac2c95` (TD33 atomic Tavily) · 5.13 backend `090d96c` (TD29/31/32), frontend `f59958` (TD28) · 5.12 `49bf33f` (TD26 then TD27) · 5.11 `a2806cd` (TD23/24/25) · 5.10 `b34721e`.

## Section 5: Backend file map

Layout under `app/` and top-level (verified against tree at SHA `ce5e746`; subsequently touched files tagged with the chat/TD that changed them — pending `master_todo #N` notes are live work). Re-verified against the Chat 6 tree listing at backend HEAD `4403bb5` (open). Re-verified against the Chat 7 tree listing at backend HEAD `a104993` (open). Re-verified against the Chat 8 tree listing at backend HEAD `c162d9c2` (open) — Chat 8 ADDED `app/routers/watchlist.py`, edited `app/models/monitored_stock.py`, `app/services/suggestion_engine.py`, `app/services/monitored_stocks_audit_service.py`, `app/main.py`, `scripts/refresh_fundamentals.py`, `scripts/fetch_news_for_universe.py` (no new collection; no index changes). Re-verified against the Chat B tree listing at backend HEAD `18be2c5` (open) — Chat B ADDED `scripts/check_datetime_hygiene.py` (#31), `tests/_fakes.py` + `tests/conftest.py` + 6 `tests/test_*.py` files (#33), edited `pyproject.toml` + `uv.lock` (#32) and swept datetime sites across `routers/portfolio.py`, `routers/transactions.py`, `services/scoring_service.py`, `services/dossier_service.py`, `services/fundamentals_service.py`, `services/conversation_service.py`, `services/reconciliation.py`, `services/tavily_client.py`, `services/price_service.py`, `services/news_classifier.py`, `services/transactions_audit_service.py`, `services/cron_heartbeat_service.py`, `services/instrument_service.py`, `scripts/seed_nifty100.py`, `scripts/import_orderbooks.py`, `scripts/add_manual_transactions.py`, `scripts/seed_cost_basis_adjustments.py` (#30/#31).

```
app/
  main.py                     FastAPI bootstrap, router includes, lifespan
                              (lifespan pings Mongo + ensure_indexes; no scheduler). (done: #34 GET /health now returns 503 + degraded on ping failure, 200 + ok on success; done: #27 includes conversations.router; done #29 includes watchlist.router AND CORSMiddleware allow_methods now includes PUT — required for the /watchlist/{isin} upsert browser preflight; done #36 includes admin.router — the new Tailscale-only POST /admin/recompute/{isin}; done #38: logging.basicConfig REPLACED by a stdlib JsonLogFormatter (logging.Formatter subclass) + _configure_logging() — one single-line JSON object per record to stdout/journald over the root logger AND uvicorn/uvicorn.error/uvicorn.access (propagate=False, no double-logging); fields timestamp(UTC ISO-8601 ms+Z from record.created)/level/logger/message/module/func/line + traceback on exc_info + caller extra merged; no new dependency; done #39 Chat 9: includes tax.router — the new GET /tax/capital-gains, the F11 capital-gains pack).
  agents/__init__.py          empty package placeholder
  scheduler/__init__.py       empty placeholder (TD21: candidate home for registry-rendered schedule tooling)
  config/settings.py          pydantic-settings; loads secrets. F2b: NTFY_PUBLIC_TOPIC_DIGESTS (required). (done: TD9 NTFY_URL/USER/PASS removed)
  db/
    client.py                 Mongo client, get_db(), Collections accessor (incl. monitored_stocks_audit F10, earnings_calendar F14, recompute_locks TD20, conversations — actively written as of #27). NOTE: app DB name is `portfolio` (MONGODB_DB_NAME default), NOT `portfolio_advisor` (5.12 lesson). (Chat B #33: the pytest `fake_db` fixture monkeypatches the Collections.* accessors to in-memory FakeCollections — patching the class attribute is seen by every module that did `from app.db.client import Collections` since they share the one class object and call the accessor at call-time)
    indexes.py                ensure_indexes() on startup. (done: TD20 recompute_locks acquired_at TTL 60s; TD26 prices_intraday captured_at_ttl ASC 90d; #27 conversations scope_created_desc). monitored_stocks has isin_unique_active (unique, partialFilterExpression={"status":"tracking"}) + (status, rejected_at). tavily_quota has unique date_unique on date_utc — the primitive the TD33 atomic claim relies on. (Chat 8 #29: NO index changes — watchlist reuses monitored_stocks one-doc-per-ISIN; the partial unique index stays scoped to status:tracking so a watchlist doc is outside it and single-doc-per-ISIN is upheld by upsert-on-{isin}.)
  models/
    _common.py                BaseDoc (to_mongo() = model_dump(by_alias=True, exclude_none=True) + Decimal→Decimal128; extra="forbid"), Money, PyObjectId, utcnow(), _convert_decimals_to_decimal128, Decimal128/ObjectId helpers. (done: #22/TD37 _to_decimal rejects NaN float (v != v) in the float branch -> ValueError("NaN not allowed"); surfaces as 422 via Money BeforeValidator). (#29 watchlist router calls _convert_decimals_to_decimal128 on the patch dump — the watchlist patch carries Money fields, raw Decimal is not BSON-encodable). (Chat B #31: utcnow() = datetime.now(timezone.utc).replace(tzinfo=None) — its naive-UTC storage invariant is now MACHINE-ENFORCED by scripts/check_datetime_hygiene.py)
    instrument.py             Instrument. (fix F20: populate_by_name + _id alias)
    holding.py                Holding (active position). Carries `tags: list[str]` (default_factory=list) — the field F15/#28 `GET /portfolio/by-tag` filters on (Mongo array-membership)
    transaction.py            Transaction (BUY/SELL/SPLIT/BONUS/DEMERGER). (5.6 ge=0; fix F29/F80/F82)
    fundamentals.py           InstrumentFundamentals (per-ISIN, per-refresh). yfinance field map keys: market_cap, pe_ratio, pb_ratio, return_on_equity, return_on_assets, operating_margin, debt_to_equity, earnings_growth_yoy, revenue_growth_yoy, dividend_yield, beta, current_price, fifty_two_week_high/low, sector, industry. (#51 OPEN: dividend_yield unit inconsistency — some rows stored already-as-percent, _fmt_pct multiplies by 100)
    earnings_event.py         F14 EarningsEvent (one doc per ISIN per earnings_date)
    suggestion.py             SuggestionRun, SuggestionOutcome, CandidateScore, SignalScore, GateResult. F2 direction; 5.6 round-trip. SuggestionRun.id POPULATED post-insert by _persist_run since 5.16 (TD35). (TD7/#45 deferred)
    news.py                   NewsArticle (only news model). 5.12: bulky field is `body_text` (NOT `body`); `body_purged_at` stamped by purge cron (TD27). Classified fields: sentiment, sentiment_confidence, themes, severity, classifier_summary. (#50 OPEN: entities_isins can carry the wrong ISIN — over-broad tagging upstream in news_fetcher/classifier; #29 widens the blast-radius since every watchlist name now pulls daily news)
    monitored_stock.py        MonitoredStock + MonitoredStockFeedbackPatch + MonitoredStockWatchlistPatch (NEW #29). (A1 Literal aligned; status Literal incl. "watchlist"). (done #29: MonitoredStockWatchlistPatch mirrors MonitoredStockFeedbackPatch — ConfigDict(extra="forbid"), status pinned Literal["watchlist"], carries only mutable watchlist fields target_buy_price/alert_above/alert_below/alert_on/tags/user_notes/thesis/conviction + last_user_interest_at + updated_at; the /watchlist router dumps it exclude_none so a re-PUT never wipes unspecified fields). (TD1/#43 deferred: direction-aware — #26 added direction-aware RELABEL on the feedback payload/outcome filter, but monitored_stocks itself stays direction-agnostic; if TD1 is taken, reconcile with the watchlist status)
    macro_signal.py           placeholder
    conversation.py           Conversation(BaseDoc) — ACTIVE write model as of #27. Fields: query, response, intent (QueryIntent 9-value Literal), scope (ConversationScope Literal["suggestions","holding"]|None), sentiment_overlay, related_entities_isins, related_holding_id, related_monitored_id, cited_* id lists, model_used, input_tokens, output_tokens, cost_usd (Money), duration_ms, user_action, user_action_at, follow_up_conversation_ids (UNUSED), created_at
    reconciliation.py         ReconciliationSnapshot (fix F16/F17)
    cost_basis_adjustment.py  CostBasisAdjustment (fix F18/F19)
    alert_log.py              Alert model (alert_type/channel/severity/TriggerData/delivery_status). (#41 Chat C: alerts_log is now WRITTEN — evaluate_stop_loss_alerts persists stop_loss_hit rows; FIRST writer)
    digest.py                 placeholder (delivery audit lives in `digest_deliveries`)
    price_daily.py            placeholder (collection writers use raw dicts)
    symbol_override.py        SymbolOverride (fix F79)
    user_profile.py           UserProfile (singleton, _id="sahil")
  routers/
    holdings.py               /portfolio/holdings*, /sell, /preview-sell, /history, /transactions. (done: #5 validate_replay on /sell; #6 dup list_transactions deleted; #7 try/except around recompute_holding -> recorded_with_warning; #15/TD29 dead `from pydoc import doc` removed). NOTE: `list_holdings` is the canonical annotate path that F15/#28 `/portfolio/by-tag` reuses verbatim
    portfolio.py              /portfolio/summary + /portfolio/risk-summary (F12/#28) + /portfolio/by-tag (F15/#28). _serialize recursive Decimal/Decimal128->str, ObjectId->str, datetime->ISO. (done #30 Chat B: utcnow() sweep)
    transactions.py           /transactions/search, CRUD, audit. (fix F21 reason required). (done: #4 write-before-apply audit-then-apply; #18/TD32 dropped $options:i on search regex). (done #31 Chat B: tz-aware Mongo-write sweep -> utcnow())
    reconciliation.py         /reconciliation/snapshot, /snapshots, /auto-snapshot
    instruments.py            /instruments (symbol_overrides CRUD) + /instruments/search/{symbol_prefix} + /instruments/{exchange}/{symbol}. (done #27 route-shadow fix: STATIC /search/{symbol_prefix} declared BEFORE dynamic /{exchange}/{symbol}; NOTE comment guards the ordering). (#29 frontend watchlist add-control + the chat research panel both call /instruments/search)
    cost_basis.py             /cost-basis/adjustments
    suggestions.py            /suggestions/latest, /runs, /runs/{id}, /performance, /{isin}/feedback, /{isin}/audit, /feedback/audit/recent. F2 ?direction; A1 MonitoredStockFeedbackPatch; A19 Query() pattern=. (done: #17/TD31 ISIN pattern; #26 direction-aware feedback relabel). NOTE: the GET /{isin}/audit endpoint also surfaces the watchlist_add/update/remove audit rows #29 writes (same monitored_stocks_audit collection). submit_feedback write-before-apply ordering covered by tests/test_submit_feedback.py (#33 Chat B)
    conversations.py          NEW (#27). Ad-hoc chat: POST /chat/suggestions (F1), POST /chat/holdings/{isin} (F3, ISIN-validated, 404 on unknown instrument), GET /chat/history. APIRouter(prefix="/chat", tags=["chat"]).
    watchlist.py              NEW (#29). F13 watchlist CRUD. APIRouter(prefix="/watchlist", tags=["watchlist"]). GET "" (list, price-enriched via bulk_get_latest_prices, newest-interest first), GET /{isin} (404 if not status=="watchlist"), PUT /{isin} (idempotent create/update: 404s unknown instrument; reads previous status -> watchlist_add vs watchlist_update; log_change BEFORE apply (F10); MonitoredStockWatchlistPatch -> _convert_decimals_to_decimal128 -> update_one $set+$setOnInsert upsert on {isin}; un-excludes a previously rejected/acted ISIN), DELETE /{isin} (hard delete, ONLY when status=="watchlist" so feedback rows are never nuked; 404 otherwise; audit watchlist_remove BEFORE delete). WatchlistUpsert request model (extra="forbid", all fields optional, `note` is the audit note NOT persisted). Local _jsonable/_serialize_row mirror routers/suggestions.py decimal-to-jsonable. ISIN Path pattern=r"^[A-Z0-9]{12}$".
    admin.py                  NEW (#36). Ops/recovery. APIRouter(prefix="/admin", tags=["admin"]). POST /admin/recompute/{isin} (ISIN pattern=r"^[A-Z0-9]{12}$") -> holdings_service.recompute_holding (TD20 per-ISIN advisory lock; NO parallel recompute path) -> {status:"recomputed", isin, holding} on an active result, {status:"no_active_holding", isin, holding:null, message} when recompute returns None (full exit / no txns; 200 not 404), 409 on lock contention (RuntimeError), 500 otherwise. Router-local _jsonable serializer (watchlist precedent). HTTP replacement for SSH-shell recovery of a stuck holding (the TD19/#7 fallback). "Tailscale-only" = existing app perimeter, no in-app auth gate. Registered in main.py.
    tax.py                    NEW (#39 Chat 9). F11 capital-gains. APIRouter(prefix="/tax", tags=["tax"]). GET /capital-gains?fy=YYYY-YY (fy OPTIONAL — omitted -> current IST FY via tax_service.current_fy(); Query charset-guarded pattern ^\d{4}-\d{2}$; 422 on malformed OR non-consecutive fy via tax_service.FyParseError). Router-local _jsonable (watchlist/cost_basis precedent; money as strings). Delegates to tax_service.compute_capital_gains. Registered in main.py.
    cron.py                   /cron/heartbeats (F4)
  services/
    instrument_service.py     lookup_isin, lookup_metadata, bulk_lookup_isins, refresh_from_nse. (done #27: lookup_by_isin(isin) — reverse lookup ISIN -> instrument dict, NSE-preferred). (done #31 Chat B: tz-aware Mongo-write sweep -> utcnow(), 3 sites)
    yfinance_lookup.py        thin yfinance Ticker wrapper. fetch_metadata(symbol, exchange) lru-cached, swallows exceptions -> safe-default dict. (Chat B #33: recompute_holding tests monkeypatch holdings_service.fetch_metadata to a static dict so no Yahoo call)
    price_service.py          EOD+intraday fetch, bulk_get_latest_prices (returns {isin: doc} with `close` Decimal128 + `date`), bulk_get_previous_closes, annotate_with_current_price, get_previous_close. IST + _to_ist() helpers (TD23). (done: #9/TD23 holiday guard; #10/TD24 docstring; #11/TD25 per-ISIN find_one; TD26 captured_at BSON Date). (#29 watchlist GET endpoints price-enrich via bulk_get_latest_prices; unchanged). (done #31 Chat B: tz-aware Mongo-write sweep -> utcnow(), incl. bulk_get_latest_intraday now_utc; in-memory aware sites annotated # tz-ok). (done #41 Chat C: NEW evaluate_stop_loss_alerts(rows) — rising-edge stop-loss breach alert on the intraday write path, first writer of alerts_log)
    holdings_service.py       recompute_holding (per-ISIN advisory-lock wrapper) + _recompute_holding_impl + _per_isin_recompute_lock (CM), validate_replay, preview_sell, _fifo_replay, _to_decimal. (done: #8/TD20 serialized per-ISIN via recompute_locks + 60s TTL). (Chat B #33: _fifo_replay + validate_replay are pure/hermetic and unit-tested directly; preview_sell + recompute_holding idempotency unit-tested against the fake_db — recompute run twice asserts stable aggregates + preserved created_at + exactly one active doc; full-exit -> None + zero active docs). (#39 Chat 9: _fifo_replay ALSO emits a per-disposal `_realized_lots` list — buy/sell trade_date + fee-normalized per-share cost/proceeds captured in the SELL branch — for tax_service to read READ-ONLY; the single FIFO source of truth, NO parallel path. _recompute_holding_impl pops `_realized_lots` off `computed` so it never lands on the extra=forbid holdings doc)
    portfolio_service.py      compute_summary + _annotate_holdings + compute_risk_summary (F12/#28). _to_dec helper imported by routers/portfolio.py for by-tag totals
    tax_service.py            NEW (#39 Chat 9). F11 capital-gains. compute_capital_gains(fy=None) -> {fy, fy_start, fy_end, summary{stcg/ltcg/total each realized_gain/proceeds/cost/lot_count}, lots[]}. READ-ONLY over the transaction ledger: replays each ISIN through holdings_service._fifo_replay (single FIFO source of truth, NO parallel path) and reads the per-disposal _realized_lots it emits; filters disposals by SELL trade_date-in-IST inside the Indian FY (1 Apr->31 Mar); LTCG = listed equity held strictly >12 calendar months (day-clamped _add_months), else STCG; holding_period_days reported. §49(2C) demerger cost honored via the manual_demerger BUY rows already in the ledger — cost_basis_adjustments (cost_basis_service) is a read-only audit surface and is deliberately NOT re-applied (would double-count). parse_fy/current_fy/FyParseError helpers; IST = fixed +5:30; money serialized as strings by the router.
    transactions_audit_service.py  log_change, get_audit_for_transaction. (5.10: log_change invoked BEFORE apply — TD16). (done #31 Chat B: tz-aware Mongo-write sweep -> utcnow())
    monitored_stocks_audit_service.py  F10 log_change (write-before-apply). (done #29: action Literal WIDENED from FeedbackAction["acted","passed","rejected"] to AuditAction (adds watchlist_add/watchlist_update/watchlist_remove) so the /watchlist CRUD path reuses the SAME audit collection — log_change builds a raw dict with no runtime validation, so this is a type-correctness/honesty change, not behavioural; FeedbackAction kept for the feedback path). (Chat B #33: tests/test_submit_feedback.py monkeypatches log_change to capture call ORDER and asserts the audit lands BEFORE the monitored_stocks update)
    news_classifier.py        Haiku batch classifier classify_unclassified(limit=None, isin_filter=None, only_recent_days=35), retry pass. (fix F27). (done #31 Chat B: tz-aware Mongo-write sweep -> utcnow()). #50 OPEN
    news_fetcher.py           fetch_for_instrument(isin, symbol, name, days=30, use_case="suggestions_news"), fetch_for_universe. #50 OPEN: this + classifier attach the entities_isins that can be wrong
    news_signals.py           compute_news_signals_for_isin, _bulk
    scoring_service.py        extract_signals, score_candidates, weights, gates. F14 earnings-proximity gate; F2 sell-side scoring. (done #30 Chat B: utcnow() sweep, 3 sites)
    dossier_service.py        generate_dossiers_for_top_k, Sonnet. _generate_one (the wiring #27 mirrors). _to_float + _format_news_summaries + _build_position_context_block (CandidateScore-coupled). (done #30 Chat B: utcnow() sweep, 2 sites). (TD3/#44 deferred); #51: _fmt_pct ×100 dividend_yield
    conversation_service.py   NEW (#27). ENRICHMENT (ensure_stock_context) + CHAT (chat_about_holding / chat_about_suggestions). Single Sonnet {answer,intent} call mirroring dossier_service._generate_one. Writes ONLY Phase-2 reference collections + conversations. (done #30 Chat B: 2 `datetime.utcnow()` stragglers in _format_position_block swept -> utcnow())
    suggestion_engine.py      run_suggestions (full pipeline); build_universe; get_watchlist_isins (NEW #29); get_excluded_isins; filter_universe; get_latest_run(direction); get_active_holdings_full(); compute_portfolio_value(holdings, prices). F2 direction. (done: #21/TD35 _persist_run sets run.id). (done #29: build_universe() = NIFTY 100 ∪ watchlist — instruments.find({"in_nifty100":True}) merged with watchlist ISINs resolved from instruments by ISIN, deduped, warns on watchlist ISINs not found in instruments; held stays filtered DOWNSTREAM by filter_universe so a held+watchlist ISIN is not a buy candidate. get_watchlist_isins() = {isin for monitored_stocks status=="watchlist"}, the single source of truth reused by the two cron scripts. get_excluded_isins UNCHANGED — it scans only rejected/tracking, so a watchlist row is never excluded; flipping rejected→watchlist auto-un-suppresses. The buy-pipeline universe log line now says "N names (NIFTY 100 + watchlist)".)
    outcome_tracker.py        create_outcomes_for_run, snapshot_open_outcomes (returns count under `active_outcomes`; #47), compute_system_performance. F2 direction stamp + read-time sign-flip
    digest_delivery.py        send_weekly_digest, send_combined_digest. (done: #21/TD35 reads buy_run.id)
    explainability.py         SIGNAL_META, GROUP_META, GATE_META, FEEDBACK_META, PAGE_INTRO + PAGE_INTRO_SELL, enrich_run, enrich_candidate
    notify.py                 push_public, email. A2: email returns {ok,id,error}, optional text=. push_public RAISES on failure. (done: #20/TD34 email() retries once on transient 429/5xx with 30s backoff). NOTE: #25 + #35 call push_public GUARDED
    cron_heartbeat_service.py F4 cron_run CM, CRON_REGISTRY, get_recent_heartbeats, ist_today_window_utc. (done: TD14 registry rename; TD27 purge CronSpec; #23/TD38 fallback; #49/TD40 idle weekly_suggestions_sell expected_weekdays=set()). (done #31 Chat B: tz-aware Mongo-write sweep -> utcnow())
scripts/
  __init__.py
  init_db.py                    calls ensure_all_indexes() generically + seeds user_profile
  refresh_instruments.py
  refresh_prices.py
  refresh_prices_intraday.py    (done: #35 insert_intraday_quotes wrapped -> GUARDED push_public("errors",...) + re-raise). (done #41 Chat C: guarded evaluate_stop_loss_alerts(rows) call after insert_intraday_quotes — same rows, no parallel loop)
  take_reconciliation_snapshot.py
  seed_nifty100.py              CORRECTLY NAMED. Reads ind_nifty100list.csv. (TD12 resolved-as-doc-fix). (done #31 Chat B: tz-aware Mongo-write sweep -> utcnow())
  seed_cost_basis_adjustments.py  (done #31 Chat B: tz-aware Mongo-write sweep -> utcnow())
  import_orderbooks.py          (calls recompute_holding -> per-ISIN locked, TD20). (done #31 Chat B: tz-aware Mongo-write sweep -> utcnow())
  reconcile_staging.py
  promote_staging.py            (calls recompute_holding -> per-ISIN locked, TD20)
  add_manual_transactions.py    (done: #5 validate_replay on manual SELL path). (done #31 Chat B: tz-aware Mongo-write sweep -> utcnow())
  refresh_fundamentals.py       F14 default universe NIFTY100 ∪ active holdings ∪ watchlist. (done #29: default mode get_nifty100_union_holdings now folds in watchlist ISINs via new get_watchlist_instruments() — reuses suggestion_engine.get_watchlist_isins(), resolves {isin,symbol,exchange} from instruments — so watchlist names get weekly fundamentals + earnings like held/NIFTY100; --holdings-only and --symbols modes unchanged. Run as a MODULE: `uv run python -m scripts.refresh_fundamentals` — running by file path raises ModuleNotFoundError: app)
  fetch_news_for_universe.py    (A16 --include-held). (done #29: fetch universe folds in watchlist ISINs in BOTH branches via new get_watchlist_for_news() — reuses get_watchlist_isins(), resolves {isin,symbol,name,exchange}, deduped by ISIN — so watchlist names get daily news + Haiku classification. THE data-volume multiplier: each watchlist name consumes one Tavily call/run against the daily quota TD33, which degrades safely via the atomic quota guard if the ceiling is hit. Soft guardrail only — NO hard cap on watchlist size). Only prod path exercising Tavily quota guard (Sun 06:30 IST; TD33). #50: universe-scoped tagging is where wrong entities_isins likely originate
  run_weekly_suggestions.py     F2 --direction=buy|sell|both. (done: #1/TD14 crontab flags; #21/TD35 _do_both via buy_run.id/sell_run.id)
  track_suggestion_outcomes.py  (done: #47/TD22 — reads stats["active_outcomes"])
  cron_health_check.py          F4 daily 21:00 IST; dual-transport. (done: #23/TD38; #24/TD39)
  smoke_test.py                 (TD8 dropped push_private)
  purge_news_bodies.py          (done: #13/TD27 daily 02:30 IST; $unset body_text + stamp body_purged_at; --dry-run)
  check_datetime_hygiene.py     NEW (#31 Chat B). Tokenize-based datetime-hygiene lint guard: bans stdlib utcnow() tree-wide; fails any tz-aware datetime.now(timezone.utc) lacking a trailing # tz-ok: <reason>. Comment-aware, self-skipping, fragment-built needles (won't trip the existing greps). Run: uv run python -m scripts.check_datetime_hygiene (0=clean, 1=violations)
tests/
  __init__.py                   placeholder (empty package marker; untouched by #33)
  _fakes.py                     NEW (#33 Chat B). In-memory Mongo doubles: FakeCollection (find/find_one with sort/skip/limit, insert_one, update_one $set/$setOnInsert/upsert, delete_one/delete_many, count_documents; operators $ne/$in/$nin/$exists/$or/$and) + seed() helper + tx() (Mongo-shaped transaction dict factory) + oid(). Zero external dependency.
  conftest.py                   NEW (#33 Chat B). `fake_db` fixture: monkeypatches every Collections.* accessor the targets touch (transactions/holdings/instruments/recompute_locks/reconciliation_snapshots/user_profile/monitored_stocks/monitored_stocks_audit/suggestion_outcomes/suggestion_runs) to a FakeCollection so tests are hermetic (no Atlas, no network).
  test_fifo_replay.py           NEW (#33 Chat B). 7 tests of holdings_service._fifo_replay (pure): buy, partial sell P&L, full exit, buy fees fold into invested, dividend accrues, SPLIT scales qty/price, BONUS dilutes cost.
  test_validate_replay.py       NEW (#33 Chat B). 5 tests of holdings_service.validate_replay (pure): valid buy-then-sell, oversell rejected, chronology by trade_date not input order, split enables post-split sell, deleted txns skipped.
  test_preview_sell.py          NEW (#33 Chat B). 6 tests of holdings_service.preview_sell (monkeypatched transactions collection): partial, full exit, oversell, non-positive qty, no-txn, split-aware.
  test_recompute_holding.py     NEW (#33 Chat B). 2 tests of holdings_service.recompute_holding (fake_db + monkeypatched fetch_metadata): FULL DB idempotency (run twice -> stable aggregates + preserved created_at + exactly one active doc) + full-exit soft-delete returns None + zero active docs.
  test_submit_feedback.py       NEW (#33 Chat B). 3 tests of routers/suggestions.submit_feedback (fake_db + monkeypatched log_change): audit-written-before-apply ORDER, previous_status captured, action->status mapping.
  test_take_auto_snapshot.py    NEW (#33 Chat B). 5 tests of reconciliation.take_auto_snapshot drift math (fake_db + monkeypatched _get_our_numbers/_send_auto_drift_alert): no-manual-baseline skips drift block, no-drift on match, drift>threshold fires alert, rising-edge dedupe suppresses repeat, exactly-at-threshold is strict-`>` not drift.
  test_tax_service.py           NEW (#39 Chat 9). 21 tests of tax_service (fake_db + tx() factory): FY parse (valid / 6 bad shapes / century rollover), strict >12-calendar-month classification, fee normalization into cost/proceeds, FY-window inclusive/exclusive edges, single-sell-spans-two-buy-lots STCG+LTCG split, partial sell, demerger cost read-from-ledger (not double-counted), empty, default-FY. 49 total with the #33 harness.
docs/
  data_flow.md                  (5 deliverable; 5.5 TD12 universe corrected). (done: #48/TD36 Tavily "monthly" -> "daily"). master_todo #29 note: build_universe universe definition now includes watchlist — verify data_flow's universe description stays accurate in the next doc-touch chat
  Project_State.md              THIS FILE (Chat B doc commit)
  master_todo.md                canonical ordered task list (Chat 5.8 NEW)
pyproject.toml                  (done #32 Chat B: requires-python = ">=3.12,<3.14" pinned) (declares resend>=2.4 + anthropic; dev dependency-group has pytest>=8.3; [tool.pytest.ini_options] pythonpath=["."])
uv.lock                         (done #32 Chat B: requires-python field tracks the <3.14 pin via uv lock)
README.md                       (5 deliverable; 5.5 §8/§11/§5). (done: #48/TD36 Tavily monthly -> daily). master_todo #29 note: README per-page/endpoint reference should gain the /watchlist endpoints + page in the next doc-touch chat
```

## Section 6: Frontend file map

Verified against tree at SHA `4f31b49` (5.13 → `f59958`; Chat 6 → `6093f63`; Chat 7 → `e14d6a75`). Re-verified against the Chat 8 tree listing at frontend HEAD `e14d6a75` (open) — Chat 8 → `58bf6369` ADDED `app/watchlist/page.tsx`, edited `lib/api.ts` + `app/page.tsx`. No new npm dependency, no new shadcn primitive. Frontend in Chat B ADVANCED to `c5bb1a34` via ONE docs-only commit `c5bb1a3` (frontend README per-page reference + nav cover /watchlist, #29 — the carried-forward doc note landing; NOT code; #33/#36 are backend only).

```
app/
  layout.tsx · page.tsx (dashboard) · providers.tsx · globals.css · favicon.ico
  page.tsx                   dashboard. (done #28: mounts <RiskSummaryCard> via independent useQuery(["dashboard","risk"]); Tags header nav link). (done #29: added a "Watchlist" header nav link -> /watchlist, lucide Eye icon). (done #39 Chat 9: added a "Tax" header nav link -> /tax, lucide Receipt icon)
  watchlist/page.tsx         NEW (#29). F13 watchlist surface. Reuses the /tags page shell (back-link, header, Card/Skeleton) + components/ui/table primitives (watchlist rows are monitored_stocks, NOT Holding[], so a purpose table — not HoldingsTable). AddToWatchlist control: api.searchInstruments(prefix) (>=2 chars) -> pick a result -> PUT /watchlist/{isin} with optional target_buy_price. WatchlistTable: per-row current price (bulk_get_latest_prices), target-buy cell highlights emerald when current <= target, tags pills, added-at, Remove button. RemoveButton: DELETE /watchlist/{isin}. Mutations use useMutation + refetchQueries(["watchlist"]) + sonner toast + ApiError.detail. lucide: Eye/Plus/Trash2/ArrowLeft.
  tags/page.tsx              NEW (#28). F15 tag view; reuses <HoldingsTable> wholesale
  tax/page.tsx               NEW (#39 Chat 9). F11 capital-gains view at /tax. Client page: FY selector (recent FYs derived client-side in IST, default = current FY), STCG/LTCG/Total summary cards, per-lot disposals table with an STCG/LTCG badge. Printable (print: variants) mirroring the /cost-basis shell. Reuses Card/Table/Select/Badge/Skeleton + inr/inrSigned/colorForChange/dateShort/dateTime. useQuery(["tax","capital-gains",fy]) -> api.getCapitalGains(fy). lucide: ArrowLeft/FileText/Printer. No new npm/shadcn dep.
  holdings/[isin]/page.tsx    drill-down. (done #27: embeds <ChatPanel> — F3). (#41 Chat C: stop_loss editing lives in the embedded NotesPanel; no page.tsx change)
  reconciliation/page.tsx · cost-basis/page.tsx · transactions/page.tsx · transactions/audit/page.tsx
  suggestions/page.tsx        F6 user_action collapsed render; F2 shadcn Tabs. (done #27: embeds <ChatPanel scope="suggestions"> + <StockResearchPanel>)
components/
  ui/                         shadcn primitives (alert-dialog, badge, button, card, chart, dialog, dropdown-menu, input, label, popover, select, separator, sheet, skeleton, table, tabs, textarea, tooltip)
  holdings-table.tsx          HoldingsTable({holdings: Holding[]}) — reused by /tags (#28). (Chat 9/#40: hide realized P&L)
  buy-sheet.tsx               (the useMutation + refetchQueries + toast + ApiError.detail convention #29's watchlist page mirrors)
  sell-sheet.tsx              Phase-1 manual SELL sheet. OPEN FOLLOW-UP (5.10): recorded_with_warning (no _id) falls through. Deferred.
  transaction-edit-sheet.tsx
  holding-header.tsx          (Chat 9/#40: hide realized P&L)
    holding-stats.tsx           (#41 Chat C: REPLACED — added read-only stop-loss strip: value + cushion % vs current price, red when breached)
  price-chart.tsx · transactions-list.tsx
  notes-panel.tsx             (done: #14/TD28 refetchQueries)
  recent-activity-card.tsx · sector-breakdown.tsx · stat-card.tsx · top-movers.tsx
  totals-row.tsx              (Chat 9/#40)
  reconciliation-badge.tsx · theme-provider.tsx · theme-toggle.tsx
  refresh-button.tsx          (done: #14/TD28 refetchQueries)
  suggestion-card.tsx         F6 CollapsedFeedbackRow; F2 isSellSide
  explain-popover.tsx · page-intro.tsx
  chat-panel.tsx              NEW (#27). Reusable chat surface + self-contained MarkdownLite
  stock-research-panel.tsx    NEW (#27). Not-held buy-research entry point
  risk-summary-card.tsx       NEW (#28). F12 dashboard card
lib/
  api.ts                      hand-typed API client; SINGLE SOURCE OF TRUTH. (done #27: chat + instrument-search types/wrappers). (done #28: RiskSummary/HoldingsByTag types + bindings). (done #29: WatchlistEntry + WatchlistUpsertPayload types + getWatchlist/getWatchlistEntry/upsertWatchlist/deleteWatchlist bindings; widened MonitoredStocksAuditEntry.action to FeedbackAction|WatchlistAuditAction and new_status to include "removed" — the backend now emits watchlist_add/update/remove; FeedbackAction itself unchanged). (done #39 Chat 9: CapitalGainsLot/CapitalGainsBucket/CapitalGainsSummary/CapitalGainsResponse types + getCapitalGains(fy?) binding -> GET /tax/capital-gains?fy=YYYY-YY, fy optional; numeric fields typed as strings for Decimal precision)
  format.ts                   inr, pct, colorForChange, dateTime, nf, date (+ inrSigned). (#29 watchlist page reuses inr + dateTime)
  utils.ts                    cn() (clsx + tailwind-merge)
public/                       static SVGs
README.md                     (TD13 per-page reference; #28 added /tags; #29 /watchlist route + nav added in frontend `c5bb1a3` — the carried-forward doc-touch landed)
AGENTS.md · CLAUDE.md · components.json (Nova) · package.json · package-lock.json
next.config.ts (default) · postcss.config.mjs · tsconfig.json (strict; "@/*"; bundler) · .npmrc (legacy-peer-deps)
```
No `middleware.ts`, no `.env.example`, no custom next.config overrides at HEAD. Tailscale is the auth perimeter. No markdown library in package.json. #28 + #29 + #39 added NO new npm dependency and NO new shadcn primitive (risk card, tags page, watchlist page, tax page use only existing Card/Badge/Button/Table/Input/Label/Select/Skeleton).

## Section 7: Database collections (exhaustive)

All in Atlas M10. DB name from env `MONGODB_DB_NAME`; **live value is `portfolio`, NOT `portfolio_advisor`** (5.12 lesson). Accessed via `Collections.<name>()`. Indexes ensured at startup via `app/db/indexes.py`. (Chat B #33: the pytest harness exercises this surface against an in-memory FakeCollection via the `fake_db` fixture — no Atlas access during tests.)

**Phase 1:**
* **instruments** — NSE/BSE master, daily from NSE EQUITY_L.csv. Fields: exchange, symbol, isin, name, instrument_type, segment, lot_size, tick_size, source, last_seen_at, last_changed_at, in_nifty100, nifty100_marked_at. ~2,368 total; ~100 in_nifty100. Indexes: (exchange, symbol) unique, isin, last_seen_at, last_changed_at, in_nifty100. (#27 `lookup_by_isin` reverse-resolves via the `isin` index. #29 `build_universe` resolves watchlist ISINs outside NIFTY 100 from this collection by ISIN; the watchlist router seeds symbol/name/exchange/sector/industry from the instrument doc and 404s a PUT for an unknown ISIN.)
* **symbol_overrides** — manual ISIN aliases. Fields: exchange, symbol, isin, reason, created_at.
* **holdings** — one doc per ISIN, soft-deleted on full exit. Fields: isin, symbol, exchange, name, sector, industry, quantity (Decimal128), avg_cost, invested_amount, realized_pnl, first_purchased_at, last_traded_at, thesis, notes, stop_loss, target_price, tags, deleted_at. **INVARIANT: every query MUST include `deleted_at: None`.** Indexes: isin unique (partial: deleted_at is None), (deleted_at, last_traded_at). Writer: `recompute_holding(isin)` is the ONLY authoritative writer; serialized per-ISIN via `recompute_locks` (TD20). `realized_pnl` structural but HIDDEN in UI (#40). (#28 risk-summary + by-tag read holdings read-only. #29 watchlist: `build_universe` keeps held filtered DOWNSTREAM via `filter_universe`, so a held+watchlist ISIN is not a buy candidate; the fundamentals/news data-refresh universe is NIFTY100 ∪ held ∪ watchlist. Chat B #33: recompute_holding idempotency is unit-tested — run twice yields stable aggregates + preserved created_at + exactly one active doc; full exit soft-deletes and returns None.)
* **transactions** — append-only ledger. (INVARIANTS: never directly UPDATE/DELETE; PATCH/DELETE require reason, write transactions_audit first, then apply, then recompute_holding — #4/TD16 SHIPPED 5.10.) Indexes: (isin, trade_date), (symbol, trade_date), trade_date. 5.13 (TD32): search prefix-matches symbol with `^escaped` (NO $options:i).
* **transactions_staging** — ICICI import holding area. 5.10 (TD17): add_manual_transactions.py replays + validate_replay + ABORT.
* **transactions_audit** — append-only. **INVARIANT: written BEFORE the change is applied** (#4/TD16 SHIPPED 5.10).
* **recompute_locks** (TD20) — per-ISIN advisory locks. _id==isin, acquired_at. TTL 60s. Atomic insert_one winner.
* **prices_daily** — EOD OHLCV. Indexes: (isin, date) unique. (#28 + #29 read latest/previous close via bulk_get_latest_prices / bulk_get_previous_closes point-queries.)
* **prices_intraday** — latest intraday quote every 15 min. **INVARIANT: append-only within a day.** TTL captured_at_ttl (ASC, 90d) SHIPPED 5.12 (TD26). #9/TD23 holiday guard. #35 (Chat A) guarded ntfy.
* **reconciliation_snapshots** — our totals vs ICICI. #25 (Chat A): take_auto_snapshot ntfy on invested drift, rising-edge deduped. (Chat B #33: the take_auto_snapshot drift math — strict-`>` threshold, rising-edge dedupe — is unit-tested against fake_db with _get_our_numbers/_send_auto_drift_alert monkeypatched.)
* **cost_basis_adjustments** — audit trail for TMPV/TMCV per IT Act Section 49(2C).
* **user_profile** — single doc, _id="sahil".

**Phase 2:**
* **monitored_stocks** — user-feedback state + watchlist (F13). Fields: isin, status (Literal tracking/passed/rejected/watchlist), symbol, exchange, name, sector, industry, added_by, added_reason, added_at, thesis, conviction, conviction_history, target_buy_price, alert_above, alert_below, alert_on, tags, user_notes, last_reviewed_at, last_user_interest_at, acted_at, passed_at, rejected_at, last_feedback_action, last_feedback_at, last_feedback_note, created_at, updated_at. **INVARIANT (F10): writes preceded by monitored_stocks_audit_service.log_change(...).** Indexes: isin unique (PARTIAL, partialFilterExpression={"status":"tracking"}), (status, rejected_at). **ONE doc per ISIN — both the feedback writer and the #29 watchlist writer upsert on `{isin}`, so status is a single field that flips (a watchlist state and a tracking/rejected/passed state can NEVER be two rows for the same ISIN). The partial unique index only constrains tracking docs, so a watchlist doc is outside it; single-doc-per-ISIN is upheld by the upsert-on-{isin}, NOT by the index.** (done #29 — ACTIVELY WRITTEN with status="watchlist": PUT /watchlist/{isin} upserts (status="watchlist", added_by="user_explicit", added_reason="watchlist", identity seeded from instruments, Money fields -> Decimal128) and un-excludes a previously rejected/acted ISIN; DELETE hard-removes ONLY a status=="watchlist" doc. get_watchlist_isins() reads status=="watchlist".) TD1/#43 deferred. (Chat B #33: submit_feedback write-before-apply ordering is unit-tested — log_change call order asserted to precede the monitored_stocks update.)
* **monitored_stocks_audit** (F10) — append-only. Fields: isin, action, previous_status, new_status, note, performed_at, _schema_version. **INVARIANT: writer invoked BEFORE update_one/delete_one.** Indexes: (performed_at desc), (isin, performed_at desc). (done #29: now also carries watchlist_add / watchlist_update (previous_status->"watchlist") / watchlist_remove (new_status="removed") rows — the action Literal in monitored_stocks_audit_service was widened to AuditAction; the SAME collection is reused, surfaced via GET /suggestions/{isin}/audit.)
* **instruments_fundamentals** — one doc per ISIN per refresh. Indexes: isin_latest_unique, fetched_at. F14: universe NIFTY100 ∪ active holdings ∪ watchlist (#29). (#27 ensure_stock_context refreshes on demand. #29: refresh_fundamentals.py now covers watchlist ISINs weekly. #51 OPEN: dividend_yield unit inconsistency.)
* **earnings_calendar** (F14) — upcoming + historical per ISIN. **INVARIANT: refresh deletes future events then re-inserts.** (#29: refresh_fundamentals.py earnings refresh now covers watchlist ISINs.)
* **news_articles** — classified news, one doc per URL. body_text purged daily (TD27). (#27 + #29 fetch+classify on demand / weekly; the F3 chat + news_score read classified articles. #50 OPEN: entities_isins can carry the wrong ISIN — blast-radius grows with the watchlist since every watchlist name now pulls daily news, #29.)
* **suggestion_runs** — append-only. 5.16 (TD35): `_persist_run` sets `run.id`. notes is a JSON string `{dossiers:[...]}`. (#29: SuggestionRun.universe_size now reflects NIFTY 100 ∪ watchlist; the buy-pipeline log line says "N names (NIFTY 100 + watchlist)".)
* **suggestion_outcomes** — one doc per top-K candidate per run. snapshot_open_outcomes returns its count under `active_outcomes` (#47).
* **tavily_quota** — one doc per UTC day. **INVARIANT: TAVILY_DAILY_CALL_LIMIT (default 200) hard ceiling on calls_today per UTC day; credits tracked NOT capped; resets 00:00 UTC** (#48/TD36). Indexes: unique date_unique on date_utc. #19/TD33 atomic find_one_and_update. (#29: each watchlist name adds ~1 Tavily call/run to the news fetch — the data-volume multiplier; with NIFTY100 ≈ 100 + held + watchlist against the 200 ceiling, a watchlist up to ~80–90 names stays safe; beyond that the atomic guard degrades the run safely. Documented soft guardrail; NO hard cap on watchlist size enforced.)
* **digest_deliveries** — audit log of weekly digests. #21/TD35: run_id via run.id.
* **cron_heartbeats** (F4) — **INVARIANTS:** append-only, best-effort WITH DISK FALLBACK (5.18 #23/TD38). TTL 60 days. (Chat 8 added NO crons — watchlist CRUD is request-driven; the data-volume change rides the existing refresh_fundamentals + fetch_news_for_universe crons. Chat B added NO crons.)
* **conversations** (#27 — ACTIVELY WRITTEN) — one doc per ad-hoc chat exchange. **INVARIANTS:** written ONLY by conversation_service._persist_conversation; chat read-only on Phase-1 + suggestion runs.

**Scaffold (not actively written):** digests, macro_signals. (alerts_log is now WRITTEN as of #41 — stop_loss_hit rows.)
**Future:** none pending. F11 read-only reformatter (Chat 9/#39). (#29 F13 watchlist needed NO new collection — it reuses monitored_stocks status="watchlist".)

## Section 8: API endpoints (exhaustive)

**Phase 1**
```
GET    /health                                       (done #34: pings Mongo; 200 ok/ok or 503 degraded/fail)
GET    /portfolio/holdings                           Holding[]
GET    /portfolio/holdings/{isin}                    Holding
POST   /portfolio/holdings                           Holding (BUY)            (#7: recorded_with_warning)
PATCH  /portfolio/holdings/{isin}                    Holding (notes/thesis/stop_loss/target_price/tags only)
POST   /portfolio/holdings/{isin}/sell               Holding OR {message, realized_total}   (#5; #7)
POST   /portfolio/holdings/{isin}/preview-sell       SellPreview                            (#33 unit-tested)
GET    /portfolio/holdings/{isin}/history?days=N     PriceBar[]
GET    /portfolio/holdings/{isin}/transactions       Transaction[]            (#6 dup handler deleted)
GET    /portfolio/summary                            PortfolioSummary
GET    /portfolio/risk-summary                       RiskSummary              (done #28 F12)
GET    /portfolio/by-tag?tag=X                       {tag, holdings, totals}  (done #28 F15)
GET    /transactions/search?...                      {results, total}         (#18 dropped $options:i)
GET    /transactions/{id}                            Transaction
PATCH  /transactions/{id}                            Transaction (requires reason)   (#4)
DELETE /transactions/{id}                            {deleted: true} (requires reason) (#4)
GET    /transactions/audit/recent?limit=N            AuditEntry[]
GET    /transactions/{id}/audit                      AuditEntry[]
POST   /reconciliation/snapshot                      ReconciliationSnapshot (manual)
GET    /reconciliation/snapshots                     ReconciliationSnapshot[]
POST   /reconciliation/auto-snapshot                 ReconciliationSnapshot (cron)   (done #25; #33 drift math unit-tested)
GET    /cost-basis/adjustments                       CostBasisAdjustment[]
GET    /instruments                                  symbol_overrides list
POST   /instruments                                  symbol_overrides upsert
GET    /instruments/search/{symbol_prefix}?limit=N   [{exchange, symbol, isin, name}]  (done #27 route-shadow fix)
GET    /instruments/{exchange}/{symbol}              full instrument metadata
DELETE /instruments/{exchange}/{symbol}              delete override
```

**Phase 2**
```
GET    /suggestions/latest?direction=buy|sell        SuggestionRun + enrichment
GET    /suggestions/runs?direction=buy|sell&...      {runs, total, limit, skip}
GET    /suggestions/runs/{run_id}                    SuggestionRun + enrichment
GET    /suggestions/performance?direction=buy|sell   SuggestionPerformance with by_bucket
POST   /suggestions/{isin}/feedback                  {isin, action, status, previous_status}   (#17; #26; #33 write-before-apply ordering unit-tested)
GET    /suggestions/{isin}/audit?limit=N             MonitoredStocksAuditEntry[] (F10)  (#17; #29: also surfaces watchlist_add/update/remove rows)
GET    /suggestions/feedback/audit/recent?limit=N    MonitoredStocksAuditEntry[] (F10)
GET    /cron/heartbeats?limit=N                      {heartbeats, health_summary}
```

**Watchlist (F13 / Chat 8 / #29 — LIVE)**
```
GET    /watchlist                                    WatchlistEntry[]   (price-enriched via bulk_get_latest_prices; newest last_user_interest_at first)
GET    /watchlist/{isin}                             WatchlistEntry     (404 if the ISIN isn't currently status=="watchlist"; ISIN pattern=r"^[A-Z0-9]{12}$")
PUT    /watchlist/{isin}                             WatchlistEntry     (idempotent create-or-update; body WatchlistUpsert extra="forbid", all fields optional + `note` audit-only; 404 if ISIN unknown in instruments; flips status to watchlist = un-excludes a previously rejected/acted ISIN; write-before-apply audit watchlist_add/update; Money->Decimal128; upsert on {isin})
DELETE /watchlist/{isin}                             {isin, deleted}    (hard-delete ONLY when status=="watchlist" — a tracking/passed/rejected feedback doc 404s here so it's never nuked; audit watchlist_remove BEFORE delete)
```
WatchlistEntry serialized shape: `{_id, isin, symbol, name?, exchange?, sector?, industry?, status:"watchlist", added_by?, added_reason?, added_at?, created_at?, updated_at?, last_user_interest_at?, target_buy_price? (string), alert_above? (string), alert_below? (string), alert_on? (string[]), tags? (string[]), user_notes?, thesis?, conviction? (float), current_price (string|null), price_as_of (iso|null)}`. Numeric/Decimal fields serialize as strings; price-only enrichment (no fundamentals/news folded in). A non-NIFTY100 watchlist name with no price ingested yet returns `current_price: null` until the next fundamentals/news/price cron picks it up (#29).

**Chat (F1 + F3 / Chat 6 / #27 — LIVE)**
```
POST   /chat/suggestions                             ChatConversation   (F1; body {query, sentiment_overlay?})
POST   /chat/holdings/{isin}                         ChatConversation   (F3; ISIN-validated; 404 if not a known NSE instrument; on-demand enrichment)
GET    /chat/history?scope=&isin=&limit=             ChatConversation[] (newest-first; scope in {suggestions,holding})
```

**Tax (F11 / #39 — LIVE, Chat 9)**
```
GET    /tax/capital-gains?fy=YYYY-YY   -> {fy, fy_start, fy_end, summary{stcg,ltcg,total: {realized_gain, proceeds, cost, lot_count}}, lots[{isin, symbol, name, buy_date, sell_date, quantity, buy_cost, sell_proceeds, gain, holding_period_days, gain_type}]}   (fy OPTIONAL -> current IST FY; Indian FY 1 Apr->31 Mar IST, SELL trade_date in IST decides the FY; LTCG = listed equity held strictly >12 calendar months else STCG; read-only over the Phase-1 ledger via holdings_service._fifo_replay; §49(2C) honored via the ledger, cost_basis_adjustments NOT re-applied; money as strings; 422 on malformed/non-consecutive fy)
```

**Future (planned, see master_todo):**
```
(none — #39 shipped; #40 frontend-only; #41 SHIPPED — a holdings.stop_loss intraday alert + alerts_log writer, NOT a new endpoint: the PATCH whitelist + get_holding already carried stop_loss)
```

**Admin (Ops / #36 — LIVE)**
```
POST   /admin/recompute/{isin}                       {status, isin, holding}   (Tailscale-only; ISIN pattern=r"^[A-Z0-9]{12}$"; delegates to holdings_service.recompute_holding (TD20 advisory lock; NO parallel recompute path); active result -> status="recomputed" + holding; recompute_holding None (full exit / no txns) -> status="no_active_holding" + holding:null (200, not 404); 409 on lock contention; 500 otherwise; the HTTP replacement for SSH-shell recovery of a stuck holding, the TD19/#7 fallback)
```

**Sell endpoint response shape (critical, often confused):** `POST /portfolio/holdings/{isin}/sell` returns one of: (a) full updated Holding (partial sell), (b) `{message, realized_total}` (full exit), (c) `{status:"recorded_with_warning", isin, warning}` (TD19). Frontend discriminates via type guard on `_id`.

**CORS note (Chat 8 / #29):** `CORSMiddleware allow_methods` MUST list every method the frontend uses. It is `["GET","POST","PUT","PATCH","DELETE","OPTIONS"]` — `PUT` was added for `PUT /watchlist/{isin}`. A missing method makes the browser's preflight `OPTIONS` return non-200 ("Response to preflight request doesn't pass access control check"), blocking the real request — but curl from inside the box does NOT do CORS preflight, so server-side curl tests pass while the browser fails. Test browser-affecting CORS with a simulated preflight: `curl -X OPTIONS … -H 'Origin: …' -H 'Access-Control-Request-Method: PUT'`.

## Section 9: Cron registry on EC2

`crontab -l` for current state. Every script is heartbeat-instrumented via `cron_run()`; the daily `cron_health_check` (21:00 IST) consumes them. `CRON_REGISTRY` in `cron_heartbeat_service.py` is the in-code mirror — keep both in sync. (Chats 6, 7 and 8 added NO crons — chat + risk-summary + by-tag + watchlist CRUD are all request-driven. Chat 8's data-volume change rides the EXISTING `refresh_fundamentals` (Sun 06:00 IST) + `fetch_news_for_universe` (Sun 06:30 IST) crons, which now fold in watchlist ISINs. Chat B added NO crons — #33 is a test harness, not a runtime job.)

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
(Each line is `cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. /home/ubuntu/.local/bin/uv run python <script>`. The `PYTHONPATH=.` is load-bearing — without it `import app` fails; this is the same `ModuleNotFoundError: app` that bites a by-file-path `uv run python scripts/X.py` invocation, Chat 8.)

**CRON_REGISTRY (11 entries, 5.12):** refresh_instruments, refresh_prices, refresh_prices_intraday, take_reconciliation_snapshot, refresh_fundamentals (#29: now also covers watchlist ISINs — same cron, larger universe), fetch_news_for_universe (#29: now also covers watchlist ISINs — same cron, the Tavily data-volume multiplier), weekly_suggestions (renamed 5.9 TD14), track_suggestion_outcomes, cron_health_check, purge_news_bodies (5.12), weekly_suggestions_sell (idle; `expected_weekdays=set()` as of Chat A #49/TD40).

**No silent failures:** every cron = log file path AND heartbeat instrumentation AND a CronSpec entry. AND the CronSpec.cron_name MUST equal the string the script passes to `cron_run()` (5.9 TD14). 5.18 (#23/TD38) disk fallback. Chat A #47 fixed track_suggestion_outcomes.

**Health-check self-resilience (5.19 #24/TD39):** `cron_health_check.main`'s per-cron Mongo-read loop is wrapped to fire a dual-transport self-failure alert then RE-RAISE. The #23 merge loop is preserved inside.

**Dual transport (commit 8):** cron_health_check.py sends every anomaly batch on `push_public("errors",...)` + `notify.email(...)` and raises ONLY when BOTH fail.

**Coverage notes:** Chat 8 #29 IS HTTP-surfaced → covered by live curls on EC2 (PUT create/update with target_buy_price survival, GET list/one, DELETE, 404 on unknown ISIN / non-watchlist / deleted, 422 on extra field, audit add→update trail, universe union in_universe:True) + a simulated CORS preflight OPTIONS for the PUT + an end-to-end `uv run python -m scripts.refresh_fundamentals --symbols 20MICRONS` (Succeeded 1/1) + frontend `npm run build`/lint via ~/deploy-ui.sh + a browser add/remove smoke over Tailscale. Chat B #33 is covered by `uv run python -m pytest tests/ -v` on EC2 (28 passed) + the hygiene guard still PASSED.

**Open scheduling work:** TD21/#46 registry-generated crontab migration (deferred; its own dedicated chat).

## Section 10: Settings and environment variables

In `app/config/settings.py` via pydantic-settings. All required unless marked default.

* **Anthropic:** ANTHROPIC_API_KEY (req) · ANTHROPIC_MODEL_PRIMARY (default "claude-sonnet-4-5") · ANTHROPIC_MODEL_FAST (default "claude-haiku-4-5").
* **MongoDB:** MONGODB_URI (req; URL-encode special chars). Code uses `MONGODB_URI` not `MONGODB_URL` (#16/TD30). MONGODB_DB_NAME (req) — live value `portfolio`.
* **Tavily:** TAVILY_API_KEY (req) · TAVILY_DAILY_CALL_LIMIT (default 200) — hard ceiling on calls_today per UTC day, enforced atomically (TD33); DAILY resets 00:00 UTC (#48/TD36) · TAVILY_SEARCH_DEPTH (default "basic") · TAVILY_MAX_RESULTS_PER_QUERY (default 5). (#29: the watchlist data-volume multiplier consumes this quota — a soft guardrail, NOT an env knob; there is no max-watchlist-size setting.)
* **Email (Resend):** RESEND_API_KEY (req) · RESEND_FROM · RESEND_TO · DIGEST_TO. No new env for the TD34 retry.
* **ntfy:** NTFY_PUBLIC_URL (default "https://ntfy.sh") · NTFY_PUBLIC_TOPIC_PRICE/NEWS/ERRORS/DIGESTS · NTFY_PUBLIC_TOPIC_DIGESTS (F2b — REQUIRED, no default). `NTFY_URL/USER/PASS` REMOVED (5.5 TD9).

(No new env for #29 — the watchlist feature adds no settings; Tavily blast-radius is a documented soft guardrail, identity seeds come from instruments, and the CORS method list is a code-level middleware config in `main.py`. No new env for Chat B — #32 only pins `requires-python`; #33 only adds the dev-group `pytest>=8.3` + `[tool.pytest.ini_options] pythonpath=["."]` in pyproject.)

## Section 11: Phase 1 INVARIANTS — never violate

From `docs/data_flow.md`. Hard rules.
1. Transactions are immutable except through the audited PATCH/DELETE flow. (RESOLVED 5.10 #4/TD16.)
2. `recompute_holding(isin)` is the only authoritative writer to holdings. Idempotent. FIFO from scratch. Serialized per-ISIN via recompute_locks (TD20/#8). (Idempotency now regression-guarded by tests/test_recompute_holding.py — #33 Chat B.)
3. `validate_replay(transactions)` rejects any timeline producing negative quantity. (RESOLVED 5.10 #5/TD17. Regression-guarded by tests/test_validate_replay.py — #33 Chat B.)
4. `holdings.deleted_at = None` filter is universal. (#27 F3 held-overlay; #28 risk-summary + by-tag; #29 watchlist `build_universe` keeps held filtered downstream via filter_universe.)
5. Cost basis is IT-Act-correct, not broker-nominal.
6. prices_intraday writes are append-only within a day. (5.11 #9/TD23; 5.12 TD26 TTL; Chat A #35.)
7. Symbol search (GET /transactions/search) is case-sensitive by construction; NO $options:i (5.13 TD32). (Same family: GET /instruments/search/{symbol_prefix} and GET /portfolio/by-tag tag match — exact + case-sensitive.)
8. ICICI portfolio display shows TMPV ~₹813 and TMCV ~₹253 — cosmetically wrong vs our tax-correct numbers.
9. preview_sell correctly folds SPLIT/BONUS adjustments into the lot walk (5.6). (Regression-guarded by tests/test_preview_sell.py — #33 Chat B.)
10. Capital-gains tax view (F11/#39) is READ-ONLY on Phase 1: tax_service sources realized lots by replaying `transactions` through holdings_service._fifo_replay (the single FIFO source of truth — extended to emit per-disposal `_realized_lots`), NEVER a parallel FIFO path, and NEVER re-applies `cost_basis_adjustments` (the §49(2C) apportioned cost is already baked into the `manual_demerger` BUY rows — re-applying would double-count). The backend `holdings.realized_pnl` field STAYS even after #40 hides it in the UI, because FIFO + the capital-gains view both read it. (Chat 9.)

## Section 12: Phase 2 INVARIANTS

* suggestion_runs are append-only.
* The persisted run `_id` is carried on the in-memory SuggestionRun (5.16/TD35): callers read `run.id`. Do NOT re-derive.
* tavily_quota: one doc per UTC day, $inc counters. Hard ceiling on calls_today. 5.14 (#19/TD33) atomic. (#27 + #29 share this guard; TavilyQuotaExceeded degrades gracefully.)
* Confidence score is deterministic, NOT LLM-generated.
* The dossier prompt requires narrative-only output. The #27 chat system prompt carries the SAME constraint.
* gate_meta/group_meta/signal_meta/confidence_meta/feedback_meta/page_intro/user_action are PRESENTATION metadata via `_serialize_run`. Never in the persistent model.
* Snapshot eligibility for snapshot_open_outcomes is `tracking_status != "expired"`. snapshot_open_outcomes returns its count under `active_outcomes` (#47).
* `get_excluded_isins()` returns three buckets: rejected (90d), passed (this run only), acted (30d). NOT env-configurable. **It scans only status ∈ {rejected, tracking} — status=="watchlist" is structurally outside the scan, so a watchlist row is NEVER excluded; flipping a rejected/acted ISIN to watchlist (PUT /watchlist) auto-un-suppresses it. Do NOT add watchlist to the excluded scan (#29).**
* F10 write-before-apply: every POST /suggestions/{isin}/feedback writes monitored_stocks_audit BEFORE update_one. **Extended #29: every /watchlist mutation (PUT add/update, DELETE remove) writes monitored_stocks_audit via the SAME log_change BEFORE the apply, using the widened AuditAction Literal.** (The feedback write-before-apply ORDER is now regression-guarded by tests/test_submit_feedback.py — #33 Chat B.)
* A1: monitored_stocks feedback writes go through `MonitoredStockFeedbackPatch(...).model_dump(exclude_none=True)`. **#29: watchlist writes go through `MonitoredStockWatchlistPatch(...).model_dump(exclude_none=True)` then `_convert_decimals_to_decimal128` (the patch carries Money fields). Both keep monitored_stocks ONE doc per ISIN by upserting on `{isin}`.** SuggestionFeedback uses `extra="forbid"` (#26 direction default).
* The `notes` field on a SuggestionRun is a JSON string `{dossiers: [...]}`.
* 5.6 round-trip: every Phase-2 Pydantic model loads cleanly from any historical persisted doc.
* 5.13 (#17/TD31): ISIN Path() params carry `pattern=r"^[A-Z0-9]{12}$"`. (#27 reuses on /chat; #29 reuses on the three /watchlist/{isin} endpoints.)

**Watchlist (F13) INVARIANTS (Chat 8 / #29):**
* `build_universe()` = **NIFTY 100 ∪ watchlist**, deduped by ISIN — EVOLVE this function, do NOT fork a parallel universe builder. Watchlist ISINs outside NIFTY 100 are resolved from `instruments` by ISIN (warn on any not found). Held is NOT added here — it stays filtered DOWNSTREAM by `filter_universe`, so net buy candidates = `(NIFTY 100 ∪ watchlist) − held − rejected − acted`. The data-REFRESH universe (fundamentals + news crons) is `NIFTY 100 ∪ held ∪ watchlist`.
* `get_watchlist_isins()` (monitored_stocks status=="watchlist") is the SINGLE source of truth for membership — `build_universe`, `refresh_fundamentals.get_watchlist_instruments`, and `fetch_news_for_universe.get_watchlist_for_news` all reuse it. Do NOT write a second `status=="watchlist"` filter.
* `monitored_stocks` is ONE doc per ISIN; the watchlist writer upserts on `{isin}`. A watchlist state and a feedback state can never coexist as two rows. The `isin_unique_active` partial index (`status:"tracking"`) is untouched and does NOT need broadening — single-doc-per-ISIN is upheld at the app layer by the upsert.
* `/watchlist` reuses `monitored_stocks` (status="watchlist") — NO new collection. PUT 404s an unknown instrument; DELETE 404s a non-watchlist doc (so feedback rows are never nuked); GET enrichment is price-only (bulk_get_latest_prices), not fundamentals/news.
* The /watchlist CRUD path reuses the SAME `monitored_stocks_audit` collection via `log_change` (the action Literal was widened to `AuditAction`, not forked) and writes the audit row BEFORE the mutation (F10).
* The data-volume multiplier (every watchlist name → weekly fundamentals + earnings + daily news + ~1 Tavily call/run) is bounded by the existing TD33 atomic daily quota ceiling, NOT by a hard watchlist-size cap. The blast-radius is a DOCUMENTED soft guardrail.

**Portfolio read-aggregation INVARIANTS (Chat 7 / #28):**
* `compute_summary` and `compute_risk_summary` share ONE annotation path — `_annotate_holdings(holdings, latest_prices) -> (annotated, accum)`. Do NOT build a parallel aggregation for risk; evolve the helper. Gated by a `/portfolio/summary` curl-diff that prints `OK: /summary unchanged`.
* The risk-summary concentration figures are by construction identical to `/portfolio/summary`'s — `risk.concentration_by_holding[0] == summary.concentration[0]`.
* Risk thresholds are module constants in `portfolio_service.py` (SINGLE_HOLDING WARN 10 / HIGH 20, SECTOR WARN 30 / HIGH 50), NOT env-configurable.
* Holdings with no price are excluded from the % denominator and surface in the low-severity `stale_price` alert.
* `GET /portfolio/by-tag` reuses the `holdings.list_holdings` annotate path verbatim; tag match exact + case-sensitive array-membership on `holdings.tags`; missing/empty tag → 422; unknown tag → empty + zeroed totals (200). Imports `portfolio_service._to_dec` — no parallel converter.

**Chat (F1 + F3) INVARIANTS (Chat 6 / #27):**
* Chat is READ-ONLY on the user's portfolio + suggestion runs. It only WRITES `conversations`. On-demand enrichment may REFRESH shared Phase-2 reference collections via the SAME cron-path services — not a Phase-1 write.
* The chat LLM call is a SINGLE Sonnet call returning `{answer, intent}`, mirroring `dossier_service._generate_one`. No second Haiku classify call.
* `scope` discriminates the surface (suggestions|holding), distinct from `intent`. `cost_usd` is `Money`.
* `_persist_conversation` inserts then RE-READS the doc.
* The per-stock endpoint resolves ANY known NSE instrument via `lookup_by_isin`; unknown ISIN -> 404 (no yfinance rescue). Held -> position/tax overlay; not held -> buy-research framing.
* `follow_up_conversation_ids` is intentionally UNUSED.

**Test-harness INVARIANTS (Chat B / #33):**
* The `tests/*` harness is HERMETIC and zero-dependency — no Atlas, no network, no yfinance. DB-coupled targets run against the in-memory `FakeCollection` via the `fake_db` fixture (which monkeypatches the `Collections.*` accessors); external calls (`fetch_metadata`, `_get_our_numbers`, `_send_auto_drift_alert`, `log_change`) are monkeypatched. Do NOT add a real/scratch Mongo dependency to the harness.
* `FakeCollection` implements ONLY the operators the SUTs actually use (`$ne`/`$in`/`$nin`/`$exists`/`$or`/`$and`, `sort`/`skip`/`limit`, `$set`/`$setOnInsert`/upsert). If a future test needs a new operator, EXTEND `FakeCollection` minimally — do NOT reach for a heavyweight in-memory Mongo dep.
* Run tests as `uv run python -m pytest` (pyproject has `pythonpath=["."]`, so `import app` resolves). Re-run `uv run python -m scripts.check_datetime_hygiene` after any datetime edit — the test files themselves use only fixed datetimes (no `utcnow()`/aware-now) so they must keep the guard green.
* Before constructing any model/dict in a test (`tx(...)`, a Holding doc, a feedback patch), the field names were grepped against the @model/@dataclass at HEAD — Glean snippets are call sites, not definitions (standing Section-14 rule).

**F2 / F14 invariants (Chat 4):**
* SuggestionDirection literal = "buy" | "sell". Defaults "buy".
* `compute_system_performance(direction="sell")` SIGN-FLIPS excess_return. snapshot_open_outcomes is DIRECTION-AGNOSTIC.
* earnings_calendar refresh deletes future events then re-inserts.
* F14 earnings-proximity gate SHARED buy+sell, 5-day threshold.
* Sell-side uses different groups and gates. CandidateScore has FIXED buy-side group fields; sell-side via group_meta (TD7/#45 deferred).
* F2 combined-digest: --direction=both emits ONE email + ONE ntfy; run_id keys on buy_run.id.

**Chat 5 A2 (CLOSED):** notify.email() returns `{ok, id, error}` and SWALLOWS Resend exceptions. #20/TD34 (5.15): retries ONCE on transient 429/5xx with 30s backoff. push_public RAISES — #24, #25, #35 guard it.

**Chat 5.16 TD35 (CLOSED):** digest_delivery + run_weekly_suggestions read `run.id`. send_combined_digest signature UNCHANGED.

**Other CLOSED Phase-2 facts:** A3+A4 SignalScore.raw_value; 5.5 TD11 explainability fallback; commit 8 dual transport.

## Section 13: Shipped vs Open

**Phase 1 (all shipped, locked):** Holdings dashboard · FIFO cost basis · ICICI import→staging→reconcile→promote · Manual entry · Transaction edit/delete w/ audit (5.10 #4) · Transaction search (5.13 #18) · Preview-sell (5.6) · Reconciliation snapshots (Chat A #25) · Cost basis adjustments · EOD+intraday price refresh (5.11 #9; 5.12 #12; Chat A #35) · Tax vs broker view · Single-holding drill-down (5.13 #14; Chat 6 #27 embeds the F3 chat) · Audit log page · Dark mode · Reconciliation badge · Recent activity card · Global refresh button (5.13 #14) · `/health` honest Mongo readiness probe (Chat A #34) · `/instruments/search` reachable over HTTP (Chat 6 #27 route-shadow fix) · `/portfolio/risk-summary` concentration & risk alerts (Chat 7 #28) · `/portfolio/by-tag` tag views + dashboard risk card + `/tags` page (Chat 7 #28).

**Phase 2 Suggestions Engine:** Unit 1-3 · Commit A · A.5 / A.5.1 (Chat A #26 direction-aware relabel) · Commit B · Feedback/audit endpoints (5.13 #17) · Tavily quota (5.14 #19) · Weekly digest (5.16 #21) · Outcome-tracking cron (Chat A #47).

**Phase 8 New features:** **Chat 6 #27 ad-hoc chat (F1 + F3) SHIPPED.** **Chat 7 #28 risk-summary + tag views (F12 + F15) SHIPPED.** **Chat 8 #29 watchlist (F13) SHIPPED** — `MonitoredStockWatchlistPatch` + `build_universe` = NIFTY 100 ∪ watchlist + `get_watchlist_isins` (Unit 1), `/watchlist` CRUD reusing monitored_stocks status="watchlist" + widened audit `AuditAction` (Unit 2), both crons fold in watchlist ISINs as the data-volume multiplier (Unit 3), frontend `/watchlist` page + nav (Unit 4), + the CORS `allow_methods` PUT fix. No new collection/index/npm dependency. **Phase 8 COMPLETE — #27 + #28 + #29 all SHIPPED.**

**Phase 9 pre-GO-LIVE hygiene sweep (Chat B — COMPLETE):** **#30 (datetime.utcnow() sweep) + #31 (tz-aware Mongo-write sweep + `scripts/check_datetime_hygiene.py` guard) + #32 (Python ceiling pin) SHIPPED 2026-06-15.** **#33 (pytest harness) SHIPPED 2026-06-26** — hermetic, zero-dependency `tests/*` (in-memory FakeCollection + fake_db fixture), 28 tests across `_fifo_replay` / `validate_replay` / `preview_sell` / `recompute_holding` idempotency / `submit_feedback` write-before-apply ordering / `take_auto_snapshot` drift math; runs via `uv run python -m pytest`. **#36 (`POST /admin/recompute/{isin}`, Tailscale-only) SHIPPED 2026-07-01** — NEW `app/routers/admin.py` registered in `app/main.py`, delegates to `holdings_service.recompute_holding` (TD20; no parallel path); `{status: recomputed/no_active_holding, isin, holding}`, 409 on lock contention. **#37 (Atlas backup → fresh-DB restore rehearsal) SHIPPED 2026-07-01** — DOC + OPS only (no `app/` code): rehearsed per-collection `mongodump --db=portfolio --collection=<name>` (this `mongodump` 100.17.0 rejects `--nsInclude`) → `mongorestore --nsFrom 'portfolio.*' --nsTo 'portfolio_restore_test.*' --drop` into a fresh scratch DB on EC2; counts matched prod (2 / 155 / 10), scratch DB dropped, prod `portfolio` untouched; exact dump/restore/verify/cleanup runbook documented in Section 4. **#38 (JSON-structured logging) SHIPPED 2026-07-01** — `app/main.py` `logging.basicConfig` -> stdlib `JsonLogFormatter` (`logging.Formatter` subclass, no new dependency) + `_configure_logging()` over root + `uvicorn`/`uvicorn.error`/`uvicorn.access` (`propagate=False`); one single-line JSON object/record to journald (timestamp UTC ms+Z from `record.created`; level/logger/message/module/func/line; traceback on exc_info; `extra` merged); verified on EC2 (hygiene PASSED, 28 pytest, JSON app + `uvicorn.access` logs valid, no double-logging). #34 + #35 SHIPPED earlier in Chat A. #38 was the LAST Chat B row — **Chat B / Phase 9 COMPLETE.**

**Phase 10 pre-launch cleanup (Chat 9 #39 + Chat C #40/#41 — ALL SHIPPED):** **#39 (F11 capital-gains pack) SHIPPED 2026-07-01** — NEW `GET /tax/capital-gains?fy=YYYY-YY` (STCG/LTCG per-lot breakdown + summary for the Indian FY, 1 Apr->31 Mar IST) backed by NEW `app/services/tax_service.py` (read-only over the ledger; replays via `holdings_service._fifo_replay`, the single FIFO source of truth extended to emit per-disposal `_realized_lots`; strict >12-calendar-month LTCG; §49(2C) via the `manual_demerger` ledger rows, `cost_basis_adjustments` not re-applied) + NEW `app/routers/tax.py` (`fy` optional -> current IST FY, 422 on malformed/non-consecutive fy) + NEW frontend `app/tax/page.tsx` (`/tax` route, FY selector + STCG/LTCG/Total cards + disposals table, printable) + `lib/api.ts` bindings + Tax nav. Backend `32088c9`, frontend `747ae4f`. Verified on EC2: 49 pytest passed, hygiene guard PASSED, endpoint + page live. Filed the bonus/demerger holding-period nuance as NEW-ITEMS #53 (read-only-on-Phase-1 limitation). **#40 (realized-P&L UI hide) SHIPPED 2026-07-03 (Chat C, frontend-only, `16fab5ae`) — removed the dashboard "Realized P&L" StatCard (`totals-row.tsx`; grid 4->3, dropped now-unused `TrendingUp`) + shrank the `app/page.tsx` DashboardSkeleton 4->3; backend `holdings.realized_pnl` field STAYS (FIFO + #39 read it); `/tax`, sell-sheet realized preview/toast, and transactions/audit copy intentionally untouched. #41 (stop_loss wiring) SHIPPED 2026-07-03 (Chat C, single logical unit, backend `eb964cc8` + frontend `a4b27bd7`) — NEW `price_service.evaluate_stop_loss_alerts(rows)` on the existing intraday write path (called guarded by `scripts/refresh_prices_intraday.py` after `insert_intraday_quotes`, same fetched rows, no parallel loop); rising-edge fire-once-on-cross-below, success-gated dedup (only a DELIVERED `stop_loss_hit` Alert suppresses; re-arm on a later at/above tick), gated on `stop_loss` set AND `"stop_loss" in alert_on`; ntfy-only via `push_public("price", ...)`; persists `Alert(alert_type="stop_loss_hit", channel="ntfy_public_price", severity="high")` to `alerts_log` (FIRST writer) + NEW dedup index `isin_type_sent_desc`; NO `routers/holdings.py` change (PATCH whitelist + `get_holding` already sufficient); frontend `components/holding-stats.tsx` gains a read-only stop-loss strip while editing stays in `notes-panel.tsx`. Verified on EC2: 49 pytest, hygiene PASSED, `alerts_log` 5 indexes, functional 1/0/1, deploy-ui build+lint clean. Closes TD6. Phase 10 is now fully SHIPPED.**

**Cross-cutting:** Transactional email via notify.email() (Chat 5 A2; 5.15 #20) · Cron observability (Chat 2; 5.18 #23; 5.19 #24; Chat A #49) · Stateful feedback (Chat 3) · Sell-side (Chat 4) · Model-layer NaN guard (5.17 #22) · datetime-hygiene machine guard (Chat B #31) · pytest regression harness (Chat B #33).

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
| 6 | 2026-06-14 | #27 F1+F3 ad-hoc chat (Phase 8). Unit 1 data layer (open base `4403bb5`) → Unit 2 enrichment `c407985` → Unit 3 chat service + endpoints (`15ea9c0`→`dd82636`) → `/instruments/search` route-shadow fix `5e787c9`. Frontend Unit 4 `6093f63`. Filed #50 + #51. | backend `5e787c9` / frontend `6093f63` |
| 7 | 2026-06-15 | #28 F12 risk-summary + F15 by-tag (Phase 8). Backend Unit 1 `97041621` → Unit 2 `803e6610`. Frontend Unit 3 + Unit 4 `e14d6a75`. Read-only; no new collections/indexes/deps; no new TD/follow-ups. | backend `803e6610` / frontend `e14d6a75` |
| 8 | 2026-06-15 | #29 F13 watchlist (Phase 8 — COMPLETE). Backend Unit 1 write-model + universe `34ff906d` → Unit 2 /watchlist CRUD `a250d001` → Unit 3 cron coverage `9857570b` → CORS fix `67704025`. Frontend Unit 4 `58bf6369`. Evolved build_universe + reused monitored_stocks; no new collection/index/dep; no new TD/follow-ups. ALSO added the Phase 10.5 USER ACCEPTANCE REVIEW stage (#52) at the user's request. | backend `67704025` / frontend `58bf6369` |
| B | 2026-06-15 → 2026-07-01 | Phase 9 pre-GO-LIVE hygiene sweep (COMPLETE). #30 P2-1 (11 `datetime.utcnow()`->`utcnow()` sites / 5 files, incl. 2 `conversation_service` stragglers the row's stale list missed) + #31 P2-8 (tree-wide tz-aware Mongo-write sweep -> `utcnow()`, 15 sites, + 19 `# tz-ok:` annotations + NEW `scripts/check_datetime_hygiene.py` tokenize-based guard) + #32 P3-2 (`requires-python = ">=3.12,<3.14"` + `uv lock` relock) SHIPPED 2026-06-15 on `025b8a0`. #33 Review-note pytest harness (hermetic, zero-dependency `tests/*` — `_fakes.py` FakeCollection + `conftest.py` fake_db fixture + 6 test files, 28 tests across the 6 targets incl. recompute_holding full DB idempotency; no new deps; `uv run python -m pytest` => 28 passed) SHIPPED 2026-06-26 on `04fd970`. Backend + test/doc only; frontend unchanged. #36 (`POST /admin/recompute/{isin}` Tailscale-only — NEW `app/routers/admin.py` delegating to `recompute_holding` TD20, registered in `main.py`; verified on EC2) SHIPPED 2026-07-01 on `1ef0ead`. #37 (Atlas backup → fresh-DB restore rehearsal — per-collection `mongodump`/`mongorestore --nsFrom/--nsTo` into a dropped scratch DB; counts matched prod 2/155/10; runbook documented in Section 4) SHIPPED 2026-07-01, DOC + OPS only so code HEAD stays `1ef0ead`. #38 (JSON-structured logging — `app/main.py` `logging.basicConfig` -> stdlib `JsonLogFormatter` + `_configure_logging()` over root + `uvicorn`/`uvicorn.access`, `propagate=False`; one JSON object/record to journald; no new dependency; verified on EC2) SHIPPED 2026-07-01 on `8127c6f`. Chat B / Phase 9 COMPLETE. Frontend reconciled to `c5bb1a34` (one docs-only commit `c5bb1a3`, #29 README/nav, not code). | backend `8127c6f` / frontend `c5bb1a34` |
| 9 | 2026-07-01 | #39 F11 capital-gains pack (Phase 10). Backend Unit 1 `32088c9` (NEW `tax_service.py` + `tax.py` + `_fifo_replay` `_realized_lots` + `tests/test_tax_service.py` + `main.py` include) -> frontend Unit 2 `747ae4f` (NEW `app/tax/page.tsx` + `lib/api.ts` + Tax nav). Read-only over the Phase-1 ledger; §49(2C) via the ledger; single FIFO source of truth, no parallel path; no new dep. Verified on EC2 (49 pytest, hygiene guard, endpoint + page live). Filed #53 (bonus/demerger holding-period nuance). | backend `32088c9` / frontend `747ae4f` |
| C | 2026-07-03 | #40 realized-P&L UI hide + #41 stop_loss wiring (Phase 10, Chat C). #40 frontend-only — removed the "Realized P&L" StatCard from `components/totals-row.tsx` (grid 4->3, dropped now-unused `TrendingUp` import) + shrank `app/page.tsx` DashboardSkeleton 4->3; backend `holdings.realized_pnl` field STAYS (FIFO + #39 capital-gains read it); `/tax`, sell-sheet preview/toast, transactions/audit copy KEPT. #41 backend+frontend single unit — NEW `price_service.evaluate_stop_loss_alerts(rows)` on the existing intraday write path (guarded call from `refresh_prices_intraday.py` after `insert_intraday_quotes`), rising-edge + success-gated dedup, ntfy-only `push_public("price",...)`, first writer of `alerts_log` (`Alert alert_type="stop_loss_hit"`) + NEW dedup index `isin_type_sent_desc`; no `holdings.py` change; frontend read-only stop-loss strip in `holding-stats.tsx` (editing stays in `notes-panel.tsx`). Verified on EC2 (49 pytest, hygiene PASSED, functional 1/0/1, deploy-ui clean). Closes TD6; Phase 10 fully SHIPPED. | backend `eb964cc8` / frontend `a4b27bd7` |

The Chat 5.10 SellSheet recorded_with_warning follow-up remains OPEN and untouched through Chat B.

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
| 8 | #27-29 | Chat 6 (F1+F3), Chat 7 (F12+F15), Chat 8 (F13 watchlist) | COMPLETE — #27 Chat 6; #28 Chat 7; #29 Chat 8 |
| 9 | #30-38 | Cross-cutting cleanup before GO LIVE | COMPLETE — #34 + #35 SHIPPED (Chat A); #30 + #31 + #32 SHIPPED 2026-06-15 (Chat B); #33 SHIPPED 2026-06-26 (Chat B); #36 SHIPPED 2026-07-01 (Chat B); #37 SHIPPED 2026-07-01 (Chat B); #38 SHIPPED 2026-07-01 (Chat B); Phase 9 COMPLETE |
| 10 | #39-41 | Chat 9 pre-launch cleanup | COMPLETE — #39 SHIPPED 2026-07-01 (Chat 9); #40 SHIPPED 2026-07-03 (Chat C); #41 SHIPPED 2026-07-03 (Chat C) |
| 10.5 | #52 | USER ACCEPTANCE REVIEW (user walks the whole tool) | OPEN — second-to-last; gates GO LIVE (NEW Chat 8) |
| 11 | #42 | Chat 10 GO LIVE (F7 real data import) | OPEN — gated behind Phase 10.5 |
| 12 | #43-45 | Deferred TDs (TD1, TD3, TD7) | DEFERRED |
| — | #46-53 | TD21 scheduler (OPEN), TD22 (SHIPPED A), TD36 (SHIPPED A), TD40 (SHIPPED A), #50 news entity mis-tagging (OPEN, Chat 6), #51 dividend_yield ×100 (OPEN, Chat 6), #53 bonus/demerger holding-period nuance (OPEN, Chat 9) | #46/#50/#51/#53 OPEN; #47/#48/#49 SHIPPED |

**Chat-bundle overlay (added 5.19, source of truth = master_todo.md "Chat bundles").** Remaining OPEN rows are grouped (NOT renumbered) into chats: **Chat A** (COMPLETE), **Chat 6** (COMPLETE), **Chat 7** (COMPLETE), **Chat 8** (COMPLETE), **Chat B** (#30, #31, #32 SHIPPED 2026-06-15; #33 SHIPPED 2026-06-26; #36, #37, #38 SHIPPED 2026-07-01 — COMPLETE), **Chat C** (#40 + #41 SHIPPED 2026-07-03 — COMPLETE), **Chat D** (#43, #44, #45), and standalone large items kept one-per-chat: #39 (Chat 9 — SHIPPED 2026-07-01), **#52 (User Review chat — NEW Chat 8, second-to-last; NEXT)**, #42 (Chat 10 GO LIVE, gated behind #52), #46 (scheduler). Bundles never override a per-row gating dependency.

**Open items carried past Chat B** (tracked in master_todo.md; pointer now at #52; Phase 10 fully SHIPPED — #39 2026-07-01, #40 + #41 2026-07-03 Chat C):
* **#39 (Phase 10 / Chat 9 — F11) SHIPPED 2026-07-01:** capital-gains pack — NEW `GET /tax/capital-gains?fy=YYYY-YY` (STCG/LTCG per-lot breakdown + summary for the FY) + NEW `routers/tax.py` + NEW `services/tax_service.py` + NEW frontend `app/tax/page.tsx`; backend `32088c9`, frontend `747ae4f`; read-only over the Phase-1 ledger, §49(2C) via the ledger, single FIFO source of truth (no parallel path); filed #53. **#40 (Chat C) is now NEXT.** (Chat B / Phase 9 is now COMPLETE: #30 `datetime.utcnow()` sweep + #31 tz-aware Mongo-write sweep + `scripts/check_datetime_hygiene.py` guard + #32 Python ceiling SHIPPED 2026-06-15; #33 pytest harness SHIPPED 2026-06-26; #36 admin recompute endpoint SHIPPED 2026-07-01 on `1ef0ead`; #37 Atlas backup → fresh-DB restore rehearsal SHIPPED 2026-07-01, DOC + OPS only — runbook in Section 4; #38 JSON-structured logging SHIPPED 2026-07-01 on `8127c6f`.)
* **#40 + #41 (Chat C — COMPLETE):** #40 realized-P&L UI hide SHIPPED 2026-07-03 (Chat C, frontend-only, `16fab5ae`); #41 stop_loss wiring SHIPPED 2026-07-03 (Chat C, backend `eb964cc8` + frontend `a4b27bd7`, closes TD6). (#39 F11 capital-gains SHIPPED 2026-07-01.) NEXT: #52 (Phase 10.5 User Acceptance Review).
* **#52 (User Review chat / Phase 10.5, NEW):** complete user acceptance review; second-to-last; gates GO LIVE.
* **#42 (Chat 10 / F7):** GO LIVE real ICICI import — gated behind #52.
* **#43–#45 (Chat D, DEFERRED):** TD1/TD3/TD7.
* **#46 (TD21):** registry-generated crontab migration; dedicated chat.
* **#50 (Chat 6):** news entity mis-tagging in `news_articles.entities_isins` (blast-radius widened by #29 watchlist news pulls).
* **#51 (Chat 6):** `dividend_yield` ×100 formatting.
* **#53 (Chat 9):** bonus/demerger holding-period nuance in the F11 capital-gains view — because #39 is read-only on Phase-1 FIFO, buy_date/cost for bonus & demerger lots reflect the ledger encoding (bonus diluted in place keeping the original trade_date; demerger as manual BUY rows), not the strict IT-Act treatment (bonus = zero cost + holding period from allotment; demerger = inherit original holding period). Fix needs Phase-1 FIFO changes; out of #39 scope.

## Section 14: Conventions the assistant has repeatedly drifted on

Memorize these.
* Port 8001 (Mac local), 8000 (EC2). Always specify which.
* SSH-first for tests: every test block begins `ssh ubuntu@100.112.20.41` and curls `localhost:8000`. (Frontend-only: `~/deploy-ui.sh` + `npm run build`/lint on EC2.) (Chat B #33: pytest also runs on EC2 — `uv run python -m pytest`.)
* Run scripts as MODULES from the repo root (`uv run python -m scripts.X`, or `PYTHONPATH=. … scripts/X.py`); a by-file-path `uv run python scripts/X.py` raises `ModuleNotFoundError: No module named 'app'` — invocation-path error, not a code bug (Chat 8). Tests run via `uv run python -m pytest` (pyproject `pythonpath=["."]`).
* Commit-block-after-code: every code/file delivery followed by paste-ready `git add .` + `git commit -m`.
* Project_State.md AND master_todo.md are ALWAYS complete full-file replacements.
* F6 two-mechanism feedback exclusion: both `get_excluded_isins` (run-build) AND `_build_user_action` (serialization) required.
* 90-day rejected cooldown and 30-day acted soft-exclude are NOT env-configurable.
* F10 write-before-apply: `log_change(...)` BEFORE `update_one(...)` / `delete_one(...)`. (Chat 8: the /watchlist CRUD reuses the SAME audit collection + log_change for add/update/remove. Chat B #33: this ordering is now regression-guarded by tests/test_submit_feedback.py.)
* Secrets path on EC2: `/etc/portfolio-advisor/secrets.env`.
* `lib/api.ts` hand-typed; `lib/api-types.ts` gitignored.
* Mutations use `refetchQueries` (synchronous), NOT `invalidateQueries`. (Chat 6 ChatPanel, Chat 7 /tags + risk query, Chat 8 watchlist page all follow this.)
* `cn` at `@/lib/utils`. Format helpers at `@/lib/format`.
* Collections accessor: `from app.db.client import Collections`. (Chat B #33: patching the `Collections.*` accessor at the class level is seen by every importer because they share the one class object and call the accessor at call-time — that's why the `fake_db` fixture works.)
* Decimal128 vs Decimal: helpers in `app/models/_common.py`. BaseDoc.to_mongo() = model_dump(by_alias=True, exclude_none=True) + Decimal→Decimal128; extra="forbid". (Chat 8: a typed write-patch carrying Money fields must be run through `_convert_decimals_to_decimal128` before update_one — the feedback patch had no Money fields, the watchlist patch does.)
* Datetimes: UTC-naive in Mongo, IST in UI. `utcnow()` from `app/models/_common.py`. (Chat B #30/#31: machine-enforced — `datetime.utcnow()` is BANNED tree-wide and every tz-aware `datetime.now(timezone.utc)` is either swapped to `utcnow()` (Mongo writes) or annotated `# tz-ok: <reason>` (in-memory). Run `uv run python -m scripts.check_datetime_hygiene` after any datetime edit.)
* Heredoc for multi-line Python: `<<'EOF'` form.
* Every cron script: `cron_run()` + CronSpec + crontab line. AND CronSpec.cron_name == the name passed to `cron_run()` (5.9 TD14).
* Direction-aware display layer: branch at the display layer, not by forking the model.
* Symbol search regex is case-sensitive on purpose; NO $options:i (5.13 TD32).
* ISIN Path() params validate charset with `pattern=r"^[A-Z0-9]{12}$"` plus min/max_length. (5.13 TD31; reused on /chat, Chat 6, and on /watchlist/{isin}, Chat 8.)
* Tavily daily quota enforced ATOMICALLY (5.14 TD33). DAILY (resets 00:00 UTC), not monthly (Chat A TD36).
* notify.email() retries a TRANSIENT Resend failure (429+5xx) ONCE with 30s backoff; contract unchanged. push_public RAISES — guard it. (5.15 TD34.)
* The persisted SuggestionRun._id is carried on `run.id`; read run.id, don't re-derive. (5.16 TD35.)
* `_to_decimal` rejects a NaN float with `ValueError("NaN not allowed")`. (5.17 TD37.)
* Cron heartbeats are best-effort WITH a disk fallback (5.18 TD38).
* `cron_health_check.main`'s per-cron read loop fires a dual-transport self-failure alert and RE-RAISES (5.19 TD39).
* (Chat A) `/health` reflects Mongo reachability in the STATUS CODE (503/200); no yfinance on the hot path (#34). `take_auto_snapshot` alerts ntfy ONLY, rising-edge deduped (#25). An "add `payload.X`" instruction can reference a non-existent payload field — grep the model (#26). Grep the PRODUCER's return dict for exact key names (#47). An idle CronSpec must carry `expected_weekdays=set()` (#49). Read the code for the ACTUAL boundary before a "monthly→daily" wording fix (#48).
* **(Chat 6) FastAPI matches routes in REGISTRATION ORDER — a STATIC route must be declared BEFORE a sibling DYNAMIC route (#27). The ad-hoc chat is ONE Sonnet `{answer,intent}` call mirroring `dossier_service._generate_one` — no second Haiku call (#27). Chat writes only `conversations`; on-demand enrichment refreshes shared Phase-2 reference collections via the SAME cron-path services (#27). Unknown ISIN -> 404, no yfinance rescue (#27). Reimplement the CandidateScore-coupled position block rather than call it (#27). No markdown npm dependency — use `MarkdownLite` (#27).**
* **(Chat 7) A new read-aggregation endpoint EVOLVES `compute_summary` via a shared `_annotate_holdings` helper — gate the behaviour-preserving extraction with a `/summary` curl-diff (#28). Risk thresholds are module constants, two-tier (#28). `GET /portfolio/by-tag` reuses the `list_holdings` annotate path; exact case-sensitive tag match; required tag->422, unknown tag->zeroed 200; import `_to_dec`, no parallel converter (#28). A new dashboard surface gets its own independent `useQuery`; add NEW api.ts types when existing ones don't match; reuse `<HoldingsTable>`; no new shadcn/npm dep (#28).**
* **(Chat 8) `build_universe()` EVOLVES to NIFTY 100 ∪ watchlist — do NOT fork a parallel universe builder; resolve watchlist ISINs outside NIFTY 100 from `instruments`; keep held filtered DOWNSTREAM via `filter_universe`. `get_watchlist_isins()` (status=="watchlist") is the SINGLE source of truth reused by build_universe + both cron scripts — no second `status=="watchlist"` filter (#29).**
* **(Chat 8) F13 watchlist REUSES `monitored_stocks` with `status="watchlist"` — NO new collection. `monitored_stocks` is ONE doc per ISIN (upsert on `{isin}`), so a watchlist state and a feedback state can never be two rows; the `isin_unique_active` partial index (`status:"tracking"`) is untouched and does NOT need broadening. `get_excluded_isins` scans only rejected/tracking, so watchlist is structurally never excluded; flipping rejected→watchlist auto-un-suppresses — do NOT add watchlist to the excluded scan (#29).**
* **(Chat 8) The /watchlist CRUD reuses the SAME `monitored_stocks_audit` collection — WIDEN the action Literal to `AuditAction` (add watchlist_add/update/remove), don't fork an audit. PUT 404s an unknown instrument; DELETE 404s a non-watchlist doc so a feedback row is never nuked. A typed write-patch with Money fields must go through `_convert_decimals_to_decimal128` before Mongo (#29).**
* **(Chat 8) The two cron scripts (`refresh_fundamentals` + `fetch_news_for_universe`) fold in watchlist ISINs — THE data-volume multiplier. Each watchlist name adds ~1 Tavily call/run; the blast-radius is bounded by the EXISTING TD33 atomic daily ceiling (degrades safely), documented as a SOFT guardrail — NO hard watchlist-size cap (#29).**
* **(Chat 8) CORS `allow_methods` must list every method the frontend uses (PUT was missing for the watchlist upsert). A missing method 503s the browser preflight even though curl-from-box passes — test browser-affecting CORS with a simulated preflight `OPTIONS` (#29).**
* **(Chat 8) When the user explicitly directs a roadmap change, make it a REAL numbered row + phase (Phase 10.5 / #52 USER ACCEPTANCE REVIEW) and thread it through the pointer, ordering rationale, chat bundles, and every summary table — do NOT renumber existing rows or phases (used Phase "10.5" to avoid cascading the GO-LIVE=Phase 11 / Deferred=Phase 12 references).**
* **(Chat B) The `app.models._common.utcnow()` naive-UTC storage invariant is now MACHINE-ENFORCED by `scripts/check_datetime_hygiene.py` (#31): stdlib `utcnow()` is BANNED tree-wide; every tz-aware `datetime.now(timezone.utc)` must be either swapped to `utcnow()` (Mongo writes) OR carry a trailing `# tz-ok: <reason>` annotation (in-memory compares / `astimezone(IST)` / JSON `as_of` / date-string computes). The guard is TOKENIZE-based, not line-based, so the formatter wrapping a long statement (parking the `# tz-ok` comment on the closing-bracket line) does NOT defeat it; it is comment-aware, self-skipping, and fragment-builds its needles so it won't trip the existing greps. A `replace_all`-style swap can silently MISS a near-duplicate site (it missed reconciliation `take_manual_snapshot` + price_service `bulk_get_latest_intraday`) — the guard is what catches it, so RE-RUN `uv run python -m scripts.check_datetime_hygiene` after any datetime edit (#30/#31).**
* **(Chat B) The pytest harness is HERMETIC + zero-dependency — DB-coupled targets run against an in-memory `FakeCollection` via the `fake_db` fixture (monkeypatches the `Collections.*` accessors); external calls (`fetch_metadata`/`_get_our_numbers`/`_send_auto_drift_alert`/`log_change`) are monkeypatched; do NOT add a real/scratch Mongo or a heavyweight in-memory-Mongo dependency. `FakeCollection` implements ONLY the operators the SUTs use — EXTEND it minimally if a future test needs more. Run as `uv run python -m pytest` (pyproject `pythonpath=["."]`). Before constructing any model/dict in a test, grep the @model definition at HEAD — Glean snippets are call sites, not definitions (#33).**

**Chat 4 additions:** Don't trust Glean snippets/memory for field names — grep first. `cron_run()` yields `_Heartbeat`; `.meta` is an ATTRIBUTE. /cron/heartbeats returns `{heartbeats, health_summary}`. Accessor `Collections.instruments_fundamentals()`. `run_suggestions()` SLOW by default.

**Chat 5 additions:** ASK FOR THE CURRENT SHA BEFORE PROPOSING ANY CODE CHANGE. When a wrapper's return shape/exception behavior changes, grep ALL callers. notify.email() returns {ok,id,error}. GitHub raw-URL caching is real — use SSH+sed as ground truth.

**Chat 5 closure:** Doc rewrites cross-check every cron/registry/file claim against on-disk state. Project_State.md structure is load-bearing — NEVER restructure. Cron-health needs redundant transports. logrotate since 2026-05-24.

**Chat 5.5:** Read the script body at HEAD before documenting it; verify argparse before documenting a cron line. Settings+secrets changes ship in ONE atomic commit. Prefer raw.githubusercontent.com URLs.

**Chat 5.7:** Never change code from memory — construct GitHub URLs from owner/repo/SHA/path. Tree-listing first. Diff file maps line-by-line.

**Chat 5.8:** master_todo.md is canonical. Read it after Project_State.md, confirm the pointer. Ship code + master_todo status in the same commit. Append new items, don't renumber.

**Chat 5.9:** A doc-update commit must NEVER shorten Project_State.md without a stated reason — verify the sentinel + line count. In-code F-numbers span TWO colliding namespaces. An "ops-only" item can hide a code bug. Grep at HEAD.

**Chat 5.10–5.19 + Chat A + Chat 6 + Chat 7:** (compacted; see the per-chat one-liners in Sections 14/15/20 above and prior versions for full prose.)

**Chat 8:** `build_universe` EVOLVES to NIFTY 100 ∪ watchlist (no parallel builder); `get_watchlist_isins` is the single membership source reused by the engine + both crons. F13 reuses `monitored_stocks` status="watchlist" — one doc per ISIN via upsert-on-{isin}; the partial unique index (status:tracking) is untouched and doesn't need broadening; `get_excluded_isins` is unchanged (watchlist is structurally outside its scan; rejected→watchlist auto-un-excludes). The /watchlist CRUD reuses the SAME audit collection via a WIDENED `AuditAction` Literal, write-before-apply; PUT 404s unknown instruments, DELETE 404s non-watchlist docs (feedback rows never nuked); a Money-bearing patch goes through `_convert_decimals_to_decimal128`. The two crons fold in watchlist ISINs (the data-volume multiplier) bounded by the TD33 daily quota — a documented soft guardrail, no hard cap. CORS `allow_methods` must include every frontend method (PUT was missing → browser preflight 503 while curl-from-box passed; test with a simulated preflight OPTIONS). Run scripts as `-m` modules (a by-path invocation raises ModuleNotFoundError: app). A user-directed roadmap change becomes a real numbered row + phase (Phase 10.5 / #52) threaded through every view, without renumbering existing rows.

**Chat B:** the datetime sweep is TWO rows — #30 (`datetime.utcnow()` -> `utcnow()`, 11 sites / 5 files incl. 2 `conversation_service` stragglers the row's stale list missed) and #31 (tree-wide tz-aware `datetime.now(timezone.utc)` Mongo-write sweep -> `utcnow()`, 15 sites, + 19 `# tz-ok:` annotations on in-memory sites). #31 also stood up `scripts/check_datetime_hygiene.py` — a tokenize-based guard (the line-based first draft FAILED on formatter-wrapped statements where the `# tz-ok` comment lands on the closing-bracket line; rewritten to group by logical line). #32 pinned `requires-python = ">=3.12,<3.14"` + `uv lock`. #33 stood up the hermetic, zero-dependency `tests/*` pytest harness — `tests/_fakes.py` (in-memory FakeCollection + tx()/oid() factories) + `tests/conftest.py` (fake_db fixture monkeypatching the Collections.* accessors) + 6 test files, 28 tests across `_fifo_replay`/`validate_replay` (pure), `preview_sell`/`take_auto_snapshot` drift / `submit_feedback` ordering (monkeypatched) and `recompute_holding` FULL DB idempotency (fake_db). Backend + test/doc only; frontend untouched. Re-read every aware-now site + every model/function signature at HEAD before patching/constructing (the master_todo line numbers were a stale map). Verified each on EC2: grep-clean for #30; guard PASSED + both negative controls (planted real utcnow() call AND planted unannotated aware-now) FAILED then cleared for #31; `uv sync` clean + Python 3.12.3 in range for #32; `uv run python -m pytest tests/ -v` => 28 passed + hygiene guard still PASSED for #33. The isolation call (hermetic fakes/monkeypatch over a scratch Mongo) and the recompute-idempotency depth (full DB) were assistant-delegated decisions, grounded in the code (zero-new-dependency ethos + the fake-collection layer already needed for the other DB-coupled targets).

## Section 15: Anti-patterns the assistant has fallen into

(Deduped — Section 14 carries the corresponding positive convention.)
* Full-file rewrites instead of additive patches. EXCEPTION: Project_State.md and master_todo.md are always full-file.
* Inventing parallel patterns. Trusting memory for function names / response shapes / paths — RE-READ AT HEAD. Truncating code with "rest unchanged". Asking "is this OK?" without applying the edit. Micro-commits. Assuming GitHub content is current. Producing files significantly larger than originals. Inventing fields in API responses. Forgetting `enrich_run`. Forgetting `holdings.deleted_at = None`. Cron entries without log paths / heartbeat monitoring. Designing unrequested UI/UX. Shipping code without the commit block. Shipping a test block without `ssh ubuntu@100.112.20.41`. Using artifact_edit on the two docs instead of full-file. Confusing the two F6 mechanisms.
* (Chat 4–Chat 7) See prior versions + the per-chat one-liners; load-bearing items folded into Section 14.
* (Chat 8) Forking a parallel universe builder instead of evolving `build_universe`; writing a second `status=="watchlist"` filter instead of reusing `get_watchlist_isins`; adding watchlist to the `get_excluded_isins` scan (it must stay structurally outside it); broadening the `isin_unique_active` partial index instead of relying on upsert-on-{isin}; adding a new collection for the watchlist instead of reusing `monitored_stocks` status="watchlist"; forking a parallel audit instead of widening the action Literal to `AuditAction`; letting DELETE nuke a feedback row (it must 404 unless status=="watchlist"); passing a Money-bearing patch to update_one without `_convert_decimals_to_decimal128`; enforcing a hard watchlist-size cap instead of the documented TD33 soft guardrail; forgetting `PUT` in CORS `allow_methods` (browser preflight 503 while curl passes); declaring the cron change verified by a by-file-path `python scripts/X.py` (ModuleNotFoundError: app) instead of `-m`; reconstructing the two docs from a terminal-wrapped `git show` paste without un-wrapping + a `git diff` gate; renumbering existing rows/phases when inserting the user-review stage instead of using Phase 10.5 / #52.
* (Chat B) Reconstructing the two docs from a wrapped paste WITHOUT un-wrapping + a `git diff` gate (the standing Section-19 rule — re-confirmed at #33's doc commit). Adding a real/scratch Mongo or a heavyweight in-memory-Mongo dependency to the test harness instead of a minimal `FakeCollection` + monkeypatch. Over-building `FakeCollection` with operators no SUT uses. Constructing `tx(...)`/Holding/feedback-patch dicts in a test from memory instead of grepping the @model at HEAD. A `replace_all`-style datetime swap that silently misses a near-duplicate site (caught only by the hygiene guard — re-run it after any datetime edit). Running the harness by `pytest tests/test_x.py` path framing without the `-m`/pythonpath path (use `uv run python -m pytest`).

## Section 16: "I am losing context" — escalation protocol

When any trigger fires, say verbatim: **`I AM LOSING CONTEXT`**

**Triggers (any one suffices):** Cannot recall a file structure discussed earlier · Conflating Phase 1 vs Phase 2 facts · Forgetting which Commit/Chat shipped which behavior · Producing a file >1.5x original line count without explicit reason · Generic patterns instead of project conventions · Forgetting the Mac/EC2 port difference, SSH-first/commit-block conventions, or the secrets path · Forgetting master_todo.md is canonical (5.8) · The user corrects the same drift twice in one chat · >15 Glean reader / code_search calls without converging · The "Truncation Notice" appears · About to produce a third large code artifact unsure whether prior decisions apply.

**Specific triggers (compacted through Chat 7; see prior versions for the full enumerated list):** shipped a patch with WRONG field names / WRONG API response shape · claimed "open" without re-reading code · find-and-replace whose original_text doesn't exist verbatim · changed a wrapper's shape without grep'ing callers · about to restructure Project_State.md · ship code without master_todo status in the same commit · a test block not SSH-first · confirm the pointer from a cached blob instead of the SHA-pinned file · build a full-file doc from a wrapped `git show` paste without un-wrapping + a `git diff` gate.

**Chat 8 triggers:** fork a parallel universe builder instead of evolving `build_universe` · write a second `status=="watchlist"` filter instead of reusing `get_watchlist_isins` · add watchlist to `get_excluded_isins` · broaden the `isin_unique_active` partial index · add a new collection for the watchlist · fork a parallel audit instead of widening `AuditAction` · let DELETE nuke a feedback row · pass a Money-bearing patch to update_one without `_convert_decimals_to_decimal128` · enforce a hard watchlist-size cap · forget `PUT` in CORS allow_methods · verify a cron change with a by-file-path invocation (ModuleNotFoundError: app) · renumber existing rows/phases when inserting the user-review stage.

**Chat B triggers:** about to add a real/scratch Mongo or a heavyweight in-memory-Mongo dependency to the test harness · constructing a `tx(...)`/Holding/feedback-patch dict in a test from memory without grepping the @model at HEAD · a datetime edit that doesn't re-run `check_datetime_hygiene` · documenting a doc change but reconstructing the full file from a wrapped paste without un-wrapping + a `git diff` gate · running the harness without the `-m`/pythonpath framing.

**What "switching chats" means:** the user copies the Section 0 bootstrap into a fresh chat, which reads Project_State.md + master_todo.md + both repos at HEAD + data_flow.md + READMEs, the user states scope, the assistant summarizes back per the Section 0 acknowledgement contract and WAITS for confirmation before doing anything. Work resumes from the master_todo.md pointer.

## Section 17: "Am I hallucinating?" diagnostic questions

* Backend port Mac local → **8001**. EC2 → **8000**. SSH → **`ssh ubuntu@100.112.20.41`**.
* Secrets on EC2 → **`/etc/portfolio-advisor/secrets.env`**. On Mac → **`<repo>/.env`**.
* How do I run a script on EC2 → as a MODULE from the repo root: **`uv run python -m scripts.<name>`** (or `PYTHONPATH=. … scripts/<name>.py`). A by-file-path run raises `ModuleNotFoundError: No module named 'app'` (Chat 8). Tests → **`uv run python -m pytest`** (pyproject `pythonpath=["."]`; Chat B #33).
* `recompute_holding(isin)` → only authoritative writer to holdings; idempotent; FIFO; serialized per-ISIN via recompute_locks (TD20). Idempotency regression-guarded by tests/test_recompute_holding.py (#33).
* Gating filter on snapshot_open_outcomes → `tracking_status != "expired"`; returns its count under `active_outcomes` (#47/TD22).
* **Universe filter in build_universe → NIFTY 100 ∪ watchlist (deduped by ISIN; watchlist ISINs outside NIFTY 100 resolved from instruments). Held is filtered DOWNSTREAM by filter_universe, so net buy candidates = (NIFTY 100 ∪ watchlist) − held − rejected − acted. The data-refresh universe (fundamentals + news crons) additionally ∪ held (Chat 8 #29).**
* **Is watchlist membership excluded by get_excluded_isins → NO. get_excluded_isins scans only rejected/tracking, so a watchlist row is structurally never excluded; PUT /watchlist flips status to "watchlist" which un-excludes a previously rejected/acted ISIN (Chat 8 #29).**
* **What is the single source of truth for watchlist membership → suggestion_engine.get_watchlist_isins() (monitored_stocks status=="watchlist"), reused by build_universe + refresh_fundamentals + fetch_news_for_universe (Chat 8 #29).**
* **Does the watchlist use a new collection → NO. It reuses monitored_stocks with status="watchlist"; one doc per ISIN via upsert-on-{isin}; the isin_unique_active partial index (status:tracking) is untouched; a watchlist write goes through MonitoredStockWatchlistPatch -> _convert_decimals_to_decimal128 (Chat 8 #29).**
* **What are the watchlist endpoints → GET /watchlist (price-enriched list), GET /watchlist/{isin}, PUT /watchlist/{isin} (idempotent upsert, 404 unknown instrument, write-before-apply audit watchlist_add/update), DELETE /watchlist/{isin} (hard delete only when status=="watchlist", else 404; audit watchlist_remove). ISIN pattern=r"^[A-Z0-9]{12}$" (Chat 8 #29).**
* **Why did add-to-watchlist fail in the browser but pass curl tests → PUT was missing from CORSMiddleware allow_methods, so the browser preflight OPTIONS was rejected; curl-from-box does no CORS preflight. Fixed by adding PUT; allow_methods is now GET/POST/PUT/PATCH/DELETE/OPTIONS (Chat 8 #29).**
* **What is the F13 data-volume multiplier and how is it bounded → both refresh_fundamentals + fetch_news_for_universe fold in watchlist ISINs (weekly fundamentals + earnings + daily news + ~1 Tavily call/run each); bounded by the EXISTING TD33 atomic daily quota ceiling (degrades safely), documented as a soft guardrail — NO hard watchlist-size cap (Chat 8 #29).**
* **How does the pytest harness reach Mongo / external services → it doesn't. The harness is HERMETIC: DB-coupled targets run against an in-memory FakeCollection via the `fake_db` fixture (monkeypatches the Collections.* accessors); fetch_metadata/_get_our_numbers/_send_auto_drift_alert/log_change are monkeypatched. Run `uv run python -m pytest` (Chat B #33).**
* **What does recompute_holding idempotency assert in the test → run twice yields identical aggregates (quantity/invested/realized_pnl) + preserved created_at + EXACTLY one active (deleted_at is None) holding doc; a full exit returns None and leaves zero active docs (Chat B #33).**
* Two F6 mechanisms & why both → get_excluded_isins (run-build) AND _build_user_action (serialization).
* refetchQueries or invalidateQueries → refetchQueries (ChatPanel + /tags + dashboard risk query + watchlist page all follow it).
* Sell endpoint response shape → full Holding (partial) OR {message, realized_total} (full exit) OR {status:"recorded_with_warning", isin, warning} (TD19).
* How does a cron register → cron_run() + CronSpec + crontab line; CronSpec.cron_name == cron_run() name (5.9 TD14).
* Where do F4 cron failure alerts go → push_public("errors",...) + notify.email(...) (dual-transport). Raises only when BOTH fail.
* What does GET /health return → 200 ok/ok or 503 degraded/fail; yfinance NOT probed (Chat A #34).
* What does GET /portfolio/risk-summary / by-tag return → (Chat 7 #28 — see Section 8; both read-only, share _annotate_holdings / list_holdings annotate path).
* What are the chat endpoints / LLM call → POST /chat/suggestions, /chat/holdings/{isin}, GET /chat/history; ONE Sonnet {answer,intent} call (Chat 6 #27).
* What's the SECOND-TO-LAST stage before GO LIVE → **Phase 10.5 USER ACCEPTANCE REVIEW (#52): the user personally walks the whole tool and files findings; GO LIVE (#42) is gated behind it (NEW Chat 8).**

**Chat 4 diagnostics:** CronSpec fields → cron_name, description, schedule_human, expected_weekdays, min_runs_per_day (default 1). Set heartbeat metadata → `ctx.meta = {...}` (ATTRIBUTE). /cron/heartbeats shape → {heartbeats, health_summary}. Fundamentals accessor → instruments_fundamentals. F2b digest ntfy topic → NTFY_PUBLIC_TOPIC_DIGESTS. F14 earnings-proximity threshold → 5 days. compute_system_performance(direction='sell') → SIGN-FLIPS.

**Chat 5+ diagnostics:** F2 frontend shipped → Yes (frontend HEAD f59958 → 6093f63 Chat 6 → e14d6a75 Chat 7 → 58bf6369 Chat 8, unchanged Chat B). target_price consumed → Yes; stop_loss consumed → Yes (#41 intraday breach alert, Chat C — closes TD6). On-disk filename → Project_State.md. App DB name → portfolio. TD8 → self-hosted ntfy decommissioned. Commit 8 → cron_health_check dual-transport.

## Section 18: Tech debt registry

**Closed audit rows (Chat 5 + earlier — all SHIPPED, kept for posterity):** A1–A19 (see prior versions), TD2, TD4, TD5, TD8.

**SHIPPED TDs (one line each — full verification prose in git history):**

| TD | master_todo | Description | Shipped |
|---|---|---|---|
| TD9 | — | Orphan NTFY_URL/USER/PASS removed from settings.py + secrets.env | 5.5 |
| TD10 | #2 | Redundant `find -size +10M` crontab line verified absent; logrotate confirmed | 5.9 |
| TD11 | — | explainability._build_signal_meta reads sig["raw_value"] | 5.5 |
| TD12 | — | seed_nifty100.py correctly named — doc-only fix | 5.5 |
| TD13 | — | Frontend per-page reference doc | 5.6 |
| TD14 | #1 | Sunday crontab flags removed + CRON_REGISTRY rename (c097b473) | 5.9 |
| TD15 | #3 | F-number fix registry authored; recovered truncated Sections | 5.9 |
| TD16 | #4 | PATCH/DELETE /transactions/{id} audit-then-apply (17f9f94) | 5.10 |
| TD17 | #5 | validate_replay on /sell + add_manual_transactions.py (5cf3087) | 5.10 |
| TD18 | #6 | Duplicate list_transactions handler deleted | 5.10 |
| TD19 | #7 | add_buy/sell wrap recompute_holding → recorded_with_warning (fb23307) | 5.10 |
| TD20 | #8 | recompute_holding serialized per-ISIN via recompute_locks (b34721e) | 5.10 |
| TD23 | #9 | Holiday guard in _intraday_row_from_df (a2806cd) | 5.11 |
| TD24 | #10 | price_stale docstring aligned (a2806cd) | 5.11 |
| TD25 | #11 | bulk_get_previous_closes per-ISIN find_one (a2806cd) | 5.11 |
| TD26 | #12 | prices_intraday.captured_at 90-day TTL | 5.12 |
| TD27 | #13 | purge_news_bodies.py daily cron (49bf33f) | 5.12 |
| TD28 | #14 | invalidateQueries → refetchQueries (f59958) | 5.13 |
| TD29 | #15 | Dead `from pydoc import doc` removed | 5.13 |
| TD30 | #16 | MONGODB_URI doc-drift confirmation | 5.13 |
| TD31 | #17 | ISIN pattern on the two /suggestions/{isin} Path params | 5.13 |
| TD32 | #18 | Dropped `$options:i` on transactions/search regex | 5.13 |
| TD33 | #19 | Atomic Tavily quota claim (4ac2c95) | 5.14 |
| TD34 | #20 | notify.email() transient-5xx/429 retry (7d77b9c) | 5.15 |
| TD35 | #21 | Explicit persisted-run-id flow (f4168b3) | 5.16 |
| TD37 | #22 | Reject NaN in `_to_decimal` (1d627d7) | 5.17 |
| TD38 | #23 | Fallback heartbeat log (0515fef) | 5.18 |
| TD39 | #24 | cron_health_check.main self-failure alert (7fcda9e) | 5.19 |
| — | #34 | GET /health 503 + degraded on Mongo ping failure (bd52c6b) | A |
| — | #35 | refresh_prices_intraday GUARDED ntfy on insert failure (bd52c6b) | A |
| — | #25 | take_auto_snapshot ntfy on invested drift, rising-edge deduped (1340396) | A |
| — | #26 | Direction-aware feedback relabel (6032b64) — does NOT close TD1/#43 | A |
| TD22 | #47 | track_suggestion_outcomes daily KeyError 'open_outcomes'→'active_outcomes' (4b638e6) | A |
| TD36 | #48 | Tavily doc cleanup monthly→daily + non-existent env var (fae6edf) — DOC-ONLY | A |
| TD40 | #49 | weekly_suggestions_sell idle spec expected_weekdays=set() (6032b64) | A |
| — | #27 | F1+F3 ad-hoc chat (Chat 6, no TD number) — backend `5e787c9`, frontend `6093f63` | 6 |
| — | #28 | F12+F15 risk-summary + by-tag (Chat 7, no TD number) — backend `97041621`/`803e6610`; frontend `e14d6a75` | 7 |
| — | #29 | F13 watchlist: MonitoredStockWatchlistPatch + build_universe = NIFTY 100 ∪ watchlist + get_watchlist_isins / /watchlist CRUD reusing monitored_stocks status="watchlist" + widened AuditAction / refresh_fundamentals + fetch_news_for_universe fold in watchlist ISINs (data-volume multiplier) / frontend /watchlist page + nav / CORS allow_methods += PUT (Chat 8, no TD number) — backend Unit 1 `34ff906d`, Unit 2 `a250d001`, Unit 3 `9857570b`, CORS `67704025`; frontend `58bf6369` | 8 |
| — | #30 | P2-1: 11 `datetime.utcnow()`->`utcnow()` sites across 5 files (portfolio/scoring/dossier/fundamentals + 2 `conversation_service` stragglers) (Chat B, no TD number) — backend `025b8a0` | B |
| — | #31 | P2-8: tree-wide tz-aware `datetime.now(timezone.utc)` Mongo-write sweep -> `utcnow()` (15 sites) + 19 `# tz-ok:` annotations + NEW `scripts/check_datetime_hygiene.py` tokenize-based lint guard (machine-enforces the naive-UTC invariant) (Chat B, no TD number) — backend `025b8a0` | B |
| — | #32 | P3-2: pin `requires-python = ">=3.12,<3.14"` + `uv lock` relock (Chat B, no TD number) — backend `025b8a0` | B |
| — | #33 | Review note: hermetic zero-dependency pytest harness — `tests/_fakes.py` (in-memory FakeCollection + tx()/oid()) + `tests/conftest.py` (fake_db fixture monkeypatching Collections.*) + 6 test files, 28 tests across `_fifo_replay`/`validate_replay`/`preview_sell`/`recompute_holding` idempotency/`submit_feedback` write-before-apply ordering/`take_auto_snapshot` drift math; no new deps; `uv run python -m pytest` => 28 passed (Chat B, no TD number) — backend `04fd970` | B |
| — | #36 | Ops gap: `POST /admin/recompute/{isin}` (Tailscale-only) — NEW `app/routers/admin.py` delegating to `holdings_service.recompute_holding` (TD20 per-ISIN advisory lock; no parallel path), registered in `app/main.py`; ISIN pattern-validated; `{status: recomputed/no_active_holding, isin, holding}`, 409 on lock contention; the HTTP replacement for the TD19/#7 SSH-shell recovery fallback (Chat B, no TD number) — backend `1ef0ead` | B |
| — | #37 | Ops gap: Atlas backup → fresh-DB restore rehearsal for `monitored_stocks` + `suggestion_outcomes` + `digest_deliveries` — rehearsed on EC2 against prod Atlas (per-collection `mongodump --db=portfolio --collection=<name>`; this `mongodump` 100.17.0 rejects `--nsInclude`) → `mongorestore --nsFrom 'portfolio.*' --nsTo 'portfolio_restore_test.*' --drop` into a fresh scratch DB; counts matched prod (2 / 155 / 10), scratch DB dropped, prod `portfolio` untouched; exact runbook documented in Section 4 (Chat B, no TD number) — DOC + OPS only, code HEAD unchanged `1ef0ead` | B |
| — | #38 | Ops gap: switch backend logging to JSON-structured — `app/main.py` `logging.basicConfig` replaced by a stdlib `JsonLogFormatter` (`logging.Formatter` subclass; no new dependency, consistent with the #32 `>=3.12,<3.14` pin) + `_configure_logging()` installing one JSON `StreamHandler` on the root logger AND `uvicorn`/`uvicorn.error`/`uvicorn.access` (`handlers.clear()` idempotent; `propagate=False`, no double-logging); each record -> one single-line JSON object to stdout/journald (timestamp UTC ISO-8601 ms+Z from `record.created` via `datetime.fromtimestamp` — clean against `check_datetime_hygiene`; level/logger/message/module/func/line; `traceback` on exc_info; `stack` on stack_info; caller `extra={...}` merged); verified on EC2 (hygiene PASSED, 28 pytest, JSON app + `uvicorn.access` logs valid, 3 `/health` -> 3 access lines) (Chat B, no TD number) — LAST Chat B row, Phase 9 COMPLETE; backend `8127c6f` | B |

**OPEN / DEFERRED TDs (full):**

| TD | master_todo | Item | Status |
|---|---|---|---|
| TD1 | #43 | Make monitored_stocks direction-aware (dual rows per ISIN). Reconcile with #26 AND with the F13 watchlist status (both ride the single-doc-per-ISIN model). | DEFERRED — post-launch |
| TD3 | #44 | Split dossier_service.valuation_verdict → {verdict, rationale}. | DEFERRED — future UI |
| TD6 | #41 | Wire holdings.stop_loss (reader + writer + alerts; frontend edit field). | SHIPPED 2026-07-03 (Chat C) — intraday breach alert on the existing write path + alerts_log first writer + read-only stop-loss strip; reader/writer already sufficient via PATCH whitelist + get_holding |
| TD7 | #45 | Refactor CandidateScore so sell-side groups are first-class fields. | DEFERRED — post-launch |
| TD21 | #46 | Registry-generated crontab migration. Its own dedicated chat. | OPEN — dedicated chat |
| — | #50 | News entity mis-tagging in `news_articles.entities_isins`. Blast-radius widened by #29 (every watchlist name now pulls daily news). Investigation-first. | OPEN — Chat 6 filed |
| — | #51 | `dividend_yield` ×100 formatting — pre-existing app-wide yfinance unit inconsistency; fix at ingest and/or both _fmt_pct formatters consistently. | OPEN — Chat 6 filed |
| — | #52 | USER ACCEPTANCE REVIEW (NEW Chat 8, user request) — complete end-to-end user review/UAT; file findings as new rows; second-to-last stage; gates GO LIVE (#42). | OPEN — Phase 10.5 |

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
| F10 | Feature | db/client.py:121; db/indexes.py:236; routers/suggestions.py:8,220,229,243,268; services/monitored_stocks_audit_service.py:1 | monitored_stocks write-before-apply audit + read endpoints (Chat 8 #29 extended: watchlist CRUD reuses this audit via the widened AuditAction Literal; Chat B #33: ordering regression-guarded by tests/test_submit_feedback.py) |
| F12 | Feature | (roadmap) | Portfolio risk-summary / concentration (Chat 7/#28 — SHIPPED; routers/portfolio.py + services/portfolio_service.py) |
| F12 | Fix-5.5+ | routers/holdings.py:325 | Fully-exited SELL response includes realized_total |
| F13 | Feature | models/monitored_stock.py:5,9,14,83 | Watchlist (Chat 8/#29 — SHIPPED; the in-code # F13 comments remain as scaffolding markers on monitored_stock.py; the implementation lives in routers/watchlist.py + suggestion_engine.build_universe/get_watchlist_isins + the two cron scripts + frontend app/watchlist/page.tsx, which carry their own #29 references) |
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

Notes: F11 (capital-gains pack, Chat 9/#39) SHIPPED 2026-07-01 — lives in `app/routers/tax.py` + `app/services/tax_service.py` + frontend `app/tax/page.tsx`; `holdings_service._fifo_replay` was extended to emit per-disposal `_realized_lots` (the read-only source tax_service reads). Its known bonus/demerger holding-period limitation is filed as NEW-ITEMS #53. F15 (tag views, Chat 7/#28) lives in `routers/portfolio.py` + the frontend `/tags` page. F13 (watchlist) is now SHIPPED via #29 — the in-code `# F13` comments on `models/monitored_stock.py` remain scaffolding markers; the implementation carries its own #29 references. Feature-F rows for colliding numbers are for disambiguation only.

**Fixed in earlier chats (posterity):** Digest sell-side Q/V/M/N bug (cea8eee). track_suggestion_outcomes daily failure (TD22, FIXED Chat A). holdings.target_price half-fixed (stop_loss is TD6). MonitoredStock schema↔writer drift (A1). Dead news_article.py (A8). All Chat 5 A2–A19 + TD8.

## Section 19: How to update this document

Updated at the end of every chat as the LAST commit — ALWAYS a complete full-file canvas artifact, never a patch.

**Update each chat:** Sec 13 (move shipped; advance chat split plan — preserve rows) · Sec 9 (cron registry if changed) · Sec 14/15/16/17 (new conventions / anti-patterns / triggers / diagnostics) · Sec 18 (add/remove/reclassify TD) · Sec 12/11 (new invariants) · Sec 7 (collection schema) · Sec 8 (endpoint changes) · Sec 5/6 (file additions/deletions — diff against the Section-0 tree listing line-by-line) · Sec 4 (pin new last-verified SHAs).

**Commit message:** `docs: update PROJECT_STATE.md after <chat scope>` + a bullet list of sections changed.

If the chat ended due to context loss, the LAST thing the assistant does is propose the Project_State + master_todo update; the user applies it manually.

**Standing doc rules:**
* On starting a new chat, after reading Project_State, audit every "open" item against on-disk code at HEAD before estimating work.
* Project_State.md structure is immutable: Section 0 at top, numbered Sections 1-22 in order. New sub-items go INSIDE existing sections, never as new top-level sections.
* When reading this file for a full-file refresh, prefer the SHA-pinned `raw.githubusercontent.com` URL over the blob URL (blob frequently `LINK_NEEDS_AUTH`). If both fail, have the user `ssh ubuntu@100.112.20.41 && cat ~/ai-stock-advisor-backend/docs/Project_State.md` and paste the bytes — Glean's raw reader sentence-wraps, so never reconstruct a full-file replacement from a wrapped read; anchor on a user-pasted byte-exact source (`git show <sha>:docs/Project_State.md`). NOTE (5.17): a `git show` paste through a narrow terminal can ITSELF hard-wrap mid-word — when reconstructing from such a paste, un-wrap carefully and gate the result with a `git diff` review so no unchanged line drifts. (Re-confirmed Chat A, Chat 6, Chat 7, Chat 8 AND Chat B: the user's `git show` paste had mid-word wraps like "shownis"/"atomicTavily"/"weekly_sugg estions"/"Itemnumbers"/"directi on"/"vsthe"/"thelast"/"HE AD"/"Markdo wnLite"/"con versation_service"/"po sition"/"fil ed"/"areexcluded"/"itemswere"/"bul k_get_latest_prices"/"descby"/"non-NIFTY100"/"extra=\"f orbid\""/"existing item s" — un-wrapped during reconstruction; gate with `git diff`.)
* The tree-listing command (Section 0) MUST be the first thing run in every new chat, before scope. Every file-read URL uses a SHA the user supplied this chat and a path verified in the tree listing.
* The end-of-chat full-file artifact MUST end with the sentinel `End of PROJECT_STATE.md.` and have a line count >= the prior commit's (or explicitly state why it shrank) BEFORE the user commits. (5.8's doc commit silently truncated 655 lines.)
* Update master_todo.md status AND the matching Section 18 TD row AND Section 13 in the SAME end-of-chat doc commit as the code; pin each commit SHA next to its TD row.
* A user-directed roadmap change is a real numbered row + phase threaded through master_todo's pointer / ordering / bundles / summary AND this file's Section 13 — without renumbering existing rows or phases (Chat 8 added Phase 10.5 / #52).

## Section 20: Trade-off rationale (decisions that might look weird)

* yfinance over Tijori/Screener Pro: free, swappable. Confidence numeric 0-100 deterministic. Suggestions Sunday 07:00 IST. Top-K = 10. 90-day rejected cooldown + 30-day acted soft-exclude + zero passed cooldown — not env-configurable. Persistent backend feedback state (Chat 3). Two-mechanism F6 exclusion. valuation_verdict one string. Dividend tracking dropped (F8). Realized P&L hidden UI, kept backend. F7 last (Chat 10). Watchlist (F13) extends the engine universe. F4 ntfy errors public over private; CRON_REGISTRY in code; cron_health_check.py is itself a registered cron.
* (Chat 4) F2b digests on public ntfy.sh; F14 as gating signal; shared scoring pipeline; CandidateScore fixed buy-side fields; --direction=both as production cron; sell-side sign-flip at read time.
* (Chat 5) F2b display-layer direction branching; audit-then-fix ordering; A2 wrapper return-shape change; TD8 in two commits; commit 8 raises only when BOTH transports fail; logrotate over hand-rolled truncation.
* (5.5–5.19) See per-chat rationale lines in prior versions.
* (Chat A) Bundle worked in meaningful units. #34: 503 status code + no yfinance on the hot path. #25: ntfy-ONLY auto-drift + rising-edge dedupe. #26: defaulted `direction` field + `$or`/`$exists:false` buy guard. #47: reproduced live before fixing. #49: option 1 (`expected_weekdays=set()`). #48: fixed the wider doc drift.
* (Chat 6) #27 built in 4 units + 1 fix. Path-2 full enrichment; generalized per-stock endpoint (kept the documented path); single Sonnet `{answer,intent}` call; `scope` field; reimplemented the position block; embedded chat on existing surfaces; self-contained `MarkdownLite`; unknown ISIN -> 404; route-shadow fixed by reordering. Filed #50/#51.
* (Chat 7) #28 built in 2 backend + 2 frontend units, design approved before code. Shared `_annotate_holdings` extraction; two-tier alert thresholds as module constants; concentration_by_holding returns EVERY priced holding; `stale_price` note; stop_loss/target gaps EXCLUDED (that's #41); by-tag reuses the list_holdings annotate path; exact case-sensitive tag match; F12 dashboard card with its own useQuery; F15 on a dedicated /tags page; NEW api.ts types; no new npm/shadcn dep.
* (Chat 8) #29 built in 4 units + 1 CORS fix, SHA re-requested per unit, design approved before code. **Set-math resolved as `build_universe` = NIFTY 100 ∪ watchlist with held filtered DOWNSTREAM** (over adding held into build_universe) — keeps the existing filter_universe contract intact, so a held+watchlist ISIN correctly stays out of buy candidates while still getting data refresh. **Reused `monitored_stocks` status="watchlist"** (over a new collection) — the model already declared the status + F13 fields; one-doc-per-ISIN via upsert-on-{isin} means the partial unique index (status:tracking) needs no broadening. **`get_excluded_isins` LEFT UNCHANGED** — watchlist is structurally outside its rejected/tracking scan, so PUT /watchlist auto-un-excludes a rejected/acted ISIN for free (over special-casing un-exclusion). **New `routers/watchlist.py`** (over forcing it into the /suggestions router) since the endpoints are /watchlist/*; **widened the audit action Literal to `AuditAction`** (over a parallel audit) to reuse the same write-before-apply audit collection. **PUT 404s an unknown instrument** (over storing inert watchlist rows) and **DELETE 404s a non-watchlist doc** (so a feedback row is never nuked). **Both crons fold in watchlist ISINs reusing `get_watchlist_isins`** (over a parallel membership filter) — the data-volume multiplier bounded by the EXISTING TD33 daily ceiling, documented as a **soft guardrail** (over a hard watchlist-size cap, consistent with the calls-only TD33 ceiling). **Frontend `/watchlist` page reuses the /tags shell + ui/table** (over HoldingsTable, which is Holding[]-typed) and the buy-sheet mutation convention; **no new npm/shadcn dep.** **CORS fix: added PUT to allow_methods** (over switching to `["*"]`) — minimal, evolves the explicit list. **Phase 10.5 / #52 USER ACCEPTANCE REVIEW** added at the user's explicit request as a real second-to-last stage gating GO LIVE, using Phase "10.5" to avoid renumbering the GO-LIVE=Phase 11 / Deferred=Phase 12 references. No new TD filed.
* (Chat B) #30/#31/#32 SHA-re-requested + re-read every aware-now site at HEAD before patching (the master_todo line numbers were a stale map). **#31 chose a tokenize-based hygiene guard** (over a line-based grep) because the formatter parks a long statement's `# tz-ok` comment on the closing-bracket line — line-based FAILED 5 sites; the guard is also comment-aware, self-skipping, and fragment-builds its needles so it won't trip the existing greps. **A `replace_all` swap silently missed two near-duplicate sites** (reconciliation take_manual_snapshot + price_service bulk_get_latest_intraday) — the guard caught them, hence the standing "re-run the guard after any datetime edit" rule. **#32 pinned `<3.14`** (lower bound unchanged) + `uv lock` with no dep churn. **#33 chose a hermetic, zero-dependency harness** — an in-memory `FakeCollection` + a `fake_db` fixture that monkeypatches the `Collections.*` accessors, over a real/scratch Mongo or a heavyweight in-memory-Mongo dep — consistent with the zero-new-dependency ethos right after #32 relocked the environment, and it makes `uv run python -m pytest` run anywhere with no Atlas allowlist or `portfolio` DB pollution. **recompute_holding got FULL DB idempotency** (run twice -> stable aggregates + preserved created_at + exactly one active doc), not a shallow single-call assertion, because the fake-collection layer was already needed for the other DB-coupled targets so the marginal cost was low. Both #33 design calls (isolation strategy + idempotency depth) were assistant-delegated by the user and grounded in the re-read code. The two doc files were reconstructed from the user's byte-exact `git show` paste with mid-word wraps un-wrapped and a `git diff` gate, per Section 19. Backend + test/doc only; no new TD/follow-ups filed.
* (Chat 9) #39 F11 capital-gains pack built in 2 units (backend + frontend), design approved before code, SHAs re-requested before writing. **Reused the existing FIFO by extending `_fifo_replay` to emit per-disposal `_realized_lots`** (over a parallel FIFO/realized-P&L path) — keeps ONE FIFO source of truth; `_recompute_holding_impl` pops the key so the extra=forbid holdings doc is untouched. **Read-only on Phase 1** — tax_service replays `transactions`, never writes. **§49(2C) honored via the ledger** (the apportioned cost is already in the `manual_demerger` BUY rows) — deliberately did NOT re-apply `cost_basis_adjustments` (that collection is a read-only audit surface; re-applying would double-count). **Strict >12-calendar-month LTCG boundary** (over a >365-day approximation) for legal accuracy; holding_period_days still reported. **`fy` optional -> current IST FY** (over required) for ergonomics; 422 on malformed OR non-consecutive fy. **Frontend `/tax` reuses the /cost-basis printable shell + existing shadcn primitives** (Card/Table/Select/Badge/Skeleton) — no new npm/shadcn dep. Design defaults were assistant-delegated (user: "do whatever you feel is best"). **Known limitation filed as #53** (bonus/demerger holding-period reflects the ledger, not the strict IT-Act treatment) rather than expanding #39 into Phase-1 FIFO changes.

## Section 21: What is intentionally NOT included

So future chats don't accidentally add these:
* Auto-trading (never). Multi-user. Mutual funds, FDs, foreign equities, derivatives, crypto. Native mobile app. Tax filing. Dividend tracking (F8 dropped). Accounting / financial planning / goal-based planning. Real-time tick data. Public-facing dashboard. Backtesting framework. Notification customization UI. Account aggregation. Social features. Technical indicator alerts. Options tracking. Index fund comparison page. Separate /news page. Heatmaps. Portfolio rebalancing recommender. Social sentiment tracking. Manual-clear endpoint for feedback (use mongosh). /calendar page. Loss-cutting sell pipeline (F2 is profit-booking only).
* **In-process application scheduler (APScheduler/lifespan jobs).** Schedule stays in crontab; TD21 will version-control it via a registry-rendered ops/crontab.
* **Mongo multi-document (M10) transactions on the synchronous write path.** Rejected for TD19; Tavily quota atomicity comes from a conditional find_one_and_update + unique index.
* **DST-aware timezone handling for IST.** India has no DST; IST is fixed UTC+5:30.
* **Dropping/replacing a same-field index to add a TTL** when an ASC-vs-DESC split lets both coexist (5.12).
* **Case-insensitive symbol search / tag match.** Symbols + tags uppercased/exact; NO $options:i (5.13 TD32; Chat 6 /instruments/search; Chat 7 by-tag).
* **A credits_today ceiling on Tavily.** Only calls_today is capped (5.14).
* **A lock or M10 transaction around the Tavily quota increment** (5.14 TD33).
* **A raised-exception path or env-configurable knobs for notify.email()** (5.15 TD34).
* **A `find_one(sort run_date desc)` re-derivation to recover "the run just created"** (5.16 TD35).
* **A signature change to send_combined_digest** (5.16).
* **Broadening the #22 NaN guard to the Decimal/Decimal128 read paths** (5.17 TD37).
* **Widening the #24 try/except beyond the per-cron Mongo-read loop** (5.19 TD39).
* **(Chat A) yfinance on the `/health` hot path** (#34). **Email on the daily auto-drift alert; a parallel reconciliation alerter** (#25). **Closing TD1/#43 via #26.** **Restoring `weekly_suggestions_sell` `expected_weekdays={6}`** without a real crontab line (#49).
* **(Chat 6) A second Haiku intent-classify call** (#27). **A standalone `/chat` route** (embeds on existing surfaces). **`react-markdown`** (MarkdownLite). **Calling `_build_position_context_block` from the chat path.** **A yfinance rescue for an unknown ISIN.** **Diverging the chat `_fmt_pct` from the dossier.** **Using `follow_up_conversation_ids` for threading now.**
* **(Chat 7) A parallel risk aggregation** (evolve `compute_summary` via `_annotate_holdings`). **Risk thresholds in env/settings.** **stop_loss/target-gap alerts in risk-summary** (that's #41). **A parallel by-tag annotate path or a parallel `_to_dec`.** **A new npm/shadcn dep for F12/F15.**
* **(Chat 8) A new collection for the watchlist** — reuse `monitored_stocks` status="watchlist" (#29).
* **(Chat 8) A parallel universe builder** — `build_universe` is EVOLVED to NIFTY 100 ∪ watchlist (#29).
* **(Chat 8) Adding watchlist to the `get_excluded_isins` scan, or broadening the `isin_unique_active` partial index** — watchlist is structurally outside the excluded scan; single-doc-per-ISIN is upheld by upsert-on-{isin} (#29).
* **(Chat 8) A second `status=="watchlist"` membership filter** — `get_watchlist_isins()` is the single source reused by the engine + both crons (#29).
* **(Chat 8) A parallel audit for watchlist** — widen the action Literal to `AuditAction` and reuse the same `monitored_stocks_audit` + `log_change` (#29).
* **(Chat 8) Letting DELETE /watchlist nuke a feedback row** — DELETE 404s unless status=="watchlist" (#29).
* **(Chat 8) A hard watchlist-size cap or a new env knob for the Tavily blast-radius** — it's a documented soft guardrail bounded by the existing TD33 daily ceiling (#29).
* **(Chat 8) Switching CORS to `allow_methods=["*"]`** — keep the explicit list; just add the method the frontend needs (PUT) (#29).
* **(Chat 8) GET /watchlist enrichment beyond latest price** — price-only via bulk_get_latest_prices; fundamentals/news are NOT folded into the list (#29).
* **(Chat B) A real/scratch Mongo or a heavyweight in-memory-Mongo dependency for the test harness** — use the minimal in-house `FakeCollection` + the `fake_db` monkeypatch fixture (#33).
* **(Chat B) Over-building `FakeCollection`** with operators no SUT uses — implement only what the targets exercise; extend minimally if a future test needs more (#33).
* **(Chat B) A line-based datetime-hygiene guard** — it must be tokenize-based to survive formatter-wrapped statements (#31).
* **(Chat B) Relaxing the `requires-python` lower bound** when adding the `<3.14` ceiling — lower bound stays `>=3.12` (#32).

## Section 22: Glossary

ISIN: 12-char NSE/BSE primary key. NSE / NIFTY 100 / FIFO / LTCG / STCG / Section 49(2C) / ICICI Direct / ICICI ZIP / TMPV / TMCV / EW NIFTY: see prior version. Composite score: 0-100, Q/V/M/N (buy) or booking_opportunity/valuation_stretch/risk/tax_concentration (sell). Confidence score: 0-100, deterministic. Dossier: Sonnet per-candidate note. Outcome: suggestion_outcomes doc. Bucket: outcome user-action label. **Watchlist (F13/#29): a monitored_stocks doc with status="watchlist"; joins the buy-side universe (build_universe = NIFTY 100 ∪ watchlist) + the fundamentals/news data-refresh universe. MonitoredStockWatchlistPatch (#29): the typed $set patch for the /watchlist CRUD path (extra=forbid, status pinned watchlist, exclude_none on dump, Money->Decimal128). get_watchlist_isins (#29): suggestion_engine single source of truth for watchlist membership, reused by build_universe + both cron scripts. AuditAction (#29): the widened monitored_stocks_audit action Literal (feedback actions + watchlist_add/update/remove). Watchlist endpoints (#29): GET /watchlist, GET/PUT/DELETE /watchlist/{isin}. Watchlist data-volume multiplier (#29): every watchlist name pulls weekly fundamentals + earnings + daily news + ~1 Tavily call/run, bounded by the TD33 daily ceiling (soft guardrail). CORS allow_methods rule (#29): must list every frontend method or the browser preflight 503s while curl-from-box passes.** user_action: per-candidate serialization-time stamp (F6). direction (F2): "buy"|"sell". monitored_stocks_audit: F10. earnings_calendar (F14). Combined digest (F2). isSellSide (F2). MonitoredStockFeedbackPatch (A1). SuggestionFeedback (#26). notify.email() return contract (A2; 5.15 TD34 retry). push_public: RAISES — guard it. /health (#34). _send_auto_drift_alert (#25). Explicit inserted_id flow (TD35). _to_decimal NaN guard (TD37). Fallback heartbeat log (TD38). Health-check self-failure alert (TD39). active_outcomes (#47/TD22). weekly_suggestions_sell (#49/TD40). Tavily quota (#48/TD36): DAILY. Conversation / ConversationScope / ensure_stock_context / lookup_by_isin / MarkdownLite / Chat endpoints / Route-shadow rule (#27). _annotate_holdings / compute_risk_summary / Risk thresholds / Portfolio endpoints risk-summary + by-tag / RiskSummaryCard / /tags page (#28). **check_datetime_hygiene.py (#31 Chat B): tokenize-based lint guard banning stdlib utcnow() + requiring `# tz-ok:` on every aware-now; machine-enforces the naive-UTC storage invariant. FakeCollection / fake_db / tx() / oid() (#33 Chat B): the hermetic in-memory Mongo doubles + fixture + factories powering the pytest harness; recompute_holding idempotency = run twice -> stable aggregates + preserved created_at + exactly one active doc. Run tests via `uv run python -m pytest`. USER ACCEPTANCE REVIEW (#52 / Phase 10.5): the second-to-last stage (NEW Chat 8) — the user personally walks the whole tool and files findings; GO LIVE (#42) is gated behind it. Script invocation rule (Chat 8): run as `uv run python -m scripts.X` (a by-file-path run raises ModuleNotFoundError: app). Capital-gains pack (F11/#39 Chat 9): GET /tax/capital-gains?fy=YYYY-YY -> STCG/LTCG per-lot breakdown + summary for the Indian FY (1 Apr->31 Mar IST); tax_service.compute_capital_gains replays transactions through holdings_service._fifo_replay (single FIFO source of truth, extended to emit per-disposal _realized_lots), read-only on Phase 1; LTCG = listed equity held strictly >12 calendar months; §49(2C) honored via the manual_demerger ledger rows, cost_basis_adjustments NOT re-applied. _realized_lots (#39): the per-disposal list _fifo_replay emits (buy/sell trade_date + fee-normalized per-share cost/proceeds), popped in _recompute_holding_impl. /tax page (#39): FY selector + STCG/LTCG/Total cards + disposals table, printable.**

End of PROJECT_STATE.md.