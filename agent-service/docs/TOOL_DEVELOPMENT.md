# Tool Development Guide

How to add a new tool to the CareTopicz agent.

## Pattern

Each tool has:

1. **Input schema** — Pydantic model in `app/tools/<name>.py`
2. **Core function** — Returns a `dict` with `success`, and either result data or `error`
3. **Formatter** — Converts that dict to a string for the LLM (in `app/tools/registry.py`)
4. **Registration** — Wrapped as a LangChain `StructuredTool` and added to `get_tools()`

## Steps

### 1. Create the tool module

Create `app/tools/my_tool.py`:

```python
from typing import Any
from pydantic import BaseModel, Field

from app.clients.openemr import fhir_get  # or other client

class MyToolInput(BaseModel):
    """Input schema for my_tool."""
    required_param: str = Field(..., description="...")
    optional_param: str | None = Field(default=None, description="...")

def my_tool(required_param: str, optional_param: str | None = None) -> dict[str, Any]:
    """Do the work. Return dict with success, and either result data or error."""
    data = ...  # call FHIR or external API
    if data is None:
        return {"success": False, "error": "Config or API unavailable.", "results": []}
    return {
        "success": True,
        "results": [...],
        "source": "OpenEMR FHIR MyResource",
    }
```

### 2. Register in registry

In `app/tools/registry.py`:

- Import the input schema and the function.
- Add a `_format_my_tool_result(data: dict) -> str` that turns the dict into readable text for the LLM.
- Add `_run_my_tool(...)` that calls your function and returns the formatted string.
- Add `_build_my_tool_tool()` returning `StructuredTool.from_function(..., name="my_tool", description="...", args_schema=MyToolInput)`.
- Append `_build_my_tool_tool()` to the list in `get_tools()`.

### 3. Description

The `description` is used by the LLM to decide when to call the tool. Include:

- When to use it (e.g. "Use when the user asks about X").
- Input meaning (e.g. "Input: patient_id (required)").

### 4. Verification

All tool output is passed through the verification layer (fact check, confidence, domain rules, hallucination). Avoid returning raw PII; use summaries or redacted text when possible.

### 5. Tests

Add unit tests in `tests/unit/` and, if needed, integration tests in `tests/integration/` that call the tool with mocked or real APIs.

## Existing examples

- **OpenEMR FHIR:** `appointment_check.py`, `insurance_coverage.py`, `patient_summary.py`, `lab_results_lookup.py`, `medication_list.py`
- **External API:** `drug_interaction.py` (RxNorm), `provider_search.py` (FHIR + NPI)
- **Static/data:** `symptom_lookup.py`

## OpenEMR client

Add new FHIR helpers in `app/clients/openemr.py` (e.g. `fhir_get("MyResource", params=...)`) and keep tokens and base URL in `app/config.py` (`openemr_fhir_base_url`, `openemr_fhir_token`).
