"""
CareTopicz Agent Service - Unit tests for verification layer.
"""

import pytest

from app.verification.confidence import score_confidence
from app.verification.domain_rules import check_domain_rules, passes_domain_rules
from app.verification.fact_checker import fact_check
from app.verification.verifier import verify_and_gate


class TestDomainRules:
    def test_passes_clean_response(self):
        assert passes_domain_rules("This is fine.")

    def test_fails_diagnosis_language(self):
        assert not passes_domain_rules("You have diabetes")
        assert not passes_domain_rules("Your diagnosis is hypertension")

    def test_fails_prescription_language(self):
        assert not passes_domain_rules("Take 10 mg daily")
        assert not passes_domain_rules("I prescribe you 500mg")


class TestFactChecker:
    def test_hallucination_tool_says_interaction_resp_says_no(self):
        result = fact_check(
            "No interactions found between these drugs.",
            ["Drug interactions found:\n- lisinopril + ibuprofen: [moderate] ..."],
        )
        assert not result.passed
        assert len(result.issues) >= 1

    def test_consistent_tool_and_response(self):
        result = fact_check(
            "There is a moderate interaction between lisinopril and ibuprofen.",
            ["Drug interactions found:\n- lisinopril + ibuprofen: [moderate] ..."],
        )
        assert result.passed


class TestConfidence:
    def test_high_confidence_with_tool(self):
        s = score_confidence(
            "There is a moderate interaction.",
            ["Drug interactions found: lisinopril + ibuprofen [moderate]"],
        )
        assert s >= 0.9

    def test_low_confidence_domain_violation(self):
        s = score_confidence("You have hypertension", [])
        assert s < 0.7


class TestVerifier:
    def test_domain_violation_refused(self):
        v = verify_and_gate("You have diabetes. Take metformin 500mg.", [])
        assert v.gated
        assert "cannot" in v.response.lower() or "consult" in v.response.lower()

    def test_high_confidence_passes_through(self):
        v = verify_and_gate(
            "There is a moderate interaction between these drugs.",
            ["Drug interactions found: ..."],
        )
        assert not v.gated or v.confidence >= 0.9
        assert "interaction" in v.response.lower()
