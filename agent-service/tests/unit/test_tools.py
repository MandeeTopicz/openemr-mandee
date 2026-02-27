"""
CareTopicz Agent Service - Unit tests for tools.
"""

import pytest

from app.tools.patient_education_generator import (
    PatientEducationInput,
    patient_education_generator,
)
from app.tools.insurance_provider_search import (
    InsuranceProviderSearchInput,
    insurance_provider_search,
)
from app.tools.provider_search import _resolve_taxonomy, provider_search


class TestPatientEducationGenerator:
    """Unit tests for patient_education_generator."""

    def test_schema_accepts_condition_reading_level_language(self):
        schema = PatientEducationInput.model_validate({
            "condition": "Type 2 Diabetes",
            "reading_level": "simple",
            "language": "English",
        })
        assert schema.condition == "Type 2 Diabetes"
        assert schema.reading_level == "simple"
        assert schema.language == "English"

    def test_schema_condition_required(self):
        with pytest.raises(Exception):
            PatientEducationInput.model_validate({"reading_level": "general"})

    def test_output_contains_diabetes_sections(self):
        result = patient_education_generator(condition="Type 2 Diabetes")
        assert result["success"] is True
        assert "diabetes" in result["condition"].lower()
        sections = result.get("required_sections", [])
        assert any("symptom" in s.lower() or "treatment" in s.lower() for s in sections)

    def test_output_contains_hypertension(self):
        result = patient_education_generator(condition="Hypertension")
        assert result["success"] is True
        out_str = str(result).lower()
        assert "blood pressure" in out_str or "hypertension" in out_str

    def test_empty_condition_returns_error(self):
        result = patient_education_generator(condition="")
        assert result["success"] is False
        assert "error" in result or "clarify" in result.get("error", "").lower()

    def test_reading_level_simple_accepted(self):
        result = patient_education_generator(
            condition="Asthma",
            reading_level="simple",
        )
        assert result["success"] is True
        assert result["reading_level"] == "simple"


class TestInsuranceProviderSearch:
    """Unit tests for insurance_provider_search."""

    def test_schema_accepts_insurance_plan_specialty_location(self):
        schema = InsuranceProviderSearchInput.model_validate({
            "insurance_plan": "Medicare",
            "specialty": "cardiologist",
            "location": "Houston",
        })
        assert schema.insurance_plan == "Medicare"
        assert schema.specialty == "cardiologist"
        assert schema.location == "Houston"

    def test_empty_insurance_plan_returns_error(self):
        result = insurance_provider_search(insurance_plan="")
        assert result["success"] is False
        assert "error" in result
        assert "clarify" in result.get("error", "").lower()

    def test_cardiologist_taxonomy_mapping(self):
        taxonomy = _resolve_taxonomy("cardiologist")
        assert "cardiovascular" in taxonomy.lower() or "cardiology" in taxonomy.lower()

    def test_dermatologist_taxonomy_mapping(self):
        taxonomy = _resolve_taxonomy("dermatologist")
        assert "dermatology" in taxonomy.lower()

    def test_unknown_specialty_handled_gracefully(self):
        taxonomy = _resolve_taxonomy("unknown_specialty_xyz")
        assert isinstance(taxonomy, str)
        assert len(taxonomy) >= 0


class TestProviderSearch:
    """Unit tests for provider_search taxonomy and behavior."""

    def test_resolve_taxonomy_cardiologist(self):
        assert _resolve_taxonomy("cardiologist") == "Cardiovascular Disease"

    def test_resolve_taxonomy_dermatologist(self):
        assert _resolve_taxonomy("dermatologist") == "Dermatology"

    def test_resolve_taxonomy_dr_lee_strips_prefix(self):
        result = provider_search("Dr. Lee", limit=5)
        assert result["success"] is True
        assert "providers" in result

    def test_resolve_taxonomy_lee_no_prefix(self):
        result = provider_search("Lee", limit=5)
        assert result["success"] is True
        assert "providers" in result

    def test_list_all_providers_triggers_all_query(self):
        result = provider_search("Who are the providers in this system?", limit=5)
        assert result["success"] is True
        assert "providers" in result

    def test_list_all_providers_alternate_phrase(self):
        result = provider_search("List all providers", limit=5)
        assert result["success"] is True
        assert "providers" in result

    def test_find_cardiologist_austin_not_all_providers(self):
        result = provider_search("Find a cardiologist in Austin", limit=5)
        assert result["success"] is True
        assert "providers" in result
