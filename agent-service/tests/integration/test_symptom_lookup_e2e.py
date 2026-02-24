"""
CareTopicz Agent Service - E2E test for symptom_lookup tool.

Run: pytest tests/integration/test_symptom_lookup_e2e.py -v
"""

from app.tools.symptom_lookup import symptom_lookup


def test_symptom_lookup_chest_pain():
    """Chest pain returns conditions with urgency."""
    result = symptom_lookup("chest pain")
    assert result["success"] is True
    assert len(result["conditions"]) >= 1
    urgencies = [c["urgency"] for c in result["conditions"]]
    assert "emergency" in urgencies
    assert "disclaimer" in result


def test_symptom_lookup_headache():
    """Headache returns multiple conditions."""
    result = symptom_lookup("headache")
    assert result["success"] is True
    assert len(result["conditions"]) >= 1
    assert any("tension" in c["condition"].lower() or "migraine" in c["condition"].lower() for c in result["conditions"])


def test_symptom_lookup_unknown():
    """Unknown symptom returns empty with note."""
    result = symptom_lookup("xyzzy_nonexistent")
    assert result["success"] is True
    assert result["conditions"] == []
    assert "note" in result
