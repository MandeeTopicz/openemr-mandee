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


class ToolUsed(BaseModel):
    """Single tool call: name and brief summary."""

    name: str = Field(..., description="Tool name that was called")
    summary: str = Field(..., description="Brief summary of what the tool did or returned")


class ChatResponse(BaseModel):
    """Response from the /chat endpoint."""

    response: str = Field(..., description="Agent response text")
    session_id: str | None = Field(default=None, description="Session ID for follow-up turns")
    run_id: str | None = Field(default=None, description="LangSmith run ID for feedback linking")
    tools_used: list[ToolUsed] = Field(
        default_factory=list,
        description="Tools called during the request (name and brief summary)",
    )


class FeedbackRequest(BaseModel):
    """Request body for the /chat/feedback endpoint."""

    run_id: str = Field(..., description="LangSmith run ID from the chat response")
    score: float = Field(..., ge=0, le=1, description="1=thumbs up, 0=thumbs down")
    comment: str | None = Field(default=None, description="Optional comment")


class HealthResponse(BaseModel):
    """Response from the /health endpoint."""

    status: str = Field(..., description="Service status: 'healthy' or 'unhealthy'")
    service: str = Field(..., description="Service name")
    version: str = Field(default="0.1.0", description="API version")
