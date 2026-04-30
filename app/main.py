"""FastAPI app entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.client import ping
from app.db.indexes import ensure_all_indexes
from app.routers import holdings, instruments

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

app.include_router(holdings.router)
app.include_router(instruments.router)

@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "mongo": "ok" if ping() else "fail"}
