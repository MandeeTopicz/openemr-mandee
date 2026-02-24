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


# Patterns that suggest fabricated or unsupported claims
_UNSUPPORTED_STATISTICS = re.compile(
    r"\b\d{1,3}%\s*(?:of|risk|chance|effective|success|mortality|morbidity)",
    re.I,
)
_UNSUPPORTED_STUDIES = re.compile(
    r"\b(?:studies show|research (?:suggests|indicates|shows)|clinical trials (?:show|demonstrate)|evidence suggests)\b",
    re.I,
)
# Specific dosage when tools don't provide it - e.g. "take 500mg twice daily"
_DOSAGE_WITHOUT_TOOL = re.compile(
    r"\btake\s+\d+\s*(?:mg|ml|mcg|g)\s+(?:\d+\s*times\s+)?(?:daily|per day|a day)",
    re.I,
)


def check_hallucination(response: str, tool_results: list[str]) -> HallucinationResult:
    """
    Detect potential hallucinations: fabricated stats, unsupported study claims,
    or invented dosages not present in tool output.
    """
    issues: list[str] = []
    combined_tools = " ".join(tool_results).lower() if tool_results else ""

    # Unsupported statistics (e.g. "85% of patients") - tools rarely provide these
    for m in _UNSUPPORTED_STATISTICS.finditer(response):
        if m.group(0).lower() not in combined_tools:
            issues.append(f"Unsupported statistic in response: {m.group(0)[:50]}")

    # "Studies show" / "research suggests" - we have no study data in tools
    if _UNSUPPORTED_STUDIES.search(response) and not _tools_mention_studies(combined_tools):
        issues.append("Response cites studies/research but tools provide no study data")

    # Specific dosage instructions when tools didn't provide dosage
    if _DOSAGE_WITHOUT_TOOL.search(response):
        if "mg" not in combined_tools and "ml" not in combined_tools and "dosage" not in combined_tools:
            issues.append("Response gives specific dosage but tools did not provide dosing information")

    return HallucinationResult(
        passed=len(issues) == 0,
        issues=issues,
    )


def _tools_mention_studies(tool_text: str) -> bool:
    """Check if tool output mentions studies/research."""
    return (
        "study" in tool_text
        or "research" in tool_text
        or "clinical trial" in tool_text
        or "evidence" in tool_text
    )
