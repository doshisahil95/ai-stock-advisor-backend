"""FastAPI app entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app.db.client import ping
from app.db.indexes import ensure_all_indexes
from app.routers import (
    conversations,
    cost_basis,
    cron,
    holdings,
    instruments,
    portfolio,
    reconciliation,
    suggestions,
    transactions,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
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
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
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
