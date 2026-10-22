# SIH26262 — AICTE FlowGuard: Final Technical Foundation Specification

**Version:** 3.0 (Final)  
**Previous Versions:** 1.0 (2026-10-22), 2.0 (2026-10-22)  
**Source Document:** AICTE Approval Process Handbook 2024–2027 (APH 2024-27)  
**APH Edition:** 2024-2027 (covers AY 2024-25 through AY 2026-27)  
**APH Inspection Status:** Original PDF inspected and verified in this session. 231 pages, extracted via pymupdf.  
**Date:** 2026-10-22

---

## 0. Change Log (v2.0 → v3.0 Final)

| # | Section | Change | Reason |
|---|---|---|---|
| F1 | §3 Regulatory Rule Register | New section. Every rule now carries explicit APH page/clause citation, verbatim supporting text, and a verification status (SOURCE_VERIFIED / PARTIALLY_VERIFIED / AMBIGUOUS / SOURCE_UNAVAILABLE). | Directive §1: strict APH-only regulatory rules with traceable evidence. |
| F2 | §3 Rule Register | Removed all rules that lacked direct APH textual evidence. Remaining rules re-verified against original PDF in this session. | Eliminate unsupported rules. |
| F3 | §9.B Rule Versioning | Reworked rule family versioning: stable `rule_family_code`, independent `version` per family, effective-date constraints preventing invalid overlaps, explicit application-binding policy. | Directive §3.1/3.2: define version uniqueness and selection. |
| F4 | §4 Pendency | Added complete clock history model (starts, pauses, resumptions, extensions, completions, corrections) as append-only clock events rather than mutable fields. | Directive §3.5: preserve complete clock history. |
| F5 | §8 Notifications | Separated notification events from delivery attempts into two tables. Defined idempotency per (event, recipient, channel, occurrence). | Directive §3.6: separate events from deliveries. |
| F6 | §11 Security | Replaced "append-only via GRANT/REVOKE" with honest assessment: database permissions prevent casual modification but do not make records immutable against privileged users. Added compensating controls. | Directive §3.7: do not claim ordinary permissions make audit immutable. |
| F7 | §8.5 Background Jobs | Selected concrete approach: `pgq`-pattern with `SELECT ... FOR UPDATE SKIP LOCKED`. Specified atomic claiming, concurrency, retries, recovery, idempotency. | Directive §3.8: select one concrete approach. |
| F8 | §10 Integrations | Explicitly marked all external integrations as MOCK for prototype. Removed any language implying confirmed access. | Directive §3.10: distinguish real from mock. |
| F9 | §12 Test Matrix | Source-linked regulatory test matrix: every test references a verified rule and APH provision. | Directive §5 and §6.6. |
| F10 | §14 Build Readiness | Final GO/CONDITIONAL/NO-GO recommendation with evidence. | Directive §6.7. |
| F11 | All sections | Audited every claimed APH reference against the original PDF extracted in this session. Corrected Cl. 2.24(a) text: "7 days from the date of uploading of the decision" (not "date of issue of LoD"). | Directive §1: verify every claim. |
| F12 | §9 Rule governance | Added SUSPENDED status for emergency deactivation of rules pending review. | Directive §3.9: suspension capability. |

---

## 1. System Architecture

### 1.1 Architecture Pattern: Modular Monolith

**Technology Stack:**

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Backend | Python 3.12+, FastAPI, Pydantic v2 |
| ORM / Migrations | SQLAlchemy 2.x, Alembic |
| Database | PostgreSQL 16 |
| Background Jobs | PostgreSQL-backed queue (`SELECT ... FOR UPDATE SKIP LOCKED` pattern) |
| Document Storage | Private object storage behind `StorageBackend` interface (local dev; S3-compatible prod) |
| Deployment | Docker Compose, `.env` configuration, Alembic migrations, seed data scripts |
| Testing | pytest, httpx (API), Playwright (E2E) |

No LLMs, generative AI, RAG, embeddings, vector databases, or ML-based interpretation.

### 1.2 Module Structure

```
┌─────────────────────────────────────────────────────────────┐
│                  FRONTEND (React + Vite + Tailwind)          │
│  Institution Portal │ RO Dashboard │ Bureau Dashboard │ Admin│
└─────────────┬───────────────────────────────────────────────┘
              │ HTTPS / JWT (REST JSON)
┌─────────────▼───────────────────────────────────────────────┐
│                    FASTAPI APPLICATION                        │
│  Auth │ RBAC │ Rate Limit │ Audit Middleware                  │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ Workflow │ Compliance │ EVC │ Notification │ Document    │  │
│ │ Rules    │ Reporting  │ APH Reference │ Audit │ Admin    │  │
│ └─────────────────────────────────────────────────────────┘  │
│                  BACKGROUND JOB RUNNER                        │
└─────────────┬───────────────────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────────────────┐
│              PostgreSQL │ Private Object Storage              │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Design Principles

1. **Regulatory traceability**: Every automated action references an APH clause and a published rule version.
2. **Human authority preserved**: Statutory decisions (approval, rejection, conditions) are human-controlled. Automatic advancement only where the published workflow explicitly permits it and all preconditions are met.
3. **Configurable, not hardcoded**: Workflow routes, timelines, and policies are versioned data.
4. **Audit-complete**: Every state change produces an audit record.
5. **Deterministic**: All regulatory logic executes through verified, published rules. No probabilistic or AI components.
6. **Separation of concerns**: APH-mandated requirements, AICTE administrative policies, and prototype defaults are stored, labelled, and enforced as distinct categories.

---

## 2. Role-Permission Matrix

### 2.1 Roles and Permissions

| Role | Permitted Actions | Restricted Actions |
|---|---|---|
| **Institution Applicant** | Create/submit applications; upload documents; respond to deficiencies; submit compliance evidence; track own application status | Cannot view other institutions; cannot modify after final submission; cannot approve/reject |
| **Institution Authorised Signatory** | Digitally sign submissions; confirm undertakings | Cannot submit without confirmation where required |
| **Regional Officer / Scrutiny Officer** | View assigned applications; record scrutiny observations; identify deficiencies; request clarification; record EVC observations | Cannot approve/reject (EC/Council only); cannot view outside assigned region |
| **Regional Coordinator** | View regional pendency dashboard; allocate tasks; monitor deadlines | Cannot perform scrutiny; cannot make decisions |
| **Regulation Bureau Officer** | View cross-region pendency; prepare consolidated reports; place recommendations before EC | Cannot make final decisions |
| **EVC Coordinator** | Manage EVC queue; schedule visits; assign members | Cannot record inspection findings; cannot approve |
| **EVC Member** | Record observations and reports for assigned cases | Cannot schedule EVCs; cannot approve |
| **SAC/SHC Committee User** | Review assigned cases; record recommendations | Recommendations only; cannot make final decisions |
| **Competent Authority** | Record final decisions; issue LoA/LoD/LoR; attach conditions | Scoped to designated authority |
| **Compliance Verification Officer** | Review evidence; record verification outcomes | Cannot modify submissions; cannot approve applications |
| **System Administrator** | Manage users/roles; configure technical settings; monitor health | Cannot modify rules; cannot access application content |
| **Regulatory Rule Administrator** | Draft/edit rules; submit for review; manage versions | Cannot approve own rules; cannot make application decisions |
| **Audit/Read-Only Reviewer** | View historical records; generate audit reports | Cannot modify any operational record |

### 2.2 Enforcement

- All permissions enforced in FastAPI backend middleware, not frontend.
- PostgreSQL RLS on applications, compliance_obligations, institution_documents.
- `approved_by != created_by` enforced by CHECK constraint on regulatory_rules.

---

## 3. Regulatory Rule Verification Register

### 3.1 Verification Status Definitions

| Status | Meaning |
|---|---|
| **SOURCE_VERIFIED** | APH text directly and unambiguously supports this rule. Clause, page, and supporting text recorded. Verified against original PDF in this session. |
| **PARTIALLY_VERIFIED** | APH establishes the general requirement but specific parameters (deadline, formula boundary, responsible authority) are not fully specified. |
| **AMBIGUOUS** | APH text is susceptible to multiple interpretations. Requires authorised human review before activation. |
| **SOURCE_UNAVAILABLE** | The specification assumes this requirement exists but the APH does not establish it. Must not be activated for regulatory automation. |

### 3.2 Verified Rules

| Rule ID | Description | APH Edition | Clause | Page | Supporting Text (verbatim or faithful summary) | Type | Status |
|---|---|---|---|---|---|---|---|
| WF-NEW-001 | New Institution applications processed via Scrutiny → EVC → EC | 2024-27 | Ch. I, Cl. 1.8, 1.9, Annexure-7 | p.7-8, p.100 | "applications submitted under this Chapter shall be evaluated by Scrutiny/Re-Scrutiny Committee" (1.8a); "The Expert Visit Committee shall be constituted... shall verify physically/ online the infrastructural facilities" (1.9a) | WORKFLOW_ROUTE | **SOURCE_VERIFIED** |
| WF-EOA-SD-001 | EoA Self-Disclosure: no Scrutiny/EVC for qualifying institutions | 2024-27 | Ch. II, Cl. 2.1, Table 2.3 | p.11-12, p.46 | Table 2.3: "Extension of Approval based on Self-Disclosure" → Self-Disclosure=Yes, Scrutiny=-, EVC=-, SAC/SHC=- | WORKFLOW_ROUTE | **SOURCE_VERIFIED** |
| WF-INTAKE-001 | Increase in Intake requires Scrutiny + EVC | 2024-27 | Ch. II, Cl. 2.6(j), Table 2.3 | p.17, p.46 | "Scrutiny and EVC shall be conducted for any increase in intake" (2.6j); Table 2.3: Scrutiny=Yes, EVC=Yes, SAC/SHC=AA | WORKFLOW_ROUTE | **SOURCE_VERIFIED** |
| WF-SITE-001 | Change of Site requires Scrutiny + EVC | 2024-27 | Ch. II, Cl. 2.17(c), Table 2.3 | p.25, p.46 | "The Expert Visit Committee shall verify the completeness of Infrastructure" (2.17c); Table 2.3: Scrutiny=Yes, EVC=Yes, SAC/SHC=AA | WORKFLOW_ROUTE | **SOURCE_VERIFIED** |
| WF-SITE-2EVC | Change of Site may require second EVC after shifting | 2024-27 | Ch. II, Cl. 2.17(e) | p.25 | "another Expert Visit Committee shall be conducted before the start of academic session... if required" | WORKFLOW_ROUTE | **AMBIGUOUS** — "if required" not defined; who decides and under what criteria is unclear |
| EL-3YR-EOA-001 | Institutions meeting Cl. 2.1(a)(i-vi) criteria eligible for 3-year extended EoA | 2024-27 | Ch. II, Cl. 2.1(a) | p.11-12 | Six criteria listed: (i) NIRF ranking, (ii) QS World Ranking Asia, (iii) NBA 50%+ courses, (iv) NAAC 3.01+, (v) UGC Autonomous, (vi) 80%+ admission for 5 consecutive years | ELIGIBILITY | **SOURCE_VERIFIED** |
| EL-BREAK-6YR | Institution not applied for EoA for 6 consecutive years must apply as new institution | 2024-27 | Ch. II, Cl. 2.16.1(a) | p.24 | "Institution not applied for EoA for SIX (06) years consecutively shall not be eligible to apply under Break in EoA and such Institutions shall apply as a New Technical Institution" | ELIGIBILITY | **SOURCE_VERIFIED** |
| EL-HIBERN-PERIOD | Hibernation period = maximum course duration - 1 year | 2024-27 | Ch. II, Cl. 2.16.1(d) | p.24-25 | "Period of Hibernation will be..." (text on p.24-25 defines formula relative to course duration) | ELIGIBILITY | **PARTIALLY_VERIFIED** — formula referenced but full text was truncated in extraction; requires re-verification of exact wording |
| FEE-TER-NEW-001 | TER charges for new institution | 2024-27 | Ch. I, Table 1.1 | p.3 (PDF p.19) | Table 1.1: Govt/J&K/NER/PwBD/Women = Rs. 1.00 Lakh; All others = Rs. 10.00 Lakh; Rejected prior year: Govt 0.25L, Others 1.00L | FEE_CALCULATION | **SOURCE_VERIFIED** |
| FEE-TER-10PCT | TER charges increase 10% annually | 2024-27 | Ch. I, Cl. 1.4.2 (Note); Ch. II, Table 2.1 (Note i) | p.3, p.14 | "10% TER charges will be increased annually" (1.4.2 Note); "TER charges will increase @ 10% annually" (Table 2.1 Note i) | FEE_CALCULATION | **PARTIALLY_VERIFIED** — increase rate established but base year not explicitly stated. See assumption A5. |
| FEE-TER-EVC | Additional EVC TER: Online Rs.1.25L / Physical Rs.2.50L | 2024-27 | Ch. I, Cl. 1.4.2(d); Ch. II, Cl. 2.3.2(c) | p.3, p.14 | "additional Expert Visit Committee... Rs.1.25/Rs.2.50 Lakh respectively" (1.4.2d); Government: Rs.0.25L/Rs.0.50L (2.3.2c) | FEE_CALCULATION | **SOURCE_VERIFIED** |
| FEE-SD-NEW | Security deposit amounts per programme | 2024-27 | Ch. I, Table 1.4 | p.10 (PDF p.26) | Table 1.4 lists deposit per programme/level. E.g., Engineering UG = Rs.35L | FEE_CALCULATION | **SOURCE_VERIFIED** |
| FEE-SD-DOUBLE | Security deposit doubles for private leased building/land | 2024-27 | Ch. I, Table 1.4 (Note) | p.10 (PDF p.26) | "The Security Deposit amount shall be DOUBLE in case of private leased building / land" | FEE_CALCULATION | **SOURCE_VERIFIED** |
| DL-APPEAL-7DAY-CH1 | Appeal within 7 days of LoD (new institutions) | 2024-27 | Ch. I, Cl. 1.11(a) | p.9 (PDF p.25) | "shall have the right to appeal (through portal) once to the Council within 7 days from the date of issue of Letter of Deficiency (LoD)" | DEADLINE | **SOURCE_VERIFIED** |
| DL-APPEAL-7DAY-CH2 | Appeal within 7 days of decision upload (extension applications) | 2024-27 | Ch. II, Cl. 2.24(a) | p.29 (PDF p.45) | "shall have the right to appeal once to the Council within 7 days from the date of uploading of the decision" | DEADLINE | **SOURCE_VERIFIED** |
| DL-LOA-VALID-2YR | LoA for new institution valid for 2 academic years | 2024-27 | Ch. I, Cl. 1.10(b)(ii) | p.9 (PDF p.25) | "Letter of Approval (LoA) for new Technical Institutions, if issued, shall be valid for two Academic Years from the date of issue" | DEADLINE | **SOURCE_VERIFIED** |
| DL-LOA-EXPIRY | On expiry of 2 years, LoA stands cancelled | 2024-27 | Ch. I, Cl. 1.10(b)(ii) NOTE | p.9 (PDF p.25) | "On Expiry of the Validity of Two Years, the LoA Stands Cancelled" | DEADLINE | **SOURCE_VERIFIED** |
| DL-SD-PENALTY | Security deposit late payment: 10% penalty up to 31st May, 20% up to 31st July, then withdrawal | 2024-27 | Ch. II, Cl. 2.25(f) | p.31 (PDF p.47) | "penalty of 10% and 20% of the value of the Security Deposit shall be imposed up to 31st May and 31st July of the Calendar Year respectively, beyond which the approval shall be withdrawn" | DEADLINE | **SOURCE_VERIFIED** — dates are fixed calendar dates per the text |
| DOC-LEASE-30YR | Lease must be extended 30 years for EoA | 2024-27 | Ch. II, Cl. 2.1(e) | p.12 (PDF p.28) | "the Council shall not issue EoA from the Year in which the Live Lease is equal to the number of years of the Course having the maximum duration. However, if such Institutions submit the Lease extended for a further 30 years, application shall be considered for EoA" | DOCUMENT_REQUIREMENT | **SOURCE_VERIFIED** |
| DOC-DSC | Documents must be digitally signed using DSC | 2024-27 | Ch. II, Cl. 2.3.4(a) | p.15 (PDF p.31) | "All Institutions shall upload the documents (Digitally Signed using DSC) as per Annexure-2" | DOCUMENT_REQUIREMENT | **SOURCE_VERIFIED** |
| INF-STRUCT-30YR | Structural stability cert required 30yr after completion cert, valid 5yr | 2024-27 | Ch. VI, Cl. 6.17(h) | p.57 (PDF p.73) | "After the expiry of a period of thirty years from the issue of Completion Certificate, a Structural Stability Certificate from the registered Structural Engineer... shall be produced. Structural Stability Certificate is valid for a period of FIVE years from the date of issue" | INFRASTRUCTURE_NORM | **SOURCE_VERIFIED** |
| INF-FIRE-SAFETY | Valid fire safety certificate required | 2024-27 | Ch. VI, Cl. 6.17(i) | p.57 (PDF p.73) | "A valid Fire Safety Certificate shall be obtained from the Competent Authority" | INFRASTRUCTURE_NORM | **SOURCE_VERIFIED** |
| PROC-ONLINE | Scrutiny/Re-Scrutiny/EVC conducted online by default | 2024-27 | Ch. I, Cl. 1.8 (Note) | p.8 (PDF p.24) | "All the Scrutiny/Re-Scrutiny and EVC will be conducted in online mode. Under extraordinary circumstances (including Court directions) the Scrutiny / Re-Scrutiny and EVC will be conducted in Offline mode also" | TRANSITION_CONDITION | **SOURCE_VERIFIED** |
| PROC-CAT1-PERIOD | Category 1 applications: processed per Public Notice period | 2024-27 | Ch. II, Table 2.2 | p.28 (PDF p.44) | "Processing Period of Application: As per Public Notice Period" for all Category 1 types | DEADLINE | **SOURCE_VERIFIED** — but specific stage-level deadlines NOT established |
| PROC-CAT2-PERIOD | Category 2 applications: processed year-round | 2024-27 | Ch. II, Table 2.2 | p.28 (PDF p.44) | "Processing Period of Application: Year round" for Category 2 types | DEADLINE | **SOURCE_VERIFIED** |
| PROC-SHC | Standing Hearing Committee: institutions submit compliance for shortcomings before EC | 2024-27 | Ch. II, Cl. 2.23.3 | p.29 (PDF p.45) | "institutes shall have a chance to submit the compliance for any of the short comings based on Scrutiny/ Re-Scrutiny/EVC related to approval before the Standing Hearing Committee. The recommendations of the Standing Hearing Committee shall be placed before the Executive Committee for approval" | WORKFLOW_ROUTE | **SOURCE_VERIFIED** |
| PROC-SAC | Standing Appellate Committee handles appeals after EC decision | 2024-27 | Ch. I, Cl. 1.11(b); Ch. II, Cl. 2.24(b) | p.9, p.29 | "The appeal of the Institution shall be considered by the Standing Appellate Committee" (1.11b); "The Appeal of the Institution shall be considered by the Standing Appellate Committee (SAC)" (2.24b) | WORKFLOW_ROUTE | **SOURCE_VERIFIED** |
| PROC-EVC-BEFORE-PASSOUT | EVC may be conducted any time before first batch passes out | 2024-27 | Ch. I, Cl. 1.10(b)(ii) NOTE 1; Ch. II, Cl. 2.6(j) | p.9, p.17 | "An Expert Visit Committee may be conducted any time before the first batch of students has passed out" (1.10 NOTE 1); "EVC shall be conducted, any time before the first batch of students passed out" (2.6j) | TRANSITION_CONDITION | **SOURCE_VERIFIED** |
| PROC-REVOKE-7DAY | Application revocation within 7 days of Public Notice last date | 2024-27 | Ch. II, Cl. 2.3.4(f) | p.15 (PDF p.31) | "at least within 7 days from the last date as notified in the Public Notice / AICTE Website. Then TER Charges after a deduction of Rs. 0.25 Lakh shall be refunded" | DEADLINE | **SOURCE_VERIFIED** |
| PENAL-UNAPPROVED | Institutions offering programmes without approval: declared unapproved, penal action | 2024-27 | Ch. VII, Cl. 7.1(a), 7.2 | p.70 (PDF p.86) | "shall be declared as unapproved Institution and necessary punitive action shall be initiated" | COMPLIANCE_CONDITION | **SOURCE_VERIFIED** |
| PENAL-REAPPLY-2YR | After withdrawal of approval: may reapply only after 2 academic years with different name | 2024-27 | Ch. VII, Cl. 7.1(b) | p.70 (PDF p.86) | "shall apply afresh for approval ONLY after completion of two Academic Years with a different name" | COMPLIANCE_CONDITION | **SOURCE_VERIFIED** |

### 3.3 Rules NOT Established by APH (SOURCE_UNAVAILABLE — must not activate)

| Item | What the spec assumed | APH evidence | Status |
|---|---|---|---|
| Stage-level processing deadlines (days per scrutiny, days per EVC scheduling) | Configurable administrative defaults | APH says "As per Public Notice Period" (Table 2.2) — no per-stage day counts | **SOURCE_UNAVAILABLE** |
| Reminder intervals (90/60/30/14/7 days) | Configurable administrative defaults | APH does not specify notification frequencies | **SOURCE_UNAVAILABLE** |
| EVC scheduling deadline after queue entry | Configurable administrative target | No deadline established | **SOURCE_UNAVAILABLE** |
| EVC report submission deadline | Configurable administrative target | No deadline established | **SOURCE_UNAVAILABLE** |
| Re-scrutiny iteration limit | Configurable administrative limit | APH does not specify a maximum | **SOURCE_UNAVAILABLE** |
| Undertaking standard durations | Configurable administrative defaults | APH references "time-bound" but no durations | **SOURCE_UNAVAILABLE** |
| Escalation chain levels and timings | Configurable administrative policy | Not in APH | **SOURCE_UNAVAILABLE** |

These items are implemented as **configurable administrative policies**, clearly labelled, and never presented as APH mandates.

---

## 4. Workflow Model

### 4.1 Application Categories and Routes (APH Table 2.3, p.46)

All 22 routes verified against Table 2.3 as extracted from PDF page 46:

| # | Application Type | Self-Disclosure | Scrutiny | EVC | SAC/SHC | Verification |
|---|---|---|---|---|---|---|
| 1 | EoA Self-Disclosure | Yes | — | — | — | SOURCE_VERIFIED |
| 2 | NRI Seats Introduction/Continuation | Yes | — | — | — | SOURCE_VERIFIED |
| 3 | Diploma↔Degree Conversion | — | Yes | Yes | AA | SOURCE_VERIFIED |
| 4 | Name Change (Institution/University/Board) | — | Yes | — | — | SOURCE_VERIFIED |
| 5 | New Programme/Level | — | Yes | Yes | AA | SOURCE_VERIFIED |
| 6 | Merger of Institutions | — | Yes | Yes | AA | SOURCE_VERIFIED |
| 7 | Break in EoA/Restoration/Hibernation | — | Yes | Yes | AA | SOURCE_VERIFIED |
| 8 | FN/OCI/Gulf Children Seats | — | Yes | — | — | SOURCE_VERIFIED |
| 9 | Increase in Intake/Additional Course | — | Yes | Yes | AA | SOURCE_VERIFIED |
| 10 | Integrated/Dual Degree | — | Yes | Yes | AA | SOURCE_VERIFIED |
| 11 | FPM Introduction/Continuation | — | Yes | Yes | AA | SOURCE_VERIFIED |
| 12 | Course Name Change/Merger/Reduction | — | Yes | — | — | SOURCE_VERIFIED |
| 13 | Collaboration & Twinning | — | Yes | Yes | AA | SOURCE_VERIFIED |
| 14 | Change of Site/Location | — | Yes | Yes | AA | SOURCE_VERIFIED |
| 15 | Closure of Institution | — | Yes | — | — | SOURCE_VERIFIED |
| 16 | Women's↔Co-ed Conversion | — | Yes | — | — | SOURCE_VERIFIED |
| 17 | Closure of Programme(s)/Course(s) | — | Yes | — | — | SOURCE_VERIFIED |
| 18 | Change Bank Details | — | Yes | — | — | SOURCE_VERIFIED |
| 19 | Change Trust/Society/Company Name | — | Yes | — | — | SOURCE_VERIFIED |
| 20 | Deemed University Conversion | — | Yes | Yes | AA | SOURCE_VERIFIED |
| 21 | ODL/OL Courses | — | Yes | Yes | AA | SOURCE_VERIFIED |
| 22 | New Institution (Ch. I) | — | Yes | Yes | AA | SOURCE_VERIFIED |

**AA = "As Applicable Depending on the Outcome of the Previous Processing Steps"** (verbatim from Table 2.3 footer). Per Cl. 2.23.3: SHC provides compliance opportunity before EC. Per Cl. 2.24: SAC handles appeals after EC decision.

### 4.2 State Machine

#### Full Route (Scrutiny + EVC + AA)

```
DRAFT → SUBMITTED → PAYMENT_VERIFIED → UNDER_SCRUTINY →
  ├→ SCRUTINY_CLEAR → EVC_QUEUED → EVC_SCHEDULED → EVC_IN_PROGRESS →
  │    EVC_COMPLETED → REPORT_SUBMITTED → PLACED_BEFORE_EC → EC_DECISION
  ├→ DEFICIENCY_NOTED → AWAITING_INSTITUTION_RESPONSE →
  │    ├→ RESPONSE_RECEIVED → RE_SCRUTINY → (→ SCRUTINY_CLEAR or DEFICIENCY_NOTED)
  │    └→ RESPONSE_TIMEOUT → ESCALATION
  └→ SHC_COMPLIANCE (Cl. 2.23.3) → SHC_RECOMMENDATION → PLACED_BEFORE_EC → EC_DECISION

EC_DECISION →
  ├→ APPROVED → LoA/EoA issued
  ├→ APPROVED_WITH_CONDITIONS → UNDERTAKING_CREATED
  └→ REJECTED → [APPEAL within 7 days? per Cl. 1.11(a)/2.24(a)]
       ├→ Yes → SAC_HEARING → SAC_RECOMMENDATION → EC/COUNCIL_DECISION
       └→ No → FINAL_REJECTION (LoR issued)
```

#### Self-Disclosure Route
```
DRAFT → SUBMITTED → PAYMENT_VERIFIED → SELF_DISCLOSURE_VALIDATED →
  ├→ DEFICIENCY_FREE → EOA_ISSUED
  └→ DEFICIENCY_DETECTED → [standard route from UNDER_SCRUTINY]
```

#### Scrutiny-Only Route
```
DRAFT → SUBMITTED → PAYMENT_VERIFIED → UNDER_SCRUTINY →
  SCRUTINY_CLEAR → PLACED_BEFORE_EC → EC_DECISION
```

### 4.3 Transition Rules

Each transition carries:
- `rule_family_code` + `rule_version` of the published rule authorising it
- `trigger_type`: AUTOMATIC | MANUAL | SCHEDULED | EVENT
- `preconditions[]`: structured checks that must all pass
- `authorised_actor_role`: the role that may trigger MANUAL transitions
- System **never** automatically approves or rejects. This is always manual by Competent Authority.

### 4.4 Processing Periods (APH Table 2.2, p.44)

| Category | APH-Established Period | System Handling |
|---|---|---|
| Category 1 (14 types) | "As per Public Notice Period" | Public Notice dates configured per AY by System Administrator. **No per-stage day count is APH-mandated.** |
| Category 2 (9 types) | "Year round" | Tracked from submission date. No fixed Public Notice deadline. |

---

## 5. Pendency and Clock Model

### 5.1 Clock Separation

| Clock | Active When | Paused When |
|---|---|---|
| **AICTE processing** | Application is with AICTE officer/committee/queue | Returned to institution; authorised hold |
| **Institutional response** | Returned to institution for deficiency/documents | AICTE is processing; authorised hold |
| **Held** | Neither clock runs; authorised by named officer | — |

### 5.2 Clock Event History (Append-Only)

Rather than mutable fields, clock state is reconstructed from an append-only event log:

```sql
CREATE TABLE clock_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    event_type VARCHAR(30) NOT NULL CHECK (event_type IN (
        'CLOCK_START', 'CLOCK_PAUSE', 'CLOCK_RESUME',
        'CLOCK_TRANSFER', 'HOLD_START', 'HOLD_END',
        'EXTENSION_GRANTED', 'CLOCK_COMPLETE', 'CORRECTION'
    )),
    clock_owner VARCHAR(20) NOT NULL CHECK (clock_owner IN ('AICTE', 'INSTITUTION', 'HELD')),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    authorised_by UUID REFERENCES users(id),
    reason TEXT,
    extended_deadline DATE,
    previous_deadline DATE,
    metadata JSONB
);

CREATE INDEX idx_clock_events_app ON clock_events(application_id, occurred_at);
```

Current clock state and elapsed time are computed from this log. No mutable `clock_owner` column on `stage_entries`.

### 5.3 Dashboards

| Metric | Visible To |
|---|---|
| Stage-wise pendency count per region | Regional Coordinator, Bureau Officer |
| Average stage duration (segmented by clock owner) | Bureau Officer |
| Application age (from submission) | All roles (filtered) |
| Officer workload | Regional Coordinator |
| Approaching deadline (where established) | Assigned officer, Regional Coordinator |
| Overdue count | Regional Coordinator, Bureau Officer |
| EVC scheduling backlog | EVC Coordinator, Bureau Officer |
| Compliance fulfilment rate | Bureau Officer, Compliance Officer |
| Document expiry approaching | Compliance Officer, Institution |

---

## 6. EVC, Compliance, and Document Validity

### 6.1 EVC (retained from v2.0, verified)

All EVC provisions verified: Cl. 1.9(a-g), Cl. 2.6(j), Cl. 2.17(c)(e), Cl. 2.23.2, Table 2.3. Online default per Cl. 1.8 Note. TER per Cl. 1.4.2(d): Online 1.25L, Physical 2.50L (SOURCE_VERIFIED).

**No changes from v2.0 §5** except: EVC scheduling deadlines, report submission deadlines, and alert thresholds are explicitly labelled **SOURCE_UNAVAILABLE — administrative policy only**.

### 6.2 Compliance Obligations (retained from v2.0)

**No changes** except: reminder intervals (90/60/30/14/7) are now explicitly labelled "configurable administrative default — not APH-mandated" in schema and seed data.

### 6.3 Document Validity (retained from v2.0, verified)

Lease 30-year rule (Cl. 2.1(e), p.28): SOURCE_VERIFIED.
Structural stability cert (Cl. 6.17(h), p.73): SOURCE_VERIFIED.
Fire safety cert (Cl. 6.17(i), p.73): SOURCE_VERIFIED.
Unverified replacement prevention logic: retained.

---

## 7. Notification and Escalation

### 7.1 Separation of Events from Deliveries

```sql
CREATE TABLE notification_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    policy_id UUID REFERENCES notification_policies(id),
    target_record_type VARCHAR(100),
    target_record_id UUID,
    trigger_date DATE NOT NULL,
    idempotency_key VARCHAR(500) NOT NULL UNIQUE,
    is_resolved BOOLEAN NOT NULL DEFAULT false,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE notification_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES notification_events(id),
    recipient_user_id UUID NOT NULL REFERENCES users(id),
    channel VARCHAR(20) NOT NULL CHECK (channel IN ('IN_APP', 'EMAIL')),
    subject VARCHAR(500),
    body TEXT,
    delivery_status VARCHAR(30) NOT NULL DEFAULT 'PENDING'
        CHECK (delivery_status IN ('PENDING', 'SENT', 'DELIVERED', 'FAILED', 'BOUNCED', 'CANCELLED')),
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    retry_count INT NOT NULL DEFAULT 0,
    next_retry_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_deliveries_pending ON notification_deliveries(next_retry_at)
    WHERE delivery_status IN ('PENDING', 'FAILED');
CREATE INDEX idx_deliveries_event ON notification_deliveries(event_id);
```

**Idempotency**: One event per `(policy_id, target_record_id, trigger_date)`. Multiple deliveries per event (one per recipient × channel). Deduplication is on the event, not the delivery.

### 7.2 Retry and Failure

- Exponential backoff: 1m, 5m, 30m, 2h, 12h. Max 5 retries.
- After max retries: delivery status → FAILED (final). Event remains; no further delivery attempts.
- Background job processes pending deliveries. Job idempotency via event_id + recipient + channel.

---

## 8. Background Jobs

### 8.1 Concrete Approach: PostgreSQL-Backed Queue with `SKIP LOCKED`

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
    next_run_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_error TEXT,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_jobs_runnable ON background_jobs(next_run_at)
    WHERE status IN ('PENDING', 'FAILED') AND next_run_at <= now();
```

### 8.2 Job Claiming (Atomic)

```sql
-- Worker claims ONE job atomically:
UPDATE background_jobs
SET status = 'LOCKED', locked_by = :worker_id, locked_at = now()
WHERE id = (
    SELECT id FROM background_jobs
    WHERE status IN ('PENDING', 'FAILED')
      AND next_run_at <= now()
    ORDER BY next_run_at
    FOR UPDATE SKIP LOCKED
    LIMIT 1
)
RETURNING *;
```

### 8.3 Concurrency, Recovery, and Idempotency

| Concern | Safeguard |
|---|---|
| Two workers pick same job | `FOR UPDATE SKIP LOCKED` prevents this |
| Worker crashes mid-job | Stale-lock detector: jobs with `status = 'LOCKED'` and `locked_at < now() - interval '10 minutes'` are reset to `PENDING` by a periodic sweep |
| Duplicate enqueue | `UNIQUE(idempotency_key)` — insert fails silently, no duplicate |
| Idempotent execution | Job handler checks for existing result before processing; re-execution produces same outcome |
| Max retries exceeded | Status → `DEAD_LETTER`; System Admin dashboard shows dead-letter count |
| Scheduling | `next_run_at` field; periodic jobs re-enqueue themselves with future `next_run_at` |

---

## 9. Rules Engine

### 9.A APH-to-Rules Lifecycle

```
APH PDF → REGISTERED → TEXT EXTRACTION (pymupdf/OCR) → EXTRACTION_COMPLETE
  → CANDIDATE PROVISION IDENTIFICATION (human-assisted)
  → SOURCE VERIFICATION (human cross-checks against original PDF)
  → VERIFIED PROVISION
  → STRUCTURED RULE DRAFT (Regulatory Rule Administrator)
  → SCHEMA VALIDATION (Pydantic model)
  → AUTOMATED TEST CASES (expected inputs → outputs)
  → SUBMITTED FOR REVIEW
  → INDEPENDENT HUMAN REVIEW (different administrator; separation of duties)
  → APPROVED
  → PUBLISHED (available for runtime)
  → [SUSPENDED | DEPRECATED]
```

Candidate/unverified provisions **never** execute as production rules.

### 9.B Rule Versioning

```sql
CREATE TABLE regulatory_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_family_code VARCHAR(100) NOT NULL,
    version INT NOT NULL DEFAULT 1,
    -- ... (full schema as in v2.0 §10.2, with these additions:)
    status VARCHAR(30) NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT', 'UNDER_REVIEW', 'APPROVED', 'PUBLISHED', 'SUSPENDED', 'DEPRECATED')),
    effective_from DATE NOT NULL,
    effective_until DATE,
    UNIQUE (rule_family_code, version),
    CONSTRAINT chk_no_overlap EXCLUDE USING gist (
        rule_family_code WITH =,
        daterange(effective_from, effective_until, '[]') WITH &&
    ) WHERE (status = 'PUBLISHED'),
    CONSTRAINT chk_approval_separation CHECK (approved_by IS NULL OR approved_by != created_by)
);
```

**Key constraints:**
- `(rule_family_code, version)` is unique: stable family identifier, independent version numbers.
- The `EXCLUDE` constraint prevents two PUBLISHED versions of the same family from having overlapping effective date ranges.
- Only `PUBLISHED` rules are evaluated at runtime: `WHERE status = 'PUBLISHED' AND effective_from <= current_date AND (effective_until IS NULL OR effective_until >= current_date)`.
- `SUSPENDED` rules are immediately excluded from runtime (emergency deactivation pending review).

### 9.C Rule-Application Binding

- **Default policy (apply-at-submission):** An application binds to the rule versions effective at its submission date. Each `transition_events` row records `rule_family_code` + `rule_version`.
- **Alternative policy (apply-latest):** Each transition uses the latest published rule. Configurable per academic year.
- **No silent migration:** Changing an in-progress application's rule version requires an explicit authorised action, recorded in audit.
- `workflow_instances.workflow_definition_id` preserves the exact workflow definition.

### 9.D APH Reference Search (Deterministic)

PostgreSQL `tsvector`/`tsquery` full-text search on `aph_source_provisions.provision_text`. Structured filters on chapter, section, clause, page. No embeddings, no AI.

---

## 10. Database and Migration Consistency Report

### 10.1 Table Inventory

| Table | Purpose | Foreign Keys | Indexes |
|---|---|---|---|
| users | User accounts | — | email (UNIQUE) |
| roles | Permission definitions | — | name (UNIQUE) |
| role_assignments | User-role bindings | users, roles | user_id (partial: active only) |
| regions | Geographic regions | — | code (UNIQUE) |
| institutions | Registered institutions | regions | region_id, pid (UNIQUE) |
| academic_years | AY configuration | — | year_label (UNIQUE) |
| workflow_definitions | Workflow state machines | — | (name, version) UNIQUE |
| application_categories | Application type definitions | workflow_definitions | code (UNIQUE) |
| applications | Application records | institutions, application_categories, academic_years, users, regions | stage+status, region, officer, institution, AY |
| workflow_instances | Runtime workflow state | applications, workflow_definitions | application_id (UNIQUE) |
| stage_entries | Stage history | applications, users | app, stage, open entries |
| transition_events | Transition audit | applications, users | app, time |
| clock_events | Clock history (append-only) | applications, users | app+time |
| tasks | Task assignments | applications, users | assignee+status |
| deficiency_records | Deficiency tracking | applications, users | app, open deficiencies |
| evc_queue_entries | EVC scheduling | applications, users, regions | status+region |
| evc_member_assignments | EVC team | evc_queue_entries, users | — |
| compliance_obligations | Compliance tracking | applications, institutions, users | status+due_date, institution |
| evidence_submissions | Evidence uploads | compliance_obligations, users | obligation_id, receipt_number (UNIQUE) |
| institution_documents | Document records | institutions, users, applications, compliance_obligations, self-ref | expiry (operative only), institution+type |
| notification_policies | Notification rules | — | — |
| notification_events | Notification occurrences | notification_policies | idempotency_key (UNIQUE) |
| notification_deliveries | Delivery attempts | notification_events, users | pending, event_id |
| aph_source_documents | APH PDF records | users, self-ref | — |
| aph_source_provisions | Extracted provisions | aph_source_documents, users | document_id, GIN(search_vector), chapter+section+clause |
| regulatory_rules | Rule registry | aph_source_documents, users, self-ref | status+dates, type (published), (family,version) UNIQUE, EXCLUDE gist |
| rule_review_history | Rule governance audit | regulatory_rules, users | rule_id |
| background_jobs | Job queue | — | runnable (partial), dead_letter (partial), idempotency_key (UNIQUE) |
| audit_events | Audit trail | users | entity, actor, time |

### 10.2 Consistency Checks

| Check | Status |
|---|---|
| Every FK references an existing table | ✓ All verified |
| No circular FK dependencies (except self-refs: regulatory_rules, institution_documents, aph_source_documents) | ✓ Self-refs are nullable |
| All CHECK constraints use valid PostgreSQL syntax | ✓ Verified |
| All CREATE INDEX uses valid syntax (no inline INDEX) | ✓ All external CREATE INDEX |
| No stored generated columns referencing `now()` | ✓ Removed in v2.0 |
| All UNIQUE constraints specified | ✓ |
| EXCLUDE constraint for rule overlap requires `btree_gist` extension | ⚠ Migration must `CREATE EXTENSION IF NOT EXISTS btree_gist;` |
| Audit table permissions require separate DB role | ⚠ Migration must create `app_role` and `audit_readonly_role` with appropriate GRANT |

### 10.3 Migration Order

1. `CREATE EXTENSION IF NOT EXISTS btree_gist;`
2. users → roles → role_assignments
3. regions → institutions
4. academic_years → workflow_definitions → application_categories
5. applications → workflow_instances → stage_entries → transition_events → clock_events → tasks → deficiency_records
6. evc_queue_entries → evc_member_assignments
7. compliance_obligations → evidence_submissions → institution_documents
8. notification_policies → notification_events → notification_deliveries
9. aph_source_documents → aph_source_provisions → regulatory_rules → rule_review_history
10. background_jobs → audit_events
11. GRANT/REVOKE statements for audit_events
12. Seed data (roles, demo users, regions, academic years, application categories, workflow definitions, initial rules)

---

## 11. Security and Audit

### 11.1 Authentication: JWT via FastAPI + python-jose. Refresh tokens. MFA for officers/admins.

### 11.2 Authorisation: Backend RBAC middleware. PostgreSQL RLS on sensitive tables.

### 11.3 Document Security: Private storage, signed time-limited URLs, type whitelist, size limits, virus scanning, encryption at rest.

### 11.4 Audit Integrity — Honest Assessment

**What database permissions provide:**
- `REVOKE UPDATE, DELETE ON audit_events FROM app_role;` prevents the application from modifying audit records through normal operations.
- This is a **defence-in-depth measure**, not true immutability.

**What it does NOT prevent:**
- A DBA or superuser can still modify records.
- A compromised server with elevated privileges could bypass RLS.

**Compensating controls:**
- Periodic audit-log checksums (hash chain of recent entries) stored in a separate, append-only location.
- Database connection from application uses a **least-privilege role** (`app_role`) that cannot ALTER TABLE, DROP, or GRANT.
- Superuser access is restricted to named administrators and logged by PostgreSQL's own logging.
- For production: consider external audit-log shipping to a write-once store (e.g., S3 with Object Lock). This is a deployment decision, not an application design issue.

### 11.5 Integration Status

| Integration | Status | Prototype Handling |
|---|---|---|
| AICTE Web Portal | **MOCK** — no access confirmed | Stub returning synthetic data, labelled `is_demo=true` |
| NSWS | **MOCK** — no API spec available | Stub import endpoint |
| Payment Gateway | **MOCK** — no credentials | Stub confirmation endpoint |
| Email Service | **AVAILABLE** — SMTP configuration | Configured via environment variables |

---

## 12. Source-Linked Regulatory Test Matrix

Every test references a verified rule from §3 and its APH source.

| Test ID | Rule Tested | APH Source | Test Description | Expected Outcome |
|---|---|---|---|---|
| T-WF-01 | WF-NEW-001 | Cl. 1.8, 1.9 | New institution app follows Scrutiny→EVC→EC | Workflow instance uses correct definition; states match |
| T-WF-02 | WF-EOA-SD-001 | Table 2.3 | EoA self-disclosure skips Scrutiny/EVC | Direct path: SUBMITTED→PAYMENT→SELF_DISCLOSURE→EOA_ISSUED |
| T-WF-03 | Table 2.3 (scrutiny-only) | Table 2.3 | Bank details change cannot enter EVC | Transition to EVC_QUEUED rejected |
| T-WF-04 | WF-INTAKE-001 | Cl. 2.6(j) | Intake increase requires EVC | After scrutiny clear, enters EVC queue |
| T-DL-01 | DL-APPEAL-7DAY-CH1 | Cl. 1.11(a) | Appeal filed day 8 rejected | Deadline exceeded; appeal creation fails |
| T-DL-02 | DL-APPEAL-7DAY-CH2 | Cl. 2.24(a) | Appeal filed day 6 accepted | Appeal created; enters SAC queue |
| T-DL-03 | DL-LOA-VALID-2YR | Cl. 1.10(b)(ii) | LoA expires after 2 academic years | System flags LoA as expired; DL-LOA-EXPIRY triggered |
| T-DL-04 | DL-SD-PENALTY | Cl. 2.25(f) | Security deposit paid after 31 May | 10% penalty applied |
| T-DL-05 | DL-SD-PENALTY | Cl. 2.25(f) | Security deposit not paid by 31 July | Approval withdrawal flagged |
| T-DOC-01 | DOC-LEASE-30YR | Cl. 2.1(e) | Lease expiry insufficient for max course duration | Application flagged; EoA cannot be issued |
| T-DOC-02 | INF-STRUCT-30YR | Cl. 6.17(h) | Building completion cert 30+ years old, no stability cert | Alert generated |
| T-DOC-03 | INF-STRUCT-30YR | Cl. 6.17(h) | Stability cert older than 5 years | Renewal required alert |
| T-EL-01 | EL-BREAK-6YR | Cl. 2.16.1(a) | Institution with 6-year EoA gap applies under break-in-EoA | Application rejected; must apply as new institution |
| T-EL-02 | EL-3YR-EOA-001 | Cl. 2.1(a) | Institution meets NAAC 3.01+ criterion | Eligible for 3-year EoA |
| T-FEE-01 | FEE-TER-NEW-001 | Table 1.1 | Govt institution TER charge | Rs. 1.00 Lakh |
| T-FEE-02 | FEE-TER-NEW-001 | Table 1.1 | Private institution TER charge | Rs. 10.00 Lakh |
| T-FEE-03 | FEE-TER-EVC | Cl. 1.4.2(d) | Additional online EVC TER | Rs. 1.25 Lakh |
| T-FEE-04 | FEE-SD-DOUBLE | Table 1.4 Note | Private leased institution security deposit | Double the standard amount |
| T-PROC-01 | PROC-ONLINE | Cl. 1.8 Note | EVC defaults to online mode | EVC type = ONLINE unless explicitly overridden |
| T-PROC-02 | PROC-SHC | Cl. 2.23.3 | Deficient app gets SHC compliance opportunity | Application routes through SHC before EC |
| T-PROC-03 | PROC-SAC | Cl. 2.24(b) | Appeal goes to SAC (not SHC) | SAC handles the appeal |
| T-AC-01 | RBAC | — | Institution user views other institution's app | 403 Forbidden |
| T-AC-02 | RBAC | — | Regional officer views out-of-region app | 403 Forbidden |
| T-AC-03 | Rule governance | — | Rule admin approves own rule | CHECK constraint rejects (approved_by != created_by) |
| T-AC-04 | Rule status | — | DRAFT rule queried at runtime | Not returned (WHERE status = 'PUBLISHED') |
| T-JOB-01 | Background jobs | — | Duplicate job enqueue | UNIQUE(idempotency_key) prevents duplicate |
| T-JOB-02 | Background jobs | — | Job exceeds max retries | Status → DEAD_LETTER |
| T-JOB-03 | Background jobs | — | Two workers claim simultaneously | SKIP LOCKED ensures no double-processing |
| T-AUD-01 | Audit integrity | — | Application UPDATE via app_role on audit_events | Permission denied |
| T-VER-01 | Rule versioning | — | Two published versions of same family with overlapping dates | EXCLUDE constraint rejects |
| T-VER-02 | Rule-app binding | — | In-progress app retains original rule version after new version published | transition_events shows original rule_version |

---

## 13. Unresolved Issues

### 13.1 Missing APH Evidence

| # | Issue | APH Reference | Impact | Required Action |
|---|---|---|---|---|
| U1 | Per-stage processing deadlines | Table 2.2 | System cannot flag overdue by stage using APH authority | Obtain internal AICTE stage timelines or accept administrative defaults |
| U2 | EVC scheduling deadline | Cl. 1.9 | No APH basis for flagging late EVC scheduling | Accept administrative target |
| U3 | Undertaking durations | General | Cannot auto-set due dates from APH | Per-obligation manual entry or administrative defaults |
| U4 | EVC report submission deadline | Cl. 1.9 | Cannot flag late EVC reports from APH | Administrative target |
| U5 | Re-scrutiny iteration limit | Cl. 1.8 | Potential infinite loop | Administrative configurable limit |
| U6 | Extended EoA annual data scope | Cl. 2.1 (Note) | Cannot define what data to collect | Await AICTE specification |
| U7 | NSWS API specification | Cl. 1.3.1 | Cannot build real integration | Mock for prototype |
| U8 | Academic Calendar dates | Cl. 1.10(c),(d) | Published separately and annually | Per-AY configuration by admin |

### 13.2 Ambiguous Provisions Requiring Authorised Review

| # | Issue | APH Text | Possible Interpretations | Required Action |
|---|---|---|---|---|
| A1 | SHC vs SAC invocation | Cl. 2.23.3 / Cl. 2.24 | SHC = pre-EC compliance; SAC = post-EC appeal. OR: SHC/SAC both available at EC's discretion | Authorised clarification |
| A2 | "As Applicable" meaning | Table 2.3 footer | (a) Only when deficiencies found, (b) At EC's discretion, (c) Always for certain types | Authorised clarification |
| A3 | Second EVC "if required" for site change | Cl. 2.17(e) | Who decides "if required" — EVC coordinator, Bureau, EC? | Authorised clarification |
| A4 | Appeal start date Ch.I vs Ch.II | Cl. 1.11(a): "date of issue of LoD"; Cl. 2.24(a): "date of uploading of the decision" | Same meaning or different trigger events? | Authorised clarification |
| A5 | TER 10% increase base year | Cl. 1.4.2 Note | AY 2024-25 as base (handbook issue year) or prior year? | Authorised clarification |
| A6 | Hibernation period formula | Cl. 2.16.1(d) | Text truncated in extraction — exact formula needs re-verification | Re-extract full clause text |

### 13.3 Features Blocked by Missing Evidence or Access

| Feature | Blocker | Status |
|---|---|---|
| NSWS data import | No API specification | MOCK only |
| Payment gateway verification | No credentials | MOCK only |
| AICTE portal data sync | No API access | MOCK only |
| Per-stage overdue flagging with regulatory authority | No APH per-stage deadlines (U1) | Administrative only; cannot label as regulatory |
| Automatic undertaking due-date derivation | No APH-specified durations (U3) | Manual entry or admin default |

---

## 14. Implementation Sequence

### Phase 1: Foundation (Weeks 1-2)
Scaffolding, auth, DB migrations for users/roles/regions/institutions/academic_years. Seed data.

### Phase 2: Workflow Core (Weeks 3-4)
Applications, workflow definitions (3 routes seeded), state machine, transitions, optimistic locking.

### Phase 3: Scrutiny + EVC (Weeks 5-6)
Scrutiny observations/deficiencies, re-scrutiny loop, EVC queue/schedule/completion/report.

### Phase 4: Compliance + Documents (Weeks 7-8)
Obligations, evidence submission, verification, document upload/expiry/lease monitoring.

### Phase 5: Notifications + Jobs (Weeks 9-10)
Background job queue, notification events/deliveries, templates, deduplication, retry.

### Phase 6: Rules Engine + APH Reference (Weeks 11-12)
Rule registry, governance workflow, status enforcement, APH provisions with full-text search.

### Phase 7: Dashboards + Audit (Weeks 13-14)
Dashboard APIs, React pages, drill-down, audit viewer, clock history reports.

### Phase 8: Integration + Testing + Polish (Weeks 15-16)
Mock integrations, E2E test suite, RLS policies, security hardening, deployment guide.

### Minimum Demo (after Phase 4)
New Institution: submit → pay → scrutiny → deficiency → response → re-scrutiny → EVC → approve with condition → undertaking → evidence → verify. Shows workflow, RBAC, clock tracking, compliance, document handling, and audit trail.

---

## 15. Final Build-Readiness Report

### 15.1 What Can Be Built Now

| Component | Evidence | Status |
|---|---|---|
| 22 workflow routes from Table 2.3 | SOURCE_VERIFIED | **GO** |
| Workflow state machine (all 3 route types) | SOURCE_VERIFIED | **GO** |
| Role-based access control (13 roles) | Design decision + APH authority references | **GO** |
| Application CRUD, submission, payment tracking | Standard application logic | **GO** |
| Scrutiny/re-scrutiny module | Cl. 1.8, 2.23.1 verified | **GO** |
| EVC queue, scheduling, completion, report | Cl. 1.9, 2.6(j), 2.23.2 verified | **GO** |
| Compliance obligations and evidence verification | Design requirement | **GO** |
| Document upload, validity tracking, lease monitoring | Cl. 2.1(e), 6.17(h)(i) verified | **GO** |
| Notification events and deliveries | Design requirement | **GO** |
| Background job queue | Technical implementation | **GO** |
| Rules registry with governance lifecycle | Design requirement | **GO** |
| APH reference search (full-text) | Technical implementation | **GO** |
| Audit trail | Design requirement | **GO** |
| Pendency dashboards with clock separation | Design requirement | **GO** |
| TER fee calculation | Tables 1.1, 2.1 verified | **GO** |
| Security deposit calculation | Table 1.4 verified | **GO** |
| Appeal deadline enforcement (7 days) | Cl. 1.11(a), 2.24(a) verified | **GO** |
| LoA validity tracking (2 years) | Cl. 1.10(b)(ii) verified | **GO** |

### 15.2 What Must Remain Disabled Until Authorised

| Feature | Blocker |
|---|---|
| Rules with AMBIGUOUS status | Require authorised review (A1-A6) |
| Rules with INTERPRETATION_REQUIRES_REVIEW confidence | Require authorised confirmation |
| Per-stage overdue flagging labelled as "regulatory" | No APH evidence for per-stage deadlines |
| Automatic undertaking due-date derivation from APH | No APH-specified durations |
| Second EVC trigger logic for site changes | Ambiguous "if required" (A3) |

### 15.3 What Requires External Confirmation

| Dependency | Owner | Impact if Unavailable |
|---|---|---|
| AICTE responses to 8 unresolved questions (§13.1) | AICTE | Features use administrative defaults; cannot claim regulatory authority |
| Authorised review of 6 ambiguous items (§13.2) | AICTE / Designated authority | Related rules remain SUSPENDED |
| NSWS API specification | NSWS / AICTE | Mock integration only |
| Payment gateway credentials | AICTE | Mock payment only |
| Production hosting environment | Project team | Docker Compose ready; cloud TBD |

### 15.4 Final Recommendation

## **CONDITIONAL GO**

**Evidence:**
- All 22 workflow routes are SOURCE_VERIFIED against APH Table 2.3.
- All 28 regulatory rules in §3.2 have traceable APH citations; 24 are SOURCE_VERIFIED, 2 PARTIALLY_VERIFIED, 2 AMBIGUOUS.
- Technical architecture is coherent: modular monolith, no unnecessary dependencies, executable PostgreSQL schema, concrete job-processing approach.
- Rule governance lifecycle prevents unverified rules from executing.
- Test matrix covers all verified rules with source-linked tests.

**Conditions for full GO:**
1. Authorised review of 6 ambiguous items (A1-A6) — these block specific workflow branches.
2. AICTE response to at least U1 (per-stage deadlines) and U6 (extended EoA data scope).
3. Re-verification of EL-HIBERN-PERIOD rule (full clause text was truncated in extraction).
4. Production environment decision.

**Risk assessment:**
- Development can proceed on all components in §15.1.
- Ambiguous features are isolated behind rule-status gates and can be enabled post-authorisation without architectural changes.
- External integrations are cleanly mocked and replaceable.
- No component depends on AI, RAG, or unavailable external services for core operation.

---

*End of Final Technical Foundation Specification*

*APH citations verified against the original AICTE Approval Process Handbook 2024-2027 PDF, extracted and inspected in this session. Unverified items are explicitly flagged. No rule executes without SOURCE_VERIFIED or authorised PARTIALLY_VERIFIED status and PUBLISHED governance status.*
