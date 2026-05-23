
# ai-stock-advisor-backend

Personal AI Stock Advisor — backend. FastAPI + Pydantic v2 + MongoDB Atlas. Single-user portfolio + research tool for NSE equities. **Strictly advisory; the system never trades.**

> Last updated: 2026-05-23 (post-Chat-5 audit + cleanup).
> Companion docs: [`docs/data_flow.md`](docs/data_flow.md) for the per-collection / per-pipeline mental model; `docs/Project_State.md` for the full architectural spec, audit log, and open questions.

---

## 1. What this is

A two-phase system:

- **Phase 1** answers "what do I own and what's it worth right now": ICICI CSV imports, manual transaction entry, FIFO replay, EOD + 15-min intraday prices, reconciliation against ICICI, IT-Act-correct cost basis (Section 49(2C) demerger handling, etc.).
- **Phase 2** answers "what should I look at this week": weekly buy + sell candidate ranking using shared scoring across fundamentals (yfinance), price momentum, and classified news (Tavily + Claude Haiku), with hard gates (market cap, negative news, earnings proximity), stateful per-user feedback (`tracking`/`passed`/`rejected`/`watchlist`), and a single weekly digest (email + push).

The two phases live in the same FastAPI app and the same Mongo database. Phase 2 is read-only on Phase 1 data.

All access is via Tailscale (no public ingress). The single user is the author. Compute is one EC2 t3.micro in `ap-south-1` (Tailscale IP `100.112.20.41`) hosting both backend (`:8000`) and frontend (`:3000`).

---

## 2. Architecture at a glance

| Layer | Tech |
|---|---|
| API | FastAPI + Uvicorn (sync mode), Pydantic v2, Python 3.12 |
| Persistence | MongoDB Atlas M10 (`personal.3eano.mongodb.net`), one database `portfolio_advisor` |
| Prices | `yfinance` (NSE tickers via `<SYMBOL>.NS`) |
| LLM | Anthropic — Claude Sonnet 4.5 (primary, dossier authoring) + Claude Haiku 4.5 (news classifier) |
| News search | Tavily (monthly quota tracked in `tavily_quota` collection) |
| Email | Resend (`@portfolioadvisor.<domain>`) |
| Push | Public ntfy.sh on random unguessable topics — `price`, `news`, `errors`, `digests` |
| Networking | Tailscale (mesh; no public ports). Funnel was used for self-hosted ntfy until 2026-05-18; decommissioned in TD8 |
| Process supervision | systemd (`portfolio-advisor.service`) on EC2; `uv run` on Mac for dev |
| Package manager | `uv` (replaces pip/venv/poetry) — `pyproject.toml` + `uv.lock` are source of truth |
| Dependency pinning | `uv.lock` is committed; `uv sync` reproduces the environment exactly |

Phase 2's outbound transports (`yfinance`, Anthropic, Tavily, Resend, public ntfy.sh) are the only external service calls the system makes. Everything else stays inside Tailscale + Mongo Atlas.

---

## 3. First-time setup (Mac)

Prerequisites: macOS, Python 3.12+, Tailscale signed in (to reach the EC2 box later for prod ops), Atlas connection allowlisted to your dev IP.

```bash
# 1. Clone
git clone git@github.com:doshisahil95/ai-stock-advisor-backend.git
cd ai-stock-advisor-backend

# 2. Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh
exec $SHELL   # pick up the new PATH

# 3. Sync the locked environment
uv sync

# 4. Create local secrets file (see Section 5 for full reference)
cp .env.example .env       # if a template exists; otherwise create from Section 5
# edit .env and fill in real values

# 5. Initialize the database (idempotent — creates collections + indexes)
PYTHONPATH=. uv run python scripts/init_db.py

# 6. Smoke test (hits Anthropic, MongoDB, public ntfy, Resend — costs a few cents)
PYTHONPATH=. uv run python scripts/smoke_test.py

# 7. Boot the API
PYTHONPATH=. uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

Expected smoke test output: 5 ✓ checks (Config / Anthropic / MongoDB / ntfy public / Email) and a 🎉 banner. If MongoDB ping fails, your IP isn't allowlisted in Atlas; if Anthropic fails, the key is wrong; if ntfy returns an error, the topic name in `.env` is malformed.

Note: the **Mac runs on port 8001**; the EC2 box runs on port 8000. The frontend's `NEXT_PUBLIC_API_BASE_URL` flips between them depending on `NODE_ENV`.

---

## 4. Running locally

### Dev server with hot reload

```bash
PYTHONPATH=. uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

`--reload` watches `app/` and reloads on file change. Use this for everything except batch scripts.

### Running a one-shot script

Every script in `scripts/` runs the same way:

```bash
PYTHONPATH=. uv run python scripts/<script>.py [--flags]
```

Most scripts support `--dry-run`. **Always dry-run first** for anything that mutates Mongo.

### Talking to the API from another terminal

```bash
curl -sS http://localhost:8001/health
curl -sS http://localhost:8001/suggestions/latest?direction=buy | jq .
```

### Connecting to Atlas directly

```bash
mongosh "$MONGODB_URI"
use portfolio_advisor
show collections
db.holdings.find({deleted_at: null}).count()
```

Always include `{deleted_at: null}` when querying `holdings`. Soft-deleted (fully-exited) holdings are still in the collection but excluded from every aggregation in the app.

---

## 5. Environment variable reference

The full set of settings is defined in `app/config/settings.py` as a Pydantic v2 `BaseSettings`. Pydantic validates on app boot — missing required vars or wrong types crash the API on startup (visible via `journalctl -u portfolio-advisor -n 50` on EC2).

### Required

| Var | Type | Purpose |
|---|---|---|
| `MONGODB_URI` | str | Full Atlas connection string `mongodb+srv://<user>:<pass>@personal.3eano.mongodb.net/...` |
| `MONGODB_DB_NAME` | str | Database name. Production: `portfolio_advisor` |
| `ANTHROPIC_API_KEY` | str | Anthropic API key for Claude (Sonnet + Haiku) |
| `ANTHROPIC_MODEL_PRIMARY` | str | Claude Sonnet 4.5 model ID for dossier authoring |
| `ANTHROPIC_MODEL_FAST` | str | Claude Haiku 4.5 model ID for news classification |
| `TAVILY_API_KEY` | str | Tavily search API key |
| `TAVILY_MONTHLY_QUOTA` | int | Searches per month; checked by `news_fetcher` before every call |
| `RESEND_API_KEY` | str | Resend transactional email API key |
| `RESEND_FROM_EMAIL` | str | From-address for digests and drift alerts (e.g. `advisor@portfolioadvisor.your-domain`) |
| `RESEND_TO_EMAIL` | str | Single-user destination address |
| `NTFY_PUBLIC_URL` | str | `https://ntfy.sh` (public) — used by `push_public` |
| `NTFY_PUBLIC_TOPIC_PRICE` | str | Random unguessable topic for `price` channel pushes |
| `NTFY_PUBLIC_TOPIC_NEWS` | str | Random unguessable topic for `news` channel pushes |
| `NTFY_PUBLIC_TOPIC_ERRORS` | str | Random unguessable topic for F4 cron-health errors |
| `NTFY_PUBLIC_TOPIC_DIGESTS` | str | Random unguessable topic for weekly digests |

### Currently-orphan (post-TD8, slated for TD9 cleanup)

| Var | Why it's still here |
|---|---|
| `NTFY_URL` | Pointed at self-hosted ntfy on Tailscale Funnel. Service decommissioned 2026-05-18 |
| `NTFY_USER` | HTTP Basic auth for self-hosted ntfy. Unused |
| `NTFY_PASS` | HTTP Basic auth for self-hosted ntfy. Unused |

These can be deleted from `settings.py` + the secrets file in a follow-up commit (TD9). Don't remove them in isolation — touching `settings.py` risks masking a Pydantic v2 validation error on boot.

### Optional / tunable

Anything else in `app/config/settings.py` has a sensible default. The most useful ones to know about: scoring weights (`WEIGHT_*` if exposed), gate thresholds (`MARKET_CAP_MIN_CR`, `EARNINGS_PROXIMITY_DAYS`, `MAX_HIGH_SEVERITY_NEGATIVE_NEWS_30D`), and any feature flags. Check `settings.py` for the current list — it's the source of truth.

---

## 6. Secrets layout

- **Mac (dev)**: `<repo>/.env`, loaded by Pydantic's `BaseSettings` automatically. Not committed (in `.gitignore`).
- **EC2 (prod)**: `/etc/portfolio-advisor/secrets.env`, owned by root, mode 0640, group `ubuntu`. The systemd unit `portfolio-advisor.service` loads it via `EnvironmentFile=`.
- **Cron scripts** also need the secrets in their environment. Crontab entries set `PYTHONPATH=.` and run via `uv run`, which inherits the shell environment — so the crontab user's shell profile (`~/.profile` or `~/.bashrc`) must `set -a; source /etc/portfolio-advisor/secrets.env; set +a`. Verify with `ssh ubuntu@100.112.20.41 'env | grep ANTHROPIC'` after a fresh login.

When a secret rotates:

1. Edit `/etc/portfolio-advisor/secrets.env` on EC2.
2. `sudo systemctl restart portfolio-advisor`.
3. `curl -sS http://localhost:8000/health` from inside the box.
4. Update your local `<repo>/.env` for symmetry.
5. If the secret is used by cron scripts, also re-source your shell profile (`exec $SHELL`) so the next cron tick picks it up.

Never commit secrets. Never paste them in chat. Never include them in error reports.

---

## 7. Cron reference

Crontab lives on EC2 — `ssh ubuntu@100.112.20.41 'crontab -l'`. Source-of-truth registry is `app/services/cron_heartbeat_service.py::CRON_REGISTRY` (10 entries). The daily F4 health check at 21:00 IST compares heartbeats against this registry and pushes to `errors` channel if anything is missing or last-failed.

| Schedule (IST) | Crontab line | Heartbeat name | Purpose |
|---|---|---|---|
| `0 3 * * *` | `refresh_instruments.py` | `refresh_instruments` | Refresh NSE master from `EQUITY_L.csv` (~2,365 symbols) into `instruments` |
| `0 19 * * 1-5` | `refresh_prices.py` | `refresh_prices_eod` | Daily EOD OHLCV bars for held + universe ISINs into `prices_daily` |
| `*/15 9-15 * * 1-5` | `refresh_prices_intraday.py` | `refresh_prices_intraday` | 15-min snapshots during market hours into `prices_intraday` (append-only) |
| `30 19 * * 1-5` | `take_reconciliation_snapshot.py` | `reconciliation_snapshot` | Auto reconciliation against cached ICICI baseline; emits `_send_drift_alerts` on threshold breach |
| `0 6 * * 0` | `refresh_fundamentals.py` | `refresh_fundamentals` | Weekly fundamentals for the buy-side universe into `instruments_fundamentals` |
| `30 6 * * 0` | `fetch_news_for_universe.py --include-held` | `fetch_news_universe` | Weekly Tavily + Haiku classified news for universe ∪ held ∪ watchlist into `news_articles` (A16 — `--include-held` is mandatory) |
| `0 7 * * 0` | `run_weekly_suggestions.py --direction=both --notify --run-type scheduled` | `weekly_suggestions` | Buy + sell pipelines + combined digest (one email + one ntfy push for both sides) |
| `0 21 * * *` | `cron_health_check.py` | (consumer, not producer) | F4 daily comparator; pushes to `errors` ntfy topic if heartbeats lag |

### Registry-only entries (idle in current deployment)

`weekly_suggestions_sell` is registered for topology flexibility — if someone ever splits the Sunday job into separate `--direction=buy` (07:00) and `--direction=sell` (07:30) crontab lines instead of the current `--direction=both`, this entry would receive its heartbeat. Today the umbrella `weekly_suggestions` covers both sides under one heartbeat, and `weekly_suggestions_sell` is idle. Not a bug.

### Editing crons

```bash
ssh ubuntu@100.112.20.41
crontab -e
# Make change, save
crontab -l       # verify
```

After any cron edit that changes schedule, ALSO update `CRON_REGISTRY` in `app/services/cron_heartbeat_service.py` and ship the code change — otherwise the F4 health check will alert on the mismatch.

---

## 8. Scripts reference

Every script lives in `scripts/`, runs via `PYTHONPATH=. uv run python scripts/<name>.py`, and follows a single convention: `--dry-run` (where it applies) is a no-side-effects preview that prints what would change. Always dry-run before live.

### Cron-driven (production)

#### `refresh_instruments.py` (49 lines)

Daily NSE master refresh. Downloads `EQUITY_L.csv` from NSE and upserts the `instruments` collection. Idempotent. No flags. Runs `cron_run(name="refresh_instruments")` to emit a heartbeat.

#### `refresh_prices.py` (164 lines)

Daily EOD OHLCV for held ISINs + Phase 2 universe ISINs. Pulls via `yfinance`, upserts one `prices_daily` doc per ISIN per trading day. Idempotent (re-running overwrites the day's bar). Skips weekends and known NSE holidays.

#### `refresh_prices_intraday.py` (53 lines)

15-min snapshot during market hours. **APPENDS** — never overwrites. The selection logic in `bulk_get_latest_prices` picks the most recent same-day intraday row, falling back to EOD when no intraday exists. Cheap, low-risk.

#### `take_reconciliation_snapshot.py` (34 lines)

Auto-reconciliation against the cached ICICI baseline in `user_profile.reconciliation_baseline`. Writes a `reconciliation_snapshots` doc with both sides' invested / current_value / deltas. If thresholds breach (`_DRIFT_THRESHOLDS` in `app/services/reconciliation.py`), calls `_send_drift_alerts` → one `push_public(channel="price", ...)` + one `notify.email(...)`. Post-A2-part-2 (commit 1 of Chat 5), the email path correctly gates `sent.append("email")` on `result["ok"]`.

#### `refresh_fundamentals.py` (176 lines)

Weekly fundamentals for the Phase 2 universe (top 250 NSE by market cap). Upserts one `instruments_fundamentals` doc per ISIN with ROE, ROA, operating margin, debt-to-equity, P/E, P/B, earnings growth YoY, plus the fundamentals timestamp. Missing-data ISINs are skipped (not zeroed) so cross-sectional normalization isn't poisoned.

#### `fetch_news_for_universe.py` (175 lines)

Weekly news fetch + classification for universe ∪ held ∪ watchlist. **Must be run with `--include-held`** (verified A16). For each ISIN, issues a Tavily search (≤5 results/ISIN/week), then runs each hit through `news_classifier` (Claude Haiku) to assign polarity + severity + category. Writes to `news_articles`. Consults `tavily_quota` before every Tavily call and refuses once the monthly cap hits.

#### `run_weekly_suggestions.py` (220 lines)

The orchestrator. Sunday 07:00 IST in production with `--direction=both --notify --run-type scheduled`.

Flags:
- `--direction={buy,sell,both}` — which pipeline(s) to run. Production uses `both`.
- `--notify` — emit email + ntfy. Omit for silent reruns.
- `--run-type={scheduled,manual,backfill}` — recorded in `suggestion_runs.run_type`. The cron-health alerter excludes non-`scheduled` runs from staleness checks.
- `--limit <N>` — top N candidates to persist (default in code).
- `--skip-dossiers` — useful for fast reruns when you only care about the ranking, not the Claude dossiers (~30s vs ~5min).

For `--direction=both`, dispatches to both `_run_buy_pipeline` and `_run_sell_pipeline`, then calls `digest_delivery.send_combined_digest(buy_run, sell_run)` — ONE email + ONE ntfy push covering both sides. The standalone `--direction=sell` reach calls `send_weekly_digest(run)` instead (refresh of the A17 stale NOTE in `_run_sell_pipeline`).

#### `cron_health_check.py` (126 lines)

F4 daily alerter. Compares `cron_heartbeats` against `CRON_REGISTRY` and pushes to the `errors` ntfy channel if any cron is missing a heartbeat or last-failed. Runs daily at 21:00 IST. Does NOT itself write a heartbeat (consumer, not producer).

#### `track_suggestion_outcomes.py` (48 lines)

Per-candidate outcome tracking. Compares price-at-suggestion vs price-at-window-end and writes to `suggestion_outcomes`, feeding `/suggestions/performance`. Designed to run on demand (not currently cron-scheduled).

### Operator scripts (manual)

#### `init_db.py` (60 lines)

First-time database initialization. Creates the 16 collections (Phase 1 + Phase 2) and their indexes. **Idempotent — safe to re-run.** Use after a fresh Atlas cluster, or after wiping a collection.

#### `import_orderbooks.py` (260 lines)

ICICI CSV import. Reads broker CSV exports and writes to `transactions_staging` keyed on `(broker, broker_txn_id)`. Idempotent — re-importing the same CSV doesn't double-write.

Flags:
- `--dry-run` — preview.
- `--broker {ICICI|ZERODHA|OTHER}` — broker source for the CSV format.
- `--user` (single-user system; default works).

After import, run `reconcile_staging.py` → `promote_staging.py`.

#### `reconcile_staging.py` (305 lines)

Stage 2 of the import pipeline. Matches `transactions_staging` rows against existing `transactions` + `symbol_overrides`. Flags conflicts (e.g. broker symbol not yet mapped to an ISIN). Auto-creates `symbol_overrides` for unambiguous matches.

Flags:
- `--dry-run` — preview matches and conflicts.
- `--auto-link` — auto-create `symbol_overrides` for unambiguous matches (writes to DB).

#### `promote_staging.py` (119 lines)

Stage 3 of the import pipeline. Moves matched rows from `transactions_staging` to live `transactions` — atomic per-row with an `transactions_audit` entry per promoted row. Triggers `recompute_holding(isin)` after each promotion.

Flags:
- `--dry-run` — preview.
- `--limit <N>` — process at most N rows (useful for first-time bulk imports).

#### `add_manual_transactions.py` (363 lines)

Corporate action workflow + manual transaction entry. Use for bonuses, splits, demergers, divestments, and any transaction not covered by the broker CSV.

Action subcommands: `--action {buy,sell,bonus,split,divestment,dividend}`. Each takes `--isin`, `--date`, and action-specific args (ratio for split/bonus; target-ISIN + ratio for demerger; etc.). Idempotent via deduplication on `(isin, date, action, ratio/amount)`.

After running, `recompute_holding(isin)` is triggered automatically. If the action creates a tax-basis vs broker-basis divergence (e.g. Section 49(2C) demerger), follow up with an entry in `seed_cost_basis_adjustments.py`.

#### `seed_cost_basis_adjustments.py` (101 lines)

Source of truth for IT-Act-driven divergences from broker-nominal cost. Currently seeds TMPV/TMCV 49(2C) demerger. Each seed entry reduces the IT-Act-correct cost basis on `holdings.invested_amount` while preserving the broker-nominal view via `totals.broker_invested` on `/portfolio/summary`. Idempotent.

Flags:
- `--dry-run` — preview.

#### `seed_nifty100.py` (161 lines)

⚠️ **Misnamed — actually seeds the top 250 NSE stocks by market cap** as the Phase 2 buy-side universe. Writes to `instruments` with a universe tag. Idempotent. Rename pending (out of scope for Chat 5).

Flags:
- `--dry-run` — preview.
- `--replace` — wipe and re-seed (use when the universe definition changes).

#### `smoke_test.py` (84 lines)

End-to-end smoke test of external transports. Hits Anthropic, MongoDB, public ntfy.sh, and Resend. Costs ~1 cent per run. Use after any infra change, secret rotation, or smoke check after deploy. Post-TD8 (commit 7a), no longer exercises self-hosted ntfy.

Expected output: 5 ✓ checks + 🎉 banner + 2 iPhone expectation bullets. Failure modes are documented inline.

---

## 9. Deploy checklist

```bash
# 1. Local: commit + push
git status
git push origin main

# 2. SSH to EC2
ssh ubuntu@100.112.20.41
cd /home/ubuntu/ai-stock-advisor-backend

# 3. Pull
git pull --ff-only

# 4. Sync deps (no-op if pyproject.toml + uv.lock unchanged)
/home/ubuntu/.local/bin/uv sync

# 5. Restart API
sudo systemctl restart portfolio-advisor
sleep 4

# 6. Health check
curl -sS http://localhost:8000/health
# Expected: {"status":"ok","mongo":"ok"}

# 7. Status check
sudo systemctl --no-pager status portfolio-advisor | head -20

# 8. Tail logs briefly to catch any boot warnings
sudo journalctl -u portfolio-advisor -n 30 --no-pager

# 9. Smoke test (only if external transports might be affected — secret rotation, dependency bumps, etc.)
PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/smoke_test.py
```

Rollback: `git reset --hard <prev-sha>`, `uv sync`, restart. Mongo schema changes are forward-compatible by convention (use `extra="forbid"` only on writer paths, not readers).

---

## 10. On-call runbook

### Daily check: did everything run?

```bash
curl -sS http://localhost:8000/cron/health | jq .
```

Returns every entry in `CRON_REGISTRY` with its last-success timestamp and any last-error message. If anything is stale or failed, the F4 alerter already pushed to the `errors` ntfy channel — check your iPhone.

### A specific cron failed

```bash
ssh ubuntu@100.112.20.41
# Cron logs live in ~/ (one per cron):
tail -200 /home/ubuntu/cron-<name>.log
# Heartbeat detail:
mongosh "$MONGODB_URI" --eval 'db.cron_heartbeats.findOne({cron_name: "<name>"})'
```

Re-run manually:
```bash
cd /home/ubuntu/ai-stock-advisor-backend
PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/<script>.py [--flags from crontab line]
```

If you re-run weekly suggestions outside the cron schedule, use `--run-type manual` so it doesn't inflate the scheduled-run statistics.

### A digest didn't arrive

Walk the data trail (full sequence in [`docs/data_flow.md`](docs/data_flow.md) under "When a stuck digest needs debugging"):

```bash
# 1. Did delivery happen?
mongosh "$MONGODB_URI" --eval 'db.digest_deliveries.find().sort({_id: -1}).limit(3).pretty()'

# 2. If delivery.email.ok = false, look at delivery.email.error
# 3. If ntfy is missing, confirm NTFY_PUBLIC_TOPIC_DIGESTS still matches your iPhone subscription
# 4. Re-trigger manually:
ssh ubuntu@100.112.20.41
cd /home/ubuntu/ai-stock-advisor-backend
PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/run_weekly_suggestions.py \
  --direction=both --notify --run-type manual
```

### A feedback action (passed/rejected/watchlist) didn't take effect

Two-mechanism exclusion (F5b) — bug can hide in either layer. Diagnostic order:

```bash
# 1. Did the audit row land?
mongosh "$MONGODB_URI" --eval 'db.monitored_stocks_audit.find({isin: "INE..."}).sort({_id: -1}).limit(5).pretty()'

# 2. Did the state mutation land?
mongosh "$MONGODB_URI" --eval 'db.monitored_stocks.findOne({isin: "INE..."})'

# 3. Run-build mechanism: rebuild a buy run; the ISIN should not appear:
PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/run_weekly_suggestions.py \
  --direction=buy --run-type manual --skip-dossiers

# 4. Serialization mechanism: hit /suggestions/latest and confirm user_action
#    reflects the latest feedback on historical runs too:
curl -sS http://localhost:8000/suggestions/latest?direction=buy | jq '.top_candidates[] | select(.isin=="INE...") | .user_action'
```

### Reconciliation drift alerted

```bash
# Most recent snapshot
mongosh "$MONGODB_URI" --eval 'db.reconciliation_snapshots.find().sort({_id: -1}).limit(1).pretty()'

# Did the alert delivery channels both fire?
# alerts_sent should be ['ntfy', 'email'] when both transports succeeded.
# Post-A2-part-2 (commit 1 of Chat 5), 'email' only appears when Resend actually accepted the message.
```

Then walk the corp-action runbook in [`docs/data_flow.md`](docs/data_flow.md) ("Adding a new corporate action") if the drift is corp-action driven.

### The API is down

```bash
ssh ubuntu@100.112.20.41
sudo systemctl --no-pager status portfolio-advisor
sudo journalctl -u portfolio-advisor -n 100 --no-pager
# Common cause: bad secret -> Pydantic validation error on boot
sudo systemctl restart portfolio-advisor
sleep 4
curl -sS http://localhost:8000/health
```

### Mongo Atlas is degraded

Check the Atlas console (M10 cluster `personal`). If the cluster is healthy but our connection is failing, the dev IP allowlist may have expired (Atlas defaults to 1-week temp entries) — re-add. If the cluster is degraded, the API will return 503 on `/health` until it recovers; this is fine, nothing to do but wait.

---

## 11. Known operational gotchas

1. **`seed_nifty100.py` actually seeds the top 250.** The name lies. Don't read the file name as a spec.
2. **`SignalScore.raw_value` shape changed 2026-05-23 (commit 2 of Chat 5).** Pre-commit-2 runs in `suggestion_runs` have `raw_value` = stringified normalized score. Post-commit-2 runs have `raw_value` = the actual raw input. The UI explainability layer derives display from a fresh fundamentals lookup, not from `raw_value`, so this is data-correctness only for now.
3. **`notify.email` never raises post-A2-part-1.** It returns `{ok, id, error}`. Old try/except patterns silently believed every email succeeded. Audited and fixed in commit 1 (`_send_drift_alerts`). Any new email caller must branch on `result["ok"]`.
4. **`notify.push_public` DOES raise on failure** (via `_publish` → `response.raise_for_status()`). The two transports are NOT symmetric. See `_send_drift_alerts` for the canonical pattern.
5. **Suggestion direction defaults to `"buy"`.** Forgetting to pass `direction="sell"` from a new code path will silently produce a buy run.
6. **Production digest is one combined email + push** via `send_combined_digest`, not two. The standalone `send_weekly_digest` inside `_run_sell_pipeline` is only the manual-rerun path. Don't replicate it elsewhere.
7. **Tavily quota is monthly, not per-run.** A failed Sunday fetch eats its weekly budget. A re-trigger mid-week eats more. Watch `tavily_quota` if you re-run.
8. **`prices_intraday` is append-only within a day.** Multiple rows per ISIN per day is expected. Always sort by `_id` desc (or timestamp) to get the latest.
9. **Mongo dates are timezone-naive.** Strip tzinfo before comparing against `datetime.utcnow()`-derived values. See `_naive()` in `validate_replay`.
10. **Decimal vs Decimal128.** Never write raw `Decimal` to Mongo — pymongo raises `bson.errors.InvalidDocument`. Use the `_convert_decimals_to_decimal128` helper.
11. **Soft-delete filter is universal.** Always include `{"deleted_at": null}` when querying `holdings`. Many bugs traced to a missing filter showing exited holdings in "active" aggregations.
12. **Self-hosted ntfy is gone (TD8, 2026-05-18).** `NTFY_URL` / `NTFY_USER` / `NTFY_PASS` still exist as orphan env vars (TD9 cleanup pending). Don't assume their presence means private ntfy is back; the service is stopped + disabled.
13. **GitHub raw URL cache can lag the actual repo HEAD.** When verifying file bytes before a code change (per Section 14 of Project_State.md), prefer `sed` against the on-disk file on EC2 over `curl` against `raw.githubusercontent.com`.

---

## 12. Glossary

- **Phase 1 / Phase 2** — portfolio truth vs suggestions engine. See Section 1 + [`docs/data_flow.md`](docs/data_flow.md).
- **F2 / F2b** — weekly digest delivery (F2 = original; F2b = 2026-05-18 migration from self-hosted ntfy to public ntfy.sh).
- **F4** — cron observability via `cron_heartbeats` + `cron_health_check.py`.
- **F5a / F5b** — stateful feedback (5a = state machine; 5b = two-mechanism exclusion guarantee).
- **F6 / F10** — feedback UI + write-before-apply audit pattern.
- **F14** — earnings-proximity gate, shared between buy and sell pipelines.
- **TD8** — self-hosted ntfy decommission (shipped 2026-05-18, code cleanup 2026-05-23 in commits 7a/7b).
- **TD9** — orphan `NTFY_*` env var cleanup (pending).
- **A1 / A2 / A3 / ... / A19** — Chat-5 audit findings. See `docs/Project_State.md` for the full registry. Commits 1-7b of Chat 5 cleared A2-part-2 through A19 plus TD8.
- **Q3** — open question: `holdings.stop_loss` field exists but is never read or written. Deferred from Chat 5.
- **Two-mechanism exclusion** — F5b guarantee that feedback'd ISINs are excluded BOTH at run-build (`get_excluded_isins`) AND at serialization (`_build_user_action`). Both must hold or stale state leaks into the UI.
- **Write-before-apply audit** — F10 / Phase 1 transactions pattern: insert the audit row BEFORE mutating state. If the audit insert fails, the state change never happens.

---

## Where to look next

- The architectural deep-dive lives in [`docs/data_flow.md`](docs/data_flow.md).
- The full project history, locked feature set, audit registry, and open questions live in `docs/Project_State.md`.
- The frontend lives in the [`ai-stock-advisor-frontend`](https://github.com/doshisahil95/ai-stock-advisor-frontend) repo.
