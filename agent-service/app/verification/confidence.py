"""
CareTopicz Agent Service - Confidence scoring for responses.

Scores 0.0-1.0 based on fact check, domain rules, and tool coverage.
"""

from app.verification.domain_rules import check_domain_rules
from app.verification.fact_checker import fact_check


def score_confidence(
    response: str,
    tool_results: list[str],
) -> float:
    """
    Compute confidence score 0.0-1.0 for a response.
    Factors: fact check pass, domain rules pass, tool coverage.
    """
    fact_result = fact_check(response, tool_results)
    domain_violations = check_domain_rules(response)

    score = 1.0

    # Fact check: -0.3 per issue
    if not fact_result.passed:
        score -= 0.3 * len(fact_result.issues)
    # Cap at 0.7 if any fact issues
    if fact_result.issues:
        score = min(score, 0.7)

    # Domain rules: -0.4 per violation (diagnosis/prescription)
    if domain_violations:
        score -= 0.4 * len(domain_violations)
        score = max(0.0, score)

    # Tool coverage: no tools used for medical query can reduce confidence
    # But we don't always need tools (e.g. greeting)
    if not fact_result.tool_used and _looks_medical(response):
        score = min(score, 0.85)  # Slight reduction for medical response without tool

    return max(0.0, min(1.0, round(score, 2)))


def _looks_medical(text: str) -> bool:
    """Heuristic: does the response look like medical advice?"""
    medical_words = (
        "interaction", "medication", "drug", "symptom", "condition", "prescribe",
        "diagnosis", "treatment", "dosage", "patient", "clinical", "doctor",
        "health", "medical", "consult", "recommend",
    )
    t = text.lower()
    return any(w in t for w in medical_words)
