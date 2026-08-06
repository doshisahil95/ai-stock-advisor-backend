#!/bin/bash
set -e
cd ~/ai-stock-advisor-backend
echo "→ Pulling latest..."
git pull
echo "→ Syncing deps..."
uv sync
echo "→ Re-applying indexes..."
PYTHONPATH=. uv run python scripts/init_db.py | tail -20

# ── TD21/#46: version-controlled crontab ────────────────────────────
# The cron SCHEDULE is rendered from app/services/cron_heartbeat_service.py
# ::CRON_REGISTRY into the committed ops/crontab. We (1) verify that committed
# file still matches the registry, (2) install it as THE crontab, and (3)
# drift-validate the live crontab against it. Any mismatch hard-fails the
# deploy (set -e) BEFORE the service restart — a bad schedule can never ship
# silently (this is what makes TD14-class drift structurally impossible).
echo "→ Verifying ops/crontab matches CRON_REGISTRY..."
PYTHONPATH=. uv run python -m scripts.render_crontab --check

echo "→ Installing crontab from ops/crontab..."
crontab ops/crontab

echo "→ Drift-validating live crontab vs ops/crontab..."
if diff <(crontab -l) ops/crontab; then
  echo "  crontab in sync ✓"
else
  echo "❌ Live crontab differs from ops/crontab after install — aborting." >&2
  exit 1
fi
# ────────────────────────────────────────────────────────────────────

echo "→ Restarting service..."
sudo systemctl restart portfolio-advisor.service
sleep 2
sudo systemctl status portfolio-advisor.service --no-pager | head -10
echo "→ Healthcheck..."
curl -s http://100.112.20.41:8000/health
echo ""
echo "✅ Deploy complete"
