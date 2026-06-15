"""Datetime hygiene guard (#31 / P2-8 CI lint rule).

Enforces the project's naive-UTC storage invariant (Section 14):

  * The legacy naive ``.utcnow()`` call is BANNED -- use ``utcnow()`` from
    app.models._common instead (returns naive UTC, matching storage).
  * Every tz-aware ``now()`` call (the aware-UTC form) must carry a trailing
    ``# tz-ok: <reason>`` annotation on the same *logical* statement, proving
    it is a deliberate in-memory / comparison / response use and NOT an
    un-swept Mongo write.

Run:  uv run python -m scripts.check_datetime_hygiene
Exit: 0 = clean, 1 = violations (prints a per-statement report).

Implementation note: this guard is tokenize-based, not line-based. A single
logical statement may be wrapped across several physical lines by the
formatter (black/ruff), which moves a long trailing comment onto the closing
bracket line. Grouping by logical line (NEWLINE-delimited) lets the
annotation be matched anywhere in the statement -- wherever the formatter
parks it. String literals and comments that merely mention the patterns are
ignored because they are not code tokens, so prose never trips the guard.

Scans app/ and scripts/. The guard skips its own file, and its detection
needles are assembled by concatenation so it never matches itself.
"""

from __future__ import annotations

import sys
import tokenize
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAN_DIRS = ("app", "scripts")
SELF_NAME = Path(__file__).name

# Assembled by concatenation so these literals never appear verbatim here.
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


def _check_file(path: Path) -> list[str]:
    """Return violation strings for one file (empty if clean)."""
    violations: list[str] = []
    rel = path.relative_to(REPO_ROOT)
    try:
        with path.open("rb") as fh:
            tokens = list(tokenize.tokenize(fh.readline))
    except (tokenize.TokenError, SyntaxError, UnicodeDecodeError) as exc:
        return [f"{rel}: could not tokenize ({exc})"]

    code_parts: list[str] = []
    comment_parts: list[str] = []
    start_line: list[int | None] = [None]

    def flush() -> None:
        if start_line[0] is not None and code_parts:
            code = "".join(code_parts)
            comment = " ".join(comment_parts)
            line_no = start_line[0]
            if BANNED_UTCNOW in code:
                violations.append(
                    f"{rel}:{line_no}: banned naive utcnow() call -- use "
                    f"utcnow() from app.models._common"
                )
            if AWARE_NOW in code and TZ_OK not in comment:
                violations.append(
                    f"{rel}:{line_no}: aware-UTC now() without a "
                    f"'# tz-ok: <reason>' annotation -- swap to utcnow() if "
                    f"this is a Mongo write, else annotate why it stays aware"
                )
        code_parts.clear()
        comment_parts.clear()
        start_line[0] = None

    for tok in tokens:
        ttype = tok.type
        if ttype == tokenize.NEWLINE:
            flush()
        elif ttype == tokenize.NL:
            if not code_parts:
                comment_parts.clear()
                start_line[0] = None
        elif ttype == tokenize.COMMENT:
            comment_parts.append(tok.string)
            if start_line[0] is None:
                start_line[0] = tok.start[0]
        elif ttype in (
            tokenize.INDENT,
            tokenize.DEDENT,
            tokenize.ENCODING,
            tokenize.ENDMARKER,
        ):
            continue
        elif ttype == tokenize.STRING:
            if start_line[0] is None:
                start_line[0] = tok.start[0]
        else:
            if start_line[0] is None:
                start_line[0] = tok.start[0]
            code_parts.append(tok.string)

    flush()
    return violations


def check() -> list[str]:
    violations: list[str] = []
    for path in _iter_py_files():
        violations.extend(_check_file(path))
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
        "now() sites carry a # tz-ok annotation."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
