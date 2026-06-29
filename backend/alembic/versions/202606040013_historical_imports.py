"""historical import order flags

Revision ID: 202606040013
Revises: 202606040012
Create Date: 2026-06-04 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "202606040013"
down_revision = "202606040012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("is_historical", sa.Boolean(), server_default=sa.text("false"), nullable=False))


def downgrade() -> None:
    op.drop_column("orders", "is_historical")
