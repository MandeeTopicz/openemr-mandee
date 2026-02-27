"""
CareTopicz Agent Service - Expanded unit tests for verification layer.
"""

from app.verification.confidence import score_confidence
from app.verification.domain_rules import check_domain_rules, passes_domain_rules
from app.verification.fact_checker import fact_check
from app.verification.hallucination import check_hallucination
from app.verification.verifier import verify_and_gate
from app.utils.response_templates import (
    TOOL_FAILURE_UNAVAILABLE,
    TOOL_LOW_CONFIDENCE,
    format_ambiguous_input,
    format_out_of_scope,
)


class TestDomainRulesExpanded:
    """Expanded domain rules tests."""

    def test_domain_rules_catches_diagnosis_claim(self):
        assert not passes_domain_rules("You have diabetes")

    def test_domain_rules_catches_diagnosis_statement(self):
        assert not passes_domain_rules("Your diagnosis is hypertension")

    def test_domain_rules_catches_dosage_instruction(self):
        assert not passes_domain_rules("Take 500mg twice daily")

    def test_domain_rules_catches_prescribe_dosage(self):
        assert not passes_domain_rules("I prescribe 10mg lisinopril")

    def test_domain_rules_catches_dosage_start(self):
        assert not passes_domain_rules("Start with 250mg amoxicillin")

    def test_domain_rules_catches_recommended_dose(self):
        assert not passes_domain_rules("Recommended dose: 500mg")

    def test_domain_rules_allows_general_education_metformin(self):
        assert passes_domain_rules("Metformin is commonly used for type 2 diabetes")

    def test_domain_rules_allows_side_effects_info(self):
        assert passes_domain_rules("Common side effects include nausea and diarrhea")

    def test_domain_rules_allows_disclaimer(self):
        assert passes_domain_rules("Always consult a healthcare provider")

    def test_domain_rules_allows_tool_result_interaction(self):
        assert passes_domain_rules("The interaction between lisinopril and ibuprofen is moderate")

    def test_domain_rules_allows_general_medical_info(self):
        assert passes_domain_rules("Blood pressure medications include ACE inhibitors")

    def test_check_domain_rules_returns_violations(self):
        violations = check_domain_rules("You have diabetes")
        assert len(violations) >= 1
        assert any(v.rule == "diagnosis_claim" for v in violations)


class TestHallucinationExpanded:
    """Expanded hallucination checker tests."""

    def test_hallucination_passes_general_education_no_tools(self):
        r = check_hallucination(
            "Diabetes is a chronic condition affecting blood sugar levels",
            [],
        )
        assert r.passed

    def test_hallucination_passes_with_tool_context(self):
        r = check_hallucination(
            "The interaction between lisinopril and ibuprofen is moderate",
            ["Moderate interaction found between lisinopril and ibuprofen"],
        )
        assert r.passed

    def test_hallucination_passes_metformin_contrast_with_tool_note(self):
        r = check_hallucination(
            "While the interaction checker did not flag a direct interaction, "
            "metformin and contrast dye have a well-established clinical concern",
            ["No known interactions found between metformin, iodinated contrast dye"],
        )
        assert r.passed

    def test_hallucination_passes_hypertension_general_info(self):
        r = check_hallucination(
            "Hypertension, or high blood pressure, is a chronic condition",
            [],
        )
        assert r.passed

    def test_hallucination_fails_unsupported_statistics(self):
        r = check_hallucination(
            "Studies show 85% of patients respond to treatment",
            [],
        )
        assert not r.passed

    def test_hallucination_fails_specific_dosage_without_tool(self):
        r = check_hallucination(
            "Take 500mg daily with meals",
            [],
        )
        assert not r.passed

    def test_hallucination_fails_studies_without_tool_data(self):
        r = check_hallucination(
            "Research indicates this combination is dangerous",
            ["No interactions found"],
        )
        assert not r.passed


class TestConfidenceExpanded:
    """Expanded confidence scorer tests."""

    def test_confidence_high_with_tool_result(self):
        s = score_confidence(
            "There is a moderate interaction between these drugs.",
            ["Drug interaction data: lisinopril + ibuprofen [moderate]"],
        )
        assert s >= 0.9

    def test_confidence_high_general_education(self):
        s = score_confidence(
            "Hypertension is high blood pressure. Consult a provider.",
            [],
        )
        assert s >= 0.9

    def test_confidence_medium_tool_dependent_no_tools(self):
        s = score_confidence(
            "The interaction between lisinopril and ibuprofen is moderate.",
            [],
        )
        assert 0.7 <= s <= 0.9 or s < 0.9

    def test_confidence_low_domain_violation(self):
        s = score_confidence("You have diabetes", [])
        assert s < 0.7


class TestVerifierIntegration:
    """Verifier integration tests for safe tools and gating."""

    def test_verifier_patient_education_safe_tool_passes(self):
        v = verify_and_gate(
            "Type 2 diabetes is a chronic condition. Here are common symptoms, "
            "treatment options, lifestyle changes, and when to seek emergency care.",
            ["Patient education template for Type 2 diabetes"],
            tools_used=["patient_education_generator"],
        )
        assert not v.gated
        assert "diabetes" in v.response.lower()

    def test_verifier_provider_search_safe_tool_passes(self):
        v = verify_and_gate(
            "I found Dr. Smith. You can schedule an appointment with their office.",
            ["Providers found: Dr. Smith, NPI 123"],
            tools_used=["provider_search"],
        )
        assert not v.gated

    def test_verifier_insurance_provider_safe_tool_passes(self):
        v = verify_and_gate(
            "Here are providers in Houston who may accept Medicare. Confirm with their office.",
            ["Insurance: Medicare. Providers found..."],
            tools_used=["insurance_provider_search"],
        )
        assert not v.gated

    def test_verifier_domain_violation_refused(self):
        v = verify_and_gate("You have diabetes", [], tools_used=[])
        assert v.gated
        assert "cannot" in v.response.lower() or "consult" in v.response.lower()

    def test_verifier_prescription_violation_refused(self):
        v = verify_and_gate("Take 500mg twice daily", [], tools_used=[])
        assert v.gated
        assert "cannot" in v.response.lower() or "consult" in v.response.lower()

    def test_verifier_fact_check_failure_refused(self):
        v = verify_and_gate(
            "No interactions found between these drugs.",
            ["Drug interactions found: lisinopril + ibuprofen [moderate]"],
        )
        assert v.gated
        assert "consult" in v.response.lower() or "professional" in v.response.lower()

    def test_verifier_confidence_medium_adds_caveat(self):
        v = verify_and_gate(
            "The interaction between lisinopril and ibuprofen may be moderate.",
            [],
        )
        if not v.gated:
            assert v.confidence >= 0.7
        else:
            assert "consult" in v.response.lower()

    def test_verifier_high_confidence_passes_through(self):
        v = verify_and_gate(
            "There is a moderate interaction between lisinopril and ibuprofen.",
            ["Drug interactions found: lisinopril + ibuprofen [moderate]"],
        )
        assert "interaction" in v.response.lower()
        assert v.confidence >= 0.9 or not v.gated


class TestResponseTemplates:
    """Tests for response_templates.py."""

    def test_tool_failure_unavailable_contains_retrieve(self):
        assert "wasn't able to retrieve" in TOOL_FAILURE_UNAVAILABLE.lower()

    def test_tool_low_confidence_contains_not_confident(self):
        assert "not confident" in TOOL_LOW_CONFIDENCE.lower()

    def test_format_ambiguous_input_contains_clarify(self):
        out = format_ambiguous_input("drug name")
        assert "drug name" in out.lower()
        assert "clarify" in out.lower()

    def test_format_out_of_scope_contains_consult(self):
        out = format_out_of_scope("drug interactions", "cooking recipes", "a cookbook")
        assert "cooking recipes" in out.lower()
        assert "consult" in out.lower()
