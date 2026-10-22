# AICTE FlowGuard — Complete Project Handover

**Handover Date:** 2026-10-22  
**Purpose:** Enable seamless continuation of development in a new Claude account  
**Status:** Phase 1 COMPLETE + Phase 2 COMPLETE. Ready for Phase 3.

---

## 1. Executive Summary

**AICTE FlowGuard** (SIH Problem Statement ID: **SIH26262**) is an end-to-end deterministic AICTE Approval Workflow Automation, Compliance Monitoring, and Alert Management System being built for **Smart India Hackathon 2026**.

The system automates the institutional approval lifecycle governed by the **AICTE Approval Process Handbook 2024–2027 (APH 2024-27)**, covering application submission, document scrutiny, Expert Visiting Committee (EVC) inspections, compliance tracking, and final authority decisions — all with full audit trails and regulatory traceability.

**Critical constraint:** NO AI/ML/RAG/LLM/embeddings. All regulatory logic uses deterministic, versioned, human-verified rules only.

**Current state:** Phase 1 (Foundation) and Phase 2 (Identity & Permissions) are fully implemented and verified. The application runs end-to-end with login, role-based dashboards, user management (CRUD), institution management with scoped data isolation, and all 28 database tables seeded. Phase 3 (Core Application Workflows) is the next step.

---

## 2. Project Objective and Scope

### Problem Statement
AICTE processes thousands of institutional approval applications annually through a complex multi-stage workflow involving multiple stakeholders, documents, inspections, and regulatory checkpoints. The current process involves manual tracking, paper-based reviews, and limited visibility into application status.

### Intended Users and Stakeholders
1. **Institutions** — Submit applications, upload documents, respond to deficiencies, track status
2. **Scrutiny Officers** — Review applications, note deficiencies, clear submissions
3. **Regional Officers/Coordinators** — Oversee region-scoped applications
4. **EVC Members** — Conduct inspections, submit reports
5. **Bureau Officers** — Route applications post-EVC, manage workflows
6. **Competent Authority** — Make final approval/rejection decisions
7. **Appellate Authority (SAC/SHC)** — Handle appeals against rejections
8. **Compliance Officers** — Track post-approval compliance obligations
9. **System Administrators** — Manage users, roles, system configuration
10. **Rule Administrators** — Manage regulatory rule lifecycle
11. **Audit Reviewers** — Read-only access to audit trails

### Solution Scope
- **Proposed system:** Full workflow automation covering all 22+ application categories from APH Table 2.3
- **Implemented so far:** Foundation infrastructure, auth, RBAC, user/institution management, data isolation
- **Planned:** Application state machine, document handling, scrutiny workflows, rule engine, compliance, notifications, dashboards

### What This System Does NOT Do
- Does NOT use AI/ML to interpret regulations
- Does NOT connect to real AICTE Portal, NSWS, or payment gateways (all external integrations are MOCKED)
- Does NOT make statutory decisions — humans retain full authority
- Does NOT invent regulatory requirements — all rules traced to APH source text

---

## 3. Problem Understanding and Intended Solution

### End-to-End Workflow

```
Institution submits application
    → Payment verification (mocked)
    → Scrutiny review by officers
        → Deficiency noted? → Institution responds → Re-scrutiny
        → Scrutiny clear
    → EVC queued and scheduled (for FULL route)
        → EVC inspection → Report submitted
    → SHC/SAC compliance review (where applicable)
    → Placed before Executive Committee
    → Competent Authority decision: Approve / Reject / Approve with Conditions
        → If rejected: Appeal to SAC → SAC recommendation → Final decision
```

### Three Workflow Route Types
1. **FULL** (Scrutiny + EVC + Authority decision) — New institutions, increase intake, site changes, etc.
2. **SCRUTINY_ONLY** (Scrutiny + Authority decision, no EVC) — Name changes, closures, bank detail changes
3. **SELF_DISCLOSURE** (Automated validation + minimal scrutiny) — Extension of Approval (self-disclosure), NRI seats

### 22 Application Categories
All from APH Table 2.3, each mapped to the appropriate workflow route. See `backend/seed.py` lines 160-184 for the complete list.

### Module Connections
- **Auth/RBAC** gates every action — role determines what you see and do
- **Applications** are the core entity — created by institutions, flow through workflow stages
- **Documents** attach to applications and compliance obligations
- **Scrutiny** module consumes applications in UNDER_SCRUTINY stage
- **Compliance** tracks post-approval obligations per institution
- **Rules engine** provides deterministic validation at each workflow transition
- **Notifications** fire on workflow transitions and clock events
- **Audit** records every state change with actor, action, and timestamp
- **Background jobs** handle async processing (notifications, clock checks)

### Unresolved Requirements
- Exact fee schedules for application categories (not fully specified in APH)
- Exact EVC composition rules per application type
- Interface specification for AICTE Portal integration (no real API access)
- NSWS payment gateway actual API (mocked in prototype)
- Specific document format requirements per category

---

## 4. Technical Foundation Specification

**File:** `SIH26262_Technical_Foundation_Specification_Final.md`  
**Version:** 3.0 (Final)  
**Date:** 2026-10-22  
**Source:** AICTE Approval Process Handbook 2024-2027 (APH 2024-27, 231 pages, verified)

### Key Contents
- **Section 1:** System architecture (modular monolith, module structure, design principles)
- **Section 2:** Workflow definitions with stage graphs and transitions
- **Section 3:** Regulatory Rule Register with 28 verified rules (APH citations, page numbers, verbatim text)
- **Section 4:** Pendency/clock management (AICTE processing time vs institutional response time)
- **Section 5:** Deficiency and resubmission model
- **Section 6:** EVC queue and assignment model
- **Section 7:** Compliance obligation tracking
- **Section 8:** Notification system (events separated from deliveries)
- **Section 8.5:** Background job processing (FOR UPDATE SKIP LOCKED)
- **Section 9:** Rule governance and versioning lifecycle
- **Section 10:** External integrations (ALL marked MOCK)
- **Section 11:** Security model
- **Section 12:** Test matrix (30 test cases, source-linked to rules)
- **Section 13:** Database schema (28 tables)
- **Section 14:** Build readiness assessment (CONDITIONAL GO)

**THIS FILE IS THE SOURCE OF TRUTH.** Transfer it to the new account. The summary above does not replace it.

### Key Architectural Decisions
1. **Modular monolith** — Single deployable, internal module boundaries. NOT microservices.
2. **PostgreSQL primary** — SQLite for local dev via TypeDecorator pattern (GUID, JSONType)
3. **Append-only clock events** — Clock history never mutated, only appended
4. **Notification events vs deliveries** — Separated into distinct tables with idempotency
5. **Rule lifecycle** — candidate → source verification → draft → tests → review → published
6. **Three workflow routes** — Defined as versioned JSON data in workflow_definitions table
7. **Background jobs** — PostgreSQL-backed with FOR UPDATE SKIP LOCKED

---

## 5. Final Technology Stack

### Frontend (IMPLEMENTED)
| Technology | Version | Purpose |
|---|---|---|
| React | 18.3.1 | UI framework |
| TypeScript | 5.6.3 | Type safety |
| Vite | 6.0.1 | Build tool and dev server |
| Tailwind CSS | 3.4.16 | Utility-first styling |
| React Router DOM | 6.28.0 | Client-side routing |
| TanStack Query | 5.62.0 | Server state management |
| TanStack Table | 8.20.0 | Data tables (available, not yet used) |
| React Hook Form | 7.54.0 | Form management (available, not yet used in forms) |
| Zod | 3.24.0 | Schema validation (available) |
| Lucide React | 0.460.0 | Icon library |
| Recharts | 2.14.0 | Charts (used in dashboard) |
| date-fns | 4.1.0 | Date formatting |
| clsx | 2.1.1 | Class name utility |

### Backend (IMPLEMENTED)
| Technology | Version | Purpose |
|---|---|---|
| Python | 3.12+ | Runtime |
| FastAPI | 0.115.6 | Web framework |
| Pydantic v2 | 2.10.4 | Validation and serialization |
| SQLAlchemy | 2.0.36 (async) | ORM |
| Alembic | 1.14.1 | Database migrations (configured, not yet run) |
| python-jose | 3.3.0 | JWT tokens |
| passlib | 1.7.4 | Password hashing (bcrypt) |
| structlog | 24.4.0 | Structured logging |
| httpx | 0.28.1 | HTTP client (for tests) |
| pytest | 8.3.4 | Testing |

### Infrastructure (CONFIGURED)
| Technology | Purpose |
|---|---|
| Docker Compose | Multi-service orchestration (PostgreSQL 16, backend, frontend) |
| PostgreSQL 16 Alpine | Production database |
| SQLite + aiosqlite | Local development database |

### Important Notes
- **bcrypt must be < 5** — bcrypt 5.x has a strict 72-byte limit that breaks seed script. Install `bcrypt<5` (4.3.0 confirmed working).
- **aiosqlite** is needed for SQLite async — add to requirements.txt if missing: `pip install aiosqlite`
- **Docker/PostgreSQL not available locally** — Development uses SQLite via TypeDecorator cross-DB compatibility layer. Docker Compose is configured but has not been tested.

---

## 6. Frontend Design System and Exact Colors

### Ink Wash Color Palette (NON-NEGOTIABLE)
```
Charcoal Gray:  #4A4A4A  — Headings, primary text, sidebar background
Cool Gray:      #CBCBCB  — Borders, dividers, subtle surfaces
Soft Ivory:     #FFFFE3  — Primary page background
Slate Blue:     #6D8196  — Primary actions, active navigation, links, accents
```

### CSS Custom Properties (defined in `frontend/src/styles/globals.css`)
```css
:root {
  --color-bg: #FFFFE3;
  --color-surface: #FFFFFF;
  --color-surface-elevated: #FFFFFF;
  --color-text: #4A4A4A;
  --color-text-muted: #7A7A7A;
  --color-border: #CBCBCB;
  --color-primary: #6D8196;
  --color-primary-hover: #5A6F82;
  --color-primary-text: #FFFFFF;
  --color-sidebar-bg: #4A4A4A;
  --color-sidebar-text: #FFFFE3;
  --color-sidebar-hover: #5A5A5A;
  --color-sidebar-active: #6D8196;
  --color-header-bg: #FFFFFF;
  --color-header-border: #CBCBCB;
}
```

### Tailwind Integration
Colors are mapped in `frontend/tailwind.config.js` under `ink.*` (direct hex) and `brand.*` (CSS variable references). Status colors (success, warning, error, info) are also defined.

### Design Requirements
- Professional enterprise-grade appearance (premium government platform)
- Consistent application shell with collapsible sidebar, header, breadcrumbs
- Reusable component classes: `.btn`, `.btn-primary`, `.card`, `.input`, `.label`, `.badge-*`, `.table-container`
- Responsive layouts
- Loading, empty, and error states for all data-driven components
- Real functionality connected to APIs — not decorative mockups
- All colors centralized via CSS variables — no scattered hardcoded values

---

## 7. Regulatory and Security Constraints

### Non-Negotiable Safeguards
1. **NO LLMs, RAG, embeddings, vector databases, or generative AI** to interpret or invent regulatory requirements
2. **Deterministic, versioned, testable rules only** for regulatory validation
3. **Rule lifecycle must be followed:** candidate → human source verification → draft → tests → independent review → approved → published
4. **Only published rules execute** — unverified, draft, or ambiguous rules remain disabled
5. **Human authority preserved** — Statutory approval/rejection/conditions are human decisions
6. **No invented requirements** — Don't fabricate deadlines, eligibility criteria, or approval rules
7. **External integrations MOCKED** — AICTE Portal, NSWS, payment gateways are sandboxed stubs
8. **Mock ≠ real** — A mock action must never appear as a real official submission/payment/approval
9. **Full traceability** — Rule provenance, versioning, APH citations, audit history
10. **Rule suspension** — Emergency deactivation capability for rules pending review

### Unresolved Regulatory Questions (from specification)
- Exact maximum processing days by application category (partially specified in APH)
- EVC composition requirements per category
- Fee schedule details
- Self-disclosure validation criteria specifics
- SHC/SAC procedural rules for hearings

---

## 8. Modules and Workflows

### Implemented Modules (Phase 1 + Phase 2)
| Module | Status | Description |
|---|---|---|
| Auth (JWT) | VERIFIED | Login, token refresh, protected routes |
| RBAC | VERIFIED | Role-based access control with `require_roles()` decorator |
| User Management | VERIFIED | Full CRUD (list/get/create/update/deactivate), admin-only |
| Institution Management | VERIFIED | List/get/create/update with scoped data isolation |
| Institution Scoping | VERIFIED | Institution users see only own; regional users see own region |
| Dashboard | VERIFIED | Stats cards, charts (Recharts), role-filtered data |
| Audit Logging | IMPLEMENTED | `log_audit_event()` service, records user/institution CRUD |
| Application Shell | VERIFIED | Sidebar, header, breadcrumbs, responsive layout |
| Design System | VERIFIED | CSS tokens, component classes, Ink Wash palette |
| Health Check | VERIFIED | API + DB connectivity check |

### Planned Modules (Phases 3–8)
| Module | Phase | Description |
|---|---|---|
| Application State Machine | 3 | Submit, track, transition applications through workflow stages |
| Application Forms | 3 | Category-specific form schemas, validation, submission |
| Workflow Engine | 3 | Stage transitions, guard conditions, automatic advances |
| Document Handling | 4 | Upload, verify, version documents per application |
| Scrutiny Interface | 4 | Reviewer queues, deficiency recording, resubmission tracking |
| Rule Engine | 5 | Deterministic validation, rule lifecycle management |
| Compliance Tracking | 5 | Post-approval obligations, evidence submission |
| Notification System | 6 | Event-based notifications, delivery tracking |
| Background Jobs | 6 | PostgreSQL-backed queue for async processing |
| Role Dashboards | 7 | Per-role dashboard views with relevant metrics |
| Audit Trail UI | 7 | Searchable, filterable audit event viewer |
| Reports | 7 | Operational analytics and metrics |
| E2E Testing | 8 | Playwright tests, API test suite |
| Docker Deployment | 8 | Full Docker Compose with PostgreSQL, health checks |

---

## 9. Implementation Phases

### Phase 1 — Foundation and Design System [COMPLETE, VERIFIED]
- Project structure (monorepo: `/backend` + `/frontend`)
- Frontend: React + Vite + Tailwind with Ink Wash design tokens
- Backend: FastAPI + SQLAlchemy + JWT auth
- 28 database tables via SQLAlchemy models
- Seed script with demo data (9 users, 1 institution, 14 roles, 7 regions, 2 academic years, 3 workflow definitions, 23 application categories)
- Application shell (sidebar, header, routing)
- Login page with demo credentials
- Dashboard with live API data and charts
- Health check endpoint
- Docker Compose configuration

### Phase 2 — Identity and Permissions [COMPLETE, VERIFIED]
- User management CRUD endpoints (admin-only): GET/POST/PATCH /api/users
- User listing with pagination, search, role/institution/region filters
- User create, update, deactivate with audit logging
- Role listing endpoint: GET /api/users/roles
- Institution endpoints: GET/POST/PATCH /api/institutions
- Institution detail with user count and region name
- Region listing: GET /api/institutions/regions
- Institution-scoped data isolation (institution users see only their own, regional users see their region)
- Permission guards on all endpoints via `require_roles()` decorator
- Secured registration endpoint (admin-only)
- Frontend Users page with paginated table, filters, create/edit modal
- Frontend Institutions page with table, region filter, detail panel
- All verified in browser: login → navigate → view data → test permissions

### Phase 3 — Core Application Workflows [NEXT]
- Institution profile management
- Application submission forms (category-specific)
- Application state machine with workflow transitions
- Stage guards (role + precondition checks)
- Workflow history and timeline views
- Backend validation for all transitions

### Phase 4 — Documents and Scrutiny
- Document upload with type validation and virus scanning stub
- Reviewer interfaces and assignment queues
- Deficiency recording with specific field citations
- Resubmission tracking with version comparison

### Phase 5 — Rules and Compliance
- Rule lifecycle UI (create, verify, test, review, publish)
- Deterministic validation engine execution
- Compliance obligation auto-generation from approved rules
- Evidence submission and verification

### Phase 6 — Notifications and Background Processing
- PostgreSQL-backed job queue with FOR UPDATE SKIP LOCKED
- Notification event/delivery pipeline
- In-app notification center
- Clock monitoring for deadline alerts

### Phase 7 — Dashboards, Analytics, and Audit
- Role-specific dashboard views
- Data tables with TanStack Table (sorting, filtering, pagination)
- Audit trail UI with search and filters
- Reports module

### Phase 8 — Integration, Testing, and Delivery
- Comprehensive pytest API tests
- Playwright E2E tests
- Mock external integrations (AICTE Portal, NSWS, payment)
- Docker deployment verification
- Demo preparation

---

## 10. Existing Files and Artifacts

### Root Level
| File | Status | Description |
|---|---|---|
| `SIH26262_Technical_Foundation_Specification_Final.md` | EXISTS | v3.0 Final spec — SOURCE OF TRUTH |
| `SIH26262_Technical_Foundation_Specification.md` | EXISTS | Earlier version (superseded) |
| `docker-compose.yml` | IMPLEMENTED | PostgreSQL 16 + backend + frontend services |
| `.env.example` | IMPLEMENTED | Environment variable template |

### Backend Files (`backend/`)
| File | Status | Description |
|---|---|---|
| `app/main.py` | IMPLEMENTED | FastAPI app with CORS, 5 routers (health, auth, dashboard, users, institutions) |
| `app/core/config.py` | IMPLEMENTED | Settings with SQLite default for local dev |
| `app/core/database.py` | IMPLEMENTED | Async engine, session factory, SQLite WAL+FK pragmas |
| `app/core/types.py` | IMPLEMENTED | GUID + JSONType TypeDecorators for SQLite/PostgreSQL portability |
| `app/core/security.py` | IMPLEMENTED | JWT auth, bcrypt hashing, `get_current_user`, `require_roles()` |
| `app/models/user.py` | IMPLEMENTED | User, Role, RoleAssignment (3 tables) |
| `app/models/institution.py` | IMPLEMENTED | Region, Institution (2 tables) |
| `app/models/application.py` | IMPLEMENTED | AcademicYear, WorkflowDefinition, ApplicationCategory, Application, WorkflowInstance, StageEntry, TransitionEvent, ClockEvent, Task, DeficiencyRecord (10 tables) |
| `app/models/evc.py` | IMPLEMENTED | EVCQueueEntry, EVCMemberAssignment (2 tables) |
| `app/models/compliance.py` | IMPLEMENTED | ComplianceObligation, EvidenceSubmission, InstitutionDocument (3 tables) |
| `app/models/notification.py` | IMPLEMENTED | NotificationPolicy, NotificationEvent, NotificationDelivery (3 tables) |
| `app/models/rules.py` | IMPLEMENTED | APHSourceDocument, APHSourceProvision, RegulatoryRule, RuleReviewHistory (4 tables) |
| `app/models/system.py` | IMPLEMENTED | BackgroundJob, AuditEvent (2 tables) |
| `app/api/routes/health.py` | VERIFIED | GET /api/health |
| `app/api/routes/auth.py` | VERIFIED | POST /api/auth/login, GET /api/auth/me, POST /api/auth/register (admin-only) |
| `app/api/routes/dashboard.py` | VERIFIED | GET /api/dashboard/stats |
| `app/api/routes/users.py` | VERIFIED | Full user CRUD + roles list |
| `app/api/routes/institutions.py` | VERIFIED | Institution CRUD + regions list + scoped isolation |
| `app/schemas/auth.py` | IMPLEMENTED | LoginRequest, TokenResponse, UserResponse, UserCreate |
| `app/schemas/common.py` | IMPLEMENTED | PaginatedResponse, MessageResponse, RegionResponse, etc. |
| `app/schemas/user.py` | IMPLEMENTED | UserCreateRequest, UserUpdateRequest, UserDetailResponse, RoleResponse |
| `app/schemas/institution.py` | IMPLEMENTED | InstitutionCreateRequest, InstitutionUpdateRequest, InstitutionDetailResponse |
| `app/services/audit.py` | IMPLEMENTED | `log_audit_event()` function |
| `app/migrations/env.py` | IMPLEMENTED | Alembic migration environment |
| `seed.py` | VERIFIED | Seeds 14 roles, 7 regions, 2 years, 1 institution, 3 workflows, 23 categories, 9 users |
| `flowguard.db` | VERIFIED | Seeded SQLite database (working) |
| `requirements.txt` | IMPLEMENTED | All Python dependencies listed |
| `Dockerfile` | IMPLEMENTED | Python 3.12-slim |
| `tests/test_health.py` | EXISTS | Basic health endpoint test |
| `alembic.ini` | IMPLEMENTED | Alembic configuration |

### Frontend Files (`frontend/`)
| File | Status | Description |
|---|---|---|
| `package.json` | IMPLEMENTED | All dependencies declared |
| `vite.config.ts` | IMPLEMENTED | Path alias @/ → src/, API proxy to :8000 |
| `tailwind.config.js` | IMPLEMENTED | Ink Wash colors, brand tokens, status colors, fonts |
| `tsconfig.json` | IMPLEMENTED | TypeScript configuration |
| `src/styles/globals.css` | IMPLEMENTED | CSS variables, component classes, base styles |
| `src/App.tsx` | IMPLEMENTED | BrowserRouter with all routes, real pages for /, /users, /institutions |
| `src/main.tsx` | IMPLEMENTED | React root with QueryClient |
| `src/lib/api.ts` | IMPLEMENTED | API client with JWT Bearer, 401 auto-redirect |
| `src/lib/auth.tsx` | IMPLEMENTED | AuthContext, login/logout, localStorage persistence |
| `src/types/api.ts` | IMPLEMENTED | All TypeScript interfaces (User, UserDetail, Role, Institution, etc.) |
| `src/components/layout/Sidebar.tsx` | VERIFIED | Collapsible sidebar with role-based nav filtering |
| `src/components/layout/Header.tsx` | VERIFIED | Header bar with user info and logout |
| `src/components/layout/AppShell.tsx` | VERIFIED | Protected layout with auth redirect |
| `src/components/ui/StatusBadge.tsx` | IMPLEMENTED | Stage-aware colored badges |
| `src/components/ui/StatsCard.tsx` | IMPLEMENTED | Dashboard stat cards |
| `src/components/ui/EmptyState.tsx` | IMPLEMENTED | Empty state component |
| `src/components/ui/LoadingSpinner.tsx` | IMPLEMENTED | Loading spinner |
| `src/components/ui/PageHeader.tsx` | IMPLEMENTED | Page header with breadcrumbs and actions |
| `src/pages/LoginPage.tsx` | VERIFIED | Login form with demo credentials panel |
| `src/pages/DashboardPage.tsx` | VERIFIED | Stats + Recharts charts from live API |
| `src/pages/UsersPage.tsx` | VERIFIED | User management with table, filters, create/edit modal |
| `src/pages/InstitutionsPage.tsx` | VERIFIED | Institution list with region filter, detail panel |
| `src/pages/ApplicationsPage.tsx` | IMPLEMENTED | Empty state placeholder (Phase 3 will build out) |
| `src/pages/PlaceholderPage.tsx` | IMPLEMENTED | Generic placeholder for unimplemented modules |

### TypeScript Build Status: CLEAN (no errors as of Phase 2 completion)

---

## 11. Actual Implementation Status

### Status Legend
- **DECIDED** — Design/requirement agreed
- **IMPLEMENTED** — Code exists in repository
- **VERIFIED** — Tested end-to-end in browser/API and confirmed working
- **PLANNED** — Intended but no code yet
- **BLOCKED** — Waiting on dependencies

| Component | Status | Evidence |
|---|---|---|
| Project structure | VERIFIED | Monorepo with backend/ and frontend/ |
| SQLite local dev database | VERIFIED | flowguard.db exists and is seeded |
| PostgreSQL Docker setup | IMPLEMENTED | docker-compose.yml exists; NOT tested (no Docker locally) |
| Cross-DB TypeDecorators | VERIFIED | GUID and JSONType work on SQLite |
| All 28 model tables | VERIFIED | Created via seed.py, queried by API endpoints |
| Seed data (9 users, 14 roles, 7 regions, etc.) | VERIFIED | All accessible via API |
| FastAPI server | VERIFIED | Runs on :8000, serves all endpoints |
| Health endpoint | VERIFIED | Returns healthy + database connected |
| JWT authentication | VERIFIED | Login returns token, protected routes enforce auth |
| Role-based authorization | VERIFIED | require_roles() blocks unauthorized access (403) |
| Institution-scoped isolation | VERIFIED | Institution user sees only own data |
| User CRUD (admin) | VERIFIED | List, create, update, deactivate all work |
| Institution CRUD | VERIFIED | List, get, create, update with region enrichment |
| Audit logging (backend) | IMPLEMENTED | Records user/institution changes; no UI yet |
| Frontend build | VERIFIED | TypeScript clean, production build passes |
| Vite dev server | VERIFIED | Runs on :5173 with API proxy |
| Login flow | VERIFIED | End-to-end in browser |
| Dashboard | VERIFIED | Stats cards + charts from live API |
| Sidebar navigation | VERIFIED | Role-based filtering, collapsible |
| Users page | VERIFIED | Paginated table, search, filters, create/edit modal |
| Institutions page | VERIFIED | Table, region filter, click-to-detail panel |
| Ink Wash design system | VERIFIED | CSS variables, Tailwind tokens, consistent styling |
| Alembic migrations | IMPLEMENTED | Configured but no migrations generated (using create_all) |
| Background jobs | DECIDED | Model exists; no worker implemented |
| Notification pipeline | DECIDED | Models exist; no endpoints or worker |
| Rule engine | DECIDED | Models exist; no execution logic |
| Application state machine | DECIDED | Models + workflow definitions exist; no transition logic |
| Document upload | DECIDED | Model exists; no file handling |
| E2E tests | PLANNED | No Playwright tests yet |
| API tests | IMPLEMENTED | test_health.py exists; not comprehensive |

---

## 12. Completed Decisions and Unresolved Questions

### Completed Decisions
1. Modular monolith, not microservices
2. SQLite for local dev, PostgreSQL for production (via TypeDecorator)
3. JWT authentication with role claims
4. Ink Wash palette with CSS variables + Tailwind integration
5. 14 system roles with backend-enforced RBAC
6. 3 workflow route types with JSON-defined stages and transitions
7. 23 application categories mapped to workflow routes
8. Append-only clock events (not mutable fields)
9. Notification events separated from deliveries
10. FOR UPDATE SKIP LOCKED for background job queue
11. All external integrations are MOCK
12. bcrypt < 5 required (5.x breaks seed)
13. Tables created via `Base.metadata.create_all` in seed, not Alembic migrations yet

### Unresolved Questions
1. Alembic migration strategy — currently using `create_all`, need to generate initial migration
2. File upload storage — `StorageBackend` interface decided but not implemented
3. EVC scheduling rules — how are visit dates assigned?
4. Fee schedule per category — not fully specified in APH
5. Self-disclosure validation criteria details
6. SHC/SAC procedural rules
7. Exact clock durations per application category
8. Rate limiting strategy (mentioned in spec, not implemented)
9. Password reset flow (not implemented)

---

## 13. Exact Next Actions

### Immediate: Phase 3 — Core Application Workflows
1. **Application submission endpoints** — POST /api/applications (institution user creates draft, fills form, submits)
2. **Application listing** — GET /api/applications with role-scoped filtering (institution sees own, regional sees region, admin sees all)
3. **Application detail** — GET /api/applications/{id} with full workflow history
4. **Workflow transition engine** — POST /api/applications/{id}/transition with:
   - Stage guard validation (check current stage allows transition)
   - Role guard (check user role matches transition's required role)
   - Precondition checks (e.g., all documents uploaded before submit)
   - Automatic transitions (e.g., SUBMITTED → PAYMENT_VERIFIED → UNDER_SCRUTINY)
   - TransitionEvent and StageEntry creation
   - ClockEvent management (start/pause processing clocks)
   - Audit logging
5. **Workflow timeline view** — Frontend component showing stage history
6. **Application form schemas** — Category-specific form_data validation using Zod
7. **Frontend: ApplicationsPage** — Full application list with filters, status badges, actions
8. **Frontend: ApplicationDetailPage** — Application info, workflow timeline, action buttons per stage
9. **Frontend: NewApplicationPage** — Multi-step form for creating and submitting applications

### Key Implementation Notes for Phase 3
- Workflow definitions are already seeded as JSON in `workflow_definitions` table
- Application model has `stage`, `status`, `form_data` (JSON), `version`, `region_id`
- WorkflowInstance links Application to WorkflowDefinition
- StageEntry records each stage visit with timestamps
- TransitionEvent records each transition with actor and trigger type
- ClockEvent is append-only for processing time tracking
- The `application.py` model file has all 10 tables ready to use

---

## 14. Complete Revised Master Implementation Prompt

**This is the full master prompt that governs all implementation work. Provide this to the new Claude account.**

---

### AICTE FLOWGUARD — MASTER IMPLEMENTATION PROMPT (v2)

#### Identity
Project: **AICTE FlowGuard** (SIH26262)
Purpose: End-to-end deterministic AICTE Approval Workflow Automation, Compliance Monitoring, and Alert Management System

#### Non-Negotiable Regulatory Safeguards
1. Do not use an LLM, RAG, embeddings, vector databases, or generative AI to interpret or invent regulatory requirements.
2. Implement regulatory validation using deterministic, versioned, testable rules.
3. A rule must not become executable merely because code has been generated for it. Follow the lifecycle: candidate → human source verification → draft → tests → independent review → approved → published.
4. Only appropriately approved and published rules may execute.
5. Preserve human authority over statutory approval, rejection, and other official decisions. The system supports and tracks the decision process; it does not decide.
6. Do not invent statutory deadlines, official eligibility criteria, or approval rules. Where information is uncertain or unavailable, mark the corresponding feature as requiring verification and implement a safe default (deny action, flag for review, or request human input).
7. External AICTE portal, NSWS, payment, and similar integrations must remain mocked or sandboxed until their actual API specifications, access, and authorization are available. A mock action must never be presented to the user as a real official submission, payment, or approval.
8. Preserve full traceability: rule provenance, versioning, APH clause citations, and auditability.

#### Technology Stack
**Frontend:** React 18, TypeScript, Vite, Tailwind CSS, semantic HTML5, custom CSS3, React Router, TanStack Query, TanStack Table, React Hook Form + Zod, Lucide React, Recharts
**Backend:** Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.x (async), Alembic, PostgreSQL 16 (SQLite for local dev)
**Infrastructure:** Docker Compose, environment-based configuration

#### Design System — Ink Wash Palette
```
Charcoal: #4A4A4A  — Text, headings, sidebar bg
Cool Gray: #CBCBCB — Borders, dividers, muted surfaces
Soft Ivory: #FFFFE3 — Page background
Slate Blue: #6D8196 — Primary actions, active nav, accents
```
Colors defined centrally via CSS custom properties. Integrated into Tailwind theme. No scattered hardcoded values.

#### Architecture
- **Modular monolith** — single deployable with internal module boundaries
- Do not split the application into microservices
- Cross-database portability via GUID/JSONType TypeDecorators
- JWT authentication with role-based access control
- 14 system roles with backend-enforced permissions
- Institution-scoped data isolation

#### Implementation Phases
Implement one phase at a time. Run checks, fix failures, report actual outcomes.

1. **Phase 1 — Foundation** [COMPLETE]: Project structure, design system, app shell, FastAPI, DB, seeding, Docker config
2. **Phase 2 — Identity & Permissions** [COMPLETE]: Auth, RBAC, user CRUD, institution CRUD, scoped isolation
3. **Phase 3 — Core Application Workflows**: Application state machine, submission, transitions, workflow history
4. **Phase 4 — Documents and Scrutiny**: Document upload, reviewer interfaces, deficiency loops
5. **Phase 5 — Rules and Compliance**: Rule lifecycle, deterministic validation, compliance tracking
6. **Phase 6 — Notifications and Background Processing**: Job queue, notification pipeline
7. **Phase 7 — Dashboards and Audit**: Role dashboards, data tables, audit trail UI
8. **Phase 8 — Integration, Testing, Delivery**: E2E tests, mock integrations, Docker deployment

#### Quality Requirements
- TypeScript must compile without errors
- All API endpoints must have proper error handling and validation
- Every state mutation must produce an audit event
- Frontend must show loading, empty, and error states
- Build real, connected functionality — not static mockups
- Test in browser before reporting complete

#### Definition of Done (per phase)
- All described features are implemented as working code
- TypeScript and Python type checks pass
- API endpoints are tested (at minimum via curl or httpx)
- Frontend pages display correct data from live API
- No broken imports, no orphaned files
- Audit trail records relevant actions

---

## 15. Continuation Prompt for New Claude Account

**Copy and paste this as your first message to the new Claude account, along with the technical specification file and any existing repository.**

---

```
I am continuing the AICTE FlowGuard project (SIH26262) from a previous Claude session. I have attached:

1. The project handover document (AICTE_FlowGuard_Project_Handover.md) — read this FIRST
2. The technical specification (SIH26262_Technical_Foundation_Specification_Final.md) — this is the SOURCE OF TRUTH
3. The existing project repository (the "AICTE project" directory)

CRITICAL CONTEXT:
- Phase 1 (Foundation) and Phase 2 (Identity & Permissions) are COMPLETE and VERIFIED
- The application runs end-to-end: backend on :8000, frontend on :5173
- 28 database tables exist and are seeded with demo data
- All demo users use password "Demo@123"
- SQLite is used for local dev (no Docker/PostgreSQL available locally)
- bcrypt must be < 5 (pip install "bcrypt<5")
- aiosqlite is required for SQLite async

YOUR TASK:
1. Read the handover document completely
2. Read the technical specification
3. Inspect the existing repository — DO NOT regenerate files that already exist
4. Verify the current state (start servers, test endpoints, check frontend)
5. Begin implementing Phase 3 — Core Application Workflows:
   - Application submission/creation endpoints
   - Application listing with role-scoped filtering
   - Workflow transition engine (stage guards, role guards, automatic transitions)
   - TransitionEvent and StageEntry creation
   - ClockEvent management
   - Frontend: Application list page, detail page, new application form
   - Workflow timeline visualization

CONSTRAINTS:
- Use the exact Ink Wash color palette: #4A4A4A, #CBCBCB, #FFFFE3, #6D8196
- Follow the master implementation prompt in the handover (Section 14)
- Preserve ALL regulatory safeguards (Section 7)
- Do NOT use AI/ML/RAG/LLM for any regulatory logic
- Treat the specification as the source of truth
- Build real, connected functionality — not mockups
- Implement and test incrementally
- Report what actually works and what doesn't
```

---

## 16. Transfer Checklist

Before starting the new session, ensure you transfer:

- [ ] **This handover document** — `AICTE_FlowGuard_Project_Handover.md`
- [ ] **Technical specification** — `SIH26262_Technical_Foundation_Specification_Final.md`
- [ ] **Entire project directory** — `AICTE project/` (includes backend/, frontend/, docker-compose.yml, .env.example)
- [ ] **Verify `flowguard.db` is included** — The seeded SQLite database
- [ ] **Verify `node_modules` excluded** — Run `npm install` in frontend/ after transfer
- [ ] **Verify Python venv excluded** — Run `pip install -r requirements.txt` in backend/ after transfer
- [ ] **Ink Wash palette reference** — Colors are documented in this handover and in globals.css/tailwind.config.js

### Post-Transfer Verification Steps
1. `cd frontend && npm install && npx tsc --noEmit` — Should be clean
2. `cd backend && pip install -r requirements.txt && pip install aiosqlite "bcrypt<5"`
3. `cd backend && PYTHONPATH=. python -m uvicorn app.main:app --port 8000`
4. `cd frontend && npx vite --port 5173`
5. Open http://localhost:5173 → Login as `admin@flowguard.gov.in` / `Demo@123`
6. Navigate to Dashboard, Users, Institutions — all should load with data

### API Endpoints Summary (currently working)
```
GET  /api/health                    — Health check
POST /api/auth/login                — JWT login
GET  /api/auth/me                   — Current user
POST /api/auth/register             — Create user (admin-only)
GET  /api/users                     — List users (admin/bureau, paginated)
GET  /api/users/roles               — List roles (authenticated)
GET  /api/users/{id}                — Get user (admin/bureau)
POST /api/users                     — Create user (admin)
PATCH /api/users/{id}               — Update user (admin)
PATCH /api/users/{id}/deactivate    — Deactivate user (admin)
GET  /api/institutions              — List institutions (scoped)
GET  /api/institutions/regions      — List regions (authenticated)
GET  /api/institutions/{id}         — Get institution (scoped)
POST /api/institutions              — Create institution (admin/bureau)
PATCH /api/institutions/{id}        — Update institution (admin/bureau)
GET  /api/dashboard/stats           — Dashboard statistics (role-filtered)
```

### Demo User Accounts
| Email | Role | Password |
|---|---|---|
| admin@flowguard.gov.in | system_admin | Demo@123 |
| institution@demo.ac.in | institution_applicant | Demo@123 |
| officer@flowguard.gov.in | regional_officer | Demo@123 |
| scrutiny@flowguard.gov.in | scrutiny_officer | Demo@123 |
| evc@flowguard.gov.in | evc_coordinator | Demo@123 |
| bureau@flowguard.gov.in | bureau_officer | Demo@123 |
| authority@flowguard.gov.in | competent_authority | Demo@123 |
| compliance@flowguard.gov.in | compliance_officer | Demo@123 |
| ruleadmin@flowguard.gov.in | rule_admin | Demo@123 |

---

*End of AICTE FlowGuard Project Handover*
