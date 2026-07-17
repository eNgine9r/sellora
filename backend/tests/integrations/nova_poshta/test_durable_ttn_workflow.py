from types import SimpleNamespace
from uuid import uuid4

from app.integrations.nova_poshta_client import NovaPoshtaClientError
from app.models.nova_poshta_operation import NovaPoshtaOperationState
from app.models.shipment import Shipment, ShipmentCarrier, ShipmentStatus
from app.services.nova_poshta_service import NovaPoshtaShipmentService


class FakeDb:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def add(self, _model) -> None:
        return None

    def flush(self) -> None:
        return None


class FakeAudit:
    def __init__(self) -> None:
        self.records: list[dict] = []

    def create(self, **kwargs):
        self.records.append(kwargs)
        return SimpleNamespace(**kwargs)


class FakeShipments:
    def __init__(self, shipment: Shipment) -> None:
        self.shipment = shipment

    def get(self, workspace_id, shipment_id):
        if self.shipment.workspace_id == workspace_id and self.shipment.id == shipment_id:
            return self.shipment
        return None

    def get_for_update(self, workspace_id, shipment_id):
        return self.get(workspace_id, shipment_id)


class FakeOperations:
    def __init__(self) -> None:
        self.operation = None

    def get(self, workspace_id, shipment_id, operation_type="CREATE_TTN"):
        operation = self.operation
        if operation and operation.workspace_id == workspace_id and operation.shipment_id == shipment_id and operation.operation_type == operation_type:
            return operation
        return None

    def get_for_update(self, workspace_id, shipment_id, operation_type="CREATE_TTN"):
        return self.get(workspace_id, shipment_id, operation_type)

    def create(self, operation):
        operation.attempt_count = operation.attempt_count or 0
        self.operation = operation
        return operation


class FakeClient:
    def __init__(self, *, ambiguous=False, reconciled=None, status="Delivered") -> None:
        self.ambiguous = ambiguous
        self.reconciled = reconciled
        self.status = status
        self.create_calls = 0
        self.find_calls = 0

    def create_internet_document(self, _payload):
        self.create_calls += 1
        if self.ambiguous:
            raise NovaPoshtaClientError(
                "transport interrupted",
                code="NOVA_POSHTA_PROVIDER_RESPONSE_AMBIGUOUS",
                retryable=True,
                ambiguous=True,
            )
        return SimpleNamespace(tracking_number="20400000000001", document_ref="provider-ref", status="CREATED")

    def find_internet_document(self, _marker, _date_from, _date_to):
        self.find_calls += 1
        return self.reconciled

    def get_document_status(self, _tracking_number):
        return self.status


class FakeSettings:
    def __init__(self, workspace_id, client: FakeClient) -> None:
        self.connection = SimpleNamespace(
            workspace_id=workspace_id,
            settings={
                "sender_city_ref": "sender-city",
                "sender_warehouse_ref": "sender-warehouse",
                "sender_counterparty_ref": "sender-counterparty",
                "sender_contact_ref": "sender-contact",
                "sender_phone": "+380671234567",
            },
            last_sync_at=None,
            provider_connection_verified_at=None,
        )
        self.client = client

    def _require_connection(self, workspace_id):
        if workspace_id != self.connection.workspace_id:
            raise ValueError("Nova Poshta is not configured")
        return self.connection, "synthetic-secret"

    def client_factory(self, _api_key):
        return self.client


def eligible_shipment() -> Shipment:
    shipment = Shipment(
        id=uuid4(),
        workspace_id=uuid4(),
        order_id=uuid4(),
        customer_id=uuid4(),
        carrier=ShipmentCarrier.NOVA_POSHTA.value,
        status=ShipmentStatus.DRAFT.value,
        recipient_name="QA8E Recipient",
        recipient_phone="+380671234567",
        city="Kyiv",
        warehouse="Warehouse 1",
        nova_poshta_city_ref="recipient-city",
        nova_poshta_warehouse_ref="recipient-warehouse",
        declared_value=100,
        nova_poshta_manual_reconciliation_required=False,
    )
    shipment.order = SimpleNamespace(order_number="QA8E-ORDER")
    return shipment


def durable_service(shipment: Shipment, client: FakeClient, operations: FakeOperations | None = None):
    service = NovaPoshtaShipmentService.__new__(NovaPoshtaShipmentService)
    service.db = FakeDb()
    service.shipments = FakeShipments(shipment)
    service.operations = operations or FakeOperations()
    service.settings = FakeSettings(shipment.workspace_id, client)
    service.audit_logs = FakeAudit()
    service.provider_writes_enabled = True
    return service


def test_successful_create_is_idempotent_across_service_instances() -> None:
    shipment = eligible_shipment()
    operations = FakeOperations()
    first_client = FakeClient()
    first = durable_service(shipment, first_client, operations)

    created = first.create_ttn(shipment.workspace_id, shipment.id, uuid4())

    second_client = FakeClient()
    second = durable_service(shipment, second_client, operations)
    repeated = second.create_ttn(shipment.workspace_id, shipment.id, uuid4())

    assert created.success
    assert repeated.success
    assert repeated.reused_existing_result
    assert first_client.create_calls == 1
    assert first.settings.connection.provider_connection_verified_at is None
    assert second_client.create_calls == 0
    assert operations.operation.state == NovaPoshtaOperationState.COMPLETED.value
    assert first.settings.connection.last_sync_at is not None
    assert first.settings.connection.provider_connection_verified_at is None


def test_ambiguous_provider_response_blocks_blind_retry_after_restart() -> None:
    shipment = eligible_shipment()
    operations = FakeOperations()
    first_client = FakeClient(ambiguous=True)
    first = durable_service(shipment, first_client, operations)

    ambiguous = first.create_ttn(shipment.workspace_id, shipment.id, uuid4())

    second_client = FakeClient(ambiguous=False, reconciled=None)
    second = durable_service(shipment, second_client, operations)
    retry = second.create_ttn(shipment.workspace_id, shipment.id, uuid4())

    assert not ambiguous.success
    assert ambiguous.manual_reconciliation_required
    assert ambiguous.blind_retry_blocked
    assert not retry.success
    assert retry.reconciliation_attempted
    assert retry.blind_retry_blocked
    assert first_client.create_calls == 1
    assert second_client.create_calls == 0
    assert second_client.find_calls == 1
    assert operations.operation.state == NovaPoshtaOperationState.RECONCILIATION_REQUIRED.value


def test_reconciliation_binds_provider_document_without_second_create() -> None:
    shipment = eligible_shipment()
    operations = FakeOperations()
    first = durable_service(shipment, FakeClient(ambiguous=True), operations)
    first.create_ttn(shipment.workspace_id, shipment.id, uuid4())

    provider_result = SimpleNamespace(
        tracking_number="20400000000002",
        document_ref="reconciled-ref",
        status="CREATED",
    )
    reconcile_client = FakeClient(reconciled=provider_result)
    restarted = durable_service(shipment, reconcile_client, operations)

    result = restarted.reconcile_ttn(shipment.workspace_id, shipment.id, uuid4())

    assert result.success
    assert result.reconciliation_attempted
    assert result.reused_existing_result
    assert reconcile_client.create_calls == 0
    assert reconcile_client.find_calls == 1
    assert shipment.nova_poshta_document_number == "20400000000002"
    assert shipment.nova_poshta_manual_reconciliation_required is False


def test_unknown_status_preserves_previous_normalized_state() -> None:
    shipment = eligible_shipment()
    shipment.status = ShipmentStatus.IN_TRANSIT.value
    shipment.tracking_number = "20400000000003"
    shipment.nova_poshta_document_number = shipment.tracking_number
    client = FakeClient(status="Unknown provider status requiring review")
    service = durable_service(shipment, client)

    result = service.sync_status(shipment.workspace_id, shipment.id, uuid4())

    assert result.success
    assert result.manual_review_required
    assert result.raw_status == "Unknown provider status requiring review"
    assert shipment.status == ShipmentStatus.IN_TRANSIT.value


def test_provider_writes_default_to_explicit_guard() -> None:
    shipment = eligible_shipment()
    client = FakeClient()
    service = durable_service(shipment, client)
    service.provider_writes_enabled = False

    result = service.create_ttn(shipment.workspace_id, shipment.id, uuid4())

    assert not result.success
    assert result.blind_retry_blocked
    assert result.errors == ["NOVA_POSHTA_PROVIDER_WRITES_DISABLED"]
    assert client.create_calls == 0
