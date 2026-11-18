#!/bin/bash
set -e

# Backend UPDATE / deploy script (run on the EC2 box).
#   pull latest → uv sync → re-apply indexes → verify+install crontab →
#   restart portfolio-advisor → healthcheck.
#
# This is the UPDATE path, NOT first-time provisioning — that's
# scripts/bootstrap_instance.sh. All paths are env-overridable; the defaults
# match the author's EC2 box (user `ubuntu`, repo in $HOME).
DEPLOY_REPO_DIR="${DEPLOY_REPO_DIR:-$HOME/ai-stock-advisor-backend}"
UV_BIN="${UV_BIN:-$HOME/.local/bin/uv}"
HEALTHCHECK_URL="${HEALTHCHECK_URL:-http://localhost:8000/health}"
SERVICE="${SERVICE:-portfolio-advisor.service}"

cd "$DEPLOY_REPO_DIR"
echo "→ Pulling latest..."
git pull --ff-only

echo "→ Syncing deps..."
"$UV_BIN" sync

echo "→ Re-applying indexes..."
PYTHONPATH=. "$UV_BIN" run python scripts/init_db.py | tail -5

# ── TD21/#46: version-controlled crontab (verify → install → drift-validate) ──
# The schedule is rendered from cron_heartbeat_service::CRON_REGISTRY into the
# committed ops/crontab. Any mismatch hard-fails the deploy (set -e) BEFORE the
# service restart, so a bad schedule can never ship silently.
echo "→ Verifying ops/crontab matches CRON_REGISTRY..."
PYTHONPATH=. "$UV_BIN" run python -m scripts.render_crontab --check

echo "→ Installing crontab from ops/crontab..."
crontab ops/crontab

echo "→ Drift-validating live crontab vs ops/crontab..."
diff <(crontab -l) ops/crontab && echo "  crontab in sync ✓"

echo "→ Restarting $SERVICE..."
sudo systemctl restart "$SERVICE"
sleep 3
sudo systemctl --no-pager status "$SERVICE" | head -6

echo "→ Healthcheck..."
curl -sS "$HEALTHCHECK_URL"; echo
echo "✅ Backend deploy complete"
