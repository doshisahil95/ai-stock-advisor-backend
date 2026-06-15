"""Datetime hygiene guard (#31 / P2-8 CI lint rule).

Enforces the project's naive-UTC storage invariant (Section 14):

  * The legacy naive ``.utcnow()`` call is BANNED outright -- use ``utcnow()``
    from app.models._common instead (returns naive UTC, matching storage).
  * Every tz-aware ``now()`` call (the aware-UTC form) must carry a trailing
    ``# tz-ok: <reason>`` annotation, proving it is a deliberate in-memory /
    comparison / response use and NOT an un-swept Mongo write.

Run:  uv run python -m scripts.check_datetime_hygiene
Exit: 0 = clean, 1 = violations (prints a per-line report).

Scans app/ and scripts/. Comment-only lines (stripped line starts with '#')
are ignored, so prose/comments that mention these patterns never trip it.

The detection needles are assembled by concatenation so this guard file does
not match itself; the guard also skips its own filename when walking.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAN_DIRS = ("app", "scripts")
SELF_NAME = Path(__file__).name

# Assembled by concatenation so the literals never appear verbatim in this file.
BANNED_UTCNOW = "datetime." + "utcnow("
AWARE_NOW = "datetime." + "now(timezone.utc)"
TZ_OK = "# tz-ok:"


def _iter_py_files():
    for d in SCAN_DIRS:
        base = REPO_ROOT / d
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            if path.name == SELF_NAME:
                continue
            yield path


def check() -> list[str]:
    violations: list[str] = []
    for path in _iter_py_files():
        rel = path.relative_to(REPO_ROOT)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except Exception as exc:  # pragma: no cover
            violations.append(f"{rel}: could not read ({exc})")
            continue
        for n, line in enumerate(lines, start=1):
            if line.strip().startswith("#"):
                continue
            if BANNED_UTCNOW in line:
                violations.append(
                    f"{rel}:{n}: banned naive utcnow() call -- use "
                    f"utcnow() from app.models._common"
                )
            if AWARE_NOW in line and TZ_OK not in line:
                violations.append(
                    f"{rel}:{n}: aware-UTC now() without a '# tz-ok: <reason>' "
                    f"annotation -- swap to utcnow() if this is a Mongo write, "
                    f"else annotate why it must stay aware"
                )
    return violations


def main() -> int:
    violations = check()
    if violations:
        print("datetime hygiene check FAILED:\n")
        for v in violations:
            print(f"  {v}")
        print(f"\n{len(violations)} violation(s).")
        return 1
    print(
        "datetime hygiene check PASSED: no banned utcnow() and all aware-UTC "
        "now() sites are annotated # tz-ok."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
