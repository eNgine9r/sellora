"""scope order number uniqueness to workspace

Revision ID: 202607130021
Revises: 202607080020
Create Date: 2026-07-13 00:21:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "202607130021"
down_revision: str | None = "202607080020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


OLD_CONSTRAINT = "uq_orders_order_number"
NEW_CONSTRAINT = "uq_orders_workspace_id_order_number"


def upgrade() -> None:
    op.drop_constraint(OLD_CONSTRAINT, "orders", type_="unique")
    op.create_unique_constraint(
        NEW_CONSTRAINT,
        "orders",
        ["workspace_id", "order_number"],
    )


def downgrade() -> None:
    op.drop_constraint(NEW_CONSTRAINT, "orders", type_="unique")
    op.create_unique_constraint(
        OLD_CONSTRAINT,
        "orders",
        ["order_number"],
    )
