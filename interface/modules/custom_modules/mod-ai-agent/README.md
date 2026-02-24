# CareTopicz AI Agent Module

OpenEMR module that embeds the CareTopicz AI assistant (Python FastAPI agent service).

## Requirements

- OpenEMR 7.0+
- CareTopicz agent service running (default: http://localhost:8000)

## Installation

1. **Register the module** in OpenEMR: Admin → Modules → Register
2. **Enable** the module
3. **Start the agent service** from the `agent-service/` directory:
   ```bash
   cd agent-service && uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

## Configuration

Optional globals (Administration → Config):

- `ai_agent_base_url` – Agent service URL (default: http://localhost:8000)
- `ai_agent_enabled` – Set to 0 to disable the chat widget

## Usage

A floating chat button appears on the patient dashboard and main pages. Click to open the chat panel and ask about drug interactions, symptoms, providers, appointments, or insurance.
