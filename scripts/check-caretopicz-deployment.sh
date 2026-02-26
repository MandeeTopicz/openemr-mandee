#!/usr/bin/env bash
# CareTopicz deployment diagnostic — run on the host (e.g. GCP VM) to verify agent + OpenEMR.
# Usage: from repo root, ./scripts/check-caretopicz-deployment.sh

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_DIR="${REPO_ROOT}/docker/development-easy"
AGENT_URL_HOST="http://127.0.0.1:8000"

echo "=== CareTopicz deployment check ==="
echo "Repo root: ${REPO_ROOT}"
echo ""

if [[ ! -f "${COMPOSE_DIR}/docker-compose.yml" ]]; then
  echo "ERROR: docker-compose not found at ${COMPOSE_DIR}. Run from repo root."
  exit 1
fi

cd "${COMPOSE_DIR}"

echo "--- 1. Docker Compose services ---"
docker compose ps
echo ""

echo "--- 2. Agent health from host (${AGENT_URL_HOST}) ---"
if curl -s -f -o /dev/null --connect-timeout 3 "${AGENT_URL_HOST}/health" 2>/dev/null; then
  echo "OK: Agent /health returned 200"
  curl -s "${AGENT_URL_HOST}/health" | head -c 200
  echo ""
else
  echo "FAIL: Cannot reach agent at ${AGENT_URL_HOST}. Is the agent container running and port 8000 exposed?"
fi
echo ""

echo "--- 3. Agent URL as seen by OpenEMR (OPENEMR_AI_AGENT_URL) ---"
OPENEMR_AGENT_URL=$(docker compose exec -T openemr env 2>/dev/null | grep OPENEMR_AI_AGENT_URL || true)
if [[ -n "${OPENEMR_AGENT_URL}" ]]; then
  echo "${OPENEMR_AGENT_URL}"
else
  echo "Could not read env from openemr container (container may not be running)."
fi
echo ""

echo "--- 4. Agent health from inside OpenEMR container (http://agent:8000) ---"
if docker compose exec -T openemr curl -s -f -o /dev/null --connect-timeout 3 "http://agent:8000/health" 2>/dev/null; then
  echo "OK: OpenEMR container can reach agent at http://agent:8000"
else
  echo "FAIL: OpenEMR container cannot reach agent at http://agent:8000. Chat will return 502."
  echo "      Ensure agent service is up: docker compose ps"
fi
echo ""

echo "=== Done ==="
