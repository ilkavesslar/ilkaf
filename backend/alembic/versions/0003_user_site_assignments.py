"""user ↔ site assignments with organization isolation

Revision ID: 0003_user_site_assignments
Revises: 0002_auth_prep
Create Date: 2026-08-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_user_site_assignments"
down_revision: Union[str, None] = "0002_auth_prep"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint("uq_users_id_organization_id", "users", ["id", "organization_id"])
    op.create_unique_constraint("uq_sites_id_organization_id", "sites", ["id", "organization_id"])
    op.create_table(
        "user_site_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "site_id", name="uq_user_site_assignments_user_site"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_user_site_assignments_organization_id",
        ),
        sa.ForeignKeyConstraint(
            ["user_id", "organization_id"],
            ["users.id", "users.organization_id"],
            name="fk_user_site_assignments_user_org",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["site_id", "organization_id"],
            ["sites.id", "sites.organization_id"],
            name="fk_user_site_assignments_site_org",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_user_site_assignments_organization_id",
        "user_site_assignments",
        ["organization_id"],
    )
    op.create_index("ix_user_site_assignments_user_id", "user_site_assignments", ["user_id"])
    op.create_index("ix_user_site_assignments_site_id", "user_site_assignments", ["site_id"])


def downgrade() -> None:
    op.drop_index("ix_user_site_assignments_site_id", table_name="user_site_assignments")
    op.drop_index("ix_user_site_assignments_user_id", table_name="user_site_assignments")
    op.drop_index("ix_user_site_assignments_organization_id", table_name="user_site_assignments")
    op.drop_table("user_site_assignments")
    op.drop_constraint("uq_sites_id_organization_id", "sites", type_="unique")
    op.drop_constraint("uq_users_id_organization_id", "users", type_="unique")
