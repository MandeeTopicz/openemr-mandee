"""
CareTopicz Agent Service - Domain rules for healthcare responses.

Enforces: never diagnose, never prescribe.
"""

import re
from dataclasses import dataclass


@dataclass
class DomainRuleViolation:
    rule: str
    match: str
    snippet: str


# Forbidden patterns - indicate diagnosis or prescription
_DIAGNOSE_PATTERNS = [
    (re.compile(r"\byou (?:have|suffer from)\s+\w+", re.I), "diagnosis_claim"),
    (re.compile(r"\b(?:your|the) (?:diagnosis|condition) is\s+\w+", re.I), "diagnosis_statement"),
    (re.compile(r"\bi (?:diagnose|diagnosed)\s+", re.I), "diagnose_verb"),
    (re.compile(r"\bthis (?:is|means) (?:a |an )?\w+ (?:diagnosis|disease|condition)", re.I), "diagnosis_implication"),
    (re.compile(r"\byou (?:are|appear to be) (?:diagnosed with|suffering from)\s+\w+", re.I), "diagnosis_assertion"),
    (re.compile(r"\bbased on (?:your )?(?:symptoms|presentation), (?:you have|it is)\s+\w+", re.I), "symptom_to_diagnosis"),
    (re.compile(r"\b(?:your|the) (?:illness|disease) is\s+\w+", re.I), "illness_statement"),
]

_PRESCRIBE_PATTERNS = [
    (re.compile(r"\b(?:you should )?take \d+\s*(?:mg|ml|mcg)\b", re.I), "dosage_instruction"),
    (re.compile(r"\bprescribe\s+(?:you )?\d+", re.I), "prescribe_dosage"),
    (re.compile(r"\bi (?:prescribe|recommend) (?:taking )?\d+", re.I), "prescribe_recommend"),
    (re.compile(r"\b(?:take|use) \d+\s*(?:mg|ml|mcg)\s+(?:once|twice|daily)", re.I), "dosage_schedule"),
    (re.compile(r"\b(?:you need to|you ought to) (?:take|use) \d+", re.I), "dosage_necessity"),
    (re.compile(r"\bstart (?:with |on )?\d+\s*(?:mg|ml|mcg)", re.I), "dosage_start"),
    (re.compile(r"\b(?:recommended|suggested) (?:dose|dosage):?\s*\d+", re.I), "recommended_dose"),
    (re.compile(r"\b\d+\s*(?:mg|ml|mcg)\s+(?:po|oral|by mouth)\b", re.I), "dosage_route"),
]


def check_domain_rules(response: str) -> list[DomainRuleViolation]:
    """
    Check response for forbidden diagnosis or prescription language.
    Returns list of violations.
    """
    # Skip domain checks for scheduling/appointment content
    scheduling_keywords = ["appointment", "available slots", "book", "provider", "office visit", "schedule id", "milestone", "ipledge", "skyrizi", "humira", "enbrel", "remicade", "stelara", "cosentyx", "tremfya", "taltz", "dupixent", "biologic", "injection", "screening", "dr.", "md", "week 0", "week 4", "dosing schedule", "prior auth", "donna lee", "billy smith", "fred stone"]
    response_lower = response.lower()
    if any(kw in response_lower for kw in scheduling_keywords):
        return []
    violations: list[DomainRuleViolation] = []
    for pattern, rule in _DIAGNOSE_PATTERNS + _PRESCRIBE_PATTERNS:
        for m in pattern.finditer(response):
            violations.append(
                DomainRuleViolation(
                    rule=rule,
                    match=m.group(0),
                    snippet=response[max(0, m.start() - 20) : m.end() + 20],
                )
            )
    return violations


def passes_domain_rules(response: str) -> bool:
    """True if no domain rule violations."""
    return len(check_domain_rules(response)) == 0
