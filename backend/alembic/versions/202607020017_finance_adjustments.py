"""finance adjustments

Revision ID: 202607020017
Revises: 202607010016
Create Date: 2026-07-02 00:17:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202607020017"
down_revision: str | None = "202607010016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "finance_adjustments",
        sa.Column("type", sa.String(length=40), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="UAH"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False, server_default="MANUAL"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_finance_adjustments_amount_positive"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_finance_adjustments_workspace_id", "finance_adjustments", ["workspace_id"], unique=False)
    op.create_index("ix_finance_adjustments_occurred_at", "finance_adjustments", ["occurred_at"], unique=False)
    op.create_index("ix_finance_adjustments_type", "finance_adjustments", ["type"], unique=False)
    op.create_index("ix_finance_adjustments_category", "finance_adjustments", ["category"], unique=False)
    op.create_index("ix_finance_adjustments_order_id", "finance_adjustments", ["order_id"], unique=False)
    op.create_index("ix_finance_adjustments_workspace_occurred_at", "finance_adjustments", ["workspace_id", "occurred_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_finance_adjustments_workspace_occurred_at", table_name="finance_adjustments")
    op.drop_index("ix_finance_adjustments_order_id", table_name="finance_adjustments")
    op.drop_index("ix_finance_adjustments_category", table_name="finance_adjustments")
    op.drop_index("ix_finance_adjustments_type", table_name="finance_adjustments")
    op.drop_index("ix_finance_adjustments_occurred_at", table_name="finance_adjustments")
    op.drop_index("ix_finance_adjustments_workspace_id", table_name="finance_adjustments")
    op.drop_table("finance_adjustments")
