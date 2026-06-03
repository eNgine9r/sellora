from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.dependencies.rbac import require_roles
from app.models.customer import Customer
from app.models.inventory import Inventory
from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.role import RoleName
from app.services.analytics_service import AnalyticsService


class FakeAnalyticsRepository:
    def __init__(self, workspace_id):
        self.workspace_id = workspace_id
        today = datetime.now(UTC)
        yesterday = today - timedelta(days=1)
        self.product = Product(id=uuid4(), workspace_id=workspace_id, name="Dress", sku="DR")
        self.variant = ProductVariant(id=uuid4(), workspace_id=workspace_id, product_id=self.product.id, sku="DR-RED-S", color="Red", size="S")
        self.orders = [
            Order(id=uuid4(), workspace_id=workspace_id, status=OrderStatus.COMPLETED.value, revenue=Decimal("100"), product_cost=Decimal("40"), ad_cost=Decimal("10"), shipping_cost=Decimal("5"), cod_fee=Decimal("3"), other_cost=Decimal("2"), net_profit=Decimal("40"), created_at=yesterday, completed_at=yesterday),
            Order(id=uuid4(), workspace_id=workspace_id, status=OrderStatus.CANCELLED.value, revenue=Decimal("50"), product_cost=Decimal("20"), ad_cost=Decimal("5"), shipping_cost=Decimal("2"), cod_fee=Decimal("1"), other_cost=Decimal("1"), net_profit=Decimal("21"), created_at=today, completed_at=None),
            Order(id=uuid4(), workspace_id=workspace_id, status=OrderStatus.RETURNED.value, revenue=Decimal("25"), product_cost=Decimal("10"), ad_cost=Decimal("2"), shipping_cost=Decimal("1"), cod_fee=Decimal("0"), other_cost=Decimal("0"), net_profit=Decimal("12"), created_at=today, completed_at=None),
            Order(id=uuid4(), workspace_id=uuid4(), status=OrderStatus.COMPLETED.value, revenue=Decimal("999"), product_cost=Decimal("1"), ad_cost=Decimal("0"), shipping_cost=Decimal("0"), cod_fee=Decimal("0"), other_cost=Decimal("0"), net_profit=Decimal("998"), created_at=today, completed_at=today),
        ]
        self.items = [
            (OrderItem(id=uuid4(), workspace_id=workspace_id, order_id=self.orders[0].id, product_variant_id=self.variant.id, sku=self.variant.sku, product_name=self.product.name, quantity=2, unit_price=Decimal("50"), unit_cost=Decimal("20"), line_total=Decimal("100"), line_cost=Decimal("40")), self.orders[0], self.variant, self.product),
            (OrderItem(id=uuid4(), workspace_id=workspace_id, order_id=self.orders[1].id, product_variant_id=self.variant.id, sku=self.variant.sku, product_name=self.product.name, quantity=1, unit_price=Decimal("50"), unit_cost=Decimal("20"), line_total=Decimal("50"), line_cost=Decimal("20")), self.orders[1], self.variant, self.product),
        ]
        self.customers = [
            Customer(id=uuid4(), workspace_id=workspace_id, name="Repeat", phone="1", instagram_username="repeat", total_orders=2, total_spent=Decimal("150"), created_at=yesterday),
            Customer(id=uuid4(), workspace_id=workspace_id, name="New", phone="2", instagram_username="new", total_orders=1, total_spent=Decimal("25"), created_at=today),
            Customer(id=uuid4(), workspace_id=uuid4(), name="Other", total_orders=9, total_spent=Decimal("999"), created_at=today),
        ]
        self.inventory_rows = [
            (Inventory(id=uuid4(), workspace_id=workspace_id, product_variant_id=self.variant.id, stock_quantity=2, reserved_quantity=1, minimum_quantity=2), self.variant, self.product),
            (Inventory(id=uuid4(), workspace_id=workspace_id, product_variant_id=uuid4(), stock_quantity=0, reserved_quantity=0, minimum_quantity=1), ProductVariant(id=uuid4(), workspace_id=workspace_id, product_id=self.product.id, sku="DR-BLK-M", color="Black", size="M"), self.product),
            (Inventory(id=uuid4(), workspace_id=uuid4(), product_variant_id=uuid4(), stock_quantity=100, reserved_quantity=0, minimum_quantity=1), self.variant, self.product),
        ]

    def list_orders(self, workspace_id, start_at, end_at):
        return [order for order in self.orders if order.workspace_id == workspace_id and start_at <= (order.completed_at or order.created_at) <= end_at]

    def list_order_items(self, workspace_id, start_at, end_at):
        return [(item, order, variant, product) for item, order, variant, product in self.items if order.workspace_id == workspace_id and start_at <= (order.completed_at or order.created_at) <= end_at]

    def list_customers(self, workspace_id):
        return [customer for customer in self.customers if customer.workspace_id == workspace_id]

    def list_inventory_items(self, workspace_id):
        return [row for row in self.inventory_rows if row[0].workspace_id == workspace_id]


def _service() -> tuple[AnalyticsService, FakeAnalyticsRepository]:
    workspace_id = uuid4()
    repo = FakeAnalyticsRepository(workspace_id)
    service = AnalyticsService.__new__(AnalyticsService)
    service.repository = repo
    return service, repo


def test_sales_summary() -> None:
    service, repo = _service()
    summary = service.sales_summary(repo.workspace_id)

    assert summary.total_orders == 3
    assert summary.total_revenue == Decimal("175.00")
    assert summary.average_order_value == Decimal("58.33")
    assert summary.completed_orders == 1
    assert summary.cancelled_orders == 1
    assert summary.returned_orders == 1


def test_profit_summary() -> None:
    service, repo = _service()
    summary = service.profit_summary(repo.workspace_id)

    assert summary.total_revenue == Decimal("175.00")
    assert summary.total_product_cost == Decimal("70.00")
    assert summary.total_net_profit == Decimal("73.00")
    assert summary.margin_percent == Decimal("41.71")


def test_sales_trend() -> None:
    service, repo = _service()
    trend = service.sales_trend(repo.workspace_id)

    assert len(trend) == 2
    assert sum(day.orders_count for day in trend) == 3
    assert sum(day.revenue for day in trend) == Decimal("175.00")


def test_top_products() -> None:
    service, repo = _service()
    products = service.top_products(repo.workspace_id)

    assert products[0].product_name == "Dress"
    assert products[0].quantity_sold == 3
    assert products[0].revenue == Decimal("150.00")
    assert products[0].net_profit == Decimal("90.00")


def test_customer_summary() -> None:
    service, repo = _service()
    summary = service.customers_summary(repo.workspace_id)

    assert summary.total_customers == 2
    assert summary.new_customers == 2
    assert summary.repeat_customers == 1
    assert summary.repeat_purchase_rate == Decimal("50.00")
    assert summary.top_customers[0].name == "Repeat"


def test_inventory_summary() -> None:
    service, repo = _service()
    summary = service.inventory_summary(repo.workspace_id)

    assert summary.total_variants == 2
    assert summary.low_stock_count == 2
    assert summary.out_of_stock_count == 1
    assert summary.total_stock_units == 2


def test_dashboard_endpoint_payload() -> None:
    service, repo = _service()
    dashboard = service.dashboard(repo.workspace_id)

    assert dashboard.today_orders >= 2
    assert dashboard.month_revenue == Decimal("175.00")
    assert dashboard.low_stock_count == 2
    assert dashboard.top_products
    assert dashboard.sales_trend


def test_workspace_isolation_excludes_other_workspace_records() -> None:
    service, repo = _service()
    summary = service.sales_summary(repo.workspace_id)

    assert summary.total_revenue != Decimal("1174.00")
    assert summary.total_orders == 3


def test_profit_analytics_rejects_manager_role() -> None:
    workspace_id = uuid4()
    manager = SimpleNamespace(
        workspaces=[SimpleNamespace(workspace_id=workspace_id, workspace=SimpleNamespace(is_active=True), role=SimpleNamespace(name=RoleName.MANAGER.value))]
    )
    guard = require_roles(RoleName.OWNER, RoleName.ANALYST)

    with pytest.raises(HTTPException) as exc:
        guard(manager, workspace_id)

    assert exc.value.status_code == 403
