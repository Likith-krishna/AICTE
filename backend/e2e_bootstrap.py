"""Builds a fresh, migrated, seeded SQLite database for Playwright E2E runs.

Invoked by frontend/playwright.config.ts as the first step of the backend
webServer command, with DATABASE_URL / DATABASE_URL_SYNC already pointed at
the dedicated E2E file (see that config). Refuses to run against anything
else, so it can never touch the developer's flowguard.db or Supabase.
"""
import asyncio
import os

from app.core.config import settings
from app.core.migrate import migrate

if "sqlite" not in settings.database_url or "e2e-test" not in settings.database_url:
    raise RuntimeError(
        "e2e_bootstrap refuses to run: DATABASE_URL does not point at the dedicated "
        "E2E SQLite file. Check playwright.config.ts's webServer env."
    )

db_path = settings.database_url_sync.split("///", 1)[-1]
for suffix in ("", "-wal", "-shm"):
    path = db_path + suffix
    if os.path.exists(path):
        os.remove(path)

migrate()

import seed  # noqa: E402

asyncio.run(seed.seed())
print("E2E database ready.")
