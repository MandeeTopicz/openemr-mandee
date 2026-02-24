"""
CareTopicz Agent Service - API route handlers.

Endpoints: /health, /chat, /verify, /tools (latter as placeholders).
"""

import asyncio

from fastapi import APIRouter, HTTPException, Request

from app.agent.graph import invoke_graph
from app.api.schemas import ChatResponse, FeedbackRequest, HealthResponse
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
        response_text, metrics = await asyncio.to_thread(invoke_graph, msg)
    except ValueError as e:
        if "ANTHROPIC_API_KEY" in str(e):
            raise HTTPException(
                status_code=503,
                detail="Agent service not configured. Set ANTHROPIC_API_KEY in .env",
            ) from e
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        from app.observability.metrics import (
            RequestMetrics,
            categorize_error,
            update_langsmith_run_metadata,
        )

        m = RequestMetrics(error_category=categorize_error(e), error_message=str(e))
        try:
            from langsmith.run_helpers import get_current_run_tree

            run_tree = get_current_run_tree()
            if run_tree and run_tree.id:
                update_langsmith_run_metadata(str(run_tree.id), m.to_metadata())
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e)) from e

    return ChatResponse(
        response=response_text,
        session_id=body.get("session_id"),
        run_id=metrics.run_id,
    )


@router.post("/chat/feedback")
async def chat_feedback(body: FeedbackRequest):
    """
    Submit user feedback (thumbs up/down) for a chat response. Links to the LangSmith trace.
    """
    try:
        from langsmith import Client

        client = Client()
        client.create_feedback(
            run_id=body.run_id,
            key="user_rating",
            score=body.score,
            comment=body.comment,
        )
        return {"status": "ok", "message": "Feedback recorded"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
