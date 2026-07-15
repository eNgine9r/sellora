from uuid import uuid4

import pytest

from app.models.order import OrderStatus
from app.models.shipment import ShipmentStatus
from app.services.shipment_service import ShipmentServiceError
from tests.test_shipments import _create_payload, _service


def test_cancelled_or_returned_orders_cannot_receive_new_shipment() -> None:
    for status in (OrderStatus.CANCELLED.value, OrderStatus.RETURNED.value):
        service, workspace_id, order = _service(status)
        with pytest.raises(ShipmentServiceError, match="cancelled or returned"):
            service.create(workspace_id, _create_payload(order.id), uuid4())


def test_repeated_local_status_update_is_idempotent() -> None:
    service, workspace_id, order = _service(OrderStatus.CONFIRMED.value)
    shipment = service.create(workspace_id, _create_payload(order.id, status=ShipmentStatus.CREATED), uuid4())

    service.change_status(workspace_id, shipment.id, ShipmentStatus.IN_TRANSIT, uuid4())
    service.change_status(workspace_id, shipment.id, ShipmentStatus.IN_TRANSIT, uuid4())

    assert service.order_service.transitions == [OrderStatus.SHIPPED]
    assert service.audit_logs.actions.count("SHIPMENT_STATUS_CHANGE") == 1


def test_one_active_shipment_rule_preserves_existing_shipment() -> None:
    service, workspace_id, order = _service()
    first = service.create(workspace_id, _create_payload(order.id, tracking=None), uuid4())

    with pytest.raises(ShipmentServiceError, match="Active shipment"):
        service.create(workspace_id, _create_payload(order.id, tracking=None), uuid4())

    assert len(service.shipments.shipments) == 1
    assert service.shipments.shipments[0].id == first.id
