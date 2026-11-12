"""Workspace-scoped, bounded, read-only global search.

Only non-financial identifiers appear in suggestions. Search never changes data,
never returns soft-deleted records and never traverses into another workspace.
"""
from uuid import UUID

from sqlalchemy import and_, exists, or_, select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.lead import Lead
from app.models.order import Order
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.shipment import Shipment


KINDS = ("orders", "customers", "leads", "products", "shipments")
PER_KIND_LIMIT = 4


def _match(column, pattern):
    return column.ilike(pattern, escape="\\")


def _pattern(query: str) -> str:
    # Escape SQL LIKE wildcard characters to search the literal text entered.
    return "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def global_search(db: Session, workspace_id: UUID, query: str) -> list[dict[str, str]]:
    text = query.strip()
    if len(text) < 2:
        return []

    needle = _pattern(text)
    results: list[dict[str, str]] = []

    def add(kind: str, rows, route: str, title_field: str, subtitle_field: str | None = None) -> None:
        for item in rows:
            title = getattr(item, title_field) or "—"
            subtitle = (getattr(item, subtitle_field) or "") if subtitle_field else ""
            results.append({
                "kind": kind, "id": str(item.id), "title": str(title),
                "subtitle": str(subtitle), "href": f"/{route}?{route[:-1] if route.endswith('s') else route}_id={item.id}",
            })

    # A dedicated endpoint avoids downloading entire tables while typing.
    add("orders", db.scalars(
        select(Order).outerjoin(Customer, and_(
            Order.customer_id == Customer.id,
            Customer.workspace_id == workspace_id, Customer.deleted_at.is_(None),
        ))
        .where(Order.workspace_id == workspace_id, Order.deleted_at.is_(None),
               or_(_match(Order.order_number, needle),
                   _match(Customer.name, needle), _match(Customer.phone, needle)))
        .order_by(Order.created_at.desc(), Order.id).limit(PER_KIND_LIMIT)
    ).all(), "orders", "order_number", "status")

    add("customers", db.scalars(
        select(Customer).where(Customer.workspace_id == workspace_id, Customer.deleted_at.is_(None),
            or_(_match(Customer.name, needle), _match(Customer.phone, needle),
                _match(Customer.instagram_username, needle)))
        .order_by(Customer.updated_at.desc(), Customer.id).limit(PER_KIND_LIMIT)
    ).all(), "customers", "name", "instagram_username")

    add("leads", db.scalars(
        select(Lead).where(Lead.workspace_id == workspace_id, Lead.deleted_at.is_(None),
            or_(_match(Lead.name, needle), _match(Lead.phone, needle),
                _match(Lead.instagram_username, needle)))
        .order_by(Lead.updated_at.desc(), Lead.id).limit(PER_KIND_LIMIT)
    ).all(), "leads", "name", "instagram_username")

    variant_matches = exists(select(ProductVariant.id).where(
        ProductVariant.product_id == Product.id,
        ProductVariant.workspace_id == workspace_id,
        ProductVariant.deleted_at.is_(None),
        _match(ProductVariant.sku, needle),
    ))
    add("products", db.scalars(
        select(Product).where(Product.workspace_id == workspace_id, Product.deleted_at.is_(None),
            or_(_match(Product.name, needle), _match(Product.sku, needle), variant_matches))
        .order_by(Product.updated_at.desc(), Product.id).limit(PER_KIND_LIMIT)
    ).all(), "products", "name", "sku")

    add("shipments", db.scalars(
        select(Shipment).where(Shipment.workspace_id == workspace_id, Shipment.deleted_at.is_(None),
            or_(_match(Shipment.tracking_number, needle),
                _match(Shipment.nova_poshta_document_number, needle),
                _match(Shipment.recipient_name, needle),
                _match(Shipment.recipient_phone, needle)))
        .order_by(Shipment.updated_at.desc(), Shipment.id).limit(PER_KIND_LIMIT)
    ).all(), "shipments", "tracking_number", "recipient_name")

    return results
