from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.product_variant import ProductVariant
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.inventory_repository import InventoryRepository, InventoryTransactionRepository
from app.repositories.product_repository import ProductRepository, ProductVariantRepository
from app.schemas.product import ProductCreate, ProductImageCreate, ProductUpdate, ProductVariantCreate, ProductVariantUpdate
from app.services.business_utils import snapshot


class ProductServiceError(ValueError):
    pass


class ProductService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.products = ProductRepository(db)
        self.variants = ProductVariantRepository(db)
        self.inventory = InventoryRepository(db)
        self.inventory_transactions = InventoryTransactionRepository(db)
        self.audit_logs = AuditLogRepository(db)

    def list_products(self, workspace_id: UUID, search: str | None = None, category: str | None = None) -> list[Product]:
        return self.products.list_for_workspace(workspace_id, search, category)

    def get_product(self, workspace_id: UUID, product_id: UUID) -> Product | None:
        return self.products.get(workspace_id, product_id)

    def create_product(self, workspace_id: UUID, payload: ProductCreate, actor_user_id: UUID | None) -> Product:
        image_payloads = payload.images
        product = self.products.create(Product(workspace_id=workspace_id, **payload.model_dump(exclude={"images"})))
        for image_payload in image_payloads:
            self._create_image(workspace_id, product.id, image_payload)
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="Product",
            entity_id=product.id,
            action="CREATE",
            new_value=snapshot(product),
        )
        self.db.commit()
        self.db.refresh(product)
        return product

    def update_product(self, workspace_id: UUID, product_id: UUID, payload: ProductUpdate, actor_user_id: UUID | None) -> Product | None:
        product = self.get_product(workspace_id, product_id)
        if product is None:
            return None
        old_value = snapshot(product)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(product, field, value)
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="Product",
            entity_id=product.id,
            action="PRODUCT_UPDATE",
            old_value=old_value,
            new_value=snapshot(product),
        )
        self.db.commit()
        self.db.refresh(product)
        return product

    def delete_product(self, workspace_id: UUID, product_id: UUID, actor_user_id: UUID | None) -> bool:
        product = self.get_product(workspace_id, product_id)
        if product is None:
            return False
        old_value = snapshot(product)
        self.products.soft_delete(product, actor_user_id)
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="Product",
            entity_id=product.id,
            action="PRODUCT_ARCHIVE",
            old_value=old_value,
            new_value=snapshot(product),
        )
        self.db.commit()
        return True

    def add_product_image(self, workspace_id: UUID, product_id: UUID, payload: ProductImageCreate, actor_user_id: UUID | None) -> ProductImage | None:
        if self.get_product(workspace_id, product_id) is None:
            return None
        image = self._create_image(workspace_id, product_id, payload)
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="ProductImage",
            entity_id=image.id,
            action="CREATE",
            new_value=snapshot(image),
        )
        self.db.commit()
        self.db.refresh(image)
        return image

    def list_variants(self, workspace_id: UUID, product_id: UUID | None = None) -> list[ProductVariant]:
        return self.variants.list_for_workspace(workspace_id, product_id)

    def get_variant(self, workspace_id: UUID, variant_id: UUID) -> ProductVariant | None:
        return self.variants.get(workspace_id, variant_id)

    def create_variant(self, workspace_id: UUID, payload: ProductVariantCreate, actor_user_id: UUID | None) -> ProductVariant:
        product = self.get_product(workspace_id, payload.product_id)
        if product is None:
            raise ProductServiceError("Product does not exist in this workspace")
        if self.variants.find_by_identity(payload.product_id, payload.color, payload.size) is not None:
            raise ProductServiceError("Product variant with this product, color, and size already exists")
        if self.variants.find_by_sku(workspace_id, payload.sku) is not None:
            raise ProductServiceError("Product variant SKU already exists")
        variant = self.variants.create(
            ProductVariant(
                workspace_id=workspace_id,
                product_id=payload.product_id,
                sku=payload.sku,
                color=payload.color,
                size=payload.size,
                price=payload.price,
                barcode=payload.barcode,
                is_active=payload.is_active,
            )
        )
        from app.models.inventory import Inventory

        self.inventory.create(
            Inventory(
                workspace_id=workspace_id,
                product_variant_id=variant.id,
                stock_quantity=payload.initial_stock_quantity,
                reserved_quantity=0,
                incoming_quantity=0,
                minimum_quantity=payload.minimum_quantity,
            )
        )
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="ProductVariant",
            entity_id=variant.id,
            action="CREATE_WITH_INVENTORY",
            new_value=snapshot(variant),
        )
        self.db.commit()
        self.db.refresh(variant)
        return variant

    def update_variant(self, workspace_id: UUID, variant_id: UUID, payload: ProductVariantUpdate, actor_user_id: UUID | None) -> ProductVariant | None:
        variant = self.get_variant(workspace_id, variant_id)
        if variant is None:
            return None
        new_color = payload.color if payload.color is not None else variant.color
        new_size = payload.size if payload.size is not None else variant.size
        duplicate = self.variants.find_by_identity(variant.product_id, new_color, new_size)
        if duplicate and duplicate.id != variant.id:
            raise ProductServiceError("Product variant with this product, color, and size already exists")
        new_sku = payload.sku if payload.sku is not None else variant.sku
        duplicate_sku = self.variants.find_by_sku(workspace_id, new_sku)
        if duplicate_sku and duplicate_sku.id != variant.id:
            raise ProductServiceError("Product variant SKU already exists")
        old_value = snapshot(variant)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(variant, field, value)
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="ProductVariant",
            entity_id=variant.id,
            action="PRODUCT_VARIANT_UPDATE",
            old_value=old_value,
            new_value=snapshot(variant),
        )
        self.db.commit()
        self.db.refresh(variant)
        return variant

    def delete_variant(self, workspace_id: UUID, variant_id: UUID, actor_user_id: UUID | None) -> bool:
        variant = self.get_variant(workspace_id, variant_id)
        if variant is None:
            return False
        if variant.inventory and variant.inventory.reserved_quantity > 0:
            raise ProductServiceError("Product variant has reserved inventory. Cancel or complete related orders before archiving it.")
        old_value = snapshot(variant)
        self.variants.soft_delete(variant, actor_user_id)
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="ProductVariant",
            entity_id=variant.id,
            action="PRODUCT_VARIANT_ARCHIVE",
            old_value=old_value,
            new_value=snapshot(variant),
        )
        self.db.commit()
        return True

    def _create_image(self, workspace_id: UUID, product_id: UUID, payload: ProductImageCreate) -> ProductImage:
        return self.products.create_image(ProductImage(workspace_id=workspace_id, product_id=product_id, **payload.model_dump()))
