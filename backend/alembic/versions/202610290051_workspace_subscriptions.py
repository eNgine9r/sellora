"""Add an opt-in current subscription record without enrolling existing shops.

Revision ID: 202610290051
Revises: 202610280050
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202610290051"
down_revision = "202610280050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("SET LOCAL lock_timeout = '5s'")
    op.create_table(
        "workspace_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_code", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("workspace_id", name="uq_workspace_subscriptions_workspace_id"),
        sa.CheckConstraint("status IN ('PENDING','TRIALING','ACTIVE','PAST_DUE','CANCELED','EXPIRED')", name="subscription_status"),
        sa.CheckConstraint("current_period_end > current_period_start", name="subscription_period"),
        sa.CheckConstraint("length(trim(plan_code)) > 0", name="subscription_plan_code"),
        sa.CheckConstraint("NOT cancel_at_period_end OR status IN ('ACTIVE','TRIALING')", name="subscription_cancel_at_end"),
    )
    op.execute("ALTER TABLE public.workspace_subscriptions ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE public.workspace_subscriptions FROM PUBLIC")
    for role_name in ("anon", "authenticated"):
        op.execute(f"""DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role_name}') THEN
                REVOKE ALL PRIVILEGES ON TABLE public.workspace_subscriptions FROM "{role_name}";
            END IF;
        END $$""")


def downgrade() -> None:
    count = op.get_bind().execute(sa.text("SELECT count(*) FROM public.workspace_subscriptions")).scalar_one()
    if count:
        raise RuntimeError("Subscription records exist; rollback requires explicit data-preserving review")
    op.drop_table("workspace_subscriptions")
