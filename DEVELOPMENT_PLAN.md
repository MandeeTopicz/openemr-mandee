# CareTopicz Development Plan

This file is the single source of truth for the development roadmap. Reference this file at the start of every Cursor session. All three planning docs (PRD, Architecture, Pre-Search) should also be in this repo under `/docs`.

---

## Project Context

- **Project:** CareTopicz — AI agent integration for OpenEMR
- **Repo:** Forked OpenEMR with a Python sidecar agent service
- **OpenEMR:** Running locally via Docker at http://localhost:8300/
- **FHIR API:** Confirmed working at http://localhost:8300/apis/default/fhir/
- **Agent Service:** Python/FastAPI at http://localhost:8000/ (once running)

## Reference Docs (in /docs)

- `OpenEMR_CareTopicz_PRD.md` — Full product requirements, all 5 phases
- `OpenEMR_Agent_Architecture.md` — System design, directory structure, data flow
- `OpenEMR_PreSearch_Document.md` — Stack decisions, constraints, checklist

---

## Phase 1: MVP (24 Hours)

**Goal:** Basic agent with 5 tools, verification, deployed and accessible.

**Hard gate. All items required to pass:**
- [ ] Agent responds to natural language queries in healthcare domain
- [ ] At least 5 functional tools the agent can invoke
- [ ] Tool calls execute successfully and return structured results
- [ ] Agent synthesizes tool results into coherent responses
- [ ] Conversation history maintained across turns
- [ ] Basic error handling (graceful failure, not crashes)
- [ ] At least one domain-specific verification check
- [ ] Simple evaluation: 5+ test cases with expected outcomes
- [ ] Deployed and publicly accessible

**Build order (follow strictly):**

### Task 1: FastAPI Skeleton
- [x] `/health` endpoint returning service status
- [x] `/chat` endpoint (placeholder, accepts message, returns mock response)
- [x] CORS configured for localhost:8300
- [x] Pydantic request/response schemas
- [x] Environment config via pydantic-settings (.env)
- [x] requirements.txt with all dependencies

### Task 2: LangGraph Minimal Graph
- [x] Basic state machine: input -> reasoning -> output
- [x] Claude (Anthropic) as LLM
- [x] AgentState TypedDict schema defined
- [x] No tools yet — just prove the graph works end-to-end

### Task 3: First Tool — drug_interaction_check
- [x] RxNorm API client (app/clients/rxnorm.py)
- [x] Drug interaction tool (app/tools/drug_interaction.py)
- [x] Tool registered in registry
- [x] LangGraph updated to support tool selection and execution
- [x] End-to-end test: ask about drug interaction, get real RxNorm data back

### Task 4: LangSmith Integration
- [x] Tracing configured (app/observability/langsmith.py)
- [x] Every request traced: input, reasoning, tool calls, output
- [x] Verify traces visible in LangSmith dashboard (when LANGCHAIN_TRACING_V2=true)
- [x] PHI redaction callback configured

### Task 5: Remaining MVP Tools (one at a time)
- [x] symptom_lookup (app/tools/symptom_lookup.py)
- [x] provider_search (app/tools/provider_search.py) — OpenEMR FHIR + NPI Registry
- [x] appointment_check (app/tools/appointment_check.py) — OpenEMR FHIR
- [x] insurance_coverage (app/tools/insurance_coverage.py) — OpenEMR FHIR
- [x] Each tool: Pydantic schema, error handling, registered in registry
- [x] OpenEMR FHIR client (app/clients/openemr.py) for tools that query OpenEMR

### Task 6: Verification Layer
- [x] Fact checker (app/verification/fact_checker.py)
- [x] Confidence scoring (app/verification/confidence.py)
- [x] Verifier node added to LangGraph state machine (post-processing in invoke_graph)
- [x] Responses gated by confidence threshold (>=0.9 direct, 0.7-0.9 caveats, 0.5-0.7 disclaimer, <0.5 refuse)
- [x] Domain rules enforced (never diagnose, never prescribe)

### Task 7: OpenEMR Module
- [x] PHP module scaffolded in interface/modules/custom_modules/mod-ai-agent/
- [x] AgentController.php routes chat to Python service
- [x] AgentProxyService.php makes GuzzleHttp calls to FastAPI
- [x] Chat widget embedded in OpenEMR (vanilla JS floating panel)
- [x] Session auth / ACL check (CsrfUtils, AclMain)

### Task 8: Eval Framework
- [x] 5+ test cases with expected outcomes for MVP
- [x] Eval runner (evals/runner.py)
- [x] Test cases in evals/datasets/
- [x] Can run evals locally and see results

### Task 9: Docker Compose
- [x] docker-compose.yml with: OpenEMR, agent service, Redis
- [x] Agent service Dockerfile
- [x] All services communicate on internal network
- [x] One command startup: `docker compose up -d`

### Task 10: Deploy
- [x] Publicly accessible URL (ngrok / Railway / Render — see DEPLOYMENT.md)
- [x] Health check passing (GET /health)
- [x] Demo-ready with sample patient data (dev-reset-install-demodata)

---

## Phase 2: Early Submission (Days 2-4)

**Goal:** Full eval framework, observability, 50+ test cases.

### Eval Dataset Expansion
- [ ] 20+ happy path test cases (correctness.json)
- [ ] 10+ edge cases (edge_cases.json)
- [ ] 10+ adversarial inputs (adversarial.json)
- [ ] 10+ multi-step reasoning scenarios (multi_step.json)
- [ ] Each test case includes: input query, expected tool calls, expected output, pass/fail criteria
- [ ] Eval runner integrated with LangSmith SDK

### Observability Hardening
- [ ] Latency tracking breakdown (LLM time, tool time, verification time)
- [ ] Token usage and cost-per-query tracking
- [ ] Error tracking with categorization
- [ ] Historical eval scores tracked in LangSmith
- [ ] User feedback mechanism (thumbs up/down linked to traces)

### Verification Hardening
- [ ] Hallucination detection (app/verification/hallucination.py)
- [ ] Domain rules expanded (app/verification/domain_rules.py)
- [ ] All three verification checks passing evals

### CI Pipeline
- [ ] GitHub Actions workflow: lint (ruff) -> test (pytest) -> eval (LangSmith) -> build
- [ ] Eval gate: blocks merge if pass rate < 80%

---

## Phase 3: Final Submission (Days 5-7)

**Goal:** Production-ready, all tools, open source release.

### Post-MVP Tools
- [ ] patient_summary (app/tools/patient_summary.py)
- [ ] lab_results_lookup (app/tools/lab_results.py)
- [ ] medication_list (app/tools/medication_list.py)
- [ ] Each follows same base class pattern as MVP tools

### Multi-Step Workflows
- [ ] Agent chains 3+ tools in single query
- [ ] Intermediate verification between tool calls
- [ ] Partial results returned on tool failure
- [ ] Latency target: < 15 seconds for 3+ tool chains

### Adversarial Hardening
- [ ] Prompt injection attempts blocked
- [ ] Jailbreak attempts blocked
- [ ] Data exfiltration attempts blocked
- [ ] System prompt reveal attempts blocked

### Performance
- [ ] Single-tool queries: < 5 seconds
- [ ] Multi-step queries: < 15 seconds
- [ ] Tool success rate: > 95%
- [ ] Eval pass rate: > 80%

### Deployment
- [ ] Docker Compose production config
- [ ] Publicly accessible demo with sample data
- [ ] Health monitoring operational

### Open Source Release
- [ ] README with quickstart (Docker Compose one-command setup)
- [ ] Architecture doc in repo
- [ ] API reference for agent service endpoints
- [ ] Tool development guide (how to add new tools)
- [ ] Eval dataset published (CC BY 4.0)
- [ ] Module compatible with OpenEMR upstream (GPL-2.0)

### Submission Deliverables
- [ ] GitHub repo with setup guide and deployed link
- [ ] Demo video (3-5 min): agent in action, eval results, observability dashboard
- [ ] Pre-Search document (completed)
- [ ] Agent Architecture doc (1-2 pages)
- [ ] AI Cost Analysis: actual dev spend + projections for 100/1K/10K/100K users
- [ ] Eval dataset: 50+ test cases with results
- [ ] Open source: published module + eval dataset
- [ ] Deployed application: publicly accessible
- [ ] Social post on X or LinkedIn

---

## Future Phases (Architecture Must Support, Do Not Build Yet)

### Phase 2 PRD (v1.1-1.5): Enhanced Intelligence
- Clinical decision support (proactive alerts)
- Contextual awareness (detect current OpenEMR screen)
- Medical document summarization
- Natural language search across patient records
- Conversation export to clinical notes

### Phase 3 PRD (v2.0): Read-Write Actions
- Appointment scheduling (write to OpenEMR calendar)
- Prescription assistance (pre-fill forms, clinician approves)
- Referral generation
- Order entry assistance
- Clinical note drafting (SOAP format)
- Bulk operations (population health queries)
- ALL write actions require explicit clinician approval

### Phase 4 PRD (v3.0): Patient Portal
- Patient-facing symptom triage (stricter guardrails, simpler language)
- Patient self-scheduling
- Patient medication and lab questions
- Insurance and billing questions
- Separate verification rules for patient-facing responses

### Phase 5 PRD (v4.0): Multi-Tenant Enterprise
- Per-institution configuration (verification thresholds, tool enable/disable)
- Role-based agent permissions mapped to OpenEMR ACL
- Analytics and reporting dashboard
- Agent marketplace for community tools

---

## Development Rules

1. **Every new tool** follows the base class pattern in app/tools/base.py
2. **Every tool** has a Pydantic schema for input validation
3. **Every tool** is registered in app/tools/registry.py
4. **Every response** passes through the verification layer before reaching the user
5. **Every request** is traced in LangSmith
6. **No patient PII** is sent to external LLM APIs
7. **Re-read the PRD and Architecture docs** at the start of every new session
8. **Do not deviate** from the established LangGraph state machine pattern
9. **Test each tool** in isolation before integrating into the graph
10. **One tool at a time** — verify it works before moving to the next
