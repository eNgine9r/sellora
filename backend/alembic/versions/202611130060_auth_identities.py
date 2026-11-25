"""Store Sellora sign-in identities and bounded email verification challenges."""

import sqlalchemy as sa
from alembic import op

revision = "202611130060"
down_revision = "202611130059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.alter_column("users", "password_hash", nullable=True)
    op.create_index("ix_users_email_lower", "users", [sa.text("lower(email)")])
    op.create_table(
        "auth_identities",
        sa.Column("provider", sa.String(16), primary_key=True),
        sa.Column("subject", sa.String(255), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("user_id", "provider"),
    )
    op.create_table(
        "auth_email_challenges",
        sa.Column("email_key", sa.String(64), primary_key=True),
        sa.Column("digest", sa.String(64)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resend_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sends", sa.SmallInteger(), nullable=False),
        sa.Column("attempts", sa.SmallInteger(), nullable=False),
    )
    op.create_index("ix_auth_email_challenges_window_ends_at", "auth_email_challenges", ["window_ends_at"])
    for table in ("auth_identities", "auth_email_challenges"):
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON TABLE public.{table} FROM PUBLIC")
        for role in ("anon", "authenticated"):
            op.execute(f"""
                DO $$ BEGIN
                    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                        REVOKE ALL ON TABLE public.{table} FROM {role};
                    END IF;
                END $$
            """)


def downgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute("LOCK TABLE public.users, public.auth_identities IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM public.auth_identities) OR "
                                  "EXISTS (SELECT 1 FROM public.users WHERE password_hash IS NULL)")):
        raise RuntimeError("Sellora sign-in identities exist; preserve their schema during rollback")
    op.drop_table("auth_email_challenges")
    op.drop_table("auth_identities")
    op.drop_index("ix_users_email_lower", table_name="users")
    op.alter_column("users", "password_hash", nullable=False)
