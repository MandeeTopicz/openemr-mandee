"""
CareTopicz Agent Service - RxNorm API client.

Resolves drug names to RxCUI and retrieves drug information.
RxNav REST API: https://rxnav.nlm.nih.gov/
Note: Drug interaction API was discontinued Jan 2024; use DrugBank or curated data for interactions.
"""

import time
from typing import Any

import httpx

RXNAV_BASE = "https://rxnav.nlm.nih.gov/REST"
RATE_LIMIT_DELAY = 0.05  # ~20 req/sec


def _rate_limit():
    """Simple rate limiting for RxNorm API (20 req/sec)."""
    time.sleep(RATE_LIMIT_DELAY)


def resolve_rxcui(drug_name: str) -> str | None:
    """
    Resolve a drug name to RxCUI (RxNorm Concept Unique Identifier).
    Returns the first matching rxcui or None if not found.
    """
    _rate_limit()
    url = f"{RXNAV_BASE}/rxcui.json"
    params = {"name": drug_name.strip()}
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, KeyError):
        return None

    ids = data.get("idGroup", {}).get("rxnormId")
    if ids and isinstance(ids, list):
        return str(ids[0])
    if ids and isinstance(ids, str):
        return ids
    return None


def get_drugs(drug_name: str) -> list[dict[str, Any]]:
    """
    Get drug concepts for a name (ingredient, brands, formulations).
    Returns list of concept properties: rxcui, name, synonym, tty.
    """
    _rate_limit()
    url = f"{RXNAV_BASE}/drugs.json"
    params = {"name": drug_name.strip()}
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, KeyError):
        return []

    concepts: list[dict[str, Any]] = []
    drug_group = data.get("drugGroup", {})
    for group in drug_group.get("conceptGroup", []) or []:
        props = group.get("conceptProperties") or []
        if isinstance(props, dict):
            props = [props]
        for p in props:
            concepts.append({
                "rxcui": p.get("rxcui"),
                "name": p.get("name"),
                "synonym": p.get("synonym"),
                "tty": p.get("tty"),
            })
    return concepts


def resolve_rxcuis(drug_names: list[str]) -> dict[str, str]:
    """
    Resolve multiple drug names to RxCUIs.
    Returns dict mapping original name -> rxcui (or None for unresolved).
    """
    result: dict[str, str] = {}
    for name in drug_names:
        rxcui = resolve_rxcui(name)
        if rxcui:
            result[name] = rxcui
    return result
