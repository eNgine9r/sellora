"""Regression tests for trustworthy Nova Poshta historical reconciliation."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.models.order import OrderStatus
from app.models.shipment import ShipmentStatus
from app.schemas.order import OrderItemCreate
from app.services.nova_poshta_service import NovaPoshtaShipmentService
from app.services.order_service import OrderService


@pytest.mark.parametrize(
    ("provider_status", "expected"),
    [
        ("Прибув у відділення", ShipmentStatus.ARRIVED),
        ("Прибув до відділення №2", ShipmentStatus.ARRIVED),
        ("Відправлення прямує до м. Кагарлик.", ShipmentStatus.IN_TRANSIT),
        ("Вручено отримувачу", ShipmentStatus.DELIVERED),
        ("Повернення відправнику", ShipmentStatus.RETURNED),
        ("Невідомий статус постачальника", None),
    ],
)
def test_nova_poshta_status_mapping(provider_status, expected):
    service = NovaPoshtaShipmentService.__new__(NovaPoshtaShipmentService)
    assert service._normalize_provider_status(provider_status) == expected


def test_historical_order_item_correction_does_not_touch_inventory():
    workspace_id, variant_id, order_id = uuid4(), uuid4(), uuid4()
    order = SimpleNamespace(
        id=order_id,
        is_historical=True,
        status=OrderStatus.DELIVERED.value,
        items=[SimpleNamespace(product_variant_id=variant_id)],
        revenue=Decimal("0"),
        product_cost=Decimal("0"),
    )
    variant = SimpleNamespace(
        id=variant_id, workspace_id=workspace_id, deleted_at=None,
        sku="NP-ARCHIVE-OTHER", product=SimpleNamespace(name="Історичний товар"),
        is_active=False,
    )
    service = OrderService.__new__(OrderService)
    service.db = MagicMock()
    service.db.get.return_value = variant
    service.orders = MagicMock()
    service.audit_logs = MagicMock()
    service._inventory_transaction = MagicMock()
    service.inventory = MagicMock()
    service._get_variant = MagicMock()
    corrected = OrderItemCreate(
        product_variant_id=variant_id, quantity=1,
        unit_price=Decimal("680.00"), unit_cost=Decimal("210.00"),
    )
    service._replace_items_for_update(workspace_id, order, [corrected], actor_user_id=None)

    assert order.revenue == Decimal("680.00")
    assert order.product_cost == Decimal("210.00")
    service._inventory_transaction.assert_not_called()
    service.inventory.get_by_variant.assert_not_called()
    service._get_variant.assert_not_called()
    service.orders.add_item.assert_called_once()
    assert service.orders.add_item.call_args.args[0].line_total == Decimal("680.00")
    assert service.audit_logs.create.call_args.kwargs["action"] == "HISTORICAL_ORDER_ITEMS_CORRECTED"


def test_historical_order_status_skips_live_inventory():
    service = OrderService.__new__(OrderService)
    service._inventory_transaction = MagicMock()
    service.inventory = MagicMock()
    order = SimpleNamespace(is_historical=True, items=[])
    service._apply_transition_inventory(
        uuid4(), order, OrderStatus.CONFIRMED, OrderStatus.SHIPPED, None,
    )
    service._inventory_transaction.assert_not_called()
    service.inventory.get_by_variant.assert_not_called()


def test_provider_arrival_projects_historical_order_without_changing_payment(monkeypatch):
    workspace_id = uuid4()
    order = SimpleNamespace(
        id=uuid4(), workspace_id=workspace_id, is_historical=True,
        status=OrderStatus.CONFIRMED.value, payment_status="PENDING",
        revenue=Decimal("0.00"),
    )
    shipment = SimpleNamespace(order=order)
    service = NovaPoshtaShipmentService.__new__(NovaPoshtaShipmentService)
    service.db = MagicMock()
    service.audit_logs = MagicMock()
    calls = []

    class FakeOrderService:
        def __init__(self, db):
            pass

        def change_status(self, ws, order_id, payload, actor, commit):
            calls.append((ws, payload.status, commit))
            order.status = payload.status.value

    monkeypatch.setattr("app.services.nova_poshta_service.OrderService", FakeOrderService)
    service._sync_historical_order_status(workspace_id, shipment, ShipmentStatus.ARRIVED, None)

    assert calls == [(workspace_id, OrderStatus.SHIPPED, False)]
    assert order.payment_status == "PENDING"
    assert order.revenue == Decimal("0.00")


def test_live_order_is_not_auto_projected_from_tracking(monkeypatch):
    workspace_id = uuid4()
    order = SimpleNamespace(
        id=uuid4(), workspace_id=workspace_id,
        is_historical=False, status=OrderStatus.CONFIRMED.value,
    )
    service = NovaPoshtaShipmentService.__new__(NovaPoshtaShipmentService)
    service.db = MagicMock()
    service.audit_logs = MagicMock()
    constructor = MagicMock()
    monkeypatch.setattr("app.services.nova_poshta_service.OrderService", constructor)
    service._sync_historical_order_status(
        workspace_id, SimpleNamespace(order=order),
        ShipmentStatus.DELIVERED, None,
    )
    constructor.assert_not_called()
