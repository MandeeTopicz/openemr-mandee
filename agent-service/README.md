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
python evals/runner.py
# or: python evals/runner.py --dataset evals/datasets/mvp.json --url http://localhost:8000 --verbose
```

Test cases are in `evals/datasets/mvp.json`. Add `--verbose` to see full responses.

## Development

See [DEVELOPMENT_PLAN.md](../DEVELOPMENT_PLAN.md) and `/docs` for full project plan.
