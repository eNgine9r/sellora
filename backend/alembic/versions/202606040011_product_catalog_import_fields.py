"""product catalog import fields

Revision ID: 202606040011
Revises: 202606040010
Create Date: 2026-06-04 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "202606040011"
down_revision = "202606040010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("category", sa.String(length=255), nullable=True))
    op.add_column("products", sa.Column("brand", sa.String(length=120), nullable=True))
    op.add_column("product_variants", sa.Column("barcode", sa.String(length=120), nullable=True))
    op.add_column("product_variants", sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.add_column("inventory", sa.Column("incoming_quantity", sa.Integer(), server_default=sa.text("0"), nullable=False))


def downgrade() -> None:
    op.drop_column("inventory", "incoming_quantity")
    op.drop_column("product_variants", "is_active")
    op.drop_column("product_variants", "barcode")
    op.drop_column("products", "brand")
    op.drop_column("products", "category")
