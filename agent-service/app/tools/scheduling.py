"""
CareTopicz Agent Service - Appointment scheduling tool.

List providers, check available slots, and book appointments in OpenEMR.
"""

from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from app.clients.openemr import _module_url


class SchedulingInput(BaseModel):
    """Input schema for scheduling tool."""

    action: Literal["list_providers", "available_slots", "book_appointment"] = Field(
        ...,
        description="Action: list_providers, available_slots, or book_appointment",
    )
    provider_id: int | None = Field(default=None, description="Provider ID (required for available_slots, book_appointment)")
    patient_id: int | None = Field(default=None, description="Patient ID (required for book_appointment)")
    start_date: str | None = Field(default=None, description="Start date YYYY-MM-DD (for available_slots)")
    end_date: str | None = Field(default=None, description="End date YYYY-MM-DD (for available_slots)")
    time_preference: Literal["morning", "afternoon", "late_morning"] | None = Field(
        default=None,
        description="morning (9–11:30), late_morning (11–1), afternoon (1–5) (optional for available_slots)",
    )
    date: str | None = Field(default=None, description="Appointment date YYYY-MM-DD (for book_appointment)")
    start_time: str | None = Field(default=None, description="Appointment start time HH:MM or HH:MM:SS (for book_appointment)")
    title: str | None = Field(default="Office Visit", description="Appointment title (for book_appointment)")


def scheduling(
    action: str,
    provider_id: int | None = None,
    patient_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    time_preference: str | None = None,
    date: str | None = None,
    start_time: str | None = None,
    title: str = "Office Visit",
) -> dict[str, Any]:
    """Dispatch scheduling actions to appointments.php."""
    url = _module_url("appointments.php")

    if action == "list_providers":
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, params={"action": "list_providers"})
                if resp.status_code != 200:
                    return {"success": False, "error": "Request failed"}
                return resp.json()
        except (httpx.HTTPError, ValueError):
            return {"success": False, "error": "Request failed"}

    if action == "available_slots":
        if provider_id is None or not start_date or not end_date:
            return {"success": False, "error": "provider_id, start_date, end_date required"}
        params: dict[str, Any] = {
            "action": "available_slots",
            "provider_id": provider_id,
            "start_date": start_date,
            "end_date": end_date,
        }
        if time_preference:
            params["time_preference"] = time_preference
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, params=params)
                if resp.status_code != 200:
                    return {"success": False, "error": "Request failed"}
                return resp.json()
        except (httpx.HTTPError, ValueError):
            return {"success": False, "error": "Request failed"}

    if action == "book_appointment":
        if provider_id is None or patient_id is None or not date or not start_time:
            return {"success": False, "error": "provider_id, patient_id, date, start_time required"}
        payload = {
            "action": "book_appointment",
            "provider_id": provider_id,
            "patient_id": patient_id,
            "date": date,
            "start_time": start_time,
            "title": title,
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, params={"action": "book_appointment"}, data=payload)
                if resp.status_code != 200:
                    return {"success": False, "error": "Request failed"}
                return resp.json()
        except (httpx.HTTPError, ValueError):
            return {"success": False, "error": "Request failed"}

    return {"success": False, "error": f"Unknown action: {action}"}
