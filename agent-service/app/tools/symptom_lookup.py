"""
CareTopicz Agent Service - Symptom lookup tool.

Maps symptoms to possible conditions with urgency levels.
Never presents as diagnosis — always "possible conditions to consider."
"""

from typing import Any

from pydantic import BaseModel, Field

from app.tools.symptom_data import lookup_symptom, search_symptoms

SOURCE = "Clinical reference (MVP - curated symptom mapping)"


class SymptomLookupInput(BaseModel):
    """Input schema for symptom_lookup."""

    symptom: str = Field(
        ...,
        description="Symptom or symptom description to look up (e.g. chest pain, headache, fever)",
        min_length=1,
    )


def symptom_lookup(symptom: str) -> dict[str, Any]:
    """
    Look up possible conditions for a symptom.
    Returns conditions with urgency and notes. Never presents as diagnosis.
    """
    symptom = symptom.strip()
    if not symptom:
        return {
            "success": False,
            "error": "Symptom is required",
            "conditions": [],
            "source": SOURCE,
        }

    # Try exact match first
    results = lookup_symptom(symptom)
    if not results:
        # Try partial search
        matches = search_symptoms(symptom)
        if matches:
            results = []
            for sym, data in matches:
                results.extend(data)
        else:
            return {
                "success": True,
                "symptom": symptom,
                "conditions": [],
                "note": "No matching symptom data found. This tool has limited coverage. Recommend professional evaluation for any concerning symptoms.",
                "source": SOURCE,
            }

    conditions = [
        {
            "condition": r.condition,
            "urgency": r.urgency,
            "notes": r.notes,
        }
        for r in results
    ]

    # Sort by urgency: emergency first, then urgent, routine, self_care
    urgency_order = {"emergency": 0, "urgent": 1, "routine": 2, "self_care": 3}
    conditions.sort(key=lambda c: urgency_order.get(c["urgency"], 4))

    return {
        "success": True,
        "symptom": symptom,
        "conditions": conditions,
        "disclaimer": "These are possible conditions to consider, not a diagnosis. Always consult a healthcare provider for medical advice.",
        "source": SOURCE,
    }
