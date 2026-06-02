"""orders and profit engine

Revision ID: 202606020005
Revises: 202606020004
Create Date: 2026-06-02 00:05:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202606020005"
down_revision: str | None = "202606020004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ORDER_STATUSES = "'NEW', 'CONFIRMED', 'SHIPPED', 'DELIVERED', 'COMPLETED', 'RETURNED', 'CANCELLED'"
PAYMENT_STATUSES = "'PENDING', 'PAID', 'COD', 'REFUNDED'"


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("order_number", sa.String(length=30), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="NEW", nullable=False),
        sa.Column("payment_status", sa.String(length=30), server_default="PENDING", nullable=False),
        sa.Column("revenue", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("product_cost", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("ad_cost", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("shipping_cost", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("cod_fee", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("other_cost", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("net_profit", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(f"status IN ({ORDER_STATUSES})", name="ck_orders_status"),
        sa.CheckConstraint(f"payment_status IN ({PAYMENT_STATUSES})", name="ck_orders_payment_status"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], name=op.f("fk_orders_customer_id_customers"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], name=op.f("fk_orders_deleted_by_users"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name=op.f("fk_orders_workspace_id_workspaces"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_orders")),
        sa.UniqueConstraint("order_number", name=op.f("uq_orders_order_number")),
    )
    op.create_index(op.f("ix_orders_order_number"), "orders", ["order_number"], unique=False)
    op.create_index(op.f("ix_orders_workspace_id"), "orders", ["workspace_id"], unique=False)
    op.create_index("ix_orders_workspace_id_created_at", "orders", ["workspace_id", "created_at"], unique=False)

    op.create_table(
        "order_items",
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_variant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku", sa.String(length=120), nullable=False),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit_cost", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_cost", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], name=op.f("fk_order_items_deleted_by_users"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], name=op.f("fk_order_items_order_id_orders"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_variant_id"], ["product_variants.id"], name=op.f("fk_order_items_product_variant_id_product_variants"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name=op.f("fk_order_items_workspace_id_workspaces"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_items")),
    )
    op.create_index(op.f("ix_order_items_workspace_id"), "order_items", ["workspace_id"], unique=False)

    op.create_table(
        "order_status_history",
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_status", sa.String(length=30), nullable=True),
        sa.Column("to_status", sa.String(length=30), nullable=False),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(f"to_status IN ({ORDER_STATUSES})", name="ck_order_status_history_to_status"),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], name=op.f("fk_order_status_history_changed_by_users"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], name=op.f("fk_order_status_history_deleted_by_users"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], name=op.f("fk_order_status_history_order_id_orders"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name=op.f("fk_order_status_history_workspace_id_workspaces"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_status_history")),
    )
    op.create_index(op.f("ix_order_status_history_workspace_id"), "order_status_history", ["workspace_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_order_status_history_workspace_id"), table_name="order_status_history")
    op.drop_table("order_status_history")
    op.drop_index(op.f("ix_order_items_workspace_id"), table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_workspace_id_created_at", table_name="orders")
    op.drop_index(op.f("ix_orders_workspace_id"), table_name="orders")
    op.drop_index(op.f("ix_orders_order_number"), table_name="orders")
    op.drop_table("orders")
