"""Retain original advertising spend and daily FX evidence.

Revision ID: 202610230045
Revises: 202610230044
"""
from alembic import op
import sqlalchemy as sa

revision = "202610230045"
down_revision = "202610230044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable, no backfill: existing manual/CSV money keeps its original meaning.
    for column in [
        sa.Column("original_spend", sa.Numeric(12, 2), nullable=True),
        sa.Column("original_currency", sa.String(3), nullable=True),
        sa.Column("spend_currency", sa.String(3), nullable=True),
        sa.Column("exchange_rate", sa.Numeric(18, 8), nullable=True),
        sa.Column("exchange_rate_date", sa.Date(), nullable=True),
        sa.Column("exchange_rate_source", sa.String(24), nullable=True),
    ]:
        op.add_column("ad_metrics", column)


def downgrade() -> None:
    for name in ["exchange_rate_source", "exchange_rate_date", "exchange_rate", "spend_currency", "original_currency", "original_spend"]:
        op.drop_column("ad_metrics", name)
