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
3. **Variable duration** — Staff can schedule 1 month at a time ("just 2 months for now") or the full course (6 months for isotretinoin, 3 for biologics). Defaults adapt by protocol.
4. **Calculates all milestone dates** with compliance windows, automatically adjusting downstream dates when earlier milestones are completed
5. **Extends schedules** — When a patient reaches the end of scheduled months, staff says "Extend Susan's schedule by 2 months" and the system appends the next months' milestones.
6. **Completes or discontinues** — Normal course completion adds the final pregnancy test for FCBP patients. Early stop (adverse reaction, no effect, patient choice) logs the reason and cancels remaining milestones.
7. **Pauses and resumes** — Temporary holds (surgery, travel) put the schedule on hold without flagging milestones as overdue. Resume recalculates pending dates from the resume date.
8. **Detects scheduling conflicts** — Expired test windows, overdue milestones, approaching deadlines
9. **Surfaces alerts on the patient dashboard** — Any staff member opening a patient's chart immediately sees protocol status (green/yellow/red/blue for paused) without checking the med list
10. **Supports the full lifecycle** — From pre-prescription initiation through monthly cycles, pauses, extensions, and treatment completion or indefinite tracking for biologics

### Lifecycle Actions

| Action | Use Case | Example |
|--------|----------|---------|
| Create (with duration) | Start a schedule; optionally limit months | "Start isotretinoin for patient 2, FCBP, 2 months only" |
| Extend | Patient needs more months | "Extend Susan's schedule by 2 months" |
| Complete treatment | Normal course completion | "Complete Susan's isotretinoin treatment" |
| Discontinue | Stop early (adverse reaction, no effect, patient choice) | "Discontinue Phil's isotretinoin, adverse reaction" |
| Pause | Temporary hold (surgery, travel) | "Pause Susan's isotretinoin, surgery next month" |
| Resume | Reactivate after pause; dates shift forward | "Resume Susan's isotretinoin" |

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
- **Flexible scheduling** — Variable duration and extend let clinics schedule 1–3 months at a time instead of committing to a full 6 months upfront
- **Handles real-world interruptions** — Pause/resume and discontinue cover surgery, travel, adverse reactions, and patient choice without breaking the workflow
- **Ensures regulatory compliance** — Automated tracking reduces the risk of iPLEDGE violations
- **Scales across specialties** — The same system handles dermatology (iPLEDGE), rheumatology (biologics), psychiatry (clozapine REMS), oncology (chemo cycles)

## Technical Implementation

- **3 new database tables** in OpenEMR: `medication_protocols`, `patient_med_schedules`, `schedule_milestones` (including `paused` status for temporary holds)
- **PHP CRUD endpoints** for all schedule operations, secured to internal Docker network
- **Agent tool** (`medication_schedule`) with full lifecycle support:
  - Create (with optional `duration_months`), status, complete milestones
  - Extend (add months), complete treatment, discontinue (with reason)
  - Pause, resume (with date recalculation)
  - Reschedule milestone, cancel, detect conflicts, dashboard view
- **Patient dashboard banner** showing protocol status with color-coded urgency (green/yellow/red/blue for paused)
- **11 eval cases** covering schedule creation, short duration, extend, discontinue, status checks, gender clarification, duplicate prevention, cancellation, and biologic protocols
- **Verification layer integration** — schedule tool responses exempt from domain rules that would otherwise block medication-related content
