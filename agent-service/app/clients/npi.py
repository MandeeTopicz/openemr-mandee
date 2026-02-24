"""
CareTopicz Agent Service - NPI Registry API client.

Searches the CMS NPPES NPI Registry for provider credentials.
API: https://npiregistry.cms.hhs.gov/api-page
"""

from typing import Any

import httpx

NPI_BASE = "https://npiregistry.cms.hhs.gov/api"


def search_npi(
    *,
    first_name: str | None = None,
    last_name: str | None = None,
    organization_name: str | None = None,
    taxonomy_description: str | None = None,
    state: str | None = None,
    city: str | None = None,
    limit: int = 20,
) -> dict[str, Any] | None:
    """
    Search NPI Registry. Returns raw API response or None on error.
    """
    params: dict[str, str | int] = {"version": "2.1", "limit": min(limit, 200)}
    if first_name:
        params["first_name"] = first_name
    if last_name:
        params["last_name"] = last_name
    if organization_name:
        params["organization_name"] = organization_name
    if taxonomy_description:
        params["taxonomy_description"] = taxonomy_description
    if state:
        params["state"] = state
    if city:
        params["city"] = city

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(NPI_BASE, params=params)
            if resp.status_code != 200:
                return None
            return resp.json()
    except (httpx.HTTPError, ValueError):
        return None
