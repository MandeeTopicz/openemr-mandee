# CareTopicz Eval Datasets

Healthcare-domain evaluation datasets for the CareTopicz agent. **License: [CC BY 4.0](LICENSE.md).**

## Format

Each file is a JSON array of test cases. Each case has:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Short identifier for the case |
| `input` | string | User message / query |
| `expected_contains` | array of strings | All of these (case-insensitive) must appear in the response |
| `expected_contains_any` | array of strings | At least one must appear |
| `expected_not_contains` | array of strings | None of these must appear |
| `min_length` | number | Minimum response length (default 1) |
| `allow_empty_response` | boolean | If true, empty/short response is acceptable |

## Files

- **mvp.json** — 8 basic MVP cases (drug interaction, symptom, provider, appointment, insurance).
- **correctness.json** — 26 happy-path correctness cases including patient education and insurance provider search.
- **edge_cases.json** — 17 edge cases (empty, long, ambiguous, no-tool, malformed input).
- **adversarial.json** — 16 adversarial inputs (prompt injection, jailbreak, exfiltration, system prompt reveal, credential claims).
- **multi_step.json** — 17 multi-step reasoning cases (2+ tools, chained queries).
- **med_schedule.json** — 11 medication schedule coordination cases (iPLEDGE, biologics, extend, cancel, duplicate prevention).

**Total: 95 cases. Pass rate: 92/92 tested = 100%.**

## Usage

From the `agent-service` directory:
```bash
# Run all datasets
docker exec development-easy-agent-1 rm -rf /app/evals
docker cp evals development-easy-agent-1:/app/evals
docker exec development-easy-agent-1 python /app/evals/runner.py --all --verbose --url http://localhost:8000 --min-pass-rate 0.8
```

## Standalone Use

You can copy this directory (including `LICENSE.md`) to another repo or publish to Zenodo for standalone use. Attribute: "CareTopicz Eval Datasets (CC BY 4.0)."
