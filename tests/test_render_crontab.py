"""Hermetic tests for the #84 (#61 follow-on) crontab-rendering generalization.

render_crontab() / render_cron_line() are PURE (no DB, no network). Two things
are locked down here:

1. With the CRON_* wrapper constants at their author-EC2 DEFAULTS, the rendered
   crontab reproduces the committed ops/crontab BYTE-FOR-BYTE. This is the same
   invariant deploy.sh enforces at deploy time (render_crontab --check) — if it
   ever breaks, the live deploy hard-fails. Testing it here catches drift before
   it reaches the box.

2. Overriding CRON_REPO_DIR / CRON_UV_BIN / CRON_LOG_DIR (what
   scripts/bootstrap_instance.sh does on a non-author box) changes every
   rendered line's paths accordingly, so a self-hoster gets a correct crontab
   without editing the service module.

The constants are read as module globals at call time inside render_cron_line,
so monkeypatching the module attribute is sufficient — no module reload needed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services import cron_heartbeat_service as chs

_OPS_CRONTAB = Path(__file__).resolve().parents[1] / "ops" / "crontab"


def test_defaults_reproduce_committed_ops_crontab():
    """Author-EC2 defaults -> byte-identical to the committed ops/crontab.

    Mirrors `render_crontab --check`. If this fails, deploy.sh would hard-fail.
    """
    assert chs.CRON_REPO_DIR == "/home/ubuntu/ai-stock-advisor-backend"
    assert chs.CRON_UV_BIN == "/home/ubuntu/.local/bin/uv"
    assert chs.CRON_LOG_DIR == "/home/ubuntu"
    rendered = chs.render_crontab()
    committed = _OPS_CRONTAB.read_text(encoding="utf-8")
    assert rendered == committed


def test_overrides_change_every_rendered_path(monkeypatch):
    """bootstrap_instance.sh path: overriding the wrapper constants rewrites the
    repo dir, uv binary, and log dir on every live line."""
    monkeypatch.setattr(chs, "CRON_REPO_DIR", "/opt/advisor/backend")
    monkeypatch.setattr(chs, "CRON_UV_BIN", "/usr/local/bin/uv")
    monkeypatch.setattr(chs, "CRON_LOG_DIR", "/var/log/advisor")

    rendered = chs.render_crontab()

    # No trace of the author's hardcoded paths.
    assert "/home/ubuntu" not in rendered
    # Every live line carries the overridden wrapper.
    live_lines = [
        ln
        for ln in rendered.splitlines()
        if ln and not ln.startswith("#")
    ]
    assert live_lines, "expected at least one rendered cron line"
    for ln in live_lines:
        assert "cd /opt/advisor/backend &&" in ln
        assert "/usr/local/bin/uv run python" in ln
        assert ">> /var/log/advisor/" in ln


def test_render_cron_line_uses_overrides(monkeypatch):
    """Single-line renderer honors the overrides too."""
    monkeypatch.setattr(chs, "CRON_REPO_DIR", "/srv/x")
    monkeypatch.setattr(chs, "CRON_UV_BIN", "/bin/uv")
    monkeypatch.setattr(chs, "CRON_LOG_DIR", "/logs")
    # Grab the first live spec (has cron_expr/command/log_file all set).
    spec = next(s for s in chs.CRON_REGISTRY if s.cron_expr is not None)
    line = chs.render_cron_line(spec)
    assert line.startswith(f"{spec.cron_expr} cd /srv/x && PYTHONPATH=. /bin/uv run python {spec.command}")
    assert line.endswith(f">> /logs/{spec.log_file} 2>&1")
