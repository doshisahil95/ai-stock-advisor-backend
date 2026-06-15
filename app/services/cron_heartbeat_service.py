"""Cron heartbeats — F4 health monitoring.

Every cron run wraps its body in `cron_run("<name>") as hb:`.
On context exit (clean or exceptional) a single doc lands in `cron_heartbeats`
capturing started_at, finished_at, status, error, and any metadata the cron set.

A separate daily check job reads these and fires ntfy on missed runs or
failures (see scripts/cron_health_check.py).

This is append-only. Used for:
- "did the Sunday digest actually run?"
- "which intraday slot failed at 11:00?"
- Forensics for missed alerts
"""

from __future__ import annotations

import json
import zoneinfo
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator, Literal

from app.db.client import Collections
from app.models._common import _convert_decimals_to_decimal128, utcnow

# ────────────────────────────────────────────────────────────────────
# Status values written to the `status` field on heartbeat docs.
HeartbeatStatus = Literal["success", "failure", "skipped"]

# IST timezone — used for "expected today?" calculations.
IST = zoneinfo.ZoneInfo("Asia/Kolkata")

# Weekday helpers (Python convention: Mon=0..Sun=6).
WEEKDAYS_MON_FRI = {0, 1, 2, 3, 4}
WEEKDAYS_ALL = {0, 1, 2, 3, 4, 5, 6}
SUNDAY = {6}

# Fallback heartbeat log — last-resort sink used by `_persist` when the Mongo
# heartbeat insert fails. Best-effort and append-only (one JSON object per
# line). The daily health check reads this in ADDITION to Mongo so a heartbeat
# lost to a transient Mongo outage does not become a false MISSING. The path
# matches the /home/ubuntu/cron-*.log logrotate glob (Section 4), so no new
# rotation config is needed.
_FALLBACK_LOG_PATH = "/home/ubuntu/cron-heartbeat-fallback.log"


# ────────────────────────────────────────────────────────────────────
# Registry
@dataclass
class CronSpec:
    """Static metadata about a registered cron entry.

    Drives the health check ("was this expected today? did it run?").
    Keep in sync with `crontab -l` on EC2 whenever you add/change a job.
    """

    cron_name: str
    description: str
    schedule_human: str  # human-readable summary, not parsed
    expected_weekdays: set[int]  # IST weekday numbers Mon=0..Sun=6
    min_runs_per_day: int = 1  # >1 only for intraday-style crons


CRON_REGISTRY: list[CronSpec] = [
    # F2 (chunk 6): sell-side weekly suggestions. Same day as buy
    # (Sunday) with 30-min offset so they don't pile on yfinance /
    # Claude / Tavily quotas back-to-back. NOTE: when the EC2 crontab
    # uses `--direction=both` the umbrella row is logged under
    # 'weekly_suggestions' (08:00 IST equivalent) and this entry is
    # idle. The entry exists so the registry / heartbeat dashboard
    # tolerates either deployment topology.
    CronSpec(
        cron_name="weekly_suggestions_sell",
        description="Weekly sell-side suggestions: profit-booking candidates from active holdings.",
        schedule_human="Sun 07:30 IST",
        # #49/TD40: idle when the EC2 crontab runs the umbrella
        # `weekly_suggestions --direction=both` (logged under
        # 'weekly_suggestions'). An empty expected_weekdays set makes
        # is_expected_today() always False, so cron_health_check never emits
        # a false "MISSING: weekly_suggestions_sell" on Sundays. Restore to
        # {6} ONLY if you split the crontab into a standalone sell-side job
        # that logs its own heartbeat under this cron_name.
        expected_weekdays=set(),
    ),
    # Phase 1 crons (instrumented in this commit)
    CronSpec(
        cron_name="refresh_instruments",
        description="Refresh NSE master from NSE EQUITY_L.csv",
        schedule_human="daily 03:00 IST",
        expected_weekdays=WEEKDAYS_ALL,
    ),
    CronSpec(
        cron_name="refresh_prices",
        description="EOD price refresh (held + monitored + NIFTY 100)",
        schedule_human="weekdays 19:00 IST",
        expected_weekdays=WEEKDAYS_MON_FRI,
    ),
    CronSpec(
        cron_name="refresh_prices_intraday",
        description="15-min intraday quotes for active holdings",
        schedule_human="weekdays 09:15-15:45 IST every 15m (~28 runs)",
        expected_weekdays=WEEKDAYS_MON_FRI,
        min_runs_per_day=1,
    ),
    CronSpec(
        cron_name="take_reconciliation_snapshot",
        description="Auto reconciliation snapshot vs ICICI",
        schedule_human="weekdays 19:30 IST",
        expected_weekdays=WEEKDAYS_MON_FRI,
    ),
    # Phase 2 crons (registered in this commit — F5a)
    CronSpec(
        cron_name="refresh_fundamentals",
        description="Weekly fundamentals refresh (NIFTY 100)",
        schedule_human="Sunday 06:00 IST",
        expected_weekdays=SUNDAY,
    ),
    CronSpec(
        cron_name="fetch_news_for_universe",
        description="Weekly Tavily news fetch + Haiku classify",
        schedule_human="Sunday 06:30 IST",
        expected_weekdays=SUNDAY,
    ),
    CronSpec(
        cron_name="weekly_suggestions",
        description="Weekly buy + sell suggestions run + combined digest",
        schedule_human="Sunday 07:00 IST",
        expected_weekdays=SUNDAY,
    ),
    CronSpec(
        cron_name="track_suggestion_outcomes",
        description="Daily outcome price snapshots (30/60/90/180d windows)",
        schedule_human="weekdays 19:45 IST",
        expected_weekdays=WEEKDAYS_MON_FRI,
    ),
    # Daily news body purge — storage hygiene (P2-4 / #13 / TD27)
    CronSpec(
        cron_name="purge_news_bodies",
        description="Purge classified news_articles body_text older than 30 days",
        schedule_human="daily 02:30 IST",
        expected_weekdays=WEEKDAYS_ALL,
    ),
    # The health check itself (records its own heartbeat)
    CronSpec(
        cron_name="cron_health_check",
        description="Daily F4 health check",
        schedule_human="daily 21:00 IST",
        expected_weekdays=WEEKDAYS_ALL,
    ),
]


def get_registry() -> list[CronSpec]:
    """Read-only registry accessor."""
    return list(CRON_REGISTRY)


def get_spec(cron_name: str) -> CronSpec | None:
    for spec in CRON_REGISTRY:
        if spec.cron_name == cron_name:
            return spec
    return None


# ────────────────────────────────────────────────────────────────────
# Context manager
@dataclass
class _Heartbeat:
    """Mutable state accumulated during a `cron_run(...)` block.

    The script can attach metadata mid-flight via `hb.metadata[key] = value`
    or call `hb.mark_skipped("reason")` for "nothing to do" runs.
    """

    cron_name: str
    started_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    # Set automatically by the context manager (or by the caller):
    status: HeartbeatStatus = "success"
    error: str | None = None
    finished_at: datetime | None = None

    def mark_skipped(self, reason: str) -> None:
        """Cron decided there was nothing to do (e.g. market closed).
        Counts as healthy in the health check, but visible in heartbeats."""
        self.status = "skipped"
        self.metadata.setdefault("skipped_reason", reason)


@contextmanager
def cron_run(cron_name: str) -> Iterator[_Heartbeat]:
    """Wrap a cron script's main body. Writes exactly one heartbeat doc on exit.

    Usage:
        def main() -> int:
            with cron_run("refresh_prices") as hb:
                rows = do_work()
                hb.metadata["rows"] = len(rows)
            return 0

    Exceptions are caught, recorded as `failure` with `error=str(exc)`, then
    re-raised so the caller's exit-code path is preserved.
    """
    hb = _Heartbeat(
        cron_name=cron_name,
        started_at=utcnow(),
    )
    try:
        yield hb
    except Exception as exc:
        hb.status = "failure"
        hb.error = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        hb.finished_at = utcnow()
        _persist(hb)


def _persist(hb: _Heartbeat) -> None:
    """Internal: write the heartbeat doc.

    Best-effort: if Mongo is unreachable we swallow the write error rather than
    masking the underlying cron error. The missing heartbeat will itself be
    flagged by the daily health check.
    """
    doc = {
        "cron_name": hb.cron_name,
        "started_at": hb.started_at,
        "finished_at": hb.finished_at,
        "status": hb.status,
        "error": hb.error,
        "metadata": hb.metadata or {},
        "_schema_version": 1,
    }
    try:
        Collections.cron_heartbeats().insert_one(_convert_decimals_to_decimal128(doc))
    except Exception:
        _append_fallback(doc)


def _isoformat_or_none(value: datetime | None) -> str | None:
    """Serialize a datetime to ISO-8601 for the fallback log, preserving None."""
    return value.isoformat() if value is not None else None


def _append_fallback(doc: dict[str, Any]) -> None:
    """Last-resort sink when the Mongo heartbeat insert fails.

    Appends the heartbeat as ONE JSON object per line to `_FALLBACK_LOG_PATH`.
    Best-effort: never raises (mirrors `_persist`'s no-mask contract — a failure
    here must not hide the underlying cron error). The daily health check reads
    this file in addition to Mongo. datetimes are stored as ISO-8601 strings;
    any non-JSON-native value in metadata falls back to its str() form.
    """
    try:
        record = {
            "cron_name": doc["cron_name"],
            "started_at": _isoformat_or_none(doc.get("started_at")),
            "finished_at": _isoformat_or_none(doc.get("finished_at")),
            "status": doc["status"],
            "error": doc["error"],
            "metadata": doc.get("metadata") or {},
            "_schema_version": doc.get("_schema_version", 1),
        }
        line = json.dumps(record, default=str)
        with open(_FALLBACK_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass


# ────────────────────────────────────────────────────────────────────
# Readers
def get_recent_heartbeats(limit: int = 200) -> list[dict]:
    """Latest heartbeats across all crons, newest first."""
    limit = max(1, min(limit, 1000))
    return list(
        Collections.cron_heartbeats().find({}).sort("started_at", -1).limit(limit)
    )


def get_latest_per_cron() -> dict[str, dict | None]:
    """Returns {cron_name: latest_heartbeat_doc_or_None}.

    Every cron in CRON_REGISTRY is represented in the keys, even those
    that have never run (value is None for those).
    """
    out: dict[str, dict | None] = {spec.cron_name: None for spec in CRON_REGISTRY}
    pipeline = [
        {"$sort": {"started_at": -1}},
        {"$group": {"_id": "$cron_name", "doc": {"$first": "$$ROOT"}}},
    ]
    for row in Collections.cron_heartbeats().aggregate(pipeline):
        out[row["_id"]] = row["doc"]
    return out


def count_today_heartbeats(
    cron_name: str,
    *,
    ist_today_utc_start: datetime,
    ist_tomorrow_utc_start: datetime,
) -> dict[str, int]:
    """Count heartbeats for a cron in the IST-today window (expressed in UTC).

    Returns {"total": N, "success": N, "failure": N, "skipped": N}.
    """
    cursor = Collections.cron_heartbeats().aggregate(
        [
            {
                "$match": {
                    "cron_name": cron_name,
                    "started_at": {
                        "$gte": ist_today_utc_start,
                        "$lt": ist_tomorrow_utc_start,
                    },
                }
            },
            {"$group": {"_id": "$status", "n": {"$sum": 1}}},
        ]
    )
    counts = {"total": 0, "success": 0, "failure": 0, "skipped": 0}
    for row in cursor:
        s = row["_id"]
        n = row["n"]
        counts["total"] += n
        if s in counts:
            counts[s] += n
    return counts


def _parse_fallback_dt(value: str | None) -> datetime | None:
    """Parse an ISO-8601 string from the fallback log to a naive-UTC datetime.

    The window bounds used by the health check are naive UTC (tzinfo stripped by
    `ist_today_window_utc`), so a tz-aware value is converted to UTC and made
    naive for an apples-to-apples comparison. Returns None on any parse error.
    """
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except Exception:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def count_today_heartbeats_from_fallback(
    cron_name: str,
    *,
    ist_today_utc_start: datetime,
    ist_tomorrow_utc_start: datetime,
) -> dict[str, int]:
    """Fallback-log mirror of `count_today_heartbeats`.

    Reads `_FALLBACK_LOG_PATH` (JSON-per-line, written by `_append_fallback`
    when a Mongo heartbeat insert fails) and counts records for `cron_name`
    whose started_at falls in the IST-today window. Returns the same
    {"total","success","failure","skipped"} shape. Best-effort: a missing or
    unreadable file, or a malformed line, contributes zero and never raises.

    A run is recorded here ONLY when its Mongo insert failed, so it cannot also
    be in Mongo — merging these counts with `count_today_heartbeats` never
    double-counts the same run.
    """
    counts = {"total": 0, "success": 0, "failure": 0, "skipped": 0}
    try:
        with open(_FALLBACK_LOG_PATH, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
    except FileNotFoundError:
        return counts
    except Exception:
        return counts
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except Exception:
            continue
        if rec.get("cron_name") != cron_name:
            continue
        started = _parse_fallback_dt(rec.get("started_at"))
        if started is None:
            continue
        if not (ist_today_utc_start <= started < ist_tomorrow_utc_start):
            continue
        counts["total"] += 1
        s = rec.get("status")
        if s in counts:
            counts[s] += 1
    return counts


# ────────────────────────────────────────────────────────────────────
# Time helpers
def ist_today_window_utc(now_utc: datetime | None = None) -> tuple[datetime, datetime]:
    """Return (start_of_today_ist, start_of_tomorrow_ist) — both in UTC.

    Mongo stores naive UTC; we strip tzinfo before returning so the bounds
    can be used directly in `$gte`/`$lt` against stored started_at values.
    """
    now = now_utc or datetime.now(timezone.utc)
    now_ist = now.astimezone(IST)
    today_ist_start = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_ist_start = today_ist_start + timedelta(days=1)
    # Convert back to UTC, then strip tzinfo to match Mongo's naive convention.
    today_utc = today_ist_start.astimezone(timezone.utc).replace(tzinfo=None)
    tomorrow_utc = tomorrow_ist_start.astimezone(timezone.utc).replace(tzinfo=None)
    return today_utc, tomorrow_utc


def is_expected_today(spec: CronSpec, now_utc: datetime | None = None) -> bool:
    """True if this cron is expected to run today (per IST weekday)."""
    now = now_utc or datetime.now(timezone.utc)
    ist_weekday = now.astimezone(IST).weekday()
    return ist_weekday in spec.expected_weekdays
