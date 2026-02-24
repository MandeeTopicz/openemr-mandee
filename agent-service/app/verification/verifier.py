"""
CareTopicz Agent Service - Response verifier.

Orchestrates fact check, confidence scoring, domain rules.
Gates response by confidence threshold.
"""

from dataclasses import dataclass

from app.verification.confidence import score_confidence
from app.verification.domain_rules import check_domain_rules
from app.verification.fact_checker import fact_check


@dataclass
class VerificationResult:
    response: str
    confidence: float
    gated: bool  # True if response was modified by threshold
    caveat_added: bool


def verify_and_gate(response: str, tool_results: list[str]) -> VerificationResult:
    """
    Verify response and apply confidence-based gating.
    - >= 0.9: return directly
    - 0.7-0.9: append caveats
    - 0.5-0.7: append strong disclaimer
    - < 0.5: refuse to answer
    """
    confidence = score_confidence(response, tool_results)
    fact_result = fact_check(response, tool_results)
    domain_violations = check_domain_rules(response)

    # Domain violations: always refuse
    if domain_violations:
        return VerificationResult(
            response=(
                "I cannot provide that response. It appears to include diagnostic or "
                "prescriptive language, which is outside my scope. I assist with "
                "information only—please consult a healthcare provider for clinical decisions."
            ),
            confidence=0.0,
            gated=True,
            caveat_added=True,
        )

    # Fact check failures: refuse or strong disclaimer
    if not fact_result.passed:
        return VerificationResult(
            response=(
                "I'm unable to provide a confident answer. The information could not be "
                "verified against authoritative sources. Please consult a healthcare "
                "professional or pharmacist for accurate guidance."
            ),
            confidence=0.0,
            gated=True,
            caveat_added=True,
        )

    caveat = ""
    if confidence >= 0.9:
        pass  # Return as-is
    elif confidence >= 0.7:
        caveat = (
            "\n\n---\n"
            "⚠️ _This information is for educational purposes. "
            "Always consult a healthcare provider for medical decisions._"
        )
    elif confidence >= 0.5:
        caveat = (
            "\n\n---\n"
            "⚠️ **Important:** This response has limited verification. "
            "Please consult a healthcare professional before making any clinical decisions."
        )
    else:
        return VerificationResult(
            response=(
                "I'm not confident enough to answer that question. "
                "Please consult a healthcare provider for reliable information."
            ),
            confidence=confidence,
            gated=True,
            caveat_added=True,
        )

    final_response = response + caveat if caveat else response
    return VerificationResult(
        response=final_response,
        confidence=confidence,
        gated=bool(caveat),
        caveat_added=bool(caveat),
    )
