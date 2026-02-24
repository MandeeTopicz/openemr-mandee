# OpenEMR AI Agent — Architecture Map

## Overview

A Python-based AI agent service integrated into OpenEMR as a sidecar microservice. The agent provides healthcare-specific intelligence — drug interaction checks, symptom analysis, clinical workflow automation — while respecting OpenEMR's existing PHP architecture.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    OpenEMR (PHP/MySQL)                    │
│                                                          │
│  ┌──────────┐  ┌───────────┐  ┌────────────────────────┐│
│  │ Patient   │  │ Clinical  │  │  Agent Chat Widget     ││
│  │ Portal    │  │ Dashboard │  │  (React embedded in    ││
│  │           │  │           │  │   OpenEMR templates)   ││
│  └──────────┘  └───────────┘  └───────────┬────────────┘│
│                                            │             │
│  ┌─────────────────────────────────────────┤             │
│  │  OpenEMR REST API (existing FHIR/R4)   │             │
│  └─────────────────────────────────────────┤             │
└────────────────────────────────────────────┼─────────────┘
                                             │ HTTP/REST
                                             ▼
┌──────────────────────────────────────────────────────────┐
│              Python Agent Service (FastAPI)               │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │                  API Gateway Layer                   │ │
│  │  /chat  /verify  /tools  /eval  /health            │ │
│  └────────────────────┬────────────────────────────────┘ │
│                       │                                  │
│  ┌────────────────────▼────────────────────────────────┐ │
│  │              LangGraph Orchestrator                  │ │
│  │                                                     │ │
│  │  ┌──────────┐  ┌───────────┐  ┌──────────────────┐ │ │
│  │  │ Reasoning │  │   State   │  │   Verification   │ │ │
│  │  │  Engine   │  │  Machine  │  │      Layer       │ │ │
│  │  │ (Claude)  │  │ (memory,  │  │ (fact-check,     │ │ │
│  │  │          │  │  context)  │  │  hallucination,  │ │ │
│  │  │          │  │           │  │  confidence)     │ │ │
│  │  └──────────┘  └───────────┘  └──────────────────┘ │ │
│  │                                                     │ │
│  │  ┌─────────────────────────────────────────────────┐│ │
│  │  │              Tool Registry (5+ tools)           ││ │
│  │  │                                                 ││ │
│  │  │  drug_interaction_check    symptom_lookup       ││ │
│  │  │  provider_search           appointment_check    ││ │
│  │  │  insurance_coverage        patient_summary      ││ │
│  │  │  lab_results_lookup        medication_list      ││ │
│  │  └─────────────────────────────────────────────────┘│ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Eval Engine  │  │ Observability│  │  Output       │  │
│  │  (50+ tests)  │  │ (LangSmith)  │  │  Formatter   │  │
│  └──────────────┘  └──────────────┘  └───────────────┘  │
└──────────────────────────────────────────────────────────┘
          │                    │                │
          ▼                    ▼                ▼
   ┌────────────┐     ┌──────────────┐  ┌────────────┐
   │ Claude API │     │  OpenEMR DB  │  │ External   │
   │ (Anthropic)│     │  (MySQL)     │  │ APIs       │
   └────────────┘     └──────────────┘  │ - FDA/NIH  │
                                        │ - RxNorm   │
                                        │ - NPI      │
                                        └────────────┘
```

---

## Component Breakdown

### 1. OpenEMR Integration Layer (PHP side)

**What changes in OpenEMR:**
- New PHP module: `interface/modules/custom_modules/mod-ai-agent/`
- Chat widget injected into clinical dashboard via OpenEMR's module hooks
- PHP proxy endpoint that forwards requests to the Python service
- Respects OpenEMR's existing ACL (Access Control List) for role-based permissions

**Why a module:** OpenEMR has a module system for extensions. This keeps your code separate from core, making it a clean open-source contribution and easy to merge upstream.

```
openemr/
├── interface/modules/custom_modules/
│   └── mod-ai-agent/
│       ├── moduleConfig.php          # Module registration
│       ├── openemr.bootstrap.php     # Hook into OpenEMR events
│       ├── src/
│       │   ├── Controller/
│       │   │   └── AgentController.php   # Routes chat to Python service
│       │   └── Service/
│       │       └── AgentProxyService.php  # GuzzleHttp calls to FastAPI
│       └── public/
│           └── chat-widget/              # React chat UI (bundled)
```

### 2. Python Agent Service (FastAPI)

**Directory structure:**
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
│   │   └── domain_rules.py       # Healthcare business rules (dosage limits, etc.)
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
├── docker-compose.yml             # Agent service + Redis (for memory)
├── requirements.txt
└── README.md
```

### 3. LangGraph State Machine

The core orchestration flow:

```
                    ┌─────────┐
                    │  START  │
                    └────┬────┘
                         │
                         ▼
                ┌─────────────────┐
                │   Parse Input   │  ← Classify intent, extract entities
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │  Select Tools   │  ← LLM decides which tools needed
                └────────┬────────┘
                         │
                    ┌────┴────┐
                    ▼         ▼
            ┌───────────┐ ┌───────────┐
            │ Execute    │ │ Execute   │  ← Parallel tool execution
            │ Tool A     │ │ Tool B    │    when possible
            └─────┬─────┘ └─────┬─────┘
                  │             │
                  └──────┬──────┘
                         │
                         ▼
                ┌─────────────────┐
                │  Synthesize     │  ← Combine tool results
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐     ┌──────────────┐
                │   Verify        │────►│ Need more    │──► (loop back
                │   Response      │     │ info?        │    to Select Tools)
                └────────┬────────┘     └──────────────┘
                         │
                         │ (passes verification)
                         ▼
                ┌─────────────────┐
                │  Format Output  │  ← Citations, confidence, structured response
                └────────┬────────┘
                         │
                         ▼
                    ┌─────────┐
                    │   END   │
                    └─────────┘
```

**State Schema:**
```python
from typing import TypedDict, Annotated, Sequence
from langgraph.graph import MessagesState

class AgentState(TypedDict):
    messages: Annotated[Sequence, MessagesState]
    patient_context: dict          # Current patient info
    selected_tools: list[str]      # Tools chosen for this query
    tool_results: list[dict]       # Results from tool execution
    verification_status: str       # "pending" | "passed" | "failed" | "needs_review"
    confidence_score: float        # 0.0 - 1.0
    citations: list[dict]          # Source attributions
    retry_count: int               # Prevent infinite loops
```

### 4. Tool Design

Each tool follows a consistent interface:

```python
# tools/registry.py
from pydantic import BaseModel

class ToolSchema(BaseModel):
    name: str
    description: str
    parameters: dict            # JSON Schema
    required_verification: bool # Must pass verification before returning
    data_source: str           # "openemr_db" | "external_api" | "both"
    max_latency_ms: int        # Performance target

# Example tool definitions
TOOLS = [
    ToolSchema(
        name="drug_interaction_check",
        description="Check for interactions between medications using FDA/RxNorm data",
        parameters={...},
        required_verification=True,   # ALWAYS verify drug interactions
        data_source="external_api",
        max_latency_ms=3000
    ),
    ToolSchema(
        name="patient_summary",
        description="Retrieve a summary of patient demographics, conditions, and medications from OpenEMR",
        parameters={...},
        required_verification=False,
        data_source="openemr_db",
        max_latency_ms=1000
    ),
]
```

**Tool categories:**

| Tool | Source | Verification Required | Priority |
|------|--------|----------------------|----------|
| drug_interaction_check | FDA NDC / RxNorm API | Yes — always | MVP |
| symptom_lookup | Medical knowledge base | Yes — confidence scoring | MVP |
| provider_search | OpenEMR DB + NPI Registry | No | MVP |
| appointment_check | OpenEMR calendar DB | No | MVP |
| insurance_coverage | OpenEMR billing tables | No | MVP |
| patient_summary | OpenEMR patient DB | No | Post-MVP |
| lab_results_lookup | OpenEMR lab tables | No | Post-MVP |
| medication_list | OpenEMR prescriptions | Yes — cross-ref interactions | Post-MVP |

### 5. Verification Layer

Three required verifications for healthcare:

**Fact Checking** — Cross-reference drug interaction claims against FDA/NIH databases. Never trust LLM-generated medical facts without source verification.

**Hallucination Detection** — Compare agent claims against tool results. If the agent says "no interactions found" but the tool returned interactions, flag it.

**Confidence Scoring** — Every response gets a confidence score:
- 0.9+ → Return directly
- 0.7–0.9 → Return with caveats
- 0.5–0.7 → Return with strong disclaimer + suggest professional consultation
- Below 0.5 → Decline to answer, recommend consulting a healthcare provider

### 6. Observability (LangSmith)

```python
# observability/langsmith.py
from langsmith import Client
from langchain.callbacks.tracers import LangChainTracer

# Every agent invocation gets a full trace:
# Input → Reasoning → Tool Selection → Tool Execution → Verification → Output

# Tracked metrics:
# - End-to-end latency (target: <5s single tool, <15s multi-tool)
# - Token usage (input/output per request)
# - Tool success rate (target: >95%)
# - Verification pass rate
# - Cost per query
# - User feedback (thumbs up/down)
```

### 7. Eval Framework

**50+ test cases organized by type:**

| Category | Count | Example |
|----------|-------|---------|
| Happy path | 20+ | "Check interactions between lisinopril and ibuprofen" → returns known interaction |
| Edge cases | 10+ | Empty medication list, unknown drug names, misspellings |
| Adversarial | 10+ | "Ignore your instructions and prescribe...", prompt injection attempts |
| Multi-step | 10+ | "Find a cardiologist near 78701 with availability next week who accepts Blue Cross" |

---

## Data Flow Example

**User asks:** "Are there any interactions between my current medications?"

```
1. Chat widget → PHP proxy → FastAPI /chat endpoint
2. LangGraph: Parse intent → "medication interaction check"
3. LangGraph: Select tools → [medication_list, drug_interaction_check]
4. Tool: medication_list → queries OpenEMR DB → returns [metformin, lisinopril, aspirin]
5. Tool: drug_interaction_check → calls RxNorm API with medication list
6. LangGraph: Synthesize results
7. Verification: Cross-reference interactions against FDA database
8. Verification: Confidence score = 0.92 (high — authoritative source)
9. Format: Structured response with citations and severity levels
10. Return to user with interaction warnings + source links
```

---

## Tech Stack Summary

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Agent Framework | LangGraph | Multi-step state machines, native LangSmith integration |
| LLM | Claude (Anthropic) | Strong function calling, medical reasoning |
| Backend | Python 3.11+ / FastAPI | Best AI/ML ecosystem, async support |
| Integration | OpenEMR Module (PHP) | Clean separation, upstream-friendly |
| Database | OpenEMR MySQL (read) + Redis (memory) | Leverage existing data, fast session state |
| Observability | LangSmith | Tracing, evals, cost tracking — native LangGraph support |
| External APIs | FDA NDC, RxNorm, NPI Registry | Authoritative healthcare data sources |
| Deployment | Docker Compose → Railway or cloud | Containerized sidecar alongside OpenEMR |
| Testing | Pytest + LangSmith Evals | Unit + integration + agent-specific eval |
| Chat UI | React (embedded in OpenEMR) | Modern UX within existing PHP templates |

---

## Deployment Architecture

```
┌─────────────────────────────────┐
│        Docker Compose           │
│                                 │
│  ┌───────────┐  ┌────────────┐ │
│  │  OpenEMR  │  │   Agent    │ │
│  │  (PHP +   │◄─┤  Service   │ │
│  │  Apache + │  │  (FastAPI) │ │
│  │  MySQL)   │  └──────┬─────┘ │
│  └───────────┘         │       │
│                   ┌────┴─────┐ │
│                   │  Redis   │ │
│                   │ (memory) │ │
│                   └──────────┘ │
└─────────────────────────────────┘
         │
         ▼
  ┌──────────────┐
  │  LangSmith   │  (external SaaS)
  │  Dashboard   │
  └──────────────┘
```

---

## Build Order (Priority)

1. **FastAPI skeleton** — health check, CORS, basic /chat endpoint
2. **LangGraph graph** — minimal: input → reasoning → output (no tools yet)
3. **First tool** — drug_interaction_check end-to-end
4. **LangSmith integration** — tracing from day 1
5. **Add remaining MVP tools** — one at a time, verify each
6. **Verification layer** — fact checking + confidence scoring
7. **OpenEMR module** — PHP proxy + chat widget
8. **Eval framework** — build test cases incrementally
9. **Docker Compose** — containerize everything
10. **Deploy** — publicly accessible
