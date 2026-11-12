"""Persist independently verified Nova Poshta tracking states for external TTNs.

Revision ID: 202611120055
Revises: 202611110054
"""
from alembic import op
import sqlalchemy as sa

revision = "202611120055"
down_revision = "202611110054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.add_column("nova_poshta_external_documents", sa.Column("provider_normalized_status", sa.String(20), nullable=True))
    op.add_column("nova_poshta_external_documents", sa.Column("provider_tracking_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(
        "ck_np_external_normalized_status",
        "nova_poshta_external_documents",
        "provider_normalized_status IS NULL OR provider_normalized_status IN "
        "('DRAFT','CREATED','IN_TRANSIT','ARRIVED','DELIVERED','RETURNED','CANCELLED')",
    )


def downgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.drop_constraint("ck_np_external_normalized_status", "nova_poshta_external_documents", type_="check")
    op.drop_column("nova_poshta_external_documents", "provider_tracking_checked_at")
    op.drop_column("nova_poshta_external_documents", "provider_normalized_status")
