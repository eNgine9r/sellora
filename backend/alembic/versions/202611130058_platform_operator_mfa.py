"""Store platform operator factors and session-bound MFA proofs."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "202611130058"
down_revision = "202611120057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.create_table(
        "platform_operator_mfa",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("encrypted_seed", sa.LargeBinary(), nullable=False),
        sa.Column("last_step", sa.BigInteger(), nullable=False),
        sa.Column("failure_count", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("window_started_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["user_id"], ["platform_operator_grants.user_id"], ondelete="CASCADE"),
    )
    op.add_column("auth_sessions", sa.Column("platform_mfa_digest", sa.LargeBinary()))
    op.add_column("auth_sessions", sa.Column("platform_mfa_expires_at", sa.DateTime(timezone=True)))
    op.execute("ALTER TABLE public.platform_operator_mfa ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON public.platform_operator_mfa FROM PUBLIC")
    for role in ("anon", "authenticated"):
        op.execute(f"""
            DO $$ BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                    REVOKE ALL ON public.platform_operator_mfa FROM {role};
                END IF;
            END $$
        """)


def downgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute("LOCK TABLE public.platform_operator_mfa IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM public.platform_operator_mfa)")):
        raise RuntimeError("Platform factors exist; preserve the schema during rollback")
    op.drop_column("auth_sessions", "platform_mfa_expires_at")
    op.drop_column("auth_sessions", "platform_mfa_digest")
    op.drop_table("platform_operator_mfa")
