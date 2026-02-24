"""
CareTopicz Agent Service - API request/response schemas.
"""

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Single chat message in a conversation."""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request body for the /chat endpoint."""

    message: str = Field(..., description="User message to the agent")
    session_id: str | None = Field(default=None, description="Session ID for conversation continuity")
    patient_id: str | None = Field(default=None, description="Optional patient context ID")


class ChatResponse(BaseModel):
    """Response from the /chat endpoint."""

    response: str = Field(..., description="Agent response text")
    session_id: str | None = Field(default=None, description="Session ID for follow-up turns")


class HealthResponse(BaseModel):
    """Response from the /health endpoint."""

    status: str = Field(..., description="Service status: 'healthy' or 'unhealthy'")
    service: str = Field(..., description="Service name")
    version: str = Field(default="0.1.0", description="API version")
