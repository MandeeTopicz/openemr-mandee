# Product Requirements Document
## OpenEMR AI Agent — "CareTopicz"

**Version:** 1.0
**Author:** Mandee
**Date:** February 2026
**Status:** Draft

---

## Product Vision

CareTopicz is an AI-powered clinical assistant integrated into OpenEMR that helps healthcare professionals make faster, safer, and more informed decisions. It provides real-time drug interaction checking, symptom analysis, patient record summarization, scheduling assistance, and insurance verification — all backed by authoritative medical data sources and a verification layer that ensures no unvalidated medical claim reaches a clinician.

Long-term, CareTopicz evolves from a read-only assistant into a full clinical workflow agent capable of taking actions within OpenEMR (scheduling appointments, updating records, generating referrals), serving both clinical staff and patients through the patient portal, and supporting multi-institution deployments with customizable verification rules and tool configurations.

---

## Problem Statement

Clinicians using OpenEMR face several recurring friction points that slow down care and introduce risk:

- Drug interaction checking is manual. Providers must leave OpenEMR to look up interactions on external sites, then mentally reconcile results with the patient's medication list.
- Patient context is fragmented. Relevant data (medications, labs, history, insurance) lives across multiple screens. There's no unified summary view driven by the clinical question being asked.
- Scheduling and coverage verification are tedious. Finding an available specialist who accepts the patient's insurance requires navigating multiple systems.
- No intelligent assistance layer exists. OpenEMR is a powerful data system, but it doesn't proactively surface insights or help clinicians reason through clinical decisions.

CareTopicz solves these by embedding an AI agent directly into the clinical workflow — one that reads OpenEMR's data, consults authoritative external sources, verifies its own answers, and presents structured, citation-backed responses.

---

## Users

### Phase 1 — Clinical Staff (MVP through v1.0)

- **Physicians:** Drug interaction checks during prescribing, symptom analysis for differential diagnosis support, patient summary generation before encounters.
- **Nurses:** Quick medication lookups, appointment availability checks, lab result contextualization.
- **Front Desk / Scheduling:** Provider search by specialty, appointment availability, insurance coverage verification.
- **Administrators:** Usage analytics, cost tracking, audit trail review.

### Phase 2 — Patient Portal (Future)

- **Patients:** Symptom triage (with clear disclaimers), medication questions, appointment scheduling, insurance coverage inquiries.

Patient-facing features require a separate permission model, stricter response guardrails, and simplified language. This is architecturally planned for but not implemented in Phase 1.

---

## Architecture Overview

CareTopicz is a Python-based sidecar service that integrates with OpenEMR via a custom module. OpenEMR remains untouched at its core.

### System Components

**OpenEMR Layer (Existing):**
- Clinical Dashboard (existing UI)
- FHIR R4 REST API (existing endpoints for patients, medications, encounters, appointments, observations, practitioners)
- MySQL Database (patient_data, prescriptions, form_encounter, openemr_postcalendar_events, billing, insurance_data, procedure_result, users)
- ACL System (existing role-based permissions)

**New OpenEMR Module (`mod-ai-agent`):**
- `AgentController.php` — Routes chat requests to the Python service
- `AgentProxyService.php` — GuzzleHttp client that calls FastAPI endpoints
- Chat Widget — React-based UI embedded in OpenEMR templates

**Python Agent Service (New, FastAPI):**
- API Gateway — `/chat`, `/verify`, `/tools`, `/health` endpoints
- LangGraph Orchestrator — State machine managing reasoning, tool selection, execution, verification, and formatting
- Reasoning Engine — Claude (Anthropic) for natural language understanding and response generation
- Tool Registry — 5-8 tools with Pydantic schemas for input validation
- Verification Layer — Deterministic Python code that validates responses against tool data
- Memory System — Redis-backed conversation history and patient context
- Observability — LangSmith tracing, metrics, and feedback capture

**External Dependencies:**
- Claude API (Anthropic) — LLM reasoning and tool calling
- RxNorm API (NIH) — Drug interaction checking and medication normalization
- NPI Registry API (CMS) — Provider search and credential verification
- FDA NDC API — Drug information and adverse event data
- Redis — Session state and conversation memory
- LangSmith (SaaS) — Tracing, evals, cost tracking

### Request Flow

1. User types a question in the chat widget (OpenEMR UI)
2. `mod-ai-agent` PHP module forwards the request to the Python service via REST
3. FastAPI receives the request at `/chat`
4. LangGraph parses intent and selects appropriate tools
5. Tools execute (query OpenEMR DB via FHIR API, call external APIs)
6. Claude synthesizes tool results into a natural language response
7. Verification layer checks the response against raw tool data
8. If verification passes: format and return. If it fails: retry or return safe fallback
9. Response returned to PHP module, displayed in chat widget
10. Full trace logged to LangSmith

---

## Feature Set

### Phase 1: Read-Only Clinical Assistant (MVP through v1.0)

The agent reads data, reasons about it, and returns verified information. It does not modify any data in OpenEMR.

#### F1.1 — Natural Language Chat Interface

A chat widget embedded in OpenEMR's clinical dashboard where staff can ask questions in plain language.

Requirements:
- Accessible from any OpenEMR page via a collapsible panel or floating widget
- Conversation history maintained across turns within a session
- Session context includes the currently viewed patient (if any)
- Clear visual indicators for agent status (thinking, tool calling, verifying)
- Typing indicator and streaming response display
- Thumbs up/down feedback on every response

#### F1.2 — Drug Interaction Checking

Check for interactions between two or more medications using authoritative FDA/RxNorm data.

Requirements:
- Accept medication names in natural language (handles brand/generic, misspellings)
- Normalize medication names via RxNorm before checking interactions
- Return interaction severity (major, moderate, minor, none)
- Include clinical description of each interaction
- Cite data source for every interaction claim
- Auto-populate from patient's current medication list when patient context is available
- Mandatory verification — every drug interaction response passes through the fact checker before delivery

#### F1.3 — Symptom Analysis

Accept natural language symptom descriptions and return possible conditions with urgency scoring.

Requirements:
- Map symptoms to possible conditions with confidence levels
- Categorize urgency (emergency, urgent, routine, self-care)
- Never present results as a diagnosis — always framed as "possible conditions to consider"
- Include disclaimers on every symptom analysis response
- Flag emergency symptom combinations (chest pain + shortness of breath, etc.) with immediate escalation messaging
- Confidence scoring gates delivery (below 0.5 triggers refusal to answer)

#### F1.4 — Provider Search

Find providers by specialty, location, and availability.

Requirements:
- Search OpenEMR's internal provider directory
- Cross-reference with NPI Registry for credential verification
- Filter by specialty, location, and availability
- Return provider details: name, specialty, credentials, contact info
- Integrate with appointment availability (F1.5) for combined queries

#### F1.5 — Appointment Availability

Check provider calendar availability within OpenEMR.

Requirements:
- Query OpenEMR's calendar tables for open slots
- Filter by provider, date range, and appointment type
- Return available time slots in a structured, readable format
- Support queries like "next available cardiologist appointment this week"

#### F1.6 — Insurance Coverage Verification

Check whether a procedure or service is covered under a patient's insurance plan.

Requirements:
- Query OpenEMR's billing and insurance tables
- Accept procedure codes or natural language descriptions of procedures
- Return coverage status, copay/coinsurance details where available
- Flag if insurance data is missing or incomplete

#### F1.7 — Patient Summary Generation

Generate a concise clinical summary for a given patient.

Requirements:
- Aggregate demographics, active problems, medications, allergies, recent labs, and recent encounters
- Tailor summary to clinical context (pre-visit summary vs. referral summary vs. general overview)
- Highlight critical items (drug allergies, abnormal lab values, overdue screenings)
- Respect ACL permissions — only show data the requesting user is authorized to see

#### F1.8 — Lab Results Lookup

Retrieve and contextualize recent lab results.

Requirements:
- Pull lab results from OpenEMR's procedure tables
- Display values alongside reference ranges
- Flag abnormal results with clinical context
- Support queries like "what were the patient's last A1C results"

#### F1.9 — Medication List Management

Pull current prescriptions and flag potential issues.

Requirements:
- Retrieve active medications from OpenEMR's prescription tables
- Flag duplicates (same drug class prescribed twice)
- Cross-reference with drug interaction checker for the full medication list
- Identify medications due for renewal

#### F1.10 — Verification Layer

Every agent response passes through verification before reaching the user.

Requirements:
- **Fact Checking:** Compare agent claims against raw tool/API data. Mismatch triggers correction or refusal.
- **Hallucination Detection:** Flag any claim not traceable to a tool result or authoritative source.
- **Confidence Scoring:** Score every response 0.0-1.0. Thresholds: >=0.9 return directly, 0.7-0.9 return with caveats, 0.5-0.7 return with strong disclaimer, <0.5 refuse to answer.
- **Domain Rules:** Enforce healthcare business rules (never suggest dosages, never present as diagnosis, always recommend professional consultation for clinical decisions).
- Responses that fail verification are either corrected automatically, retried with additional tool calls, or replaced with a safe fallback message.

#### F1.11 — Observability Dashboard

Full visibility into agent behavior via LangSmith.

Requirements:
- Trace logging for every request (input, reasoning, tool calls, verification, output)
- Latency tracking with breakdown (LLM time, tool execution time, verification time)
- Error tracking with categorization and stack traces
- Token usage and cost per query
- Historical eval scores with regression detection
- User feedback (thumbs up/down) linked to traces

#### F1.12 — Evaluation Framework

Systematic testing of agent correctness, safety, and reliability.

Requirements:
- Minimum 50 test cases: happy path (20+), edge cases (10+), adversarial inputs (10+), multi-step reasoning (10+)
- Each test case includes: input query, expected tool calls, expected output, pass/fail criteria
- Automated eval runs via LangSmith on every PR
- Baseline scores tracked — regressions block deployment
- Eval datasets versioned alongside code

---

### Phase 2: Enhanced Intelligence (v1.1 through v1.5)

These features deepen the agent's clinical utility without yet taking write actions.

#### F2.1 — Clinical Decision Support

Proactive alerts and recommendations based on patient data patterns.

Requirements:
- Flag potential drug-drug interactions when a new prescription is being entered
- Alert on abnormal lab trends (e.g., steadily rising creatinine)
- Suggest preventive care reminders (overdue screenings based on age/sex/conditions)
- Surface relevant clinical guidelines based on active diagnoses

#### F2.2 — Multi-Step Clinical Workflows

Handle complex queries that chain multiple tools together.

Requirements:
- Support queries like: "Find a cardiologist who accepts Blue Cross, is within 20 miles, and has availability next week — then summarize this patient's cardiac history for the referral"
- LangGraph orchestrates multi-tool chains with intermediate verification
- Partial results returned if one tool in the chain fails
- Total latency target: < 15 seconds for 3+ tool chains

#### F2.3 — Contextual Awareness

The agent understands what the clinician is currently doing in OpenEMR and tailors responses accordingly.

Requirements:
- Detect the current screen/module (prescribing, charting, scheduling, billing)
- Auto-inject relevant patient context without the user having to specify
- Suggest relevant tools based on context (e.g., on the prescribing screen, proactively offer drug interaction check)
- Support "what about this patient?" queries that resolve to the currently viewed patient

#### F2.4 — Medical Document Summarization

Summarize uploaded or linked clinical documents (referral letters, discharge summaries, lab reports).

Requirements:
- Accept PDF and text document uploads
- Extract key clinical information (diagnoses, medications, recommendations)
- Highlight action items for the clinician
- Maintain source attribution for all extracted claims

#### F2.5 — Natural Language Search Across Records

Allow clinicians to search patient records using natural language instead of navigating multiple screens.

Requirements:
- Queries like "when was the last time this patient had a CBC" or "show me all encounters related to diabetes"
- Translates natural language to structured queries against OpenEMR's database
- Returns results with links back to the relevant OpenEMR screens
- Respects ACL permissions for all query results

#### F2.6 — Conversation Export and Charting Integration

Export agent conversations or summaries directly into clinical notes.

Requirements:
- One-click export of agent response to encounter note
- Formatted for clinical documentation standards
- Includes citations and data sources
- Audit trail records what was exported and by whom

---

### Phase 3: Read-Write Agent Actions (v2.0)

The agent transitions from advisor to actor — capable of taking actions within OpenEMR with appropriate safeguards. Every write action requires explicit clinician approval before execution.

#### F3.1 — Appointment Scheduling

The agent can book, reschedule, and cancel appointments on behalf of staff.

Requirements:
- Confirm action with user before executing ("I'll schedule a cardiology appointment for Tuesday at 2pm — proceed?")
- Write to OpenEMR's calendar tables via FHIR API or direct DB
- Enforce scheduling rules (provider availability, appointment type constraints)
- Full audit trail of agent-initiated schedule changes
- Rollback capability if appointment was created in error

#### F3.2 — Prescription Assistance

Pre-populate prescription forms based on clinical discussion.

Requirements:
- Agent suggests medication, dosage, and frequency based on clinical context
- Pre-fills the prescription form — clinician reviews and approves before submission
- Agent never submits prescriptions autonomously
- Mandatory drug interaction check runs before presenting the suggestion
- Includes formulary checking against patient's insurance

#### F3.3 — Referral Generation

Generate and submit referral orders based on clinical conversation.

Requirements:
- Auto-populate referral form with: patient info, referring provider, reason for referral, relevant history
- Attach relevant clinical summary
- Clinician review and approval required before submission
- Track referral status within the agent conversation

#### F3.4 — Order Entry Assistance

Help clinicians enter lab orders, imaging orders, and other clinical orders.

Requirements:
- Suggest appropriate orders based on clinical context and active diagnoses
- Pre-fill order forms with relevant details
- Clinician approval required for all orders
- Check for duplicate or redundant orders

#### F3.5 — Clinical Note Drafting

Generate draft clinical notes based on encounter context and conversation.

Requirements:
- Generate SOAP-format notes from encounter data and agent interactions
- Clinician reviews, edits, and signs off
- Never auto-submit notes without clinician approval
- Include all relevant data sources and citations

#### F3.6 — Bulk Operations

Handle batch tasks like patient outreach, recall lists, and population health queries.

Requirements:
- Queries like "list all diabetic patients overdue for A1C testing"
- Generate outreach lists with contact information
- Support bulk message drafting for patient communications
- Enforce privacy controls — only authorized users can run population queries

---

### Phase 4: Patient Portal Integration (v3.0)

Extend CareTopicz to patients through OpenEMR's existing patient portal.

#### F4.1 — Patient-Facing Symptom Triage

Patients describe symptoms and receive guidance on urgency and next steps.

Requirements:
- Simplified, non-clinical language in all responses
- Stronger disclaimers than clinician-facing version ("This is not a diagnosis...")
- Clear escalation paths: "Call 911," "Schedule an appointment," "Monitor at home"
- Never suggests specific medications or treatments
- Separate, stricter verification rules for patient-facing responses
- Conversation logged and available to the patient's care team

#### F4.2 — Patient Appointment Self-Scheduling

Patients can search for and book appointments through the agent.

Requirements:
- Search available providers by specialty and availability
- Book appointments directly (write to OpenEMR calendar)
- Send confirmation to patient and provider
- Support rescheduling and cancellation
- Respect scheduling rules set by the practice

#### F4.3 — Patient Medication and Lab Questions

Patients can ask about their medications and lab results.

Requirements:
- Explain medications in plain language (purpose, common side effects, when to take)
- Contextualize lab results without clinical interpretation ("Your A1C is 7.2 — your doctor considers this above the typical target range")
- Direct clinical interpretation questions to their provider
- Never recommend medication changes

#### F4.4 — Insurance and Billing Questions

Patients can ask about their coverage and billing.

Requirements:
- Explain coverage details in plain language
- Help patients understand bills and charges
- Direct disputes or complex questions to billing staff
- No access to other patients' billing data

---

### Phase 5: Multi-Tenant and Enterprise (v4.0)

Support multiple institutions with customizable configurations.

#### F5.1 — Institution-Level Configuration

Each deploying institution can customize the agent's behavior.

Requirements:
- Configurable verification thresholds per institution
- Custom tool enable/disable (some institutions may not want symptom analysis)
- Custom domain rules (institution-specific formularies, scheduling policies)
- Branding customization for the chat widget
- Institution-specific system prompts and response guidelines

#### F5.2 — Role-Based Agent Permissions

Different user roles see different agent capabilities.

Requirements:
- Map to OpenEMR's existing ACL system
- Physicians get full tool access; front desk gets scheduling/insurance only
- Patient portal users get patient-safe subset
- Administrators can configure role-tool mappings
- Audit trail tracks who accessed what through the agent

#### F5.3 — Analytics and Reporting Dashboard

Institution-level analytics on agent usage, performance, and value.

Requirements:
- Query volume and patterns (most-used tools, peak hours)
- Clinical impact metrics (time saved per interaction, interaction check coverage)
- Cost reporting per department/provider
- Comparison across time periods
- Export capabilities for institutional reporting

#### F5.4 — Agent Marketplace

Community-contributed tools and verification modules.

Requirements:
- Standardized tool interface for third-party contributions
- Verification module plugin system
- Review and approval process for community tools
- Version management and dependency tracking

---

## Non-Functional Requirements

### Security Configuration

**Data Flow Security:**
- No patient PII sent to external LLM APIs — only de-identified queries or structured tool parameters (e.g., drug names, procedure codes, not patient names or IDs)
- Patient data stays within the OpenEMR server boundary. The Python agent service queries OpenEMR's FHIR API over an internal network — never exposed publicly.
- LangSmith traces configured with a custom callback handler that redacts PHI fields (patient name, DOB, SSN, MRN) before transmission to the external SaaS platform.

**API Key and Secret Management:**
- All API keys (Claude, FDA, LangSmith) stored in environment variables during development.
- Production: Docker secrets or a secrets manager (AWS Secrets Manager, HashiCorp Vault) — never committed to version control.
- `.env` files listed in `.gitignore` and `.dockerignore`.
- Separate API keys for development, staging, and production environments.
- API key rotation policy: keys rotated every 90 days or immediately on suspected compromise.

**Authentication and Authorization:**
- Agent service endpoints require a valid OpenEMR session token passed via the PHP proxy module — no direct public access to the FastAPI service.
- The PHP `AgentProxyService` authenticates against OpenEMR's session management before forwarding requests.
- OpenEMR's ACL system enforced at the tool level — each tool checks the requesting user's role before executing. A front desk user cannot access clinical tools; a nurse cannot access admin analytics.
- CORS configured to accept requests only from the OpenEMR host origin.

**Input Validation and Prompt Injection Prevention:**
- All user input validated via Pydantic schemas before reaching the LLM context.
- System prompt includes explicit guardrails: ignore attempts to override instructions, refuse to reveal system prompt contents, refuse to act outside defined tool scope.
- Input sanitization strips common injection patterns (role overrides, system prompt leaks, encoded instructions).
- Adversarial eval suite (10+ test cases) specifically tests prompt injection, jailbreaking, role confusion, and data exfiltration attempts.
- Tool parameters are strictly typed — the agent cannot construct arbitrary SQL or API calls.

**Network Security:**
- Agent service runs on an internal Docker network — only the PHP proxy module can reach it.
- External API calls (RxNorm, NPI, FDA) made from the agent service, not from the client.
- HTTPS enforced for all external communications.
- Rate limiting on the `/chat` endpoint to prevent abuse (configurable per deployment).

### HIPAA Compliance

**Applicability:** CareTopicz handles Protected Health Information (PHI) — patient names, medical records, diagnoses, medications, lab results. HIPAA's Privacy Rule and Security Rule apply to all components that touch this data.

**Technical Safeguards (HIPAA 164.312):**
- **Access Control (164.312(a)):** Agent enforces OpenEMR's existing ACL system. Each tool call validates the requesting user's role and permissions before returning patient data. Unique user identifiers are tied to every agent session.
- **Audit Controls (164.312(b)):** Every agent interaction logged with: timestamp, authenticated user ID, patient ID accessed, tools invoked, data returned, and verification status. Logs stored in both LangSmith (agent traces) and OpenEMR's native `log` table (data access audit).
- **Integrity Controls (164.312(c)):** Agent responses include source citations. Verification layer ensures claims match authoritative data. Responses are checksummed in LangSmith traces.
- **Transmission Security (164.312(e)):** All data in transit encrypted via TLS/HTTPS. Internal Docker network traffic between OpenEMR and the agent service uses encrypted channels. No PHI transmitted to external LLM APIs.

**Administrative Safeguards:**
- Agent never stores PHI at rest outside of OpenEMR's existing database and LangSmith traces (which are PHI-redacted).
- Redis session store holds conversation history with configurable TTL (default: 24 hours, then auto-purged).
- Minimum necessary principle: tools return only the data required to answer the specific query, not full patient records.
- Agent cannot diagnose, prescribe, or take autonomous clinical action — human clinician approval required for all clinical decisions and all write actions (Phase 3+).

**BAA Considerations:**
- LangSmith traces are PHI-redacted before transmission, so a BAA with LangChain/LangSmith may not be required. However, if an institution opts to include PHI in traces, a BAA must be established.
- Claude API (Anthropic): No PHI is sent to the LLM. Only de-identified clinical questions and structured tool parameters are included in prompts. If an institution's risk assessment requires a BAA with the LLM provider, the architecture supports routing to a HIPAA-eligible LLM endpoint (e.g., Azure OpenAI with BAA).
- Redis: deployed within the institution's own infrastructure (Docker Compose), so no third-party BAA needed.

**Breach Response:**
- Agent audit logs enable rapid identification of which patient records were accessed in any incident.
- LangSmith traces provide a full replay of agent reasoning and data access for forensic analysis.
- Configurable alert triggers for anomalous access patterns (e.g., single user querying an unusual volume of patient records).

### Performance

- Single-tool queries: < 5 seconds end-to-end
- Multi-step queries (3+ tools): < 15 seconds
- Tool success rate: > 95%
- Eval pass rate: > 80%
- Hallucination rate: < 5%
- Verification accuracy: > 90%
- Support 100 concurrent users at MVP scale

### Reliability

- Health check endpoint for uptime monitoring
- Graceful degradation when external APIs are unavailable
- Automatic retry with backoff for transient failures
- LLM fallback (Claude to GPT-4o) if primary model is unavailable
- Unverified responses clearly marked — never silently delivered

### Scalability

- Stateless agent service — horizontally scalable behind a load balancer
- Redis for session state — separates memory from compute
- Docker containerized — deployable on any infrastructure
- LLM routing layer supports model selection based on query complexity (cheaper models for simple routing, Claude for complex reasoning)

### Budget Constraints

**Development Sprint (1 week):**
- LLM API costs (Claude): $50-100 estimated. Based on ~3,000 input tokens + ~800 output tokens per query, at Claude Sonnet pricing (~$0.01-0.03/query for single-tool, ~$0.05-0.10 for multi-step). Development and testing generates ~500-2,000 queries.
- External APIs (RxNorm, NPI, FDA): $0 — all free/public APIs.
- LangSmith: $0 — free tier covers development (5,000 traces/month).
- Infrastructure: $0-20 — Railway free tier for demo deployment, OpenEMR Docker runs locally.
- Total estimated development cost: $50-120.

**Production Cost Projections (monthly):**
- 100 users (5 queries/user/day): ~$150-450/month (LLM API) + $0 (external APIs) + $20 (LangSmith Developer tier) + $20-50 (hosting) = ~$190-520/month.
- 1,000 users: ~$1,500-4,500/month (LLM) + $39 (LangSmith Plus) + $50-150 (hosting) = ~$1,600-4,700/month.
- 10,000 users: ~$15,000-45,000/month (LLM) + $400 (LangSmith Enterprise) + $200-500 (hosting) = ~$15,600-46,000/month.
- 100,000 users: Requires prompt caching, response caching, model routing (simple queries to cheaper models), and batching optimizations. Estimated $80,000-200,000/month before optimization, target $30,000-80,000/month after.

**Cost Optimization Strategies:**
- Prompt caching: cache system prompts and common tool schemas to reduce input tokens by ~40%.
- Response caching: cache identical drug interaction queries (same medication pair = same result). TTL: 24 hours.
- Model routing: use a lightweight classifier to route simple queries (appointment lookups, medication lists) to a cheaper/faster model, reserving Claude for complex reasoning (symptom analysis, multi-step workflows).
- Token optimization: minimize context window by including only relevant patient data, not full records.

### Development Tooling and Code Organization

**Development Environment:**
- **IDE:** Cursor (AI-assisted development, primary coding tool)
- **AI Assistance:** Claude (architecture planning, debugging consultation, code review)
- **Version Control:** Git + GitHub (forked OpenEMR repository)
- **Python Environment:** Python 3.11+, managed via `venv` or `poetry` for dependency isolation
- **PHP Environment:** OpenEMR's existing Docker Compose development setup (Apache, PHP 8.x, MySQL)

**Code Quality Tools:**
- **Python Linting:** `ruff` (fast, replaces flake8/isort/black) with strict configuration
- **Python Type Checking:** `mypy` with strict mode — all tool functions and state schemas fully typed
- **Python Formatting:** `ruff format` (black-compatible)
- **PHP Static Analysis:** PHPStan (already configured in OpenEMR with custom rules — see existing codebase patterns)
- **Pre-commit Hooks:** `pre-commit` framework running ruff, mypy, and pytest on staged files

**Testing Tools:**
- **Python Unit/Integration:** `pytest` with `pytest-asyncio` for async FastAPI testing
- **Python Coverage:** `pytest-cov` with minimum 80% coverage target on tool and verification code
- **Agent Evals:** LangSmith Evals SDK — automated eval runs integrated with pytest
- **API Testing:** `httpx` test client for FastAPI endpoint testing
- **Mocking:** `unittest.mock` for external API mocking, `responses` library for HTTP mocking

**CI/CD Pipeline (GitHub Actions):**
1. **Lint:** `ruff check` + `mypy` (Python), PHPStan (PHP module)
2. **Test:** `pytest` unit and integration tests
3. **Eval:** LangSmith eval suite — blocks merge if pass rate drops below 80%
4. **Build:** Docker image build and push
5. **Deploy:** Automated deploy to staging on PR merge, manual promotion to production

**Code Organization — Python Agent Service:**

```
agent-service/
├── app/
│   ├── main.py                     # FastAPI app factory, CORS, lifespan events
│   ├── config.py                   # Pydantic Settings class, env var loading
│   ├── dependencies.py             # FastAPI dependency injection (DB connections, LLM client)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py               # Route definitions: /chat, /verify, /tools, /health
│   │   ├── schemas.py              # Request/response Pydantic models for API layer
│   │   └── middleware.py           # Auth validation, rate limiting, request logging
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── graph.py                # LangGraph StateGraph definition and compilation
│   │   ├── state.py                # AgentState TypedDict schema
│   │   ├── nodes/
│   │   │   ├── __init__.py
│   │   │   ├── reasoning.py        # LLM reasoning node (intent classification, synthesis)
│   │   │   ├── tool_selector.py    # Decides which tools to invoke based on query
│   │   │   ├── tool_executor.py    # Executes selected tools, handles errors
│   │   │   ├── verifier.py         # Orchestrates verification checks
│   │   │   └── formatter.py        # Structures final response with citations
│   │   └── prompts/
│   │       ├── system.py           # Healthcare system prompt with guardrails
│   │       └── templates.py        # Per-tool prompt templates (few-shot examples)
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base.py                 # Abstract base tool class with common interface
│   │   ├── registry.py             # Tool registration, schema export, discovery
│   │   ├── drug_interaction.py     # RxNorm API integration
│   │   ├── symptom_lookup.py       # Symptom-to-condition mapping
│   │   ├── provider_search.py      # OpenEMR DB + NPI Registry
│   │   ├── appointment_check.py    # OpenEMR calendar queries
│   │   ├── insurance_coverage.py   # OpenEMR billing table queries
│   │   ├── patient_summary.py      # Multi-table patient aggregation
│   │   ├── lab_results.py          # Procedure result queries
│   │   └── medication_list.py      # Prescription queries with interaction cross-ref
│   ├── verification/
│   │   ├── __init__.py
│   │   ├── fact_checker.py         # Compares agent claims vs raw tool data
│   │   ├── hallucination.py        # Flags claims without source attribution
│   │   ├── confidence.py           # Scores 0.0-1.0 based on data quality signals
│   │   └── domain_rules.py         # Healthcare business rules enforcement
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── conversation.py         # Redis-backed chat history (per-session)
│   │   └── context.py              # Patient context window management
│   ├── observability/
│   │   ├── __init__.py
│   │   ├── langsmith.py            # LangSmith tracer setup and PHI redaction callback
│   │   ├── metrics.py              # Custom metrics (latency breakdown, tool success rate)
│   │   └── feedback.py             # User feedback ingestion and trace linking
│   └── clients/
│       ├── __init__.py
│       ├── openemr.py              # OpenEMR FHIR API client (httpx-based)
│       ├── rxnorm.py               # RxNorm API client with rate limiting
│       ├── npi.py                  # NPI Registry API client
│       └── fda.py                  # FDA NDC/FAERS API client
├── evals/
│   ├── runner.py                   # Eval execution engine (LangSmith SDK integration)
│   ├── datasets/
│   │   ├── correctness.json        # 20+ happy path test cases
│   │   ├── edge_cases.json         # 10+ edge cases
│   │   ├── adversarial.json        # 10+ adversarial/injection test cases
│   │   └── multi_step.json         # 10+ multi-tool chain scenarios
│   └── scorers/
│       ├── accuracy.py             # Response correctness scoring
│       ├── tool_selection.py       # Tool choice accuracy scoring
│       └── safety.py               # Safety and refusal scoring
├── tests/
│   ├── conftest.py                 # Shared fixtures (mock APIs, test DB, FastAPI test client)
│   ├── unit/
│   │   ├── test_tools/             # One test file per tool
│   │   ├── test_verification/      # Fact checker, hallucination, confidence tests
│   │   └── test_state.py           # Agent state management tests
│   └── integration/
│       ├── test_agent_flow.py      # Full input-to-output agent tests
│       └── test_api_endpoints.py   # FastAPI route tests
├── scripts/
│   ├── seed_eval_data.py           # Generate/update eval datasets
│   └── run_evals.py                # CLI for running eval suite locally
├── Dockerfile
├── docker-compose.yml              # Agent service + Redis + OpenEMR (dev)
├── pyproject.toml                  # Project metadata, dependencies, tool config (ruff, mypy, pytest)
├── .env.example                    # Template for required environment variables
├── .pre-commit-config.yaml         # Pre-commit hook configuration
└── README.md
```

**Code Organization — OpenEMR Module:**

```
openemr/interface/modules/custom_modules/mod-ai-agent/
├── moduleConfig.php                # Module metadata, version, dependencies
├── openemr.bootstrap.php           # Hook registration (menu items, event listeners)
├── src/
│   ├── Controller/
│   │   └── AgentController.php     # Routes: receives chat requests, returns responses
│   └── Service/
│       └── AgentProxyService.php   # GuzzleHttp client to FastAPI, auth token forwarding
├── public/
│   └── chat-widget/
│       ├── dist/                   # Built React chat widget (bundled JS/CSS)
│       └── src/                    # React source (if building within the module)
├── templates/
│   └── chat-panel.php              # PHP template that mounts the React widget
└── README.md                       # Module-specific setup and configuration
```

**Naming Conventions:**
- Python: snake_case for files, functions, variables. PascalCase for classes. All modules include `__init__.py`.
- PHP: PSR-4 autoloading, PascalCase for classes, following OpenEMR's existing patterns.
- Eval datasets: JSON files with descriptive names matching eval categories.

### Team and Skills Assessment

**Current Capabilities:**
- Strong frontend development (React, TypeScript) — demonstrated by Vellum whiteboard project (20,700 lines of code in one week).
- Prior AI agent experience: built an OpenAI function-calling agent with Firebase Cloud Functions for Vellum, handling tool definitions, conversation history, and multi-step execution.
- Comfortable with Python for scripting and tooling. Transitioning to Python as primary backend language for this project.
- Familiar with OpenEMR's codebase structure, PHP patterns (GuzzleHttp, SystemLogger, PHPStan rules), and MySQL schema from pre-search exploration.
- Testing experience with Vitest (unit) and Playwright (E2E). Comfortable with pytest fundamentals.

**Learning Curve Areas:**
- **LangGraph/LangChain:** First time using these frameworks. Mitigation: LangGraph has strong documentation and tutorials. The state machine paradigm maps conceptually to the Firebase Cloud Functions agent architecture already built.
- **LangSmith Evals:** New tooling. Mitigation: LangSmith provides example eval datasets and scoring functions. Start with simple correctness evals, add complexity incrementally.
- **Healthcare data models:** Understanding OpenEMR's database schema (40+ tables) takes exploration. Mitigation: focus on the 8 tables directly relevant to the agent's tools; use OpenEMR's FHIR API as an abstraction layer where possible.
- **HIPAA compliance implementation:** Understanding the technical requirements. Mitigation: the architecture is designed so PHI never leaves the OpenEMR server boundary, which simplifies compliance significantly.

**Skill Development Plan:**
- Day 1: Complete LangGraph quickstart tutorial, build a minimal graph with one tool.
- Day 1-2: Integrate LangSmith tracing on the first working tool.
- Day 2-3: Expand tools, relying on the established pattern (each tool follows the same base class interface).
- Day 3-5: Build eval framework using LangSmith SDK examples as templates.
- Day 5-7: Harden verification, adversarial testing, and polish for submission.

---

## Open Source Strategy

- **OpenEMR Module (mod-ai-agent):** GPL-2.0 — PHP module with chat widget and proxy controller, compatible with OpenEMR upstream.
- **Python Agent Service:** MIT — FastAPI service with LangGraph orchestration, tools, and verification.
- **Healthcare Eval Dataset:** CC BY 4.0 — 50+ test cases for healthcare agent evaluation.
- **Documentation:** CC BY 4.0 — Setup guides, architecture docs, tool development guide, eval guide.

---

## Success Metrics

MVP targets:
- Tool success rate: > 95%
- Eval pass rate: > 80%
- Hallucination rate: < 5%
- End-to-end latency (single tool): < 5s

v1.0 targets:
- Tool success rate: > 98%
- Eval pass rate: > 90%
- Hallucination rate: < 2%
- End-to-end latency (single tool): < 3s
- User satisfaction (thumbs up rate): > 70%

Long-term targets:
- Tool success rate: > 99%
- Eval pass rate: > 95%
- Hallucination rate: < 1%
- End-to-end latency (single tool): < 2s
- User satisfaction (thumbs up rate): > 85%
- Clinician time saved per interaction: > 2 min avg
- Drug interaction check coverage: 100% system-wide

---

## Risks and Mitigations

- **LLM hallucination on medical claims** (Critical / Medium likelihood): Verification layer, fact checking against authoritative sources, confidence scoring.
- **External API downtime (RxNorm, FDA)** (High / Low likelihood): Response caching, graceful degradation, clear user messaging.
- **Prompt injection attacks** (High / Medium likelihood): Input sanitization, Pydantic validation, adversarial testing, system prompt hardening.
- **LLM API cost overruns** (Medium / Medium likelihood): Token tracking via LangSmith, prompt caching, model routing by complexity.
- **Patient data leakage** (Critical / Low likelihood): No PII to external APIs, trace redaction, ACL enforcement, audit logging.
- **OpenEMR upstream breaking changes** (Medium / Low likelihood): Module architecture isolates from core, version pinning, CI testing against OpenEMR releases.
- **Clinician over-reliance on agent** (High / Medium likelihood): Mandatory disclaimers, never diagnose/prescribe, human approval for all actions.

---

## Glossary

- **CareTopicz:** Working name for the OpenEMR AI agent.
- **LangGraph:** Python framework for building stateful, multi-step AI agent workflows.
- **LangSmith:** Observability and evaluation platform for LLM applications.
- **RxNorm:** NIH system for normalized drug naming and interaction data.
- **NPI:** National Provider Identifier — unique ID for healthcare providers.
- **FHIR R4:** Healthcare data exchange standard used by OpenEMR's REST API.
- **Verification Layer:** Deterministic code that validates agent responses against authoritative data before delivery.
- **Sidecar:** A service that runs alongside the main application, communicating via API.
- **ACL:** Access Control List — OpenEMR's role-based permission system.
- **Pydantic:** Python library for data validation using type annotations.
- **SOAP Notes:** Subjective, Objective, Assessment, Plan — standard clinical documentation format.
