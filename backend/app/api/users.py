from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import Principal, RoleName
from app.core.security import get_current_principal
from app.db.database import get_db_session
from app.models import Site
from app.schemas.sites import MeResponse, SiteSummary

router = APIRouter(
    tags=["identity"],
    dependencies=[Depends(get_current_principal)],
)


@router.get("/me", response_model=MeResponse)
async def read_me(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> MeResponse:
    if principal.role == RoleName.SYSTEM_ADMIN:
        query = select(Site)
    elif principal.role == RoleName.ORG_ADMIN:
        query = select(Site).where(Site.organization_id == principal.organization_id)
    elif principal.site_ids:
        query = select(Site).where(Site.id.in_(principal.site_ids))
    else:
        query = None

    sites: list[SiteSummary] = []
    if query is not None:
        rows = (await session.scalars(query)).all()
        role_by_site = dict(principal.site_roles)
        for site in sorted(rows, key=lambda item: item.name):
            assigned = role_by_site.get(site.id, principal.role)
            sites.append(
                SiteSummary(
                    id=site.id,
                    name=site.name,
                    code=site.code,
                    role=assigned.value,
                )
            )

    roles = [principal.role.value]
    extra = {role.value for _, role in principal.site_roles}
    for name in sorted(extra):
        if name not in roles:
            roles.append(name)

    return MeResponse(
        id=principal.user_id,
        email=principal.email,
        name=principal.display_name,
        roles=roles,
        sites=sites,
    )
