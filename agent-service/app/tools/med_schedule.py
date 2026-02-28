"""
CareTopicz Agent Service - Regulated medication schedule tool.

Manage iPLEDGE, biologic, and REMS medication schedules.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.clients.openemr import (
    cancel_medication_schedule,
    check_schedule_conflicts,
    complete_milestone,
    complete_treatment,
    create_medication_schedule,
    discontinue_medication_schedule,
    extend_medication_schedule,
    get_dashboard_alerts,
    get_medication_schedule,
    get_patient_demographics,
    pause_medication_schedule,
    reschedule_milestone,
    resume_medication_schedule,
)


class MedicationScheduleInput(BaseModel):
    """Input schema for medication_schedule."""

    action: Literal[
        "create",
        "status",
        "complete",
        "cancel",
        "reschedule",
        "conflicts",
        "dashboard",
        "extend",
        "complete_treatment",
        "discontinue",
        "pause",
        "resume",
    ] = Field(
        ...,
        description="Action: create, status, complete, cancel, reschedule, conflicts, dashboard, extend, complete_treatment, discontinue, pause, resume",
    )
    patient_id: int | None = Field(
        default=None,
        description="OpenEMR patient ID (required for create, status)",
    )
    medication: str | None = Field(
        default=None,
        description="Medication name (required for create), e.g. isotretinoin, adalimumab",
    )
    patient_category: Literal["fcbp", "non_fcbp_female", "male", "all"] | None = Field(
        default=None,
        description="fcbp, non_fcbp_female, or male (for create)",
    )
    milestone_id: int | None = Field(
        default=None,
        description="Milestone ID (for complete, reschedule)",
    )
    completed_date: str | None = Field(
        default=None,
        description="Date completed YYYY-MM-DD (for complete)",
    )
    new_due_date: str | None = Field(
        default=None,
        description="New due date YYYY-MM-DD (for reschedule)",
    )
    schedule_id: int | None = Field(
        default=None,
        description="Schedule ID (for cancel, conflicts)",
    )
    reason: str | None = Field(
        default=None,
        description="Reason for cancellation (for cancel)",
    )
    notes: str | None = Field(
        default=None,
        description="Additional notes",
    )
    start_date: str | None = Field(
        default=None,
        description="Start date YYYY-MM-DD (for create)",
    )
    created_by: str | None = Field(
        default="agent",
        description="Username of staff creating (for create)",
    )
    duration_months: int | None = Field(
        default=None,
        description="Number of months of milestones to generate (default: 6 for isotretinoin, 3 for biologics). For create or extend.",
    )


def _patient_name(patient_id: int) -> str:
    """Get patient display name."""
    demos = get_patient_demographics(patient_id)
    if not demos:
        return f"Patient {patient_id}"
    f = demos.get("fname", "")
    l = demos.get("lname", "")
    return f"{f} {l}".strip() or f"Patient {patient_id}"


def _format_schedule_status(data: dict[str, Any], patient_id: int | None = None) -> str:
    """Format schedule/milestone data for LLM."""
    if not data.get("success"):
        return f"Error: {data.get('error', 'Unknown error')}"

    sched = data.get("schedule")
    schedules = data.get("schedules", [])

    if sched:
        lines = []
        pid = sched.get("patient_id")
        name = _patient_name(int(pid)) if pid else (_patient_name(patient_id) if patient_id else None)
        if name:
            lines.append(f"Patient: {name}")
        lines.append(f"Schedule ID: {sched.get('id')} | Status: {sched.get('status', '')}")
        lines.append(f"Protocol: {sched.get('patient_category', '')} | Start: {sched.get('start_date', '')}")
        milestones = sched.get("milestones", [])
        pending = [m for m in milestones if m.get("status") in ("pending", "scheduled", "overdue")]
        if pending:
            lines.append("\nNext pending:")
            for m in pending[:5]:
                due = m.get("due_date", "")
                wend = m.get("window_end", "")
                status = m.get("status", "pending")
                mid = m.get('id', '')
            lines.append(f"  - [milestone_id={mid}] {m.get('step_name', '')}: due {due} (window ends {wend}) [{status}]")
        else:
            lines.append("\nAll milestones completed or no milestones.")
        if data.get("warnings"):
            lines.append("\nWarnings: " + "; ".join(data["warnings"]))
        return "\n".join(lines)

    if schedules is not None:
        if not schedules:
            return "No active schedules found."
        lines = []
        for s in schedules:
            pid = s.get("patient_id")
            name = _patient_name(int(pid)) if pid else "Unknown"
            mname = s.get("medication_name", "")
            lines.append(f"- {name}: Schedule {s.get('id')} | {mname} | Status: {s.get('status', '')}")
            milestones = s.get("milestones", [])
            pending = [m for m in milestones if m.get("status") in ("pending", "scheduled", "overdue")]
            if pending:
                m0 = pending[0]
                lines.append(f"  Next: {m0.get('step_name', '')} due {m0.get('due_date', '')}")
        return "Active schedules:\n" + "\n".join(lines)

    return "No schedule data returned."


def medication_schedule(
    action: str,
    patient_id: int | None = None,
    medication: str | None = None,
    patient_category: str | None = None,
    milestone_id: int | None = None,
    completed_date: str | None = None,
    new_due_date: str | None = None,
    schedule_id: int | None = None,
    reason: str | None = None,
    notes: str | None = None,
    start_date: str | None = None,
    created_by: str = "agent",
    duration_months: int | None = None,
) -> dict[str, Any]:
    """
    Manage regulated medication schedules (iPLEDGE, biologics, REMS).
    """
    if action == "create":
        if not patient_id or not medication or not patient_category:
            return {"success": False, "error": "patient_id, medication, and patient_category required for create"}
        from datetime import date
        sd = start_date or str(date.today())
        result = create_medication_schedule(
            patient_id=patient_id,
            medication=medication,
            patient_category=patient_category,
            start_date=sd,
            created_by=created_by or "agent",
            duration_months=duration_months,
            notes=notes or "",
        )
        if result.get("success") and result.get("schedule"):
            return result
        return result

    if action == "extend":
        if not schedule_id and not patient_id:
            return {"success": False, "error": "schedule_id or patient_id required for extend"}
        if not duration_months:
            return {"success": False, "error": "duration_months required for extend (how many months to add)"}
        result = extend_medication_schedule(
            schedule_id=schedule_id,
            patient_id=patient_id,
            duration_months=duration_months or 3,
        )
        return result

    if action == "complete_treatment":
        if not schedule_id and not patient_id:
            return {"success": False, "error": "schedule_id or patient_id required for complete_treatment"}
        result = complete_treatment(
            schedule_id=schedule_id,
            patient_id=patient_id,
            notes=notes or "",
        )
        return result

    if action == "discontinue":
        if not schedule_id and not patient_id:
            return {"success": False, "error": "schedule_id or patient_id required for discontinue"}
        result = discontinue_medication_schedule(
            schedule_id=schedule_id,
            patient_id=patient_id,
            reason=reason or "Discontinued",
            discontinued_by=created_by or "agent",
        )
        if result.get("success"):
            return {"success": True, "message": f"Schedule {schedule_id or 'for patient ' + str(patient_id)} has been successfully discontinued. Reason: {reason or 'Discontinued'}. No further action needed."}
        return result

    if action == "pause":
        if not schedule_id and not patient_id:
            return {"success": False, "error": "schedule_id or patient_id required for pause"}
        result = pause_medication_schedule(
            schedule_id=schedule_id,
            patient_id=patient_id,
            notes=notes or "",
        )
        return result

    if action == "resume":
        if not schedule_id and not patient_id:
            return {"success": False, "error": "schedule_id or patient_id required for resume"}
        result = resume_medication_schedule(
            schedule_id=schedule_id,
            patient_id=patient_id,
        )
        return result

    if action == "status":
        if not patient_id:
            return {"success": False, "error": "patient_id required for status"}
        result = get_medication_schedule(patient_id)
        return result

    if action == "complete":
        if not milestone_id:
            return {"success": False, "error": "milestone_id required for complete"}
        from datetime import date
        cd = completed_date or str(date.today())
        result = complete_milestone(
            milestone_id=milestone_id,
            completed_by=created_by or "agent",
            completed_date=cd,
            notes=notes or "",
        )
        if result.get("success") and result.get("schedule"):
            pid = result["schedule"].get("patient_id")
            result["_formatted"] = _format_schedule_status(result, int(pid) if pid else None)
        return result

    if action == "cancel":
        if not schedule_id:
            return {"success": False, "error": "schedule_id required for cancel"}
        result = cancel_medication_schedule(
            schedule_id=schedule_id,
            reason=reason or "Cancelled",
            cancelled_by=created_by or "agent",
        )
        if result.get("success"):
            return {"success": True, "message": f"Schedule {schedule_id} has been successfully cancelled. Reason: {reason or 'Cancelled'}. No further action needed."}
        return result

    if action == "reschedule":
        if not milestone_id or not new_due_date:
            return {"success": False, "error": "milestone_id and new_due_date required for reschedule"}
        return reschedule_milestone(
            milestone_id=milestone_id,
            new_due_date=new_due_date,
            rescheduled_by=created_by or "agent",
        )

    if action == "conflicts":
        if not schedule_id:
            return {"success": False, "error": "schedule_id required for conflicts"}
        return check_schedule_conflicts(schedule_id)

    if action == "dashboard":
        return get_dashboard_alerts()

    return {"success": False, "error": f"Unknown action: {action}"}
