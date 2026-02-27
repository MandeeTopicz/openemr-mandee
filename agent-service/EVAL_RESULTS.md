# CareTopicz Eval Results

## Summary

- **Total cases:** 92
- **Passed:** 92
- **Failed:** 0
- **Pass rate:** 100.0% (gate threshold: 80%)

## Dataset Breakdown

| Dataset | Cases | Passed | Failed |
|---------|-------|--------|--------|
| MVP | 8 | 8 | 0 |
| Correctness | 26 | 26 | 0 |
| Edge Cases | 17 | 17 | 0 |
| Multi-Step | 13 | 13 | 0 |
| Adversarial | 16 | 16 | 0 |
| Med Schedule (Bounty) | 12 | 12 | 0 |
| **Total** | **92** | **92** | **0** |

## Tools Covered

11 tools tested across all datasets:
- Drug interaction check
- Symptom lookup
- Provider search (NPI + OpenEMR)
- Insurance provider search
- Patient education generator
- Medication schedule coordinator (iPLEDGE, biologics)
- Appointment availability
- General medical knowledge
- Domain safety (refusals)
- Multi-step reasoning (tool chains)
- Adversarial/prompt injection resistance

## Run Command
```bash
cd agent-service
docker exec development-easy-agent-1 rm -rf /app/evals
docker cp evals development-easy-agent-1:/app/evals
docker exec development-easy-agent-1 python /app/evals/runner.py --all --verbose --url http://localhost:8000 --min-pass-rate 0.8
```
