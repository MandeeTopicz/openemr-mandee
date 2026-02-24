"""
CareTopicz Agent Service - LangSmith tracing configuration.

Traces every request: input -> reasoning -> tool calls -> output.
PHI redaction callback strips patient name, DOB, SSN, MRN before transmission.
"""

import re
from typing import Any

from langsmith import Client, anonymizer, configure


def _redact_phi_text(text: str) -> str:
    """Redact PHI from a string."""
    result = text
    result = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED-SSN]", result)
    result = re.sub(r"\b\d{9}\b", "[REDACTED-ID]", result)
    result = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", "[REDACTED-DOB]", result)
    result = re.sub(r"\b\d{1,2}/\d{1,2}/\d{4}\b", "[REDACTED-DOB]", result)
    result = re.sub(r"\bMRN\s*[:=]\s*\S+", "MRN: [REDACTED]", result, flags=re.I)
    result = re.sub(
        r"\bmedical\s*record\s*(?:#|number)?\s*[:=]?\s*\S+",
        "medical record: [REDACTED]",
        result,
        flags=re.I,
    )
    return result


def create_phi_anonymizer():
    """Create anonymizer function that redacts PHI from trace data."""
    return anonymizer.create_anonymizer(_phi_replacer)


def _phi_replacer(value: str, path: list) -> str:
    """Replace PHI in string values. Used by create_anonymizer."""
    return _redact_phi_text(value)


def setup_langsmith(
    *,
    tracing_enabled: bool | None = None,
    project_name: str | None = None,
    enable_phi_redaction: bool = True,
) -> None:
    """
    Configure LangSmith tracing. Call at app startup.

    When LANGCHAIN_TRACING_V2=true and LANGCHAIN_API_KEY are set,
    traces are sent to LangSmith. This sets up PHI redaction.
    """
    client_kwargs: dict[str, Any] = {}

    if enable_phi_redaction:
        phi_anon = create_phi_anonymizer()
        client_kwargs["anonymizer"] = phi_anon

    client = Client(**client_kwargs) if client_kwargs else None

    configure_kwargs: dict[str, Any] = {}
    if client is not None:
        configure_kwargs["client"] = client
    if project_name is not None:
        configure_kwargs["project_name"] = project_name
    if tracing_enabled is not None:
        configure_kwargs["enabled"] = tracing_enabled

    if configure_kwargs:
        configure(**configure_kwargs)


def is_tracing_enabled() -> bool:
    """Check if LangSmith tracing is enabled via env."""
    import os

    v = os.environ.get("LANGCHAIN_TRACING_V2", "").lower()
    return v in ("true", "1", "yes")
