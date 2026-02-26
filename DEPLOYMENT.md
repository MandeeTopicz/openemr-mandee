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

## Production Docker Compose (agent only)

For deploying only the agent service (e.g. alongside an existing OpenEMR instance):

```yaml
# docker-compose.agent.yml — agent + Redis (optional)
services:
  agent:
    build: ./agent-service
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENEMR_FHIR_BASE_URL=${OPENEMR_FHIR_BASE_URL}
      - OPENEMR_FHIR_TOKEN=${OPENEMR_FHIR_TOKEN}
      - CORS_ORIGINS=${CORS_ORIGINS:-http://localhost:8300}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
```

Build and run: `docker compose -f docker-compose.agent.yml up -d`. Set env vars in `.env` or the host.

---

## Health Check & Monitoring

- **Agent**: `GET /health` → `{"status":"healthy","service":"CareTopicz Agent","version":"0.1.0"}`
- **OpenEMR**: `GET /meta/health/readyz` (or your deployment health endpoint)

Use these for load balancer or platform health probes. For operational monitoring, use LangSmith (when `LANGCHAIN_TRACING_V2=true`) for latency, token usage, and error tracking.

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

---

## Option C: GCP (Single VM, e.g. 34.139.68.240)

Deploy the full stack on a single GCP VM (e.g. Compute Engine) so OpenEMR is reachable at `http://<VM_IP>:8300`. The chat widget may return **502** if the agent is unreachable from OpenEMR.

### Why 502 happens

The PHP module returns **502 Bad Gateway** when the agent proxy throws (connection refused, timeout, or invalid response). So 502 means: **OpenEMR could not get a valid response from the agent service**.

### Checklist (run on the GCP VM)

1. **Agent container running and healthy**
   ```bash
   cd /path/to/repo/docker/development-easy
   docker compose ps
   ```
   Ensure `agent` and `openemr` are `Up` and (if applicable) `healthy`.

2. **Agent URL from OpenEMR**
   - With this repo’s `docker-compose.yml`, OpenEMR gets `OPENEMR_AI_AGENT_URL=http://agent:8000` (Docker network).
   - From inside the OpenEMR container, the agent must be reachable at that URL:
   ```bash
   docker compose exec openemr curl -s -o /dev/null -w "%{http_code}" http://agent:8000/health
   ```
   Expect `200`. If you see connection refused or timeout, the agent is not reachable from OpenEMR.

3. **Ports and firewall**
   - OpenEMR: port **8300** (and 9300 if HTTPS) must be open on the VM firewall and to the internet if you need public access.
   - Agent port 8000 does **not** need to be public; OpenEMR talks to it over the Docker network (`http://agent:8000`).

4. **Agent env (API key)**
   - Ensure `agent-service/.env` (or env_file in compose) has a valid `ANTHROPIC_API_KEY`. If the key is missing or invalid, `/chat` may return 500/503 from the agent; the proxy can surface that as 502.

5. **PHP error log**
   - On 502, check OpenEMR/PHP logs. The controller logs: `AIAgent chat error: <message>` (e.g. "Connection refused", "timed out"). That confirms the failure is between OpenEMR and the agent.

### Diagnostic script

From the repo root, run:

```bash
./scripts/check-caretopicz-deployment.sh
```

This script checks: agent container up, agent health endpoint from host and (if possible) from OpenEMR container, and reports the current `OPENEMR_AI_AGENT_URL` seen by OpenEMR. See [scripts/check-caretopicz-deployment.sh](scripts/check-caretopicz-deployment.sh).

### After fixing

Test the chat with at least three different queries (e.g. drug interaction, symptom lookup, appointment question). Once 502 is resolved, the widget should return verified responses. Use [DEMO_SCRIPT.md](DEMO_SCRIPT.md) for sample queries.

---

## Summary

| Method | Public URL | Use Case |
|--------|------------|----------|
| ngrok | `https://xxx.ngrok-free.app` | Quick demo, no cloud account |
| Railway | `https://xxx.railway.app` | Persistent demo, free tier |
| Render | `https://xxx.onrender.com` | Persistent demo, free tier |
| GCP VM | `http://<VM_IP>:8300` | Persistent demo, single VM (see Option C for 502 fix) |
