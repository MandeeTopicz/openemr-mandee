"""
CareTopicz Agent Service - E2E test for drug_interaction_check tool.

Run: pytest tests/integration/test_drug_interaction_e2e.py -v
Requires: ANTHROPIC_API_KEY in .env (skipped if not set)
"""

import os

import pytest

from app.tools.drug_interaction import drug_interaction_check
from app.tools.drug_interactions_data import check_interaction


def test_drug_interaction_check_lisinopril_ibuprofen():
    """Ask about lisinopril + ibuprofen -> returns known interaction."""
    result = drug_interaction_check(["lisinopril", "ibuprofen"])
    assert result["success"] is True
    assert len(result["interactions"]) >= 1
    interaction = result["interactions"][0]
    assert "lisinopril" in (interaction["drug1"], interaction["drug2"])
    assert "ibuprofen" in (interaction["drug1"], interaction["drug2"])
    assert interaction["severity"] in ("major", "moderate", "minor")
    assert "ACE" in interaction["description"] or "NSAID" in interaction["description"]


def test_drug_interaction_check_no_interaction():
    """Ask about drug pair with no known interaction."""
    result = drug_interaction_check(["lisinopril", "metformin"])
    assert result["success"] is True
    assert result["interactions"] == []


def test_drug_interaction_check_requires_two_drugs():
    """Single drug returns error."""
    result = drug_interaction_check(["lisinopril"])
    assert result["success"] is False
    assert "error" in result
    assert "2" in result["error"] or "least" in result["error"].lower()


def test_curated_data_lisinopril_ibuprofen():
    """Curated data has lisinopril+ibuprofen interaction."""
    i = check_interaction("lisinopril", "ibuprofen")
    assert i is not None
    assert i.severity == "moderate"
    assert "ACE" in i.description or "NSAID" in i.description


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY required for full agent e2e",
)
def test_chat_endpoint_drug_interaction():
    """Full agent: ask about drug interaction, get real tool result."""
    from app.agent.graph import invoke_graph

    response, _ = invoke_graph(
        "Check for drug interactions between lisinopril and ibuprofen"
    )
    assert response
    assert "interaction" in response.lower() or "ACE" in response or "NSAID" in response
    assert "lisinopril" in response.lower()
    assert "ibuprofen" in response.lower()
