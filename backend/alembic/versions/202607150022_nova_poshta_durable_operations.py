"""add durable Nova Poshta provider operations

Revision ID: 202607150022
Revises: 202607130021
Create Date: 2026-07-15 15:22:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "202607150022"
down_revision: str | None = "202607130021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _revoke_table_privileges_if_role_exists(table_name: str, role_name: str) -> None:
    # Supabase provides these roles, while local and CI PostgreSQL instances may not.
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role_name}') THEN
                REVOKE ALL PRIVILEGES ON TABLE public."{table_name}" FROM "{role_name}";
            END IF;
        END
        $$
        """
    )


def upgrade() -> None:
    op.create_table(
        "nova_poshta_operations",
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_type", sa.String(length=40), nullable=False),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("provider_marker", sa.String(length=120), nullable=False),
        sa.Column("provider_document_ref", sa.String(length=120), nullable=True),
        sa.Column("provider_document_number", sa.String(length=120), nullable=True),
        sa.Column("provider_status", sa.String(length=255), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("provider_called_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=120), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_nova_poshta_operations_idempotency_key"),
        sa.UniqueConstraint(
            "workspace_id",
            "shipment_id",
            "operation_type",
            name="uq_nova_poshta_operations_workspace_shipment_type",
        ),
    )
    op.create_index(
        "ix_nova_poshta_operations_shipment_id",
        "nova_poshta_operations",
        ["shipment_id"],
        unique=False,
    )
    op.create_index(
        "ix_nova_poshta_operations_workspace_id",
        "nova_poshta_operations",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_nova_poshta_operations_workspace_state",
        "nova_poshta_operations",
        ["workspace_id", "state"],
        unique=False,
    )
    op.add_column("shipments", sa.Column("nova_poshta_create_state", sa.String(length=40), nullable=True))
    op.add_column(
        "shipments",
        sa.Column(
            "nova_poshta_manual_reconciliation_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column("shipments", sa.Column("nova_poshta_last_error_code", sa.String(length=120), nullable=True))

    op.execute('ALTER TABLE IF EXISTS public."nova_poshta_operations" ENABLE ROW LEVEL SECURITY')
    for role_name in ("anon", "authenticated"):
        _revoke_table_privileges_if_role_exists("nova_poshta_operations", role_name)


def downgrade() -> None:
    op.drop_column("shipments", "nova_poshta_last_error_code")
    op.drop_column("shipments", "nova_poshta_manual_reconciliation_required")
    op.drop_column("shipments", "nova_poshta_create_state")
    op.drop_index("ix_nova_poshta_operations_workspace_state", table_name="nova_poshta_operations")
    op.drop_index("ix_nova_poshta_operations_workspace_id", table_name="nova_poshta_operations")
    op.drop_index("ix_nova_poshta_operations_shipment_id", table_name="nova_poshta_operations")
    op.drop_table("nova_poshta_operations")
