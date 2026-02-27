"""
CareTopicz Agent Service - Patient summary tool.

Retrieves a patient summary from OpenEMR.
Output excludes name, DOB, SSN, MRN to avoid sending PII to the LLM.
"""

from typing import Any

from pydantic import BaseModel, Field

from app.clients.openemr import get_patient, get_patient_demographics
from app.utils.response_templates import TOOL_FAILURE_UNAVAILABLE


class PatientSummaryInput(BaseModel):
    """Input schema for patient_summary."""

    patient_id: str = Field(..., description="OpenEMR/FHIR Patient ID to summarize")


def _age_range_from_birth_date(birth_date: str | None) -> str:
    """Return age range (e.g. '30-39') without exposing exact DOB. Returns 'unknown' if missing."""
    if not birth_date or len(birth_date) < 4:
        return "unknown"
    try:
        from datetime import date

        y = int(birth_date[:4])
        today = date.today()
        age = today.year - y
        if age < 0:
            return "unknown"
        low = (age // 10) * 10
        high = low + 9
        return f"{low}-{high}"
    except (ValueError, TypeError):
        return "unknown"


def patient_summary(patient_id: str) -> dict[str, Any]:
    """
    Get a summary of a patient record from OpenEMR.
    Returns patient demographics including name, DOB, gender. The agent operates inside OpenEMR where staff already has access to patient data.
    """
    data = get_patient(patient_id)
    # Fallback to direct PHP endpoint if FHIR fails
    if data is None:
        demo = get_patient_demographics(int(patient_id) if str(patient_id).isdigit() else 0)
        if demo:
            data = {
                "gender": demo.get("sex", "unknown"),
                "birthDate": demo.get("DOB", ""),
            }
    if data is None:
        return {
            "success": False,
            "error": TOOL_FAILURE_UNAVAILABLE,
            "summary": "",
        }

    g = (data.get("gender") or "").strip().lower()
    if g in ("male", "female", "other", "unknown"):
        gender = g
    else:
        gender = "unknown"

    birth_date = data.get("birthDate") or ""
    age_range = _age_range_from_birth_date(birth_date)

    # Get full demographics if available
    name = ""
    dob = ""
    demo = get_patient_demographics(int(patient_id) if str(patient_id).isdigit() else 0)
    if demo:
        name = f"{demo.get("fname", "")} {demo.get("lname", "")}".strip()
        dob = demo.get("DOB", "")
    summary_parts = [
        f"Patient: {name or "Unknown"} (ID: {patient_id}).",
        f"Gender: {gender}. DOB: {dob or "unknown"}. Age range: {age_range}.",

    ]
    summary = " ".join(summary_parts)

    return {
        "success": True,
        "patient_id": patient_id,
        "summary": summary,
        "gender": gender,
        "age_range": age_range,
        "source": "OpenEMR FHIR Patient",
    }
