"""
CareTopicz Agent Service - Fact checker.

Compares LLM response claims against tool results to detect hallucinations.
"""

from dataclasses import dataclass


@dataclass
class FactCheckResult:
    passed: bool
    issues: list[str]
    tool_used: bool


def fact_check(response: str, tool_results: list[str]) -> FactCheckResult:
    """
    Check that response claims are supported by tool results.
    - If tool said "interaction found" and response says "no interaction" -> fail
    - If tool said "no interaction" and response invents interactions -> fail
    - If no tools were called, lower confidence but don't fail on medical claims
    """
    issues: list[str] = []
    combined_tools = " ".join(tool_results).lower() if tool_results else ""

    # Drug interaction specific checks
    if "drug_interaction_check" in combined_tools or "interaction" in combined_tools:
        tool_says_interaction = (
            "interaction" in combined_tools
            and ("major" in combined_tools or "moderate" in combined_tools or "minor" in combined_tools)
            and "no known interaction" not in combined_tools
            and "no interactions found" not in combined_tools
        )
        resp_lower = response.lower()
        resp_says_no_interaction = (
            "no interaction" in resp_lower
            or "no known interaction" in resp_lower
            or "no interactions found" in resp_lower
        )
        resp_says_has_interaction = (
            "interaction" in resp_lower
            and ("major" in resp_lower or "moderate" in resp_lower or "caution" in resp_lower)
        )
        if tool_says_interaction and resp_says_no_interaction:
            issues.append("Tool reported interactions but response says none")
        if not tool_says_interaction and "no interaction" not in combined_tools and resp_says_has_interaction:
            # Tool may have returned empty - don't flag if tool explicitly said no interaction
            resp_acknowledges_no_interaction = "no interaction" in resp_lower or "did not flag" in resp_lower or "not flag" in resp_lower or "no direct" in resp_lower or "no known interaction" in resp_lower or "checker did not" in resp_lower
            if ("no known" in combined_tools or "no interactions" in combined_tools) and not resp_acknowledges_no_interaction:
                issues.append("Tool reported no interactions but response suggests there are")

    # Symptom lookup: response should not invent conditions not in tool output
    if "symptom" in combined_tools or "condition" in combined_tools:
        # Basic check: if tool returned conditions, response shouldn't contradict
        if "possible conditions" in combined_tools or "urgency" in combined_tools:
            resp_lower = response.lower()
            if "you have" in resp_lower or "diagnosis" in resp_lower:
                issues.append("Response presents as diagnosis despite symptom lookup")

    passed = len(issues) == 0
    return FactCheckResult(
        passed=passed,
        issues=issues,
        tool_used=len(tool_results) > 0,
    )
