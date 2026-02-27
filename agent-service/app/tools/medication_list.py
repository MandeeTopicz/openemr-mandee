"""
CareTopicz Agent Service - Medication list tool.
Queries OpenEMR prescriptions via internal PHP endpoint.
"""
from typing import Any
from pydantic import BaseModel, Field
from app.clients.openemr import _module_url
from app.utils.response_templates import TOOL_FAILURE_UNAVAILABLE
import httpx

class MedicationListInput(BaseModel):
    patient_id: str = Field(..., description="Patient ID to look up medications for")
    include_discontinued: bool = Field(default=False, description="If true, include stopped medications")
    limit: int = Field(default=50, ge=1, le=100, description="Max number of medications to return")

def medication_list(patient_id: str, include_discontinued: bool = False, limit: int = 50) -> dict[str, Any]:
    url = _module_url("medications.php")
    params = {"patient_id": patient_id}
    if include_discontinued:
        params["include_discontinued"] = "1"
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
            if resp.status_code != 200:
                return {"success": False, "error": TOOL_FAILURE_UNAVAILABLE, "medications": []}
            data = resp.json()
            if not data.get("success"):
                return {"success": False, "error": data.get("error", TOOL_FAILURE_UNAVAILABLE), "medications": []}
            return data
    except Exception:
        return {"success": False, "error": TOOL_FAILURE_UNAVAILABLE, "medications": []}
