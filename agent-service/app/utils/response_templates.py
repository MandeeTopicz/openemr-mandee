"""
CareTopicz Agent Service - Standard response templates for tool errors and refusals.

Use these so error handling looks and feels the same regardless of which tool was called.
Tools return these strings in their "error" or "note" fields; the LLM is instructed
to use them consistently when relaying to the user.
"""

# Tool failure / service unavailable (FHIR down, API error, etc.)
TOOL_FAILURE_UNAVAILABLE = (
    "I wasn't able to retrieve that information right now. "
    "Please try again, or consult your clinical system or pharmacist as needed."
)

# Low confidence / partial or no data (e.g. symptom lookup with no match)
TOOL_LOW_CONFIDENCE = (
    "I found some information but I'm not confident in its accuracy. "
    "I'd recommend verifying with a healthcare provider or clinical reference."
)


def format_ambiguous_input(clarification_hint: str) -> str:
    """User input was missing or ambiguous. Ask for clarification in a standard way."""
    hint = clarification_hint.strip().rstrip(".")
    return f"I want to make sure I help you accurately. Could you clarify {hint}?"


def format_out_of_scope(supported: str, asked: str, resource: str) -> str:
    """Request is out of scope. Use for refusals (e.g. diagnosis, prescription)."""
    return (
        f"I can only help with {supported}. "
        f"For {asked}, please consult {resource}."
    )
