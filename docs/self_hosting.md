# Self-Hosting: Stand Up Your Own Instance

> **Status: DOC/PREP ONLY (master_todo #61).** This document is the onboarding
> guide + the **outline** of a future one-time bootstrap script that would let
> a *different* person stand up their own instance of this tool from scratch.
> **No generalized deploy script has shipped yet.** The committed `deploy.sh`
> at repo root is the author's EC2-specific *update* script (pull → sync →
> render/install crontab → restart), **not** a first-time provisioner and
> **not** parameterized for another person's machine. The "Script outline"
> section below is the design for that future helper; everything else is a
> manual runbook you can follow today.
>
> Companion docs: `docs/Project_State.md`, `docs/data_flow.md`,
> `docs/onboarding_and_access.md` (#60, adding viewers/recipients to an
> *existing* instance), and both repo READMEs (their §3/§8/§9 setup+deploy
> sections are the authoritative per-repo manuals this doc references).

---

## Who this is for

Someone who wants to run their **own** copy — their own Atlas cluster, their
own broker data, their own API keys — not view the author's instance (that's
`docs/onboarding_and_access.md`). This is inherently a fork-and-run exercise:
the system is single-user (Project_State §1, §21), so "another person" means
"another whole instance."

---

## What you are standing up

Two repos, one box, one database:

- **Backend** (`ai-stock-advisor-backend`) — FastAPI on `:8000`.
- **Frontend** (`ai-stock-advisor-frontend`) — Next.js on `:3000`.
- **MongoDB Atlas** — one database (default name `portfolio`, see
  `MONGODB_DB_NAME`).
- **Compute** — one small Linux box (the author uses AWS EC2 t3.micro,
  ap-south-1). Any always-on Linux host works.
- **Network** — Tailscale mesh, **no public ingress** (Tailscale is the auth
  perimeter; there is no login).

### External accounts you must create first

Everything below is required before the app will boot (Pydantic validates all
required settings on startup — a missing one crashes the API):

| Service | Why | Cost |
|---|---|---|
| MongoDB Atlas | The database | Free tier works to start; author uses M10 |
| Anthropic | Claude Sonnet (dossiers) + Haiku (news classify) | Pay-as-you-go |
| Tavily | News search | Free tier (daily quota) |
| Resend | Transactional email (digests/alerts) + a verified sending domain | Free tier |
| ntfy.sh | Push notifications (public, unguessable topics) | Free |
| Tailscale | The network perimeter | Free tier |

---

## Required configuration (backend secrets)

The complete required set is defined in `app/config/settings.py`. As of the
current HEAD the **required** keys (no default → must be present) are:

```ini
# /etc/portfolio-advisor/secrets.env   (EC2, root-owned, mode 0640)
#   or  <repo>/.env                    (Mac dev, gitignored, mode 600)

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Tavily
TAVILY_API_KEY=tvly-...

# MongoDB (URL-encode special chars in the password)
MONGODB_URI=mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/?retryWrites=true&w=majority

# Public ntfy.sh topics — generate LONG random unguessable strings for each
NTFY_PUBLIC_TOPIC_PRICE=<random>
NTFY_PUBLIC_TOPIC_NEWS=<random>
NTFY_PUBLIC_TOPIC_ERRORS=<random>
NTFY_PUBLIC_TOPIC_DIGESTS=<random>

# Resend (RESEND_FROM domain must be verified in Resend for SPF/DKIM)
RESEND_API_KEY=re_...
RESEND_FROM=advisor@your-verified-domain.example
RESEND_TO=you@example.com
```

Keys **with** defaults you may override (`MONGODB_DB_NAME=portfolio`,
`ANTHROPIC_MODEL_PRIMARY`, `ANTHROPIC_MODEL_FAST`, `TAVILY_*` limits,
`NTFY_PUBLIC_URL`, `TAILSCALE_IP`, `API_PORT`) — see `settings.py` for the
current authoritative list; it is the source of truth.

> **Generate ntfy topics** with something like
> `python3 -c "import secrets; print(secrets.token_urlsafe(24))"` per channel.
> Whoever guesses a topic can read those pushes, so keep them long + secret.

**Frontend env** (`.env.local` / systemd `Environment=`): only
`NEXT_PUBLIC_API_BASE_URL` — the backend base URL with no trailing slash
(`http://<tailscale-ip>:8000` on the box, `http://localhost:8001` for Mac dev).

---

## Manual bootstrap runbook (today)

This is what the future script (below) will automate. Following it by hand
works right now. It assumes a fresh Linux box you can SSH into, with Tailscale
already installed + logged in on it.

### 1. System prerequisites
```bash
# Python 3.12 + git + Node 22 + uv
sudo apt update && sudo apt install -y git python3.12 python3.12-venv
curl -LsSf https://astral.sh/uv/install.sh | sh          # uv (backend)
# Node 22 (frontend) — via nodesource or nvm, per your distro.
```

### 2. Clone both repos
```bash
cd ~
git clone https://github.com/<you>/ai-stock-advisor-backend.git
git clone https://github.com/<you>/ai-stock-advisor-frontend.git
```

### 3. Backend secrets
```bash
sudo mkdir -p /etc/portfolio-advisor
sudo vim /etc/portfolio-advisor/secrets.env      # paste the block above
sudo chmod 0640 /etc/portfolio-advisor/secrets.env
sudo chown root:$(whoami) /etc/portfolio-advisor/secrets.env
```

### 4. Backend deps + DB init + smoke
```bash
cd ~/ai-stock-advisor-backend
uv sync
PYTHONPATH=. uv run python scripts/init_db.py      # creates collections + indexes, seeds user_profile
PYTHONPATH=. uv run python scripts/smoke_test.py   # 5 ✓ checks: Config/Anthropic/Mongo/ntfy/Email
```
If `init_db.py` can't reach Atlas → your box's IP isn't allowlisted in the
Atlas cluster. If `smoke_test` fails a transport, that credential is wrong.

### 5. Backend service (systemd)
Mirror the author's unit (Project_State §4): `uvicorn app.main:app --port 8000
--host 0.0.0.0`, `User=<you>`, `EnvironmentFile=/etc/portfolio-advisor/secrets.env`,
`PYTHONPATH=<repo>`, `PYTHONUNBUFFERED=1`, single worker. Enable + start, then:
```bash
curl -sS http://localhost:8000/health           # expect {"status":"ok","mongo":"ok"}
```

### 6. Crontab (version-controlled)
The schedule is rendered from `CRON_REGISTRY` into `ops/crontab`. **The paths
in `ops/crontab` are hardcoded to `/home/ubuntu/...`** — see the
"generalization gaps" section; on a different username/path you must
regenerate or hand-fix them before installing:
```bash
cd ~/ai-stock-advisor-backend
PYTHONPATH=. uv run python -m scripts.render_crontab --check   # verify committed file matches registry
crontab ops/crontab
diff <(crontab -l) ops/crontab                                 # must be clean
```

### 7. Frontend
```bash
cd ~/ai-stock-advisor-frontend
npm install --legacy-peer-deps
# point the build at your backend:
echo 'NEXT_PUBLIC_API_BASE_URL=http://<your-tailscale-ip>:8000' > .env.local
npm run build
# run under systemd (frontend README §7 Option A) on :3000, then:
curl -sS -o /dev/null -w "ui -> %{http_code}\n" http://localhost:3000   # expect 200
```

### 8. Seed your own portfolio data
This is *your* data, not the author's. Options, in order of realism:
- Import broker CSVs: `import_orderbooks.py` → `reconcile_staging.py` →
  `promote_staging.py` (backend README §8 has the flags — note
  `reconcile_staging.py` takes **no** flags, a documented drift the author hit
  at GO-LIVE).
- Manual/corporate actions: `add_manual_transactions.py`, then
  `seed_cost_basis_adjustments.py` for any §49(2C)-style divergence.
- Universe for suggestions: `seed_nifty100.py` (one-time), then the Sunday
  crons populate fundamentals/news.

### 9. Access
Reach the UI at `http://<your-tailscale-ip>:3000` from any device on your
tailnet. To add viewers/recipients later, see `docs/onboarding_and_access.md`.

---

## Script outline: `scripts/bootstrap_instance.sh` (future, NOT built)

The future #61 code deliverable is a **one-time provisioner** distinct from the
existing update-only `deploy.sh`. Proposed shape — a guided, idempotent,
parameterized bash script (or a thin Python CLI) that automates steps 3–7
above and refuses to clobber an existing install:

```bash
#!/usr/bin/env bash
set -euo pipefail

# ── Parameters (env or flags; NO hardcoded /home/ubuntu, IP, or user) ──
REPO_DIR_BACKEND="${REPO_DIR_BACKEND:-$HOME/ai-stock-advisor-backend}"
REPO_DIR_FRONTEND="${REPO_DIR_FRONTEND:-$HOME/ai-stock-advisor-frontend}"
SECRETS_PATH="${SECRETS_PATH:-/etc/portfolio-advisor/secrets.env}"
RUN_USER="${RUN_USER:-$(whoami)}"
TAILSCALE_IP="${TAILSCALE_IP:-$(tailscale ip -4 2>/dev/null | head -1)}"
API_PORT="${API_PORT:-8000}"
UI_PORT="${UI_PORT:-3000}"
UV_BIN="${UV_BIN:-$HOME/.local/bin/uv}"

# 1. Preflight: check git/uv/node present; refuse if secrets file already
#    exists AND service already running (idempotency guard — don't nuke a
#    live install).
# 2. Prompt for (or read from env) the required secrets, write SECRETS_PATH
#    with 0640 root:$RUN_USER. Validate none are empty before proceeding.
# 3. Backend: uv sync; run init_db.py; run smoke_test.py — ABORT on any
#    failure (a bad credential must stop bootstrap, not half-provision).
# 4. Render + install a systemd unit for the backend from a template,
#    substituting $REPO_DIR_BACKEND / $RUN_USER / $SECRETS_PATH / $API_PORT.
# 5. Render + install a systemd unit for the frontend, substituting
#    $REPO_DIR_FRONTEND / $RUN_USER / $UI_PORT and writing
#    NEXT_PUBLIC_API_BASE_URL=http://$TAILSCALE_IP:$API_PORT.
# 6. Crontab: regenerate ops/crontab with the correct paths for $RUN_USER /
#    $REPO_DIR_BACKEND / $UV_BIN (see generalization gaps below), then
#    `crontab ops/crontab` + drift-validate.
# 7. Health gate: curl /health (ok/ok) and the UI (200) before declaring
#    success; print next steps (Atlas IP allowlist, data seeding, ntfy
#    iPhone subscription).
```

Design rules for that script (consistent with the project's conventions):
- **Idempotent + safe:** re-running must not destroy data or a live service;
  guard on "already installed."
- **Fail-fast:** any smoke/health failure aborts (`set -e`), mirroring
  `deploy.sh`'s hard-fail crontab validation.
- **No hardcoded identity:** everything the current `deploy.sh` /
  `ops/crontab` hardcodes (`/home/ubuntu`, `100.112.20.41`, `ubuntu` user,
  `/home/ubuntu/.local/bin/uv`) becomes a parameter.
- **Reuses existing scripts:** `init_db.py`, `smoke_test.py`,
  `render_crontab.py` are the building blocks — the bootstrap orchestrates
  them, it does not reimplement them.

---

## Generalization gaps in the current code (what #61's code cycle must fix)

These are the concrete places today's code assumes the author's box. A future
code cycle (not this one) should parameterize them:

1. **`deploy.sh`** hardcodes `cd ~/ai-stock-advisor-backend` and
   `curl http://100.112.20.41:8000/health`. Update-only; not a provisioner.
2. **`ops/crontab`** hardcodes `/home/ubuntu/ai-stock-advisor-backend`,
   `/home/ubuntu/.local/bin/uv`, and `/home/ubuntu/cron-*.log` on every line.
   These come from `cron_heartbeat_service` wrapper constants
   (`CRON_REPO_DIR`, `CRON_UV_BIN`, `CRON_LOG_DIR`) — generalization means
   making those configurable (e.g. from settings/env) so `render_crontab.py`
   emits the right paths for a different user.
3. **systemd units** are documented in Project_State §4 / the READMEs but are
   **not committed as templates** — the bootstrap script should ship
   parameterized unit templates.
4. **`init_db.py`** seeds a `user_profile` with `_id: "sahil"` hardcoded and
   derives the display name from `RESEND_TO`. A generic install should derive
   the profile id from the installer (or make it configurable) rather than the
   literal `"sahil"`.
5. **Atlas IP allowlist** is a manual console step per box; the bootstrap can
   only *remind*, not automate (it needs Atlas API keys the user may not want
   to grant).

---

## What this doc deliberately does NOT do

- **No multi-tenant / shared instance.** Each person runs their own instance;
  single-user is a hard design constraint (§21).
- **No public ingress.** The instance stays Tailscale-only, no login.
- **No code shipped this cycle.** This is #61's DOC/PREP deliverable. When the
  `bootstrap_instance.sh` outline is taken up, it becomes its own master_todo
  unit with the standard commit + verify block, and closes the generalization
  gaps listed above.
