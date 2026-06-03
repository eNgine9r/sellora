from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.models.customer import Customer
from app.models.inventory import Inventory
from app.models.inventory_transaction import InventoryTransactionType
from app.models.order import OrderStatus
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.schemas.order import OrderCreate, OrderItemCreate, OrderStatusUpdate
from app.services.order_service import OrderService


class FakeDb:
    def __init__(self, variant: ProductVariant, customer: Customer | None = None) -> None:
        self.variant = variant
        self.customer = customer

    def commit(self) -> None:
        pass

    def refresh(self, model) -> None:
        pass

    def get(self, model, model_id):
        if model is ProductVariant and model_id == self.variant.id:
            return self.variant
        if model is Customer and self.customer and model_id == self.customer.id:
            return self.customer
        return None


class FakeAuditLogs:
    def __init__(self) -> None:
        self.records = []

    def create(self, **kwargs):
        self.records.append(kwargs)
        return SimpleNamespace(**kwargs)


class FakeOrders:
    def __init__(self) -> None:
        self.order = None
        self.items = []
        self.history = []

    def create(self, order):
        order.id = order.id or uuid4()
        self.order = order
        return order

    def add_item(self, item):
        item.id = item.id or uuid4()
        self.items.append(item)
        self.order.items = self.items
        return item

    def add_status_history(self, history):
        history.id = history.id or uuid4()
        self.history.append(history)
        self.order.status_history = self.history
        return history

    def get(self, workspace_id, order_id):
        if self.order and self.order.workspace_id == workspace_id and self.order.id == order_id:
            return self.order
        return None

    def next_sequence_for_year(self, workspace_id, year):
        return 1

    def dashboard_today(self, workspace_id):
        return (1, Decimal("100.00"), Decimal("40.00"))


class FakeInventoryRepo:
    def __init__(self, inventory: Inventory) -> None:
        self.inventory = inventory

    def get_by_variant(self, workspace_id, product_variant_id):
        if self.inventory.workspace_id == workspace_id and self.inventory.product_variant_id == product_variant_id:
            return self.inventory
        return None


class FakeInventoryService:
    def __init__(self, inventory: Inventory) -> None:
        self.inventory = inventory
        self.transactions = []

    def record_transaction(self, workspace_id, inventory_id, payload, actor_user_id, commit=True):
        previous_stock = self.inventory.stock_quantity
        previous_reserved = self.inventory.reserved_quantity
        if payload.transaction_type == InventoryTransactionType.RESERVE:
            self.inventory.reserved_quantity += payload.quantity
        elif payload.transaction_type == InventoryTransactionType.UNRESERVE:
            self.inventory.reserved_quantity -= payload.quantity
        elif payload.transaction_type == InventoryTransactionType.STOCK_OUT:
            self.inventory.stock_quantity -= payload.quantity
        elif payload.transaction_type == InventoryTransactionType.RETURN:
            self.inventory.stock_quantity += payload.quantity
        self.transactions.append((payload.transaction_type, previous_stock, self.inventory.stock_quantity, previous_reserved, self.inventory.reserved_quantity))
        return SimpleNamespace(id=uuid4(), transaction_type=payload.transaction_type.value)


def _service() -> tuple[OrderService, Inventory, Customer]:
    workspace_id = uuid4()
    customer = Customer(id=uuid4(), workspace_id=workspace_id, name="Customer", total_orders=0, total_spent=Decimal("0"))
    product = Product(id=uuid4(), workspace_id=workspace_id, name="Dress", sku="DR")
    variant = ProductVariant(id=uuid4(), workspace_id=workspace_id, product_id=product.id, sku="DR-RED-S", color="Red", size="S", product=product)
    inventory = Inventory(id=uuid4(), workspace_id=workspace_id, product_variant_id=variant.id, stock_quantity=10, reserved_quantity=0, minimum_quantity=2)
    service = OrderService.__new__(OrderService)
    service.db = FakeDb(variant, customer)
    service.orders = FakeOrders()
    service.inventory = FakeInventoryRepo(inventory)
    service.inventory_service = FakeInventoryService(inventory)
    service.audit_logs = FakeAuditLogs()
    return service, inventory, customer


def _create_order(service: OrderService, inventory: Inventory, customer: Customer):
    return service.create(
        inventory.workspace_id,
        OrderCreate(
            customer_id=customer.id,
            items=[OrderItemCreate(product_variant_id=inventory.product_variant_id, quantity=2, unit_price=Decimal("50"), unit_cost=Decimal("20"))],
            ad_cost=Decimal("10"),
            shipping_cost=Decimal("5"),
            cod_fee=Decimal("3"),
            other_cost=Decimal("2"),
        ),
        actor_user_id=uuid4(),
    )


def test_order_creation_generates_number_reserves_inventory_and_calculates_profit() -> None:
    service, inventory, customer = _service()

    order = _create_order(service, inventory, customer)

    assert order.order_number.startswith("ORD-")
    assert order.order_number.endswith("000001")
    assert inventory.reserved_quantity == 2
    assert order.revenue == Decimal("100")
    assert order.product_cost == Decimal("40")
    assert order.net_profit == Decimal("40")
    assert service.inventory_service.transactions[-1][0] == InventoryTransactionType.RESERVE


def test_shipping_order_decreases_stock_and_reserved_quantities() -> None:
    service, inventory, customer = _service()
    order = _create_order(service, inventory, customer)

    service.change_status(inventory.workspace_id, order.id, OrderStatusUpdate(status=OrderStatus.SHIPPED), actor_user_id=uuid4())

    assert inventory.reserved_quantity == 0
    assert inventory.stock_quantity == 8


def test_cancelling_order_returns_reservation() -> None:
    service, inventory, customer = _service()
    order = _create_order(service, inventory, customer)

    service.change_status(inventory.workspace_id, order.id, OrderStatusUpdate(status=OrderStatus.CANCELLED), actor_user_id=uuid4())

    assert inventory.reserved_quantity == 0
    assert inventory.stock_quantity == 10


def test_returning_order_restores_inventory_after_shipping() -> None:
    service, inventory, customer = _service()
    order = _create_order(service, inventory, customer)
    service.change_status(inventory.workspace_id, order.id, OrderStatusUpdate(status=OrderStatus.SHIPPED), actor_user_id=uuid4())

    service.change_status(inventory.workspace_id, order.id, OrderStatusUpdate(status=OrderStatus.RETURNED), actor_user_id=uuid4())

    assert inventory.stock_quantity == 10


def test_completed_order_updates_customer_metrics() -> None:
    service, inventory, customer = _service()
    order = _create_order(service, inventory, customer)

    service.change_status(inventory.workspace_id, order.id, OrderStatusUpdate(status=OrderStatus.COMPLETED), actor_user_id=uuid4())

    assert customer.total_orders == 1
    assert customer.total_spent == Decimal("100")
    assert customer.last_order_at is not None
