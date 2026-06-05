from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.product_variant import ProductVariant


class ProductRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_workspace(self, workspace_id: UUID, search: str | None = None) -> list[Product]:
        stmt: Select[tuple[Product]] = select(Product).where(Product.workspace_id == workspace_id, Product.deleted_at.is_(None)).options(selectinload(Product.images))
        if search:
            query = f"%{search}%"
            stmt = stmt.where(or_(Product.name.ilike(query), Product.sku.ilike(query)))
        return list(self.db.execute(stmt.order_by(Product.created_at.desc())).scalars())

    def get(self, workspace_id: UUID, product_id: UUID) -> Product | None:
        stmt = select(Product).where(Product.workspace_id == workspace_id, Product.id == product_id, Product.deleted_at.is_(None)).options(selectinload(Product.images), selectinload(Product.variants))
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, product: Product) -> Product:
        self.db.add(product)
        self.db.flush()
        return product

    def create_image(self, image: ProductImage) -> ProductImage:
        self.db.add(image)
        self.db.flush()
        return image

    def soft_delete(self, product: Product, deleted_by: UUID | None) -> Product:
        product.deleted_at = datetime.now(UTC)
        product.deleted_by = deleted_by
        self.db.flush()
        return product


class ProductVariantRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_workspace(self, workspace_id: UUID, product_id: UUID | None = None) -> list[ProductVariant]:
        stmt: Select[tuple[ProductVariant]] = select(ProductVariant).where(ProductVariant.workspace_id == workspace_id, ProductVariant.deleted_at.is_(None)).options(selectinload(ProductVariant.inventory))
        if product_id:
            stmt = stmt.where(ProductVariant.product_id == product_id)
        return list(self.db.execute(stmt.order_by(ProductVariant.created_at.desc())).scalars())

    def get(self, workspace_id: UUID, variant_id: UUID) -> ProductVariant | None:
        stmt = select(ProductVariant).where(ProductVariant.workspace_id == workspace_id, ProductVariant.id == variant_id, ProductVariant.deleted_at.is_(None)).options(selectinload(ProductVariant.inventory))
        return self.db.execute(stmt).scalar_one_or_none()

    def find_by_identity(self, product_id: UUID, color: str | None, size: str | None) -> ProductVariant | None:
        stmt = select(ProductVariant).where(ProductVariant.product_id == product_id, ProductVariant.color == color, ProductVariant.size == size, ProductVariant.deleted_at.is_(None))
        return self.db.execute(stmt).scalar_one_or_none()

    def find_by_sku(self, workspace_id: UUID, sku: str | None) -> ProductVariant | None:
        if not sku:
            return None
        stmt = select(ProductVariant).where(ProductVariant.workspace_id == workspace_id, ProductVariant.sku == sku, ProductVariant.deleted_at.is_(None))
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, variant: ProductVariant) -> ProductVariant:
        self.db.add(variant)
        self.db.flush()
        return variant

    def soft_delete(self, variant: ProductVariant, deleted_by: UUID | None) -> ProductVariant:
        variant.deleted_at = datetime.now(UTC)
        variant.deleted_by = deleted_by
        self.db.flush()
        return variant
