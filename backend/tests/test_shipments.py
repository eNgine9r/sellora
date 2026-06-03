from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.dependencies.rbac import require_min_role
from app.models.customer import Customer
from app.models.order import Order, OrderStatus
from app.models.role import RoleName
from app.models.shipment import Shipment, ShipmentCarrier, ShipmentStatus
from app.schemas.order import OrderStatusUpdate
from app.schemas.shipment import ShipmentCreate
from app.services.import_center_service import MappingSuggestionService, MappingValidationService
from app.services.shipment_service import ShipmentService, ShipmentServiceError


class FakeDb:
    def __init__(self, customer=None) -> None:
        self.customer = customer
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, obj) -> None:
        pass

    def get(self, model, obj_id):
        if model is Customer and self.customer and self.customer.id == obj_id:
            return self.customer
        return None


class FakeShipmentRepo:
    def __init__(self, workspace_id, order) -> None:
        self.workspace_id = workspace_id
        self.order = order
        self.shipments = []

    def list(self, workspace_id, status=None, search=None):
        rows = [item for item in self.shipments if item.workspace_id == workspace_id and item.deleted_at is None]
        if status:
            rows = [item for item in rows if item.status == status]
        if search:
            rows = [item for item in rows if item.tracking_number and search in item.tracking_number]
        return rows

    def get(self, workspace_id, shipment_id):
        for shipment in self.shipments:
            if shipment.workspace_id == workspace_id and shipment.id == shipment_id and shipment.deleted_at is None:
                return shipment
        return None

    def get_by_order(self, workspace_id, order_id):
        for shipment in self.shipments:
            if shipment.workspace_id == workspace_id and shipment.order_id == order_id and shipment.deleted_at is None:
                return shipment
        return None

    def find_active_by_order(self, workspace_id, order_id, exclude_shipment_id=None):
        for shipment in self.shipments:
            if shipment.workspace_id == workspace_id and shipment.order_id == order_id and shipment.deleted_at is None and shipment.status != ShipmentStatus.CANCELLED.value and shipment.id != exclude_shipment_id:
                return shipment
        return None

    def find_by_tracking_number(self, workspace_id, tracking_number, exclude_shipment_id=None):
        for shipment in self.shipments:
            if tracking_number and shipment.workspace_id == workspace_id and shipment.tracking_number == tracking_number and shipment.deleted_at is None and shipment.id != exclude_shipment_id:
                return shipment
        return None

    def create(self, shipment):
        shipment.id = shipment.id or uuid4()
        shipment.created_at = shipment.created_at or datetime.now(UTC)
        shipment.updated_at = shipment.updated_at or datetime.now(UTC)
        shipment.order = self.order
        shipment.customer = None
        self.shipments.append(shipment)
        return shipment

    def summary_counts(self, workspace_id):
        return 1, 2, 3, 4


class FakeOrderRepo:
    def __init__(self, workspace_id, order) -> None:
        self.workspace_id = workspace_id
        self.order = order

    def get(self, workspace_id, order_id):
        if workspace_id == self.workspace_id and order_id == self.order.id and self.order.deleted_at is None:
            return self.order
        return None


class FakeAuditLogs:
    def __init__(self) -> None:
        self.actions = []

    def create(self, **kwargs):
        self.actions.append(kwargs["action"])
        return SimpleNamespace(**kwargs)


class FakeOrderService:
    def __init__(self, order) -> None:
        self.order = order
        self.transitions = []

    def change_status(self, workspace_id, order_id, payload: OrderStatusUpdate, actor_user_id):
        self.transitions.append(payload.status)
        self.order.status = payload.status.value
        return SimpleNamespace(id=order_id, status=payload.status.value)


def _service(order_status=OrderStatus.NEW.value):
    workspace_id = uuid4()
    order = Order(id=uuid4(), workspace_id=workspace_id, order_number="ORD-2026-000001", status=order_status, revenue=Decimal("100"), product_cost=Decimal("0"), ad_cost=Decimal("0"), shipping_cost=Decimal("0"), cod_fee=Decimal("0"), other_cost=Decimal("0"), net_profit=Decimal("100"))
    order.deleted_at = None
    order.created_at = datetime.now(UTC)
    order.updated_at = datetime.now(UTC)
    service = ShipmentService.__new__(ShipmentService)
    service.db = FakeDb()
    service.shipments = FakeShipmentRepo(workspace_id, order)
    service.orders = FakeOrderRepo(workspace_id, order)
    service.audit_logs = FakeAuditLogs()
    service.order_service = FakeOrderService(order)
    return service, workspace_id, order


def _create_payload(order_id, tracking="TTN-SYNTHETIC-001", status=ShipmentStatus.DRAFT):
    return ShipmentCreate(order_id=order_id, tracking_number=tracking, carrier=ShipmentCarrier.NOVA_POSHTA, status=status, city="Synthetic City", warehouse="Synthetic Warehouse", shipping_cost=Decimal("75"), cod_amount=Decimal("1000"), declared_value=Decimal("1000"))


def test_shipment_creation_and_order_link() -> None:
    service, workspace_id, order = _service()
    shipment = service.create(workspace_id, _create_payload(order.id), uuid4())

    assert shipment.order_id == order.id
    assert shipment.order_number == "ORD-2026-000001"
    assert shipment.tracking_number == "TTN-SYNTHETIC-001"
    assert "SHIPMENT_CREATE" in service.audit_logs.actions


def test_duplicate_active_shipment_for_order_rejected() -> None:
    service, workspace_id, order = _service()
    service.create(workspace_id, _create_payload(order.id), uuid4())

    with pytest.raises(ShipmentServiceError, match="Active shipment"):
        service.create(workspace_id, _create_payload(order.id, tracking="TTN-SYNTHETIC-002"), uuid4())


def test_tracking_number_unique_per_workspace() -> None:
    service, workspace_id, order = _service()
    shipment = service.create(workspace_id, _create_payload(order.id), uuid4())
    shipment.status = ShipmentStatus.CANCELLED.value

    with pytest.raises(ShipmentServiceError, match="tracking_number already exists"):
        service.create(workspace_id, _create_payload(order.id, tracking="TTN-SYNTHETIC-001"), uuid4())


def test_tracking_number_required_for_non_draft_status() -> None:
    service, workspace_id, order = _service()

    with pytest.raises(ValueError, match="tracking_number is required"):
        ShipmentCreate(order_id=order.id, status=ShipmentStatus.CREATED)

    draft = service.create(workspace_id, ShipmentCreate(order_id=order.id), uuid4())
    with pytest.raises(ShipmentServiceError, match="tracking_number is required"):
        service.change_status(workspace_id, draft.id, ShipmentStatus.IN_TRANSIT, uuid4())


def test_status_actions_delegate_order_transitions() -> None:
    service, workspace_id, order = _service(OrderStatus.CONFIRMED.value)
    shipment = service.create(workspace_id, _create_payload(order.id, status=ShipmentStatus.CREATED), uuid4())

    service.change_status(workspace_id, shipment.id, ShipmentStatus.IN_TRANSIT, uuid4())
    service.change_status(workspace_id, shipment.id, ShipmentStatus.DELIVERED, uuid4())
    service.change_status(workspace_id, shipment.id, ShipmentStatus.RETURNED, uuid4())

    assert service.order_service.transitions == [OrderStatus.SHIPPED, OrderStatus.DELIVERED, OrderStatus.RETURNED]
    assert "SHIPMENT_DELIVERED" in service.audit_logs.actions
    assert "SHIPMENT_RETURNED" in service.audit_logs.actions


def test_workspace_isolation_and_soft_delete() -> None:
    service, workspace_id, order = _service()
    shipment = service.create(workspace_id, _create_payload(order.id), uuid4())

    assert service.get(uuid4(), shipment.id) is None
    assert service.delete(workspace_id, shipment.id, uuid4())
    assert service.get(workspace_id, shipment.id) is None


def test_analyst_read_only_and_manager_status_permissions() -> None:
    workspace_id = uuid4()
    analyst = SimpleNamespace(workspaces=[SimpleNamespace(workspace_id=workspace_id, workspace=SimpleNamespace(is_active=True), role=SimpleNamespace(name="ANALYST"))])
    manager = SimpleNamespace(workspaces=[SimpleNamespace(workspace_id=workspace_id, workspace=SimpleNamespace(is_active=True), role=SimpleNamespace(name="MANAGER"))])

    assert require_min_role(RoleName.ANALYST)(analyst, workspace_id) is analyst
    with pytest.raises(HTTPException):
        require_min_role(RoleName.MANAGER)(analyst, workspace_id)
    assert require_min_role(RoleName.MANAGER)(manager, workspace_id) is manager


def test_import_dry_run_supports_shipment_mapping_with_synthetic_data() -> None:
    workspace_id = uuid4()
    order = SimpleNamespace(id=uuid4(), workspace_id=workspace_id, order_number="ORD-2026-000001", deleted_at=None)
    lookup = SimpleNamespace(find_shipment_by_tracking=lambda *args: None, find_order_by_number=lambda *args: order, find_shipment_by_order=lambda *args: None)
    report = MappingValidationService().validate(
        "shipments",
        {"order_number": "Order Number", "tracking_number": "Tracking Number", "status": "Shipment Status", "city": "City"},
        [{"Order Number": "ORD-2026-000001", "Tracking Number": "TTN-SYNTHETIC-001", "Shipment Status": "CREATED", "City": "Synthetic City"}],
        workspace_id,
        lookup,
    )
    suggestion = MappingSuggestionService().suggest(["Номер замовлення", "ТТН", "Статус доставки", "Місто"], "shipments")

    assert report.is_valid
    assert suggestion.suggested_mapping["tracking_number"] == "ТТН"
    assert "shipments" in Path("app/services/import_center_service.py").read_text()


def test_auth_session_restore_refresh_behavior_not_regressed() -> None:
    source = Path("../frontend/src/stores/auth.store.tsx").read_text()

    assert "refreshAccessToken(refreshToken)" in source
    assert "fetchCurrentUser(tokens.access_token)" in source
