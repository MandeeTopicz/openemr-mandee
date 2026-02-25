# CareTopicz Agent Service

Python FastAPI sidecar for OpenEMR — AI clinical assistant with drug interaction checks, symptom analysis, provider search, appointments, insurance, patient summary, lab results, and medication lists.

## Quick Start

**Option 1 — One-command (Docker Compose, with OpenEMR):**

```bash
cd docker/development-easy
docker compose up -d
# OpenEMR: http://localhost:8300  |  Agent health: http://localhost:8000/health
```

**Option 2 — Local Python:**

```bash
cd agent-service
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
# Set ANTHROPIC_API_KEY in .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- **API docs:** http://localhost:8000/docs
- **Health:** http://localhost:8000/health
- **Chat:** POST http://localhost:8000/chat

## Evals

Evaluation datasets and runner for testing the agent. **Total: 61 test cases** across 5 datasets.

**Datasets:** [evals/datasets/](evals/datasets/) — all eval JSON files:

| File | Description | Count |
|------|-------------|-------|
| [correctness.json](evals/datasets/correctness.json) | Happy-path correctness | 22 |
| [edge_cases.json](evals/datasets/edge_cases.json) | Edge cases | 11 |
| [adversarial.json](evals/datasets/adversarial.json) | Adversarial inputs | 10 |
| [multi_step.json](evals/datasets/multi_step.json) | Multi-step scenarios | 10 |
| [mvp.json](evals/datasets/mvp.json) | MVP smoke tests | 8 |

**Categories:** 22 correctness, 11 edge cases, 10 adversarial, 10 multi-step, 8 MVP.

**License:** Datasets are under [CC BY 4.0](evals/datasets/LICENSE.md).

### How to run

Agent service must be running (e.g. `uvicorn app.main:app --host 0.0.0.0 --port 8000`).

```bash
cd agent-service
# All 61 cases
python evals/runner.py --all

# With LangSmith logging (traces for each run)
python evals/runner.py --all --langsmith

# With 80% pass-rate gate (fails if below; used in CI)
python evals/runner.py --all --min-pass-rate 0.8
```

Single dataset / MVP only:

```bash
python evals/runner.py                                    # MVP only (8 cases)
python evals/runner.py --dataset evals/datasets/correctness.json --verbose
```

## CI

GitHub Actions (`.github/workflows/agent-ci.yml`) runs on push/PR when `agent-service/**` changes:

1. **Lint** — ruff check
2. **Test** — pytest (unit + integration; e2e requiring API key are skipped without it)
3. **Eval** — full eval suite with **80% pass rate gate** (merge blocked if below). Requires `ANTHROPIC_API_KEY` repo secret.
4. **Build** — Docker image build

Eval locally with gate: `python evals/runner.py --all --min-pass-rate 0.8`

## Performance requirements

| Requirement | Target | How to verify |
|-------------|--------|----------------|
| Single-tool queries | < 5 s | Run `python evals/timed_queries.py` (agent must be running with valid `ANTHROPIC_API_KEY`) |
| Tool success rate | > 95% | Tracked in evals and LangSmith; review eval failures and tool errors |
| Eval pass rate | > 80% | `python evals/runner.py --all --min-pass-rate 0.8` (CI gate) |
| Health check | Responds | `GET /health` returns 200 and `{"status":"healthy",...}` |

**Timed queries script** — Runs three single-tool prompts and reports response time for each:

```bash
cd agent-service
# Agent must be running with valid ANTHROPIC_API_KEY in .env
python evals/timed_queries.py --url http://localhost:8000
```

Sample queries: drug interaction (ibuprofen + aspirin), symptom lookup (chest pain, shortness of breath), provider search (cardiologist in New York).

## Documentation

- [API Reference](docs/API_REFERENCE.md) — `/health`, `/chat`, `/chat/feedback`
- [Tool Development Guide](docs/TOOL_DEVELOPMENT.md) — How to add a new tool
- [DEVELOPMENT_PLAN.md](../DEVELOPMENT_PLAN.md) — Roadmap and phases
- [docs/OpenEMR_Agent_Architecture.md](../docs/OpenEMR_Agent_Architecture.md) — System architecture
