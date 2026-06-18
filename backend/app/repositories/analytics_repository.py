from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.ad_campaign import AdCampaign
from app.models.ad_metric import AdMetric
from app.models.customer import Customer
from app.models.lead import Lead
from app.models.shipment import Shipment
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


    def list_ad_metrics(self, workspace_id: UUID, start_at: datetime, end_at: datetime) -> Sequence[tuple[AdMetric, AdCampaign]]:
        stmt: Select[tuple[AdMetric, AdCampaign]] = (
            select(AdMetric, AdCampaign)
            .join(AdCampaign, AdMetric.campaign_id == AdCampaign.id)
            .where(
                AdMetric.workspace_id == workspace_id,
                AdCampaign.workspace_id == workspace_id,
                AdMetric.deleted_at.is_(None),
                AdCampaign.deleted_at.is_(None),
                AdMetric.metric_date >= start_at.date(),
                AdMetric.metric_date <= end_at.date(),
            )
        )
        return list(self.db.execute(stmt).all())

    def list_leads(self, workspace_id: UUID, start_at: datetime, end_at: datetime) -> list[Lead]:
        stmt = select(Lead).where(
            Lead.workspace_id == workspace_id,
            Lead.deleted_at.is_(None),
            Lead.created_at >= start_at,
            Lead.created_at <= end_at,
        )
        return list(self.db.execute(stmt).scalars())

    def list_shipments(self, workspace_id: UUID, start_at: datetime, end_at: datetime) -> list[Shipment]:
        stmt = select(Shipment).where(
            Shipment.workspace_id == workspace_id,
            Shipment.deleted_at.is_(None),
            Shipment.created_at >= start_at,
            Shipment.created_at <= end_at,
        )
        return list(self.db.execute(stmt).scalars())
