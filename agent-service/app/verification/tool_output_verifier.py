"""
CareTopicz Agent Service - Intermediate verification of tool outputs.

Runs after each tool call: schema check, domain rules, confidence threshold.
Used by the verified tool node in the LangGraph flow.
"""

from app.verification.domain_rules import check_domain_rules

# Minimum length for a tool output to be considered valid (avoid empty or trivial)
_MIN_LENGTH = 3

# Confidence threshold for tool output (we use a simple pass/fail for tool output)
_TOOL_OUTPUT_CONFIDENCE_THRESHOLD = 0.5


def verify_tool_output(content: str) -> bool:
    """
    Verify a single tool output: schema (non-empty string), domain rules, basic quality.
    Returns True if the output passes verification.
    """
    if not isinstance(content, str):
        return False
    content_stripped = content.strip()
    if len(content_stripped) < _MIN_LENGTH:
        return False
    # Domain rules: tool output must not contain diagnosis/prescription language
    violations = check_domain_rules(content_stripped)
    if violations:
        return False
    # Optional: reject obvious error messages that look like tool failure
    lower = content_stripped.lower()
    if lower.startswith("error:") or "exception" in lower[:200] or "traceback" in lower[:200]:
        return False
    return True
