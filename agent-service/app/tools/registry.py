"""
CareTopicz Agent Service - Tool registration and schema export.

Registers tools for LangGraph agent and exports tool list.
"""

from langchain_core.tools import StructuredTool

def _tool_error_for_llm(error: str) -> str:
    """Return tool error string for LLM. Standard (user-facing) messages as-is; others prefixed with 'Error:'."""
    if not error:
        return "Unknown error."
    if error.startswith("I ") or "Could you clarify" in error:
        return error
    return f"Error: {error}"

from app.tools.appointment_check import (
    AppointmentCheckInput,
)
from app.tools.appointment_check import (
    appointment_check as _appointment_check,
)
from app.tools.drug_interaction import DrugInteractionInput, drug_interaction_check
from app.tools.insurance_coverage import (
    InsuranceCoverageInput,
)
from app.tools.insurance_coverage import (
    insurance_coverage as _insurance_coverage,
)
from app.tools.insurance_provider_search import (
    InsuranceProviderSearchInput,
    insurance_provider_search as _insurance_provider_search,
)
from app.tools.lab_results_lookup import LabResultsLookupInput
from app.tools.lab_results_lookup import lab_results_lookup as _lab_results_lookup
from app.tools.medication_list import MedicationListInput
from app.tools.medication_list import medication_list as _medication_list
from app.tools.patient_summary import PatientSummaryInput
from app.tools.patient_summary import patient_summary as _patient_summary
from app.tools.patient_education_generator import (
    PatientEducationInput,
    patient_education_generator as _patient_education_generator,
)
from app.tools.cancel_schedule import CancelScheduleInput
from app.tools.cancel_schedule import cancel_schedule as _cancel_schedule
from app.tools.med_schedule import MedicationScheduleInput
from app.tools.med_schedule import medication_schedule as _medication_schedule
from app.tools.provider_search import ProviderSearchInput
from app.tools.provider_search import provider_search as _provider_search
from app.tools.scheduling import SchedulingInput
from app.tools.scheduling import scheduling as _scheduling
from app.tools.symptom_lookup import SymptomLookupInput
from app.tools.symptom_lookup import symptom_lookup as _symptom_lookup


def _format_interaction_result(data: dict) -> str:
    """Format tool result as readable text for the LLM."""
    if not data.get("success"):
        return _tool_error_for_llm(data.get("error", "Unknown error"))
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
        return _tool_error_for_llm(data.get("error", "Unknown error"))
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
        return _tool_error_for_llm(data.get("error", "Unknown error"))
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


def _format_insurance_provider_search_result(data: dict) -> str:
    if not data.get("success"):
        return _tool_error_for_llm(data.get("error", "Unknown error"))
    providers = data.get("providers", [])
    note = data.get("insurance_note", "")
    if not providers:
        return (
            f"No providers found for {data.get('specialty') or 'any specialty'} "
            f"in {data.get('location') or 'any location'}.\n\n{note}"
        )
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
    return (
        f"Insurance: {data.get('insurance_plan', '')}. "
        f"Providers found:\n" + "\n".join(lines) + f"\n\n{note}"
    )


def _run_insurance_provider_search(
    insurance_plan: str,
    specialty: str = "",
    location: str = "",
    limit: int = 10,
) -> str:
    result = _insurance_provider_search(
        insurance_plan=insurance_plan,
        specialty=specialty,
        location=location,
        limit=limit,
    )
    return _format_insurance_provider_search_result(result)


def _build_insurance_provider_search_tool() -> StructuredTool:
    return StructuredTool.from_function(
        func=_run_insurance_provider_search,
        name="insurance_provider_search",
        description="Find providers by specialty and location who may accept a given insurance. Use when the user asks which providers accept an insurance (e.g. Medicare, Aetna, Blue Cross) or 'find a cardiologist that takes X'. Input: insurance_plan (required), optional specialty, optional location, optional limit.",
        args_schema=InsuranceProviderSearchInput,
    )


def _format_appointment_result(data: dict) -> str:
    if not data.get("success"):
        return _tool_error_for_llm(data.get("error", "Unknown error"))
    appointments = data.get("appointments", [])
    if not appointments:
        return "No appointments found."
    lines = []
    for a in appointments:
        date = a.get('date', '')
        start = a.get('start_time', a.get('start', ''))
        end = a.get('end_time', a.get('end', ''))
        title = a.get('title', a.get('description', 'Appointment'))
        provider = a.get('provider_name', '')
        patient = a.get('patient_name', '')
        line = f"- {date} {start}-{end}: {title}"
        if provider:
            line += f" with {provider}"
        if patient:
            line += f" (patient: {patient})"
        line += f" (status: {a.get('status', '')})"
        lines.append(line)
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
        return _tool_error_for_llm(data.get("error", "Unknown error"))
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


def _format_patient_summary_result(data: dict) -> str:
    if not data.get("success"):
        return _tool_error_for_llm(data.get("error", "Unknown error"))
    return data.get("summary", "No summary.") + f"\n\nSource: {data.get('source', '')}"


def _run_patient_summary(patient_id: str) -> str:
    result = _patient_summary(patient_id=patient_id)
    return _format_patient_summary_result(result)


def _build_patient_summary_tool() -> StructuredTool:
    return StructuredTool.from_function(
        func=_run_patient_summary,
        name="patient_summary",
        description="Get a brief, privacy-safe summary of a patient record from OpenEMR. Use when the user asks about a patient overview or demographics (no PII returned). Input: patient_id (required).",
        args_schema=PatientSummaryInput,
    )


def _format_lab_results_result(data: dict) -> str:
    if not data.get("success"):
        return _tool_error_for_llm(data.get("error", "Unknown error"))
    results = data.get("results", [])
    if not results:
        return f"No lab results found for patient {data.get('patient_id', '')}.\nSource: {data.get('source', '')}"
    lines = [f"- {r['code']}: {r['value']} (date: {r['date']}, status: {r['status']})" for r in results]
    return "Lab results:\n" + "\n".join(lines) + f"\n\nSource: {data.get('source', '')}"


def _run_lab_results_lookup(patient_id: str, code: str | None = None, limit: int = 20) -> str:
    result = _lab_results_lookup(patient_id=patient_id, code=code, limit=limit)
    return _format_lab_results_result(result)


def _build_lab_results_lookup_tool() -> StructuredTool:
    return StructuredTool.from_function(
        func=_run_lab_results_lookup,
        name="lab_results_lookup",
        description="Look up laboratory results for a patient from OpenEMR. Use when the user asks about labs, test results, or specific values (e.g. glucose, hemoglobin). Input: patient_id (required), optional code filter, optional limit.",
        args_schema=LabResultsLookupInput,
    )


def _format_medication_list_result(data: dict) -> str:
    if not data.get("success"):
        return _tool_error_for_llm(data.get("error", "Unknown error"))
    meds = data.get("medications", [])
    if not meds:
        return f"No medications found for patient {data.get('patient_id', '')}.\nSource: {data.get('source', '')}"
    lines = [f"- {m['name']}: {m['dose']} (status: {m['status']})" for m in meds]
    return "Medications:\n" + "\n".join(lines) + f"\n\nSource: {data.get('source', '')}"


def _run_medication_list(
    patient_id: str,
    include_discontinued: bool = False,
    limit: int = 50,
) -> str:
    result = _medication_list(
        patient_id=patient_id,
        include_discontinued=include_discontinued,
        limit=limit,
    )
    return _format_medication_list_result(result)


def _build_medication_list_tool() -> StructuredTool:
    return StructuredTool.from_function(
        func=_run_medication_list,
        name="medication_list",
        description="Get current medication list for a patient from OpenEMR. Use when the user asks about medications, current drugs, or what a patient is taking. Input: patient_id (required), optional include_discontinued, optional limit.",
        args_schema=MedicationListInput,
    )


def _format_patient_education_result(data: dict) -> str:
    """Format patient education template for LLM to generate handout content."""
    if not data.get("success"):
        return _tool_error_for_llm(data.get("error", "Unknown error"))
    parts = [
        data.get("instructions", ""),
        "Sections to include: " + "; ".join(data.get("required_sections", [])),
        data.get("format_note", ""),
    ]
    return "\n\n".join(parts)


def _run_patient_education_generator(
    condition: str,
    reading_level: str = "general",
    language: str = "English",
) -> str:
    result = _patient_education_generator(
        condition=condition,
        reading_level=reading_level,
        language=language,
    )
    return _format_patient_education_result(result)


def _build_patient_education_generator_tool() -> StructuredTool:
    return StructuredTool.from_function(
        func=_run_patient_education_generator,
        name="patient_education_generator",
        description="Generate a structured patient education handout for a condition or topic. Use when the user asks for a handout, take-home sheet, or patient education document. Input: condition (required), optional reading_level (simple/general/detailed), optional language.",
        args_schema=PatientEducationInput,
    )


def _format_medication_schedule_result(data: dict) -> str:
    """Format medication schedule result for LLM."""
    if not data.get("success"):
        return _tool_error_for_llm(data.get("error", "Unknown error"))
    if data.get("_formatted"):
        return data["_formatted"]
    from app.tools.med_schedule import _format_schedule_status

    sched = data.get("schedule")
    pid = sched.get("patient_id") if sched else None
    return _format_schedule_status(data, int(pid) if pid else None)


def _run_medication_schedule(
    action: str,
    patient_id: int | None = None,
    medication: str | None = None,
    patient_category: str | None = None,
    milestone_id: int | None = None,
    completed_date: str | None = None,
    new_due_date: str | None = None,
    schedule_id: int | None = None,
    reason: str | None = None,
    notes: str | None = None,
    start_date: str | None = None,
    created_by: str = "agent",
    duration_months: int | None = None,
) -> str:
    result = _medication_schedule(
        action=action,
        patient_id=patient_id,
        medication=medication,
        patient_category=patient_category,
        milestone_id=milestone_id,
        completed_date=completed_date,
        new_due_date=new_due_date,
        schedule_id=schedule_id,
        reason=reason,
        notes=notes,
        start_date=start_date,
        created_by=created_by,
        duration_months=duration_months,
    )
    return _format_medication_schedule_result(result)


def _build_medication_schedule_tool() -> StructuredTool:
    return StructuredTool.from_function(
        func=_run_medication_schedule,
        name="medication_schedule",
        description="Manage regulated medication schedules (iPLEDGE/isotretinoin, biologics, REMS). Create compliance schedules, check status, complete milestones, detect conflicts. Use for isotretinoin/Accutane, Humira/adalimumab, and similar protocols.",
        args_schema=MedicationScheduleInput,
    )


def _format_scheduling_result(data: dict) -> str:
    """Format scheduling result for LLM."""
    if not data.get("success"):
        return _tool_error_for_llm(data.get("error", "Unknown error"))
    if "providers" in data:
        providers = data["providers"]
        if not providers:
            return "No providers found."
        lines = [f"- {p.get('fname', '')} {p.get('lname', '')} (id: {p.get('id')}, specialty: {p.get('specialty', 'General')})" for p in providers]
        return "Providers:\n" + "\n".join(lines)
    if "slots" in data:
        slots = data["slots"]
        if not slots:
            return "No available slots found."
        lines = [f"- {s['date']} at {s['start_time']}" for s in slots]
        return "Available slots:\n" + "\n".join(lines)
    if "pc_eid" in data:
        return f"Appointment booked successfully. pc_eid: {data['pc_eid']}"
    return "Done."


def _run_scheduling(
    action: str,
    provider_id: int | None = None,
    patient_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    time_preference: str | None = None,
    date: str | None = None,
    start_time: str | None = None,
    title: str = "Office Visit",
) -> str:
    result = _scheduling(
        action=action,
        provider_id=provider_id,
        patient_id=patient_id,
        start_date=start_date,
        end_date=end_date,
        time_preference=time_preference,
        date=date,
        start_time=start_time,
        title=title,
    )
    return _format_scheduling_result(result)


def _build_scheduling_tool() -> StructuredTool:
    return StructuredTool.from_function(
        func=_run_scheduling,
        name="scheduling",
        description="List providers, check appointment availability, and book appointments in OpenEMR calendar.",
        args_schema=SchedulingInput,
    )


def get_tools() -> list[StructuredTool]:
    """Return list of tools for the agent."""
    return [
        _build_drug_interaction_tool(),
        _build_symptom_lookup_tool(),
        _build_medication_schedule_tool(),
        _build_scheduling_tool(),
        _build_provider_search_tool(),
        _build_insurance_provider_search_tool(),
        _build_appointment_check_tool(),
        _build_insurance_coverage_tool(),
        _build_patient_summary_tool(),
        _build_lab_results_lookup_tool(),
        _build_medication_list_tool(),
        _build_patient_education_generator_tool(),
    ]
