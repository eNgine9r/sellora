"""Separate historical declared/collectable order amount from real revenue.

Revision ID: 202610220041
Revises: 202610210040

No historic value is backfilled by schema migration. Explicit reviewed
provider-evidence backfill populates only workspace-scoped recovered orders.
"""
from alembic import op
import sqlalchemy as sa

revision = "202610220041"
down_revision = "202610210040"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("orders", sa.Column("historical_order_value", sa.Numeric(12,2), nullable=True))
    op.add_column("orders", sa.Column("historical_value_source", sa.String(length=32), nullable=True))
    op.execute("""
        ALTER TABLE orders ADD CONSTRAINT ck_order_historical_value_nonnegative
        CHECK (historical_order_value IS NULL OR historical_order_value >= 0)
    """)


def downgrade():
    op.drop_constraint("ck_order_historical_value_nonnegative", "orders", type_="check")
    op.drop_column("orders", "historical_value_source")
    op.drop_column("orders", "historical_order_value")
