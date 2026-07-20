"""add Direct customer automation metadata

Revision ID: 202607200033
Revises: 202607200032
Create Date: 2026-07-20 14:30:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "202607200033"
down_revision: str | None = "202607200032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("instagram_scoped_id", sa.String(180), nullable=True))
    op.add_column("customers", sa.Column("source", sa.String(40), server_default="MANUAL", nullable=False))
    op.add_column("customers", sa.Column("lifecycle_status", sa.String(30), server_default="CUSTOMER", nullable=False))
    op.add_column("customers", sa.Column("profile_status", sa.String(30), server_default="INCOMPLETE", nullable=False))
    op.add_column(
        "customers",
        sa.Column("source_direct_conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_customers_source_direct_conversation_id",
        "customers",
        "direct_conversations",
        ["source_direct_conversation_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "uq_customers_workspace_instagram_scoped_id_active",
        "customers",
        ["workspace_id", "instagram_scoped_id"],
        unique=True,
        postgresql_where=sa.text("instagram_scoped_id IS NOT NULL AND deleted_at IS NULL"),
    )
    op.execute(
        """
        UPDATE customers
        SET profile_status = CASE
            WHEN phone IS NOT NULL AND city IS NOT NULL THEN 'COMPLETE'
            ELSE 'INCOMPLETE'
        END
        """
    )


def downgrade() -> None:
    op.drop_index("uq_customers_workspace_instagram_scoped_id_active", table_name="customers")
    op.drop_constraint("fk_customers_source_direct_conversation_id", "customers", type_="foreignkey")
    op.drop_column("customers", "source_direct_conversation_id")
    op.drop_column("customers", "profile_status")
    op.drop_column("customers", "lifecycle_status")
    op.drop_column("customers", "source")
    op.drop_column("customers", "instagram_scoped_id")
