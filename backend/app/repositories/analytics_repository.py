from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.customer import Customer
from app.models.inventory import Inventory
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.product_variant import ProductVariant


class AnalyticsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_orders(self, workspace_id: UUID, start_at: datetime, end_at: datetime) -> list[Order]:
        metric_date = func.coalesce(Order.completed_at, Order.created_at)
        stmt = (
            select(Order)
            .where(
                Order.workspace_id == workspace_id,
                Order.deleted_at.is_(None),
                metric_date >= start_at,
                metric_date <= end_at,
            )
            .options(selectinload(Order.items))
        )
        return list(self.db.execute(stmt).scalars())

    def list_order_items(self, workspace_id: UUID, start_at: datetime, end_at: datetime) -> Sequence[tuple[OrderItem, Order, ProductVariant, Product]]:
        metric_date = func.coalesce(Order.completed_at, Order.created_at)
        stmt: Select[tuple[OrderItem, Order, ProductVariant, Product]] = (
            select(OrderItem, Order, ProductVariant, Product)
            .join(Order, OrderItem.order_id == Order.id)
            .join(ProductVariant, OrderItem.product_variant_id == ProductVariant.id)
            .join(Product, ProductVariant.product_id == Product.id)
            .where(
                Order.workspace_id == workspace_id,
                Order.deleted_at.is_(None),
                OrderItem.deleted_at.is_(None),
                ProductVariant.deleted_at.is_(None),
                Product.deleted_at.is_(None),
                metric_date >= start_at,
                metric_date <= end_at,
            )
        )
        return list(self.db.execute(stmt).all())

    def list_customers(self, workspace_id: UUID) -> list[Customer]:
        stmt = select(Customer).where(Customer.workspace_id == workspace_id, Customer.deleted_at.is_(None))
        return list(self.db.execute(stmt).scalars())

    def list_inventory_items(self, workspace_id: UUID) -> Sequence[tuple[Inventory, ProductVariant, Product]]:
        stmt: Select[tuple[Inventory, ProductVariant, Product]] = (
            select(Inventory, ProductVariant, Product)
            .join(ProductVariant, Inventory.product_variant_id == ProductVariant.id)
            .join(Product, ProductVariant.product_id == Product.id)
            .where(
                Inventory.workspace_id == workspace_id,
                Inventory.deleted_at.is_(None),
                ProductVariant.deleted_at.is_(None),
                Product.deleted_at.is_(None),
            )
        )
        return list(self.db.execute(stmt).all())
