"""Cron wrapper: run weekly suggestions (buy and/or sell), instrumented with heartbeat.

F2 (chunk 6):
- --direction=buy|sell|both (default 'buy').
- 'both' runs buy then sell sequentially under ONE heartbeat (cron_heartbeats
  logs one row, not two) and emits ONE combined digest via
  digest_delivery.send_combined_digest. This is the production cron path.
- 'buy' or 'sell' alone behave as before with their own heartbeat + digest.

Heartbeat job names:
  buy      -> 'weekly_suggestions'
  sell     -> 'weekly_suggestions_sell'
  both     -> 'weekly_suggestions' (umbrella row records both)
"""

from __future__ import annotations

import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("run_weekly_suggestions")


def _run_single(
    direction: str, notify: bool, skip_dossiers: bool = False
) -> tuple[int, dict]:
    """Run one direction. Returns (exit_code, metadata dict for heartbeat)."""
    from app.services.suggestion_engine import run_suggestions

    run = run_suggestions(
        run_type="scheduled",
        notify=notify,
        direction=direction,
        skip_dossiers=skip_dossiers,
    )
    meta = {
        f"{direction}_status": run.status,
        f"{direction}_top": len(run.top_candidates),
        f"{direction}_eligible": run.candidates_post_gates,
        f"{direction}_universe": run.universe_size,
    }
    exit_code = 0 if run.status in ("success", "partial") else 1
    return exit_code, meta, run


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Weekly suggestions cron entrypoint with heartbeat instrumentation",
    )
    parser.add_argument(
        "--direction",
        choices=("buy", "sell", "both"),
        default="buy",
        help=(
            "Which side to run. 'both' runs buy then sell back-to-back under "
            "ONE heartbeat and emits ONE combined digest."
        ),
    )
    parser.add_argument(
        "--no-notify",
        action="store_true",
        help=(
            "Skip outcome creation + email/ntfy digest. Use for manual reruns. "
            "Scheduled cron uses default (notify=True)."
        ),
    )
    parser.add_argument(
        "--skip-dossiers",
        action="store_true",
        help=(
            "Skip Claude dossier generation. Smoke-test only -- the persisted "
            "run will have no narratives. Do NOT use for scheduled production."
        ),
    )
    args = parser.parse_args()
    notify = not args.no_notify
    skip_dossiers = args.skip_dossiers
    # Late imports: keep top-of-file fast in case heartbeat fails to import.
    from app.services.cron_heartbeat_service import cron_run

    if args.direction == "buy":
        job_name = "weekly_suggestions"

        def _do_buy():
            exit_code, meta, _run = _run_single(
                "buy", notify=notify, skip_dossiers=skip_dossiers
            )
            if exit_code != 0:
                raise RuntimeError(f"buy pipeline status={meta.get('buy_status')}")
            return meta

        with cron_run(job_name) as ctx:
            ctx.meta = _do_buy()
        return 0

    if args.direction == "sell":
        job_name = "weekly_suggestions_sell"

        def _do_sell():
            exit_code, meta, _run = _run_single(
                "sell", notify=notify, skip_dossiers=skip_dossiers
            )
            if exit_code != 0:
                raise RuntimeError(f"sell pipeline status={meta.get('sell_status')}")
            return meta

        with cron_run(job_name) as ctx:
            ctx.meta = _do_sell()
        return 0

    # direction == "both": one heartbeat, sequential runs, combined digest.
    # IMPORTANT: we call run_suggestions with notify=False per side so we don't
    # send two separate digests; then we emit ONE combined digest at the end.
    job_name = "weekly_suggestions"  # umbrella row, same as buy alone

    def _do_both():
        from app.services.suggestion_engine import run_suggestions
        from app.services.digest_delivery import send_combined_digest
        from app.services.outcome_tracker import create_outcomes_for_run

        log.info("=== Running BOTH directions (F2 combined cron path) ===")

        # 1. Buy run -- notify=False, we'll combine deliveries below.
        buy_run = run_suggestions(
            run_type="scheduled",
            notify=False,
            direction="buy",
            skip_dossiers=skip_dossiers,
        )
        log.info(
            "  buy:  status=%s top=%d", buy_run.status, len(buy_run.top_candidates)
        )

        # 2. Sell run -- notify=False, same reason.
        sell_run = run_suggestions(
            run_type="scheduled",
            notify=False,
            direction="sell",
            skip_dossiers=skip_dossiers,
        )
        log.info(
            "  sell: status=%s top=%d", sell_run.status, len(sell_run.top_candidates)
        )

        # 3. Outcomes for BOTH directions, only if notify is on (production).
        if notify:
            # P3-5 (#21): run_suggestions now carries the persisted _id on the
            # returned SuggestionRun (set in _persist_run), so attach outcomes
            # via buy_run.id / sell_run.id directly instead of re-deriving the
            # most-recent run per direction with find_one.
            if buy_run.id and buy_run.top_candidates:
                try:
                    create_outcomes_for_run(
                        buy_run.id,
                        buy_run.run_date,
                        buy_run.top_candidates,
                        direction="buy",
                    )
                except Exception:
                    log.exception("create_outcomes_for_run (buy) failed")

            if sell_run.id and sell_run.top_candidates:
                try:
                    create_outcomes_for_run(
                        sell_run.id,
                        sell_run.run_date,
                        sell_run.top_candidates,
                        direction="sell",
                    )
                except Exception:
                    log.exception("create_outcomes_for_run (sell) failed")

            # 4. Single combined digest.
            try:
                delivery = send_combined_digest(buy_run, sell_run)
                log.info("Combined digest delivery: %s", delivery)
            except Exception:
                log.exception("send_combined_digest failed")

        meta = {
            "buy_status": buy_run.status,
            "buy_top": len(buy_run.top_candidates),
            "sell_status": sell_run.status,
            "sell_top": len(sell_run.top_candidates),
        }

        # Heartbeat status: fail only if BOTH sides failed.
        buy_ok = buy_run.status in ("success", "partial")
        sell_ok = sell_run.status in ("success", "partial")
        if not (buy_ok or sell_ok):
            raise RuntimeError(
                f"both pipelines failed: buy={buy_run.status} sell={sell_run.status}"
            )

        return meta

    with cron_run(job_name) as ctx:
        ctx.meta = _do_both()
    return 0


if __name__ == "__main__":
    sys.exit(main())
