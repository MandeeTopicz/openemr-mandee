"""
CareTopicz Agent Service - Lab results lookup tool.

Queries OpenEMR FHIR Observation (laboratory) resources for a patient.
"""

from typing import Any

from pydantic import BaseModel, Field

from app.clients.openemr import search_observations


class LabResultsLookupInput(BaseModel):
    """Input schema for lab_results_lookup."""

    patient_id: str = Field(..., description="Patient ID to look up lab results for")
    code: str | None = Field(
        default=None,
        description="Optional LOINC or code filter (e.g. 'glucose', 'hemoglobin')",
    )
    limit: int = Field(default=20, ge=1, le=100, description="Max number of results to return")


def lab_results_lookup(
    patient_id: str,
    code: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """
    Look up laboratory results for a patient from OpenEMR.
    Requires OpenEMR FHIR token to be configured.
    """
    data = search_observations(
        patient_id=patient_id,
        category="laboratory",
        code=code,
        _count=limit,
    )
    if data is None:
        return {
            "success": False,
            "error": "OpenEMR FHIR not configured or unavailable. Set OPENEMR_FHIR_TOKEN.",
            "results": [],
        }

    results: list[dict[str, Any]] = []
    entries = data.get("entry") or []
    for e in entries:
        res = e.get("resource", {})
        code_text = ""
        for c in res.get("code", {}).get("coding", []):
            code_text = c.get("display") or c.get("code") or ""
            if code_text:
                break
        value = res.get("valueQuantity", {})
        value_str = value.get("value")
        unit = value.get("unit") or ""
        if value_str is not None:
            value_display = f"{value_str} {unit}".strip()
        else:
            value_display = res.get("valueString") or res.get("valueCode") or "—"
        effective = res.get("effectiveDateTime") or res.get("issued") or ""
        results.append({
            "code": code_text or "unknown",
            "value": value_display,
            "date": effective[:10] if effective else "",
            "status": res.get("status", "unknown"),
        })

    return {
        "success": True,
        "patient_id": patient_id,
        "results": results,
        "count": len(results),
        "source": "OpenEMR FHIR Observation (laboratory)",
    }
