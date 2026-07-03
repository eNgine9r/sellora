"""create meta ad connections

Revision ID: 202607030018
Revises: 202607020017
Create Date: 2026-07-03 00:18:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202607030018"
down_revision: str | None = "202607020017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "meta_ad_connections",
        sa.Column("provider", sa.String(length=40), nullable=False, server_default="meta_ads"),
        sa.Column("connection_status", sa.String(length=40), nullable=False, server_default="NOT_CONNECTED"),
        sa.Column("external_business_id", sa.String(length=120), nullable=True),
        sa.Column("external_ad_account_id", sa.String(length=120), nullable=True),
        sa.Column("account_name", sa.String(length=255), nullable=True),
        sa.Column("currency", sa.String(length=12), nullable=True),
        sa.Column("timezone", sa.String(length=80), nullable=True),
        sa.Column("encrypted_access_token", sa.Text(), nullable=True),
        sa.Column("token_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scopes", sa.Text(), nullable=True),
        sa.Column("connected_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disconnected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=80), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connected_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_meta_ad_connections_workspace_id", "meta_ad_connections", ["workspace_id"], unique=False)
    op.create_index("ix_meta_ad_connections_connection_status", "meta_ad_connections", ["connection_status"], unique=False)
    op.create_index("ix_meta_ad_connections_external_ad_account_id", "meta_ad_connections", ["external_ad_account_id"], unique=False)
    op.create_index("ix_meta_ad_connections_workspace_status", "meta_ad_connections", ["workspace_id", "connection_status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_meta_ad_connections_workspace_status", table_name="meta_ad_connections")
    op.drop_index("ix_meta_ad_connections_external_ad_account_id", table_name="meta_ad_connections")
    op.drop_index("ix_meta_ad_connections_connection_status", table_name="meta_ad_connections")
    op.drop_index("ix_meta_ad_connections_workspace_id", table_name="meta_ad_connections")
    op.drop_table("meta_ad_connections")
