"""
CareTopicz Agent Service - API route handlers.

Endpoints: /health, /chat, /verify, /tools (latter as placeholders).
"""

import asyncio
import json
import logging

import redis
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
import os
from langchain_core.messages import AIMessage, HumanMessage

from app.agent.graph import invoke_graph
from app.api.schemas import ChatResponse, FeedbackRequest, HealthResponse, ToolUsed
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

_redis = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    decode_responses=True,
)


def _get_history(session_id: str) -> list:
    """Get conversation history from Redis."""
    try:
        data = _redis.get(f"chat_history:{session_id}")
        if data:
            messages = json.loads(data)
            result = []
            for m in messages:
                if m.get("role") == "human":
                    result.append(HumanMessage(content=m.get("content", "")))
                else:
                    result.append(AIMessage(content=m.get("content", "")))
            return result
    except redis.RedisError as e:
        logger.warning("Redis get_history failed: %s", e)
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Redis history parse error: %s", e)
    return []


def _save_history(session_id: str, history: list):
    """Save conversation history to Redis with 7 day TTL."""
    try:
        messages = []
        for m in history:
            if isinstance(m, HumanMessage):
                messages.append({"role": "human", "content": m.content})
            else:
                messages.append({"role": "ai", "content": m.content})
        # Keep last 20 messages (10 turns)
        messages = messages[-20:]
        _redis.setex(f"chat_history:{session_id}", 7 * 86400, json.dumps(messages))
    except redis.RedisError as e:
        logger.warning("Redis save_history failed: %s", e)

_EMPTY_MSG_RESPONSE = "I didn't receive a message. How can I help you?"


@router.get("/health", response_model=HealthResponse)
async def health():
    """Return service health status."""
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version="0.1.0",
    )


@router.get("/metrics")
async def metrics():
    """
    Return latency and success rate metrics for tool calls.
    Targets: single-tool < 5s, multi-step < 15s, tool success rate > 95%.
    """
    from app.observability.metrics import get_metrics_report

    return get_metrics_report()


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
        session_id = body.get("session_id") or "default"
        history = _get_history(session_id)
        response_text, metrics, tools_used = await asyncio.to_thread(invoke_graph, msg, None, history)
        # Store conversation turn
        history.append(HumanMessage(content=msg))
        history.append(AIMessage(content=response_text))
        _save_history(session_id, history)
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
        tools_used=[ToolUsed(name=t["name"], summary=t["summary"]) for t in tools_used],
    )


@router.get("/pdfs/{filename}")
async def serve_pdf(filename: str):
    """Serve generated PDF files."""
    pdf_dir = "/app/pdfs"
    pdf_path = os.path.join(pdf_dir, filename)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(pdf_path, media_type="application/pdf", filename=filename)


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
