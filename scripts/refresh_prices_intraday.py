"""Cron entry: refresh intraday quotes for active holdings.

Runs every 15 min during NSE market hours (Mon-Fri 09:15-15:45 IST).
Inserts new docs into prices_intraday — no upsert (we want history).
"""

from __future__ import annotations

import logging
import sys

from app.db.client import Collections
from app.services.cron_heartbeat_service import cron_run
from app.services.notify import push_public
from app.services.price_service import (
    evaluate_stop_loss_alerts,
    evaluate_target_price_alerts,
    fetch_intraday_quotes,
    insert_intraday_quotes,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def main() -> int:
    with cron_run("refresh_prices_intraday") as hb:
        holdings = list(
            Collections.holdings().find(
                {"deleted_at": None},
                {"isin": 1, "symbol": 1, "exchange": 1},
            )
        )
        if not holdings:
            log.info("No active holdings — nothing to refresh")
            hb.mark_skipped("no_active_holdings")
            return 0

        hb.metadata["holdings"] = len(holdings)
        log.info("Intraday refresh for %d active holdings", len(holdings))

        rows = fetch_intraday_quotes(holdings)
        if not rows:
            log.info("No intraday data returned (market closed?)")
            hb.mark_skipped("market_closed_or_no_data")
            return 0

        # We only reach here when yfinance returned intraday rows, i.e. the
        # market is open — so an insert failure here is by construction a
        # market-hours failure. Push an immediate alert (master_todo #35):
        # this cron runs every 15 min but the F4 health check only sweeps at
        # 21:00 IST, so without this a mid-session insert outage stays
        # invisible for hours.
        #
        # #73 U2-e: a single bad row must NOT suppress the stop-loss / target
        # evaluators. insert_intraday_quotes uses insert_many(ordered=False), so
        # the VALID rows still land even when one row is bad. Previously the cron
        # re-raised on any insert error, skipping BOTH evaluators for the tick —
        # a genuine breach could go un-alerted because of one malformed row. We
        # now capture the insert failure, alert on it, remember it, and STILL run
        # the evaluators on the fetched rows; the heartbeat is marked failed at
        # the end so F4 still sees the problem.
        insert_failed = False
        insert_error = ""
        try:
            inserted = insert_intraday_quotes(rows)
        except Exception as exc:
            insert_failed = True
            insert_error = str(exc)
            inserted = 0
            log.exception("insert_intraday_quotes failed during market hours")
            # push_public raises on transport failure — guard it so a failed
            # alert can't mask the original insert error (mirrors #24/TD39).
            try:
                push_public(
                    channel="errors",
                    title="Intraday price insert failed",
                    message=(
                        "refresh_prices_intraday: insert_intraday_quotes raised "
                        f"during market hours ({len(rows)} rows pending): {exc}"
                    ),
                    priority="high",
                    tags=["warning"],
                )
            except Exception:
                log.exception("Failed to send intraday-insert failure ntfy")

        hb.metadata["rows_fetched"] = len(rows)
        hb.metadata["rows_inserted"] = inserted
        if insert_failed:
            hb.metadata["insert_failed"] = True

        # master_todo #41 (TD6): evaluate stop-loss rising-edge alerts on the
        # SAME rows we just fetched -- no parallel price-fetch loop. Guarded so
        # an alerting failure can never mask the insert outcome. Runs even after
        # a partial insert failure (#73 U2-e) so a real breach still alerts.
        try:
            alerts_fired = evaluate_stop_loss_alerts(rows)
            hb.metadata["stop_loss_alerts_fired"] = alerts_fired
            if alerts_fired:
                log.info("Stop-loss alerts fired: %d", alerts_fired)
        except Exception:
            log.exception("evaluate_stop_loss_alerts failed after intraday insert")
            hb.metadata["stop_loss_alerts_error"] = True

        # master_todo #56: evaluate target-price rising-edge alerts on the SAME
        # rows (mirror of #41; no parallel price-fetch loop). Guarded so an
        # alerting failure can never mask the insert outcome.
        try:
            target_alerts_fired = evaluate_target_price_alerts(rows)
            hb.metadata["target_alerts_fired"] = target_alerts_fired
            if target_alerts_fired:
                log.info("Target-price alerts fired: %d", target_alerts_fired)
        except Exception:
            log.exception("evaluate_target_price_alerts failed after intraday insert")
            hb.metadata["target_alerts_error"] = True

        # #73 U2-e: surface the insert failure to F4 AFTER the evaluators ran, so
        # cron_run records this tick as failed (mid-session outage stays visible)
        # without having suppressed the alert evaluation.
        if insert_failed:
            raise RuntimeError(
                f"insert_intraday_quotes failed during market hours: {insert_error}"
            )

        log.info("Intraday refresh complete: %d inserted", inserted)
        return 0


if __name__ == "__main__":
    sys.exit(main())
