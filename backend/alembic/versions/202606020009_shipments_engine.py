"""shipments engine

Revision ID: 202606020009
Revises: 202606020008
Create Date: 2026-06-03 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202606020009"
down_revision = "202606020008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shipments",
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tracking_number", sa.String(length=120), nullable=True),
        sa.Column("carrier", sa.String(length=40), nullable=False, server_default="NOVA_POSHTA"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="DRAFT"),
        sa.Column("recipient_name", sa.String(length=255), nullable=True),
        sa.Column("recipient_phone", sa.String(length=80), nullable=True),
        sa.Column("city", sa.String(length=255), nullable=True),
        sa.Column("warehouse", sa.String(length=255), nullable=True),
        sa.Column("shipping_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("cod_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("declared_value", sa.Numeric(12, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("carrier IN ('NOVA_POSHTA', 'UKRPOSHTA', 'MEEST', 'ROZETKA_DELIVERY', 'OTHER')", name="shipments_carrier_allowed"),
        sa.CheckConstraint("status IN ('DRAFT', 'CREATED', 'IN_TRANSIT', 'ARRIVED', 'DELIVERED', 'RETURNED', 'CANCELLED')", name="shipments_status_allowed"),
        sa.CheckConstraint("shipping_cost IS NULL OR shipping_cost >= 0", name="shipments_shipping_cost_non_negative"),
        sa.CheckConstraint("cod_amount IS NULL OR cod_amount >= 0", name="shipments_cod_amount_non_negative"),
        sa.CheckConstraint("declared_value IS NULL OR declared_value >= 0", name="shipments_declared_value_non_negative"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shipments_workspace_id", "shipments", ["workspace_id"])
    op.create_index("ix_shipments_order_id", "shipments", ["order_id"])
    op.create_index("ix_shipments_customer_id", "shipments", ["customer_id"])
    op.create_index("ix_shipments_status", "shipments", ["status"])
    op.create_index("uq_shipments_workspace_tracking_number", "shipments", ["workspace_id", "tracking_number"], unique=True, postgresql_where=sa.text("tracking_number IS NOT NULL"))
    op.create_index("uq_shipments_workspace_active_order", "shipments", ["workspace_id", "order_id"], unique=True, postgresql_where=sa.text("deleted_at IS NULL AND status != 'CANCELLED'"))


def downgrade() -> None:
    op.drop_index("uq_shipments_workspace_active_order", table_name="shipments")
    op.drop_index("uq_shipments_workspace_tracking_number", table_name="shipments")
    op.drop_index("ix_shipments_status", table_name="shipments")
    op.drop_index("ix_shipments_customer_id", table_name="shipments")
    op.drop_index("ix_shipments_order_id", table_name="shipments")
    op.drop_index("ix_shipments_workspace_id", table_name="shipments")
    op.drop_table("shipments")
