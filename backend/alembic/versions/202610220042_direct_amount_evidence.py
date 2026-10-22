"""Retain scoped supporting Direct messages for historical price estimates.

Revision ID: 202610220042
Revises: 202610220041
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "202610220042"
down_revision = "202610220041"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("orders",sa.Column("historical_value_evidence",JSONB(),nullable=True))


def downgrade():
    op.drop_column("orders","historical_value_evidence")
