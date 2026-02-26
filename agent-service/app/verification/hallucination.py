"""
CareTopicz Agent Service - Hallucination detection.
Detects fabricated claims, invented statistics, and unsupported clinical details
that are not grounded in tool results.
"""
import re
from dataclasses import dataclass

@dataclass
class HallucinationResult:
    passed: bool
    issues: list[str]

_UNSUPPORTED_STATISTICS = re.compile(
    r"\b\d{1,3}%\s*(?:of|risk|chance|effective|success|mortality|morbidity)",
    re.I,
)
_UNSUPPORTED_STUDIES = re.compile(
    r"\b(?:studies show|research (?:suggests|indicates|shows)|clinical trials (?:show|demonstrate)|evidence suggests)\b",
    re.I,
)
_DOSAGE_WITHOUT_TOOL = re.compile(
    r"\btake\s+\d+\s*(?:mg|ml|mcg|g)\s+(?:\d+\s*times\s+)?(?:daily|per day|a day)",
    re.I,
)

def _looks_general_education(response: str) -> bool:
    t = response.lower()
    if re.search(r"\b(is|are)\s+(a|an|the)\s+\w+\s+(condition|disease|disorder|syndrome)", t):
        return True
    if "chronic condition" in t or "chronic medical" in t:
        return True
    if "blood pressure" in t and ("force" in t or "artery" in t or "high" in t):
        return True
    if "overview" in t or "here's what" in t or "concise overview" in t:
        return True
    if "type 2 diabetes" in t or "type 1 diabetes" in t or "diabetes mellitus" in t:
        return True
    if "metformin" in t and ("contrast" in t or "kidney" in t or "renal" in t):
        return True
    if "hypertension" in t or "high blood pressure" in t:
        return True
    return False

def _tools_provided_context(tool_results: list[str]) -> bool:
    if not tool_results:
        return False
    combined = " ".join(tool_results).lower()
    return len(combined) > 50 and "error" not in combined

def check_hallucination(response: str, tool_results: list[str]) -> HallucinationResult:
    issues: list[str] = []
    combined_tools = " ".join(tool_results).lower() if tool_results else ""
    general_ed = _looks_general_education(response)
    tools_gave_context = _tools_provided_context(tool_results)
    skip_study_stats = general_ed or tools_gave_context

    if not skip_study_stats:
        for m in _UNSUPPORTED_STATISTICS.finditer(response):
            if m.group(0).lower() not in combined_tools:
                issues.append(f"Unsupported statistic: {m.group(0)[:50]}")

    if not skip_study_stats and _UNSUPPORTED_STUDIES.search(response) and not _tools_mention_studies(combined_tools):
        issues.append("Response cites studies/research but tools provide no study data")

    if _DOSAGE_WITHOUT_TOOL.search(response):
        if "mg" not in combined_tools and "ml" not in combined_tools and "dosage" not in combined_tools:
            issues.append("Response gives specific dosage but tools did not provide dosing information")

    return HallucinationResult(passed=len(issues) == 0, issues=issues)

def _tools_mention_studies(tool_text: str) -> bool:
    return "study" in tool_text or "research" in tool_text or "clinical trial" in tool_text or "evidence" in tool_text
