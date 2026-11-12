"""Add backend-only product usage events and per-workspace UTC daily counts."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "202611120057"
down_revision = "202611120056"
branch_labels = None
depends_on = None

EVENTS = "'workspace.activated', 'product.first_created', 'order.first_created', 'order.created', 'integration.used'"


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.create_table(
        "product_usage_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("source_key", sa.String(40), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "event_type", "source_key", name="uq_product_usage_event_source"),
        sa.CheckConstraint(f"event_type IN ({EVENTS})", name="event_type"),
        sa.CheckConstraint("source IN ('WORKSPACE', 'CATALOG', 'ORDERS', 'NOVA_POSHTA', 'META_ADS', 'INSTAGRAM')", name="source"),
        sa.CheckConstraint("schema_version > 0", name="schema_version"),
    )
    op.create_table(
        "product_usage_daily",
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("event_type", sa.String(32), primary_key=True),
        sa.Column("event_count", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(f"event_type IN ({EVENTS}, 'capture.dropped')", name="event_type"),
        sa.CheckConstraint("event_count > 0", name="event_count"),
    )
    op.create_index("ix_product_usage_daily_day", "product_usage_daily", ["day", "workspace_id"])
    for table in ("product_usage_events", "product_usage_daily"):
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
    op.execute("LOCK TABLE public.product_usage_events, public.product_usage_daily IN ACCESS EXCLUSIVE MODE")
    has_data = op.get_bind().execute(sa.text("""
        SELECT EXISTS (SELECT 1 FROM public.product_usage_events)
            OR EXISTS (SELECT 1 FROM public.product_usage_daily)
    """)).scalar_one()
    if has_data:
        raise RuntimeError("Product usage records exist; disable capture for a data-preserving rollback")
    op.drop_table("product_usage_daily")
    op.drop_table("product_usage_events")
