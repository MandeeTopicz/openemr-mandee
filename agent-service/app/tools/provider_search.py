"""
CareTopicz Agent Service - Provider search tool.

Searches OpenEMR FHIR Practitioner/PractitionerRole and NPI Registry.
"""

from typing import Any

from pydantic import BaseModel, Field

from app.clients.npi import search_npi
from app.clients.openemr import search_practitioners
from app.utils.response_templates import format_ambiguous_input

# Map common search terms to NPI taxonomy descriptions
_TAXONOMY_MAP = {
    "cardiologist": "Cardiovascular Disease",
    "cardiology": "Cardiovascular Disease",
    "dermatologist": "Dermatology",
    "dermatology": "Dermatology",
    "orthopedic": "Orthopaedic Surgery",
    "orthopedist": "Orthopaedic Surgery",
    "pediatrician": "Pediatrics",
    "pediatrics": "Pediatrics",
    "family medicine": "Family Medicine",
    "family doctor": "Family Medicine",
    "primary care": "Family Medicine",
    "internal medicine": "Internal Medicine",
    "internist": "Internal Medicine",
    "psychiatrist": "Psychiatry & Neurology",
    "psychiatry": "Psychiatry & Neurology",
    "psychologist": "Psychology",
    "surgeon": "Surgery",
    "neurologist": "Neurology",
    "neurology": "Neurology",
    "gastroenterologist": "Gastroenterology",
    "gastroenterology": "Gastroenterology",
    "pulmonologist": "Pulmonary Disease",
    "pulmonology": "Pulmonary Disease",
    "endocrinologist": "Endocrinology, Diabetes & Metabolism",
    "endocrinology": "Endocrinology, Diabetes & Metabolism",
    "rheumatologist": "Rheumatology",
    "rheumatology": "Rheumatology",
    "urologist": "Urology",
    "urology": "Urology",
    "ophthalmologist": "Ophthalmology",
    "ophthalmology": "Ophthalmology",
    "radiologist": "Diagnostic Radiology",
    "radiology": "Diagnostic Radiology",
    "anesthesiologist": "Anesthesiology",
    "anesthesiology": "Anesthesiology",
    "emergency medicine": "Emergency Medicine",
    "oncologist": "Medical Oncology",
    "oncology": "Medical Oncology",
    "obgyn": "Obstetrics & Gynecology",
    "ob-gyn": "Obstetrics & Gynecology",
    "gynecologist": "Obstetrics & Gynecology",
}

def _resolve_taxonomy(term: str) -> str:
    """Map a common specialty term to an NPI taxonomy description."""
    lower = term.lower().strip()
    if lower in _TAXONOMY_MAP:
        return _TAXONOMY_MAP[lower]
    # Try partial match
    for key, val in _TAXONOMY_MAP.items():
        if key in lower or lower in key:
            return val
    return term


class ProviderSearchInput(BaseModel):
    """Input schema for provider_search."""

    query: str = Field(
        ...,
        description="Provider name, specialty, or location to search (e.g. 'cardiologist Austin', 'Dr. Smith')",
        min_length=1,
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Maximum number of providers to return",
    )


def provider_search(query: str, limit: int = 10) -> dict[str, Any]:
    """
    Search for providers by name, specialty, or location.
    Combines OpenEMR FHIR (if configured) and NPI Registry.
    """
    query = query.strip()
    if not query:
        return {
            "success": False,
            "error": format_ambiguous_input("which provider name, specialty, or location you're searching for"),
            "providers": [],
        }

    providers: list[dict[str, Any]] = []

    # 1. Try OpenEMR FHIR if token is set
    fhir_pract = search_practitioners(name=query)
    if fhir_pract:
        entries = fhir_pract.get("entry") or []
        for e in entries[:limit]:
            res = e.get("resource", {})
            name_parts = []
            for p in res.get("name", [{}]):
                given = " ".join(p.get("given", []))
                family = p.get("family", "")
                if given or family:
                    name_parts.append(f"{given} {family}".strip())
            name = name_parts[0] if name_parts else "Unknown"
            providers.append({
                "name": name,
                "source": "OpenEMR",
                "id": res.get("id"),
            })

    # 2. NPI Registry - parse query for name/specialty/location
    specialty_keywords = ["cardio", "derm", "ortho", "pedia", "family", "internal", "psych",
                          "surgeon", "oncol", "neuro", "gastro", "pulmon", "endocrin", "rheumat",
                          "urolog", "ophthal", "radiol", "anesthes", "emergency", "primary care"]
    us_states = {"AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
                 "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
                 "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
                 "VA","WA","WV","WI","WY","DC"}

    parts = query.split()
    query_lower = query.lower()
    taxonomy = None
    first_name = None
    last_name = None
    city = None
    state = None

    # Detect specialty
    is_specialty = any(s in query_lower for s in specialty_keywords)
    if is_specialty:
        # Extract specialty word(s) and location
        spec_words = []
        loc_words = []
        for p in parts:
            if any(s in p.lower() for s in specialty_keywords):
                spec_words.append(p)
            elif p.upper() in us_states:
                state = p.upper()
            elif p.lower() in ["in", "near", "around"]:
                continue
            else:
                loc_words.append(p)
        raw_taxonomy = " ".join(spec_words) if spec_words else query
        taxonomy = _resolve_taxonomy(raw_taxonomy)
        if loc_words:
            city = " ".join(loc_words)
    else:
        # Treat as name search
        # Remove "Dr." or "Dr" prefix
        clean_parts = [p for p in parts if p.lower().strip(".") != "dr"]
        first_name = clean_parts[0] if len(clean_parts) >= 1 else None
        last_name = clean_parts[1] if len(clean_parts) >= 2 else None

    npi_data = search_npi(
        first_name=first_name,
        last_name=last_name,
        taxonomy_description=taxonomy,
        city=city,
        state=state,
        limit=limit,
    )
    if npi_data:
        results = npi_data.get("results") or []
        for r in results[:limit]:
            num = r.get("number")
            enum_type = r.get("enumeration_type", "")
            if enum_type == "NPI-2":  # organization
                name = r.get("basic", {}).get("organization_name", "Unknown")
            else:
                p = r.get("basic", {})
                first = p.get("first_name", "")
                last = p.get("last_name", "")
                name = f"{first} {last}".strip() or "Unknown"
            tax = r.get("taxonomies", [{}])
            specialty = tax[0].get("desc", "") if tax else ""
            addr = r.get("addresses", [{}])
            loc = addr[0] if addr else {}
            city = loc.get("city", "")
            state = loc.get("state", "")
            providers.append({
                "name": name,
                "npi": num,
                "specialty": specialty,
                "city": city,
                "state": state,
                "source": "NPI Registry",
            })

    return {
        "success": True,
        "query": query,
        "providers": providers[:limit],
        "source": "OpenEMR FHIR + NPI Registry",
    }
