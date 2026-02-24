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
