"""
CareTopicz Agent Service - Patient summary tool.

Retrieves a brief, non-PII summary of a patient record from OpenEMR FHIR.
Output excludes name, DOB, SSN, MRN to avoid sending PII to the LLM.
"""

from typing import Any

from pydantic import BaseModel, Field

from app.clients.openemr import get_patient


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
    Get a brief, privacy-safe summary of a patient record from OpenEMR.
    Returns only non-PII (e.g. gender, age range). No name, DOB, SSN, or MRN.
    """
    data = get_patient(patient_id)
    if data is None:
        return {
            "success": False,
            "error": "OpenEMR FHIR not configured or patient not found. Set OPENEMR_FHIR_TOKEN.",
            "summary": "",
        }

    g = (data.get("gender") or "").strip().lower()
    if g in ("male", "female", "other", "unknown"):
        gender = g
    else:
        gender = "unknown"

    birth_date = data.get("birthDate") or ""
    age_range = _age_range_from_birth_date(birth_date)

    summary_parts = [
        f"Patient record found (ID: {patient_id}).",
        f"Gender: {gender}. Age range: {age_range}.",
        "No name or identifiers included per privacy.",
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
