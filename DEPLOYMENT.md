# CareTopicz Deployment Guide

How to deploy OpenEMR + CareTopicz Agent for public access. Task 10 in [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md).

---

## Prerequisites

- `agent-service/.env` with `ANTHROPIC_API_KEY`
- Docker and Docker Compose installed
- mod-ai-agent module registered and enabled in OpenEMR

---

## Option A: Quick Public Demo (ngrok)

Expose your local Docker stack to the internet in under a minute.

1. **Start the stack**
   ```bash
   cd docker/development-easy
   docker compose up -d
   ```

2. **Load demo data** (if not already done)
   ```bash
   docker compose exec openemr /root/devtools dev-reset-install-demodata
   ```
   - Login: `admin` / `pass`
   - Demo credentials: [Development Demo](https://www.open-emr.org/wiki/index.php/Development_Demo#Demo_Credentials)

3. **Install ngrok** and get a free auth token from [ngrok.com](https://ngrok.com)

4. **Expose OpenEMR**
   ```bash
   ngrok http 8300
   ```
   ngrok will output a public URL such as `https://abc123.ngrok-free.app` — share that for demo access.

5. **Verify health**
   - OpenEMR: `https://<ngrok-url>/` — login works
   - Agent health (internal): `curl http://localhost:8000/health`

---

## Option B: Cloud Deploy (Railway / Render)

Deploy the full stack to a cloud provider for a persistent public URL.

### Railway

1. Create a [Railway](https://railway.app) project and connect your repo.
2. Add services:
   - **OpenEMR**: Use `openemr/openemr:flex` or build from repo
   - **MySQL**: Add Railway MySQL plugin or use external
   - **Agent**: Build from `agent-service/Dockerfile`, set `ANTHROPIC_API_KEY`, `OPENEMR_FHIR_BASE_URL`
   - **Redis**: Add Redis plugin
3. Set `OPENEMR_AI_AGENT_URL` on OpenEMR to the agent service URL (e.g. `http://agent:8000` or Railway-assigned URL).
4. Configure OpenEMR `site_addr_oath` (Admin > Config > Connectors) to your public Railway URL.
5. Load demo data via devtools or setup wizard.

### Render

1. Create a [Render](https://render.com) account.
2. New Web Service:
   - Connect repo
   - Build: Docker, use `docker/development-easy/docker-compose.yml` or a production Dockerfile
   - Env: `ANTHROPIC_API_KEY`, `OPENEMR_FHIR_BASE_URL`, etc.
3. For multi-container, use Render Compose or separate services for OpenEMR, Agent, MySQL, Redis.
4. Set public URL in OpenEMR site address and agent `CORS_ORIGINS`.

### Environment Variables (Production)

| Variable | Description | Example |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Claude API key (required) | `sk-ant-...` |
| `OPENEMR_FHIR_BASE_URL` | OpenEMR FHIR API (agent → OpenEMR) | `https://your-openemr.com/apis/default/fhir` |
| `OPENEMR_FHIR_VERIFY_SSL` | SSL verify for FHIR | `true` |
| `CORS_ORIGINS` | Comma-separated origins for agent | `https://your-openemr.com` |
| `OPENEMR_AI_AGENT_URL` | Agent URL (OpenEMR PHP → agent) | `http://agent:8000` |

---

## Health Check

- **Agent**: `GET /health` → `{"status":"healthy","service":"CareTopicz Agent"}`
- **OpenEMR**: `GET /meta/health/readyz` (or your deployment health endpoint)

Use these for load balancer or platform health probes.

---

## Demo-Ready Setup

1. Load sample patient data:
   ```bash
   docker compose exec openemr /root/devtools dev-reset-install-demodata
   ```

2. Enable mod-ai-agent (Admin → Other → Manage Modules → CareTopicz AI Agent → Enable).

3. Open a patient dashboard — the floating chat button should appear at bottom-right.

4. Test the agent: e.g. "Do lisinopril and ibuprofen interact?"

---

## Summary

| Method | Public URL | Use Case |
|--------|------------|----------|
| ngrok | `https://xxx.ngrok-free.app` | Quick demo, no cloud account |
| Railway | `https://xxx.railway.app` | Persistent demo, free tier |
| Render | `https://xxx.onrender.com` | Persistent demo, free tier |
