"""Postgres integration tests.

Local: skipped unless ILKA_POSTGRES_URL is set in the process environment or repo-root
`.env` (never print the value). Do not put Neon URLs in git.
CI: set ILKA_REQUIRE_POSTGRES_TESTS=1 so a missing URL fails the job instead of skipping.
Ordinary CI uses the disposable Actions Postgres service, not Neon.
"""

from __future__ import annotations

import os
import subprocess
import uuid
from pathlib import Path
from uuid import UUID

import pytest
from app.core.config import _asyncpg_compatible_url, get_settings
from app.main import create_app
from app.models import Organization, Role, Site, User, UserSiteAssignment
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"


def _postgres_url_from_environment() -> str:
    url = os.environ.get("ILKA_POSTGRES_URL", "").strip()
    if url:
        return url
    env_path = BACKEND_DIR.parent / ".env"
    if not env_path.is_file():
        return ""
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        if key.strip() == "ILKA_POSTGRES_URL":
            return val.strip().strip('"').strip("'")
    return ""


POSTGRES_URL = _postgres_url_from_environment()
REQUIRE_POSTGRES_TESTS = os.environ.get("ILKA_REQUIRE_POSTGRES_TESTS", "").strip() in {
    "1",
    "true",
    "yes",
}

if REQUIRE_POSTGRES_TESTS and not POSTGRES_URL:
    raise RuntimeError(
        "ILKA_POSTGRES_URL is required when ILKA_REQUIRE_POSTGRES_TESTS is set"
    )

pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="ILKA_POSTGRES_URL not set (optional local Postgres / CI service)",
)


def _async_url() -> str:
    url = POSTGRES_URL
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]
    return _asyncpg_compatible_url(url)


def _alembic(*args: str) -> None:
    completed = _alembic_captured(*args)
    completed.check_returncode()


def _alembic_captured(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = POSTGRES_URL
    env["ENVIRONMENT"] = "testing"
    return subprocess.run(
        ["alembic", *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_alembic_upgrade_downgrade_upgrade() -> None:
    _alembic("upgrade", "head")
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")


@pytest.mark.asyncio
async def test_postgres_crud_constraints() -> None:
    _alembic("upgrade", "head")
    engine = create_async_engine(
        _async_url(),
        pool_pre_ping=True,
        connect_args={
            "statement_cache_size": 0,
            "timeout": 60,
            **(
                {"ssl": True}
                if "sslmode=" in POSTGRES_URL.lower() or "neon.tech" in POSTGRES_URL.lower()
                else {}
            ),
        },
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            org = Organization(name=f"org-{uuid.uuid4()}")
            role = Role(name=f"role-{uuid.uuid4()}", description="test")
            session.add_all([org, role])
            await session.flush()
            assert org.created_at is not None
            site = Site(organization_id=org.id, name="plant-1")
            user = User(
                organization_id=org.id,
                role_id=role.id,
                email=f"{uuid.uuid4()}@example.com",
                idp_subject=None,
            )
            session.add_all([site, user])
            await session.commit()

        async with factory() as session:
            session.add(Organization(name=org.name))
            with pytest.raises(IntegrityError):
                await session.commit()

        async with factory() as session:
            session.add(
                User(
                    organization_id=uuid.uuid4(),
                    role_id=role.id,
                    email=f"{uuid.uuid4()}@example.com",
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_postgres_user_site_assignment_isolation() -> None:
    _alembic("upgrade", "head")
    engine = create_async_engine(
        _async_url(),
        pool_pre_ping=True,
        connect_args={
            "statement_cache_size": 0,
            "timeout": 60,
            **(
                {"ssl": True}
                if "sslmode=" in POSTGRES_URL.lower() or "neon.tech" in POSTGRES_URL.lower()
                else {}
            ),
        },
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            org_a = Organization(name=f"org-a-{uuid.uuid4()}")
            org_b = Organization(name=f"org-b-{uuid.uuid4()}")
            role = Role(name=f"role-{uuid.uuid4()}", description="test")
            session.add_all([org_a, org_b, role])
            await session.flush()
            user_a = User(
                organization_id=org_a.id,
                role_id=role.id,
                email=f"{uuid.uuid4()}@example.com",
            )
            site_a = Site(organization_id=org_a.id, name="site-a")
            site_b = Site(organization_id=org_b.id, name="site-b")
            session.add_all([user_a, site_a, site_b])
            await session.commit()

        async with factory() as session:
            session.add(
                UserSiteAssignment(
                    user_id=user_a.id,
                    site_id=site_a.id,
                    organization_id=org_a.id,
                )
            )
            await session.commit()

        async with factory() as session:
            session.add(
                UserSiteAssignment(
                    user_id=user_a.id,
                    site_id=site_b.id,
                    organization_id=org_a.id,
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()
    finally:
        await engine.dispose()


def _redact_database_output(text: str) -> str:
    if POSTGRES_URL:
        return text.replace(POSTGRES_URL, "<database-url>")
    return text


async def _insert_case_variant_pair(
    engine,
) -> tuple[str, list[UUID], list[UUID], list[UUID]]:
    """Insert two users whose emails differ only by case. Returns a token and ids."""
    factory = async_sessionmaker(engine, expire_on_commit=False)
    token = uuid.uuid4().hex
    async with factory() as session:
        org = Organization(name=f"org-{uuid.uuid4()}")
        role = Role(name=f"role-{uuid.uuid4()}", description="email-index")
        session.add_all([org, role])
        await session.flush()
        first = User(
            organization_id=org.id,
            role_id=role.id,
            email=f"A.{token}@example.com",
            idp_subject=f"sub-a-{token}",
        )
        second = User(
            organization_id=org.id,
            role_id=role.id,
            email=f"a.{token}@example.com",
            idp_subject=f"sub-b-{token}",
        )
        session.add_all([first, second])
        await session.commit()
        return token, [first.id, second.id], [org.id], [role.id]


async def _delete_created(
    engine, user_ids: list[UUID], org_ids: list[UUID], role_ids: list[UUID]
) -> None:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        if user_ids:
            await session.execute(User.__table__.delete().where(User.id.in_(user_ids)))
        if org_ids:
            await session.execute(
                Organization.__table__.delete().where(Organization.id.in_(org_ids))
            )
        if role_ids:
            await session.execute(Role.__table__.delete().where(Role.id.in_(role_ids)))
        await session.commit()


def _postgres_engine():
    return create_async_engine(
        _async_url(),
        pool_pre_ping=True,
        connect_args={
            "statement_cache_size": 0,
            "timeout": 60,
            **(
                {"ssl": True}
                if "sslmode=" in POSTGRES_URL.lower() or "neon.tech" in POSTGRES_URL.lower()
                else {}
            ),
        },
    )


@pytest.mark.asyncio
async def test_postgres_email_lower_index_and_collision_guard() -> None:
    """Expression index rejects case variants and refuses to build over existing ones."""
    _alembic("upgrade", "head")
    _alembic("downgrade", "0004_sites_authz_cameras")
    engine = _postgres_engine()
    user_ids: list[UUID] = []
    org_ids: list[UUID] = []
    role_ids: list[UUID] = []
    try:
        token, user_ids, org_ids, role_ids = await _insert_case_variant_pair(engine)
        completed = _alembic_captured("upgrade", "head")
        output = _redact_database_output(completed.stderr + completed.stdout).replace(
            token, "<token>"
        )
        assert completed.returncode != 0, output
        assert "collision group" in output
        assert token not in output
        await _delete_created(engine, user_ids, org_ids, role_ids)
        user_ids, org_ids, role_ids = [], [], []
        _alembic("upgrade", "head")
        async with engine.connect() as connection:
            indexdef = await connection.scalar(
                text(
                    "SELECT indexdef FROM pg_indexes "
                    "WHERE indexname = 'uq_users_email_lower'"
                )
            )
        assert indexdef is not None
        compact = "".join(str(indexdef).lower().split())
        assert "createuniqueindex" in compact
        assert "lower(" in compact and "email" in compact

        keep = uuid.uuid4().hex
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            org = Organization(name=f"org-{uuid.uuid4()}")
            role = Role(name=f"role-{uuid.uuid4()}", description="email-index")
            session.add_all([org, role])
            await session.flush()
            org_ids = [org.id]
            role_ids = [role.id]
            kept = User(
                organization_id=org.id,
                role_id=role.id,
                email=f"A.{keep}@example.com",
                idp_subject=f"sub-keep-{keep}",
            )
            session.add(kept)
            await session.commit()
            user_ids = [kept.id]
        async with factory() as session:
            session.add(
                User(
                    organization_id=org_ids[0],
                    role_id=role_ids[0],
                    email=f"a.{keep}@example.com",
                    idp_subject=f"sub-reject-{keep}",
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()
    finally:
        await _delete_created(engine, user_ids, org_ids, role_ids)
        await engine.dispose()
        _alembic("upgrade", "head")


def test_ready_against_postgres() -> None:
    _alembic("upgrade", "head")
    os.environ["DATABASE_URL"] = POSTGRES_URL
    os.environ["ENVIRONMENT"] = "development"
    get_settings.cache_clear()
    application = create_app()
    try:
        with TestClient(application) as client:
            response = client.get("/ready")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ready"
        assert body["database"] == "ok"
    finally:
        os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
        os.environ["ENVIRONMENT"] = "testing"
        get_settings.cache_clear()
