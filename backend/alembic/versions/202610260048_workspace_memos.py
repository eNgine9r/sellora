"""Shared workspace notes and dated tasks for Calendar and Notes.

Revision ID: 202610260048
Revises: 202610260047
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202610260048"
down_revision = "202610260047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspace_memos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(8), nullable=False, server_default="NOTE"),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("due_on", sa.Date(), nullable=True),
        sa.Column("is_done", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint("kind IN ('NOTE','TASK')", name="kind"),
        sa.CheckConstraint("kind = 'TASK' OR (due_on IS NULL AND is_done = false)", name="note_task_fields"),
    )
    op.create_index("ix_workspace_memos_workspace_id", "workspace_memos", ["workspace_id"])
    op.create_index("ix_workspace_memos_active_due", "workspace_memos", ["workspace_id", "due_on"])
    op.execute("ALTER TABLE workspace_memos ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("ix_workspace_memos_active_due", table_name="workspace_memos")
    op.drop_index("ix_workspace_memos_workspace_id", table_name="workspace_memos")
    op.drop_table("workspace_memos")
