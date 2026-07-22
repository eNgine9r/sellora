"""zero legacy profit for financially excluded orders

Revision ID: 202607220035
Revises: 202607220034
"""

from alembic import op


revision: str = "202607220035"
down_revision: str | None = "202607220034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE orders
        SET net_profit = 0
        WHERE net_profit <> 0
          AND (
            status IN ('CANCELLED', 'RETURNED')
            OR payment_status = 'REFUNDED'
          )
        """
    )


def downgrade() -> None:
    # The previous legacy values cannot be reconstructed safely. Keeping the
    # canonical zero is preferable to inventing financial data on downgrade.
    pass
