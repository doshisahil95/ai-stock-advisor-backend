#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# scripts/bootstrap_instance.sh — one-time first-instance provisioner.
# #84 (#61 follow-on). Implements the outline in docs/self_hosting.md.
#
# This is DISTINCT from the repo-root deploy.sh (which is the UPDATE-only
# script: pull → sync → render/install crontab → restart). This script
# provisions a FRESH Linux box: writes secrets, initializes the DB, runs a
# smoke test, installs parameterized systemd units for backend + frontend,
# installs the version-controlled crontab, and health-gates before declaring
# success.
#
# Design rules (docs/self_hosting.md):
#   - Idempotent + safe: refuses to clobber a live install (secrets present
#     AND backend service already running).
#   - Fail-fast: `set -euo pipefail`; any smoke/health failure aborts rather
#     than half-provisioning.
#   - No hardcoded identity: everything deploy.sh / ops/crontab hardcode
#     (/home/ubuntu, the Tailscale IP, the `ubuntu` user, the uv path) is a
#     parameter with a sensible default.
#   - Reuses existing scripts: init_db.py, smoke_test.py, render_crontab.py are
#     the building blocks — this orchestrates them, it does not reimplement.
#
# Usage:
#   scripts/bootstrap_instance.sh              # interactive, uses defaults
#   REPO_DIR_BACKEND=... RUN_USER=... scripts/bootstrap_instance.sh
#   scripts/bootstrap_instance.sh --dry-run    # print the plan, change nothing
#   scripts/bootstrap_instance.sh --help
#
# Secrets are prompted for (or read from env) and written to $SECRETS_PATH.
# Run from the backend repo root (it locates its own siblings via the params).
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Parameters (env or defaults; NO hardcoded /home/ubuntu, IP, or user) ──
REPO_DIR_BACKEND="${REPO_DIR_BACKEND:-$HOME/ai-stock-advisor-backend}"
REPO_DIR_FRONTEND="${REPO_DIR_FRONTEND:-$HOME/ai-stock-advisor-frontend}"
SECRETS_PATH="${SECRETS_PATH:-/etc/portfolio-advisor/secrets.env}"
RUN_USER="${RUN_USER:-$(whoami)}"
TAILSCALE_IP="${TAILSCALE_IP:-$(tailscale ip -4 2>/dev/null | head -1 || true)}"
API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-8000}"
UI_PORT="${UI_PORT:-3000}"
UV_BIN="${UV_BIN:-$HOME/.local/bin/uv}"
PROFILE_ID="${PROFILE_ID:-$RUN_USER}"

# systemd unit names (match the live EC2 units in Project_State §4).
BACKEND_UNIT="portfolio-advisor.service"
FRONTEND_UNIT="portfolio-advisor-ui.service"

# Derived.
API_BASE_URL="http://${TAILSCALE_IP:-127.0.0.1}:${API_PORT}"
HEALTH_URL="http://localhost:${API_PORT}/health"
UI_URL="http://localhost:${UI_PORT}"
TEMPLATE_DIR="$REPO_DIR_BACKEND/ops/systemd"

DRY_RUN=0

# ── Secret keys with NO default in settings.py — must be present ──
REQUIRED_SECRETS=(
    ANTHROPIC_API_KEY
    TAVILY_API_KEY
    MONGODB_URI
    NTFY_PUBLIC_TOPIC_PRICE
    NTFY_PUBLIC_TOPIC_NEWS
    NTFY_PUBLIC_TOPIC_ERRORS
    NTFY_PUBLIC_TOPIC_DIGESTS
    RESEND_API_KEY
    RESEND_FROM
    RESEND_TO
)

log()  { printf '→ %s\n' "$*"; }
ok()   { printf '\xe2\x9c\x93 %s\n' "$*"; }
die()  { printf '\xe2\x9d\x8c %s\n' "$*" >&2; exit 1; }
run()  { if [[ "$DRY_RUN" == "1" ]]; then printf '   [dry-run] %s\n' "$*"; else eval "$*"; fi; }

usage() {
    sed -n '2,34p' "$0"
    exit 0
}

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        -h|--help) usage ;;
        *) die "unknown argument: $arg (see --help)" ;;
    esac
done

echo "═════════════════════════════════════════════════════════════════"
echo "  Personal AI Stock Advisor — first-instance provisioner (#84)"
echo "═════════════════════════════════════════════════════════════════"
echo "  RUN_USER          = $RUN_USER"
echo "  REPO_DIR_BACKEND  = $REPO_DIR_BACKEND"
echo "  REPO_DIR_FRONTEND = $REPO_DIR_FRONTEND"
echo "  SECRETS_PATH      = $SECRETS_PATH"
echo "  TAILSCALE_IP      = ${TAILSCALE_IP:-<unresolved>}"
echo "  API_HOST:PORT     = $API_HOST:$API_PORT"
echo "  UI_PORT           = $UI_PORT"
echo "  UV_BIN            = $UV_BIN"
echo "  PROFILE_ID        = $PROFILE_ID"
echo "  DRY_RUN           = $DRY_RUN"
echo "─────────────────────────────────────────────────────────────────"

# ── Step 1: Preflight + idempotency guard ─────────────────────────────
log "Step 1/7 — preflight"
command -v git  >/dev/null 2>&1 || die "git not found (see docs/self_hosting.md step 1)"
command -v node >/dev/null 2>&1 || die "node not found (Node 22 required for the frontend)"
[[ -x "$UV_BIN" ]] || command -v uv >/dev/null 2>&1 || die "uv not found at $UV_BIN and not on PATH"
[[ -d "$REPO_DIR_BACKEND" ]]  || die "backend repo not found at $REPO_DIR_BACKEND"
[[ -d "$REPO_DIR_FRONTEND" ]] || die "frontend repo not found at $REPO_DIR_FRONTEND"
[[ -d "$TEMPLATE_DIR" ]]      || die "systemd templates not found at $TEMPLATE_DIR"

# Idempotency: refuse if this looks like a live install (don't nuke it).
service_active() { systemctl is-active --quiet "$1" 2>/dev/null; }
if [[ -f "$SECRETS_PATH" ]] && service_active "$BACKEND_UNIT"; then
    die "$SECRETS_PATH exists AND $BACKEND_UNIT is active — this box is already \
provisioned. Use deploy.sh for updates. Refusing to clobber a live install."
fi
ok "preflight passed"

# ── Step 2: Secrets ───────────────────────────────────────────────────
log "Step 2/7 — secrets at $SECRETS_PATH"
if [[ -f "$SECRETS_PATH" ]]; then
    ok "secrets file already exists — leaving it untouched (validating below)"
else
    tmp_secrets="$(mktemp)"
    trap 'rm -f "$tmp_secrets"' EXIT
    {
        echo "# Written by scripts/bootstrap_instance.sh on $(date -u +%FT%TZ)"
        for key in "${REQUIRED_SECRETS[@]}"; do
            val="${!key:-}"
            if [[ -z "$val" ]]; then
                if [[ "$DRY_RUN" == "1" ]]; then
                    val="<PROMPT:$key>"
                else
                    read -r -p "  $key = " val < /dev/tty
                    [[ -n "$val" ]] || die "$key is required and cannot be empty"
                fi
            fi
            echo "$key=$val"
        done
    } > "$tmp_secrets"
    run "sudo mkdir -p \"\$(dirname \"$SECRETS_PATH\")\""
    run "sudo cp \"$tmp_secrets\" \"$SECRETS_PATH\""
    run "sudo chmod 0640 \"$SECRETS_PATH\""
    run "sudo chown root:\"$RUN_USER\" \"$SECRETS_PATH\""
    ok "secrets written (0640 root:$RUN_USER)"
fi

# Validate no required key is empty in the on-disk file (skip in dry-run).
if [[ "$DRY_RUN" != "1" ]]; then
    for key in "${REQUIRED_SECRETS[@]}"; do
        line="$(sudo grep -E "^${key}=" "$SECRETS_PATH" || true)"
        [[ -n "$line" && "$line" != "${key}=" ]] || die "required secret $key is missing/empty in $SECRETS_PATH"
    done
    ok "all ${#REQUIRED_SECRETS[@]} required secrets present"
fi

# ── Step 3: Backend deps + DB init + smoke (ABORT on failure) ─────────
log "Step 3/7 — backend deps + init_db + smoke_test"
run "cd \"$REPO_DIR_BACKEND\" && \"$UV_BIN\" sync"
run "cd \"$REPO_DIR_BACKEND\" && PROFILE_ID=\"$PROFILE_ID\" PYTHONPATH=. \"$UV_BIN\" run python scripts/init_db.py"
run "cd \"$REPO_DIR_BACKEND\" && PYTHONPATH=. \"$UV_BIN\" run python scripts/smoke_test.py"
ok "backend init + smoke passed"

# ── Step 4: Backend systemd unit from template ────────────────────────
log "Step 4/7 — install $BACKEND_UNIT"
render_backend_unit() {
    sed \
        -e "s|@RUN_USER@|$RUN_USER|g" \
        -e "s|@REPO_DIR@|$REPO_DIR_BACKEND|g" \
        -e "s|@SECRETS_PATH@|$SECRETS_PATH|g" \
        -e "s|@UV_BIN@|$UV_BIN|g" \
        -e "s|@API_HOST@|$API_HOST|g" \
        -e "s|@API_PORT@|$API_PORT|g" \
        "$TEMPLATE_DIR/portfolio-advisor.service.template"
}
if [[ "$DRY_RUN" == "1" ]]; then
    echo "   [dry-run] rendered $BACKEND_UNIT:"; render_backend_unit | sed 's/^/     /'
else
    render_backend_unit | sudo tee "/etc/systemd/system/$BACKEND_UNIT" >/dev/null
    sudo systemctl daemon-reload
    sudo systemctl enable --now "$BACKEND_UNIT"
    ok "$BACKEND_UNIT installed + started"
fi

# ── Step 5: Frontend systemd unit from template ───────────────────────
log "Step 5/7 — frontend build + install $FRONTEND_UNIT"
run "cd \"$REPO_DIR_FRONTEND\" && npm install --legacy-peer-deps"
run "cd \"$REPO_DIR_FRONTEND\" && NEXT_PUBLIC_API_BASE_URL=\"$API_BASE_URL\" npm run build"
render_frontend_unit() {
    sed \
        -e "s|@RUN_USER@|$RUN_USER|g" \
        -e "s|@REPO_DIR_FRONTEND@|$REPO_DIR_FRONTEND|g" \
        -e "s|@UI_PORT@|$UI_PORT|g" \
        -e "s|@API_BASE_URL@|$API_BASE_URL|g" \
        "$TEMPLATE_DIR/portfolio-advisor-ui.service.template"
}
if [[ "$DRY_RUN" == "1" ]]; then
    echo "   [dry-run] rendered $FRONTEND_UNIT:"; render_frontend_unit | sed 's/^/     /'
else
    render_frontend_unit | sudo tee "/etc/systemd/system/$FRONTEND_UNIT" >/dev/null
    sudo systemctl daemon-reload
    sudo systemctl enable --now "$FRONTEND_UNIT"
    ok "$FRONTEND_UNIT installed + started"
fi

# ── Step 6: Crontab (render with THIS box's paths, install, drift-validate) ─
log "Step 6/7 — crontab"
# Export the CRON_* overrides so cron_heartbeat_service renders lines for THIS
# user/path, then regenerate ops/crontab and install it. On the author's box
# these equal the committed defaults, so this is a no-op regeneration.
export CRON_REPO_DIR="$REPO_DIR_BACKEND"
export CRON_UV_BIN="$UV_BIN"
export CRON_LOG_DIR="$HOME"
run "cd \"$REPO_DIR_BACKEND\" && PYTHONPATH=. \"$UV_BIN\" run python -m scripts.render_crontab > ops/crontab"
run "cd \"$REPO_DIR_BACKEND\" && crontab ops/crontab"
if [[ "$DRY_RUN" != "1" ]]; then
    if diff <(crontab -l) "$REPO_DIR_BACKEND/ops/crontab" >/dev/null; then
        ok "crontab installed + drift-validated"
    else
        die "live crontab differs from rendered ops/crontab after install"
    fi
fi

# ── Step 7: Health gate ───────────────────────────────────────────────
log "Step 7/7 — health gate"
if [[ "$DRY_RUN" == "1" ]]; then
    echo "   [dry-run] would curl $HEALTH_URL (expect ok/ok) and $UI_URL (expect 200)"
else
    sleep 3
    health="$(curl -sS "$HEALTH_URL" || true)"
    echo "  backend: $health"
    echo "$health" | grep -q '"status":"ok"' || die "backend health check failed: $health"
    code="$(curl -sS -o /dev/null -w '%{http_code}' "$UI_URL" || true)"
    echo "  ui -> $code"
    [[ "$code" == "200" ]] || die "frontend did not return 200 (got $code)"
    ok "health gate passed"
fi

echo "─────────────────────────────────────────────────────────────────"
ok "Bootstrap complete."
echo "  Next steps (manual — the provisioner can only remind, not automate):"
echo "   • Allowlist this box's public IP in the MongoDB Atlas cluster."
echo "   • Subscribe your iPhone ntfy app to the NTFY_PUBLIC_TOPIC_* topics."
echo "   • Seed YOUR portfolio data: import_orderbooks.py → reconcile_staging.py"
echo "     → promote_staging.py; seed_nifty100.py for the suggestion universe."
echo "   • Reach the UI at http://${TAILSCALE_IP:-<tailscale-ip>}:$UI_PORT from your tailnet."
echo "   • Add extra email recipients later via RESEND_CC (docs/onboarding_and_access.md)."
