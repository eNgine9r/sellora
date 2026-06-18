"""nova poshta integration

Revision ID: 202606040010
Revises: 202606020009
Create Date: 2026-06-04 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202606040010"
down_revision = "202606020009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integration_connections",
        sa.Column("provider", sa.String(length=60), nullable=False),
        sa.Column("connection_name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="DISCONNECTED"),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settings", sa.JSON(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("provider IN ('NOVA_POSHTA')", name="integration_connections_provider_allowed"),
        sa.CheckConstraint("status IN ('DISCONNECTED', 'CONNECTED', 'ERROR')", name="integration_connections_status_allowed"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_integration_connections_workspace_id", "integration_connections", ["workspace_id"])
    op.create_index("ix_integration_connections_provider", "integration_connections", ["provider"])
    op.create_index("uq_integration_connections_workspace_provider", "integration_connections", ["workspace_id", "provider"], unique=True, postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_table(
        "integration_credentials",
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("encrypted_access_token", sa.Text(), nullable=False),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["integration_connections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_integration_credentials_workspace_id", "integration_credentials", ["workspace_id"])
    op.create_index("ix_integration_credentials_connection_id", "integration_credentials", ["connection_id"])
    for column in (
        sa.Column("external_provider", sa.String(length=60), nullable=True),
        sa.Column("external_ref", sa.String(length=120), nullable=True),
        sa.Column("external_status", sa.String(length=120), nullable=True),
        sa.Column("nova_poshta_city_ref", sa.String(length=120), nullable=True),
        sa.Column("nova_poshta_warehouse_ref", sa.String(length=120), nullable=True),
        sa.Column("nova_poshta_document_ref", sa.String(length=120), nullable=True),
        sa.Column("nova_poshta_document_number", sa.String(length=120), nullable=True),
        sa.Column("nova_poshta_raw_status", sa.String(length=255), nullable=True),
        sa.Column("nova_poshta_synced_at", sa.DateTime(timezone=True), nullable=True),
    ):
        op.add_column("shipments", column)


def downgrade() -> None:
    for name in ("nova_poshta_synced_at", "nova_poshta_raw_status", "nova_poshta_document_number", "nova_poshta_document_ref", "nova_poshta_warehouse_ref", "nova_poshta_city_ref", "external_status", "external_ref", "external_provider"):
        op.drop_column("shipments", name)
    op.drop_index("ix_integration_credentials_connection_id", table_name="integration_credentials")
    op.drop_index("ix_integration_credentials_workspace_id", table_name="integration_credentials")
    op.drop_table("integration_credentials")
    op.drop_index("uq_integration_connections_workspace_provider", table_name="integration_connections")
    op.drop_index("ix_integration_connections_provider", table_name="integration_connections")
    op.drop_index("ix_integration_connections_workspace_id", table_name="integration_connections")
    op.drop_table("integration_connections")
