# AICTE FlowGuard (SIH26262)

Deterministic AICTE approval-workflow automation prototype. See
[`AICTE_FlowGuard_Project_Handover.md`](AICTE_FlowGuard_Project_Handover.md) and
[`SIH26262_Technical_Foundation_Specification_Final.md`](SIH26262_Technical_Foundation_Specification_Final.md)
for the full project context and regulatory constraints. This file only covers how to
run the application and its tests locally.

## Prerequisites

- Python 3.11+ (3.12 recommended; developed against 3.13 where 3.12 wasn't available)
- Node.js 20+
- No local database server is required for day-to-day development — SQLite is the
  default. PostgreSQL (Supabase) is optional and only needed if you're working on the
  cloud-database integration.

## Backend setup

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt "bcrypt<5" aiosqlite
```

`bcrypt<5` is required — `passlib`'s bcrypt backend does not support bcrypt 5.x's API yet.

By default (no `backend/.env`), the app uses `sqlite+aiosqlite:///./flowguard.db` — no
further setup needed. To point at Supabase/PostgreSQL instead, create `backend/.env`
(git-ignored, never commit it):

```
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>:<port>/<db>?ssl=require
DATABASE_URL_SYNC=postgresql://<user>:<password>@<host>:<port>/<db>?sslmode=require
```

See [`backend/docs/DATABASE_MIGRATIONS.md`](backend/docs/DATABASE_MIGRATIONS.md) for
migration details, and `.env.example` for the other available settings
(`SECRET_KEY`, `CORS_ORIGINS`, etc. — these use different variable names than the
Docker Compose `POSTGRES_*` ones; see that file's comments).

Run migrations and seed demo data (safe to re-run, never destroys existing rows):

```bash
.venv/Scripts/python seed.py
```

Start the API:

```bash
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

Health check: `curl http://127.0.0.1:8000/api/health` should report
`{"status":"healthy","database":"connected",...}`.

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Opens on `http://localhost:5173`; its dev server proxies `/api` to
`http://localhost:8000` (see `vite.config.ts`) — the backend must already be running.

Demo logins (after seeding): any email from the seed data's demo user list, password
`Demo@123` (shown on the login page itself).

## Running the tests

| Suite | Command | Notes |
|---|---|---|
| Backend (pytest) | `cd backend && .venv/Scripts/python -m pytest` | Runs against a throwaway temp SQLite DB (see `tests/conftest.py`) — never touches `flowguard.db` or Supabase. |
| Frontend types | `cd frontend && npm run type-check` | |
| Frontend build | `cd frontend && npm run build` | |
| Frontend unit tests | `cd frontend && npm run test:unit` | Vitest + Testing Library. |
| End-to-end | `cd frontend && npm run test:e2e` | Playwright — see below. |

### End-to-end (Playwright)

```bash
cd frontend
npx playwright install chromium   # once
npm run test:e2e
```

This **starts its own backend and frontend dev servers** on ports 8000/5173 (see
`playwright.config.ts`), each run against a dedicated, disposable SQLite file
(`backend/.e2e-test.db`) that `backend/e2e_bootstrap.py` wipes and re-seeds from scratch
every run. It will fail to start if you already have a manual dev server bound to those
same ports — stop those first. It never touches `backend/flowguard.db` or Supabase.

## Local MySQL copy of application data

Not yet implemented. A local MySQL (`flowguard_local`) is planned as a read-only,
one-way export target from the primary database for reporting/analysis — see project
conversation history for the approved design (idempotent, FK-ordered, batched
transactions, no password/secret fields copied, never a source of truth for workflow
status). This is intentionally separate from Alembic migrations, which only ever target
SQLite or PostgreSQL.
