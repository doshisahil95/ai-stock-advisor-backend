# Self-Hosting & EC2 Rebuild Runbook

> **Status: the one-time provisioner `scripts/bootstrap_instance.sh` (#84) HAS SHIPPED.**
> This document is the operator runbook for standing up **or rebuilding** the instance:
> what it needs (secrets, Tailscale, OS), the exact step-by-step, and — in §10 — the
> concrete values used the last time the box was rebuilt end-to-end (2026-11-14, after
> the original EC2 instance was accidentally terminated).
>
> Companion docs: `docs/Project_State.md` (§3/§4 hold the *current* infra values),
> `docs/onboarding_and_access.md` (adding *other* viewers/recipients),
> `docs/data_flow.md`, and both repo READMEs.

---

## 1. What you are standing up

Two repos, one box, one database:

- **Backend** (`ai-stock-advisor-backend`) — FastAPI on `:8000` (`uvicorn app.main:app`).
- **Frontend** (`ai-stock-advisor-frontend`) — Next.js on `:3000`.
- **MongoDB Atlas** — one database (default name `portfolio`, see `MONGODB_DB_NAME`).
- **Compute** — one small Linux box (AWS EC2 **t3.micro**, `ap-south-1`, **Ubuntu 24.04 LTS**).
- **Network** — **Tailscale** mesh, **no public ingress** (Tailscale is the auth perimeter;
  there is no login).

### External accounts you must have

| Service | Why | Cost |
|---|---|---|
| MongoDB Atlas | The database | Free tier works; author uses M10 |
| Anthropic | Claude Sonnet (dossiers) + Haiku (news classify) | Pay-as-you-go |
| Tavily | News search | Free tier (daily quota) |
| Resend | Transactional email (digests/alerts) + a verified sending domain | Free tier |
| ntfy.sh | Push notifications (public, unguessable topics) | Free |
| Tailscale | The network perimeter | Free tier |

---

## 2. Required secrets

The authoritative list is `app/config/settings.py`. The **required** keys (no default →
must be present, or the API crashes on boot via Pydantic validation) are:

```ini
# /etc/portfolio-advisor/secrets.env   (EC2, root-owned, mode 0640, group ubuntu)

ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
MONGODB_URI=mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/?retryWrites=true&w=majority
NTFY_PUBLIC_TOPIC_PRICE=<random>
NTFY_PUBLIC_TOPIC_NEWS=<random>
NTFY_PUBLIC_TOPIC_ERRORS=<random>
NTFY_PUBLIC_TOPIC_DIGESTS=<random>
RESEND_API_KEY=re_...
RESEND_FROM=advisor@your-verified-domain.example
RESEND_TO=you@example.com
```

Keys **with** defaults you may override — most usefully `TAILSCALE_IP` (defaults to the
author's box; set it to `tailscale ip -4`), plus `MONGODB_DB_NAME=portfolio`,
`ANTHROPIC_MODEL_PRIMARY`, `ANTHROPIC_MODEL_FAST`, `TAVILY_*` limits, `NTFY_PUBLIC_URL`,
`API_PORT`, and the optional `RESEND_CC`. See `settings.py` for the authoritative list.

> **Gotchas:**
> - **`MONGODB_URI` must use a literal `&`**, not `\&`. A `\&` (common when a `.env` was
>   written to be `source`-able by bash) leaks into the value and makes pymongo warn
>   `"The value of retrywrites must be 'true' or 'false'"`.
> - The legacy `NTFY_URL` / `NTFY_USER` / `NTFY_PASS` keys were **removed** (TD9) — they
>   are ignored if present (`extra="ignore"`), so a copied `.env` is harmless but should
>   be trimmed.
> - `settings.py` reads this file **directly** (`env_file=`), so the app does not need the
>   secrets exported into the shell. (The README's note about sourcing them in `~/.profile`
>   is belt-and-braces for cron shells, not strictly required.)
> - Generate ntfy topics with `python3 -c "import secrets; print(secrets.token_urlsafe(24))"`.
>   Whoever guesses a topic can read those pushes, so keep them long + secret.

**Frontend env** (systemd `Environment=`): only `NEXT_PUBLIC_API_BASE_URL` — the backend
base URL, no trailing slash (`http://<tailscale-ip>:8000`). It is baked at **build** time.

---

## 3. Tailscale — the network perimeter (do this BEFORE the provisioner)

There is no public ingress and no app login: **anything that can reach `:3000`/`:8000`
sees everything**. The tailnet ACL is therefore the entire access-control layer, and it
is **not** the default allow-all on the author's tailnet.

### 3.1 The tailnet ACL — the EC2 node **MUST** carry `tag:server`

The author's tailnet policy (Tailscale admin console → **Access controls**) is:

```jsonc
{
  "tagOwners": {
    "tag:server": ["autogroup:admin"]
  },
  "acls": [
    {
      "action": "accept",
      "src":    ["autogroup:member"],
      "dst":    ["tag:server:22,443,3000,8000"]
    }
  ],
  "ssh": [
    {
      "action": "check",
      "src":    ["autogroup:member"],
      "dst":    ["tag:server"],
      "users":  ["ubuntu"]
    }
  ],
  "nodeAttrs": [
    {
      "target": ["tag:server"],
      "attr":   ["funnel"]
    }
  ]
}
```

**Consequence:** the `acls` rule only grants access to nodes carrying **`tag:server`**. If
the new EC2 node is not tagged, members (your Mac, your phone) **cannot reach `:3000`/`:8000`
or SSH at all**. Tagging is mandatory, not optional.

> The `funnel` node attribute is present but **Funnel is NOT used** by this app (it was
> decommissioned in TD8). Never run `tailscale funnel`. Port `443` in the ACL is a leftover.

### 3.2 Join the box to the tailnet

```bash
curl -fsSL https://tailscale.com/install.sh | sh

# Join + tag in one step (the tag:server owner is autogroup:admin, so log in as admin):
sudo tailscale up --ssh --advertise-tags=tag:server
#   → open the printed URL and authenticate with the identity that OWNS the tailnet

tailscale ip -4          # note this — the frontend build and CORS depend on it
tailscale status         # a tagged node shows "-" in the owner column
```

If `--advertise-tags` doesn't take, tag it in the console instead (most reliable):
**Machines → the new node → ⋯ → Edit ACL tags → check `tag:server` → Save.**

`--ssh` enables Tailscale SSH (the ACL `ssh` rule targets `tag:server`, user `ubuntu`;
action `check` means a periodic browser re-auth).

### 3.3 Key expiry

**Machines → node → ⋯ → Disable key expiry.** Node keys expire after ~180 days by default,
which silently drops the box off the tailnet and makes the whole app unreachable. (Tagged
nodes are machine-owned and don't expire, so once `tag:server` is applied this is handled —
but disable it explicitly for personal devices like your phone.)

### 3.4 Reclaiming the tailnet IP after a rebuild

Tailnet IPs are tied to node identity, so a fresh box gets a **new** `100.x` address unless
you reclaim the old one:

1. **Before** joining the new box, **remove the old/terminated node** in
   **Machines** (otherwise its address stays reserved).
2. Then `sudo tailscale up` — the allocator usually hands the freed address back.
3. If it doesn't: `sudo tailscale down && sudo tailscale up`, or remove other stale nodes.

⚠️ **If the tailnet IP changes, three code spots must be updated** (all default to the old
author IP `100.112.20.41`): `app/main.py` CORS `allow_origin_regex` / `allow_origins`,
`app/services/reconciliation.py` (drift-email dashboard link), and `settings.TAILSCALE_IP`
(feeds `digest_delivery`'s dashboard link). The CORS regex now matches any
`http://100.x.x.x:<port>` tailnet origin, so only the two link sites + `TAILSCALE_IP`
matter going forward.

---

## 4. System prerequisites

### 4.1 OS / instance
- **Ubuntu 24.04 LTS (x86_64)**, `ap-south-1`, **t3.micro** (2 vCPU / 1 GiB).
- Root volume **≥ 16 GiB** (the 8 GiB default is too small for `node_modules` + `.next` + the uv venv).
- Security Group: **inbound SSH (22) from your IP only.** **Do NOT open 8000/3000** — Tailscale is the perimeter. Outbound: default (all).
- Associate an **Elastic IP** so the public/egress address is stable (SSH + the Atlas allowlist depend on it).

### 4.2 Timezone — **REQUIRED**
The crontab schedule is documented in **IST** and cron runs in the **system** timezone;
the F4 heartbeat logic uses `Asia/Kolkata`. A fresh Ubuntu box is UTC, so every cron fires
5.5 h late and the health check false-alarms. Set it first:

```bash
sudo timedatectl set-timezone Asia/Kolkata
timedatectl          # expect: Time zone: Asia/Kolkata (IST, +0530)
```

### 4.3 Swap — recommended on 1 GiB
`npm run build` (Next.js) and the ~5-minute Sunday dossier run are RAM-tight on t3.micro:

```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h
```

### 4.4 Packages, uv, Node
```bash
sudo apt update
sudo apt install -y git python3.12 python3.12-venv build-essential
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"       # and add to ~/.profile
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt install -y nodejs
node -v && npm -v                          # Node 22
```

---

## 5. Rebuild runbook (step-by-step)

Assumes the box is reachable over SSH and Tailscale is already up + tagged (§3).

### 5.1 Clone both repos (into `$HOME`)
```bash
cd ~
git clone https://github.com/doshisahil95/ai-stock-advisor-backend.git
git clone https://github.com/doshisahil95/ai-stock-advisor-frontend.git
```

### 5.2 Create the secrets file
```bash
sudo mkdir -p /etc/portfolio-advisor
sudo tee /etc/portfolio-advisor/secrets.env >/dev/null <<'EOF'
ANTHROPIC_API_KEY=...
TAVILY_API_KEY=...
MONGODB_URI=mongodb+srv://.../?retryWrites=true&w=majority
NTFY_PUBLIC_TOPIC_PRICE=...
NTFY_PUBLIC_TOPIC_NEWS=...
NTFY_PUBLIC_TOPIC_ERRORS=...
NTFY_PUBLIC_TOPIC_DIGESTS=...
RESEND_API_KEY=...
RESEND_FROM=...
RESEND_TO=...
TAILSCALE_IP=<tailscale ip -4>
EOF
sudo chmod 0640 /etc/portfolio-advisor/secrets.env
sudo chown root:ubuntu /etc/portfolio-advisor/secrets.env
```

### 5.3 Atlas allowlist
Add the box's **egress IP** (the Elastic IP) to the Atlas cluster's **Network Access** list:
```bash
curl -s ifconfig.me
```

### 5.4 Run the provisioner
```bash
cd ~/ai-stock-advisor-backend
export TAILSCALE_IP=$(tailscale ip -4)
export PROFILE_ID=sahil          # IMPORTANT on an EXISTING db — see note
./scripts/bootstrap_instance.sh --dry-run     # review the plan first
./scripts/bootstrap_instance.sh
```
The provisioner runs: `uv sync` → `init_db.py` (idempotent) → `smoke_test.py` (real
Anthropic/Mongo/ntfy/email) → installs both systemd units → `npm install --legacy-peer-deps`
+ `npm run build` (bakes `NEXT_PUBLIC_API_BASE_URL`) → renders + installs the crontab →
health-gates `:8000` (`ok/ok`) and `:3000` (`200`).

> **`PROFILE_ID` matters on an existing database.** `init_db.py` seeds `user_profile` with
> `_id = PROFILE_ID` (defaults to the run user). Against the author's DB the existing doc is
> `_id="sahil"`, so set `PROFILE_ID=sahil` to hit the already-exists branch (no duplicate
> doc). On a genuinely fresh Atlas DB, the default is fine.

### 5.5 Post-bootstrap one-time infra (NOT installed by the provisioner)
```bash
# logrotate for ~/cron-*.log
sudo tee /etc/logrotate.d/portfolio-advisor >/dev/null <<'EOF'
/home/ubuntu/cron-*.log { weekly rotate 4 compress delaycompress notifempty missingok copytruncate su ubuntu ubuntu create 0664 ubuntu ubuntu }
EOF

# passwordless restart of the two services
sudo tee /etc/sudoers.d/portfolio-advisor-systemctl >/dev/null <<'EOF'
ubuntu ALL=(root) NOPASSWD: /usr/bin/systemctl restart portfolio-advisor.service, /usr/bin/systemctl restart portfolio-advisor-ui.service
EOF

# (optional, README §6) let cron shells see the secrets
grep -q portfolio-advisor ~/.profile || echo 'set -a; source /etc/portfolio-advisor/secrets.env; set +a' >> ~/.profile
```

### 5.6 Verify
```bash
curl -sS localhost:8000/health                              # {"status":"ok","mongo":"ok"}
curl -sS -o /dev/null -w '%{http_code}\n' localhost:3000    # 200
curl -sS localhost:8000/cron/heartbeats | jq '.health_summary'   # NOTE: /cron/heartbeats, not /cron/health
crontab -l                                                  # 10 lines, /home/ubuntu/... paths
sudo systemctl --no-pager status portfolio-advisor portfolio-advisor-ui

# Confirm the tailnet origin passes CORS (simulated browser preflight):
curl -s -o /dev/null -w 'preflight -> %{http_code}\n' -X OPTIONS \
  http://localhost:8000/portfolio/holdings \
  -H "Origin: http://$(tailscale ip -4):3000" -H 'Access-Control-Request-Method: PATCH'
```
Then open `http://<tailscale-ip>:3000` from a tailnet device and **perform a write** (edit a
holding) to confirm CORS end-to-end.

> `healthy: false` rows right after a restart / just after midnight are normal — they mean
> "expected today but hasn't run yet". A row is a real problem only if `last_status` is
> `failed`, or a cron that should have run today hasn't by the 21:00 IST health check.

---

## 6. The provisioner — `scripts/bootstrap_instance.sh` (#84)

The committed one-time provisioner automates §5.2–§5.6. It is **idempotent + safe**
(refuses to clobber a live install: secrets file present AND backend service active), and
**fail-fast** (`set -euo pipefail`; a smoke/health failure aborts). All parameters are
env-or-default — no hardcoded `/home/ubuntu`, IP, or user:

`REPO_DIR_BACKEND`, `REPO_DIR_FRONTEND`, `SECRETS_PATH`, `RUN_USER`, `TAILSCALE_IP`,
`API_HOST`, `API_PORT`, `UI_PORT`, `UV_BIN`, `PROFILE_ID`.

It reuses the building blocks (`init_db.py`, `smoke_test.py`, `render_crontab.py`) and
installs parameterized systemd units from `ops/systemd/*.template`.

> **`deploy.sh` is the UPDATE-only script** (pull → `uv sync` → `init_db` → crontab
> render/install/drift-validate → restart). First-time provisioning is
> `bootstrap_instance.sh`, not `deploy.sh`. `deploy.sh`'s `HEALTHCHECK_URL` default still
> points at the author's original IP — override it (`HEALTHCHECK_URL=http://localhost:8000/health`)
> on a different box.

---

## 7. Rebuild as executed — 2026-11-14

The original EC2 instance was accidentally terminated; the box was rebuilt from scratch.
Recorded here so the next rebuild is mechanical:

| Item | Value |
|---|---|
| Region / type / OS | `ap-south-1` / **t3.micro** / **Ubuntu 24.04.5 LTS** |
| Elastic IP | **13.204.207.223** |
| Tailscale IP | **100.107.240.8** (was `100.112.20.41` on the old box) |
| Tailscale tag | **`tag:server`** (required by the ACL) |
| SSH user | `ubuntu` |
| Timezone | `Asia/Kolkata` |
| Swap | 2 GiB |
| Node / uv | Node 22.23.5 / uv 0.13.8 |
| Atlas cluster | `personal.uealjs.mongodb.net`, db `portfolio` |
| `PROFILE_ID` | `sahil` |

**Code change shipped with this rebuild** (because the tailnet IP changed): `app/main.py`
CORS origin was generalized to a tailnet regex (`http://(100\.\d+\.\d+\.\d+|localhost)(:\d+)?|https://.*\.ts\.net`),
`app/services/reconciliation.py` now uses `settings.TAILSCALE_IP`, and the
`settings.TAILSCALE_IP` / frontend `lib/api.ts` fallback defaults were updated.

Post-rebuild verified: Atlas reachable + all indexes ensured, `user_profile 'sahil'` intact
(no duplicate), smoke test 5/5, both services active+enabled, crontab installed +
drift-validated, `/health` ok/ok, UI 200, CORS preflight 200.

> **Known follow-up after this rebuild:** the Phase-1 ledger (`transactions`/`holdings`) is
> the #42 GO-LIVE snapshot and is **stale** — it must be refreshed via the ICICI
> import pipeline (`import_orderbooks.py` → `reconcile_staging.py` → `promote_staging.py`,
> plus `add_manual_transactions.py` for corporate actions). See the repo README §8.

---

## 8. Generalization gaps (post-#84)

Closed by #84: the `/home/ubuntu` hardcoding in `deploy.sh`/`ops/crontab` (now `CRON_*`
env-overridable), committed systemd unit templates, and `init_db.py`'s hardcoded `_id`.

Still manual (the provisioner can only *remind*, not automate):
- **Atlas IP allowlist** (needs Atlas API keys the operator may not want to grant).
- **Tailscale join + `tag:server`** (§3) — must be done before the provisioner.
- **Data seeding** — importing the operator's own portfolio (broker CSVs + corporate actions).

## 9. What this doc deliberately does NOT do

- **No multi-tenant / shared instance.** Single-user is a hard design constraint.
- **No public ingress.** The instance stays Tailscale-only, no login.
- **No Funnel.** Never expose `:3000`/`:8000` publicly.
