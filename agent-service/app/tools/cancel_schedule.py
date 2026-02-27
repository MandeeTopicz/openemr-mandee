"""
CareTopicz Agent Service - Cancel/discontinue medication schedule tool.
Dedicated tool so the LLM does not need to choose an action parameter.
"""
from typing import Any
from pydantic import BaseModel, Field
from app.clients.openemr import cancel_medication_schedule

class CancelScheduleInput(BaseModel):
    schedule_id: int = Field(..., description="The schedule ID to cancel")
    reason: str = Field(default="Cancelled", description="Reason for cancellation")

def cancel_schedule(schedule_id: int, reason: str = "Cancelled") -> dict[str, Any]:
    """Cancel or discontinue a medication schedule by its ID. Use this when the user wants to stop, cancel, or discontinue a schedule."""
    result = cancel_medication_schedule(
        schedule_id=schedule_id,
        reason=reason,
        cancelled_by="agent",
    )
    if result.get("success"):
        return {"success": True, "message": f"Schedule {schedule_id} has been successfully cancelled. Reason: {reason}."}
    return result
