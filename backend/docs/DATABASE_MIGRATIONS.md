# Database migrations

This project uses Alembic. Migrations live in `app/migrations/versions/`.

## Supported engines

- **SQLite** — default for local development and all automated tests. No setup required.
- **PostgreSQL** (Supabase in this project, or any Postgres 14+) — the intended primary
  database once `backend/.env` is configured (see below).

`app/core/types.py` defines `GUID` and `JSONType` `TypeDecorator`s that render as native
`UUID`/`JSONB` on PostgreSQL and as `CHAR(36)`/`TEXT` on SQLite, from the same model
definitions. Migration `0002_phase3_workflow.py`'s one partial unique index
(`uq_stage_entries_one_open`) is declared with both `sqlite_where` and `postgresql_where`
so it applies correctly on either engine. There is currently no MySQL support in the
application itself — a local MySQL copy of application data (for reporting/analysis only)
is a separate, explicitly-approved piece of work, not a migration target.

## `app/core/migrate.py` — what `migrate()` actually does

- **Fresh database**: `alembic upgrade head` creates every table from the migration chain.
- **Legacy Phase 1–2 database** (tables created by `Base.metadata.create_all()` before
  Alembic was introduced, i.e. no `alembic_version` table but a `users` table already
  exists): the schema was verified identical to revision `0001_baseline`, so it is
  *stamped* at that baseline and then upgraded — no table is dropped or recreated.
- **Already-migrated database**: `upgrade head` applies only new revisions.

This function is what `backend/seed.py`'s `__main__` block and `backend/e2e_bootstrap.py`
both call before seeding — it is always safe to run, and never destroys existing data.

## Running migrations

```bash
cd backend
# .venv must already have requirements.txt installed (see project root README)
.venv/Scripts/python -m alembic upgrade head      # Windows
# .venv/bin/python -m alembic upgrade head        # macOS/Linux
```

Or equivalently, via the helper that also stamps a legacy database correctly:

```bash
.venv/Scripts/python -c "from app.core.migrate import migrate; print(migrate())"
```

The target database is whatever `DATABASE_URL_SYNC` resolves to (`backend/.env`, falling
back to the SQLite default in `app/core/config.py` if unset) — `app/migrations/env.py`
always overrides Alembic's own `sqlalchemy.url` from `Settings`, so `alembic.ini`'s
`sqlalchemy.url` line is never actually used.

## Seeding demo data

```bash
cd backend
.venv/Scripts/python seed.py
```

`seed.py` runs `migrate()` first, then seeds. It is **idempotent**: it checks whether
`Role` rows already exist and, if so, only adds anything from `PHASE3_USERS`/
`PHASE3_INSTITUTIONS` that doesn't already exist by email/pid — safe to run repeatedly
against a database that already has data, including your real `backend/flowguard.db`.
All demo users get the password `Demo@123`.

## Creating a new migration

```bash
cd backend
.venv/Scripts/python -m alembic revision -m "describe the change"
```

Write the upgrade/downgrade manually (no autogenerate is wired up in this project) and
make sure any new constraint that isn't portable across SQLite/PostgreSQL (partial
indexes, `CHECK` constraints with dialect-specific syntax) is guarded the same way
`0002_phase3_workflow.py` guards its partial index.

## Backups

Before any schema change against a database with real data, copy the SQLite file:

```bash
cp backend/flowguard.db backend/backups/flowguard_<label>_<date>.db
```

For Supabase/Postgres, use the project's own point-in-time recovery / manual backup
tooling — this repository does not script a Postgres backup.
