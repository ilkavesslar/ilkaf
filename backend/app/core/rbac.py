"""RBAC names, permission map, and tenant-scope helpers.

Authentication is implemented in ``app.core.auth`` / ``app.core.security``.
This module answers authorization questions for an already-authenticated Principal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID

from fastapi import HTTPException, status


class RoleName(StrEnum):
    """Canonical ILKA roles. SYSTEM_ADMIN is the Sprint 2 ADMIN capability."""

    SYSTEM_ADMIN = "SYSTEM_ADMIN"
    ORG_ADMIN = "ORG_ADMIN"
    SITE_MANAGER = "SITE_MANAGER"
    SAFETY_OFFICER = "SAFETY_OFFICER"
    OPERATOR = "OPERATOR"
    VIEWER = "VIEWER"


ADMIN_ROLE = RoleName.SYSTEM_ADMIN


class Permission(StrEnum):
    SITES_READ = "sites:read"
    SITES_CREATE = "sites:create"
    SITES_UPDATE = "sites:update"
    SITES_DELETE = "sites:delete"
    USERS_READ = "users:read"
    USERS_MANAGE = "users:manage"
    CAMERAS_READ = "cameras:read"
    CAMERAS_CREATE = "cameras:create"
    CAMERAS_UPDATE = "cameras:update"
    CAMERAS_DELETE = "cameras:delete"
    SAFETY_READ = "safety:read"
    SAFETY_MANAGE = "safety:manage"


_LEGACY_PERMISSIONS = {
    "site.read": Permission.SITES_READ,
    "site.write": Permission.SITES_UPDATE,
    "org.read": Permission.USERS_READ,
    "org.write": Permission.USERS_MANAGE,
    "user.read": Permission.USERS_READ,
    "camera.read": Permission.CAMERAS_READ,
    "camera.write": Permission.CAMERAS_UPDATE,
    "incident.read": Permission.SAFETY_READ,
    "incident.verify": Permission.SAFETY_MANAGE,
    "incident.ack": Permission.SAFETY_READ,
}


PERMISSIONS: dict[RoleName, frozenset[str]] = {
    RoleName.SYSTEM_ADMIN: frozenset({"*"}),
    RoleName.ORG_ADMIN: frozenset(
        {
            Permission.SITES_READ,
            Permission.SITES_CREATE,
            Permission.SITES_UPDATE,
            Permission.SITES_DELETE,
            Permission.USERS_READ,
            Permission.USERS_MANAGE,
            Permission.CAMERAS_READ,
            Permission.CAMERAS_CREATE,
            Permission.CAMERAS_UPDATE,
            Permission.CAMERAS_DELETE,
            Permission.SAFETY_READ,
            Permission.SAFETY_MANAGE,
        }
    ),
    RoleName.SITE_MANAGER: frozenset(
        {
            Permission.SITES_READ,
            Permission.SITES_UPDATE,
            Permission.USERS_READ,
            Permission.CAMERAS_READ,
            Permission.CAMERAS_CREATE,
            Permission.CAMERAS_UPDATE,
            Permission.CAMERAS_DELETE,
            Permission.SAFETY_READ,
        }
    ),
    RoleName.SAFETY_OFFICER: frozenset(
        {
            Permission.SITES_READ,
            Permission.CAMERAS_READ,
            Permission.SAFETY_READ,
            Permission.SAFETY_MANAGE,
        }
    ),
    RoleName.OPERATOR: frozenset(
        {
            Permission.SITES_READ,
            Permission.CAMERAS_READ,
            Permission.SAFETY_READ,
        }
    ),
    RoleName.VIEWER: frozenset(
        {
            Permission.SITES_READ,
            Permission.CAMERAS_READ,
        }
    ),
}

ORG_WIDE_ROLES = frozenset({RoleName.SYSTEM_ADMIN, RoleName.ORG_ADMIN})


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    organization_id: UUID
    role: RoleName
    email: str = ""
    display_name: str = ""
    site_ids: frozenset[UUID] = field(default_factory=frozenset)
    site_roles: tuple[tuple[UUID, RoleName], ...] = ()


def canonicalize_permission(permission: str) -> str:
    return _LEGACY_PERMISSIONS.get(permission, permission)


def has_permission_for_role(role: RoleName, permission: str) -> bool:
    granted = PERMISSIONS[role]
    needed = canonicalize_permission(permission)
    return "*" in granted or needed in granted or permission in granted


def effective_role(principal: Principal, site_id: UUID | None = None) -> RoleName:
    if principal.role in ORG_WIDE_ROLES:
        return principal.role
    if site_id is None:
        return principal.role
    for assigned_site, assigned_role in principal.site_roles:
        if assigned_site == site_id:
            return assigned_role
    return principal.role


def has_permission(principal: Principal, permission: str, site_id: UUID | None = None) -> bool:
    return has_permission_for_role(effective_role(principal, site_id), permission)


def require_permission(principal: Principal, permission: str, site_id: UUID | None = None) -> None:
    if not has_permission(principal, permission, site_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


def require_organization(principal: Principal, organization_id: UUID) -> None:
    if principal.role == RoleName.SYSTEM_ADMIN:
        return
    if principal.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="cross-tenant access denied"
        )


def has_site_access(principal: Principal, organization_id: UUID, site_id: UUID) -> bool:
    if principal.role == RoleName.SYSTEM_ADMIN:
        return True
    if principal.organization_id != organization_id:
        return False
    if principal.role == RoleName.ORG_ADMIN:
        return True
    return site_id in principal.site_ids


def require_site(principal: Principal, organization_id: UUID, site_id: UUID) -> None:
    require_organization(principal, organization_id)
    if principal.role in ORG_WIDE_ROLES:
        return
    if site_id not in principal.site_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="site access denied")


def require_role(principal: Principal, *roles: RoleName) -> None:
    if principal.role not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
