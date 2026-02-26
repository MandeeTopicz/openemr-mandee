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
- **correctness.json** — 22 happy-path correctness cases.
- **edge_cases.json** — 11 edge cases (empty, long, ambiguous, no-tool).
- **adversarial.json** — 10 adversarial inputs (prompt injection, jailbreak, exfiltration, system prompt).
- **multi_step.json** — 10 multi-step reasoning cases (2+ tools).

**Total: 61 cases.**

## Usage

From the `agent-service` directory:

```bash
# Run all datasets (in-process, no server)
python evals/runner.py --all

# Run one dataset
python evals/runner.py --dataset evals/datasets/mvp.json

# With 80% pass gate (CI)
python evals/runner.py --all --min-pass-rate 0.8
```

## Standalone Use

You can copy this directory (including `LICENSE.md`) to another repo or publish to Zenodo for standalone use. Attribute: "CareTopicz Eval Datasets (CC BY 4.0)."
