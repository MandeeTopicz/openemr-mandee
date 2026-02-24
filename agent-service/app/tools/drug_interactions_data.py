"""
CareTopicz Agent Service - Curated drug interaction data for MVP.

RxNorm interaction API was discontinued Jan 2024. This dataset provides
known major/moderate interactions for demo. Production would use DrugBank or FDA.
Source: Clinical reference, based on common high-priority interactions.
"""

from dataclasses import dataclass


@dataclass
class Interaction:
    severity: str  # "major" | "moderate" | "minor"
    description: str
    source: str = "Clinical reference (MVP - RxNorm interaction API discontinued)"


def _normalize(name: str) -> str:
    return name.strip().lower()


# (drug1, drug2) -> Interaction (order-independent)
_INTERACTIONS: dict[tuple[str, str], Interaction] = {}

def _add(a: str, b: str, sev: str, desc: str):
    key = tuple(sorted([_normalize(a), _normalize(b)]))
    _INTERACTIONS[key] = Interaction(severity=sev, description=desc)


_add("lisinopril", "ibuprofen", "moderate",
     "ACE inhibitors + NSAIDs can reduce antihypertensive effect and increase risk of kidney impairment.")
_add("lisinopril", "potassium", "major",
     "ACE inhibitors + potassium can cause hyperkalemia. Monitor potassium levels.")
_add("lisinopril", "potassium chloride", "major",
     "ACE inhibitors + potassium can cause hyperkalemia. Monitor potassium levels.")
_add("lisinopril", "spironolactone", "major",
     "ACE inhibitors + potassium-sparing diuretics increase hyperkalemia risk.")
_add("lisinopril", "trimethoprim", "moderate",
     "ACE inhibitors + trimethoprim may increase hyperkalemia risk.")

_add("warfarin", "aspirin", "major",
     "Warfarin + aspirin increases bleeding risk. Often used together but requires careful monitoring.")
_add("warfarin", "ibuprofen", "major",
     "Warfarin + NSAIDs increase bleeding risk. Avoid or use with caution.")
_add("warfarin", "naproxen", "major",
     "Warfarin + NSAIDs increase bleeding risk.")

_add("metformin", "contrast", "major",
     "Metformin + iodinated contrast may increase lactic acidosis risk. Hold metformin per protocol.")
_add("metformin", "alcohol", "moderate",
     "Metformin + alcohol may increase lactic acidosis risk.")

_add("amoxicillin", "methotrexate", "major",
     "Penicillins can increase methotrexate toxicity. Monitor methotrexate levels.")

_add("fluoxetine", "tramadol", "major",
     "SSRIs + tramadol increase serotonin syndrome and seizure risk.")
_add("sertraline", "tramadol", "major",
     "SSRIs + tramadol increase serotonin syndrome and seizure risk.")


def check_interaction(drug1: str, drug2: str) -> Interaction | None:
    """Check for known interaction between two drugs (by name). Returns None if none."""
    key = tuple(sorted([_normalize(drug1), _normalize(drug2)]))
    return _INTERACTIONS.get(key)


def get_all_interactions_for_drug(drug_name: str) -> list[tuple[str, Interaction]]:
    """Get all known interactions for a drug. Returns list of (other_drug, interaction)."""
    norm = _normalize(drug_name)
    result: list[tuple[str, Interaction]] = []
    for (a, b), interaction in _INTERACTIONS.items():
        if a == norm:
            result.append((b, interaction))
        elif b == norm:
            result.append((a, interaction))
    return result
