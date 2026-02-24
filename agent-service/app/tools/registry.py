"""
CareTopicz Agent Service - Tool registration and schema export.

Registers tools for LangGraph agent and exports tool list.
"""

from langchain_core.tools import StructuredTool

from app.tools.appointment_check import (
    AppointmentCheckInput,
    appointment_check as _appointment_check,
)
from app.tools.drug_interaction import DrugInteractionInput, drug_interaction_check
from app.tools.insurance_coverage import (
    InsuranceCoverageInput,
    insurance_coverage as _insurance_coverage,
)
from app.tools.provider_search import ProviderSearchInput, provider_search as _provider_search
from app.tools.symptom_lookup import SymptomLookupInput, symptom_lookup as _symptom_lookup


def _format_interaction_result(data: dict) -> str:
    """Format tool result as readable text for the LLM."""
    if not data.get("success"):
        return f"Error: {data.get('error', 'Unknown error')}"
    interactions = data.get("interactions", [])
    if not interactions:
        drugs = data.get("drugs_checked", list(data.get("drugs_resolved", {}).keys()) or ["?"])
        return (
            f"No known interactions found between {drugs}. "
            f"Source: {data.get('source', '')}"
        )
    lines = []
    for i in interactions:
        lines.append(
            f"- {i['drug1']} + {i['drug2']}: [{i['severity']}] {i['description']} (Source: {i.get('source', '')})"
        )
    return "Drug interactions found:\n" + "\n".join(lines) + f"\n\nSource: {data.get('source', '')}"


def _run_drug_interaction_check(drug_names: list[str]) -> str:
    """Wrapper that returns string for LLM consumption."""
    result = drug_interaction_check(drug_names)
    return _format_interaction_result(result)


def _build_drug_interaction_tool() -> StructuredTool:
    """Build drug_interaction_check as a LangChain tool."""
    return StructuredTool.from_function(
        func=_run_drug_interaction_check,
        name="drug_interaction_check",
        description="Check for interactions between two or more medications. Use when the user asks about drug interactions, medication combinations, or compatibility. Input: list of 2+ drug names (generic or brand), e.g. ['lisinopril', 'ibuprofen'].",
        args_schema=DrugInteractionInput,
    )


def _format_symptom_result(data: dict) -> str:
    if not data.get("success"):
        return f"Error: {data.get('error', 'Unknown error')}"
    conditions = data.get("conditions", [])
    if not conditions:
        return data.get("note", "No matching symptom data found.") + f"\nSource: {data.get('source', '')}"
    lines = []
    for c in conditions:
        lines.append(f"- {c['condition']} [{c['urgency']}]: {c['notes']}")
    out = f"Symptom: {data.get('symptom', '')}\nPossible conditions:\n" + "\n".join(lines)
    if data.get("disclaimer"):
        out += f"\n\n{data['disclaimer']}"
    return out + f"\n\nSource: {data.get('source', '')}"


def _run_symptom_lookup(symptom: str) -> str:
    result = _symptom_lookup(symptom)
    return _format_symptom_result(result)


def _build_symptom_lookup_tool() -> StructuredTool:
    return StructuredTool.from_function(
        func=_run_symptom_lookup,
        name="symptom_lookup",
        description="Look up possible conditions for a symptom. Use when the user describes symptoms and wants to understand possible causes or urgency. Never presents as diagnosis. Input: symptom description, e.g. 'chest pain', 'headache', 'fever'.",
        args_schema=SymptomLookupInput,
    )


def _format_provider_result(data: dict) -> str:
    if not data.get("success"):
        return f"Error: {data.get('error', 'Unknown error')}"
    providers = data.get("providers", [])
    if not providers:
        return f"No providers found for: {data.get('query', '')}"
    lines = []
    for p in providers:
        parts = [f"- {p.get('name', 'Unknown')}"]
        if p.get("npi"):
            parts.append(f"NPI: {p['npi']}")
        if p.get("specialty"):
            parts.append(f"Specialty: {p['specialty']}")
        if p.get("city") and p.get("state"):
            parts.append(f"Location: {p['city']}, {p['state']}")
        parts.append(f"(Source: {p.get('source', '')})")
        lines.append(" ".join(parts))
    return "Providers found:\n" + "\n".join(lines)


def _run_provider_search(query: str, limit: int = 10) -> str:
    result = _provider_search(query=query, limit=limit)
    return _format_provider_result(result)


def _build_provider_search_tool() -> StructuredTool:
    return StructuredTool.from_function(
        func=_run_provider_search,
        name="provider_search",
        description="Search for healthcare providers by name, specialty, or location. Use when the user wants to find a doctor, specialist, or provider. Input: search query (e.g. 'cardiologist Austin', 'Dr. Smith'), optional limit.",
        args_schema=ProviderSearchInput,
    )


def _format_appointment_result(data: dict) -> str:
    if not data.get("success"):
        return f"Error: {data.get('error', 'Unknown error')}"
    appointments = data.get("appointments", [])
    if not appointments:
        return "No appointments found."
    lines = []
    for a in appointments:
        lines.append(f"- {a.get('start', '')} to {a.get('end', '')}: {a.get('description', '')} (status: {a.get('status', '')})")
    return "Appointments:\n" + "\n".join(lines)


def _run_appointment_check(
    practitioner_id: str | None = None,
    patient_id: str | None = None,
    date: str | None = None,
) -> str:
    result = _appointment_check(
        practitioner_id=practitioner_id,
        patient_id=patient_id,
        date=date,
    )
    return _format_appointment_result(result)


def _build_appointment_check_tool() -> StructuredTool:
    return StructuredTool.from_function(
        func=_run_appointment_check,
        name="appointment_check",
        description="Check appointment availability or list appointments from OpenEMR. Use when the user asks about scheduling, availability, or appointments. Input: optional practitioner_id, patient_id, or date (YYYY-MM-DD).",
        args_schema=AppointmentCheckInput,
    )


def _format_insurance_result(data: dict) -> str:
    if not data.get("success"):
        return f"Error: {data.get('error', 'Unknown error')}"
    coverage = data.get("coverage", [])
    if not coverage:
        return f"No insurance coverage found for patient {data.get('patient_id', '') or 'N/A'}."
    lines = []
    for c in coverage:
        lines.append(f"- {c.get('payor', 'Unknown')}: {c.get('type', '')} (status: {c.get('status', '')})")
    return "Insurance coverage:\n" + "\n".join(lines)


def _run_insurance_coverage(patient_id: str | None = None) -> str:
    result = _insurance_coverage(patient_id=patient_id)
    return _format_insurance_result(result)


def _build_insurance_coverage_tool() -> StructuredTool:
    return StructuredTool.from_function(
        func=_run_insurance_coverage,
        name="insurance_coverage",
        description="Look up insurance coverage for a patient from OpenEMR. Use when the user asks about insurance, coverage verification, or benefits. Input: optional patient_id.",
        args_schema=InsuranceCoverageInput,
    )


def get_tools() -> list[StructuredTool]:
    """Return list of tools for the agent."""
    return [
        _build_drug_interaction_tool(),
        _build_symptom_lookup_tool(),
        _build_provider_search_tool(),
        _build_appointment_check_tool(),
        _build_insurance_coverage_tool(),
    ]
