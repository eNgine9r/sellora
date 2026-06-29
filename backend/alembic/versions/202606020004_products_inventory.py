"""products variants and inventory

Revision ID: 202606020004
Revises: 202606020003
Create Date: 2026-06-02 00:04:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202606020004"
down_revision: str | None = "202606020003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TRANSACTION_TYPES = "'STOCK_IN', 'STOCK_OUT', 'RESERVE', 'UNRESERVE', 'RETURN', 'ADJUSTMENT'"


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sku", sa.String(length=120), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], name=op.f("fk_products_deleted_by_users"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name=op.f("fk_products_workspace_id_workspaces"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
    )
    op.create_index(op.f("ix_products_workspace_id"), "products", ["workspace_id"], unique=False)
    op.create_index("ix_products_workspace_id_sku", "products", ["workspace_id", "sku"], unique=False)

    op.create_table(
        "product_variants",
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku", sa.String(length=120), nullable=False),
        sa.Column("color", sa.String(length=80), nullable=True),
        sa.Column("size", sa.String(length=80), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], name=op.f("fk_product_variants_deleted_by_users"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name=op.f("fk_product_variants_product_id_products"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name=op.f("fk_product_variants_workspace_id_workspaces"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_product_variants")),
        sa.UniqueConstraint("product_id", "color", "size", name="uq_product_variants_product_id_color_size"),
    )
    op.create_index(op.f("ix_product_variants_workspace_id"), "product_variants", ["workspace_id"], unique=False)
    op.create_index("ix_product_variants_workspace_id_sku", "product_variants", ["workspace_id", "sku"], unique=False)

    op.create_table(
        "product_images",
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("image_url", sa.String(length=1000), nullable=False),
        sa.Column("alt_text", sa.String(length=255), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], name=op.f("fk_product_images_deleted_by_users"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name=op.f("fk_product_images_product_id_products"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name=op.f("fk_product_images_workspace_id_workspaces"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_product_images")),
    )
    op.create_index(op.f("ix_product_images_workspace_id"), "product_images", ["workspace_id"], unique=False)

    op.create_table(
        "inventory",
        sa.Column("product_variant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stock_quantity", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("reserved_quantity", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("minimum_quantity", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("stock_quantity >= 0", name="ck_inventory_stock_quantity_non_negative"),
        sa.CheckConstraint("reserved_quantity >= 0", name="ck_inventory_reserved_quantity_non_negative"),
        sa.CheckConstraint("minimum_quantity >= 0", name="ck_inventory_minimum_quantity_non_negative"),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], name=op.f("fk_inventory_deleted_by_users"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_variant_id"], ["product_variants.id"], name=op.f("fk_inventory_product_variant_id_product_variants"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name=op.f("fk_inventory_workspace_id_workspaces"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory")),
        sa.UniqueConstraint("product_variant_id", name=op.f("uq_inventory_product_variant_id")),
    )
    op.create_index(op.f("ix_inventory_workspace_id"), "inventory", ["workspace_id"], unique=False)

    op.create_table(
        "inventory_transactions",
        sa.Column("inventory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_variant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transaction_type", sa.String(length=30), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("previous_stock_quantity", sa.Integer(), nullable=False),
        sa.Column("new_stock_quantity", sa.Integer(), nullable=False),
        sa.Column("previous_reserved_quantity", sa.Integer(), nullable=False),
        sa.Column("new_reserved_quantity", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(f"transaction_type IN ({TRANSACTION_TYPES})", name="ck_inventory_transactions_transaction_type"),
        sa.CheckConstraint("quantity > 0", name="ck_inventory_transactions_quantity_positive"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_inventory_transactions_created_by_users"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], name=op.f("fk_inventory_transactions_deleted_by_users"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["inventory_id"], ["inventory.id"], name=op.f("fk_inventory_transactions_inventory_id_inventory"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_variant_id"], ["product_variants.id"], name=op.f("fk_inventory_transactions_product_variant_id_product_variants"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name=op.f("fk_inventory_transactions_workspace_id_workspaces"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_transactions")),
    )
    op.create_index(op.f("ix_inventory_transactions_workspace_id"), "inventory_transactions", ["workspace_id"], unique=False)
    op.create_index("ix_inventory_transactions_inventory_id_created_at", "inventory_transactions", ["inventory_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_inventory_transactions_inventory_id_created_at", table_name="inventory_transactions")
    op.drop_index(op.f("ix_inventory_transactions_workspace_id"), table_name="inventory_transactions")
    op.drop_table("inventory_transactions")
    op.drop_index(op.f("ix_inventory_workspace_id"), table_name="inventory")
    op.drop_table("inventory")
    op.drop_index(op.f("ix_product_images_workspace_id"), table_name="product_images")
    op.drop_table("product_images")
    op.drop_index("ix_product_variants_workspace_id_sku", table_name="product_variants")
    op.drop_index(op.f("ix_product_variants_workspace_id"), table_name="product_variants")
    op.drop_table("product_variants")
    op.drop_index("ix_products_workspace_id_sku", table_name="products")
    op.drop_index(op.f("ix_products_workspace_id"), table_name="products")
    op.drop_table("products")
