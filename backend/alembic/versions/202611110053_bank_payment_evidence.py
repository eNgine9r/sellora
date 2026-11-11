"""Workspace-scoped read-only-by-default monobank payment evidence, not order revenue.

Revision ID: 202611110053
Revises: 202610290052
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202611110053"
down_revision = "202610290052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.create_table(
        "bank_payment_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("provider_account_id", sa.String(128), nullable=False),
        sa.Column("external_reference", sa.String(160), nullable=False),
        sa.Column("rail", sa.String(40), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("origin", sa.String(40), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_hold", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("invoice_id", sa.String(160)),
        sa.Column("order_number", sa.String(30)),
        sa.Column("candidate_order_id", postgresql.UUID(as_uuid=True)),
        sa.Column("review_reason", sa.String(64), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("workspace_id", "provider", "provider_account_id", "external_reference",
                            name="uq_bank_evidence_tenant_provider_account_event"),
        sa.CheckConstraint("amount_minor > 0 AND amount_minor < 100000000000000",
                           name="bank_evidence_positive_minor_amount"),
        sa.CheckConstraint("currency = 'UAH'", name="bank_evidence_ua_currency"),
    )
    op.create_index("ix_bank_payment_evidence_workspace_id", "bank_payment_evidence", ["workspace_id"])
    op.create_index("ix_bank_payment_evidence_candidate_order_id", "bank_payment_evidence", ["candidate_order_id"])
    op.create_index("ix_bank_evidence_workspace_occurred", "bank_payment_evidence", ["workspace_id", "occurred_at"])
    op.execute("ALTER TABLE public.bank_payment_evidence ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE public.bank_payment_evidence FROM PUBLIC")
    for role_name in ("anon", "authenticated"):
        op.execute(f"""DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role_name}') THEN
                REVOKE ALL PRIVILEGES ON TABLE public.bank_payment_evidence FROM "{role_name}";
            END IF;
        END $$""")


def downgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute("LOCK TABLE public.bank_payment_evidence IN ACCESS EXCLUSIVE MODE")
    count = op.get_bind().execute(sa.text("SELECT count(*) FROM public.bank_payment_evidence")).scalar_one()
    if count:
        raise RuntimeError("Evidence exists; rollback requires a separate data-preserving migration")
    op.drop_table("bank_payment_evidence")
