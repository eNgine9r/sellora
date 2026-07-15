from types import SimpleNamespace
from uuid import uuid4

from app.models.shipment import Shipment, ShipmentCarrier, ShipmentStatus
from app.services.nova_poshta_service import NovaPoshtaShipmentService
from tests.test_nova_poshta import _shipment_service


def _eligible_shipment() -> Shipment:
    shipment = Shipment(
        id=uuid4(),
        workspace_id=uuid4(),
        order_id=uuid4(),
        customer_id=uuid4(),
        carrier=ShipmentCarrier.NOVA_POSHTA.value,
        status=ShipmentStatus.DRAFT.value,
        recipient_name="QA8E Recipient",
        recipient_phone="0000000000",
        city="Kyiv",
        warehouse="Warehouse 1",
        nova_poshta_city_ref="city-ref",
        nova_poshta_warehouse_ref="warehouse-ref",
        declared_value=100,
    )
    shipment.order = SimpleNamespace(order_number="QA8E-ORDER")
    return shipment


def test_provider_write_flag_blocks_ttn_before_provider_call() -> None:
    shipment = _eligible_shipment()
    service = _shipment_service(shipment)
    service.provider_writes_enabled = False
    client = service.settings.client_factory("synthetic-credential-value")
    service.settings.client_factory = lambda _credential: client

    response = service.create_ttn(shipment.workspace_id, shipment.id, uuid4())

    assert not response.success
    assert response.errors == ["NOVA_POSHTA_PROVIDER_WRITES_DISABLED"]
    assert not client.create_called
    assert shipment.tracking_number is None


def test_in_progress_guard_blocks_duplicate_ttn_without_provider_call() -> None:
    shipment = _eligible_shipment()
    service = _shipment_service(shipment)
    client = service.settings.client_factory("synthetic-credential-value")
    service.settings.client_factory = lambda _credential: client
    NovaPoshtaShipmentService._in_progress_ttn_keys.add((shipment.workspace_id, shipment.id))
    try:
        response = service.create_ttn(shipment.workspace_id, shipment.id, uuid4())
    finally:
        NovaPoshtaShipmentService._in_progress_ttn_keys.discard((shipment.workspace_id, shipment.id))

    assert not response.success
    assert response.errors == ["NOVA_POSHTA_TTN_IN_PROGRESS"]
    assert not client.create_called
    assert shipment.tracking_number is None


def test_tracking_refresh_maps_known_provider_status_without_order_inventory_side_effects() -> None:
    shipment = _eligible_shipment()
    shipment.status = ShipmentStatus.CREATED.value
    shipment.tracking_number = "TTN-001"
    shipment.nova_poshta_document_number = "TTN-001"
    service = _shipment_service(shipment)
    service.settings.client_factory = lambda _credential: SimpleNamespace(get_document_status=lambda _tracking: "Delivered to recipient")

    response = service.sync_status(shipment.workspace_id, shipment.id, uuid4())

    assert response.success
    assert shipment.status == ShipmentStatus.DELIVERED.value
    assert shipment.nova_poshta_raw_status == "Delivered to recipient"
    assert shipment.external_status == "Delivered to recipient"


def test_unknown_provider_status_keeps_previous_normalized_status() -> None:
    shipment = _eligible_shipment()
    shipment.status = ShipmentStatus.IN_TRANSIT.value
    shipment.tracking_number = "TTN-001"
    shipment.nova_poshta_document_number = "TTN-001"
    service = _shipment_service(shipment)
    service.settings.client_factory = lambda _credential: SimpleNamespace(get_document_status=lambda _tracking: "Provider status needs support review")

    response = service.sync_status(shipment.workspace_id, shipment.id, uuid4())

    assert response.success
    assert shipment.status == ShipmentStatus.IN_TRANSIT.value
    assert shipment.nova_poshta_raw_status == "Provider status needs support review"
