from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.ad_campaign import AdCampaign, AdCampaignBudgetType, AdCampaignObjective, AdCampaignPlatform, AdCampaignStatus
from app.models.ad_metric import AdMetric
from app.models.customer import Customer
from app.models.inventory import Inventory
from app.models.lead import Lead, LeadStatus
from app.models.order import Order, OrderStatus, PaymentStatus
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.shipment import Shipment, ShipmentCarrier, ShipmentStatus
from app.models.workspace import Workspace
from app.schemas.order import OrderCreate, OrderItemCreate
from app.services.order_service import OrderService

DEMO_WORKSPACE_SLUG = "sellora-demo"
DEMO_WORKSPACE_NAME = "Sellora DEMO Workspace"
DEMO_PRODUCTS = [
    ("DEMO-RING-LUNA", "DEMO Каблучка Luna", "rings", "DEMO-RING-LUNA-GOLD", "Gold", "17", Decimal("890"), Decimal("390"), 3, 5),
    ("DEMO-NECK-AURA", "DEMO Підвіска Aura", "necklaces", "DEMO-NECK-AURA-SILVER", "Silver", None, Decimal("1240"), Decimal("520"), 12, 4),
    ("DEMO-EAR-NOVA", "DEMO Сережки Nova", "earrings", "DEMO-EAR-NOVA-PEARL", "Pearl", None, Decimal("760"), Decimal("280"), 0, 3),
    ("DEMO-WATCH-MIRA", "DEMO Годинник Mira", "watches", "DEMO-WATCH-MIRA-BLACK", "Black", None, Decimal("2100"), Decimal("1100"), 7, 2),
]
DEMO_CUSTOMERS = [
    ("DEMO Олена К.", "@olena_demo"),
    ("DEMO Марія С.", "@maria_demo"),
    ("DEMO Ірина П.", "@iryna_demo"),
]


def get_or_create_workspace(db: Session) -> Workspace:
    workspace = db.execute(select(Workspace).where(Workspace.slug == DEMO_WORKSPACE_SLUG)).scalar_one_or_none()
    if workspace is None:
        workspace = Workspace(name=DEMO_WORKSPACE_NAME, slug=DEMO_WORKSPACE_SLUG, subscription_plan="demo")
        db.add(workspace)
        db.flush()
    return workspace


def seed_products(db: Session, workspace: Workspace) -> list[ProductVariant]:
    variants: list[ProductVariant] = []
    for product_sku, name, category, variant_sku, color, size, price, _cost, stock, minimum in DEMO_PRODUCTS:
        product = db.execute(select(Product).where(Product.workspace_id == workspace.id, Product.sku == product_sku, Product.deleted_at.is_(None))).scalar_one_or_none()
        if product is None:
            product = Product(workspace_id=workspace.id, sku=product_sku, name=name, category=category, brand="DEMO", is_active=True)
            db.add(product)
            db.flush()
        variant = db.execute(select(ProductVariant).where(ProductVariant.workspace_id == workspace.id, ProductVariant.sku == variant_sku, ProductVariant.deleted_at.is_(None))).scalar_one_or_none()
        if variant is None:
            variant = ProductVariant(workspace_id=workspace.id, product_id=product.id, sku=variant_sku, color=color, size=size, price=price, is_active=True)
            db.add(variant)
            db.flush()
        inventory = db.execute(select(Inventory).where(Inventory.workspace_id == workspace.id, Inventory.product_variant_id == variant.id, Inventory.deleted_at.is_(None))).scalar_one_or_none()
        if inventory is None:
            db.add(Inventory(workspace_id=workspace.id, product_variant_id=variant.id, stock_quantity=stock, reserved_quantity=0, incoming_quantity=2 if stock <= minimum else 0, minimum_quantity=minimum))
        variants.append(variant)
    return variants


def seed_customers_and_leads(db: Session, workspace: Workspace) -> list[Customer]:
    customers = []
    for name, instagram in DEMO_CUSTOMERS:
        customer = db.execute(select(Customer).where(Customer.workspace_id == workspace.id, Customer.instagram_username == instagram.lstrip("@"), Customer.deleted_at.is_(None))).scalar_one_or_none()
        if customer is None:
            customer = Customer(workspace_id=workspace.id, name=name, instagram_username=instagram.lstrip("@"))
            db.add(customer)
            db.flush()
        customers.append(customer)
        lead = db.execute(select(Lead).where(Lead.workspace_id == workspace.id, Lead.instagram_username == instagram.lstrip("@"), Lead.deleted_at.is_(None))).scalar_one_or_none()
        if lead is None:
            db.add(Lead(workspace_id=workspace.id, name=name, instagram_username=instagram.lstrip("@"), status=LeadStatus.CONVERTED.value))
    return customers


def seed_orders_and_shipments(db: Session, workspace: Workspace, customers: list[Customer], variants: list[ProductVariant]) -> None:
    service = OrderService(db)
    today = datetime.now(UTC)
    for index in range(12):
        order_number = f"ORD-2026-DEMO-{index + 1:03d}"
        existing = db.execute(select(Order).where(Order.workspace_id == workspace.id, Order.order_number == order_number, Order.deleted_at.is_(None))).scalar_one_or_none()
        if existing:
            continue
        variant = variants[index % len(variants)]
        product_cost = DEMO_PRODUCTS[index % len(DEMO_PRODUCTS)][7]
        status = [OrderStatus.COMPLETED, OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.CONFIRMED][index % 4]
        created_at = today - timedelta(days=index)
        order = service.create(
            workspace.id,
            OrderCreate(customer_id=customers[index % len(customers)].id, status=status, payment_status=PaymentStatus.PAID, is_historical=True, items=[OrderItemCreate(product_variant_id=variant.id, quantity=1 + (index % 2), unit_price=variant.price or Decimal("0"), unit_cost=product_cost)], ad_cost=Decimal("35"), shipping_cost=Decimal("65"), cod_fee=Decimal("0"), other_cost=Decimal("0"), notes="Synthetic DEMO order"),
            actor_user_id=None,
            affect_inventory=False,
            order_number=order_number,
            created_at=created_at,
            completed_at=created_at if status in {OrderStatus.COMPLETED, OrderStatus.DELIVERED} else None,
        )
        if index < 6 and not db.execute(select(Shipment).where(Shipment.workspace_id == workspace.id, Shipment.order_id == order.id, Shipment.deleted_at.is_(None))).scalar_one_or_none():
            db.add(Shipment(workspace_id=workspace.id, order_id=order.id, customer_id=order.customer_id, tracking_number=f"DEMO-TTN-{index + 1:03d}", carrier=ShipmentCarrier.NOVA_POSHTA.value, status=ShipmentStatus.DELIVERED.value if status in {OrderStatus.COMPLETED, OrderStatus.DELIVERED} else ShipmentStatus.IN_TRANSIT.value, notes="Synthetic DEMO shipment"))


def seed_advertising(db: Session, workspace: Workspace) -> None:
    campaign = db.execute(select(AdCampaign).where(AdCampaign.workspace_id == workspace.id, AdCampaign.name == "DEMO Instagram Launch", AdCampaign.deleted_at.is_(None))).scalar_one_or_none()
    if campaign is None:
        campaign = AdCampaign(workspace_id=workspace.id, name="DEMO Instagram Launch", platform=AdCampaignPlatform.INSTAGRAM.value, status=AdCampaignStatus.ACTIVE.value, objective=AdCampaignObjective.SALES.value, budget_type=AdCampaignBudgetType.DAILY.value, daily_budget=Decimal("250"))
        db.add(campaign)
        db.flush()
    today = datetime.now(UTC).date()
    for offset in range(14):
        metric_date = today - timedelta(days=offset)
        metric = db.execute(select(AdMetric).where(AdMetric.workspace_id == workspace.id, AdMetric.campaign_id == campaign.id, AdMetric.metric_date == metric_date, AdMetric.deleted_at.is_(None))).scalar_one_or_none()
        if metric is None:
            spend = Decimal("180") + Decimal(offset * 3)
            revenue = Decimal("520") + Decimal(offset * 15)
            db.add(AdMetric(workspace_id=workspace.id, campaign_id=campaign.id, metric_date=metric_date, spend=spend, impressions=3200 + offset * 80, reach=2100 + offset * 60, clicks=120 + offset, messages=24 + offset, leads=8 + offset % 3, orders=2 + offset % 2, revenue=revenue, net_profit=revenue - spend - Decimal("260")))


def main() -> None:
    db = SessionLocal()
    try:
        workspace = get_or_create_workspace(db)
        variants = seed_products(db, workspace)
        customers = seed_customers_and_leads(db, workspace)
        db.commit()
        seed_orders_and_shipments(db, workspace, customers, variants)
        seed_advertising(db, workspace)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
