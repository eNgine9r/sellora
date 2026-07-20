"""add Instagram participant profile enrichment cache

Revision ID: 202607200031
Revises: 202607190030
Create Date: 2026-07-20 11:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "202607200031"
down_revision: str | None = "202607190030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "instagram_participant_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instagram_connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("participant_scoped_id", sa.String(length=180), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("username", sa.String(length=160), nullable=True),
        sa.Column("profile_picture_url", sa.Text(), nullable=True),
        sa.Column("profile_picture_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("follower_count", sa.Integer(), nullable=True),
        sa.Column("is_verified_user", sa.Boolean(), nullable=True),
        sa.Column("is_user_follow_business", sa.Boolean(), nullable=True),
        sa.Column("is_business_follow_user", sa.Boolean(), nullable=True),
        sa.Column("status", sa.String(length=40), server_default="PENDING", nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=120), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["direct_conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["instagram_connection_id"], ["instagram_connections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "conversation_id",
            name="uq_instagram_participant_profiles_workspace_conversation",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "instagram_connection_id",
            "participant_scoped_id",
            name="uq_instagram_participant_profiles_workspace_participant",
        ),
    )
    op.create_index(
        "ix_instagram_participant_profiles_workspace_status_retry",
        "instagram_participant_profiles",
        ["workspace_id", "status", "next_retry_at"],
    )
    op.create_index(
        "ix_instagram_participant_profiles_workspace_id",
        "instagram_participant_profiles",
        ["workspace_id"],
    )
    op.execute("ALTER TABLE instagram_participant_profiles ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index(
        "ix_instagram_participant_profiles_workspace_status_retry",
        table_name="instagram_participant_profiles",
    )
    op.drop_index(
        "ix_instagram_participant_profiles_workspace_id",
        table_name="instagram_participant_profiles",
    )
    op.drop_table("instagram_participant_profiles")
