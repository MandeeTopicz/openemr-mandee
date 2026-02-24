"""
CareTopicz Agent Service - API route handlers.

Endpoints: /health, /chat, /verify, /tools (latter as placeholders).
"""

import asyncio

from fastapi import APIRouter, HTTPException, Request

from app.agent.graph import invoke_graph
from app.api.schemas import ChatResponse, HealthResponse
from app.config import settings

router = APIRouter()

_EMPTY_MSG_RESPONSE = "I didn't receive a message. How can I help you?"


@router.get("/health", response_model=HealthResponse)
async def health():
    """Return service health status."""
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version="0.1.0",
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request):
    """
    Accept a user message and return an agent response via LangGraph.
    """
    body = await request.json()
    msg = (body.get("message") or "").strip()
    if not msg:
        return ChatResponse(
            response=_EMPTY_MSG_RESPONSE,
            session_id=body.get("session_id"),
        )

    try:
        response_text = await asyncio.to_thread(invoke_graph, msg)
    except ValueError as e:
        if "ANTHROPIC_API_KEY" in str(e):
            raise HTTPException(
                status_code=503,
                detail="Agent service not configured. Set ANTHROPIC_API_KEY in .env",
            ) from e
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return ChatResponse(
        response=response_text,
        session_id=body.get("session_id"),
    )
