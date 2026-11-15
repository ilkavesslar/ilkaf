from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.db import get_db_session
from app.main import app
from app.models import Base
from tests.helpers.auth import create_test_session
from tests.helpers.identity import IdentityWorld, seed_identity_world


@pytest.fixture
async def auth_env(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[tuple[AsyncClient, IdentityWorld]]:
    monkeypatch.setenv("AUTH_SECRET_KEY", "ilka-test-secret")
    monkeypatch.setenv("AUTH_ALGORITHM", "HS256")
    get_settings.cache_clear()

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(engine.sync_engine, "connect")
    def _fk(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session

    async with factory() as session:
        world = await seed_identity_world(session)
        await session.commit()
        for key, user in world.users.items():
            # Create a real session for every seeded user so existing tests can
            # authenticate without calling the login endpoint.
            world.sessions[key] = await create_test_session(session, user)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, world

    app.dependency_overrides.clear()
    await engine.dispose()
    get_settings.cache_clear()
