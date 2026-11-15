import uuid

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Base, Organization, Role, Site, User, UserSiteAssignment


@pytest.mark.asyncio
async def test_user_site_assignment_constraints() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(engine.sync_engine, "connect")
    def _fk(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    org_a = Organization(name=f"org-a-{uuid.uuid4()}")
    org_b = Organization(name=f"org-b-{uuid.uuid4()}")
    role = Role(name=f"role-{uuid.uuid4()}", description="test")

    try:
        async with factory() as session:
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
                    site_id=site_a.id,
                    organization_id=org_a.id,
                )
            )
            with pytest.raises(IntegrityError):
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

        async with factory() as session:
            session.add(
                UserSiteAssignment(
                    user_id=user_a.id,
                    site_id=site_b.id,
                    organization_id=org_b.id,
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()
    finally:
        await engine.dispose()
