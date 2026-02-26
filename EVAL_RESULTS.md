# CareTopicz Eval Results

Results from running the full eval suite (76 cases across 5 datasets). Regenerate by running:

```bash
cd agent-service
pip install -r requirements.txt
python evals/runner.py --all --verbose
```

---

## Overall Results

| Metric | Value |
|--------|--------|
| **Total cases** | 76 |
| **Passed** | 76 |
| **Failed** | 0 |
| **Pass rate** | 100% |
| **CI gate (80%)** | Pass rate ≥ 80% required for merge — **passed** |

---

## Breakdown by Dataset

| Dataset | Cases | Passed | Failed | Pass rate |
|---------|-------|--------|--------|-----------|
| mvp.json | 8 | 8 | 0 | 100% |
| correctness.json | 22 | 22 | 0 | 100% |
| edge_cases.json | 17 | 17 | 0 | 100% |
| multi_step.json | 13 | 13 | 0 | 100% |
| adversarial.json | 16 | 16 | 0 | 100% |

---

## Query Types / Categories

- **MVP:** Basic drug interaction, symptom, provider, appointment, insurance queries.
- **Correctness:** Happy-path medical information and tool use.
- **Edge cases:** Empty input, very long input, ambiguous questions, no-tool questions.
- **Adversarial:** Prompt injection, jailbreak, data exfiltration, system prompt reveal attempts.
- **Multi-step:** Queries that require chaining 2+ tools (e.g. drug check + provider search).

---

## Notable Failures

None. All 76 cases passed.

---

## Comparison to 80% CI Gate

- **Threshold:** 80% (61/76 must pass).
- **Result:** 100% pass rate — gate **passed**.

---

*Last run: full suite — 76/76 passed, 100% pass rate.*
