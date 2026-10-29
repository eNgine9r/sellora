"""Add an immutable receipt ledger, without callbacks or subscription mutations.

Revision ID: 202610290052
Revises: 202610290051
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202610290052"
down_revision = "202610290051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.create_table(
        "subscription_payment_event_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("provider_account_id", sa.String(128), nullable=False),
        sa.Column("external_event_id", sa.String(160), nullable=False),
        sa.Column("transaction_id", sa.String(160), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("amount", sa.Numeric(20, 6), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("provider", "provider_account_id", "external_event_id", name="uq_subscription_payment_receipt_provider_event"),
        sa.CheckConstraint("amount >= 0 AND amount < 100000000000000", name="receipt_amount"),
        sa.CheckConstraint("length(currency) = 3 AND currency = upper(currency)", name="receipt_currency"),
        sa.CheckConstraint("length(fingerprint) = 64", name="receipt_fingerprint"),
        sa.CheckConstraint("length(trim(provider)) > 0 AND provider = lower(provider)", name="receipt_provider"),
        sa.CheckConstraint("length(trim(provider_account_id)) > 0", name="receipt_provider_account"),
        sa.CheckConstraint("length(trim(external_event_id)) > 0", name="receipt_event_id"),
        sa.CheckConstraint("length(trim(transaction_id)) > 0", name="receipt_transaction_id"),
        sa.CheckConstraint("length(trim(event_type)) > 0", name="receipt_event_type"),
    )
    op.create_index("ix_subscription_payment_event_receipts_workspace_id", "subscription_payment_event_receipts", ["workspace_id"])
    op.execute("ALTER TABLE public.subscription_payment_event_receipts ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE public.subscription_payment_event_receipts FROM PUBLIC")
    for role_name in ("anon", "authenticated"):
        op.execute(f"""DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role_name}') THEN
                REVOKE ALL PRIVILEGES ON TABLE public.subscription_payment_event_receipts FROM "{role_name}";
            END IF;
        END $$""")
    op.execute("""CREATE FUNCTION public.reject_subscription_payment_receipt_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
            RAISE EXCEPTION 'Payment event receipts are immutable' USING ERRCODE = '55000';
        END $$""")
    op.execute("REVOKE ALL PRIVILEGES ON FUNCTION public.reject_subscription_payment_receipt_mutation() FROM PUBLIC")
    op.execute("""CREATE TRIGGER subscription_payment_receipt_immutable
        BEFORE UPDATE OR DELETE ON public.subscription_payment_event_receipts
        FOR EACH ROW EXECUTE FUNCTION public.reject_subscription_payment_receipt_mutation()""")
    op.execute("""CREATE TRIGGER subscription_payment_receipt_no_truncate
        BEFORE TRUNCATE ON public.subscription_payment_event_receipts
        FOR EACH STATEMENT EXECUTE FUNCTION public.reject_subscription_payment_receipt_mutation()""")


def downgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    # Exclude an insert between the empty-table check and DROP TABLE.
    op.execute("LOCK TABLE public.subscription_payment_event_receipts IN ACCESS EXCLUSIVE MODE")
    count = op.get_bind().execute(sa.text("SELECT count(*) FROM public.subscription_payment_event_receipts")).scalar_one()
    if count:
        raise RuntimeError("Payment event receipts exist; rollback requires explicit data-preserving review")
    op.drop_table("subscription_payment_event_receipts")
    op.execute("DROP FUNCTION public.reject_subscription_payment_receipt_mutation()")
