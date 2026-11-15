"""case-insensitive unique index on users.email

Revision ID: 0005_users_email_lower_unique
Revises: 0004_sites_authz_cameras
Create Date: 2026-10-15

Does not delete or merge user rows. If lower(email) collides, upgrade aborts.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_users_email_lower_unique"
down_revision: str | None = "0004_sites_authz_cameras"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def case_insensitive_email_collision_groups(connection: sa.Connection) -> int:
    """Count collision groups only. Do not select email addresses."""
    count = connection.execute(
        sa.text(
            "SELECT count(*) FROM ("
            "SELECT 1 FROM users GROUP BY lower(email) HAVING count(*) > 1"
            ") AS email_collisions"
        )
    ).scalar_one()
    return int(count or 0)


def upgrade() -> None:
    connection = op.get_bind()
    collisions = case_insensitive_email_collision_groups(connection)
    if collisions:
        raise RuntimeError(
            "uq_users_email_lower was not created: "
            f"{collisions} case-insensitive email collision group(s) exist. "
            "This migration does not delete or merge users. "
            "An administrator must resolve the duplicate accounts, then rerun the upgrade."
        )
    op.create_index(
        "uq_users_email_lower",
        "users",
        [sa.literal_column("lower(email)")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_users_email_lower", table_name="users")
