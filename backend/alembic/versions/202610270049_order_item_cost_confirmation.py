"""Record whether an order item's product cost was explicitly confirmed.

Revision ID: 202610270049
Revises: 202610260048
"""
from alembic import op
import sqlalchemy as sa

revision = "202610270049"
down_revision = "202610260048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No rewrite or guessed backfill of existing financial records.
    op.add_column("order_items", sa.Column("cost_confirmed", sa.Boolean(), nullable=True))


def downgrade() -> None:
    # The marker can contain evidence that a zero cost is genuine. Refuse to
    # silently destroy that evidence on rollback.
    connection = op.get_bind()
    exists = connection.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM order_items WHERE cost_confirmed IS NOT NULL)"
    )).scalar()
    if exists:
        raise RuntimeError("Cannot discard recorded cost confirmations on downgrade")
    op.drop_column("order_items", "cost_confirmed")
