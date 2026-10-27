"""Add isolated NovaPay/bank COD reconciliation evidence ledger.

Revision ID: 202610230044
Revises: 202610230043
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202610230044"
down_revision = "202610230043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cod_payment_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("external_reference", sa.String(160), nullable=False),
        sa.Column("tracking_number", sa.String(40), nullable=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("shipments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("gross_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("fee_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("review_reason", sa.String(90), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "source", "external_reference", name="uq_cod_evidence_workspace_source_ref"),
        sa.CheckConstraint("gross_amount > 0", name="ck_cod_payment_evidence_positive_amount"),
        sa.CheckConstraint("fee_amount >= 0 AND fee_amount <= gross_amount", name="ck_cod_payment_evidence_valid_fee"),
    )
    op.create_index("ix_cod_payment_evidence_workspace_id", "cod_payment_evidence", ["workspace_id"])
    op.create_index("ix_cod_payment_evidence_tracking_number", "cod_payment_evidence", ["tracking_number"])
    op.create_index("ix_cod_payment_evidence_order_id", "cod_payment_evidence", ["order_id"])
    op.create_index("ix_cod_payment_evidence_paid_at", "cod_payment_evidence", ["workspace_id", "paid_at"])
    op.execute("ALTER TABLE public.cod_payment_evidence ENABLE ROW LEVEL SECURITY")
    # PostgreSQL CI does not have Supabase's optional anon/authenticated roles.
    # Preserve the strict grant policy where those roles exist.
    op.execute("REVOKE ALL PRIVILEGES ON TABLE public.cod_payment_evidence FROM PUBLIC")
    for role_name in ("anon", "authenticated"):
        op.execute(f"""
            DO $roles$ BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role_name}') THEN
                    REVOKE ALL PRIVILEGES ON TABLE public.cod_payment_evidence FROM "{role_name}";
                END IF;
            END $roles$
        """)


def downgrade() -> None:
    op.drop_index("ix_cod_payment_evidence_paid_at", "cod_payment_evidence")
    op.drop_index("ix_cod_payment_evidence_order_id", "cod_payment_evidence")
    op.drop_index("ix_cod_payment_evidence_tracking_number", "cod_payment_evidence")
    op.drop_index("ix_cod_payment_evidence_workspace_id", "cod_payment_evidence")
    op.drop_table("cod_payment_evidence")
