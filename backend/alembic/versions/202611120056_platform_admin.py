"""Add platform grants, audit events, and password session provenance."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202611120056"
down_revision = "202611120055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.add_column("auth_sessions", sa.Column("authenticated_via", sa.String(16)))
    op.create_check_constraint(
        "auth_session_authenticated_via", "auth_sessions",
        "authenticated_via IS NULL OR authenticated_via = 'PASSWORD'",
    )
    op.create_table(
        "platform_operator_grants",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("role", sa.String(24), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint("role IN ('PLATFORM_ADMIN', 'PLATFORM_SUPPORT', 'PLATFORM_AUDITOR')", name="platform_role"),
    )
    op.create_table(
        "platform_audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_role", sa.String(24)),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("outcome", sa.String(12), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_role", sa.String(24)),
        sa.Column("approval_ref", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_platform_audit_action_created", "platform_audit_events", ["action", "created_at"])
    op.create_index("ix_platform_audit_actor_created", "platform_audit_events", ["actor_user_id", "created_at"])
    op.create_index("ix_platform_workspaces_created_id", "workspaces", ["created_at", "id"])
    for table in ("platform_operator_grants", "platform_audit_events"):
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
    op.execute("""
        CREATE FUNCTION public.reject_platform_audit_change() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
            RAISE EXCEPTION 'Platform audit events are append-only';
        END; $$
    """)
    op.execute("""
        CREATE TRIGGER platform_audit_append_only
        BEFORE UPDATE OR DELETE OR TRUNCATE ON public.platform_audit_events
        FOR EACH STATEMENT EXECUTE FUNCTION public.reject_platform_audit_change()
    """)


def downgrade() -> None:
    bind = op.get_bind()
    op.execute("LOCK TABLE public.platform_operator_grants, public.platform_audit_events IN ACCESS EXCLUSIVE MODE")
    if bind.execute(sa.text("""
        SELECT EXISTS (SELECT 1 FROM public.platform_operator_grants)
            OR EXISTS (SELECT 1 FROM public.platform_audit_events)
    """)).scalar_one():
        raise RuntimeError("Platform records exist; disable the feature for data-preserving rollback")
    op.drop_index("ix_platform_workspaces_created_id", table_name="workspaces")
    op.drop_table("platform_audit_events")
    op.execute("DROP FUNCTION public.reject_platform_audit_change()")
    op.drop_table("platform_operator_grants")
    op.drop_constraint("auth_session_authenticated_via", "auth_sessions", type_="check")
    op.drop_column("auth_sessions", "authenticated_via")
