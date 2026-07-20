"""add Instagram inbox history and message state sync

Revision ID: 202607200032
Revises: 202607200031
Create Date: 2026-07-20 12:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "202607200032"
down_revision: str | None = "202607200031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def uuid(name: str, nullable: bool = False):
    return sa.Column(name, postgresql.UUID(as_uuid=True), nullable=nullable)


def timestamps():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "instagram_history_syncs",
        uuid("id"),
        uuid("workspace_id"),
        uuid("instagram_connection_id"),
        sa.Column("status", sa.String(40), server_default="PENDING", nullable=False),
        uuid("requested_by", True),
        sa.Column("conversation_cursor", sa.Text(), nullable=True),
        sa.Column("conversation_limit", sa.Integer(), server_default="100", nullable=False),
        sa.Column("messages_per_conversation", sa.Integer(), server_default="20", nullable=False),
        sa.Column("conversation_pages_processed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("conversations_discovered", sa.Integer(), server_default="0", nullable=False),
        sa.Column("conversations_synced", sa.Integer(), server_default="0", nullable=False),
        sa.Column("messages_discovered", sa.Integer(), server_default="0", nullable=False),
        sa.Column("messages_imported", sa.Integer(), server_default="0", nullable=False),
        sa.Column("messages_existing", sa.Integer(), server_default="0", nullable=False),
        sa.Column("messages_unavailable", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rate_limit_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error_code", sa.String(120), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["instagram_connection_id"], ["instagram_connections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "instagram_connection_id",
            name="uq_instagram_history_syncs_workspace_connection",
        ),
        sa.CheckConstraint(
            "status in ('PENDING','RUNNING','COMPLETED','PARTIAL','RETRY_PENDING','FAILED_SAFE')",
            name="ck_instagram_history_syncs_status",
        ),
        sa.CheckConstraint("conversation_limit between 1 and 500", name="ck_instagram_history_syncs_conversation_limit"),
        sa.CheckConstraint("messages_per_conversation between 1 and 20", name="ck_instagram_history_syncs_message_limit"),
    )
    op.create_index(
        "ix_instagram_history_syncs_status_retry",
        "instagram_history_syncs",
        ["status", "next_retry_at"],
    )

    op.create_table(
        "instagram_message_states",
        uuid("id"),
        uuid("workspace_id"),
        uuid("direct_message_id"),
        sa.Column("provider_message_id", sa.String(180), nullable=False),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("edit_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("reaction", sa.String(80), nullable=True),
        sa.Column("reaction_actor_scoped_id", sa.String(180), nullable=True),
        sa.Column("reaction_updated_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["direct_message_id"], ["direct_messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "direct_message_id",
            name="uq_instagram_message_states_workspace_message",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "provider_message_id",
            name="uq_instagram_message_states_workspace_provider_message",
        ),
        sa.CheckConstraint("edit_count >= 0", name="ck_instagram_message_states_edit_count_nonnegative"),
    )
    op.create_index(
        "ix_instagram_message_states_provider_message",
        "instagram_message_states",
        ["workspace_id", "provider_message_id"],
    )

    for table in ["instagram_history_syncs", "instagram_message_states"]:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("ix_instagram_message_states_provider_message", table_name="instagram_message_states")
    op.drop_table("instagram_message_states")
    op.drop_index("ix_instagram_history_syncs_status_retry", table_name="instagram_history_syncs")
    op.drop_table("instagram_history_syncs")
