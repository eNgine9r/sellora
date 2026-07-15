from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.inventory_transaction import InventoryTransactionType
from app.models.order import OrderStatus
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.schemas.order import OrderCreate, OrderItemCreate, OrderStatusUpdate, OrderUpdate
from app.services.order_service import OrderServiceError
from tests.test_orders import _add_second_variant, _create_order, _service


def test_invalid_status_transition_is_rejected_without_inventory_change() -> None:
    service, inventory, customer = _service()
    order = _create_order(service, inventory, customer)

    with pytest.raises(OrderServiceError, match="not allowed"):
        service.change_status(inventory.workspace_id, order.id, OrderStatusUpdate(status=OrderStatus.DELIVERED), actor_user_id=uuid4())

    assert order.status == OrderStatus.NEW.value
    assert inventory.stock_quantity == 10
    assert inventory.reserved_quantity == 2


def test_repeated_shipment_transition_deducts_stock_once_and_adds_history_once() -> None:
    service, inventory, customer = _service()
    order = _create_order(service, inventory, customer)
    service.change_status(inventory.workspace_id, order.id, OrderStatusUpdate(status=OrderStatus.CONFIRMED), actor_user_id=uuid4())

    first = service.change_status(inventory.workspace_id, order.id, OrderStatusUpdate(status=OrderStatus.SHIPPED), actor_user_id=uuid4())
    second = service.change_status(inventory.workspace_id, order.id, OrderStatusUpdate(status=OrderStatus.SHIPPED), actor_user_id=uuid4())

    assert first is second
    assert inventory.stock_quantity == 8
    assert inventory.reserved_quantity == 0
    assert [tx[0] for tx in service.inventory_service.transactions].count(InventoryTransactionType.STOCK_OUT) == 1
    assert [history.to_status for history in service.orders.history].count(OrderStatus.SHIPPED.value) == 1


def test_return_after_delivery_restores_stock_once() -> None:
    service, inventory, customer = _service()
    order = _create_order(service, inventory, customer)
    service.change_status(inventory.workspace_id, order.id, OrderStatusUpdate(status=OrderStatus.CONFIRMED), actor_user_id=uuid4())
    service.change_status(inventory.workspace_id, order.id, OrderStatusUpdate(status=OrderStatus.SHIPPED), actor_user_id=uuid4())
    service.change_status(inventory.workspace_id, order.id, OrderStatusUpdate(status=OrderStatus.DELIVERED), actor_user_id=uuid4())

    service.change_status(inventory.workspace_id, order.id, OrderStatusUpdate(status=OrderStatus.RETURNED), actor_user_id=uuid4())
    service.change_status(inventory.workspace_id, order.id, OrderStatusUpdate(status=OrderStatus.RETURNED), actor_user_id=uuid4())

    assert inventory.stock_quantity == 10
    assert inventory.reserved_quantity == 0
    assert [tx[0] for tx in service.inventory_service.transactions].count(InventoryTransactionType.RETURN) == 1


def test_archived_variant_is_rejected_for_new_order_and_edit() -> None:
    service, inventory, customer = _service()
    variant = service.db.variants[inventory.product_variant_id]
    variant.is_active = False

    with pytest.raises(OrderServiceError, match="archived"):
        service.create(
            inventory.workspace_id,
            OrderCreate(customer_id=customer.id, items=[OrderItemCreate(product_variant_id=inventory.product_variant_id, quantity=1, unit_price=Decimal("50"), unit_cost=Decimal("20"))]),
            actor_user_id=uuid4(),
        )

    variant.is_active = True
    order = _create_order(service, inventory, customer)
    second_variant, _second_inventory = _add_second_variant(service, inventory.workspace_id)
    second_variant.is_active = False

    with pytest.raises(OrderServiceError, match="archived"):
        service.update(inventory.workspace_id, order.id, OrderUpdate(items=[OrderItemCreate(product_variant_id=second_variant.id, quantity=1, unit_price=Decimal("50"), unit_cost=Decimal("20"))]), actor_user_id=uuid4())


def test_product_inactive_variant_is_rejected() -> None:
    service, inventory, customer = _service()
    variant = service.db.variants[inventory.product_variant_id]
    product = Product(id=variant.product_id, workspace_id=inventory.workspace_id, name="Inactive product", sku="INACTIVE", is_active=False)
    variant.product = product

    with pytest.raises(OrderServiceError, match="archived"):
        service.create(
            inventory.workspace_id,
            OrderCreate(customer_id=customer.id, items=[OrderItemCreate(product_variant_id=inventory.product_variant_id, quantity=1, unit_price=Decimal("50"), unit_cost=Decimal("20"))]),
            actor_user_id=uuid4(),
        )
