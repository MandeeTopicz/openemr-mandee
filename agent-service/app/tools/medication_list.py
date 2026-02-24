"""
CareTopicz Agent Service - Medication list tool.

Queries OpenEMR FHIR MedicationRequest for a patient's current medications.
"""

from typing import Any

from pydantic import BaseModel, Field

from app.clients.openemr import search_medication_requests


class MedicationListInput(BaseModel):
    """Input schema for medication_list."""

    patient_id: str = Field(..., description="Patient ID to look up medications for")
    include_discontinued: bool = Field(
        default=False,
        description="If true, include stopped/cancelled medications",
    )
    limit: int = Field(default=50, ge=1, le=100, description="Max number of medications to return")


def medication_list(
    patient_id: str,
    include_discontinued: bool = False,
    limit: int = 50,
) -> dict[str, Any]:
    """
    Get current medication list for a patient from OpenEMR.
    Requires OpenEMR FHIR token to be configured.
    """
    status = None if include_discontinued else "active"
    data = search_medication_requests(patient_id=patient_id, status=status, _count=limit)
    if data is None:
        return {
            "success": False,
            "error": "OpenEMR FHIR not configured or unavailable. Set OPENEMR_FHIR_TOKEN.",
            "medications": [],
        }

    medications: list[dict[str, Any]] = []
    entries = data.get("entry") or []
    for e in entries:
        res = e.get("resource", {})
        med = res.get("medicationCodeableConcept", {})
        name = ""
        for c in med.get("coding", []):
            name = c.get("display") or c.get("text") or c.get("code") or ""
            if name:
                break
        if not name:
            name = med.get("text") or "Unknown medication"
        status_val = res.get("status", "unknown")
        intent = res.get("intent", "")
        dosage_instruction = (res.get("dosageInstruction") or [{}])[0]
        dose = dosage_instruction.get("doseAndRate", [{}])[0].get("doseQuantity", {})
        dose_text = ""
        if dose:
            val = dose.get("value")
            unit = dose.get("unit", "")
            if val is not None:
                dose_text = f"{val} {unit}".strip()
        medications.append({
            "name": name,
            "status": status_val,
            "intent": intent or "order",
            "dose": dose_text or "—",
        })

    return {
        "success": True,
        "patient_id": patient_id,
        "medications": medications,
        "count": len(medications),
        "source": "OpenEMR FHIR MedicationRequest",
    }
