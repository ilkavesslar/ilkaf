from __future__ import annotations

from uuid import uuid4

import pytest
from app.core.password import get_password_hasher
from app.models import Base, Organization, Role, User
from app.services.bootstrap_admin import (
    BootstrapError,
    provision_first_admin,
    session_cookie_attributes,
)
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(engine.sync_engine, "connect")
    def _fk(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        db.add(Role(name="SYSTEM_ADMIN", description="admin"))
        db.add(Role(name="VIEWER", description="viewer"))
        db.add(Organization(name="Existing Plant"))
        await db.commit()
        yield db
    await engine.dispose()


@pytest.mark.asyncio
async def test_provisions_one_argon2id_admin(session) -> None:
    password = "correct-horse-battery"
    email, organization = await provision_first_admin(session, "Admin@Example.com", password)
    assert email == "admin@example.com"
    assert organization == "Existing Plant"
    user = await session.scalar(select(User).where(func.lower(User.email) == email))
    assert user is not None
    assert user.disabled_at is None
    assert user.email_verified is True
    assert user.password_hash is not None
    assert user.password_hash.startswith("$argon2id$")
    assert user.password_hash != password
    assert get_password_hasher().verify(password, user.password_hash) is True
    role = await session.scalar(select(Role).where(Role.id == user.role_id))
    assert role is not None and role.name == "SYSTEM_ADMIN"
    orgs = (await session.scalars(select(Organization))).all()
    assert len(orgs) == 1


@pytest.mark.asyncio
async def test_refuses_a_second_admin(session) -> None:
    await provision_first_admin(session, "admin@example.com", "correct-horse-battery")
    with pytest.raises(BootstrapError, match="already exists"):
        await provision_first_admin(session, "other@example.com", "another-horse-battery")
    count = await session.scalar(select(func.count()).select_from(User))
    assert count == 1


@pytest.mark.asyncio
async def test_does_not_overwrite_an_existing_email(session) -> None:
    viewer = await session.scalar(select(Role).where(Role.name == "VIEWER"))
    org = await session.scalar(select(Organization))
    assert viewer is not None and org is not None
    session.add(
        User(
            id=uuid4(),
            organization_id=org.id,
            role_id=viewer.id,
            email="taken@example.com",
            display_name="Taken",
        )
    )
    await session.commit()
    with pytest.raises(BootstrapError, match="already belongs"):
        await provision_first_admin(session, "Taken@Example.com", "correct-horse-battery")
    taken = await session.scalar(select(User).where(User.email == "taken@example.com"))
    assert taken is not None
    assert taken.password_hash is None
    assert taken.role_id == viewer.id


def test_cookie_attributes_omit_the_token() -> None:
    attributes = session_cookie_attributes(
        "ilka_session=secret-token; HttpOnly; Path=/; SameSite=lax"
    )
    assert attributes == ["HttpOnly", "Path=/", "SameSite=lax"]
    assert "secret-token" not in " ".join(attributes)


@pytest.mark.asyncio
async def test_rejects_a_short_password_and_a_bad_email(session) -> None:
    with pytest.raises(BootstrapError, match="12 characters"):
        await provision_first_admin(session, "admin@example.com", "short")
    with pytest.raises(BootstrapError, match="not valid"):
        await provision_first_admin(session, "not-an-email", "correct-horse-battery")
    assert await session.scalar(select(func.count()).select_from(User)) == 0
