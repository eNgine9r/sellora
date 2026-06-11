"""workspace currency setting

Revision ID: 202606040012
Revises: 202606040011
Create Date: 2026-06-04 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "202606040012"
down_revision = "202606040011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workspaces", sa.Column("currency_code", sa.String(length=3), server_default="UAH", nullable=False))
    op.create_check_constraint("ck_workspaces_currency_code", "workspaces", "currency_code in ('UAH', 'USD')")


def downgrade() -> None:
    op.drop_constraint("ck_workspaces_currency_code", "workspaces", type_="check")
    op.drop_column("workspaces", "currency_code")
