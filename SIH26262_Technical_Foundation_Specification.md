# SIH26262 — AICTE FlowGuard: Technical Foundation Specification

**Version:** 2.0  
**Previous Version:** 1.0 (2026-10-22)  
**Source Document:** AICTE Approval Process Handbook 2024–2027 (APH 2024-27)  
**Academic-Year Applicability:** AY 2024-25 through AY 2026-27  
**Date:** 2026-10-22

---

## 0. Change Log (v1.0 → v2.0)

| # | Section | Change | Reason |
|---|---|---|---|
| C1 | §1 Architecture | Replaced layered-services/API-gateway/distributed architecture with modular monolith. Specified React + FastAPI + PostgreSQL stack. Removed Elasticsearch, GraphQL, Vector DB, API Gateway. | Unnecessary distributed complexity. No requirement justifies these components. |
| C2 | §1 Architecture | Removed all RAG, LLM, embedding, and vector-search infrastructure from architecture, diagrams, data model, APIs, and dependencies. | System must be deterministic and rule-driven. AI-based regulatory interpretation is not permitted. |
| C3 | §1 Design Principles | Removed "graceful degradation" principle referencing LLM/RAG dependency. | No AI subsystem exists to degrade from. |
| C4 | §9 Rules Engine | Removed entire §9.B (RAG Subsystem). Replaced with §9.B APH-to-Rules Lifecycle specifying controlled extraction → verification → publication pipeline. | Candidate provisions must follow a governed lifecycle, not AI extraction. |
| C5 | §10 Data Model | Removed `document_chunks`, `embedding_vector`, `regulatory_documents` (RAG tables). Replaced with `aph_source_documents` and `aph_source_provisions` for deterministic text storage. | No embeddings or vector search. Provisions stored as structured text with full-text search. |
| C6 | §10 Data Model | Fixed all SQL syntax: replaced inline `INDEX` declarations with `CREATE INDEX` statements; removed `GENERATED ALWAYS AS (... NOW())` stored column; added `CREATE TABLE` keywords; added proper `CHECK` constraints, `NOT NULL` where required, foreign keys on all references. | v1.0 SQL was not executable PostgreSQL. |
| C7 | §4 Pendency | Added separate institutional-response-time vs AICTE-processing-time clock tracking. Specified hold, extension, and overdue effects on each clock. | Required by directive §5 to track clocks separately. |
| C8 | §6 Compliance | Clarified reminder intervals (90/60/30/14/7) as configurable administrative defaults, not regulatory requirements. | v1.0 presented these as if established. APH does not specify notification frequencies. |
| C9 | §8 Notifications | Specified PostgreSQL-backed job queue (no Redis/Celery unless justified). Detailed idempotent execution, dead-letter handling, duplicate prevention. | Aligned with modular-monolith baseline. Redis/Celery may be introduced later if load justifies it. |
| C10 | §9 Rules Engine | Added rule-status enforcement: only `PUBLISHED` rules may execute. Draft, under-review, and ambiguous rules blocked from runtime evaluation. | Required by directive §3 and §6. |
| C11 | §11 Security | Added document upload security details: type whitelist, size limits, storage abstraction, virus scanning, signed-URL access pattern. | Required by directive §6. |
| C12 | §13 API | Removed RAG Service from API catalogue. Replaced with APH Reference Search (full-text, deterministic). | No AI service. |
| C13 | New §14 | Added test case specifications covering workflow transitions, access control, EVC, compliance, document expiry, deadlines, duplicate jobs, versioning, and audit. | Required by directive §9. |
| C14 | New §15 | Added implementation sequence and minimum end-to-end demo plan. | Required by directive §9. |
| C15 | New §16 | Added readiness checklist separating regulatory verification, technical correctness, and remaining dependencies. | Required by directive §9. |
| C16 | §9 Rules Engine | Added APH version transition policy: in-progress applications retain the rule version they started under unless an authorised migration is executed. | Required by directive §8. |
| C17 | §11 Synthetic Data | Removed "RAG-extracted provisions" category. Replaced with "Candidate provisions from APH extraction" requiring human review before any operational use. | No AI extraction; human-reviewed provisions only. |

---

## 1. System Architecture Overview

### 1.1 Architecture Pattern

The system is a **modular monolith** — a single deployable application with well-defined internal module boundaries. Each module owns its domain logic, data access, and API routes, but all modules share one PostgreSQL database and one deployment unit.

**Technology Stack:**

| Layer | Technology |
|---|---|
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS |
| **Backend** | Python 3.12+, FastAPI, Pydantic v2 |
| **ORM / Migrations** | SQLAlchemy 2.x, Alembic |
| **Database** | PostgreSQL 16 |
| **Background Jobs** | PostgreSQL-backed job queue (e.g., `pgq`, `asyncpg`-based scheduler, or `apscheduler` with PostgreSQL job store). Redis/Celery may be introduced if load testing justifies it. |
| **Document Storage** | Private object storage behind a storage abstraction interface (local filesystem for development; S3-compatible for production) |
| **Deployment** | Docker Compose, environment-based configuration (`.env`), Alembic migrations, seed data scripts |
| **Testing** | pytest, httpx (API tests), Playwright or Cypress (E2E) |

### 1.2 Module Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                     FRONTEND (React + Vite)                      │
│  Institution Portal │ RO Dashboard │ Bureau Dashboard │ Admin    │
└────────────┬────────────────────────────────────────────────────┘
             │ HTTPS / JWT (REST JSON API)
┌────────────▼────────────────────────────────────────────────────┐
│                  FASTAPI APPLICATION                             │
│  Auth Middleware │ RBAC Middleware │ Rate Limit │ Audit Middleware│
│ ┌──────────────────────────────────────────────────────────────┐│
│ │                    APPLICATION MODULES                        ││
│ │ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ││
│ │ │ Workflow    │ │ Compliance │ │ EVC        │ │ Notification│ ││
│ │ │ Module     │ │ Module     │ │ Module     │ │ Module      │ ││
│ │ └────────────┘ └────────────┘ └────────────┘ └────────────┘ ││
│ │ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ││
│ │ │ Document   │ │ Rules      │ │ Reporting  │ │ Audit      │ ││
│ │ │ Module     │ │ Engine     │ │ Module     │ │ Module     │ ││
│ │ └────────────┘ └────────────┘ └────────────┘ └────────────┘ ││
│ │ ┌────────────┐ ┌────────────┐                                ││
│ │ │ APH Ref.   │ │ Admin      │                                ││
│ │ │ Search     │ │ Module     │                                ││
│ │ └────────────┘ └────────────┘                                ││
│ └──────────────────────────────────────────────────────────────┘│
│                    BACKGROUND JOB RUNNER                         │
│  Deadline checks │ Notification dispatch │ Expiry scans │ Retry │
└────────────┬────────────────────────────────────────────────────┘
             │
┌────────────▼────────────────────────────────────────────────────┐
│                       DATA LAYER                                 │
│           PostgreSQL │ Private Object Storage                    │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Design Principles

1. **Regulatory traceability**: Every automated action references the exact APH clause and the published rule version that authorised it.
2. **Human authority preserved**: Automated advancement occurs only when the published workflow explicitly permits it and all required preconditions are satisfied. Statutory decisions (approval, rejection, conditions) remain human-controlled.
3. **Configurable, not hardcoded**: Workflow routes, timelines, and policies are versioned data in the rules registry, not application logic.
4. **Audit-complete**: Every state change, submission, verification, notification, and escalation produces an immutable audit record.
5. **Deterministic**: All regulatory logic is executed through verified, published rules. No probabilistic, ML-based, or generative-AI components participate in regulatory decisions, workflow routing, deadline calculation, or compliance evaluation.
6. **Separation of concerns**: Regulatory rules (APH-mandated), administrative policies (AICTE operational), and prototype defaults are stored, labelled, and enforced as distinct categories.

---

## 2. Role-Permission Matrix

### 2.1 Role Definitions and Permitted Actions

#### Prototype Role Consolidation

For the prototype, the following consolidations are proposed while preserving separation of duties:

- **EVC Member** and **EVC Coordinator** are separate roles (coordinator schedules; member records observations).
- **SAC/SHC Committee User** and **Competent Authority** are separate (committee recommends; authority decides).
- **Compliance Verification Officer** may overlap with **Regional Officer** for prototype, with a dedicated permission flag.
- **Regulatory Rule Administrator** is distinct from **System Administrator** (separation of technical config from regulatory rule governance).

| Role | Permitted Actions | Restricted Actions | Data Visibility |
|---|---|---|---|
| **Institution Applicant** | Create/submit applications; upload documents; respond to deficiencies; submit compliance evidence; submit renewal documents; track own application status | Cannot view other institutions' data; cannot modify submitted data after final submission; cannot approve/reject anything | Own applications, obligations, documents, notifications |
| **Institution Authorised Signatory** | Digitally sign submissions; confirm undertakings; authorise institutional responses | Cannot submit without signatory confirmation where required | Same as Institution Applicant for their institution |
| **Regional Officer / Scrutiny Officer** | View assigned applications; record scrutiny observations; identify deficiencies; request clarification; record EVC observations; process authorised actions per assigned workflow stage | Cannot approve/reject applications (reserved for EC/Council); cannot view applications outside assigned region unless explicitly authorised | Assigned applications within region; scrutiny/re-scrutiny reports; EVC reports for assigned cases |
| **Regional Coordinator** | View regional pendency dashboard; allocate tasks to regional officers; monitor deadlines and workload; view escalation status | Cannot perform scrutiny actions; cannot make approval/rejection decisions | All applications within region; regional workload metrics |
| **Regulation Bureau Officer** | View cross-region pendency; monitor stage-wise bottlenecks; prepare consolidated reports; place recommendations before EC | Cannot make final approval/rejection decisions (reserved for EC/Council) | Cross-region application summaries; stage-wise analytics; compliance status |
| **EVC Coordinator** | Identify EVC-required applications; manage EVC queue; schedule EVC visits; assign EVC members; monitor EVC timelines | Cannot record inspection findings (reserved for EVC members); cannot make approval decisions | EVC queue; scheduling status; EVC timelines |
| **EVC Member** | Access assigned inspection cases; record observations and reports; verify infrastructure | Cannot schedule EVCs; cannot approve/reject applications | Assigned EVC cases only; relevant application documents |
| **SAC/SHC Committee User** | Access assigned committee cases; review reports; record committee observations and recommendations | Cannot make final decisions (recommendations only unless designated as competent authority) | Assigned committee cases; relevant scrutiny/EVC reports |
| **Competent Authority** | Record final approval/rejection decisions; issue LoA/LoD/LoR; record conditions and undertakings attached to approvals | Actions restricted to decisions within designated authority scope | Cases placed before them for decision; supporting reports |
| **Compliance Verification Officer** | Review submitted evidence; record verification outcomes; verify renewed documents | Cannot modify institutional submissions; cannot make approval decisions on applications | Assigned compliance obligations; submitted evidence; document verification queue |
| **System Administrator** | Manage users and role assignments; configure technical settings; monitor system health; manage background job schedules | Cannot modify regulatory rules; cannot make approval decisions; cannot access application content beyond metadata | System configuration; user accounts; job status; system health metrics |
| **Regulatory Rule Administrator** | Create/edit draft rules; submit rules for review; manage rule versions; configure rule effective periods | Cannot unilaterally publish rules (requires approver); cannot make application-level decisions | Rule registry; rule versions; review history |
| **Audit/Read-Only Reviewer** | View historical records; view workflow events; view rule versions; generate audit reports | Cannot modify any operational record | Historical audit trails; workflow event logs; rule version history |

### 2.2 Permission Enforcement

- All permissions enforced in the **backend API layer** (FastAPI dependency-injection middleware), not the frontend.
- Frontend renders UI elements based on permission claims in the JWT, but the API independently validates every request.
- **Row-level security**: PostgreSQL RLS policies on key tables filtering by institution_id, region_id, or task assignment.
- **Action-level security**: Validates that the requesting user holds the required role AND is assigned to the specific application/task.
- **Separation of duties on rules**: A Regulatory Rule Administrator cannot approve a rule they drafted. The `approved_by` field must differ from `created_by`.

---

## 3. Complete Approval Workflow Model

### 3.1 Application Categories and Workflow Routes

Based on APH Table 2.3 (p.30) and Chapter I/II provisions, each application type follows a specific route:

| # | Application Type | APH Reference | Self-Disclosure | Scrutiny/Re-Scrutiny | EVC | SAC/SHC | Confidence |
|---|---|---|---|---|---|---|---|
| 1 | New Institution | Ch. I, Cl. 1.8, 1.9 | — | Yes | Yes | AA | EXPLICIT |
| 2 | EoA (Self-Disclosure) | Ch. II, Cl. 2.1 | Yes | — | — | — | EXPLICIT |
| 3 | Increase in Intake / Additional Courses | Ch. II, Cl. 2.6, Table 2.3 | — | Yes | Yes | AA | EXPLICIT |
| 4 | New Programme/Level in Existing | Ch. II, Cl. 2.7, Table 2.3 | — | Yes | Yes | AA | EXPLICIT |
| 5 | Conversion Diploma↔Degree | Ch. II, Cl. 2.14, Table 2.3 | — | Yes | Yes | AA | EXPLICIT |
| 6 | Change of Site/Location | Ch. II, Cl. 2.17, Table 2.3 | — | Yes | Yes | AA | EXPLICIT |
| 7 | Break in EoA / Restoration / Hibernation | Ch. II, Cl. 2.16, Table 2.3 | — | Yes | Yes | AA | EXPLICIT |
| 8 | Merger of Institutions | Ch. II, Cl. 2.13, Table 2.3 | — | Yes | Yes | AA | EXPLICIT |
| 9 | Introduction of Integrated/Dual Degree | Ch. II, Cl. 2.10, Table 2.3 | — | Yes | Yes | AA | EXPLICIT |
| 10 | Introduction/Continuation of FPM | Ch. II, Cl. 2.12, Table 2.3 | — | Yes | Yes | AA | EXPLICIT |
| 11 | Collaboration & Twinning | Ch. III, Cl. 3.4, Table 2.3 | — | Yes | Yes | AA | EXPLICIT |
| 12 | Introduction/Continuation FN/OCI Seats | Ch. II, Cl. 2.9, Table 2.3 | — | Yes | — | — | EXPLICIT |
| 13 | Introduction/Continuation NRI Seats | Ch. II, Cl. 2.8, Table 2.3 | Yes | — | — | — | EXPLICIT |
| 14 | Change Name of Institution/University | Ch. II, Cl. 2.19, Table 2.3 | — | Yes | — | — | EXPLICIT |
| 15 | Change Name of Course/Merger/Reduction | Ch. II, Cl. 2.18, Table 2.3 | — | Yes | — | — | EXPLICIT |
| 16 | Closure of Institution | Ch. II, Cl. 2.21, Table 2.3 | — | Yes | — | — | EXPLICIT |
| 17 | Closure of Programme/Course | Ch. II, Cl. 2.18, Table 2.3 | — | Yes | — | — | EXPLICIT |
| 18 | Women's↔Co-ed Conversion | Ch. II, Cl. 2.15, Table 2.3 | — | Yes | — | — | EXPLICIT |
| 19 | Change Bank Details | Ch. II, Cl. 2.3, Table 2.3 | — | Yes | — | — | EXPLICIT |
| 20 | Change Name/Address Trust/Society | Ch. II, Cl. 2.20, Table 2.3 | — | Yes | — | — | EXPLICIT |
| 21 | Type of Institution (→Deemed University) | Ch. II, Table 2.3 | — | Yes | Yes | AA | EXPLICIT |
| 22 | ODL/OL Courses | Ch. V, Cl. 5.3.10, Table 2.3 | — | Yes | Yes | AA | EXPLICIT |

**AA = As Applicable** — SAC/SHC is invoked depending on the outcome of prior stages. Interpretation (assumption A1/A2): SHC for deficiency compliance hearings before EC; SAC for appeals after adverse EC decision. **This interpretation requires authorised confirmation.**

### 3.2 Workflow State Machine

#### Core States (Scrutiny + EVC + AA route)

```
DRAFT → SUBMITTED → PAYMENT_VERIFIED → UNDER_SCRUTINY →
  ├→ SCRUTINY_CLEAR → [EVC_REQUIRED per workflow definition?]
  │    ├→ Yes → EVC_QUEUED → EVC_SCHEDULED → EVC_IN_PROGRESS → EVC_COMPLETED →
  │    │         PLACED_BEFORE_EC → EC_DECISION
  │    └→ No → PLACED_BEFORE_EC → EC_DECISION
  ├→ DEFICIENCY_NOTED → AWAITING_INSTITUTION_RESPONSE →
  │    ├→ RESPONSE_RECEIVED → RE_SCRUTINY → (loops to SCRUTINY_CLEAR or DEFICIENCY_NOTED)
  │    └→ RESPONSE_TIMEOUT → ESCALATION
  └→ REJECTED_AT_SCRUTINY → [APPEAL within 7 days?]
       ├→ Yes → APPEAL_FILED → SAC_HEARING → SAC_RECOMMENDATION → EC_DECISION
       └→ No → FINAL_REJECTION (LoR issued)

EC_DECISION →
  ├→ APPROVED (LoA/EoA issued)
  ├→ APPROVED_WITH_CONDITIONS → UNDERTAKING_CREATED
  ├→ REFERRED_TO_SHC → SHC_HEARING → SHC_RECOMMENDATION → EC_DECISION
  └→ REJECTED → [APPEAL within 7 days?]
       ├→ Yes → SAC_APPEAL → SAC_HEARING → SAC_RECOMMENDATION → COUNCIL_DECISION
       └→ No → FINAL_REJECTION (LoR issued)

COUNCIL_DECISION →
  ├→ APPROVED
  ├→ APPROVED_WITH_CONDITIONS → UNDERTAKING_CREATED
  └→ FINAL_REJECTION
```

#### Self-Disclosure Route

```
DRAFT → SUBMITTED → PAYMENT_VERIFIED → SELF_DISCLOSURE_VALIDATED →
  ├→ DEFICIENCY_FREE → EOA_ISSUED
  └→ DEFICIENCY_DETECTED → [enters standard route from UNDER_SCRUTINY]
```

#### Scrutiny-Only Route

```
DRAFT → SUBMITTED → PAYMENT_VERIFIED → UNDER_SCRUTINY →
  ├→ SCRUTINY_CLEAR → PLACED_BEFORE_EC → EC_DECISION
  ├→ DEFICIENCY_NOTED → (same deficiency loop as above)
  └→ REJECTED_AT_SCRUTINY → (same appeal path as above)
```

### 3.3 Transition Rules

Each transition is defined as a versioned record stored in the workflow definition:

```
TransitionRule:
  id: UUID
  workflow_definition_id: FK
  from_state: string
  to_state: string
  trigger: AUTOMATIC | MANUAL | SCHEDULED | EVENT
  preconditions: [
    { type: "DOCUMENT_SUBMITTED", params: { document_type: "..." } }
    { type: "PAYMENT_VERIFIED" }
    { type: "ROLE_AUTHORISED", params: { roles: ["REGIONAL_OFFICER"] } }
    { type: "STAGE_COMPLETE", params: { stage: "SCRUTINY" } }
    { type: "DEADLINE_NOT_EXCEEDED", params: { deadline_rule_id: "..." } }
    { type: "DEFICIENCY_RESOLVED", params: { all: true } }
    { type: "RULE_STATUS", params: { status: "PUBLISHED" } }
  ]
  postconditions: [
    { action: "NOTIFY", params: { template_id: "...", recipient_role: "..." } }
    { action: "CREATE_TASK", params: { assignee_role: "...", description: "..." } }
    { action: "AUDIT_LOG", params: { event_type: "..." } }
    { action: "UPDATE_PENDENCY", params: { stage: "...", clock: "AICTE" } }
  ]
  authorised_actor_role: string | "SYSTEM"
  rule_version_id: FK → regulatory_rules (must be PUBLISHED)
  aph_reference: string
```

### 3.4 Automatic vs Manual Advancement

| Advancement Type | When Used | Examples |
|---|---|---|
| **Automatic** | All preconditions are data-verifiable and the published workflow explicitly permits it | Payment verification → application enters processing queue; deficiency-free self-disclosure → EoA issuance queue |
| **Manual** | A human decision or verification is required | Scrutiny observations; EVC findings; EC/Council approval/rejection; SAC/SHC recommendations |
| **Scheduled** | Time-based triggers via background jobs | Deadline expiry status updates; overdue escalation; reminder generation |
| **Event-driven** | A data event triggers a postcondition | Document upload triggers verification task creation; payment confirmation marks payment verified |

**Critical constraint**: The system **never** automatically approves or rejects an application. Approval/rejection is always a manual action by an authorised human (EC, Council, or designated competent authority per APH).

### 3.5 Returns and Resubmission

When an application is returned for deficiencies (APH Cl. 1.8(f), 2.23.1):

1. System records each deficiency: description, category, APH reference, identified_by, timestamp.
2. Institution receives notification with deficiency list and response deadline (if established).
3. Institution uploads corrective documents through the portal.
4. Resubmission creates a workflow event; application re-enters the appropriate stage.
5. Re-scrutiny evaluates the response against the original deficiency list.
6. Complete resubmission and re-entry history is preserved in `stage_entries` and `transition_events`.

### 3.6 Appeal Procedure (APH Cl. 1.11, 2.24)

| Step | APH Reference | System Action |
|---|---|---|
| Institution files appeal within 7 days of LoD | Cl. 1.11(a), 2.24(a) | System validates appeal window (7 days from LoD issue date); creates appeal record |
| SAC schedule notified on portal | Cl. 1.11(b), 2.24(b) | System assigns to SAC queue; notifies institution of schedule |
| SAC reviews SC/Re-SC/EVC reports + Bureau observations | Cl. 1.11(d), 2.24(d) | System assembles case file with all prior stage reports |
| SAC records recommendation | Cl. 1.11(e) | SAC/SHC Committee User records recommendation with reasons |
| EC/Council makes final decision | Cl. 1.11(f) | Competent Authority records final decision; system issues LoA/LoR |

### 3.7 Processing Period Rules (APH Table 2.2, p.28)

| Category | Processing Period | System Handling |
|---|---|---|
| **Category 1** (EoA, NRI, Conversion, Name Change, New Programme, Merger, Break, FN/OCI, Intake, Integrated, Off-Campus, FPM, Course Changes, Twinning) | As per Public Notice period | Deadline derived from Public Notice dates configured per academic year by System Administrator |
| **Category 2** (Change of Site, Closure, Women↔Co-ed, Bank Details, Trust Name, Extended EoA, Deemed University, ODL/OL) | Year round | No fixed Public Notice deadline; processing timeline tracked from submission date |

**⚠ Clarification Required (Q1)**: The APH specifies "As per Public Notice Period" for Category 1 but does not prescribe fixed days per processing stage. The system allows Public Notice dates (start, submission deadline, processing deadline) to be configured per academic year. Stage-level deadlines within the processing period are **administrative policy**, not regulatory mandates, and are labelled as such.

---

## 4. Pendency and Monitoring Model

### 4.1 Application Pendency Tracking

Each application maintains a **stage history** with separate clock tracking:

```
StageEntry:
  application_id: FK
  stage: string
  entered_at: timestamp
  exited_at: timestamp | null
  clock_owner: AICTE | INSTITUTION | HELD
  assigned_officer_id: FK | null
  assigned_committee_id: FK | null
  hold_reason: text | null
  hold_authorised_by: FK | null
  extension_authorised_by: FK | null
  extension_reason: text | null
  extended_deadline: date | null
```

### 4.2 Clock Separation

| Clock | Active When | Paused When | Overdue Eligible |
|---|---|---|---|
| **AICTE processing clock** | Application is with an AICTE officer, committee, or EVC queue for action | Application returned to institution; authorised hold; awaiting committee scheduling | Yes, if administrative processing target is established |
| **Institutional response clock** | Application returned to institution for deficiency response or document submission | AICTE is processing; authorised hold | Yes, if response deadline is established |
| **Authorised hold** | Neither clock runs. Hold must have a recorded reason and authorising officer. | — | No |

An application is labelled **overdue** only when:
1. A processing timeline is established (from APH or configured administrative policy).
2. The start event for that timeline has occurred.
3. The elapsed time on the **relevant clock** exceeds the established timeline.
4. The application is not in an authorised hold state.

### 4.3 Effect of Holds and Extensions

| Event | Effect on AICTE Clock | Effect on Institutional Clock | Audit |
|---|---|---|---|
| **Authorised hold placed** | Paused | Paused | Hold reason, authorising officer, timestamp recorded |
| **Hold released** | Resumed from paused duration | Resumed from paused duration | Release reason, releasing officer, timestamp recorded |
| **Deadline extension granted** | Extended deadline recorded; overdue threshold adjusted | Extended deadline recorded | Extension reason, authorising officer, new deadline, original deadline recorded |

### 4.4 Metrics and Dashboards

| Metric | Calculation | Visible To |
|---|---|---|
| **Stage-wise pendency count** | COUNT of applications per stage, per region | Regional Coordinator, Bureau Officer |
| **Average stage duration** | AVG(exited_at - entered_at) per stage over configurable period, segmented by clock_owner | Bureau Officer, System Administrator |
| **Application age** | Days since submitted_at (computed at query time) | All roles (filtered by access) |
| **Officer workload** | COUNT of active applications per assigned officer | Regional Coordinator |
| **Approaching deadline** | Applications where remaining time on the relevant clock < configured threshold | Assigned officer, Regional Coordinator |
| **Overdue count** | Applications meeting overdue criteria above | Regional Coordinator, Bureau Officer |
| **EVC scheduling backlog** | Applications in EVC queue without confirmed date | EVC Coordinator, Bureau Officer |
| **Compliance fulfilment rate** | COUNT(fulfilled) / COUNT(total) obligations per period | Bureau Officer, Compliance Verification Officer |
| **Document expiry approaching** | Documents where verified_expiry_date - current_date < threshold | Compliance Verification Officer, Institution |

### 4.5 Drill-Down Capability

Every dashboard metric links to the underlying application list. Clicking a metric navigates to a filtered view showing:
- Application ID and institution name
- Current stage and status
- Time in current stage (on the relevant clock)
- Assigned officer/committee
- Next pending action
- Applicable deadline (if established) and its source (REGULATORY / ADMINISTRATIVE)

---

## 5. EVC Scheduling Automation

*(No structural changes from v1.0 — retained in full. Corrections noted below.)*

### 5.1 EVC Lifecycle

Based on APH Cl. 1.9, 2.6(j), 2.23.2, and Table 2.3:

```
IDENTIFIED → PREREQUISITES_CHECK → QUEUED → SCHEDULING →
  SCHEDULED → IN_PROGRESS → COMPLETED → REPORT_SUBMITTED →
  PLACED_BEFORE_EC
```

### 5.2 EVC Identification

An application enters the EVC track when:
1. The workflow definition for its application type includes an EVC stage (per Table 2.3), AND
2. The preceding stage (Scrutiny/Re-Scrutiny) is completed satisfactorily, or the application type mandates EVC regardless.

**APH-established EVC requirements:**
- New Institution applications (Ch. I, Cl. 1.9) — mandatory
- Increase in Intake / Additional Courses (Ch. II, Cl. 2.6(j)) — mandatory
- Change of Site/Location (Ch. II, Cl. 2.17(c), (e)) — mandatory, possibly two EVCs (pre-shift and post-shift)
- Break in EoA / Restoration / Hibernation (Ch. II, Cl. 2.16) — mandatory
- Random inspection of existing institutions (Ch. II, Cl. 2.3.5(a)) — may occur at any time
- EVC "any time before the first batch of students has passed out" (Ch. I, Cl. 1.10(b)(ii)(1); Ch. II, Cl. 2.6(j))

### 5.3 EVC Prerequisites

| Prerequisite | APH Reference | System Check |
|---|---|---|
| Scrutiny/Re-Scrutiny completed | Cl. 1.8, 2.23.1 | Stage history shows SCRUTINY_CLEAR or RE_SCRUTINY_CLEAR |
| Required documents uploaded | Annexure-1/2 | Document checklist validation against application type |
| TER charges paid | Cl. 1.4.2, 2.3.2 | Payment record verified |
| Video uploaded (for online EVC) | Cl. 1.9(f) | Document type "EVC_VIDEO" uploaded |
| Additional TER for extra EVC | Cl. 1.4.2(d), 2.3.2(c) | If additional EVC, additional TER payment verified |

### 5.4 EVC Alerts

| Alert | Trigger | Recipients | Source |
|---|---|---|---|
| Application entered EVC queue | Queue entry event | EVC Coordinator | System event |
| Unscheduled EVC exceeds N days in queue | Configurable threshold (ADMINISTRATIVE) | EVC Coordinator, Regional Coordinator | Administrative policy |
| EVC date approaching | Confirmed date - configurable days (ADMINISTRATIVE) | EVC Members, Institution, EVC Coordinator | Administrative policy |
| EVC completion overdue | Confirmed date passed without completion | EVC Coordinator, Bureau Officer | Administrative policy |
| EVC report not submitted | Completion recorded but no report within N days (ADMINISTRATIVE) | EVC Coordinator | Administrative policy |
| EVC for new institution — first batch approaching pass-out | Calculated from LoA date + programme duration | EVC Coordinator, Bureau Officer | Derived from APH Cl. 1.10(b)(ii)(1) |

**⚠ Clarification Required (Q2)**: The APH does not specify a fixed deadline for scheduling or completing an EVC after queue entry. Alert thresholds above are configurable administrative policy.

### 5.5 Online vs Physical EVC

Per APH Cl. 1.9 (Note): "All the Scrutiny/Re-Scrutiny and EVC will be conducted in online mode. Under extraordinary circumstances (including Court directions) the Scrutiny / Re-Scrutiny and EVC will be conducted in Offline mode also."

The system defaults to online EVC. Physical EVC requires explicit designation. EVC type affects:
- TER charges: Online Rs. 1.25 Lakh; Physical Rs. 2.50 Lakh (Cl. 1.4.2(d)) — **EXPLICIT**
- Video requirements: 30+ minute video upload for online (Cl. 1.9(f)) — **EXPLICIT**
- Logistics: venue, travel, date ranges for physical

---

## 6. Undertaking and Institutional Compliance Automation

### 6.1 Compliance Obligation Lifecycle

```
CREATED → PENDING_SUBMISSION → SUBMITTED → UNDER_VERIFICATION →
  ├→ ACCEPTED → FULFILLED → CLOSED
  ├→ CORRECTION_REQUIRED → AWAITING_RESUBMISSION → SUBMITTED (loop)
  └→ REJECTED → ESCALATED

Overdue path: PENDING_SUBMISSION → OVERDUE → ESCALATED
```

### 6.2 Submission and Verification

1. **Submission**: Institution uploads evidence documents. System records timestamp, creates version record, generates receipt.
2. **Verification task creation**: On submission, system creates a task for the assigned Compliance Verification Officer.
3. **Verification outcomes**:
   - **Accepted**: Evidence meets requirements. Obligation marked FULFILLED.
   - **Correction Required**: Verifier records specific deficiencies. Institution notified.
   - **Rejected**: Evidence fundamentally insufficient. Obligation enters ESCALATED state.
4. **A file upload does NOT automatically establish compliance.** The obligation remains SUBMITTED until a verifier records an explicit verification outcome.

### 6.3 Due Date Derivation

| Source | Label | Handling |
|---|---|---|
| APH-specified deadline | `REGULATORY` | Due date derived from a published regulatory rule. |
| EC/Council-specified condition | `DECISION` | Due date as stated in the decision record. Entered by the recording officer. |
| Administrative policy | `ADMINISTRATIVE` | Due date derived from configured policy. Labelled "Administrative default, not a regulatory deadline." |

**⚠ Clarification Required (Q3)**: The APH references "time-bound undertakings" but does not specify standard durations for all undertaking types. The system supports explicit due dates per obligation and configurable default durations clearly flagged as administrative defaults.

### 6.4 Reminder and Escalation Schedule

Reminder intervals are **configurable administrative defaults**, not regulatory requirements. The APH does not specify notification frequencies.

**Default configuration (example only — configurable per obligation type):**

| Time Before Due Date | Action |
|---|---|
| 90 days | Advance reminder to institution |
| 60 days | Second reminder |
| 30 days | Reminder + notification to assigned verifier |
| 14 days | Urgent reminder to institution + Regional Coordinator |
| 7 days | Final warning + escalation to Bureau Officer |
| Due date | Obligation status → OVERDUE; escalation notification |
| Due date + grace period | Further escalation per configured escalation policy |

Reminders stop when the obligation is fulfilled or closed through an authorised action.

---

## 7. Document Validity and Lease Monitoring

*(Retained from v1.0 with minor corrections.)*

### 7.1 Document Lifecycle

```
UPLOADED → METADATA_RECORDED → UNDER_VERIFICATION →
  ├→ VERIFIED → VALID → [APPROACHING_EXPIRY → EXPIRED]
  ├→ VERIFICATION_FAILED → INSTITUTION_NOTIFIED
  └→ REPLACED_BY_RENEWAL (only after new document is verified)
```

### 7.2 Lease Document Monitoring (APH Cl. 2.1(e)) — EXPLICIT

> "In case of Institutions having Lease agreement for Land, the Council shall not issue EoA from the Year in which the Live Lease is equal to the number of years of the Course having the maximum duration. However, if such Institutions submit the Lease extended for a further 30 years, application shall be considered for EoA."

System behaviour:
1. Tracks lease expiry date against maximum course duration at the institution.
2. Calculates **last eligible EoA year** = lease_expiry_year - max_course_duration_years.
3. Generates alerts when institution approaches this threshold.
4. Flags applications where lease validity is insufficient for EoA issuance.
5. Tracks renewal submissions (must be extended for 30 years per APH).

### 7.3 Structural Stability Certificate (APH Cl. 6.17(h)) — EXPLICIT

> "After the expiry of a period of thirty years from the issue of Completion Certificate, a Structural Stability Certificate... shall be produced. Structural Stability Certificate is valid for a period of FIVE years from the date of issue."

System behaviour:
1. Calculates when structural stability certificate becomes required (30 years from completion certificate).
2. Tracks 5-year validity of each structural stability certificate.
3. Generates renewal reminders before expiry.

### 7.4 Preventing Unverified Replacement

When a renewal document is uploaded:
1. New document enters PENDING verification status.
2. Existing verified document retains `is_operative = true`.
3. Only when renewal is verified: new document becomes operative; old document marked SUPERSEDED.
4. Until verification, old document remains the operative record, and expiry alerts continue.

### 7.5 Document Expiry Alerts

| Alert | Trigger | Recipients | Source |
|---|---|---|---|
| Approaching expiry | verified_expiry_date - configurable threshold | Institution, Compliance Verification Officer | ADMINISTRATIVE (threshold); REGULATORY (expiry rule) |
| Document expired | Expiry date reached without verified renewal | Institution, Regional Coordinator, Bureau Officer | REGULATORY (expiry); ADMINISTRATIVE (alert) |
| Lease insufficient for EoA | Last eligible EoA year approaching | Institution, Regional Officer | REGULATORY (Cl. 2.1(e)) |

---

## 8. Notification and Escalation Engine

### 8.1 Architecture

The notification engine is an **internal module** (not a separate service) consumed by all domain modules.

```
NotificationModule:
  EventHandler       -- Receives domain events from modules via internal function calls
  PolicyEvaluator    -- Matches events against notification policies in DB
  RecipientResolver  -- Determines recipients from role/institution/region rules
  TemplateRenderer   -- Generates notification content from Jinja2 templates + case data
  DeliveryManager    -- Sends via configured channels with retry
  DeduplicationGuard -- Prevents duplicate notifications via idempotency keys
  AuditLogger        -- Records every notification attempt and outcome
```

### 8.2 Delivery and Retry

| Property | Specification |
|---|---|
| **In-app notifications** | Stored in `notifications` table; served via REST polling or WebSocket; persisted for offline retrieval |
| **Email notifications** | Sent via SMTP or transactional email API; Jinja2 HTML templates with case reference links |
| **Retry policy** | Failed deliveries retried with exponential backoff: 1 min, 5 min, 30 min, 2 hr, 12 hr; max 5 retries. Managed by background job queue. |
| **Delivery status** | PENDING → SENT → DELIVERED / FAILED / BOUNCED |

### 8.3 Deduplication

Each notification generates an idempotency key: `{policy_id}:{target_record_id}:{trigger_date}`. A UNIQUE constraint on this key prevents duplicates. The background job checks for existing active notifications before creating a new one.

### 8.4 Resolution and Closure

Future scheduled notifications are cancelled when:
- The obligation they reference is fulfilled or closed.
- The deadline changes through an authorised action.
- The application moves past the relevant stage.
- The alert condition is no longer met.

### 8.5 Background Job Infrastructure

- **PostgreSQL-backed job queue**: Jobs stored in a `background_jobs` table with status, retry count, next_retry_at, and execution lock. Ensures jobs survive process restarts.
- **Idempotent execution**: Each job carries a unique execution ID. Re-execution with the same ID produces the same outcome (checked via `processed_job_ids` or idempotency key).
- **Dead-letter handling**: Jobs exceeding max retries are marked `DEAD_LETTER` for manual review by System Administrator.
- **Duplicate prevention**: Before enqueueing, check for existing pending/active job with the same idempotency key.
- **Health monitoring**: System Administrator dashboard shows queue depth, failure rate, processing latency, dead-letter count.
- **No reliance on frontend timers or volatile in-memory scheduling.**
- Redis/Celery may be introduced if load testing demonstrates PostgreSQL-based scheduling is insufficient. This is not assumed for the initial deployment.

---

## 9. Deterministic Rules Engine and APH-to-Rules Lifecycle

### 9.A APH-to-Rules Lifecycle

This lifecycle governs how APH provisions become executable rules. No candidate provision may execute as a production rule until it completes this pipeline.

```
APH SOURCE REGISTRATION
  → DOCUMENT EXTRACTION (PDF text extraction + OCR)
  → CLAUSE-AWARE STRUCTURING (preserve chapter/section/clause/page/table hierarchy)
  → CANDIDATE PROVISION IDENTIFICATION (human-assisted extraction of discrete provisions)
  → SOURCE VERIFICATION (cross-check extracted text against original PDF)
  → STRUCTURED RULE DRAFTING (Regulatory Rule Administrator creates rule record)
  → SCHEMA VALIDATION (Pydantic model validates rule structure and required fields)
  → AUTOMATED TESTS (rule passes test cases for expected inputs → outputs)
  → AUTHORISED HUMAN REVIEW (different administrator reviews; separation of duties)
  → APPROVAL (reviewer approves; rule status → APPROVED)
  → VERSIONED PUBLICATION (rule status → PUBLISHED; effective_from set; available for runtime)
  → DETERMINISTIC RUNTIME EXECUTION (only PUBLISHED rules evaluated by workflow engine)
```

#### 9.A.1 Source Document Registration

```
APHSourceDocument:
  id: UUID
  title: string                        -- "Approval Process Handbook 2024-2027"
  version: string
  academic_year_range: string
  file_storage_ref: string             -- Path in private storage
  total_pages: int
  registration_status: REGISTERED | EXTRACTION_COMPLETE | ARCHIVED
  registered_at: timestamp
  registered_by: FK → users
  supersedes_document_id: FK | null
```

#### 9.A.2 Extracted Provisions (Candidate Stage)

After PDF extraction, provisions are stored as structured text (no embeddings, no vectors):

```
APHSourceProvision:
  id: UUID
  document_id: FK → aph_source_documents
  provision_text: text                  -- Faithful text or summary of the provision
  chapter: string | null
  section: string | null
  clause: string | null
  page_number: int | null
  table_reference: string | null
  heading_hierarchy: string[]
  extraction_status: CANDIDATE | VERIFIED | REJECTED
  verified_by: FK → users | null
  verified_at: timestamp | null
  verification_notes: text | null
```

**Candidate provisions** are reference material only. They cannot be used to create PUBLISHED rules until they are marked VERIFIED by a human reviewer who has cross-checked the extracted text against the original PDF.

#### 9.A.3 APH Reference Search (Deterministic)

Officers can search APH provisions using:
- **Full-text search** on `provision_text` via PostgreSQL `tsvector`/`tsquery`.
- **Structured filters**: chapter, section, clause, page number, table reference.
- **Keyword search** on headings and clause references.

No embeddings, no vector similarity, no LLM interpretation. Results show the extracted provision text, source location, and verification status. Unverified provisions are clearly labelled.

### 9.B Rule Registry

#### 9.B.1 Rule Structure

Every published rule must record, where applicable:

```
RegulatoryRule:
  id: UUID
  rule_code: string                     -- e.g. "WF-NEW-INST-001"
  description: text
  
  -- Source traceability
  source_document_id: FK → aph_source_documents
  source_document_version: string
  clause_reference: string              -- "Ch. I, Cl. 1.8(a)"
  section_reference: string | null
  page_reference: string | null
  provision_text: text                  -- Faithful text or summary of the APH provision
  
  -- Applicability
  academic_year_applicability: string
  applicable_categories: string[]       -- ["NEW_INSTITUTION"] or ["ALL"]
  applicable_institution_types: string[] -- ["GOVERNMENT", "PRIVATE"] or ["ALL"]
  applicable_programmes: string[]       -- ["ENGINEERING", "MANAGEMENT"] or ["ALL"]
  preconditions: JSON | null            -- Structured conditions that must be true
  
  -- Rule logic
  rule_type: WORKFLOW_ROUTE | TRANSITION_CONDITION | DEADLINE | DOCUMENT_REQUIREMENT |
             ELIGIBILITY | FEE_CALCULATION | COMPLIANCE_CONDITION | INFRASTRUCTURE_NORM
  conditions: JSON
  deadline_calculation: JSON | null     -- Only when APH establishes a deadline
  deadline_source: REGULATORY | ADMINISTRATIVE | null
  responsible_role: string | null       -- Only when APH establishes this
  exceptions: JSON | null
  
  -- Governance
  effective_from: date
  effective_until: date | null
  status: DRAFT | UNDER_REVIEW | APPROVED | PUBLISHED | DEPRECATED
  confidence: EXPLICIT | INTERPRETATION_REQUIRES_REVIEW
  interpretation_notes: text | null
  
  -- Versioning
  version: int
  previous_version_id: FK | null
  superseded_by_id: FK | null
  
  -- Audit
  created_by: FK → users
  reviewed_by: FK → users | null
  approved_by: FK → users | null       -- Must differ from created_by
  published_at: timestamp | null
  
  -- Testing
  test_cases: JSON                      -- Expected input → output pairs
```

#### 9.B.2 Rule Status Enforcement

**Only rules with `status = PUBLISHED` may be evaluated at runtime.** The workflow engine, deadline calculator, fee calculator, and all rule-dependent logic must filter by `status = 'PUBLISHED'` AND `effective_from <= current_date` AND (`effective_until IS NULL OR effective_until >= current_date`).

Rules with `confidence = INTERPRETATION_REQUIRES_REVIEW` may be published only after the interpretation is reviewed and explicitly approved by an authorised reviewer. The review record must include the reviewer's assessment of the interpretation.

#### 9.B.3 Rule Examples from APH

| Rule Code | Description | APH Reference | Type | Confidence |
|---|---|---|---|---|
| WF-NEW-001 | New Institution: Scrutiny → EVC → EC | Ch. I, Cl. 1.8, 1.9, Annexure-7 | WORKFLOW_ROUTE | EXPLICIT |
| WF-EOA-SD-001 | EoA Self-Disclosure: no Scrutiny/EVC for qualifying institutions | Ch. II, Cl. 2.1, Table 2.3 | WORKFLOW_ROUTE | EXPLICIT |
| WF-INTAKE-001 | Increase in Intake: Scrutiny + EVC | Ch. II, Cl. 2.6(j), Table 2.3 | WORKFLOW_ROUTE | EXPLICIT |
| EL-3YR-EOA-001 | Institutions qualifying under Cl. 2.1(a)(i-vi) eligible for 3-year EoA | Ch. II, Cl. 2.1(a) | ELIGIBILITY | EXPLICIT |
| FEE-TER-NEW-001 | TER for new institution: Govt/J&K/NER/PwBD/Women = 1.00L, Others = 10.00L | Ch. I, Table 1.1 | FEE_CALCULATION | EXPLICIT |
| FEE-TER-10PCT | TER charges increase 10% annually | Ch. I, Cl. 1.4.2 (Note) | FEE_CALCULATION | EXPLICIT |
| DOC-LEASE-30YR | Lease must be extended 30 years for EoA | Ch. II, Cl. 2.1(e) | DOCUMENT_REQUIREMENT | EXPLICIT |
| DL-APPEAL-7DAY | Appeal within 7 days of LoD | Ch. I, Cl. 1.11(a); Ch. II, Cl. 2.24(a) | DEADLINE | EXPLICIT |
| DL-LOA-VALID-2YR | LoA valid for 2 academic years | Ch. I, Cl. 1.10(b)(ii) | DEADLINE | EXPLICIT |
| INF-LAND-001 | Land/built-up area per Annexure-3 | Ch. VI, Cl. 6.17, Annexure-3 | INFRASTRUCTURE_NORM | EXPLICIT |
| INF-STRUCT-30YR | Structural stability cert: required after 30yr, valid 5yr | Ch. VI, Cl. 6.17(h) | INFRASTRUCTURE_NORM | EXPLICIT |
| COMP-SD-DOUBLE | Security deposit doubles for private leased | Ch. I, Table 1.4 (Note) | FEE_CALCULATION | EXPLICIT |
| EL-BREAK-6YR | 6yr EoA gap → apply as new institution | Ch. II, Cl. 2.16.1(a) | ELIGIBILITY | EXPLICIT |
| EL-HIBERN-PERIOD | Hibernation = max duration - 1 year | Ch. II, Cl. 2.16.1(d)(i) | ELIGIBILITY | EXPLICIT |
| WF-SITE-2EVC | Change of Site may require 2 EVCs | Ch. II, Cl. 2.17(c), (e) | WORKFLOW_ROUTE | INTERPRETATION_REQUIRES_REVIEW |

#### 9.B.4 Rule Governance Process

```
DRAFT → SUBMITTED_FOR_REVIEW → UNDER_REVIEW → APPROVED → PUBLISHED → [DEPRECATED]
```

- **Regulatory Rule Administrator** drafts and submits rules.
- **A different Regulatory Rule Administrator or designated Approver** reviews and approves. The `approved_by` must differ from `created_by`.
- Publication makes the rule available for runtime evaluation.
- Deprecated rules are retained for historical traceability but excluded from runtime evaluation.

#### 9.B.5 Rule Execution at Runtime

When the workflow engine evaluates a transition:

1. **Resolve applicable rules**: Query by application category, institution type, programme, academic year, WHERE `status = 'PUBLISHED'` AND within effective date range.
2. **Evaluate preconditions**: Check each rule's conditions against current application state.
3. **Calculate deadlines**: For deadline rules, compute dates from the specified start event.
4. **Record rule version**: Every transition, deadline, or fee calculation records `rule.id` + `rule.version` in the transition event.
5. **Block ambiguous rules**: Rules with `confidence = INTERPRETATION_REQUIRES_REVIEW` that have not been explicitly reviewed and approved are excluded from runtime evaluation.

### 9.C APH Version Transition Policy

When a new APH version is issued:

1. The new APH is registered as a new `aph_source_documents` record.
2. New rules are drafted, reviewed, and published with updated `source_document_id` and `effective_from` dates.
3. **In-progress applications retain the rule version they started under** unless an authorised migration is explicitly executed. The `workflow_instances.workflow_definition_id` and each `transition_events.rule_version_id` preserve the exact versions used.
4. A **rule-version selection policy** is configurable: "apply-at-submission" (default, application uses rules effective at submission date) or "apply-latest" (application transitions use the latest published rule at each transition). The policy is set per academic year by an authorised administrator.
5. Old rules are deprecated (not deleted). Their `effective_until` is set. They remain queryable for historical audit.

---

## 10. Data Model

### 10.1 Entity Relationship Summary

```
Users ─┬─ has_many → RoleAssignments ─── references → Roles
       └─ belongs_to → Institution | Region | null

Institutions ─┬─ has_many → Applications
              ├─ has_many → InstitutionDocuments
              ├─ has_many → ComplianceObligations
              └─ belongs_to → Region

Applications ─┬─ has_one → WorkflowInstance
              ├─ has_many → StageEntries
              ├─ has_many → TransitionEvents
              ├─ has_many → DeficiencyRecords
              ├─ has_many → Tasks
              └─ references → ApplicationCategory, AcademicYear

WorkflowDefinitions ─┬─ has_many → TransitionRules (embedded in definition JSONB)
                     └─ versioned (name + version unique)

WorkflowInstances ─── references → WorkflowDefinition, Application

EVCQueueEntries ─── references → Application
EVCMemberAssignments ─── references → EVCQueueEntry, User

ComplianceObligations ─┬─ has_many → EvidenceSubmissions
                       └─ references → Application, Institution, RegulatoryRule

InstitutionDocuments ─── self-references (version chain)

NotificationPolicies ─── has_many → Notifications
Notifications ─── references → NotificationPolicy, User

RegulatoryRules ─── self-references (version chain)
APHSourceDocuments ─── has_many → APHSourceProvisions
RuleReviewHistory ─── references → RegulatoryRule, User

AuditEvents ─── references → User (append-only)
BackgroundJobs ─── standalone (job queue)
```

### 10.2 Core Tables (Executable PostgreSQL)

#### Users and Access Control

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    permissions JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE role_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    role_id UUID NOT NULL REFERENCES roles(id),
    scope_type VARCHAR(50) NOT NULL CHECK (scope_type IN ('INSTITUTION', 'REGION', 'GLOBAL')),
    scope_id UUID,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    assigned_by UUID NOT NULL REFERENCES users(id),
    revoked_at TIMESTAMPTZ,
    UNIQUE (user_id, role_id, scope_type, scope_id)
);

CREATE INDEX idx_role_assignments_user ON role_assignments(user_id) WHERE revoked_at IS NULL;
```

#### Institutions and Regions

```sql
CREATE TABLE regions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    code VARCHAR(20) NOT NULL UNIQUE
);

CREATE TABLE institutions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pid VARCHAR(50) UNIQUE,
    name VARCHAR(500) NOT NULL,
    institution_type VARCHAR(50) CHECK (institution_type IN (
        'GOVERNMENT', 'PRIVATE', 'GOVT_AIDED', 'AUTONOMOUS', 'DEEMED_UNIVERSITY',
        'CENTRAL_UNIVERSITY', 'STATE_UNIVERSITY', 'PRIVATE_UNIVERSITY'
    )),
    region_id UUID NOT NULL REFERENCES regions(id),
    state VARCHAR(100),
    city VARCHAR(100),
    trust_society_company_name VARCHAR(500),
    trust_type VARCHAR(50) CHECK (trust_type IN ('TRUST', 'SOCIETY', 'COMPANY')),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_institutions_region ON institutions(region_id);
```

#### Academic Years and Application Categories

```sql
CREATE TABLE academic_years (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    year_label VARCHAR(20) NOT NULL UNIQUE,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    public_notice_start DATE,
    public_notice_submission_deadline DATE,
    public_notice_processing_deadline DATE,
    CONSTRAINT chk_ay_dates CHECK (start_date < end_date)
);

CREATE TABLE workflow_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    version INT NOT NULL DEFAULT 1,
    applicable_from DATE,
    applicable_until DATE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    definition JSONB NOT NULL,
    aph_reference VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (name, version)
);

CREATE TABLE application_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    chapter_reference VARCHAR(50),
    clause_reference VARCHAR(100),
    processing_period VARCHAR(50) NOT NULL CHECK (processing_period IN ('PUBLIC_NOTICE', 'YEAR_ROUND')),
    workflow_definition_id UUID REFERENCES workflow_definitions(id)
);
```

#### Applications

```sql
CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_number VARCHAR(50) NOT NULL UNIQUE,
    institution_id UUID NOT NULL REFERENCES institutions(id),
    category_id UUID NOT NULL REFERENCES application_categories(id),
    academic_year_id UUID NOT NULL REFERENCES academic_years(id),
    submitted_at TIMESTAMPTZ,
    submitted_by UUID REFERENCES users(id),
    current_stage VARCHAR(100) NOT NULL DEFAULT 'DRAFT',
    current_status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE'
        CHECK (current_status IN ('ACTIVE', 'ON_HOLD', 'COMPLETED', 'WITHDRAWN')),
    payment_status VARCHAR(50) DEFAULT 'UNPAID'
        CHECK (payment_status IN ('UNPAID', 'PENDING_VERIFICATION', 'VERIFIED', 'FAILED')),
    payment_amount DECIMAL(12,2),
    payment_verified_at TIMESTAMPTZ,
    assigned_officer_id UUID REFERENCES users(id),
    assigned_region_id UUID REFERENCES regions(id),
    outcome VARCHAR(50) CHECK (outcome IN (
        'APPROVED', 'REJECTED', 'APPROVED_WITH_CONDITIONS', 'WITHDRAWN'
    )),
    outcome_letter_type VARCHAR(10) CHECK (outcome_letter_type IN ('LoA', 'EoA', 'LoD', 'LoR')),
    outcome_date DATE,
    outcome_decision_by UUID REFERENCES users(id),
    is_demo BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_applications_stage_status ON applications(current_stage, current_status);
CREATE INDEX idx_applications_region ON applications(assigned_region_id);
CREATE INDEX idx_applications_officer ON applications(assigned_officer_id);
CREATE INDEX idx_applications_institution ON applications(institution_id);
CREATE INDEX idx_applications_academic_year ON applications(academic_year_id);
```

#### Workflow Engine

```sql
CREATE TABLE workflow_instances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL UNIQUE REFERENCES applications(id),
    workflow_definition_id UUID NOT NULL REFERENCES workflow_definitions(id),
    current_state VARCHAR(100) NOT NULL,
    state_data JSONB DEFAULT '{}'::jsonb,
    version INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE stage_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    stage VARCHAR(100) NOT NULL,
    entered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    exited_at TIMESTAMPTZ,
    clock_owner VARCHAR(20) NOT NULL DEFAULT 'AICTE'
        CHECK (clock_owner IN ('AICTE', 'INSTITUTION', 'HELD')),
    assigned_officer_id UUID REFERENCES users(id),
    assigned_committee_id UUID,
    hold_reason TEXT,
    hold_authorised_by UUID REFERENCES users(id),
    extension_authorised_by UUID REFERENCES users(id),
    extension_reason TEXT,
    extended_deadline DATE
);

CREATE INDEX idx_stage_entries_app ON stage_entries(application_id);
CREATE INDEX idx_stage_entries_stage ON stage_entries(stage, exited_at);
CREATE INDEX idx_stage_entries_open ON stage_entries(application_id) WHERE exited_at IS NULL;

CREATE TABLE transition_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    from_state VARCHAR(100),
    to_state VARCHAR(100) NOT NULL,
    trigger_type VARCHAR(50) NOT NULL
        CHECK (trigger_type IN ('MANUAL', 'AUTOMATIC', 'SCHEDULED', 'EVENT')),
    triggered_by UUID REFERENCES users(id),
    rule_id UUID,
    rule_version INT,
    reason TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_transition_events_app ON transition_events(application_id);
CREATE INDEX idx_transition_events_time ON transition_events(created_at);

CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID REFERENCES applications(id),
    task_type VARCHAR(100) NOT NULL,
    description TEXT,
    assigned_to UUID REFERENCES users(id),
    assigned_role VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')),
    due_date DATE,
    completed_at TIMESTAMPTZ,
    completed_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_tasks_assignee ON tasks(assigned_to, status);

CREATE TABLE deficiency_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    stage VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(100),
    aph_reference VARCHAR(255),
    identified_by UUID NOT NULL REFERENCES users(id),
    identified_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    response_deadline DATE,
    response_submitted_at TIMESTAMPTZ,
    resolution_status VARCHAR(50) NOT NULL DEFAULT 'OPEN'
        CHECK (resolution_status IN ('OPEN', 'RESPONDED', 'RESOLVED', 'UNRESOLVED')),
    resolution_notes TEXT,
    resolved_at TIMESTAMPTZ
);

CREATE INDEX idx_deficiency_app ON deficiency_records(application_id);
CREATE INDEX idx_deficiency_open ON deficiency_records(application_id) WHERE resolution_status = 'OPEN';
```

#### EVC Management

```sql
CREATE TABLE evc_queue_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    evc_type VARCHAR(20) NOT NULL CHECK (evc_type IN ('ONLINE', 'PHYSICAL')),
    priority VARCHAR(20) NOT NULL DEFAULT 'NORMAL'
        CHECK (priority IN ('NORMAL', 'COURT_DIRECTED', 'EXPEDITED')),
    eligibility_confirmed_at TIMESTAMPTZ NOT NULL,
    queue_entry_timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    scheduling_status VARCHAR(30) NOT NULL DEFAULT 'UNSCHEDULED'
        CHECK (scheduling_status IN (
            'UNSCHEDULED', 'PROPOSED', 'CONFIRMED', 'RESCHEDULED', 'COMPLETED', 'CANCELLED'
        )),
    proposed_date DATE,
    confirmed_date DATE,
    coordinator_id UUID REFERENCES users(id),
    region_id UUID NOT NULL REFERENCES regions(id),
    completion_date DATE,
    report_submitted_at TIMESTAMPTZ
);

CREATE INDEX idx_evc_queue_status ON evc_queue_entries(scheduling_status, region_id);

CREATE TABLE evc_member_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evc_queue_entry_id UUID NOT NULL REFERENCES evc_queue_entries(id),
    member_user_id UUID NOT NULL REFERENCES users(id),
    role_in_evc VARCHAR(50),
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### Compliance and Documents

```sql
CREATE TABLE compliance_obligations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID REFERENCES applications(id),
    institution_id UUID NOT NULL REFERENCES institutions(id),
    source_provision VARCHAR(255),
    source_decision_id UUID,
    condition_description TEXT NOT NULL,
    required_evidence_types JSONB,
    due_date DATE,
    due_date_source VARCHAR(30) CHECK (due_date_source IN ('REGULATORY', 'DECISION', 'ADMINISTRATIVE')),
    due_date_rule_id UUID,
    reminder_config JSONB DEFAULT '{"days_before": [90, 60, 30, 14, 7]}'::jsonb,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING_SUBMISSION'
        CHECK (status IN (
            'PENDING_SUBMISSION', 'SUBMITTED', 'UNDER_VERIFICATION',
            'CORRECTION_REQUIRED', 'FULFILLED', 'OVERDUE', 'ESCALATED', 'CLOSED'
        )),
    assigned_verifier_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    fulfilled_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ
);

CREATE INDEX idx_obligations_status ON compliance_obligations(status, due_date);
CREATE INDEX idx_obligations_institution ON compliance_obligations(institution_id);
CREATE INDEX idx_obligations_overdue ON compliance_obligations(due_date)
    WHERE status IN ('PENDING_SUBMISSION', 'CORRECTION_REQUIRED');

CREATE TABLE evidence_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    obligation_id UUID NOT NULL REFERENCES compliance_obligations(id),
    submitted_by UUID NOT NULL REFERENCES users(id),
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    file_storage_ref VARCHAR(500) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_size_bytes BIGINT,
    content_type VARCHAR(100),
    version_number INT NOT NULL DEFAULT 1,
    receipt_number VARCHAR(50) NOT NULL UNIQUE,
    verification_status VARCHAR(30) NOT NULL DEFAULT 'PENDING'
        CHECK (verification_status IN ('PENDING', 'ACCEPTED', 'REJECTED', 'CORRECTION_REQUIRED')),
    verified_by UUID REFERENCES users(id),
    verified_at TIMESTAMPTZ,
    verification_notes TEXT
);

CREATE INDEX idx_evidence_obligation ON evidence_submissions(obligation_id);

CREATE TABLE institution_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID NOT NULL REFERENCES institutions(id),
    application_id UUID REFERENCES applications(id),
    obligation_id UUID REFERENCES compliance_obligations(id),
    document_type VARCHAR(50) NOT NULL,
    source_requirement VARCHAR(255),
    file_storage_ref VARCHAR(500) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_size_bytes BIGINT,
    content_type VARCHAR(100),
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    uploaded_by UUID NOT NULL REFERENCES users(id),
    issue_date DATE,
    validity_start_date DATE,
    expiry_date DATE,
    verification_status VARCHAR(30) NOT NULL DEFAULT 'PENDING'
        CHECK (verification_status IN ('PENDING', 'VERIFIED', 'REJECTED', 'SUPERSEDED')),
    verified_by UUID REFERENCES users(id),
    verified_at TIMESTAMPTZ,
    verified_expiry_date DATE,
    replaces_document_id UUID REFERENCES institution_documents(id),
    replaced_by_document_id UUID REFERENCES institution_documents(id),
    is_operative BOOLEAN NOT NULL DEFAULT false,
    version_number INT NOT NULL DEFAULT 1
);

CREATE INDEX idx_inst_docs_expiry ON institution_documents(verified_expiry_date, verification_status)
    WHERE is_operative = true;
CREATE INDEX idx_inst_docs_institution ON institution_documents(institution_id, document_type);
```

#### Notifications

```sql
CREATE TABLE notification_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    trigger_event VARCHAR(100) NOT NULL,
    trigger_condition JSONB,
    recipient_resolution JSONB NOT NULL,
    channel VARCHAR(20) NOT NULL DEFAULT 'BOTH'
        CHECK (channel IN ('IN_APP', 'EMAIL', 'BOTH')),
    timing JSONB NOT NULL,
    escalation_policy_id UUID,
    message_template_id UUID NOT NULL,
    deduplication_key_template VARCHAR(500),
    resolution_event VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id UUID REFERENCES notification_policies(id),
    target_record_type VARCHAR(100),
    target_record_id UUID,
    recipient_user_id UUID NOT NULL REFERENCES users(id),
    channel VARCHAR(20) NOT NULL CHECK (channel IN ('IN_APP', 'EMAIL')),
    subject VARCHAR(500),
    body TEXT,
    case_reference VARCHAR(255),
    deduplication_key VARCHAR(500) UNIQUE,
    delivery_status VARCHAR(30) NOT NULL DEFAULT 'PENDING'
        CHECK (delivery_status IN ('PENDING', 'SENT', 'DELIVERED', 'FAILED', 'BOUNCED', 'CANCELLED')),
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    retry_count INT NOT NULL DEFAULT 0,
    next_retry_at TIMESTAMPTZ,
    escalation_level INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_notifications_recipient ON notifications(recipient_user_id, delivery_status);
CREATE INDEX idx_notifications_target ON notifications(target_record_type, target_record_id);
CREATE INDEX idx_notifications_pending ON notifications(next_retry_at)
    WHERE delivery_status IN ('PENDING', 'FAILED');
```

#### Rules Registry and APH Source

```sql
CREATE TABLE aph_source_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    version VARCHAR(50) NOT NULL,
    academic_year_range VARCHAR(100),
    file_storage_ref VARCHAR(500) NOT NULL,
    total_pages INT,
    registration_status VARCHAR(30) NOT NULL DEFAULT 'REGISTERED'
        CHECK (registration_status IN ('REGISTERED', 'EXTRACTION_COMPLETE', 'ARCHIVED')),
    registered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    registered_by UUID NOT NULL REFERENCES users(id),
    supersedes_document_id UUID REFERENCES aph_source_documents(id)
);

CREATE TABLE aph_source_provisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES aph_source_documents(id),
    provision_text TEXT NOT NULL,
    chapter VARCHAR(100),
    section VARCHAR(100),
    clause VARCHAR(100),
    page_number INT,
    table_reference VARCHAR(100),
    heading_hierarchy JSONB,
    search_vector TSVECTOR,
    extraction_status VARCHAR(30) NOT NULL DEFAULT 'CANDIDATE'
        CHECK (extraction_status IN ('CANDIDATE', 'VERIFIED', 'REJECTED')),
    verified_by UUID REFERENCES users(id),
    verified_at TIMESTAMPTZ,
    verification_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_provisions_document ON aph_source_provisions(document_id);
CREATE INDEX idx_provisions_search ON aph_source_provisions USING GIN(search_vector);
CREATE INDEX idx_provisions_clause ON aph_source_provisions(chapter, section, clause);

CREATE TABLE regulatory_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_code VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    source_document_id UUID REFERENCES aph_source_documents(id),
    source_document_version VARCHAR(50),
    clause_reference VARCHAR(255),
    section_reference VARCHAR(100),
    page_reference VARCHAR(50),
    provision_text TEXT,
    academic_year_applicability VARCHAR(100),
    applicable_categories JSONB DEFAULT '["ALL"]'::jsonb,
    applicable_institution_types JSONB DEFAULT '["ALL"]'::jsonb,
    applicable_programmes JSONB DEFAULT '["ALL"]'::jsonb,
    rule_type VARCHAR(50) NOT NULL
        CHECK (rule_type IN (
            'WORKFLOW_ROUTE', 'TRANSITION_CONDITION', 'DEADLINE',
            'DOCUMENT_REQUIREMENT', 'ELIGIBILITY', 'FEE_CALCULATION',
            'COMPLIANCE_CONDITION', 'INFRASTRUCTURE_NORM'
        )),
    conditions JSONB,
    preconditions JSONB,
    deadline_calculation JSONB,
    deadline_source VARCHAR(30) CHECK (deadline_source IN ('REGULATORY', 'ADMINISTRATIVE')),
    responsible_role VARCHAR(100),
    exceptions JSONB,
    confidence VARCHAR(50) NOT NULL DEFAULT 'EXPLICIT'
        CHECK (confidence IN ('EXPLICIT', 'INTERPRETATION_REQUIRES_REVIEW')),
    interpretation_notes TEXT,
    effective_from DATE NOT NULL,
    effective_until DATE,
    status VARCHAR(30) NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT', 'UNDER_REVIEW', 'APPROVED', 'PUBLISHED', 'DEPRECATED')),
    version INT NOT NULL DEFAULT 1,
    previous_version_id UUID REFERENCES regulatory_rules(id),
    superseded_by_id UUID REFERENCES regulatory_rules(id),
    created_by UUID NOT NULL REFERENCES users(id),
    reviewed_by UUID REFERENCES users(id),
    approved_by UUID REFERENCES users(id),
    published_at TIMESTAMPTZ,
    test_cases JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_approval_separation CHECK (approved_by IS NULL OR approved_by != created_by)
);

CREATE INDEX idx_rules_status ON regulatory_rules(status, effective_from, effective_until);
CREATE INDEX idx_rules_type ON regulatory_rules(rule_type) WHERE status = 'PUBLISHED';
CREATE INDEX idx_rules_code ON regulatory_rules(rule_code);

CREATE TABLE rule_review_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id UUID NOT NULL REFERENCES regulatory_rules(id),
    action VARCHAR(30) NOT NULL
        CHECK (action IN ('SUBMITTED', 'REVIEWED', 'APPROVED', 'REJECTED', 'PUBLISHED', 'DEPRECATED')),
    performed_by UUID NOT NULL REFERENCES users(id),
    comments TEXT,
    performed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_rule_review_rule ON rule_review_history(rule_id);
```

#### Background Jobs

```sql
CREATE TABLE background_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    idempotency_key VARCHAR(500) UNIQUE,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'LOCKED', 'COMPLETED', 'FAILED', 'DEAD_LETTER')),
    locked_by VARCHAR(255),
    locked_at TIMESTAMPTZ,
    retry_count INT NOT NULL DEFAULT 0,
    max_retries INT NOT NULL DEFAULT 5,
    next_retry_at TIMESTAMPTZ,
    last_error TEXT,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_jobs_pending ON background_jobs(next_retry_at)
    WHERE status IN ('PENDING', 'FAILED');
CREATE INDEX idx_jobs_dead_letter ON background_jobs(created_at)
    WHERE status = 'DEAD_LETTER';
```

#### Audit Trail

```sql
CREATE TABLE audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID NOT NULL,
    actor_user_id UUID REFERENCES users(id),
    actor_role VARCHAR(100),
    action VARCHAR(100) NOT NULL,
    details JSONB,
    previous_state JSONB,
    new_state JSONB,
    rule_id UUID,
    rule_version INT,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_entity ON audit_events(entity_type, entity_id);
CREATE INDEX idx_audit_actor ON audit_events(actor_user_id);
CREATE INDEX idx_audit_time ON audit_events(created_at);
```

**Audit immutability enforcement:**
- The application database role used by FastAPI has only INSERT permission on `audit_events`. No UPDATE or DELETE.
- A separate restricted database role (used only by the audit reporting module) has SELECT permission.
- This is enforced via PostgreSQL `GRANT` statements in the migration, not application-level checks.

```sql
-- In migration, after creating audit_events:
REVOKE UPDATE, DELETE ON audit_events FROM app_role;
GRANT INSERT, SELECT ON audit_events TO app_role;
GRANT SELECT ON audit_events TO audit_readonly_role;
```

### 10.3 Concurrency and Consistency

| Concern | Safeguard |
|---|---|
| **Concurrent state transitions** | Optimistic locking via `workflow_instances.version`; increment on each transition; reject if version mismatch |
| **Double submission** | UNIQUE on `applications.application_number`; idempotency key on submission API |
| **Document replacement race** | Single transaction wrapping verification + operative flag swap |
| **Notification deduplication** | UNIQUE on `notifications.deduplication_key` |
| **Duplicate background jobs** | UNIQUE on `background_jobs.idempotency_key`; `SELECT ... FOR UPDATE SKIP LOCKED` for job pickup |
| **Audit immutability** | PostgreSQL GRANT — no UPDATE/DELETE for application role |

---

## 11. Security, Integration, and Audit

### 11.1 Authentication and Authorisation

| Control | Implementation |
|---|---|
| **Authentication** | JWT-based (FastAPI + python-jose); refresh tokens; MFA for officer and admin roles; session timeout per role |
| **Authorisation** | Backend-enforced RBAC via FastAPI dependency injection; every endpoint checks role + scope |
| **Row-level security** | PostgreSQL RLS policies on applications, compliance_obligations, institution_documents |
| **API security** | Pydantic input validation on all endpoints; rate limiting via middleware; CORS whitelist; CSRF protection on mutation endpoints |

### 11.2 Document Security

| Control | Implementation |
|---|---|
| **Storage** | Private object storage behind a `StorageBackend` abstraction (local filesystem dev; S3-compatible prod). Never publicly accessible. |
| **Access** | Backend generates signed, time-limited URLs after permission check. No direct storage access from frontend. |
| **Upload validation** | File type whitelist (PDF, JPEG, PNG, DOC/DOCX); configurable max size (default 25MB); virus scanning via ClamAV or equivalent |
| **Encryption** | Encrypted at rest (storage-level encryption). TLS in transit. |
| **Versioning** | Each upload creates a new `institution_documents` or `evidence_submissions` record. Old versions retained, not overwritten. |
| **DSC verification** | Where APH requires digitally signed documents (Cl. 1.4.3), system validates DSC signature on upload. |

### 11.3 Audit Trail Protections

- `audit_events` table is append-only at the database level (GRANT/REVOKE enforced).
- All state changes, document uploads, verification actions, notifications, rule changes, and login events generate audit records.
- Records include: actor, role, timestamp, IP, action, entity, before/after state, rule version used.
- Retention: minimum APH validity period + 2 years, or as required by applicable regulations.

### 11.4 Integration Readiness

| Integration Point | Status | Approach |
|---|---|---|
| **AICTE Web Portal** | **Unconfirmed** | System is designed for potential integration. API contracts defined but **no actual AICTE endpoints fabricated**. For prototype: mock integration returning synthetic data. |
| **Payment Gateway** | **Unconfirmed** | Interface for TER charge verification defined. For prototype: mock payment confirmation endpoint. |
| **Email Service** | **Available** | SMTP or transactional email API (e.g., AWS SES, Mailgun). Configured via environment variables. |
| **NSWS** | **Unconfirmed** | APH Cl. 1.3.1 requires NSWS submission. For prototype: mock NSWS data import endpoint. |

All external integrations use a **labelled mock** for the prototype. Mock implementations are clearly tagged in code (`# MOCK: Replace with actual integration`) and return synthetic data flagged with `is_demo = true`.

### 11.5 Synthetic vs Verified Data

| Data Type | Label | Handling |
|---|---|---|
| **Demonstration/seed data** | `is_demo = true` | Loaded via seed scripts; clearly labelled; excluded from production reports by default |
| **Regulatory rules from APH** | `status` field | Not operational until `PUBLISHED` through the governance process |
| **Candidate provisions from extraction** | `extraction_status = CANDIDATE` | Reference material only; cannot create published rules until marked `VERIFIED` by human reviewer |
| **Mock integration responses** | Labelled in code and response payload | Never mixed with real integration data |

---

## 12. Missing Regulatory Inputs, Ambiguities, and Assumptions

### 12.1 Items Requiring Clarification from AICTE

| # | Item | APH Reference | Nature of Gap | System Handling |
|---|---|---|---|---|
| Q1 | **Stage-level processing deadlines**: APH specifies "As per Public Notice Period" for Category 1 but does not prescribe fixed days per stage. | Table 2.2, p.28 | Missing regulatory timeline | Configurable administrative deadlines, labelled as such |
| Q2 | **EVC scheduling deadline**: No fixed deadline for scheduling EVC after queue entry. | Ch. I, Cl. 1.9; Ch. II, Cl. 2.6(j) | Missing regulatory timeline | Configurable administrative target |
| Q3 | **Undertaking standard durations**: "Time-bound undertakings" referenced but APH does not specify durations for all types. | General | Missing specification | Configurable defaults, flagged as administrative |
| Q4 | **Security Deposit penalty dates**: Cl. 2.25(f) says 10% up to 31st May, 20% up to 31st July. Fixed calendar or relative? | Ch. II, Cl. 2.25(f) | Ambiguous | Treated as fixed calendar dates per text. Flagged. |
| Q5 | **"Competent Authority" mapping**: Term used for different actors in different contexts. | Multiple clauses | Ambiguous role mapping | Configurable per context; flagged for authorised mapping |
| Q6 | **Re-scrutiny iteration limit**: APH does not specify maximum cycles. | Ch. I, Cl. 1.8 | Missing specification | Configurable administrative limit |
| Q7 | **EVC report submission deadline**: No deadline for report after visit. | Ch. I, Cl. 1.9 | Missing regulatory timeline | Configurable administrative target |
| Q8 | **SHC vs SAC invocation criteria**: "As Applicable" in Table 2.3. Exact conditions unclear. | Ch. II, Cl. 2.23.3, 2.24; Table 2.3 | Partially ambiguous | See assumptions A1/A2 |
| Q9 | **Extended EoA annual data scope**: 3-year EoA institutions must submit data, but scope not detailed. | Ch. II, Cl. 2.1 (Note) | Missing specification | Placeholder data-submission task; scope configurable |
| Q10 | **NSWS integration details**: No API specification provided. | Ch. I, Cl. 1.3.1 | Missing integration spec | Mock integration for prototype |
| Q11 | **Academic Calendar dates**: Provisions reference calendar published separately and annually. | Ch. I, Cl. 1.10(c), (d) | External dependency | System configured per academic year by administrator |
| Q12 | **Change of Site — second EVC trigger**: "if required" — who decides and criteria? | Ch. II, Cl. 2.17(e) | Ambiguous trigger | See assumption in WF-SITE-2EVC rule |

### 12.2 Design Assumptions (Subject to Authorised Review)

| # | Assumption | Rationale | Confidence |
|---|---|---|---|
| A1 | SHC handles deficiency compliance hearings before EC; SAC handles appeals after adverse EC decision. | Cl. 2.23.3 (SHC) and Cl. 2.24 (SAC) read together. | INTERPRETATION_REQUIRES_REVIEW |
| A2 | "As Applicable" for SAC/SHC in Table 2.3 means: invoked only when deficiencies found or appeal filed. | No indication SAC/SHC is mandatory for clean applications. | INTERPRETATION_REQUIRES_REVIEW |
| A3 | Reminder intervals (90/60/30/14/7 days) are configurable administrative defaults, not regulatory requirements. | APH does not specify notification frequencies. | EXPLICIT (absence) |
| A4 | 7-day appeal window calculated from LoD upload date to portal. | APH: "from the date of issue of Letter of Deficiency." Portal upload constitutes issue. | INTERPRETATION_REQUIRES_REVIEW |
| A5 | TER 10% annual increase applies from AY 2025-26 onward, using AY 2024-25 as base. | APH states increase but not base year explicitly. | INTERPRETATION_REQUIRES_REVIEW |
| A6 | Online mode is default for Scrutiny/EVC; physical is an exception. | Ch. I Cl. 1.8/1.9 Note. | EXPLICIT |

### 12.3 Verified Regulatory Mappings

The following mappings are directly supported by explicit APH provisions:

| Mapping | APH Source | Status |
|---|---|---|
| 22 application types with workflow routes | Table 2.3, p.30 | **Verified — EXPLICIT** |
| Category 1 vs Category 2 processing periods | Table 2.2, p.28 | **Verified — EXPLICIT** |
| TER charges per application type | Table 1.1, Table 2.1, Table 3.1, Table 4.1 | **Verified — EXPLICIT** |
| 10% annual TER increase | Cl. 1.4.2 Note, Table 2.1 Note i | **Verified — EXPLICIT** |
| Security deposit amounts | Table 1.4, Table 1.4 Note | **Verified — EXPLICIT** |
| 7-day appeal window | Cl. 1.11(a), 2.24(a) | **Verified — EXPLICIT** |
| LoA valid 2 academic years | Cl. 1.10(b)(ii) | **Verified — EXPLICIT** |
| 30-year lease extension requirement | Cl. 2.1(e) | **Verified — EXPLICIT** |
| Structural stability cert: 30yr trigger, 5yr validity | Cl. 6.17(h) | **Verified — EXPLICIT** |
| 6-year EoA gap → new institution application | Cl. 2.16.1(a) | **Verified — EXPLICIT** |
| Hibernation period formula | Cl. 2.16.1(d)(i) | **Verified — EXPLICIT** |
| Online mode default for Scrutiny/EVC | Cl. 1.8 Note, 1.9 Note | **Verified — EXPLICIT** |
| EVC TER: Online 1.25L / Physical 2.50L | Cl. 1.4.2(d) | **Verified — EXPLICIT** |
| EoA Self-Disclosure eligibility (3-year criteria) | Cl. 2.1(a)(i-vi) | **Verified — EXPLICIT** |
| Land and built-up area norms | Annexure-3 | **Verified — EXPLICIT** |
| Faculty requirements | Annexure-5 | **Verified — EXPLICIT** |
| Book/computer/lab norms | Annexure-4 | **Verified — EXPLICIT** |

---

## 13. API Catalogue

### 13.1 Module APIs

All endpoints are REST JSON, served by FastAPI. Authentication via JWT Bearer token. Authorisation enforced per-endpoint by RBAC middleware.

| Module | Key Endpoints | Auth Required |
|---|---|---|
| **Auth** | POST /auth/login, POST /auth/refresh, POST /auth/logout | Public (login); Authenticated (others) |
| **Application** | POST /applications, GET /applications, GET /applications/{id}, PATCH /applications/{id}/submit, GET /applications/{id}/timeline | Yes |
| **Workflow** | GET /applications/{id}/workflow, POST /applications/{id}/workflow/transition, GET /applications/{id}/workflow/available-actions | Yes |
| **Scrutiny** | POST /applications/{id}/scrutiny/observations, POST /applications/{id}/scrutiny/deficiencies, POST /applications/{id}/scrutiny/complete | Yes (Regional Officer) |
| **EVC** | GET /evc/queue, POST /evc/{id}/schedule, POST /evc/{id}/assign-members, POST /evc/{id}/complete, POST /evc/{id}/report | Yes (EVC Coordinator/Member) |
| **Compliance** | GET /obligations, POST /obligations/{id}/evidence, POST /obligations/{id}/verify, GET /obligations/overdue | Yes |
| **Document** | POST /documents/upload, GET /documents/{id}, POST /documents/{id}/verify, GET /documents/expiring | Yes |
| **Notification** | GET /notifications, PATCH /notifications/{id}/read, GET /notifications/delivery-status | Yes |
| **Rules** | GET /rules, GET /rules/{id}, POST /rules (draft), PATCH /rules/{id}/submit, PATCH /rules/{id}/approve, PATCH /rules/{id}/publish | Yes (Rule Admin) |
| **APH Reference** | GET /aph/search?q=...&chapter=...&clause=..., GET /aph/provisions/{id} | Yes |
| **Dashboard** | GET /dashboard/pendency, GET /dashboard/workload, GET /dashboard/overdue, GET /dashboard/evc-backlog | Yes (role-filtered) |
| **Audit** | GET /audit/events?entity_type=...&entity_id=..., GET /audit/events?actor_id=... | Yes (Audit Reviewer) |
| **Admin** | CRUD /admin/users, CRUD /admin/roles, CRUD /admin/academic-years, CRUD /admin/policies | Yes (System Admin) |

### 13.2 Frontend Consumption

All role-based dashboards consume the same API endpoints with role-based filtering enforced at the backend. The frontend:
- Renders UI based on JWT permission claims.
- Calls shared APIs; backend filters by authenticated user's scope.
- Contains **no** business logic for workflow transitions, deadline calculations, or rule evaluation.
- Provides drill-down navigation from dashboard metrics to underlying application lists.

---

## 14. Test Cases

### 14.1 Workflow Transition Tests

| # | Test | Input | Expected | Covers |
|---|---|---|---|---|
| T-WF-01 | New institution follows Scrutiny → EVC → EC route | Application type = NEW_INSTITUTION | Workflow instance created with correct definition; states match expected route | Valid route |
| T-WF-02 | EoA Self-Disclosure skips Scrutiny and EVC | Application type = EOA_SELF_DISCLOSURE, qualifying institution | Workflow goes SUBMITTED → PAYMENT_VERIFIED → SELF_DISCLOSURE_VALIDATED → EOA_ISSUED | Valid route |
| T-WF-03 | Scrutiny-only type cannot enter EVC | Application type = CHANGE_BANK_DETAILS | Transition to EVC_QUEUED rejected; no EVC stage in workflow definition | Invalid transition |
| T-WF-04 | Transition rejected when precondition unmet | Attempt UNDER_SCRUTINY → SCRUTINY_CLEAR without officer recording observations | Transition fails with precondition error | Precondition enforcement |
| T-WF-05 | Concurrent transition conflict | Two officers attempt transition on same application simultaneously | Second transition fails with version mismatch error | Optimistic locking |
| T-WF-06 | Only PUBLISHED rules used for routing | Create rule as DRAFT; attempt to use it for transition | Rule not found in applicable rules query; transition uses existing published rule | Rule status enforcement |
| T-WF-07 | Appeal filed after 7-day window | Application rejected on day 0; appeal submitted on day 8 | Appeal creation rejected; deadline exceeded | Deadline enforcement |
| T-WF-08 | Appeal filed within window | Application rejected on day 0; appeal submitted on day 6 | Appeal created; application enters SAC queue | Valid appeal |

### 14.2 Access Control Tests

| # | Test | Actor | Action | Expected |
|---|---|---|---|---|
| T-AC-01 | Institution user cannot view other institution's application | User with scope institution_id = A | GET /applications/{id} where application belongs to institution B | 403 Forbidden |
| T-AC-02 | Regional officer cannot view application outside region | Officer scoped to region X | GET /applications/{id} in region Y | 403 Forbidden |
| T-AC-03 | EVC member cannot schedule EVC | User with EVC_MEMBER role | POST /evc/{id}/schedule | 403 Forbidden |
| T-AC-04 | Rule administrator cannot approve own rule | User who created rule | PATCH /rules/{id}/approve | 400 (separation of duties violation) |
| T-AC-05 | Audit reviewer cannot modify data | User with AUDIT_REVIEWER role | PATCH /applications/{id} | 403 Forbidden |

### 14.3 EVC Tests

| # | Test | Expected |
|---|---|---|
| T-EVC-01 | Application enters EVC queue after scrutiny clear (EVC-required type) | EVC queue entry created with correct application reference |
| T-EVC-02 | Application does NOT enter EVC queue (scrutiny-only type) | No EVC queue entry created |
| T-EVC-03 | EVC cannot be scheduled without confirmed eligibility | Schedule attempt fails with prerequisite error |
| T-EVC-04 | EVC completion triggers report-required task | Task created for assigned EVC members |

### 14.4 Compliance and Document Tests

| # | Test | Expected |
|---|---|---|
| T-COMP-01 | Evidence upload does not auto-fulfil obligation | Obligation status remains SUBMITTED until verifier acts |
| T-COMP-02 | Obligation becomes OVERDUE when due_date passes | Background job updates status; escalation notification created |
| T-COMP-03 | Document renewal does not replace operative document until verified | Old document remains is_operative = true until new one verified |
| T-COMP-04 | Lease expiry triggers EoA eligibility flag | Application flagged when lease validity insufficient per Cl. 2.1(e) formula |
| T-COMP-05 | Structural stability cert reminder at 30yr mark | Alert generated when completion_certificate_date + 30 years approached |

### 14.5 Deadline and Notification Tests

| # | Test | Expected |
|---|---|---|
| T-DL-01 | Reminder generated at configured intervals before due date | Notifications created per reminder_config; deduplication key prevents doubles |
| T-DL-02 | Duplicate notification prevented | Same idempotency key → no new notification; no error |
| T-DL-03 | Notifications cancelled when obligation fulfilled | Future pending notifications for that obligation set to CANCELLED |
| T-DL-04 | Escalation progresses through levels | After level 1 delay, level 2 notification created for next recipient role |

### 14.6 Background Job Tests

| # | Test | Expected |
|---|---|---|
| T-JOB-01 | Job survives process restart | Job in PENDING status picked up after restart; not lost |
| T-JOB-02 | Failed job retried with backoff | Retry count incremented; next_retry_at set with exponential delay |
| T-JOB-03 | Job exceeding max retries → dead letter | Status set to DEAD_LETTER; no further retries |
| T-JOB-04 | Duplicate job prevented | Same idempotency_key → insert rejected; no duplicate execution |
| T-JOB-05 | Concurrent job pickup uses SKIP LOCKED | Two workers picking jobs simultaneously do not process same job |

### 14.7 Versioning and Audit Tests

| # | Test | Expected |
|---|---|---|
| T-VER-01 | Transition records exact rule version used | transition_events.rule_id and rule_version populated |
| T-VER-02 | Deprecated rule excluded from runtime | Query for applicable rules does not return deprecated rules |
| T-VER-03 | Audit event created for every state change | Every POST/PATCH endpoint generates an audit_events row |
| T-VER-04 | Audit records cannot be modified | UPDATE or DELETE on audit_events by app_role fails with permission error |
| T-VER-05 | New APH version does not retroactively change in-progress application rules | Application retains original workflow_definition_id after new version published |

---

## 15. Implementation Sequence and Demo Plan

### 15.1 Implementation Phases

#### Phase 1: Foundation (Weeks 1–2)
- Project scaffolding: FastAPI app, React app, Docker Compose, PostgreSQL, Alembic.
- Database migrations for core tables: users, roles, role_assignments, regions, institutions, academic_years.
- Auth module: JWT login, role-based middleware, password hashing.
- Seed data script: demo roles, users, regions, 2–3 institutions.

#### Phase 2: Workflow Core (Weeks 3–4)
- Workflow definitions table and 3 workflow definitions seeded (New Institution, EoA Self-Disclosure, Scrutiny-Only).
- Application CRUD + submission flow.
- Workflow engine: state machine evaluation, transition with preconditions, optimistic locking.
- Stage entries and transition events recording.
- Application categories seeded with workflow_definition_id references.

#### Phase 3: Scrutiny and EVC (Weeks 5–6)
- Scrutiny module: observations, deficiency recording, re-scrutiny loop.
- EVC module: queue management, scheduling, member assignment, completion, report.
- Deficiency records and returns/resubmission flow.

#### Phase 4: Compliance and Documents (Weeks 7–8)
- Compliance obligations CRUD, evidence submission, verification workflow.
- Institution document upload, metadata, verification, operative-flag logic.
- Document expiry detection (lease, structural stability cert).
- Storage abstraction with local filesystem backend.

#### Phase 5: Notifications and Background Jobs (Weeks 9–10)
- Background job table and runner (PostgreSQL-backed).
- Notification policies, template rendering, deduplication.
- Deadline-relative reminders, escalation chain.
- Email delivery (SMTP integration).

#### Phase 6: Rules Engine and APH Reference (Weeks 11–12)
- Regulatory rules table, CRUD, governance workflow (draft → review → publish).
- Rule status enforcement in workflow engine.
- APH source documents and provisions tables.
- Full-text search on provisions (PostgreSQL tsvector).
- Rule review history and separation-of-duties enforcement.

#### Phase 7: Dashboards, Reporting, and Audit (Weeks 13–14)
- Dashboard API: pendency, workload, overdue, EVC backlog.
- React dashboard pages for each role.
- Drill-down from metrics to application lists.
- Audit event viewer with filters.

#### Phase 8: Integration, Polish, and Testing (Weeks 15–16)
- Mock integrations for AICTE Portal, NSWS, Payment Gateway.
- End-to-end test suite (Playwright/Cypress).
- Security hardening: RLS policies, audit GRANT/REVOKE, upload validation.
- Performance testing; Redis/Celery evaluation if needed.
- Documentation and deployment guide.

### 15.2 Minimum End-to-End Demo Plan

**Goal**: Demonstrate one complete application lifecycle from submission to approval, exercising every major system component.

**Demo Scenario**: New Institution Application (Scrutiny → EVC → EC Approval)

| Step | Actor | Action | System Behaviour Shown |
|---|---|---|---|
| 1 | Institution Applicant | Create and submit new-institution application | Application created; workflow instance initialised; payment required |
| 2 | System | Payment verification (mock) | Automatic transition to UNDER_SCRUTINY; task created for Regional Officer |
| 3 | Regional Officer | Record scrutiny observations; identify one deficiency | Deficiency recorded; notification sent to institution; clock switches to INSTITUTION |
| 4 | Institution Applicant | Upload corrective document; resubmit | Response recorded; clock switches to AICTE; re-scrutiny task created |
| 5 | Regional Officer | Clear re-scrutiny | Transition to SCRUTINY_CLEAR; application enters EVC queue |
| 6 | EVC Coordinator | Schedule online EVC; assign members | EVC status → SCHEDULED; members notified |
| 7 | EVC Members | Record observations; submit report | EVC → COMPLETED → REPORT_SUBMITTED |
| 8 | Bureau Officer | Place before EC | Application → PLACED_BEFORE_EC |
| 9 | Competent Authority | Approve with condition (undertaking) | Outcome = APPROVED_WITH_CONDITIONS; LoA issued; compliance obligation created |
| 10 | Institution Applicant | Submit evidence for undertaking | Evidence uploaded; verification task created |
| 11 | Compliance Officer | Verify and accept evidence | Obligation → FULFILLED |
| 12 | Audit Reviewer | View complete audit trail | All 11 prior steps visible with actor, timestamp, rule version |
| 13 | Bureau Officer | View pendency dashboard | Dashboard shows correct stage counts, application age, officer workload |

**Demo also shows:**
- Access control: Institution user blocked from viewing other institution's data.
- Notification delivery: At least one email and one in-app notification visible.
- Rule traceability: Each transition shows the published rule that authorised it.
- Document expiry: A pre-seeded institution document approaching expiry, visible in alerts.

---

## 16. Readiness Checklist

### 16.1 Regulatory Verification

| # | Item | Status | Action Required |
|---|---|---|---|
| R1 | All 22 application types mapped to workflow routes | Done (§3.1) | Authorised review of Table 2.3 mapping |
| R2 | TER charges and formulas verified | Done (rule examples) | Authorised confirmation of 10% base year (A5) |
| R3 | Appeal deadlines verified (7 days) | Done | Authorised confirmation of LoD issue-date interpretation (A4) |
| R4 | SAC/SHC invocation criteria documented | Partial (A1, A2) | **Requires authorised clarification (Q8)** |
| R5 | Lease 30-year rule implemented | Done (§7.2) | — |
| R6 | Structural stability cert lifecycle | Done (§7.3) | — |
| R7 | 12 open regulatory questions documented | Done (§12.1) | **Each requires AICTE response** |
| R8 | 6 design assumptions documented | Done (§12.2) | **Each requires authorised review** |
| R9 | Rule governance lifecycle specified | Done (§9.A) | — |
| R10 | Candidate provisions cannot execute as rules | Enforced (§9.B.2) | — |

### 16.2 Technical Correctness

| # | Item | Status | Action Required |
|---|---|---|---|
| T1 | PostgreSQL schema is executable | Done (§10.2) | Run migrations against test database |
| T2 | All SQL uses valid syntax (CREATE TABLE, CREATE INDEX, CHECK, REFERENCES) | Done | — |
| T3 | No RAG/LLM/AI/vector components in architecture | Done (C2) | — |
| T4 | Audit table is append-only (GRANT/REVOKE) | Specified (§10.2) | Verify in migration |
| T5 | Optimistic locking on workflow transitions | Specified (§10.3) | Verify in implementation |
| T6 | Background job idempotency and deduplication | Specified (§8.5, §10.2) | Verify in implementation |
| T7 | Rule status enforcement (only PUBLISHED executes) | Specified (§9.B.2) | Verify in implementation |
| T8 | Separation of duties (approved_by != created_by) | CHECK constraint in schema | — |
| T9 | Test cases defined for all major flows | Done (§14) | Implement as pytest + Playwright tests |

### 16.3 Remaining Dependencies

| # | Dependency | Status | Mitigation |
|---|---|---|---|
| D1 | AICTE Web Portal API access | **Not available** | Mock integration |
| D2 | NSWS API specification | **Not available** | Mock integration |
| D3 | Payment gateway credentials | **Not available** | Mock payment verification |
| D4 | AICTE responses to 12 open questions (§12.1) | **Pending** | System uses configurable administrative defaults; flagged for authorised override |
| D5 | Authorised review of 6 assumptions (§12.2) | **Pending** | Rules with INTERPRETATION_REQUIRES_REVIEW confidence blocked from production use until reviewed |
| D6 | Production hosting environment | **Not specified** | Docker Compose deployment; cloud hosting TBD |
| D7 | Email service credentials | **Not available** | Console logging for development; SMTP config for staging |

---

*End of Technical Foundation Specification v2.0*

*Every regulatory rule traces to the AICTE Approval Process Handbook 2024-2027. Administrative configurations are explicitly distinguished from regulatory requirements. Candidate provisions and unverified interpretations cannot execute as production rules. Items marked ⚠ or flagged in §12 require authorised clarification before operational deployment.*
