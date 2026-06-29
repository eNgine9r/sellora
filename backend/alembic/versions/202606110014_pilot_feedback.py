"""pilot feedback

Revision ID: 202606110014
Revises: 202606040013
Create Date: 2026-06-11 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202606110014"
down_revision = "202606040013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pilot_feedback",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("page_path", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], name=op.f("fk_pilot_feedback_deleted_by_users"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_pilot_feedback_user_id_users"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name=op.f("fk_pilot_feedback_workspace_id_workspaces"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pilot_feedback")),
    )
    op.create_index(op.f("ix_pilot_feedback_workspace_id"), "pilot_feedback", ["workspace_id"], unique=False)
    op.create_index("ix_pilot_feedback_workspace_status", "pilot_feedback", ["workspace_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_pilot_feedback_workspace_status", table_name="pilot_feedback")
    op.drop_index(op.f("ix_pilot_feedback_workspace_id"), table_name="pilot_feedback")
    op.drop_table("pilot_feedback")
