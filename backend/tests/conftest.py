import os

# Must run before any `app.*` import: Settings() is instantiated at import
# time and reads these from the environment.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/llm_prognoz_test"
)
os.environ.setdefault("SECRET_KEY", "test-secret-key")

import asyncpg
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.api.forecasts as forecasts_module
import app.worker as worker_module
from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.models.base import Base


def _admin_dsn_and_dbname() -> tuple[str, str]:
    url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    base, dbname = url.rsplit("/", 1)
    return f"{base}/postgres", dbname


@pytest_asyncio.fixture
async def engine():
    # Function-scoped (not session-scoped): pytest-asyncio gives each test
    # function its own event loop by default, and asyncpg connections can't
    # cross event loops, so the engine must live entirely within one test.
    admin_dsn, dbname = _admin_dsn_and_dbname()
    conn = await asyncpg.connect(admin_dsn)
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", dbname)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{dbname}"')
    finally:
        await conn.close()

    eng = create_async_engine(settings.database_url)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
def sessionmaker_(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
def _wire_test_db(sessionmaker_, monkeypatch):
    """Point both the API (via dependency override) and the worker job
    functions (which open their own sessions) at the same test database.
    """

    async def override_get_db():
        async with sessionmaker_() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(worker_module, "async_session", sessionmaker_)
    yield
    app.dependency_overrides.pop(get_db, None)


class InlineQueue:
    """Stand-in for the Arq Redis queue: runs the worker job function
    immediately instead of enqueueing it, so tests don't need a live
    Redis/worker process while still exercising the real job code.
    """

    async def enqueue_job(self, job_name: str, *args) -> None:
        fn = getattr(worker_module, job_name)
        await fn({}, *args)


@pytest_asyncio.fixture(autouse=True)
def _stub_queue(monkeypatch):
    async def fake_get_queue():
        return InlineQueue()

    monkeypatch.setattr(forecasts_module, "get_queue", fake_get_queue)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as c:
        yield c


@pytest_asyncio.fixture
async def db_session(sessionmaker_):
    """A session for tests to set up fixture data directly, bypassing the API."""
    async with sessionmaker_() as session:
        yield session


async def register(client, email="user@example.com", password="testpass123", org_name="Acme") -> dict[str, str]:
    resp = await client.post(
        "/auth/register", json={"org_name": org_name, "email": email, "password": password}
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
