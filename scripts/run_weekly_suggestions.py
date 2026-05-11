"""Run the weekly suggestions cron.

Usage:
  # Production cron entry (Sunday 06:00 IST)
  PYTHONPATH=. uv run python scripts/run_weekly_suggestions.py

  # Dry run — compute but don't persist
  PYTHONPATH=. uv run python scripts/run_weekly_suggestions.py --dry-run

  # Limit to first N stocks for fast testing
  PYTHONPATH=. uv run python scripts/run_weekly_suggestions.py --dry-run --limit 10

  # Override top-K
  PYTHONPATH=. uv run python scripts/run_weekly_suggestions.py --dry-run --top-k 5
"""

from __future__ import annotations

import argparse
import logging
import sys

from app.services.suggestion_engine import run_suggestions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run weekly suggestions engine")
    parser.add_argument("--dry-run", action="store_true", help="Don't persist run")
    parser.add_argument(
        "--limit", type=int, default=None, help="Limit universe to N stocks"
    )
    parser.add_argument("--top-k", type=int, default=None, help="Override top-K")
    parser.add_argument(
        "--run-type",
        type=str,
        default="manual",
        choices=["scheduled", "manual"],
        help="Mark this run's origin (default 'manual')",
    )
    args = parser.parse_args()

    try:
        run = run_suggestions(
            run_type=args.run_type,
            limit=args.limit,
            dry_run=args.dry_run,
            top_k_override=args.top_k,
        )
    except Exception as exc:
        print(f"❌ Run failed: {exc}", file=sys.stderr)
        return 1

    print()
    print("=" * 70)
    print(f"  Run status: {run.status}")
    print(f"  Universe:   {run.universe_size}")
    print(
        f"  Excluded:   held={run.excluded_held}, rejected={run.excluded_rejected}, stale={run.excluded_stale_data}"
    )
    print(f"  Considered: {run.candidates_considered}")
    print(f"  Post-gates: {run.candidates_post_gates}")
    print(f"  Top-{run.top_k} surfaced")
    print("=" * 70)
    print()
    print("Top candidates:")
    for c in run.top_candidates:
        print(
            f"  #{c.rank:>2}  {c.symbol:<12} composite={c.composite_score:>5.1f}  "
            f"conf={c.confidence_score:>3.0f}  Q={c.quality_score:>5.1f}  "
            f"V={c.valuation_score:>5.1f}  M={c.momentum_score:>5.1f}"
        )
    print()

    return 0 if run.status in ("success", "partial") else 1


if __name__ == "__main__":
    sys.exit(main())
