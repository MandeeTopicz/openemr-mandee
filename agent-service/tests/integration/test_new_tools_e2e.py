"""
CareTopicz Agent Service - Integration tests for new tools (patient education, insurance provider).

Requires agent running at AGENT_URL. Mark with @pytest.mark.integration to skip in CI.
Run: pytest tests/integration/test_new_tools_e2e.py -v -m integration
"""

import pytest
import httpx

AGENT_URL = "http://localhost:8000"


@pytest.mark.integration
class TestPatientEducationE2E:
    """E2E tests for patient education handout generation."""

    def test_education_diabetes(self):
        """Agent should generate a patient education handout for diabetes."""
        r = httpx.post(
            f"{AGENT_URL}/chat",
            json={"message": "Generate a patient handout for Type 2 diabetes"},
            timeout=60,
        )
        assert r.status_code == 200
        data = r.json()
        assert "diabetes" in data["response"].lower()
        assert len(data["response"]) > 200
        tool_names = [t["name"] for t in data.get("tools_used", [])]
        assert any("education" in t for t in tool_names)

    def test_education_hypertension(self):
        """Agent should generate a patient education handout for hypertension."""
        r = httpx.post(
            f"{AGENT_URL}/chat",
            json={"message": "Generate a simple patient education handout for high blood pressure"},
            timeout=60,
        )
        assert r.status_code == 200
        data = r.json()
        resp = data["response"].lower()
        assert "blood pressure" in resp or "hypertension" in resp
        assert len(data["response"]) > 200


@pytest.mark.integration
class TestInsuranceProviderE2E:
    """E2E tests for insurance provider search."""

    def test_medicare_cardiologist(self):
        """Agent should find cardiologists accepting Medicare."""
        r = httpx.post(
            f"{AGENT_URL}/chat",
            json={"message": "Find a cardiologist in Houston that takes Medicare"},
            timeout=60,
        )
        assert r.status_code == 200
        data = r.json()
        resp = data["response"].lower()
        assert "cardiologist" in resp or "cardiovascular" in resp or "cardiology" in resp

    def test_insurance_search_missing_plan(self):
        """Agent should handle missing insurance plan gracefully."""
        r = httpx.post(
            f"{AGENT_URL}/chat",
            json={"message": "Find a doctor that takes my insurance"},
            timeout=60,
        )
        assert r.status_code == 200
        data = r.json()
        resp = data["response"].lower()
        assert "insurance" in resp or "plan" in resp or "clarify" in resp


@pytest.mark.integration
class TestProviderSearchE2E:
    """E2E tests for provider search (OpenEMR)."""

    def test_openemr_provider_dr_lee(self):
        """Agent should find Dr. Lee from OpenEMR."""
        r = httpx.post(
            f"{AGENT_URL}/chat",
            json={"message": "Find Dr. Lee"},
            timeout=60,
        )
        assert r.status_code == 200
        data = r.json()
        assert "lee" in data["response"].lower() or "donna" in data["response"].lower()

    def test_all_system_providers(self):
        """Agent should list all OpenEMR providers."""
        r = httpx.post(
            f"{AGENT_URL}/chat",
            json={"message": "Who are the providers in this system?"},
            timeout=60,
        )
        assert r.status_code == 200
        data = r.json()
        resp = data["response"].lower()
        found = sum(1 for name in ["lee", "smith", "stone"] if name in resp)
        assert found >= 2
