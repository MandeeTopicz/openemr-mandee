# AgentForge Pre-Search Document
## OpenEMR AI Agent Integration

**Project:** OpenEMR Healthcare AI Agent  
**Author:** Mandee  
**Date:** February 2026  
**Repository:** [OpenEMR](https://github.com/openemr/openemr) (Fork)

---

## Stack Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Domain | Healthcare (OpenEMR) | High-stakes, strong verification requirements, real-world impact |
| Agent Framework | LangGraph | State machines for healthcare verification loops, native LangSmith integration |
| LLM | Claude (Anthropic) | Cautious medical reasoning, strong tool calling, competitive pricing |
| Observability | LangSmith | Native LangGraph integration, built-in evals, cost tracking |
| Backend | Python 3.11+ / FastAPI | Best AI/ML ecosystem, async support, LangGraph compatibility |
| Integration Pattern | OpenEMR Module + Python Sidecar | Clean separation, upstream-friendly, leverages best tools for each layer |
| Database | OpenEMR MySQL (read) + Redis (memory) | Leverage existing data, fast session state |
| External APIs | FDA NDC, RxNorm, NPI Registry | Free, authoritative healthcare data sources |
| Deployment | Docker Compose → Railway | Containerized, reproducible, easy demo deployment |
| Testing | pytest + LangSmith Evals | Unit + integration + agent-specific evaluation |
| Open Source | OpenEMR module + eval dataset | GPL-2.0 module, CC BY 4.0 dataset |

### Tool Inventory

| Tool | Data Source | MVP | External Dependencies |
|------|-----------|-----|----------------------|
| drug_interaction_check | RxNorm API | ✅ | NIH RxNorm REST API |
| symptom_lookup | Medical knowledge base | ✅ | None (LLM reasoning + structured data) |
| provider_search | OpenEMR DB + NPI Registry | ✅ | NPI Registry API |
| appointment_check | OpenEMR calendar tables | ✅ | None (direct DB query) |
| insurance_coverage | OpenEMR billing tables | ✅ | None (direct DB query) |
| patient_summary | OpenEMR patient tables | Post-MVP | None (direct DB query) |
| lab_results_lookup | OpenEMR lab tables | Post-MVP | None (direct DB query) |
| medication_list | OpenEMR prescription tables | Post-MVP | None (direct DB query) |

### Performance Targets

| Metric | Target |
|--------|--------|
| Single-tool latency | < 5 seconds |
| Multi-step latency (3+ tools) | < 15 seconds |
| Tool success rate | > 95% |
| Eval pass rate | > 80% |
| Hallucination rate | < 5% |
| Verification accuracy | > 90% |

---

## What OpenEMR Already Provides

OpenEMR is a mature, full-featured open-source electronic medical records system. The following infrastructure exists and will be leveraged — not rebuilt.

### Existing Tech Stack

| Layer | Technology | Details |
|-------|-----------|---------|
| Backend | PHP (modern patterns) | PSR-3 logging, dependency injection via `OEGlobalsBag`, enforced by PHPStan custom rules |
| Database | MySQL/MariaDB | Full patient, encounter, prescription, billing, and calendar schema |
| HTTP Client | GuzzleHttp | Mandated by codebase (raw curl banned via PHPStan rule) |
| Logging | SystemLogger | PSR-3 compliant, centralized logging across the application |
| Static Analysis | PHPStan | Custom rules enforce modern coding patterns (no `$GLOBALS`, no `empty()`, no legacy SQL functions) |
| Package Manager | Composer | Standard PHP dependency management |
| REST API | FHIR R4 compliant | Existing endpoints for patients, encounters, medications, observations |
| Auth & ACL | Role-based access control | Granular permissions for clinical, admin, and patient portal users |
| Module System | Custom modules (`custom_modules/`) | Plugin architecture for extending OpenEMR without modifying core |
| Docker Support | Official Docker Compose | Development and production containerization already configured |
| Demo Data | Built-in sample dataset | Sample patients, medications, encounters, appointments for development |

### Existing Data We'll Query

| Data | Table/Source | What It Contains |
|------|-------------|-----------------|
| Patients | `patient_data` | Demographics, contact info, insurance |
| Medications | `prescriptions` | Active/historical prescriptions per patient |
| Encounters | `form_encounter` | Visit records, diagnoses, notes |
| Appointments | `openemr_postcalendar_events` | Calendar events, provider schedules, availability |
| Billing | `billing`, `insurance_data` | Procedure codes, insurance plans, coverage |
| Lab Results | `procedure_result` | Lab values, reference ranges, dates |
| Providers | `users` (where `authorized=1`) | Provider names, specialties, credentials |
| Audit Trail | `log` | Existing access logging for compliance |

### Existing APIs We'll Call

OpenEMR's FHIR R4 REST API already exposes endpoints for:
- `GET /fhir/Patient` — Patient search and retrieval
- `GET /fhir/MedicationRequest` — Active prescriptions
- `GET /fhir/Encounter` — Visit history
- `GET /fhir/Appointment` — Scheduling data
- `GET /fhir/Observation` — Lab results and vitals
- `GET /fhir/Practitioner` — Provider directory

These endpoints handle authentication, pagination, and data formatting. The agent service calls these rather than querying MySQL directly where possible, respecting OpenEMR's access control layer.

---

## What We're Building

Everything below is new — the AI agent layer that sits alongside OpenEMR as a sidecar service.

### New: OpenEMR Module (PHP Side)

A custom module that integrates the agent into OpenEMR's UI without modifying core files.

```
openemr/
├── interface/modules/custom_modules/
│   └── mod-ai-agent/
│       ├── moduleConfig.php            # Module registration
│       ├── openemr.bootstrap.php       # Hook into OpenEMR events
│       ├── src/
│       │   ├── Controller/
│       │   │   └── AgentController.php # Routes chat to Python service
│       │   └── Service/
│       │       └── AgentProxyService.php # GuzzleHttp calls to FastAPI
│       └── public/
│           └── chat-widget/            # React chat UI (bundled)
```

### New: Python Agent Service (FastAPI)

The core AI service that handles reasoning, tool execution, and verification.

```
agent-service/
├── app/
│   ├── main.py                    # FastAPI app, CORS, startup
│   ├── config.py                  # Environment config
│   ├── api/
│   │   ├── routes.py              # /chat, /verify, /tools, /health
│   │   └── middleware.py          # Auth, rate limiting, logging
│   ├── agent/
│   │   ├── graph.py               # LangGraph state machine definition
│   │   ├── state.py               # Agent state schema
│   │   ├── nodes/
│   │   │   ├── reasoning.py       # LLM reasoning node
│   │   │   ├── tool_selector.py   # Decides which tool to invoke
│   │   │   ├── tool_executor.py   # Runs the selected tool
│   │   │   ├── verifier.py        # Domain verification checks
│   │   │   └── formatter.py       # Structures final output
│   │   └── prompts/
│   │       ├── system.py          # Healthcare-specific system prompt
│   │       └── templates.py       # Per-tool prompt templates
│   ├── tools/
│   │   ├── registry.py            # Tool registration + schemas
│   │   ├── drug_interaction.py    # FDA/RxNorm drug interaction check
│   │   ├── symptom_lookup.py      # Symptom → condition mapping
│   │   ├── provider_search.py     # NPI registry provider lookup
│   │   ├── appointment_check.py   # OpenEMR calendar availability
│   │   ├── insurance_coverage.py  # Coverage verification
│   │   ├── patient_summary.py     # Pull patient record summary
│   │   ├── lab_results.py         # Recent lab results lookup
│   │   └── medication_list.py     # Current medications for patient
│   ├── verification/
│   │   ├── fact_checker.py        # Cross-reference claims vs sources
│   │   ├── hallucination.py       # Flag unsupported claims
│   │   ├── confidence.py          # Score response confidence
│   │   └── domain_rules.py        # Healthcare business rules
│   ├── memory/
│   │   ├── conversation.py        # Chat history management
│   │   └── context.py             # Patient context window management
│   └── observability/
│       ├── langsmith.py           # LangSmith tracing setup
│       ├── metrics.py             # Latency, token usage, cost tracking
│       └── feedback.py            # User feedback capture
├── evals/
│   ├── runner.py                  # Eval execution engine
│   ├── datasets/
│   │   ├── correctness.json       # 20+ happy path test cases
│   │   ├── edge_cases.json        # 10+ edge cases
│   │   ├── adversarial.json       # 10+ adversarial inputs
│   │   └── multi_step.json        # 10+ multi-step scenarios
│   └── scorers/
│       ├── accuracy.py
│       ├── tool_selection.py
│       └── safety.py
├── tests/
│   ├── unit/
│   └── integration/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

### New: External API Integrations

| API | Purpose | Auth | Rate Limit |
|-----|---------|------|-----------|
| RxNorm (https://rxnav.nlm.nih.gov/REST) | Drug interaction checking, medication normalization | None (free, public) | 20 req/sec |
| NPI Registry (https://npiregistry.cms.hhs.gov/api) | Provider search and credential verification | None (free, public) | Reasonable use |
| FDA NDC (https://api.fda.gov) | Drug information, adverse event data | API key (free) | 240 req/min |

### New: LangGraph State Machine

The orchestration flow for every agent query:

```
START → Parse Input → Select Tools → Execute Tool(s) → Synthesize
    → Verify Response → [Pass?] → Format Output → END
                          ↓ [Fail/Need more info]
                    Loop back to Select Tools (max 3 retries)
```

### New: Verification Layer

Three required verification checks for healthcare responses:

| Check | What It Does | When It Runs |
|-------|-------------|-------------|
| Fact Checking | Cross-references drug interaction claims against FDA/RxNorm data | Every drug-related response |
| Hallucination Detection | Compares agent claims against actual tool results | Every response |
| Confidence Scoring | Quantifies certainty; gates response delivery | Every response |

**Confidence thresholds:**
- ≥ 0.9 → Return directly
- 0.7–0.9 → Return with caveats
- 0.5–0.7 → Strong disclaimer + recommend professional consultation
- < 0.5 → Decline to answer

### New: Observability (LangSmith)

| Capability | Implementation |
|-----------|---------------|
| Trace Logging | Full trace per request: input → reasoning → tool calls → output |
| Latency Tracking | Time breakdown: LLM calls, tool execution, total response |
| Error Tracking | Capture and categorize failures with stack traces |
| Token Usage | Input/output tokens per request, cost per query |
| Eval Results | Historical scores, regression detection |
| User Feedback | Thumbs up/down linked to traces |

### New: Eval Framework

**50+ test cases organized by type:**

| Category | Count | Example |
|----------|-------|---------|
| Happy path | 20+ | "Check interactions between lisinopril and ibuprofen" → returns known interaction |
| Edge cases | 10+ | Empty medication list, unknown drug names, misspellings |
| Adversarial | 10+ | Prompt injection attempts, requests for diagnoses, scope bypass |
| Multi-step | 10+ | "Find a cardiologist near 78701 with availability next week who accepts Blue Cross" |

### New: Deployment Stack

```
┌─────────────────────────────────┐
│        Docker Compose           │
│                                 │
│  ┌───────────┐  ┌────────────┐ │
│  │  OpenEMR  │  │   Agent    │ │
│  │  (exists) │◄─┤  Service   │ │
│  │  PHP +    │  │  (new)     │ │
│  │  Apache + │  │  FastAPI   │ │
│  │  MySQL    │  └──────┬─────┘ │
│  └───────────┘         │       │
│                   ┌────┴─────┐ │
│                   │  Redis   │ │
│                   │  (new)   │ │
│                   └──────────┘ │
└─────────────────────────────────┘
         │
         ▼
  ┌──────────────┐
  │  LangSmith   │  (external SaaS, new)
  │  Dashboard   │
  └──────────────┘
```

---

## Phase 1: Domain & Constraints

### 1. Domain Selection

**Domain:** Healthcare (OpenEMR — open-source electronic medical records)

**Specific Use Cases:**
- **Drug Interaction Checking** — Clinicians input a patient's medication list and receive interaction warnings with severity levels, sourced from FDA/RxNorm data.
- **Symptom Analysis** — Natural language symptom input mapped to possible conditions with urgency scoring to support clinical triage decisions.
- **Provider Search** — Query available providers by specialty and location, cross-referencing OpenEMR's internal provider directory and the NPI Registry.
- **Appointment Availability** — Check provider calendar availability within OpenEMR for scheduling recommendations.
- **Insurance Coverage Verification** — Validate procedure coverage against patient insurance plan data stored in OpenEMR's billing tables.
- **Patient Summary Generation** — Aggregate patient demographics, active conditions, medications, and recent lab results into a concise clinical summary.
- **Lab Results Lookup** — Retrieve and contextualize recent lab results for a given patient.
- **Medication List Management** — Pull current prescriptions and flag potential issues (duplicates, contraindications).

**Verification Requirements:**
- Drug interaction claims must be cross-referenced against FDA NDC and RxNorm authoritative databases — never trust LLM-generated medical facts alone.
- Symptom-to-condition mappings require confidence scoring and mandatory disclaimers below threshold.
- All responses involving patient data must respect HIPAA-aligned access controls enforced by OpenEMR's existing ACL system.
- Agent must never diagnose or prescribe — it assists clinical decision-making only.

**Data Sources:**
- OpenEMR MySQL database (patients, encounters, prescriptions, billing, calendar)
- FDA National Drug Code (NDC) Directory API
- NIH RxNorm API (drug interactions, normalization)
- NPI Registry API (National Provider Identifier lookup)
- OpenEMR's existing FHIR R4 REST API

---

### 2. Scale & Performance

**Expected Query Volume:**
- Development/demo: 10–50 queries/day
- MVP target: 100 concurrent users
- Production projection: up to 10,000 users (see cost analysis)

**Acceptable Latency:**
- Single-tool queries: < 5 seconds end-to-end
- Multi-step reasoning (3+ tool chains): < 15 seconds
- Target: sub-3-second for simple lookups (appointment availability, medication list)

**Concurrent User Requirements:**
- FastAPI with async endpoints handles concurrency natively
- Redis for session/memory state prevents bottlenecks
- LLM API calls are the primary latency constraint — mitigated by streaming responses

**Cost Constraints:**
- Development budget: ~$50–100 in LLM API costs during sprint (~500-2,000 queries at $0.01-0.10 each).
- External APIs: $0 — RxNorm, NPI, and FDA APIs are all free/public.
- LangSmith: $0 — free tier covers 5,000 traces/month, sufficient for development.
- Infrastructure: $0–20 — Railway free tier for demo, OpenEMR Docker runs locally.
- Total estimated development sprint cost: $50–120.
- Production projections: 100 users ~$190–520/month, 1,000 users ~$1,600–4,700/month, 10,000 users ~$15,600–46,000/month. See PRD for detailed breakdown and optimization strategies.

---

### 3. Reliability Requirements

**Cost of a Wrong Answer:**
- **Drug interactions:** Potentially life-threatening. A missed interaction between medications could lead to adverse events. This is the highest-stakes tool and requires mandatory verification.
- **Symptom analysis:** Could cause unnecessary panic or, worse, false reassurance. Requires confidence scoring and explicit disclaimers.
- **Scheduling/insurance:** Low clinical risk but impacts patient experience and operational efficiency.

**Non-Negotiable Verification:**
- Drug interaction results must be verified against authoritative sources (FDA/RxNorm) before being returned to the user.
- The agent must never present LLM-generated medical claims without source attribution.
- Confidence scores below 0.5 trigger a refusal to answer with a recommendation to consult a healthcare provider.

**Human-in-the-Loop Requirements:**
- High-risk responses (drug interactions with severity "major") include an escalation flag suggesting provider review.
- The agent does not take actions (prescribe, schedule, modify records) — it only provides information and recommendations.
- Future iteration: configurable escalation triggers per institution.

**Audit/Compliance Needs:**
- Full trace logging of every agent interaction (input, reasoning, tool calls, output) via LangSmith.
- All traces are timestamped and tied to user session IDs.
- Patient data access logged through OpenEMR's existing audit trail system.
- No patient data is sent to external LLM APIs — only de-identified queries or structured tool parameters.

---

### 4. Team & Skill Constraints

**Familiarity with Agent Frameworks:**
- Prior experience building an AI agent with OpenAI function calling (Vellum project — collaborative whiteboard with AI agent backend using Firebase Cloud Functions). Built tool definitions, conversation history management, and multi-step execution handling.
- First time using LangGraph/LangChain — pre-search research completed on framework capabilities. The state machine paradigm maps conceptually to the existing agent architecture experience.

**Experience with Healthcare Domain:**
- Working with OpenEMR codebase (PHP, MySQL, FHIR APIs).
- Understanding of healthcare data models (patients, encounters, prescriptions, billing).
- Familiarity with the repo's coding standards (PHPStan rules, GuzzleHttp patterns, SystemLogger).
- HIPAA compliance: new territory. Mitigation: architecture designed so PHI never leaves the OpenEMR server boundary, which simplifies compliance. No PHI sent to external LLM APIs.

**Comfort with Eval/Testing Frameworks:**
- Prior experience with Vitest (unit), Playwright (E2E) from Vellum project.
- New to LangSmith Evals — will leverage documentation and examples. Plan: start with simple correctness evals, add complexity incrementally.
- Comfortable with pytest for Python-side testing.

**Learning Curve Mitigation Plan:**
- Day 1: LangGraph quickstart tutorial, build minimal graph with one tool.
- Day 1-2: Integrate LangSmith tracing on first working tool.
- Day 2-3: Expand tools using established base class pattern.
- Day 3-5: Build eval framework using LangSmith SDK examples.
- Day 5-7: Harden verification, adversarial testing, polish.

**Development Tooling:**
- IDE: Cursor (AI-assisted development)
- AI Assistance: Claude (architecture, debugging, code review)
- Python: 3.11+, ruff (linting/formatting), mypy (type checking), pytest
- PHP: OpenEMR's existing PHPStan setup
- CI/CD: GitHub Actions (lint, test, eval, build, deploy)
- Pre-commit hooks: ruff, mypy, pytest on staged files

---

## Phase 2: Architecture Discovery

### 5. Agent Framework Selection

**Choice: LangGraph**

**Why LangGraph over alternatives:**

| Framework | Considered | Decision |
|-----------|-----------|----------|
| LangGraph | ✅ Selected | Multi-step state machines, conditional branching, native LangSmith integration. Healthcare workflows require verification loops (tool → verify → retry or return) that map directly to LangGraph's graph-based orchestration. |
| LangChain | Runner-up | Great for simple chains but lacks native state machine support for complex verification loops. LangGraph is built on top of LangChain, so we get LangChain's tool ecosystem anyway. |
| CrewAI | Rejected | Multi-agent collaboration is overkill for this project. We need one agent with multiple tools, not multiple agents negotiating. |
| AutoGen | Rejected | Microsoft ecosystem focus, conversational agents — not the best fit for structured healthcare tool orchestration. |
| Custom | Rejected | Would require building orchestration, state management, and tool registry from scratch. Not feasible in a one-week sprint. |

**Architecture: Single agent, multi-tool.** One LangGraph state machine handles all routing, tool execution, and verification. Multi-agent would add complexity without clear benefit for this use case.

**State Management:**
- LangGraph's built-in state (`TypedDict`) tracks conversation messages, selected tools, tool results, verification status, and confidence scores.
- Redis provides cross-request memory (conversation history persistence between sessions).

**Tool Integration Complexity:**
- 5 tools for MVP, 8 total planned.
- Tools split between OpenEMR database queries (internal) and external API calls (FDA, RxNorm, NPI).
- Each tool has a Pydantic schema for input validation and structured output.

---

### 6. LLM Selection

**Choice: Claude (Anthropic)**

**Rationale:**
- Strong function/tool calling support with structured outputs.
- Tends toward caution in medical reasoning — preferable in healthcare where false confidence is dangerous.
- Excellent at following complex system prompts with verification instructions.
- Competitive pricing for development and production use.

**Fallback:** GPT-4o as a secondary option if Claude API availability becomes an issue.

**Function Calling Support:** Both Claude and GPT-4o have robust tool/function calling. LangGraph abstracts the LLM layer, making it easy to swap models.

**Context Window Needs:**
- Typical query + patient context + tool results: ~2,000–4,000 tokens input.
- System prompt with healthcare guidelines: ~1,500 tokens.
- Well within Claude's context window. No need for RAG or document chunking for MVP.

**Cost Per Query (Estimated):**
- Average input: ~3,000 tokens, output: ~800 tokens.
- At Claude Sonnet pricing: ~$0.01–0.03 per query.
- Multi-step queries (2–3 LLM calls): ~$0.05–0.10 per query.

---

### 7. Tool Design

**External API Dependencies:**
- **RxNorm API** (https://rxnav.nlm.nih.gov/REST) — Free, no API key required, rate-limited. Used for drug interaction checking and medication normalization.
- **NPI Registry** (https://npiregistry.cms.hhs.gov/api) — Free, public API. Used for provider search and verification.
- **FDA NDC** (https://api.fda.gov) — Free with API key. Used for drug information lookup.

**Mock vs Real Data:**
- Development uses OpenEMR's built-in demo dataset (includes sample patients, medications, encounters).
- External APIs are called live during development (all are free/public).
- Eval test cases use predefined fixtures with known expected outcomes.

**Error Handling Per Tool:**
- API timeout → retry once with backoff, then return graceful error message.
- Invalid input → Pydantic validation catches malformed parameters before execution.
- Empty results → Agent communicates "no results found" clearly, suggests alternative queries.
- Rate limiting → Queue and retry with exponential backoff.

---

### 8. Observability Strategy

**Choice: LangSmith**

**Rationale:**
- Native integration with LangGraph/LangChain — zero-config tracing.
- Built-in eval framework that works with our test datasets.
- Cost tracking per request (token usage, API costs).
- Trace visualization for debugging multi-step agent flows.
- Free tier sufficient for development and MVP.

**What Metrics Matter Most:**
1. **End-to-end latency** — Are we hitting the <5s / <15s targets?
2. **Tool success rate** — Are tools executing without errors? Target: >95%.
3. **Verification pass rate** — How often do responses pass fact-checking? Target: >90%.
4. **Token usage / cost per query** — Tracking spend to project production costs.
5. **Hallucination rate** — How often does the agent make unsupported claims? Target: <5%.

**Real-Time Monitoring Needs:**
- LangSmith dashboard provides real-time trace viewing during development.
- Production: alerts on error rate spikes, latency degradation, or cost anomalies.
- Custom metrics exported to LangSmith for domain-specific tracking (e.g., drug interaction severity distribution).

**Cost Tracking Requirements:**
- Per-request token usage (input + output) logged automatically by LangSmith.
- Aggregated daily/weekly cost reports for development spend tracking.
- Production projections based on actual per-query cost data.

---

### 9. Eval Approach

**How We Measure Correctness:**

| Eval Type | Method | Target |
|-----------|--------|--------|
| Correctness | Compare agent output against known ground truth (e.g., known drug interactions from FDA data) | >80% pass rate |
| Tool Selection | Verify agent picks the right tool for each query type | >90% accuracy |
| Tool Execution | Confirm tool calls succeed with correct parameters | >95% success rate |
| Safety | Test refusal of harmful requests, hallucination detection | 100% refusal of out-of-scope medical advice |
| Consistency | Same input produces same output across runs | Deterministic for factual queries |
| Edge Cases | Missing data, invalid input, ambiguous queries handled gracefully | No crashes, clear error messages |
| Latency | Response time within targets | <5s single, <15s multi-step |

**Ground Truth Data Sources:**
- FDA drug interaction database (known interactions with severity ratings).
- OpenEMR demo dataset (known patients, medications, appointments).
- Manually curated test cases with clinician-reviewed expected outcomes.

**Automated vs Human Evaluation:**
- Automated: correctness scoring, tool selection accuracy, latency, safety checks — all run via LangSmith Evals.
- Human: review of a sample of agent responses for clinical appropriateness, tone, and completeness.

**CI Integration:**
- Eval suite runs on every PR via GitHub Actions.
- Baseline scores tracked — regressions block merge.
- LangSmith datasets versioned alongside code.

---

### 10. Verification Design

**Claims That Must Be Verified:**
- Any drug interaction severity claims (cross-ref against RxNorm/FDA).
- Symptom-to-condition mappings (confidence scored, never presented as diagnosis).
- Provider credentials and availability (verified against live data).

**Fact-Checking Data Sources:**
- RxNorm Interaction API for drug-drug interactions.
- FDA Adverse Event Reporting System (FAERS) for supplementary safety data.
- OpenEMR database as source of truth for patient-specific data.

**Confidence Thresholds:**
- **≥ 0.9** — Return response directly.
- **0.7–0.9** — Return with caveats ("based on available data...").
- **0.5–0.7** — Return with strong disclaimer + recommend professional consultation.
- **< 0.5** — Decline to answer. Recommend consulting a healthcare provider.

**Escalation Triggers:**
- Drug interaction with severity "major" or "contraindicated."
- Symptom combination suggesting emergency (e.g., chest pain + shortness of breath).
- Agent confidence below 0.5 on any clinical query.
- User explicitly requests to speak with a provider.

---

## Phase 3: Post-Stack Refinement

### 11. Failure Mode Analysis

**When Tools Fail:**
- External API down (RxNorm, NPI) → Return cached results if available, otherwise inform user the service is temporarily unavailable and suggest trying again.
- OpenEMR database connection lost → Health check endpoint detects, returns 503 with clear error.
- LLM API error → Retry once, then return a generic "unable to process" message.

**Ambiguous Queries:**
- Agent asks clarifying questions rather than guessing (e.g., "Did you mean ibuprofen or naproxen?").
- LangGraph state machine supports a "clarification needed" node that loops back to the user.

**Rate Limiting and Fallback:**
- LLM API rate limits → Queue requests with exponential backoff.
- External API rate limits (RxNorm: 20 requests/second) → Implement request throttling in the tool layer.
- Fallback: if Claude API is unavailable, route to GPT-4o as secondary LLM.

**Graceful Degradation:**
- If verification layer fails, response is still returned but marked as "unverified" with a warning banner.
- If one tool in a multi-tool chain fails, partial results are returned with an explanation of what couldn't be completed.

---

### 12. Security Considerations

**Prompt Injection Prevention:**
- System prompt includes explicit instructions to ignore user attempts to override behavior.
- User input sanitized and validated via Pydantic schemas before reaching LLM context — the agent cannot execute arbitrary queries.
- Input sanitization strips common injection patterns (role overrides, system prompt leaks, encoded instructions).
- Adversarial test cases (10+) specifically test prompt injection, jailbreaking, role confusion, and data exfiltration.

**Data Leakage Risks:**
- Patient data queried server-side via OpenEMR's FHIR API; only relevant results included in LLM context.
- No patient PII sent to external APIs — RxNorm queries use drug names, NPI queries use provider names, not patient identifiers.
- LangSmith traces configured with a custom PHI redaction callback that strips patient name, DOB, SSN, and MRN before transmission.
- Agent cannot access patient data without valid OpenEMR session authentication forwarded through the PHP proxy.

**API Key Management:**
- All API keys stored in environment variables during development (`.env` files in `.gitignore`).
- Production: Docker secrets or dedicated secrets manager (AWS Secrets Manager, HashiCorp Vault).
- Separate keys for development, staging, and production environments.
- Key rotation policy: 90-day rotation or immediate rotation on suspected compromise.
- `.env.example` template committed to repo (with placeholder values, never real keys).

**Network Security:**
- Agent service runs on internal Docker network — only the PHP proxy module can reach it, not exposed publicly.
- External API calls (RxNorm, NPI, FDA) made from agent service, not from client browser.
- HTTPS enforced for all external communications.
- CORS configured to accept requests only from the OpenEMR host origin.
- Rate limiting on `/chat` endpoint to prevent abuse.

**HIPAA Compliance:**
- **Access Control (164.312(a)):** Agent enforces OpenEMR's existing ACL. Each tool validates requesting user's role before returning patient data. Unique user IDs tied to every session.
- **Audit Controls (164.312(b)):** Every interaction logged with timestamp, user ID, patient ID accessed, tools invoked, data returned, verification status. Dual logging: LangSmith (agent traces, PHI-redacted) and OpenEMR's `log` table (data access).
- **Transmission Security (164.312(e)):** All data in transit encrypted via TLS/HTTPS. No PHI transmitted to external LLM APIs.
- **Minimum Necessary:** Tools return only data required for the specific query, not full patient records.
- **BAA Considerations:** LangSmith traces are PHI-redacted, so BAA may not be required. If institution opts to include PHI in traces, BAA with LangChain must be established. Claude API receives no PHI. Redis deployed within institution's own infrastructure.
- **Breach Response:** Agent audit logs enable rapid identification of accessed records. LangSmith traces provide full replay for forensic analysis.

**Audit Logging:**
- Every agent interaction logged with: timestamp, user ID, input, tool calls, output, verification status.
- Logs stored via LangSmith (agent traces) and OpenEMR's native audit system (data access).
- Retention policy aligned with healthcare compliance requirements.

---

### 13. Testing Strategy

**Unit Tests (pytest):**
- Each tool tested in isolation with mocked external dependencies.
- Pydantic schema validation tests for all tool inputs/outputs.
- Verification functions tested with known good/bad inputs.
- State management functions tested for correctness.

**Integration Tests:**
- Full agent flow tests: input → tool selection → execution → verification → output.
- Tests run against OpenEMR's demo database with known test data.
- External API integration tests (can be skipped in CI with mocks).

**Adversarial Testing:**
- 10+ test cases attempting prompt injection, role confusion, and scope bypass.
- Tests for data leakage (asking the agent to reveal system prompts, other patient data).
- Tests for harmful medical advice requests (agent must refuse).

**Regression Testing:**
- LangSmith eval suite runs on every PR.
- Baseline scores established during MVP — any regression below threshold blocks merge.
- Test datasets versioned in the repository alongside code.

---

### 14. Open Source Planning

**What We Will Release:**
- **OpenEMR AI Agent Module** — A reusable OpenEMR custom module (`mod-ai-agent`) that any OpenEMR installation can enable for AI-assisted clinical workflows.
- **Healthcare Agent Eval Dataset** — 50+ test cases for healthcare agent evaluation, published as a public dataset.
- **Documentation** — Comprehensive setup guide, architecture overview, and contribution guidelines.

**Licensing:**
- Agent module: GPL-2.0 (matching OpenEMR's license for module compatibility).
- Python agent service: MIT License (permissive, encourages adoption).
- Eval dataset: CC BY 4.0 (open data).

**Documentation Requirements:**
- README with quickstart guide (Docker Compose one-command setup).
- Architecture document (already created).
- API reference for the agent service endpoints.
- Tool development guide (how to add new tools).
- Eval guide (how to run and extend the test suite).

**Community Engagement:**
- Submit PR to OpenEMR repository with the module.
- Post on OpenEMR community forums introducing the AI agent capability.
- Share on X/LinkedIn with demo video and screenshots.

---

### 15. Deployment & Operations

**Hosting Approach:**
- Docker Compose bundles OpenEMR + Agent Service + Redis as a single deployable stack.
- Agent service containerized independently for flexibility.
- Demo deployment on Railway (FastAPI service) with OpenEMR on a cloud VM.

**CI/CD for Agent Updates:**
- GitHub Actions pipeline: lint → test → eval → build → deploy.
- Eval gate: deployment blocked if eval pass rate drops below 80%.
- Docker image built and pushed on merge to main.

**Monitoring and Alerting:**
- LangSmith dashboard for agent-specific metrics.
- FastAPI health endpoint (`/health`) for uptime monitoring.
- Alerts on: error rate > 5%, latency > 10s (p95), eval regression.

**Rollback Strategy:**
- Docker image versioned with git SHA tags.
- Previous image can be redeployed in < 2 minutes.
- Database migrations (if any) designed to be backward-compatible.

---

### 16. Iteration Planning

**User Feedback Collection:**
- Thumbs up/down on every agent response in the chat widget.
- Optional free-text feedback field.
- Feedback logged to LangSmith and linked to the corresponding trace.

**Eval-Driven Improvement Cycle:**
1. Review LangSmith traces for failed evals.
2. Identify root cause (wrong tool selection, hallucination, missing verification).
3. Update system prompt, tool logic, or verification rules.
4. Add new test cases for the discovered failure mode.
5. Re-run evals to confirm improvement.

**Feature Prioritization:**
- MVP (24 hours): 5 tools, basic verification, deployed.
- Early submission (4 days): Full eval framework, observability, 50+ test cases.
- Final (7 days): All 8 tools, production-hardened verification, open source release.

**Long-Term Maintenance:**
- Eval suite runs weekly against production to catch model drift.
- External API changes monitored (RxNorm, FDA versioning).
- Community contributions reviewed via standard PR process.
- Agent prompts and verification rules updated as OpenEMR releases new versions.
