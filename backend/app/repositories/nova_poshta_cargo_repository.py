"""Read-only, workspace-isolated product snapshots for TTN cargo descriptions."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.product_variant import ProductVariant


class NovaPoshtaCargoRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_order_categories(self, workspace_id: UUID, order_id: UUID) -> list[tuple[str, str | None]]:
        stmt = (
            select(OrderItem.product_name, Product.category)
            .join(
                Order,
                (Order.id == OrderItem.order_id)
                & (Order.workspace_id == workspace_id)
                & (Order.deleted_at.is_(None)),
            )
            .join(
                ProductVariant,
                (ProductVariant.id == OrderItem.product_variant_id)
                & (ProductVariant.workspace_id == workspace_id),
            )
            .join(
                Product,
                (Product.id == ProductVariant.product_id)
                & (Product.workspace_id == workspace_id),
            )
            .where(
                OrderItem.workspace_id == workspace_id,
                OrderItem.order_id == order_id,
                OrderItem.deleted_at.is_(None),
                OrderItem.quantity > 0,
            )
        )
        return [(name, category) for name, category in self.db.execute(stmt).all()]
