# CareTopicz Eval Results

Results from running the full eval suite (61 cases across 5 datasets). Regenerate by running:

```bash
cd agent-service
pip install -r requirements.txt
python evals/runner.py --all --verbose
```

---

## Overall Results

| Metric | Value |
|--------|--------|
| **Total cases** | 61 |
| **Passed** | _Run evals and fill in_ |
| **Failed** | _Run evals and fill in_ |
| **Pass rate** | _Run evals and fill in_ % |
| **CI gate (80%)** | Pass rate ≥ 80% required for merge |

---

## Breakdown by Dataset

| Dataset | Cases | Passed | Failed | Pass rate |
|---------|-------|--------|--------|-----------|
| mvp.json | 8 | _fill_ | _fill_ | _%_ |
| correctness.json | 22 | _fill_ | _fill_ | _%_ |
| edge_cases.json | 11 | _fill_ | _fill_ | _%_ |
| adversarial.json | 10 | _fill_ | _fill_ | _%_ |
| multi_step.json | 10 | _fill_ | _fill_ | _%_ |

---

## Query Types / Categories

- **MVP:** Basic drug interaction, symptom, provider, appointment, insurance queries.
- **Correctness:** Happy-path medical information and tool use.
- **Edge cases:** Empty input, very long input, ambiguous questions, no-tool questions.
- **Adversarial:** Prompt injection, jailbreak, data exfiltration, system prompt reveal attempts.
- **Multi-step:** Queries that require chaining 2+ tools (e.g. drug check + provider search).

---

## Notable Failures

_Document any recurring failures and likely causes (e.g. rate limits, flaky tool, assertion too strict):_

- _Example: "adversarial/system_prompt_reveal fails when model occasionally echoes structure"_
- _Example: "multi_step/query_X fails under load due to timeout"_

---

## Comparison to 80% CI Gate

- **Threshold:** 80% (49/61 must pass).
- **Result:** _Pass rate from run_ — gate **passed** / **failed**.

---

*Last run: _date and command_.*
