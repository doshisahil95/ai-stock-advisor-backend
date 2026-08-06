"""Render (or verify) the committed `ops/crontab` from CRON_REGISTRY (TD21/#46).

The cron SCHEDULE is now version-controlled: `app/services/cron_heartbeat_service.py`
::CRON_REGISTRY is the single source of truth, this script renders it into a
committed `ops/crontab`, and `deploy.sh` installs that file + drift-validates
`crontab -l` against it. This makes TD14-class drift (a crontab line carrying
flags the script's argparse rejects, or a schedule the registry doesn't know
about) structurally impossible — the crontab can only ever be what the registry
renders.

The actual rendering lives in cron_heartbeat_service.render_crontab() so the
health-check registry and the rendered schedule can never disagree. This script
is a thin CLI over it.

Usage (run as a MODULE from the repo root — a by-file-path invocation raises
ModuleNotFoundError: app, per the Section-4 convention):

    # Regenerate the committed artifact after editing CRON_REGISTRY:
    PYTHONPATH=. uv run python -m scripts.render_crontab > ops/crontab

    # Verify the committed ops/crontab matches the registry (exit 1 on drift):
    PYTHONPATH=. uv run python -m scripts.render_crontab --check

This script is PURE — no DB, no network — so it is safe to run anywhere,
including a pre-commit hook or CI.
"""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

from app.services.cron_heartbeat_service import render_crontab

# The committed artifact, relative to the repo root (this file lives in scripts/).
_OPS_CRONTAB_PATH = Path(__file__).resolve().parents[1] / "ops" / "crontab"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render or verify the committed ops/crontab from CRON_REGISTRY (TD21/#46).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Do not print the crontab; instead compare the freshly-rendered "
            "crontab against the committed ops/crontab on disk. Exit 0 if they "
            "match, 1 (with a unified diff on stderr) if they drift."
        ),
    )
    args = parser.parse_args()

    rendered = render_crontab()

    if not args.check:
        # Default mode: emit to stdout so `> ops/crontab` regenerates the file.
        # Use sys.stdout.write (not print) so we don't append an extra newline
        # on top of render_crontab()'s single trailing newline.
        sys.stdout.write(rendered)
        return 0

    # --check mode: the committed file must exist and match byte-for-byte.
    if not _OPS_CRONTAB_PATH.exists():
        sys.stderr.write(
            f"ERROR: {_OPS_CRONTAB_PATH} does not exist. "
            f"Run: PYTHONPATH=. uv run python -m scripts.render_crontab > ops/crontab\n"
        )
        return 1

    committed = _OPS_CRONTAB_PATH.read_text(encoding="utf-8")
    if committed == rendered:
        print("OK: ops/crontab is in sync with CRON_REGISTRY.")
        return 0

    sys.stderr.write(
        "ERROR: ops/crontab has DRIFTED from CRON_REGISTRY. "
        "Regenerate with: PYTHONPATH=. uv run python -m scripts.render_crontab > ops/crontab\n\n"
    )
    diff = difflib.unified_diff(
        committed.splitlines(keepends=True),
        rendered.splitlines(keepends=True),
        fromfile="ops/crontab (committed)",
        tofile="CRON_REGISTRY (rendered)",
    )
    sys.stderr.writelines(diff)
    return 1


if __name__ == "__main__":
    sys.exit(main())
