"""enforce unique connected Instagram account routing

Revision ID: 202607190030
Revises: 202607180029
Create Date: 2026-07-19 13:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "202607190030"
down_revision: str | None = "202607180029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_instagram_connections_connected_account",
        "instagram_connections",
        ["instagram_account_id"],
        unique=True,
        postgresql_where=sa.text(
            "instagram_account_id IS NOT NULL AND deleted_at IS NULL AND status = 'CONNECTED'"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_instagram_connections_connected_account",
        table_name="instagram_connections",
    )
