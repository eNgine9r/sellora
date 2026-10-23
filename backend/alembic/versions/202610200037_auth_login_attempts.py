"""Persist privacy-preserving login failure counters across Raspberry workers.

Revision ID: 202610200037
Revises: 202607220036

No customer data, messages, provider credentials, or existing sessions change.
"""

from alembic import op
import sqlalchemy as sa


revision = "202610200037"
down_revision = "202607220036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_login_attempts",
        sa.Column("identity_hash", sa.String(length=64), primary_key=True),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("reset_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("failure_count >= 0", name="failure_count_nonnegative"),
    )
    op.create_index("ix_auth_login_attempts_reset_at", "auth_login_attempts", ["reset_at"])
    # This table never needs to be exposed to Supabase Data API roles.
    op.execute("ALTER TABLE public.auth_login_attempts ENABLE ROW LEVEL SECURITY")
    for role_name in ("anon", "authenticated"):
        op.execute(f"""
            DO $$ BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role_name}') THEN
                    REVOKE ALL PRIVILEGES ON TABLE public.auth_login_attempts FROM "{role_name}";
                END IF;
            END $$
        """)


def downgrade() -> None:
    # Destructive session-security rollbacks must be deliberate and separately approved.
    raise RuntimeError("Do not automatically remove authentication controls")
