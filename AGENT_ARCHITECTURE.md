# CareTopicz Agent Architecture

## Overview

CareTopicz is an AI clinical assistant module for OpenEMR that manages regulated medication scheduling, drug interaction checking, symptom analysis, and clinical workflow automation. It runs as a sidecar service alongside OpenEMR, communicating exclusively through PHP REST endpoints.

## System Architecture
```
+--------------------------------------------------+
|                  Browser / Client                 |
|     Chat Widget  |  Dashboard Banner  |  Calendar |
+--------+---------+-----------+--------+-----------+
         |                     |
         v                     v
+--------------------------------------------------+
|              OpenEMR (PHP / Apache)               |
|                                                   |
|  mod-ai-agent/public/                             |
|    chat.php ---------> Agent Service (proxy)      |
|    med_schedule.php -> MariaDB (CRUD)             |
|    appointments.php -> OpenEMR Calendar           |
|    pdf_proxy.php ----> Agent Service (PDF fetch)  |
|                                                   |
|  Patient Dashboard Banner (PHP)                   |
|    Reads: patient_med_schedules                   |
|    Reads: schedule_milestones                     |
|    Shows: medication, screenings, next injection  |
+--------+---------+-----------+--------+-----------+
         |                     |
         v                     v
+--------------------------------------------------+
|           Agent Service (Python / FastAPI)         |
|                                                   |
|  Orchestrator: LangGraph ReAct Agent              |
|    - Claude Sonnet 4 (reasoning engine)           |
|    - Tool selection and multi-step planning       |
|    - Conversation state management                |
|                                                   |
|  Tool Registry (12 tools):                        |
|    Core: drug_interaction, symptom_lookup,         |
|          provider_search, insurance_provider,      |
|          appointment_check, insurance_coverage,    |
|          patient_summary, lab_results,             |
|          medication_list, patient_education        |
|    Bounty: medication_schedule, schedule_pdf       |
|                                                   |
|  Verification Layer:                              |
|    - Domain rules (never diagnose/prescribe)      |
|    - Fact checking                                |
|    - Hallucination detection                      |
|    - Confidence scoring                           |
|    - Safe tool bypass                             |
|                                                   |
|  PDF Generator (ReportLab)                        |
|    - Patient schedule documents                   |
|    - Served via /pdfs/ endpoint                   |
+--------+---------+-----------+--------+-----------+
         |                     |
         v                     v
+-------------------+   +-------------------+
|   MariaDB 11.8    |   |  Redis 7-alpine   |
|                   |   |                   |
| medication_       |   | Chat history      |
|   protocols       |   | (db 1, 7-day TTL) |
| patient_med_      |   | Session-based     |
|   schedules       |   | 20 msg window     |
| schedule_         |   |                   |
|   milestones      |   |                   |
+-------------------+   +-------------------+
```

## Request Flow

1. User types in chat widget (JavaScript)
2. Chat widget POSTs to `chat.php` (PHP proxy)
3. `chat.php` forwards to Agent Service port 8000
4. Agent Service loads conversation history from Redis
5. LangGraph orchestrator invokes Claude with system prompt + tools
6. Claude selects tool(s) and provides parameters
7. Tool executes (calls PHP endpoints on OpenEMR or external APIs)
8. Tool results returned to Claude for synthesis
9. Claude generates response
10. Verification layer checks response (domain rules, fact check, hallucination)
11. Response returned through PHP proxy to chat widget
12. Conversation saved to Redis

## Database Schema (Bounty)

### medication_protocols
Stores protocol templates as structured JSON. Each protocol defines the medication, patient category, milestone templates with timing rules, and compliance windows.

### patient_med_schedules
Links a patient to a protocol with status tracking. Statuses: initiating, active, completing, paused, completed, cancelled. Notes field stores actual medication name when using a shared protocol template.

### schedule_milestones
Individual steps within a schedule. Each milestone has a step name, due date, compliance window, status (pending, scheduled, completed, overdue), and completion tracking.

## Biologic Onboarding Flow

The conversational biologic flow is prompt-engineered, not hardcoded:

1. Agent detects biologic initiation request
2. Asks screening questions one at a time (first biologic?, TB, Hep B/C, baseline labs, prior auth)
3. Records dates for each screening
4. Creates schedule using adalimumab template protocol
5. Stores actual medication name in notes field
6. Attempts to auto-complete confirmed screening milestones
7. Offers appointment booking with correct dosing intervals
8. Offers PDF generation at end of workflow

Supported biologics (10): Humira, Enbrel, Remicade, Stelara, Cosentyx, Skyrizi, Tremfya, Taltz, Dupixent, Ilumya — each with correct FDA dosing schedules.

## Verification Layer

All agent responses pass through verification before reaching the user:

- **Domain rules**: Regex patterns detect diagnosis claims ("you have X") and prescription language ("take 500mg daily"). Violations are refused.
- **Safe tool bypass**: Responses from scheduling, drug interaction, symptom lookup, and other clinical tools skip fact-check gating to prevent false blocks.
- **Confidence scoring**: 0.9+ passes as-is, 0.7-0.9 adds disclaimer (if not already present), 0.5-0.7 adds strong disclaimer, below 0.5 refuses.
- **Duplicate disclaimer prevention**: Verifier checks if response already contains a clinical disclaimer before appending one.

## Memory System

- **Redis** (db 1): Stores conversation history as JSON arrays keyed by session ID
- **TTL**: 7 days per session
- **Window**: Last 20 messages retained per session
- **Session ID**: Generated client-side, stored in browser cookie (7-day expiry)
- **Persistence**: Survives container rebuilds and page refreshes

## Eval Suite

95 test cases across 6 datasets:
- **correctness.json** (26): Drug interactions, symptoms, providers verified against ground truth
- **adversarial.json** (16): Prompt injection, jailbreak, role-play bypass, credential claims
- **edge_cases.json** (17): Empty input, misspellings, unknown drugs, ambiguous queries
- **multi_step.json** (17): Multi-tool chains, sequential reasoning
- **med_schedule.json** (11): iPLEDGE, biologics, extend, cancel, duplicate prevention
- **mvp.json** (8): Core MVP functionality

Published publicly: github.com/MandeeTopicz/caretopicz-evals (CC BY 4.0)

## Deployment

- **Platform**: Google Cloud Platform (GCP)
- **VM**: e2-small (2 vCPU, 2GB RAM)
- **URL**: http://34.139.68.240:8300
- **Stack**: Docker Compose (OpenEMR + Agent + Redis)
- **Performance**: LCP 2.46s (optimized via PHP opcache + Apache deflate)
