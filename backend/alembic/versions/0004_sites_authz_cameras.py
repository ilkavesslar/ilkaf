"""site metadata, assignment roles, camera registry, canonical roles

Revision ID: 0004_sites_authz_cameras
Revises: 0003_user_site_assignments
Create Date: 2026-09-05
"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_sites_authz_cameras"
down_revision: Union[str, None] = "0003_user_site_assignments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ROLES = (
    ("SYSTEM_ADMIN", "Cross-tenant administration (Sprint 2 ADMIN)"),
    ("ORG_ADMIN", "Organization-wide administration"),
    ("SITE_MANAGER", "Manage assigned site resources"),
    ("SAFETY_OFFICER", "Safety monitoring within assigned sites"),
    ("OPERATOR", "Operational monitoring within assigned sites"),
    ("VIEWER", "Read-only access to authorized sites"),
)


def upgrade() -> None:
    op.add_column("users", sa.Column("display_name", sa.String(length=200), nullable=False, server_default=""))
    op.add_column(
        "users",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.add_column("sites", sa.Column("code", sa.String(length=64), nullable=True))
    op.add_column("sites", sa.Column("description", sa.String(length=1000), nullable=False, server_default=""))
    op.add_column("sites", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column(
        "sites",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sites_code", "sites", ["code"])
    op.create_unique_constraint("uq_sites_organization_code", "sites", ["organization_id", "code"])
    op.add_column("user_site_assignments", sa.Column("role_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_user_site_assignments_role_id",
        "user_site_assignments",
        "roles",
        ["role_id"],
        ["id"],
    )
    op.create_table(
        "cameras",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("location", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "code", name="uq_cameras_site_code"),
        sa.UniqueConstraint("id", "organization_id", name="uq_cameras_id_organization_id"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_cameras_organization_id",
        ),
        sa.ForeignKeyConstraint(
            ["site_id", "organization_id"],
            ["sites.id", "sites.organization_id"],
            name="fk_cameras_site_org",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'MAINTENANCE')",
            name="ck_cameras_status",
        ),
    )
    op.create_index("ix_cameras_organization_id", "cameras", ["organization_id"])
    op.create_index("ix_cameras_site_id", "cameras", ["site_id"])

    for name, description in _ROLES:
        op.execute(
            sa.text(
                """
                INSERT INTO roles (id, name, description)
                SELECT :id, :name, :description
                WHERE NOT EXISTS (SELECT 1 FROM roles WHERE name = :name)
                """
            ).bindparams(id=uuid.uuid4(), name=name, description=description)
        )


def downgrade() -> None:
    op.drop_index("ix_cameras_site_id", table_name="cameras")
    op.drop_index("ix_cameras_organization_id", table_name="cameras")
    op.drop_table("cameras")
    op.drop_constraint("fk_user_site_assignments_role_id", "user_site_assignments", type_="foreignkey")
    op.drop_column("user_site_assignments", "role_id")
    op.drop_constraint("uq_sites_organization_code", "sites", type_="unique")
    op.drop_index("ix_sites_code", table_name="sites")
    op.drop_column("sites", "updated_at")
    op.drop_column("sites", "is_active")
    op.drop_column("sites", "description")
    op.drop_column("sites", "code")
    op.drop_column("users", "updated_at")
    op.drop_column("users", "display_name")
