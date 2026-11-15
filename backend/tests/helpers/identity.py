from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from app.core.rbac import RoleName
from app.models import Organization, Role, Site, User, UserSiteAssignment
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class IdentityWorld:
    org: Organization
    other_org: Organization
    roles: dict[str, Role]
    site_a: Site
    site_b: Site
    other_site: Site
    users: dict[str, User]
    sessions: dict[str, str] = field(default_factory=dict)


async def seed_roles(session: AsyncSession) -> dict[str, Role]:
    roles: dict[str, Role] = {}
    for name in RoleName:
        role = Role(name=name.value, description=name.value)
        session.add(role)
        roles[name.value] = role
    await session.flush()
    return roles


async def seed_identity_world(session: AsyncSession) -> IdentityWorld:
    roles = await seed_roles(session)
    org = Organization(name=f"org-{uuid4()}")
    other_org = Organization(name=f"org-{uuid4()}")
    session.add_all([org, other_org])
    await session.flush()

    site_a = Site(organization_id=org.id, name="Main Factory", code="MAIN")
    site_b = Site(organization_id=org.id, name="Warehouse", code="WHSE")
    other_site = Site(organization_id=other_org.id, name="Other Plant", code="OTHER")
    session.add_all([site_a, site_b, other_site])
    await session.flush()

    users: dict[str, User] = {}

    def add_user(key: str, role_name: str, email: str, subject: str) -> User:
        user = User(
            organization_id=org.id,
            role_id=roles[role_name].id,
            email=email,
            display_name=key.replace("_", " ").title(),
            idp_subject=subject,
        )
        session.add(user)
        users[key] = user
        return user

    add_user("SYSTEM_ADMIN", "SYSTEM_ADMIN", "admin@example.com", "sub-admin")
    add_user("ORG_ADMIN", "ORG_ADMIN", "orgadmin@example.com", "sub-org-admin")
    add_user("SITE_MANAGER", "SITE_MANAGER", "manager@example.com", "sub-manager")
    add_user("SAFETY_OFFICER", "SAFETY_OFFICER", "safety@example.com", "sub-safety")
    add_user("OPERATOR", "OPERATOR", "operator@example.com", "sub-operator")
    add_user("VIEWER", "VIEWER", "viewer@example.com", "sub-viewer")
    inactive = User(
        organization_id=org.id,
        role_id=roles["VIEWER"].id,
        email="inactive@example.com",
        display_name="Inactive",
        idp_subject="sub-inactive",
        disabled_at=datetime.now(UTC),
    )
    session.add(inactive)
    users["INACTIVE"] = inactive
    unbound = User(
        organization_id=org.id,
        role_id=roles["VIEWER"].id,
        email="unbound@example.com",
        display_name="Unbound",
        idp_subject=None,
    )
    session.add(unbound)
    users["UNBOUND"] = unbound
    await session.flush()

    for key in ("SITE_MANAGER", "SAFETY_OFFICER", "OPERATOR", "VIEWER"):
        session.add(
            UserSiteAssignment(
                user_id=users[key].id,
                site_id=site_a.id,
                organization_id=org.id,
                role_id=roles[key].id,
            )
        )
    session.add(
        UserSiteAssignment(
            user_id=unbound.id,
            site_id=site_a.id,
            organization_id=org.id,
            role_id=roles["VIEWER"].id,
        )
    )
    await session.flush()
    return IdentityWorld(
        org=org,
        other_org=other_org,
        roles=roles,
        site_a=site_a,
        site_b=site_b,
        other_site=other_site,
        users=users,
        sessions={},
    )
