"""Add advisory historical COGS estimate fields isolated from confirmed finance.

Revision ID: 202610230043
Revises: 202610220042
"""

from alembic import op
import sqlalchemy as sa

revision: str = "202610230043"
down_revision: str | None = "202610220042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("estimated_product_cost", sa.Numeric(12, 2), nullable=True))
    op.add_column("orders", sa.Column("estimated_cost_source", sa.String(30), nullable=True))
    op.add_column("orders", sa.Column("estimated_cost_confidence", sa.String(30), nullable=True))
    op.add_column("orders", sa.Column("estimated_cost_reference", sa.String(512), nullable=True))
    op.create_check_constraint(
        "ck_orders_estimate_historical_positive",
        "orders",
        "(estimated_product_cost IS NULL OR (estimated_product_cost > 0 AND is_historical = true))",
    )
    op.create_check_constraint(
        "ck_orders_estimate_fields_together",
        "orders",
        """(estimated_product_cost IS NULL AND estimated_cost_source IS NULL
            AND estimated_cost_confidence IS NULL AND estimated_cost_reference IS NULL)
            OR (estimated_product_cost IS NOT NULL AND estimated_cost_source IS NOT NULL
            AND estimated_cost_confidence IS NOT NULL)""",
    )


def downgrade() -> None:
    op.drop_constraint("ck_orders_estimate_fields_together", "orders", type_="check")
    op.drop_constraint("ck_orders_estimate_historical_positive", "orders", type_="check")
    for name in ("estimated_cost_reference", "estimated_cost_confidence", "estimated_cost_source", "estimated_product_cost"):
        op.drop_column("orders", name)
