"""Ad-hoc chat endpoints (#27, Chat 6 -- F1 + F3).

- POST /chat/suggestions       (F1) chat about the latest weekly suggestion runs.
- POST /chat/holdings/{isin}   (F3) chat about a specific stock -- held OR
                               researched not-yet-owned (on-demand enrichment
                               in conversation_service).
- GET  /chat/history           recent exchanges for the embedded chat panels.

This router is a thin HTTP layer: validate, delegate to conversation_service,
serialize. Mirrors the request-model + decimal-to-jsonable serialization
conventions in routers/suggestions.py.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Literal

from bson import Decimal128, ObjectId
from fastapi import APIRouter, HTTPException, Path, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.db.client import Collections
from app.services import conversation_service

log = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


def _jsonable(v: Any) -> Any:
    """Recursively convert Mongo/Decimal types to JSON-friendly values
    (mirrors routers/suggestions.py._decimal_to_jsonable)."""
    if isinstance(v, Decimal128):
        return str(v.to_decimal())
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, datetime):
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()
    if isinstance(v, list):
        return [_jsonable(x) for x in v]
    if isinstance(v, dict):
        return {k: _jsonable(val) for k, val in v.items()}
    return v


def _serialize_conversation(doc: dict) -> dict:
    """Serialize a conversation Mongo doc for the API response."""
    return {
        "id": str(doc["_id"]),
        "query": doc.get("query"),
        "response": doc.get("response"),
        "intent": doc.get("intent"),
        "scope": doc.get("scope"),
        "sentiment_overlay": doc.get("sentiment_overlay"),
        "related_entities_isins": doc.get("related_entities_isins", []),
        "related_holding_id": (
            str(doc["related_holding_id"]) if doc.get("related_holding_id") else None
        ),
        "model_used": doc.get("model_used"),
        "input_tokens": doc.get("input_tokens", 0),
        "output_tokens": doc.get("output_tokens", 0),
        "cost_usd": _jsonable(doc.get("cost_usd")),
        "duration_ms": doc.get("duration_ms", 0),
        "created_at": _jsonable(doc.get("created_at")),
    }


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(..., min_length=1, max_length=2000)
    sentiment_overlay: Literal["cautious", "neutral", "aggressive"] | None = None


@router.post("/suggestions")
def chat_suggestions(payload: ChatRequest) -> dict:
    """F1: ad-hoc chat about the latest weekly suggestion runs."""
    doc = conversation_service.chat_about_suggestions(
        payload.query, payload.sentiment_overlay
    )
    return _serialize_conversation(doc)


@router.post("/holdings/{isin}")
def chat_holding(
    payload: ChatRequest,
    isin: str = Path(..., min_length=12, max_length=12, pattern=r"^[A-Z0-9]{12}$"),
) -> dict:
    """F3: ad-hoc chat about a specific stock (held or researched not-yet-owned)."""
    doc = conversation_service.chat_about_holding(
        isin, payload.query, payload.sentiment_overlay
    )
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{isin} is not a recognized NSE instrument. "
            "Refresh the instrument master if you believe this is wrong.",
        )
    return _serialize_conversation(doc)


@router.get("/history")
def chat_history(
    scope: Literal["suggestions", "holding"] | None = Query(None),
    isin: str | None = Query(
        None, min_length=12, max_length=12, pattern=r"^[A-Z0-9]{12}$"
    ),
    limit: int = Query(20, ge=1, le=100),
) -> list[dict]:
    """Newest-first recent chat exchanges, optionally filtered by scope and/or ISIN.

    Backs the embedded chat panels so they can render prior exchanges on load."""
    query: dict = {}
    if scope:
        query["scope"] = scope
    if isin:
        query["related_entities_isins"] = isin
    cursor = Collections.conversations().find(query).sort("created_at", -1).limit(limit)
    return [_serialize_conversation(d) for d in cursor]
