"""enforce the canonical inventory availability invariant

Revision ID: 202607220034
Revises: 202607200033
"""

from alembic import op


revision: str = "202607220034"
down_revision: str | None = "202607200033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_inventory_reserved_lte_stock",
        "inventory",
        "reserved_quantity <= stock_quantity",
    )


def downgrade() -> None:
    op.drop_constraint("ck_inventory_reserved_lte_stock", "inventory", type_="check")
