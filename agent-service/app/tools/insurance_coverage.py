"""
CareTopicz Agent Service - Insurance coverage verification tool.

Queries OpenEMR FHIR Coverage resource.
"""

from typing import Any

from pydantic import BaseModel, Field

from app.clients.openemr import search_coverage
from app.utils.response_templates import TOOL_FAILURE_UNAVAILABLE


class InsuranceCoverageInput(BaseModel):
    """Input schema for insurance_coverage."""

    patient_id: str | None = Field(
        default=None,
        description="Patient ID to look up insurance for. If omitted, returns all coverage (system-level).",
    )


def insurance_coverage(patient_id: str | None = None) -> dict[str, Any]:
    """
    Look up insurance coverage for a patient from OpenEMR.
    Requires OpenEMR FHIR token to be configured.
    """
    data = search_coverage(patient_id=patient_id)
    if data is None:
        return {
            "success": False,
            "error": TOOL_FAILURE_UNAVAILABLE,
            "coverage": [],
        }

    coverages: list[dict[str, Any]] = []
    entries = data.get("entry") or []
    for e in entries:
        res = e.get("resource", {})
        status = res.get("status", "active")
        payor = res.get("payor", [{}])
        org = payor[0].get("display", "") if payor else ""
        type_code = ""
        for c in res.get("type", []):
            for coding in c.get("coding", []):
                type_code = coding.get("code", "") or coding.get("display", "")
                if type_code:
                    break
            if type_code:
                break
        coverages.append({
            "status": status,
            "payor": org,
            "type": type_code or "unknown",
        })

    return {
        "success": True,
        "patient_id": patient_id,
        "coverage": coverages,
        "count": len(coverages),
        "source": "OpenEMR FHIR Coverage",
    }
