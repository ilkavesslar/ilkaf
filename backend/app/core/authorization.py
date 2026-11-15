"""Authorization FastAPI dependencies built on RBAC helpers."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status

from app.core.rbac import Permission, Principal, RoleName, require_permission, require_site
from app.core.security import get_current_principal


def require_authenticated_user() -> Callable[..., Principal]:
    return get_current_principal


def require_permission_dep(permission: str | Permission) -> Callable[..., Principal]:
    needed = permission.value if isinstance(permission, Permission) else permission

    async def _dependency(
        principal: Principal = Depends(get_current_principal),
    ) -> Principal:
        require_permission(principal, needed)
        return principal

    return _dependency


def require_role_dep(*roles: RoleName) -> Callable[..., Principal]:
    async def _dependency(
        principal: Principal = Depends(get_current_principal),
    ) -> Principal:
        if principal.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return principal

    return _dependency


def ensure_site_access(principal: Principal, organization_id: UUID, site_id: UUID) -> None:
    require_site(principal, organization_id, site_id)


def require_site_permission(
    principal: Principal,
    organization_id: UUID,
    site_id: UUID,
    permission: str | Permission,
) -> None:
    require_site(principal, organization_id, site_id)
    needed = permission.value if isinstance(permission, Permission) else permission
    require_permission(principal, needed, site_id)
