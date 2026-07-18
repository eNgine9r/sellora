"""consolidate order fulfillment journal

Revision ID: 202607180026
Revises: 202607180025
Create Date: 2026-07-18 00:26:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "202607180026"
down_revision: str | None = "202607180025"
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


def _active_state_sql() -> str:
    return "state IN ('" + "','".join(ACTIVE_STATES) + "')"


def upgrade() -> None:
    op.add_column("order_fulfillments", sa.Column("operation_type", sa.String(length=40), nullable=False, server_default="ORDER_SHIPMENT_TTN"))
    op.add_column("order_fulfillments", sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("order_fulfillments", sa.Column("provider_document_ref", sa.String(length=120), nullable=True))
    op.add_column("order_fulfillments", sa.Column("provider_document_number", sa.String(length=120), nullable=True))
    op.add_column("order_fulfillments", sa.Column("nova_poshta_operation_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("order_fulfillments", sa.Column("reservation_applied", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("order_fulfillments", sa.Column("reservation_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("order_fulfillments", sa.Column("shipment_created", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("order_fulfillments", sa.Column("provider_request_started", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("order_fulfillments", sa.Column("provider_result_received", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("order_fulfillments", sa.Column("local_persistence_completed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("order_fulfillments", sa.Column("manual_reconciliation_required", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("order_fulfillments", sa.Column("blind_retry_blocked", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("order_fulfillments", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("order_fulfillments", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("order_fulfillments", sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("order_fulfillments", sa.Column("last_reconciled_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key("fk_order_fulfillments_nova_poshta_operation_id", "order_fulfillments", "nova_poshta_operations", ["nova_poshta_operation_id"], ["id"], ondelete="SET NULL")

    op.execute(
        """
        UPDATE order_fulfillments
        SET state = CASE state
            WHEN 'PREPARED' THEN 'PENDING'
            WHEN 'FAILED_VALIDATION' THEN 'FAILED_SAFE'
            WHEN 'SHIPMENT_CREATED' THEN 'SHIPMENT_READY'
            ELSE state
        END,
        local_persistence_completed = CASE WHEN order_id IS NOT NULL AND shipment_id IS NOT NULL THEN true ELSE local_persistence_completed END,
        shipment_created = CASE WHEN shipment_id IS NOT NULL THEN true ELSE shipment_created END,
        completed_at = CASE WHEN state = 'COMPLETED' THEN COALESCE(completed_at, updated_at) ELSE completed_at END
        """
    )

    op.execute(
        """
        UPDATE order_fulfillments canonical
        SET
            order_id = COALESCE(canonical.order_id, duplicate.order_id),
            shipment_id = COALESCE(canonical.shipment_id, duplicate.shipment_id),
            nova_poshta_operation_id = COALESCE(canonical.nova_poshta_operation_id, duplicate.nova_poshta_operation_id),
            provider_document_ref = COALESCE(canonical.provider_document_ref, duplicate.provider_document_ref),
            provider_document_number = COALESCE(canonical.provider_document_number, duplicate.provider_document_number),
            tracking_number = COALESCE(canonical.tracking_number, duplicate.provider_document_number),
            reservation_applied = canonical.reservation_applied OR duplicate.reservation_applied,
            reservation_verified = canonical.reservation_verified OR duplicate.reservation_applied,
            shipment_created = canonical.shipment_created OR duplicate.shipment_created,
            provider_request_started = canonical.provider_request_started OR duplicate.provider_request_started,
            provider_result_received = canonical.provider_result_received OR duplicate.provider_result_received,
            local_persistence_completed = canonical.local_persistence_completed OR duplicate.local_persistence_completed,
            manual_reconciliation_required = canonical.manual_reconciliation_required OR duplicate.manual_reconciliation_required,
            blind_retry_blocked = canonical.blind_retry_blocked OR duplicate.blind_retry_blocked,
            attempt_count = GREATEST(canonical.attempt_count, duplicate.attempt_count),
            started_at = COALESCE(canonical.started_at, duplicate.started_at),
            completed_at = COALESCE(canonical.completed_at, duplicate.completed_at),
            failed_at = COALESCE(canonical.failed_at, duplicate.failed_at),
            last_reconciled_at = COALESCE(canonical.last_reconciled_at, duplicate.last_reconciled_at),
            state = CASE
                WHEN canonical.provider_document_ref IS NOT NULL AND duplicate.provider_document_ref IS NOT NULL AND canonical.provider_document_ref <> duplicate.provider_document_ref THEN 'RECONCILIATION_REQUIRED'
                WHEN canonical.tracking_number IS NOT NULL AND duplicate.provider_document_number IS NOT NULL AND canonical.tracking_number <> duplicate.provider_document_number THEN 'RECONCILIATION_REQUIRED'
                WHEN canonical.state = 'COMPLETED' OR duplicate.state = 'COMPLETED' THEN 'COMPLETED'
                WHEN duplicate.state = 'RECONCILIATION_REQUIRED' THEN 'RECONCILIATION_REQUIRED'
                WHEN canonical.state IN ('PENDING','VALIDATING') THEN duplicate.state
                ELSE canonical.state
            END,
            last_error_code = CASE
                WHEN canonical.provider_document_ref IS NOT NULL AND duplicate.provider_document_ref IS NOT NULL AND canonical.provider_document_ref <> duplicate.provider_document_ref THEN 'FULFILLMENT_JOURNAL_CONFLICT'
                WHEN canonical.tracking_number IS NOT NULL AND duplicate.provider_document_number IS NOT NULL AND canonical.tracking_number <> duplicate.provider_document_number THEN 'FULFILLMENT_JOURNAL_CONFLICT'
                ELSE canonical.last_error_code
            END
        FROM order_fulfillment_operations duplicate
        WHERE canonical.workspace_id = duplicate.workspace_id
          AND canonical.idempotency_key = duplicate.idempotency_key
        """
    )

    op.execute(
        """
        INSERT INTO order_fulfillments (
            id, workspace_id, idempotency_key, request_fingerprint, state, result_code,
            customer_id, address_id, order_id, shipment_id, tracking_number,
            operation_type, attempt_count, provider_document_ref, provider_document_number,
            nova_poshta_operation_id, reservation_applied, reservation_verified,
            shipment_created, provider_request_started, provider_result_received,
            local_persistence_completed, manual_reconciliation_required, blind_retry_blocked,
            last_error_code, last_error_message, started_at, completed_at, failed_at,
            last_reconciled_at, created_by, created_at, updated_at
        )
        SELECT
            duplicate.id, duplicate.workspace_id, duplicate.idempotency_key, duplicate.request_fingerprint,
            duplicate.state, NULL, NULL, NULL, duplicate.order_id, duplicate.shipment_id,
            duplicate.provider_document_number, duplicate.operation_type, duplicate.attempt_count,
            duplicate.provider_document_ref, duplicate.provider_document_number,
            duplicate.nova_poshta_operation_id, duplicate.reservation_applied,
            duplicate.reservation_applied, duplicate.shipment_created,
            duplicate.provider_request_started, duplicate.provider_result_received,
            duplicate.local_persistence_completed, duplicate.manual_reconciliation_required,
            duplicate.blind_retry_blocked, duplicate.safe_error_code, duplicate.safe_error_message,
            duplicate.started_at, duplicate.completed_at, duplicate.failed_at,
            duplicate.last_reconciled_at, duplicate.created_by, duplicate.created_at, duplicate.updated_at
        FROM order_fulfillment_operations duplicate
        WHERE NOT EXISTS (
            SELECT 1 FROM order_fulfillments canonical
            WHERE canonical.workspace_id = duplicate.workspace_id
              AND (
                canonical.idempotency_key = duplicate.idempotency_key
                OR (canonical.order_id IS NOT NULL AND canonical.order_id = duplicate.order_id AND canonical.request_fingerprint = duplicate.request_fingerprint)
                OR (canonical.shipment_id IS NOT NULL AND canonical.shipment_id = duplicate.shipment_id)
              )
        )
        """
    )

    op.create_index("ix_order_fulfillments_workspace_order", "order_fulfillments", ["workspace_id", "order_id"], unique=False)
    op.create_index("ix_order_fulfillments_workspace_shipment", "order_fulfillments", ["workspace_id", "shipment_id"], unique=False)
    op.create_index("ix_order_fulfillments_workspace_state", "order_fulfillments", ["workspace_id", "state"], unique=False)
    op.create_index("ix_order_fulfillments_workspace_provider_ref", "order_fulfillments", ["workspace_id", "provider_document_ref"], unique=False)
    op.create_index("ix_order_fulfillments_workspace_provider_number", "order_fulfillments", ["workspace_id", "provider_document_number"], unique=False)
    op.create_index(
        "uq_order_fulfillments_one_active_per_order",
        "order_fulfillments",
        ["workspace_id", "order_id"],
        unique=True,
        postgresql_where=sa.text("order_id IS NOT NULL AND " + _active_state_sql()),
    )
    op.create_index(
        "uq_order_fulfillments_completed_fingerprint",
        "order_fulfillments",
        ["workspace_id", "order_id", "request_fingerprint"],
        unique=True,
        postgresql_where=sa.text("order_id IS NOT NULL AND state = 'COMPLETED'"),
    )

    op.drop_index("uq_order_fulfillment_operations_completed_fingerprint", table_name="order_fulfillment_operations")
    op.drop_index("uq_order_fulfillment_operations_one_active_per_order", table_name="order_fulfillment_operations")
    op.drop_index("ix_order_fulfillment_operations_workspace_provider_number", table_name="order_fulfillment_operations")
    op.drop_index("ix_order_fulfillment_operations_workspace_provider_ref", table_name="order_fulfillment_operations")
    op.drop_index("ix_order_fulfillment_operations_workspace_state", table_name="order_fulfillment_operations")
    op.drop_index("ix_order_fulfillment_operations_workspace_order", table_name="order_fulfillment_operations")
    op.drop_table("order_fulfillment_operations")


def downgrade() -> None:
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
    op.create_index("uq_order_fulfillment_operations_one_active_per_order", "order_fulfillment_operations", ["workspace_id", "order_id"], unique=True, postgresql_where=sa.text(_active_state_sql()))
    op.create_index("uq_order_fulfillment_operations_completed_fingerprint", "order_fulfillment_operations", ["workspace_id", "order_id", "request_fingerprint"], unique=True, postgresql_where=sa.text("state = 'COMPLETED'"))
    op.execute('ALTER TABLE IF EXISTS public."order_fulfillment_operations" ENABLE ROW LEVEL SECURITY')

    op.drop_index("uq_order_fulfillments_completed_fingerprint", table_name="order_fulfillments")
    op.drop_index("uq_order_fulfillments_one_active_per_order", table_name="order_fulfillments")
    op.drop_index("ix_order_fulfillments_workspace_provider_number", table_name="order_fulfillments")
    op.drop_index("ix_order_fulfillments_workspace_provider_ref", table_name="order_fulfillments")
    op.drop_index("ix_order_fulfillments_workspace_state", table_name="order_fulfillments")
    op.drop_index("ix_order_fulfillments_workspace_shipment", table_name="order_fulfillments")
    op.drop_index("ix_order_fulfillments_workspace_order", table_name="order_fulfillments")
    op.drop_constraint("fk_order_fulfillments_nova_poshta_operation_id", "order_fulfillments", type_="foreignkey")
    for column in (
        "last_reconciled_at", "failed_at", "completed_at", "started_at", "blind_retry_blocked",
        "manual_reconciliation_required", "local_persistence_completed", "provider_result_received",
        "provider_request_started", "shipment_created", "reservation_verified", "reservation_applied",
        "nova_poshta_operation_id", "provider_document_number", "provider_document_ref", "attempt_count",
        "operation_type",
    ):
        op.drop_column("order_fulfillments", column)
