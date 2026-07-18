"""add order fulfillment operation journal

Revision ID: 202607180025
Revises: 202607160024
Create Date: 2026-07-18 00:25:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "202607180025"
down_revision: str | None = "202607160024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACTIVE_STATES = (
    "PENDING",
    "VALIDATING",
    "RESERVING_STOCK",
    "STOCK_RESERVED",
    "CREATING_SHIPMENT",
    "SHIPMENT_READY",
    "PROVIDER_REQUESTING",
    "PROVIDER_RESULT_RECEIVED",
    "PERSISTING_RESULT",
    "RECONCILIATION_REQUIRED",
    "RECONCILING",
)


def upgrade() -> None:
    op.create_table(
        "order_fulfillment_operations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("nova_poshta_operation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("operation_type", sa.String(length=40), nullable=False, server_default="ORDER_SHIPMENT_TTN"),
        sa.Column("state", sa.String(length=40), nullable=False, server_default="PENDING"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("provider_document_ref", sa.String(length=120), nullable=True),
        sa.Column("provider_document_number", sa.String(length=120), nullable=True),
        sa.Column("reservation_applied", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("shipment_created", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("provider_request_started", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("provider_result_received", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("local_persistence_completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("manual_reconciliation_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("blind_retry_blocked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("safe_error_code", sa.String(length=120), nullable=True),
        sa.Column("safe_error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["nova_poshta_operation_id"], ["nova_poshta_operations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "idempotency_key", name="uq_order_fulfillment_operations_workspace_idempotency_key"),
    )
    op.create_index("ix_order_fulfillment_operations_workspace_order", "order_fulfillment_operations", ["workspace_id", "order_id"], unique=False)
    op.create_index("ix_order_fulfillment_operations_workspace_state", "order_fulfillment_operations", ["workspace_id", "state"], unique=False)
    op.create_index("ix_order_fulfillment_operations_workspace_provider_ref", "order_fulfillment_operations", ["workspace_id", "provider_document_ref"], unique=False)
    op.create_index("ix_order_fulfillment_operations_workspace_provider_number", "order_fulfillment_operations", ["workspace_id", "provider_document_number"], unique=False)
    op.create_index(
        "uq_order_fulfillment_operations_one_active_per_order",
        "order_fulfillment_operations",
        ["workspace_id", "order_id"],
        unique=True,
        postgresql_where=sa.text("state IN ('" + "','".join(ACTIVE_STATES) + "')"),
    )
    op.create_index(
        "uq_order_fulfillment_operations_completed_fingerprint",
        "order_fulfillment_operations",
        ["workspace_id", "order_id", "request_fingerprint"],
        unique=True,
        postgresql_where=sa.text("state = 'COMPLETED'"),
    )
    op.execute('ALTER TABLE IF EXISTS public."order_fulfillment_operations" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    op.drop_index("uq_order_fulfillment_operations_completed_fingerprint", table_name="order_fulfillment_operations")
    op.drop_index("uq_order_fulfillment_operations_one_active_per_order", table_name="order_fulfillment_operations")
    op.drop_index("ix_order_fulfillment_operations_workspace_provider_number", table_name="order_fulfillment_operations")
    op.drop_index("ix_order_fulfillment_operations_workspace_provider_ref", table_name="order_fulfillment_operations")
    op.drop_index("ix_order_fulfillment_operations_workspace_state", table_name="order_fulfillment_operations")
    op.drop_index("ix_order_fulfillment_operations_workspace_order", table_name="order_fulfillment_operations")
    op.drop_table("order_fulfillment_operations")
