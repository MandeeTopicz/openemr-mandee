"""
CareTopicz Agent Service - Provider search tool.

Searches OpenEMR FHIR Practitioner/PractitionerRole and NPI Registry.
"""

from typing import Any

from pydantic import BaseModel, Field

from app.clients.npi import search_npi
from app.clients.openemr import search_practitioners
from app.utils.response_templates import format_ambiguous_input


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

    # 2. NPI Registry - parse query for name/specialty
    # Simple heuristic: if 2 words and looks like name, use first/last
    parts = query.split()
    first_name = parts[0] if len(parts) >= 1 else None
    last_name = parts[1] if len(parts) >= 2 else None
    taxonomy = None
    if any(s in query.lower() for s in ["cardio", "derm", "ortho", "pedia", "family", "internal", "psych"]):
        taxonomy = query
        first_name = last_name = None

    npi_data = search_npi(
        first_name=first_name or None,
        last_name=last_name or None,
        taxonomy_description=taxonomy or None,
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
