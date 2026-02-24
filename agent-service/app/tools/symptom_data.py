"""
CareTopicz Agent Service - Curated symptom → condition mapping for MVP.

Maps common symptoms to possible conditions with urgency levels.
Source: Clinical reference. Production would use ICD-10, SNOMED, or medical KB.
"""

from dataclasses import dataclass


@dataclass
class SymptomResult:
    condition: str
    urgency: str  # "emergency" | "urgent" | "routine" | "self_care"
    notes: str


def _normalize(s: str) -> str:
    return s.strip().lower().replace("-", " ")


# symptom_key -> list of (condition, urgency, notes)
_SYMPTOM_MAP: dict[str, list[SymptomResult]] = {}

def _add(symptom: str, condition: str, urgency: str, notes: str):
    key = _normalize(symptom)
    if key not in _SYMPTOM_MAP:
        _SYMPTOM_MAP[key] = []
    _SYMPTOM_MAP[key].append(SymptomResult(condition=condition, urgency=urgency, notes=notes))


_add("chest pain", "Cardiac ischemia / angina", "emergency",
     "Chest pain requires immediate evaluation. Call 911 if accompanied by shortness of breath, sweating.")
_add("chest pain", "GERD / acid reflux", "routine",
     "Acid reflux can mimic cardiac pain. Rule out cardiac causes first.")
_add("shortness of breath", "Respiratory distress", "emergency",
     "Seek immediate care. May indicate asthma exacerbation, pulmonary embolism, or heart failure.")
_add("shortness of breath", "Anxiety", "routine",
     "Anxiety can cause breathlessness. Rule out physical causes first.")
_add("headache", "Tension headache", "self_care",
     "Rest, hydration, OTC pain relievers. Seek care if sudden/severe or new pattern.")
_add("headache", "Migraine", "routine",
     "Consider migraine if one-sided, throbbing, with nausea or light sensitivity.")
_add("headache", "Hypertension", "urgent",
     "Severe headache with high BP warrants prompt evaluation.")
_add("fever", "Viral infection", "self_care",
     "Most fevers are viral. Rest, fluids. Seek care if >3 days, very high, or in infant.")
_add("fever", "Bacterial infection", "urgent",
     "High fever with shaking chills, worsening — may need antibiotics.")
_add("cough", "Upper respiratory infection", "self_care",
     "Usually viral. Hydration, rest. Seek care if prolonged, blood-tinged, or wheezing.")
_add("cough", "Asthma", "urgent",
     "Cough with wheezing or difficulty breathing — may need rescue inhaler.")
_add("abdominal pain", "GI upset / gastroenteritis", "self_care",
     "Mild, resolving with diet changes. Seek care if severe, persistent, or fever.")
_add("abdominal pain", "Appendicitis", "emergency",
     "Right lower quadrant pain, fever, nausea — seek emergency care.")
_add("fatigue", "Anemia", "routine",
     "Chronic fatigue may warrant CBC. Consider B12, iron, thyroid.")
_add("fatigue", "Sleep disorder", "routine",
     "Poor sleep quality can cause fatigue. Consider sleep study if persistent.")
_add("sore throat", "Pharyngitis / viral", "self_care",
     "Rest, fluids, lozenges. Seek care if severe, fever, or difficulty swallowing.")
_add("sore throat", "Strep throat", "routine",
     "Rapid test available. May need antibiotics if positive.")


def lookup_symptom(symptom: str) -> list[SymptomResult]:
    """Look up possible conditions for a symptom. Returns empty list if not found."""
    key = _normalize(symptom)
    return _SYMPTOM_MAP.get(key, [])


def search_symptoms(query: str) -> list[tuple[str, list[SymptomResult]]]:
    """Search symptoms by partial match. Returns list of (symptom, results)."""
    q = _normalize(query)
    results: list[tuple[str, list[SymptomResult]]] = []
    for symptom, data in _SYMPTOM_MAP.items():
        if q in symptom or symptom in q:
            results.append((symptom, data))
    return results
