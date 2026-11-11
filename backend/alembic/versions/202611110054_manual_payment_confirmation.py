"""Manual double-check of receipt and funds, no bank API.
Revision ID: 202611110054
Revises: 202611110053
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202611110054"
down_revision = "202611110053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.create_table(
        "manual_payment_confirmations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_method", sa.String(40), nullable=False),
        sa.Column("transaction_reference", sa.String(160), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("receipt_checked", sa.Boolean(), nullable=False),
        sa.Column("bank_received_checked", sa.Boolean(), nullable=False),
        sa.Column("receipt_note", sa.String(240)),
        sa.Column("verified_by_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["verified_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("workspace_id", "order_id", name="uq_manual_payment_workspace_order"),
        sa.UniqueConstraint("workspace_id", "transaction_reference", name="uq_manual_payment_workspace_transaction"),
        sa.CheckConstraint("amount_minor > 0", name="manual_payment_amount_positive"),
        sa.CheckConstraint("currency = 'UAH'", name="manual_payment_ua_currency"),
        sa.CheckConstraint("receipt_checked IS TRUE AND bank_received_checked IS TRUE",
                           name="manual_payment_both_checks_required"),
    )
    op.create_index("ix_manual_payment_confirmations_workspace_id", "manual_payment_confirmations", ["workspace_id"])
    op.create_index("ix_manual_payment_confirmations_order_id", "manual_payment_confirmations", ["order_id"])
    op.execute("ALTER TABLE public.manual_payment_confirmations ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL PRIVILEGES ON public.manual_payment_confirmations FROM PUBLIC")
    for role in ("anon", "authenticated"):
        op.execute(f"""DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                REVOKE ALL PRIVILEGES ON TABLE public.manual_payment_confirmations FROM "{role}";
            END IF;
        END $$""")


def downgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    count = op.get_bind().execute(sa.text("SELECT count(*) FROM public.manual_payment_confirmations")).scalar_one()
    if count:
        raise RuntimeError("Manual payment confirmations exist; data-preserving reversal required")
    op.drop_table("manual_payment_confirmations")
