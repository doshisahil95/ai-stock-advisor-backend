"""FastAPI app entry point."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app.db.client import ping
from app.db.indexes import ensure_all_indexes
from app.routers import (
    admin,
    conversations,
    cost_basis,
    cron,
    holdings,
    instruments,
    portfolio,
    reconciliation,
    suggestions,
    transactions,
    watchlist,
)

# --- Structured JSON logging (master_todo #38) -----------------------------
# One single-line JSON object per log record into stdout (journald), replacing
# the prior logging.basicConfig text formatter. Stdlib only — no new
# dependency (keeps the #32 ">=3.12,<3.14" environment lean).

# Standard LogRecord attributes that are NOT caller-supplied context. Anything
# on a record outside this set (and not private) is merged into the JSON
# object, so an explicit extra={...} (e.g. isin, cron_name) is preserved.
_RESERVED_LOG_RECORD_ATTRS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)


class JsonLogFormatter(logging.Formatter):
    """Render each LogRecord as a single-line JSON object.

    Fields: timestamp (UTC ISO-8601 ms + 'Z'), level, logger, message,
    module, func, line; traceback when exc_info is present; plus any
    caller-supplied extra={...} keys merged at the top level.

    The timestamp is derived from record.created via datetime.fromtimestamp
    (NOT datetime.now()/utcnow()), so this stays clean against
    scripts/check_datetime_hygiene.py.
    """

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc)
        payload: dict = {
            "timestamp": ts.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            payload["traceback"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)
        for key, value in record.__dict__.items():
            if key in _RESERVED_LOG_RECORD_ATTRS or key.startswith("_"):
                continue
            payload[key] = value
        return json.dumps(payload, default=str, ensure_ascii=False)


def _configure_logging() -> None:
    """Install the JSON formatter on the root + uvicorn handlers.

    Replaces logging.basicConfig. All stdout — app loggers AND uvicorn /
    uvicorn.access request logs — becomes one structured JSON stream into
    journald. uvicorn configures its own logging when it loads, then imports
    this module, so this call runs last and wins; handlers.clear() keeps it
    idempotent. (master_todo #38)
    """
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    # Route uvicorn's own loggers through the same JSON handler and stop them
    # propagating to root (otherwise every uvicorn line would log twice).
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        ulog = logging.getLogger(name)
        ulog.handlers.clear()
        ulog.addHandler(handler)
        ulog.setLevel(logging.INFO)
        ulog.propagate = False


_configure_logging()
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting portfolio-advisor API")
    if not ping():
        log.error("MongoDB ping failed at startup")
    else:
        log.info("MongoDB reachable")
    results = ensure_all_indexes()
    for coll, indexes in results.items():
        log.info("indexes ok: %s -> %d", coll, len(indexes))
    log.info("API ready")
    yield
    log.info("Shutting down portfolio-advisor API")


app = FastAPI(
    title="Portfolio Advisor",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow Next.js dashboard (running on EC2 + accessed via Tailscale)
# Permissive for our Tailscale-only context; if we ever go public, tighten this.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://100.112.20.41:3000",  # EC2 IP, used during dev
        "http://localhost:3000",  # Local fallback if needed
        "https://*.ts.net",  # Tailscale Funnel domains
    ],
    allow_origin_regex=r"https://.*\.ts\.net",  # Funnel subdomain wildcard
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS", "PUT"],
    allow_headers=["*"],
)

app.include_router(holdings.router)
app.include_router(instruments.router)
app.include_router(portfolio.router)
app.include_router(reconciliation.router)
app.include_router(cost_basis.router)
app.include_router(transactions.router)
app.include_router(suggestions.router)
app.include_router(cron.router)
app.include_router(conversations.router)
app.include_router(watchlist.router)
app.include_router(admin.router)


@app.get("/health", tags=["meta"])
def health(response: Response) -> dict:
    """Liveness + Mongo readiness probe.

    Pings MongoDB on every call (ping() catches its own errors and returns a
    bool). On success returns 200 with {"status": "ok", "mongo": "ok"}; on
    failure returns 503 with {"status": "degraded", "mongo": "fail"} so an
    external monitor — or the deploy checklist — sees an unhealthy box as
    unhealthy instead of a misleading 200. (master_todo #34)

    yfinance is deliberately NOT probed here: it is a slow, rate-limited
    external dependency and a Yahoo throttle would cause false 503s on the
    hot health path. Price-source health is observed via the refresh_prices*
    cron heartbeats (F4), not /health.
    """
    if not ping():
        log.error("Health check: MongoDB ping failed")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "degraded", "mongo": "fail"}
    return {"status": "ok", "mongo": "ok"}
