"""
CareTopicz Agent Service - Appointment check tool.
Queries OpenEMR calendar via PHP endpoint.
"""
from typing import Any
import httpx
from pydantic import BaseModel, Field
from app.clients.openemr import _module_url

class AppointmentCheckInput(BaseModel):
    patient_id: str | None = Field(default=None, description="Patient ID to check appointments for")
    practitioner_id: str | None = Field(default=None, description="Provider ID to check appointments for")
    date: str | None = Field(default=None, description="Date to check (YYYY-MM-DD). If omitted, returns all future appointments.")

def appointment_check(patient_id=None, practitioner_id=None, date=None) -> dict[str, Any]:
    """Check appointments from OpenEMR calendar."""
    try:
        url = _module_url("appointments.php")
        params = {"action": "list_appointments"}
        if patient_id:
            params["patient_id"] = str(patient_id)
        if practitioner_id:
            params["provider_id"] = str(practitioner_id)
        if date:
            params["date"] = date
        resp = httpx.get(url, params=params, timeout=10, verify=False)
        data = resp.json()
        if not data.get("success"):
            return {"success": False, "error": data.get("error", "Failed"), "appointments": []}
        return {"success": True, "appointments": data.get("appointments", []), "count": data.get("count", 0), "source": "OpenEMR Calendar"}
    except Exception as e:
        return {"success": False, "error": str(e), "appointments": []}
