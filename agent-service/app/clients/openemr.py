"""
CareTopicz Agent Service - OpenEMR FHIR API client.

Queries Practitioner, PractitionerRole, Appointment, Coverage resources.
Requires Bearer token (OAuth2) for authenticated requests.
"""

from typing import Any

import httpx

from app.config import settings


def _get_client() -> httpx.Client:
    """HTTP client for OpenEMR FHIR with optional SSL verification."""
    return httpx.Client(
        timeout=15.0,
        verify=settings.openemr_fhir_verify_ssl,
        headers={
            "Accept": "application/fhir+json",
            "Content-Type": "application/fhir+json",
        },
    )


def fhir_get(
    resource: str,
    resource_id: str | None = None,
    params: dict[str, str | int] | None = None,
) -> dict[str, Any] | None:
    """
    GET a FHIR resource from OpenEMR.
    Returns parsed JSON or None on error.
    """
    token = settings.openemr_fhir_token
    if not token:
        return None

    base = settings.openemr_fhir_base_url.rstrip("/")
    url = f"{base}/{resource}"
    if resource_id:
        url = f"{url}/{resource_id}"

    headers = {"Authorization": f"Bearer {token}"}

    try:
        with _get_client() as client:
            resp = client.get(url, params=params or {}, headers=headers)
            if resp.status_code != 200:
                return None
            return resp.json()
    except (httpx.HTTPError, ValueError):
        return None


def search_practitioners(name: str | None = None) -> dict[str, Any] | None:
    """Search Practitioner resources. Optional name filter."""
    params: dict[str, str | int] = {}
    if name:
        params["name"] = name
    return fhir_get("Practitioner", params=params if params else None)


def search_practitioner_roles(
    practitioner: str | None = None,
    specialty: str | None = None,
) -> dict[str, Any] | None:
    """Search PractitionerRole resources by practitioner or specialty."""
    params: dict[str, str | int] = {}
    if practitioner:
        params["practitioner"] = practitioner
    if specialty:
        params["specialty"] = specialty
    return fhir_get("PractitionerRole", params=params if params else None)


def search_appointments(
    practitioner: str | None = None,
    patient: str | None = None,
    date: str | None = None,
    status: str = "booked",
) -> dict[str, Any] | None:
    """Search Appointment resources."""
    params: dict[str, str | int] = {"status": status}
    if practitioner:
        params["actor"] = practitioner
    if patient:
        params["patient"] = patient
    if date:
        params["date"] = date
    return fhir_get("Appointment", params=params)


def search_coverage(patient_id: str | None = None) -> dict[str, Any] | None:
    """Search Coverage resources, optionally by patient."""
    params: dict[str, str | int] = {}
    if patient_id:
        params["beneficiary"] = f"Patient/{patient_id}"
    return fhir_get("Coverage", params=params if params else None)


def get_patient(patient_id: str) -> dict[str, Any] | None:
    """Get a single Patient by ID."""
    return fhir_get("Patient", resource_id=patient_id)


def search_observations(
    patient_id: str | None = None,
    category: str | None = None,
    code: str | None = None,
    _count: int = 50,
) -> dict[str, Any] | None:
    """Search Observation resources (e.g. lab results)."""
    params: dict[str, str | int] = {"_count": _count}
    if patient_id:
        params["patient"] = patient_id
    if category:
        params["category"] = category
    if code:
        params["code"] = code
    return fhir_get("Observation", params=params)


def search_medication_requests(
    patient_id: str | None = None,
    status: str | None = None,
    _count: int = 100,
) -> dict[str, Any] | None:
    """Search MedicationRequest resources for a patient's medication list."""
    params: dict[str, str | int] = {"_count": _count}
    if patient_id:
        params["subject"] = f"Patient/{patient_id}"
    if status:
        params["status"] = status
    return fhir_get("MedicationRequest", params=params)


def _openemr_module_base() -> str:
    """Derive OpenEMR base URL from FHIR URL for module endpoints."""
    base = settings.openemr_fhir_base_url.rstrip("/")
    parts = base.split("/apis/")
    return parts[0] if parts else "http://openemr"


def _module_url(path: str) -> str:
    """Build URL for mod-ai-agent public PHP endpoints."""
    base = _openemr_module_base()
    return f"{base}/interface/modules/custom_modules/mod-ai-agent/public/{path}"


def search_providers_direct(name: str | None = None) -> list[dict[str, Any]]:
    """
    Search OpenEMR providers via the internal PHP endpoint (bypasses FHIR/OAuth).
    Returns list of provider dicts or empty list on error.
    """
    url = _module_url("providers.php")
    params = {}
    if name:
        params["name"] = name
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
            if resp.status_code != 200:
                return []
            data = resp.json()
            return data.get("providers", [])
    except (httpx.HTTPError, ValueError):
        return []


def get_patient_demographics(patient_id: int) -> dict[str, Any] | None:
    """Fetch patient name, sex, DOB from OpenEMR."""
    url = _module_url("patient_info.php")
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params={"pid": patient_id})
            if resp.status_code != 200:
                return None
            data = resp.json()
            if not data.get("success"):
                return None
            return data.get("patient")
    except (httpx.HTTPError, ValueError):
        return None


def create_medication_schedule(
    patient_id: int,
    medication: str,
    patient_category: str,
    start_date: str,
    created_by: str = "agent",
    duration_months: int | None = None,
) -> dict[str, Any]:
    """Create a new medication compliance schedule."""
    url = _module_url("med_schedule.php")
    payload = {
        "patient_id": patient_id,
        "medication": medication,
        "patient_category": patient_category,
        "created_by": created_by,
        "start_date": start_date,
    }
    if duration_months is not None:
        payload["duration_months"] = duration_months
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, params={"action": "create_schedule"}, json=payload)
            return resp.json()
    except (httpx.HTTPError, ValueError):
        return {"success": False, "error": "Request failed"}


def get_medication_schedule(patient_id: int) -> dict[str, Any]:
    """Get active medication schedule for a patient."""
    url = _module_url("med_schedule.php")
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params={"action": "get_schedule", "patient_id": patient_id})
            return resp.json()
    except (httpx.HTTPError, ValueError):
        return {"success": False, "error": "Request failed"}


def complete_milestone(
    milestone_id: int,
    completed_by: str,
    completed_date: str,
    notes: str = "",
) -> dict[str, Any]:
    """Mark a milestone as completed."""
    url = _module_url("med_schedule.php")
    payload = {
        "milestone_id": milestone_id,
        "completed_by": completed_by,
        "completed_date": completed_date,
        "notes": notes,
    }
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, params={"action": "complete_milestone"}, json=payload)
            return resp.json()
    except (httpx.HTTPError, ValueError):
        return {"success": False, "error": "Request failed"}


def cancel_medication_schedule(schedule_id: int, reason: str, cancelled_by: str) -> dict[str, Any]:
    """Cancel a medication schedule."""
    url = _module_url("med_schedule.php")
    payload = {
        "schedule_id": schedule_id,
        "cancelled_reason": reason,
        "cancelled_by": cancelled_by,
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, params={"action": "cancel_schedule"}, json=payload)
            return resp.json()
    except (httpx.HTTPError, ValueError):
        return {"success": False, "error": "Request failed"}


def reschedule_milestone(milestone_id: int, new_due_date: str, rescheduled_by: str) -> dict[str, Any]:
    """Reschedule a milestone to a new date."""
    url = _module_url("med_schedule.php")
    payload = {
        "milestone_id": milestone_id,
        "new_due_date": new_due_date,
        "rescheduled_by": rescheduled_by,
    }
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, params={"action": "reschedule_milestone"}, json=payload)
            return resp.json()
    except (httpx.HTTPError, ValueError):
        return {"success": False, "error": "Request failed"}


def check_schedule_conflicts(schedule_id: int) -> dict[str, Any]:
    """Check for scheduling conflicts."""
    url = _module_url("med_schedule.php")
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params={"action": "check_conflicts", "schedule_id": schedule_id})
            return resp.json()
    except (httpx.HTTPError, ValueError):
        return {"success": False, "error": "Request failed"}


def get_dashboard_alerts() -> dict[str, Any]:
    """Get all active schedules with upcoming/overdue milestones."""
    url = _module_url("med_schedule.php")
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params={"action": "get_all_active"})
            return resp.json()
    except (httpx.HTTPError, ValueError):
        return {"success": False, "error": "Request failed"}


def extend_medication_schedule(
    schedule_id: int | None = None,
    patient_id: int | None = None,
    duration_months: int = 3,
) -> dict[str, Any]:
    """Extend an existing medication schedule by adding more monthly milestones."""
    url = _module_url("med_schedule.php")
    payload = {
        "duration_months": duration_months,
    }
    if schedule_id is not None:
        payload["schedule_id"] = schedule_id
    if patient_id is not None:
        payload["patient_id"] = patient_id
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, params={"action": "extend_schedule"}, json=payload)
            return resp.json()
    except (httpx.HTTPError, ValueError):
        return {"success": False, "error": "Request failed"}


def complete_treatment(
    schedule_id: int | None = None,
    patient_id: int | None = None,
    notes: str = "",
) -> dict[str, Any]:
    """Mark schedule as completing and add final pregnancy test for FCBP if applicable."""
    url = _module_url("med_schedule.php")
    payload: dict[str, Any] = {"notes": notes}
    if schedule_id is not None:
        payload["schedule_id"] = schedule_id
    if patient_id is not None:
        payload["patient_id"] = patient_id
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, params={"action": "complete_treatment"}, json=payload)
            return resp.json()
    except (httpx.HTTPError, ValueError):
        return {"success": False, "error": "Request failed"}


def discontinue_medication_schedule(
    schedule_id: int | None = None,
    patient_id: int | None = None,
    reason: str = "Discontinued",
    discontinued_by: str = "agent",
) -> dict[str, Any]:
    """Discontinue a medication schedule (stop early with reason)."""
    url = _module_url("med_schedule.php")
    payload = {
        "cancelled_reason": reason,
        "cancelled_by": discontinued_by,
    }
    if schedule_id is not None:
        payload["schedule_id"] = schedule_id
    if patient_id is not None:
        payload["patient_id"] = patient_id
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, params={"action": "discontinue_schedule"}, json=payload)
            return resp.json()
    except (httpx.HTTPError, ValueError):
        return {"success": False, "error": "Request failed"}


def pause_medication_schedule(
    schedule_id: int | None = None,
    patient_id: int | None = None,
    notes: str = "",
) -> dict[str, Any]:
    """Pause a medication schedule temporarily."""
    url = _module_url("med_schedule.php")
    payload: dict[str, Any] = {"notes": notes}
    if schedule_id is not None:
        payload["schedule_id"] = schedule_id
    if patient_id is not None:
        payload["patient_id"] = patient_id
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, params={"action": "pause_schedule"}, json=payload)
            return resp.json()
    except (httpx.HTTPError, ValueError):
        return {"success": False, "error": "Request failed"}


def resume_medication_schedule(
    schedule_id: int | None = None,
    patient_id: int | None = None,
) -> dict[str, Any]:
    """Resume a paused medication schedule and shift pending milestone dates forward."""
    url = _module_url("med_schedule.php")
    payload: dict[str, Any] = {}
    if schedule_id is not None:
        payload["schedule_id"] = schedule_id
    if patient_id is not None:
        payload["patient_id"] = patient_id
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, params={"action": "resume_schedule"}, json=payload)
            return resp.json()
    except (httpx.HTTPError, ValueError):
        return {"success": False, "error": "Request failed"}
