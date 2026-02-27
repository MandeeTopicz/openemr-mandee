"""
CareTopicz Agent Service - System prompt content tests.
"""

from app.agent.prompts.system import SYSTEM_PROMPT


def test_prompt_contains_never_diagnose():
    assert "never diagnose" in SYSTEM_PROMPT.lower()


def test_prompt_contains_never_prescribe():
    assert "never" in SYSTEM_PROMPT.lower() and "prescribe" in SYSTEM_PROMPT.lower()


def test_prompt_contains_formatting_rules():
    assert "concise" in SYSTEM_PROMPT.lower()
    assert "disclaimer" in SYSTEM_PROMPT.lower()


def test_prompt_contains_error_handling():
    prompt_lower = SYSTEM_PROMPT.lower()
    assert (
        "error" in prompt_lower
        or "out-of-scope" in prompt_lower
        or "out of scope" in prompt_lower
    )


def test_prompt_contains_multi_step_instructions():
    prompt_lower = SYSTEM_PROMPT.lower()
    assert "multi-step" in prompt_lower or "transition" in prompt_lower


def test_prompt_contains_instruction_protection():
    """Prompt should indicate scope boundaries and not revealing internal instructions."""
    prompt_lower = SYSTEM_PROMPT.lower()
    assert "scope" in prompt_lower or "outside" in prompt_lower
    assert (
        "assist" in prompt_lower
        or "consult" in prompt_lower
        or "cannot" in prompt_lower
    )
