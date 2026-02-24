"""
CareTopicz Agent Service - Appointment availability check tool.

Queries OpenEMR FHIR Appointment resource for availability.
"""

from typing import Any

from pydantic import BaseModel, Field

from app.clients.openemr import search_appointments


class AppointmentCheckInput(BaseModel):
    """Input schema for appointment_check."""

    practitioner_id: str | None = Field(
        default=None,
        description="Practitioner ID or reference (e.g. Practitioner/5) to check availability",
    )
    patient_id: str | None = Field(
        default=None,
        description="Patient ID to check appointments for",
    )
    date: str | None = Field(
        default=None,
        description="Date to check (YYYY-MM-DD). If omitted, returns booked appointments.",
    )


def appointment_check(
    practitioner_id: str | None = None,
    patient_id: str | None = None,
    date: str | None = None,
) -> dict[str, Any]:
    """
    Check appointment availability or list appointments from OpenEMR.
    Requires OpenEMR FHIR token to be configured.
    """
    data = search_appointments(
        practitioner=practitioner_id,
        patient=patient_id,
        date=date,
        status="booked",
    )
    if data is None:
        return {
            "success": False,
            "error": "OpenEMR FHIR not configured or unavailable. Set OPENEMR_FHIR_TOKEN.",
            "appointments": [],
        }

    appointments: list[dict[str, Any]] = []
    entries = data.get("entry") or []
    for e in entries:
        res = e.get("resource", {})
        start = ""
        for ext in res.get("extension", []):
            if ext.get("url", "").endswith("start"):
                start = ext.get("valueDateTime", "")
                break
        start = start or res.get("start", "")
        end = res.get("end", "")
        status = res.get("status", "")
        desc = res.get("description", "")
        participants = res.get("participant", [])
        actor_ref = ""
        for p in participants:
            ref = p.get("actor", {}).get("reference", "")
            if ref:
                actor_ref = ref
                break
        appointments.append({
            "start": start,
            "end": end,
            "status": status,
            "description": desc or "Appointment",
            "actor": actor_ref,
        })

    return {
        "success": True,
        "appointments": appointments,
        "count": len(appointments),
        "source": "OpenEMR FHIR Appointment",
    }
