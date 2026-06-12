"""F4: Daily cron health check (runs 21:00 IST).

Reads the cron registry (app.services.cron_heartbeat_service.CRON_REGISTRY),
compares against today's heartbeats in MongoDB, and fires a batched alert
on TWO independent transports (ntfy push + Resend email) if any expected
cron:
- did not run today, OR
- ran but its latest run today was a failure, OR
- ran fewer times today than min_runs_per_day.

Dual-transport rationale (commit 8 of Chat 5): the ntfy push alone was
silently dropped on at least one Saturday (likely an APNs hiccup), and
cron-health is the only cross-cron observability surface we have. Email
provides redundancy. Both transports are attempted independently; the
script only raises (marking the run as failed for tomorrow's check) when
BOTH fail.

The check itself writes a heartbeat (recursive — intentional). If everything
is healthy, no alert is sent. Silent success.

Usage (cron):
    0 21 * * *  cd /home/ubuntu/ai-stock-advisor-backend && PYTHONPATH=. \\
                /home/ubuntu/.local/bin/uv run python scripts/cron_health_check.py \\
                >> /home/ubuntu/cron-health.log 2>&1
"""

from __future__ import annotations

import logging
import sys

from app.services.cron_heartbeat_service import (
    count_today_heartbeats,
    count_today_heartbeats_from_fallback,
    cron_run,
    get_registry,
    is_expected_today,
    ist_today_window_utc,
)
from app.services.notify import email, push_public

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


def main() -> int:
    with cron_run("cron_health_check") as hb:
        today_start, tomorrow_start = ist_today_window_utc()
        anomalies: list[str] = []
        per_cron_status: list[dict] = []
        fallback_total = 0

        for spec in get_registry():
            # Skip ourselves — we're literally running right now, so a count
            # of 0 success would be a false alarm. Future runs see this one
            # via get_latest_per_cron.
            if spec.cron_name == "cron_health_check":
                continue

            expected = is_expected_today(spec)
            counts = count_today_heartbeats(
                spec.cron_name,
                ist_today_utc_start=today_start,
                ist_tomorrow_utc_start=tomorrow_start,
            )
            # Merge in any heartbeats that fell back to disk because their Mongo
            # insert failed (best-effort sink in cron_heartbeat_service._persist).
            # A run lands in at most one source, so this never double-counts.
            fallback_counts = count_today_heartbeats_from_fallback(
                spec.cron_name,
                ist_today_utc_start=today_start,
                ist_tomorrow_utc_start=tomorrow_start,
            )
            for _k in counts:
                counts[_k] += fallback_counts[_k]
            fallback_total += fallback_counts["total"]
            per_cron_status.append(
                {
                    "cron_name": spec.cron_name,
                    "expected": expected,
                    "counts": counts,
                }
            )

            if not expected:
                continue

            ran_ok = counts["success"] + counts["skipped"]
            if ran_ok < spec.min_runs_per_day:
                anomalies.append(
                    f"MISSING: {spec.cron_name} "
                    f"(expected {spec.min_runs_per_day}+ runs today, "
                    f"got {counts['success']} success + {counts['skipped']} skipped)"
                )
            if counts["failure"] > 0:
                anomalies.append(
                    f"FAILED: {spec.cron_name} ({counts['failure']} failure(s) today)"
                )

        hb.metadata["per_cron_status"] = per_cron_status
        hb.metadata["anomaly_count"] = len(anomalies)
        hb.metadata["anomalies"] = anomalies
        hb.metadata["fallback_heartbeats_merged"] = fallback_total

        print("=" * 70)
        print(" Cron health check")
        print("=" * 70)
        for entry in per_cron_status:
            print(
                f"  {entry['cron_name']:32s} expected={entry['expected']} "
                f"counts={entry['counts']}"
            )
        print()

        if not anomalies:
            print("✓ All expected crons healthy.")
            return 0

        print(f"⚠ {len(anomalies)} anomaly/anomalies detected:")
        for a in anomalies:
            print(f"  - {a}")

        anomaly_text = "\n".join(f"- {a}" for a in anomalies)
        status_text = "\n".join(
            f"  {e['cron_name']:32s} expected={e['expected']} "
            f"success={e['counts']['success']} "
            f"failure={e['counts']['failure']} "
            f"skipped={e['counts']['skipped']}"
            for e in per_cron_status
        )
        text_body = (
            f"⚠ Cron health: {len(anomalies)} issue(s)\n\n"
            f"Anomalies:\n{anomaly_text}\n\n"
            f"Per-cron status today (IST):\n{status_text}\n\n"
            f"Generated by scripts/cron_health_check.py on EC2."
        )
        anomaly_html = "".join(f"<li>{a}</li>" for a in anomalies)
        status_html = "".join(
            f"<tr>"
            f"<td>{e['cron_name']}</td>"
            f"<td>{'yes' if e['expected'] else 'no'}</td>"
            f"<td>{e['counts']['success']}</td>"
            f"<td>{e['counts']['failure']}</td>"
            f"<td>{e['counts']['skipped']}</td>"
            f"</tr>"
            for e in per_cron_status
        )
        html_body = (
            f"<h2>⚠ Cron health: {len(anomalies)} issue(s)</h2>"
            f"<h3>Anomalies</h3>"
            f"<ul>{anomaly_html}</ul>"
            f"<h3>Per-cron status today (IST)</h3>"
            f"<table border='1' cellpadding='6' cellspacing='0'>"
            f"<tr><th>Cron</th><th>Expected</th><th>Success</th>"
            f"<th>Failure</th><th>Skipped</th></tr>"
            f"{status_html}"
            f"</table>"
            f"<p style='color:#666;font-size:12px;'>"
            f"Generated by scripts/cron_health_check.py on EC2. "
            f"See docs/data_flow.md for the F4 cron-health architecture."
            f"</p>"
        )

        # Two independent transports (ntfy push + email). Both attempted on
        # every anomaly. Raise (so cron_run records this run as failed and
        # tomorrow's check surfaces it) ONLY when BOTH transports fail.
        ntfy_ok = False
        try:
            push_public(
                channel="errors",
                title=f"⚠ Cron health: {len(anomalies)} issue(s)",
                message="\n".join(anomalies),
                priority="high",
                tags=["warning", "cron"],
            )
            ntfy_ok = True
            print("✓ Alert published to ntfy (errors channel)")
        except Exception:
            log.exception("Failed to publish health alert to ntfy")

        email_result = email(
            subject=f"Portfolio Advisor — cron health: {len(anomalies)} issue(s)",
            html=html_body,
            text=text_body,
        )
        email_ok = bool(email_result.get("ok"))
        if email_ok:
            print(f"✓ Alert email sent: id={email_result.get('id')}")
        else:
            log.error("Alert email failed: %s", email_result.get("error"))

        if not ntfy_ok and not email_ok:
            raise RuntimeError(
                "Both ntfy and email alert transports failed; see logs for details."
            )

        # Return 0 even on anomalies — the alert IS the signal. Returning
        # non-zero would itself mark this run as failed and double-count noise.
        return 0


if __name__ == "__main__":
    sys.exit(main())
