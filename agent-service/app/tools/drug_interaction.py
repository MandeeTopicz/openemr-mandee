"""
CareTopicz Agent Service - Drug interaction check tool.

Uses RxNorm for drug resolution and curated interaction data (MVP).
Production would use DrugBank or FDA API.
"""

from typing import Any

from pydantic import BaseModel, Field

from app.clients.rxnorm import resolve_rxcui, resolve_rxcuis
from app.tools.drug_interactions_data import check_interaction, get_all_interactions_for_drug
from app.utils.response_templates import format_ambiguous_input

SOURCE = "RxNorm (drug ID) + Clinical reference (interactions)"


class DrugInteractionInput(BaseModel):
    """Input schema for drug_interaction_check."""

    drug_names: list[str] = Field(
        ...,
        description="List of 2+ drug names (brand or generic) to check for interactions",
        min_length=2,
    )


def drug_interaction_check(drug_names: list[str]) -> dict[str, Any]:
    """
    Check for interactions between medications.
    Uses RxNorm for drug identification and authoritative interaction data.
    """
    if len(drug_names) < 2:
        return {
            "success": False,
            "error": format_ambiguous_input("which two or more medications you want to check for interactions"),
            "interactions": [],
            "source": SOURCE,
        }

    resolved = resolve_rxcuis(drug_names)
    interactions_found: list[dict[str, Any]] = []

    for i, drug_a in enumerate(drug_names):
        for drug_b in drug_names[i + 1 :]:
            interaction = check_interaction(drug_a, drug_b)
            if interaction:
                interactions_found.append({
                    "drug1": drug_a,
                    "drug2": drug_b,
                    "rxcui1": resolved.get(drug_a),
                    "rxcui2": resolved.get(drug_b),
                    "severity": interaction.severity,
                    "description": interaction.description,
                    "source": interaction.source,
                })

    result = {
        "success": True,
        "drugs_checked": drug_names,
        "drugs_resolved": resolved,
        "interactions": interactions_found,
        "source": SOURCE,
    }

    return result


# For single-drug lookup (e.g. "what interacts with lisinopril?")
def drug_interaction_lookup(drug_name: str) -> dict[str, Any]:
    """Get known interactions for a single drug."""
    rxcui = resolve_rxcui(drug_name)
    known = get_all_interactions_for_drug(drug_name)

    interactions = [
        {
            "drug": drug_name,
            "interacts_with": other,
            "severity": i.severity,
            "description": i.description,
            "source": i.source,
        }
        for other, i in known
    ]

    return {
        "success": True,
        "drug": drug_name,
        "rxcui": rxcui,
        "interactions": interactions,
        "source": SOURCE,
    }
