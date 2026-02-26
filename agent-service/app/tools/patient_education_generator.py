"""
CareTopicz Agent Service - Patient education handout generator.

Generates structured patient education content (template for LLM to fill).
No external API; returns outline and instructions for the LLM response.
"""

from typing import Any

from pydantic import BaseModel, Field


class PatientEducationInput(BaseModel):
    """Input schema for patient_education_generator."""

    condition: str = Field(
        ...,
        description="Medical condition or topic (e.g. 'Type 2 diabetes', 'hypertension', 'post-knee-replacement care')",
        min_length=1,
    )
    reading_level: str = Field(
        default="general",
        description="Target reading level: 'simple' (5th grade), 'general' (8th grade), or 'detailed' (college level)",
    )
    language: str = Field(
        default="English",
        description="Language for the handout",
    )


_READING_MAP = {
    "simple": "Use very simple words. Write at a 5th grade reading level. Short sentences only.",
    "general": "Use clear, everyday language. Write at an 8th grade reading level. Avoid medical jargon where possible.",
    "detailed": "Use precise medical terminology with explanations. Suitable for health-literate patients.",
}


def patient_education_generator(
    condition: str,
    reading_level: str = "general",
    language: str = "English",
) -> dict[str, Any]:
    """
    Return a structured template for generating a patient education handout.
    The LLM uses this to produce the full handout in its response.
    """
    condition = condition.strip()
    if not condition:
        return {
            "success": False,
            "error": "Please specify the condition or topic for the patient education handout.",
        }

    level_instructions = _READING_MAP.get(
        reading_level.lower().strip(), _READING_MAP["general"]
    )

    return {
        "success": True,
        "condition": condition,
        "reading_level": reading_level,
        "language": language,
        "instructions": (
            f"Generate a patient education handout about {condition}. "
            f"{level_instructions} Language: {language}."
        ),
        "required_sections": [
            f"What Is {condition}",
            "Common Signs and Symptoms",
            "Treatment Options",
            "Lifestyle Changes and Self-Care",
            "When to Seek Emergency Care",
            "Questions to Ask Your Doctor",
        ],
        "format_note": (
            "Present each section with a clear label followed by 2-4 sentences of plain language explanation. "
            "End with: This handout is for general education only. Follow your healthcare provider's specific "
            "instructions for your care."
        ),
    }
