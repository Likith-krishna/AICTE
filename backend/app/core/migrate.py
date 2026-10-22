"""Bring a database to the latest Alembic revision without destroying data.

* Fresh database ................. ``alembic upgrade head`` creates every table.
* Legacy Phase 1-2 database ...... tables were created by ``Base.metadata.create_all``
  (no ``alembic_version`` table). Its schema was verified identical to revision
  ``0001_baseline`` (see docs/DATABASE_MIGRATIONS.md), so it is *stamped* at the
  baseline and then upgraded. No table is dropped or recreated by the stamp.
* Already-migrated database ...... ``upgrade head`` applies only new revisions.

Usage:  python -m app.core.migrate
"""
from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import settings

BASELINE_REVISION = "0001_baseline"
BACKEND_DIR = Path(__file__).resolve().parents[2]


def alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "app" / "migrations"))
    return cfg


def migrate() -> str:
    engine = create_engine(settings.database_url_sync)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    cfg = alembic_config()
    if "alembic_version" not in tables and "users" in tables:
        command.stamp(cfg, BASELINE_REVISION)
        action = "stamped legacy create_all database at baseline, then upgraded"
    else:
        action = "upgraded"
    command.upgrade(cfg, "head")
    return action


if __name__ == "__main__":
    print(f"Database {migrate()} to head ({settings.database_url_sync}).")
