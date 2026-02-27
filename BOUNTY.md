# CareTopicz Bounty: Regulated Medication Coordination Engine

## The Customer

**Dermatology and specialty clinics** managing patients on medications with complex regulatory scheduling requirements — particularly isotretinoin (iPLEDGE program), biologics, and other REMS medications.

The primary users are **medical assistants, nurses, and front desk staff** who coordinate the scheduling between providers, labs, pharmacies, and regulatory programs. Providers prescribe and move on — support staff manage the logistics.

## The Problem

A real dermatology patient had to redo her pregnancy tests **5 times** before ever starting Accutane, all due to scheduling coordination failures. iPLEDGE requires pregnancy tests within strict 7-day windows, 30-day waiting periods between tests, monthly verification windows (days 19-23), and 7-day prescription pickup deadlines. If any single date slips, downstream steps cascade and may require restarting.

No EHR — including OpenEMR — has built-in support for managing these cascading compliance timelines. Clinics use verbal instructions, sticky notes, and spreadsheets, leading to:

- Missed compliance windows requiring repeated tests
- Patient frustration and treatment delays
- Staff spending hours manually tracking deadlines
- Risk of regulatory non-compliance

## The Feature

An **AI-powered Regulated Medication Coordination Engine** that:

1. **Creates compliance schedules** when staff tells the agent a patient is starting a regulated medication
2. **Determines the correct protocol** based on patient demographics (sex, childbearing potential) and medication
3. **Calculates all milestone dates** with compliance windows, automatically adjusting downstream dates when earlier milestones are completed
4. **Detects scheduling conflicts** — expired test windows, overdue milestones, approaching deadlines
5. **Surfaces alerts on the patient dashboard** — any staff member opening a patient's chart immediately sees their protocol status without checking the med list or asking the agent
6. **Supports the full lifecycle** — from pre-prescription initiation through monthly cycles to treatment completion or indefinite tracking for biologics

### Supported Protocols

- **iPLEDGE (isotretinoin)** — Full support for all 3 patient categories: FCBP (pregnancy testing), non-FCBP female, and male
- **Biologics (adalimumab/Humira)** — TB screening, hepatitis screening, prior auth, biweekly injections, quarterly labs
- **Extensible** — Protocol templates are stored as structured data, making it straightforward to add clozapine REMS, methotrexate monitoring, chemotherapy cycles, etc.

## The Data Source

**FDA REMS (Risk Evaluation and Mitigation Strategies) program requirements** — specifically the iPLEDGE REMS for isotretinoin and FDA prescribing information for biologics. These are authoritative, publicly available regulatory requirements that define the exact scheduling rules, timing windows, and compliance criteria.

Protocol rules are stored as structured JSON in the `medication_protocols` table, sourced from official FDA REMS documentation and drug prescribing information.

## The Impact

- **Eliminates repeated tests** — The agent tracks compliance windows and flags conflicts before they cause failures
- **Reduces staff coordination burden** — Instead of manually tracking dates across multiple systems, staff asks the agent "What's due this week?"
- **Improves patient experience** — Fewer unnecessary visits, faster time to treatment start
- **Ensures regulatory compliance** — Automated tracking reduces the risk of iPLEDGE violations
- **Scales across specialties** — The same system handles dermatology (iPLEDGE), rheumatology (biologics), psychiatry (clozapine REMS), oncology (chemo cycles)

## Technical Implementation

- **3 new database tables** in OpenEMR: `medication_protocols`, `patient_med_schedules`, `schedule_milestones`
- **PHP CRUD endpoints** for all schedule operations, secured to internal Docker network
- **Agent tool** (`medication_schedule`) with full CRUD: create schedules, check status, complete milestones, cancel, reschedule, detect conflicts
- **Patient dashboard banner** showing protocol status with color-coded urgency
- **8 eval cases** covering schedule creation, status checks, gender clarification, duplicate prevention, cancellation, and biologic protocols
- **Verification layer integration** — schedule tool responses exempt from domain rules that would otherwise block medication-related content
