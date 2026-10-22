"""Test harness: a throw-away SQLite database built via Alembic + seed.

Environment variables are set BEFORE the app is imported so the global engine
points at the temporary database, never at the developer's flowguard.db.
"""
import asyncio
import os
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

_TMP = Path(tempfile.mkdtemp(prefix="flowguard-test-"))
_DB = _TMP / "test.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB}"
os.environ["DATABASE_URL_SYNC"] = f"sqlite:///{_DB}"
os.environ["DEBUG"] = "false"
os.environ["ENVIRONMENT"] = "test"

from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.migrate import migrate  # noqa: E402
from app.main import app  # noqa: E402

PASSWORD = "Demo@123"


def pytest_collection_modifyitems(items):
    # One event loop for the whole session: the async engine/pool is global.
    for item in items:
        if asyncio.iscoroutinefunction(getattr(item, "function", None)):
            item.add_marker(pytest.mark.asyncio(loop_scope="session"))


@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def database():
    migrate()
    import seed
    await seed.seed()
    yield _DB


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def client(database):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


_token_cache: dict[str, str] = {}


async def login(client: AsyncClient, email: str) -> dict:
    if email not in _token_cache:
        r = await client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
        assert r.status_code == 200, r.text
        _token_cache[email] = r.json()["access_token"]
    return {"Authorization": f"Bearer {_token_cache[email]}"}


@pytest.fixture(scope="session")
def auth():
    return login
