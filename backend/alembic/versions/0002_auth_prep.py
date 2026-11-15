"""idp_subject and tenant indexes

Revision ID: 0002_auth_prep
Revises: 0001_foundation
Create Date: 2026-08-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_auth_prep"
down_revision: Union[str, None] = "0001_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("idp_subject", sa.String(length=320), nullable=True))
    op.create_unique_constraint("uq_users_idp_subject", "users", ["idp_subject"])
    op.create_index("ix_users_organization_id", "users", ["organization_id"])
    op.create_index("ix_sites_organization_id", "sites", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_sites_organization_id", table_name="sites")
    op.drop_index("ix_users_organization_id", table_name="users")
    op.drop_constraint("uq_users_idp_subject", "users", type_="unique")
    op.drop_column("users", "idp_subject")
