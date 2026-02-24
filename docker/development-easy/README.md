### Easy Development Docker Environment
The instructions for The Easy Development Docker environment can be found at [CONTRIBUTING.md](../../CONTRIBUTING.md#code-contributions-local-development).

### CareTopicz Agent Service
The compose stack includes the CareTopicz AI agent (port 8000) and Redis. Ensure `agent-service/.env` exists with `ANTHROPIC_API_KEY` for the agent to handle chat requests. Start with:

```bash
docker compose up -d
```

- OpenEMR: http://localhost:8300
- Agent: http://localhost:8000 (health: `/health`)
