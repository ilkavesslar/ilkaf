import pytest
from app.core.auth import SessionClaims
from app.core.rbac import RoleName
from app.models import Base, User
from app.services.identity import resolve_principal_from_session
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from tests.helpers.identity import IdentityWorld, seed_identity_world


def _claims(**kwargs):  # type: ignore[no-untyped-def]
    defaults = {"user_id": None, "email": None, "name": None, "session_id": None}
    defaults.update(kwargs)
    return SessionClaims(**defaults)


@pytest.mark.asyncio
async def test_resolve_principal_by_user_id() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        world = await seed_identity_world(session)
        await session.commit()
        user = world.users["VIEWER"]
        principal = await resolve_principal_from_session(
            session,
            _claims(user_id=user.id, email=user.email, name=user.display_name),
        )
        assert principal.user_id == user.id
        assert principal.email == user.email
        assert principal.role == RoleName.VIEWER
    await engine.dispose()


@pytest.mark.asyncio
async def test_email_lookup_is_case_insensitive() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        world = await seed_identity_world(session)
        await session.commit()
        user = world.users["VIEWER"]
        principal = await resolve_principal_from_session(
            session,
            _claims(email="Viewer@Example.COM"),
        )
        assert principal.user_id == user.id
    await engine.dispose()


@pytest.mark.asyncio
async def test_unknown_identity_is_401() -> None:
    from uuid import uuid4

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        await seed_identity_world(session)
        await session.commit()
        with pytest.raises(HTTPException) as denied:
            await resolve_principal_from_session(
                session,
                _claims(user_id=uuid4(), email="nobody@example.com"),
            )
        assert denied.value.status_code == 401
    await engine.dispose()


@pytest.mark.asyncio
async def test_inactive_user_rejected() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        world = await seed_identity_world(session)
        await session.commit()
        user = world.users["INACTIVE"]
        with pytest.raises(HTTPException) as denied:
            await resolve_principal_from_session(
                session,
                _claims(user_id=user.id, email=user.email),
            )
        assert denied.value.status_code == 403
    await engine.dispose()


@pytest.mark.asyncio
async def test_display_name_backfilled_when_empty() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        world = await seed_identity_world(session)
        await session.commit()
        user = world.users["UNBOUND"]
        user.display_name = ""
        await session.commit()
        principal = await resolve_principal_from_session(
            session,
            _claims(user_id=user.id, email=user.email, name="Updated Name"),
        )
        assert principal.display_name == "Updated Name"
    await engine.dispose()


def test_user_model_defines_case_insensitive_email_index() -> None:
    indexes = {index.name: index for index in User.__table__.indexes}
    index = indexes["uq_users_email_lower"]
    assert index.unique is True


@pytest.mark.asyncio
async def test_case_variant_email_is_rejected() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        world = await seed_identity_world(session)
        await session.commit()
        session.add(
            User(
                organization_id=world.org.id,
                role_id=world.roles["VIEWER"].id,
                email="Viewer@example.com",
                display_name="Case variant",
                idp_subject="sub-case-variant",
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()
    await engine.dispose()


@pytest.mark.asyncio
async def test_user_model_keeps_idp_subject_for_compatibility() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        world = await seed_identity_world(session)
        await session.commit()
        user = await session.scalar(select(User).where(User.id == world.users["VIEWER"].id))
        assert user is not None
        assert user.idp_subject is not None
    await engine.dispose()
