"""
CareTopicz Agent Service - Insurance and provider network search.

Finds providers by specialty/location and adds insurance context.
NPI Registry does not list accepted plans; we return matching providers
with a note to confirm insurance with the provider's office.
"""

from typing import Any

from pydantic import BaseModel, Field

from app.clients.npi import search_npi
from app.tools.provider_search import _resolve_taxonomy
from app.utils.response_templates import format_ambiguous_input

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA",
    "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT",
    "VA", "WA", "WV", "WI", "WY", "DC",
}


def _parse_location(location: str) -> tuple[str | None, str | None]:
    """Parse location string into (city, state)."""
    if not location or not location.strip():
        return None, None
    parts = location.strip().split()
    city = None
    state = None
    for p in parts:
        if p.upper() in US_STATES:
            state = p.upper()
        else:
            city = (city + " " + p).strip() if city else p
    return city or None, state


class InsuranceProviderSearchInput(BaseModel):
    """Input schema for insurance_provider_search."""

    insurance_plan: str = Field(
        ...,
        description="Insurance plan name (e.g. 'Blue Cross', 'Aetna', 'Medicare')",
        min_length=1,
    )
    specialty: str = Field(
        default="",
        description="Medical specialty (e.g. 'cardiologist', 'dermatologist')",
    )
    location: str = Field(
        default="",
        description="City, state, or zip code",
    )
    limit: int = Field(default=10, ge=1, le=20, description="Maximum number of providers to return")


def insurance_provider_search(
    insurance_plan: str,
    specialty: str = "",
    location: str = "",
    limit: int = 10,
) -> dict[str, Any]:
    """
    Find providers matching specialty and location, with insurance context.
    NPI does not provide accepted insurance; we return matches and note that
    insurance acceptance should be confirmed with the provider's office.
    """
    insurance_plan = insurance_plan.strip()
    if not insurance_plan:
        return {
            "success": False,
            "error": format_ambiguous_input("which insurance plan you want to check"),
            "providers": [],
        }

    taxonomy = _resolve_taxonomy(specialty.strip()) if specialty.strip() else None
    city, state = _parse_location(location)
    npi_limit = limit

    npi_data = search_npi(
        taxonomy_description=taxonomy,
        city=city,
        state=state,
        limit=npi_limit,
    )

    providers: list[dict[str, Any]] = []
    if npi_data:
        results = npi_data.get("results") or []
        for r in results[:limit]:
            num = r.get("number")
            enum_type = r.get("enumeration_type", "")
            if enum_type == "NPI-2":
                name = r.get("basic", {}).get("organization_name", "Unknown")
            else:
                p = r.get("basic", {})
                first = p.get("first_name", "")
                last = p.get("last_name", "")
                name = f"{first} {last}".strip() or "Unknown"
            tax = r.get("taxonomies", [{}])
            spec = tax[0].get("desc", "") if tax else ""
            addr = r.get("addresses", [{}])
            loc = addr[0] if addr else {}
            providers.append({
                "name": name,
                "npi": num,
                "specialty": spec,
                "city": loc.get("city", ""),
                "state": loc.get("state", ""),
                "source": "NPI Registry",
            })

    insurance_note = (
        "These providers match your criteria. Insurance acceptance should be confirmed "
        "directly with the provider's office."
    )
    if insurance_plan.lower() in ("medicare", "medicaid"):
        insurance_note += (
            f" Many providers with the matching specialty accept {insurance_plan}."
        )

    return {
        "success": True,
        "insurance_plan": insurance_plan,
        "specialty": specialty or "any",
        "location": location or "any",
        "providers": providers,
        "insurance_note": insurance_note,
        "source": "NPI Registry",
    }
