# CareTopicz Agent Service

Python FastAPI sidecar for OpenEMR — AI clinical assistant with drug interaction checks, symptom analysis, and more.

## Quick Start

```bash
cd agent-service
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- **API docs:** http://localhost:8000/docs
- **Health:** http://localhost:8000/health
- **Chat:** POST http://localhost:8000/chat

## Evals

Run test cases against the agent (service must be running):

```bash
cd agent-service
uvicorn app.main:app --host 0.0.0.0 --port 8000 &  # start agent
python evals/runner.py                    # MVP only (8 cases)
python evals/runner.py --all              # All 60+ cases (correctness, edge, adversarial, multi_step)
python evals/runner.py --dataset evals/datasets/correctness.json --verbose
```

Datasets in `evals/datasets/`:
- `mvp.json` — 8 MVP cases
- `correctness.json` — 22 happy path
- `edge_cases.json` — 11 edge cases
- `adversarial.json` — 10 adversarial inputs
- `multi_step.json` — 10 multi-step scenarios

## CI

GitHub Actions (`.github/workflows/agent-ci.yml`) runs on push/PR when `agent-service/**` changes:

1. **Lint** — ruff check
2. **Test** — pytest (unit + integration; e2e requiring API key are skipped without it)
3. **Eval** — full eval suite with **80% pass rate gate** (merge blocked if below). Requires `ANTHROPIC_API_KEY` repo secret.
4. **Build** — Docker image build

Eval locally with gate: `python evals/runner.py --all --min-pass-rate 0.8`

## Development

See [DEVELOPMENT_PLAN.md](../DEVELOPMENT_PLAN.md) and `/docs` for full project plan.
