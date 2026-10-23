"""Add revocable server-side sessions without touching legacy JWT authentication.

Revision ID: 202610200038
Revises: 202610200037
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op


revision = "202610200038"
down_revision = "202610200037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("refresh_hash", sa.String(64), nullable=False),
        sa.Column("previous_refresh_hash", sa.String(64), nullable=True),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rotation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint("rotation_count >= 0", name="auth_sessions_rotation_count"),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])
    op.execute("ALTER TABLE public.auth_sessions ENABLE ROW LEVEL SECURITY")
    for role_name in ("anon", "authenticated"):
        op.execute(f"""
            DO $$ BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role_name}') THEN
                    REVOKE ALL PRIVILEGES ON TABLE public.auth_sessions FROM "{role_name}";
                END IF;
            END $$
        """)


def downgrade() -> None:
    raise RuntimeError("Dropping live sessions is not an automated rollback; disable the feature flag instead.")
