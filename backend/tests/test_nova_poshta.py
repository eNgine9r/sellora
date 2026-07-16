from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
import pytest

from app.models.integration_connection import IntegrationConnection, IntegrationProvider, IntegrationStatus
from app.models.integration_credential import IntegrationCredential
from app.models.role import RoleName
from app.models.shipment import Shipment, ShipmentCarrier, ShipmentStatus
from app.schemas.integration import NovaPoshtaSettingsRequest
from app.services.nova_poshta_service import NovaPoshtaDirectoryService, NovaPoshtaSettingsService, NovaPoshtaShipmentService
from app.utils.secrets import decrypt_secret, encrypt_secret, mask_secret
from app.dependencies.rbac import require_min_role


class FakeDb:
    def commit(self): pass
    def flush(self): pass
    def refresh(self, model): pass


class FakeConnections:
    def __init__(self): self.connection = None
    def get_by_provider(self, workspace_id, provider):
        if self.connection and self.connection.workspace_id == workspace_id and self.connection.provider == provider and self.connection.deleted_at is None:
            return self.connection
        return None
    def create(self, connection):
        connection.id = connection.id or uuid4(); self.connection = connection; return connection


class FakeCredentials:
    def __init__(self): self.credential = None
    def get_active_for_connection(self, workspace_id, connection_id):
        if self.credential and self.credential.workspace_id == workspace_id and self.credential.connection_id == connection_id and self.credential.deleted_at is None:
            return self.credential
        return None
    def create(self, credential):
        credential.id = credential.id or uuid4(); self.credential = credential; return credential


class FakeAudit:
    def __init__(self): self.records = []
    def create(self, **kwargs): self.records.append(kwargs); return SimpleNamespace(**kwargs)


class FakeClient:
    def __init__(self, credential, fail=False, fail_create=False, fail_status=False):
        self.credential = credential; self.fail = fail; self.fail_create = fail_create; self.fail_status = fail_status; self.create_called = False
    def test_connection(self):
        if self.fail: raise RuntimeError("failed")
        return True
    def search_cities(self, query, limit=20): return [SimpleNamespace(ref="city-ref", description=f"{query} city")]
    def search_warehouses(self, city_ref, query=None, limit=50): return [SimpleNamespace(ref="warehouse-ref", description="Warehouse", number="1")]
    def create_internet_document(self, payload):
        self.create_called = True
        if self.fail_create: raise RuntimeError("raw upstream payload with credential-like value")
        return SimpleNamespace(tracking_number="TTN-001", document_ref="doc-ref", status="CREATED")
    def get_document_status(self, tracking_number):
        if self.fail_status: raise RuntimeError("raw status failure")
        return "Delivered"


def _settings_service(client_factory=None):
    service = NovaPoshtaSettingsService.__new__(NovaPoshtaSettingsService)
    service.db = FakeDb(); service.connections = FakeConnections(); service.credentials = FakeCredentials(); service.audit_logs = FakeAudit(); service.client_factory = client_factory or (lambda credential: FakeClient(credential))
    return service


def test_encrypted_storage_round_trip_and_masking() -> None:
    value = "synthetic-credential-value"
    encrypted = encrypt_secret(value)
    assert encrypted != value
    assert decrypt_secret(encrypted) == value
    assert mask_secret(value).endswith(value[-4:])


def test_settings_save_encrypts_and_masks_response_without_raw_value() -> None:
    service = _settings_service(); workspace_id = uuid4()
    response = service.save_settings(workspace_id, NovaPoshtaSettingsRequest(api_key="synthetic-credential-value"), uuid4())
    stored = service.credentials.credential.encrypted_access_token
    assert stored != "synthetic-credential-value"
    assert response.masked_api_key is not None
    assert "synthetic-credential-value" not in str(response.model_dump())
    assert service.audit_logs.records[-1]["action"] == "NOVA_POSHTA_CONNECTED"



def test_sender_settings_update_preserves_existing_credential_without_raw_response() -> None:
    service = _settings_service(); workspace_id = uuid4()
    service.save_settings(workspace_id, NovaPoshtaSettingsRequest(api_key="synthetic-credential-value"), uuid4())
    response = service.save_settings(workspace_id, NovaPoshtaSettingsRequest(sender_city_ref="sender-city", sender_warehouse_ref="sender-wh", sender_counterparty_ref="sender", sender_contact_ref="contact", sender_phone="0000000000"), uuid4())
    assert decrypt_secret(service.credentials.credential.encrypted_access_token) == "synthetic-credential-value"
    assert response.sender_city_ref == "sender-city"
    assert "synthetic-credential-value" not in str(response.model_dump())
    assert service.audit_logs.records[-1]["action"] == "NOVA_POSHTA_SENDER_SETTINGS_UPDATED"


def test_first_connection_requires_api_key() -> None:
    service = _settings_service(); workspace_id = uuid4()
    with pytest.raises(ValueError):
        service.save_settings(workspace_id, NovaPoshtaSettingsRequest(sender_city_ref="sender-city"), uuid4())

def test_connection_success_and_failure_use_mocked_client() -> None:
    success = _settings_service(); workspace_id = uuid4()
    success.save_settings(workspace_id, NovaPoshtaSettingsRequest(api_key="synthetic-credential-value"), uuid4())
    assert success.test_connection(workspace_id, uuid4()).success
    failure = _settings_service(lambda credential: FakeClient(credential, fail=True))
    failure.save_settings(workspace_id, NovaPoshtaSettingsRequest(api_key="synthetic-credential-value"), uuid4())
    assert not failure.test_connection(workspace_id, uuid4()).success


def test_directory_search_uses_mocked_client() -> None:
    service = _settings_service(); workspace_id = uuid4()
    service.save_settings(workspace_id, NovaPoshtaSettingsRequest(api_key="synthetic-credential-value"), uuid4())
    directory = NovaPoshtaDirectoryService.__new__(NovaPoshtaDirectoryService); directory.settings = service
    assert directory.search_cities(workspace_id, "Kyiv")[0].ref == "city-ref"
    assert directory.search_warehouses(workspace_id, "city-ref")[0].ref == "warehouse-ref"


def test_rbac_owner_manager_analyst_nova_poshta_permissions() -> None:
    workspace_id = uuid4()
    owner = SimpleNamespace(workspaces=[SimpleNamespace(workspace_id=workspace_id, workspace=SimpleNamespace(is_active=True), role=SimpleNamespace(name="OWNER"))])
    manager = SimpleNamespace(workspaces=[SimpleNamespace(workspace_id=workspace_id, workspace=SimpleNamespace(is_active=True), role=SimpleNamespace(name="MANAGER"))])
    analyst = SimpleNamespace(workspaces=[SimpleNamespace(workspace_id=workspace_id, workspace=SimpleNamespace(is_active=True), role=SimpleNamespace(name="ANALYST"))])
    assert require_min_role(RoleName.OWNER)(owner, workspace_id) is owner
    with pytest.raises(HTTPException): require_min_role(RoleName.OWNER)(manager, workspace_id)
    assert require_min_role(RoleName.MANAGER)(manager, workspace_id) is manager
    with pytest.raises(HTTPException): require_min_role(RoleName.MANAGER)(analyst, workspace_id)


def _shipment_service(shipment, sender_settings_complete=True):
    settings = _settings_service(); workspace_id = shipment.workspace_id
    payload = NovaPoshtaSettingsRequest(api_key="synthetic-credential-value", sender_city_ref="sender-city", sender_warehouse_ref="sender-wh", sender_counterparty_ref="sender", sender_contact_ref="contact", sender_phone="0000000000") if sender_settings_complete else NovaPoshtaSettingsRequest(api_key="synthetic-credential-value")
    settings.save_settings(workspace_id, payload, uuid4())
    service = NovaPoshtaShipmentService.__new__(NovaPoshtaShipmentService)
    service.db = FakeDb(); service.settings = settings; service.audit_logs = FakeAudit(); service.shipments = SimpleNamespace(get=lambda workspace_id, shipment_id: shipment if shipment.workspace_id == workspace_id and shipment.id == shipment_id else None)
    return service


def test_create_ttn_validates_required_fields_before_api_call() -> None:
    shipment = Shipment(id=uuid4(), workspace_id=uuid4(), order_id=uuid4(), customer_id=None, carrier=ShipmentCarrier.NOVA_POSHTA.value, status=ShipmentStatus.DRAFT.value)
    service = _shipment_service(shipment)
    response = service.create_ttn(shipment.workspace_id, shipment.id, uuid4())
    assert not response.success
    assert "customer is required" in response.errors


def test_create_ttn_reports_clear_sender_settings_message() -> None:
    shipment = Shipment(id=uuid4(), workspace_id=uuid4(), order_id=uuid4(), customer_id=uuid4(), carrier=ShipmentCarrier.NOVA_POSHTA.value, status=ShipmentStatus.DRAFT.value, recipient_name="Recipient", recipient_phone="0000000000", city="City", warehouse="Warehouse", nova_poshta_city_ref="city-ref", nova_poshta_warehouse_ref="warehouse-ref", declared_value=100)
    shipment.order = SimpleNamespace(order_number="ORD-SYNTH")
    service = _shipment_service(shipment, sender_settings_complete=False)
    response = service.create_ttn(shipment.workspace_id, shipment.id, uuid4())
    assert not response.success
    assert response.message == "Sender settings are incomplete. Please fill sender city, warehouse, counterparty, contact person, and phone."
    assert "sender_city_ref is required" in response.errors


def test_create_ttn_updates_shipment_and_does_not_log_credential() -> None:
    shipment = Shipment(id=uuid4(), workspace_id=uuid4(), order_id=uuid4(), customer_id=uuid4(), carrier=ShipmentCarrier.NOVA_POSHTA.value, status=ShipmentStatus.DRAFT.value, recipient_name="Recipient", recipient_phone="0000000000", city="City", warehouse="Warehouse", nova_poshta_city_ref="city-ref", nova_poshta_warehouse_ref="warehouse-ref", declared_value=100)
    shipment.order = SimpleNamespace(order_number="ORD-SYNTH")
    service = _shipment_service(shipment)
    response = service.create_ttn(shipment.workspace_id, shipment.id, uuid4())
    assert response.success
    assert shipment.tracking_number == "TTN-001"
    assert shipment.nova_poshta_document_ref == "doc-ref"
    assert "synthetic-credential-value" not in str(service.audit_logs.records)


def test_manual_shipments_remain_valid_without_nova_poshta_configuration() -> None:
    shipment = Shipment(id=uuid4(), workspace_id=uuid4(), order_id=uuid4(), carrier=ShipmentCarrier.OTHER.value, status=ShipmentStatus.DRAFT.value)
    assert shipment.carrier == ShipmentCarrier.OTHER.value


def test_create_ttn_prevents_duplicate_nova_poshta_document() -> None:
    shipment = Shipment(id=uuid4(), workspace_id=uuid4(), order_id=uuid4(), customer_id=uuid4(), carrier=ShipmentCarrier.NOVA_POSHTA.value, status=ShipmentStatus.CREATED.value, recipient_name="Recipient", recipient_phone="0000000000", city="City", warehouse="Warehouse", nova_poshta_city_ref="city-ref", nova_poshta_warehouse_ref="warehouse-ref", declared_value=100, tracking_number="TTN-001", nova_poshta_document_ref="doc-ref", nova_poshta_document_number="TTN-001")
    shipment.order = SimpleNamespace(order_number="ORD-SYNTH")
    service = _shipment_service(shipment)
    response = service.create_ttn(shipment.workspace_id, shipment.id, uuid4())
    assert not response.success
    assert response.tracking_number == "TTN-001"
    assert "ttn already exists" in response.errors


def test_create_ttn_api_failure_uses_safe_error_message_without_raw_payload() -> None:
    shipment = Shipment(id=uuid4(), workspace_id=uuid4(), order_id=uuid4(), customer_id=uuid4(), carrier=ShipmentCarrier.NOVA_POSHTA.value, status=ShipmentStatus.DRAFT.value, recipient_name="Recipient", recipient_phone="0000000000", city="City", warehouse="Warehouse", nova_poshta_city_ref="city-ref", nova_poshta_warehouse_ref="warehouse-ref", declared_value=100)
    shipment.order = SimpleNamespace(order_number="ORD-SYNTH")
    service = _shipment_service(shipment)
    service.settings.client_factory = lambda credential: FakeClient(credential, fail_create=True)
    response = service.create_ttn(shipment.workspace_id, shipment.id, uuid4())
    assert not response.success
    assert response.errors == ["NOVA_POSHTA_TTN_FAILED"]
    assert "raw upstream" not in str(response.model_dump())
    assert "synthetic-credential-value" not in str(service.audit_logs.records)


def test_sync_status_failure_returns_safe_message() -> None:
    shipment = Shipment(id=uuid4(), workspace_id=uuid4(), order_id=uuid4(), customer_id=uuid4(), carrier=ShipmentCarrier.NOVA_POSHTA.value, status=ShipmentStatus.CREATED.value, tracking_number="TTN-001", nova_poshta_document_number="TTN-001")
    service = _shipment_service(shipment)
    service.settings.client_factory = lambda credential: FakeClient(credential, fail_status=True)
    response = service.sync_status(shipment.workspace_id, shipment.id, uuid4())
    assert not response.success
    assert response.message == "Nova Poshta status sync is unavailable. Please try again later."
    assert "raw status failure" not in str(response.model_dump())


def test_create_ttn_incomplete_response_is_safe_and_does_not_store_tracking() -> None:
    shipment = Shipment(id=uuid4(), workspace_id=uuid4(), order_id=uuid4(), customer_id=uuid4(), carrier=ShipmentCarrier.NOVA_POSHTA.value, status=ShipmentStatus.DRAFT.value, recipient_name="Recipient", recipient_phone="0000000000", city="City", warehouse="Warehouse", nova_poshta_city_ref="city-ref", nova_poshta_warehouse_ref="warehouse-ref", declared_value=100)
    shipment.order = SimpleNamespace(order_number="ORD-SYNTH")
    service = _shipment_service(shipment)
    service.settings.client_factory = lambda credential: SimpleNamespace(create_internet_document=lambda payload: SimpleNamespace(tracking_number=None, document_ref=None, status="CREATED"))

    response = service.create_ttn(shipment.workspace_id, shipment.id, uuid4())

    assert not response.success
    assert response.errors == ["NOVA_POSHTA_TTN_INCOMPLETE"]
    assert shipment.tracking_number is None
    assert "synthetic-credential-value" not in str(service.audit_logs.records)
    assert "TTN_CREATE_INCOMPLETE" in str(service.audit_logs.records)


def test_sync_status_without_tracking_is_blocked_before_api_call() -> None:
    shipment = Shipment(id=uuid4(), workspace_id=uuid4(), order_id=uuid4(), customer_id=uuid4(), carrier=ShipmentCarrier.NOVA_POSHTA.value, status=ShipmentStatus.CREATED.value)
    service = _shipment_service(shipment)

    with pytest.raises(ValueError, match="does not have a Nova Poshta tracking number"):
        service.sync_status(shipment.workspace_id, shipment.id, uuid4())


def test_sync_status_empty_response_returns_safe_unavailable_message() -> None:
    shipment = Shipment(id=uuid4(), workspace_id=uuid4(), order_id=uuid4(), customer_id=uuid4(), carrier=ShipmentCarrier.NOVA_POSHTA.value, status=ShipmentStatus.CREATED.value, tracking_number="TTN-001", nova_poshta_document_number="TTN-001", external_status="Previous status")
    service = _shipment_service(shipment)
    service.settings.client_factory = lambda credential: SimpleNamespace(get_document_status=lambda tracking_number: None)

    response = service.sync_status(shipment.workspace_id, shipment.id, uuid4())

    assert not response.success
    assert response.status == "Previous status"
    assert response.message == "Nova Poshta status sync is unavailable. Please try again later."
    assert "synthetic-credential-value" not in str(service.audit_logs.records)


def test_cross_workspace_ttn_access_uses_workspace_scoped_connection_and_shipment() -> None:
    shipment = Shipment(id=uuid4(), workspace_id=uuid4(), order_id=uuid4(), customer_id=uuid4(), carrier=ShipmentCarrier.NOVA_POSHTA.value, status=ShipmentStatus.DRAFT.value, recipient_name="Recipient", recipient_phone="0000000000", city="City", warehouse="Warehouse", nova_poshta_city_ref="city-ref", nova_poshta_warehouse_ref="warehouse-ref", declared_value=100)
    shipment.order = SimpleNamespace(order_number="ORD-SYNTH")
    service = _shipment_service(shipment)

    with pytest.raises(ValueError, match="Nova Poshta is not configured"):
        service.create_ttn(uuid4(), shipment.id, uuid4())


def test_settings_write_gate_requires_environment_workspace_permission_sender_and_verification(monkeypatch) -> None:
    service = _settings_service(); workspace_id = uuid4()
    monkeypatch.setattr("app.services.nova_poshta_service.get_settings", lambda: SimpleNamespace(staging_nova_poshta_allow_writes=True))
    response = service.save_settings(
        workspace_id,
        NovaPoshtaSettingsRequest(api_key="synthetic-credential-value", sender_city_ref="sender-city", sender_warehouse_ref="sender-wh", sender_counterparty_ref="sender", sender_contact_ref="contact", sender_phone="380671234567"),
        uuid4(),
    )
    assert not response.provider_writes_enabled
    assert response.workspace_permission is False
    assert "CONNECTION_NOT_VERIFIED" in response.write_blockers
    service.test_connection(workspace_id, uuid4())
    response = service.get_settings(workspace_id)
    assert "WORKSPACE_PERMISSION_DISABLED" in response.write_blockers
    assert not response.provider_writes_enabled
    response = service.set_write_permission(workspace_id, __import__("app.schemas.integration", fromlist=["NovaPoshtaWritePermissionRequest"]).NovaPoshtaWritePermissionRequest(allowed=True), uuid4())
    assert response.workspace_permission is True
    assert response.provider_writes_enabled is True
    assert service.audit_logs.records[-1]["action"] == "NOVA_POSHTA_PROVIDER_WRITES_ENABLED"


def test_provider_writes_disabled_by_workspace_permission_blocks_durable_ttn(monkeypatch) -> None:
    monkeypatch.setattr("app.services.nova_poshta_service.get_settings", lambda: SimpleNamespace(staging_nova_poshta_allow_writes=True))
    shipment = Shipment(id=uuid4(), workspace_id=uuid4(), order_id=uuid4(), customer_id=uuid4(), carrier=ShipmentCarrier.NOVA_POSHTA.value, status=ShipmentStatus.DRAFT.value, recipient_name="Recipient", recipient_phone="+380671234567", city="City", warehouse="Warehouse", nova_poshta_city_ref="city-ref", nova_poshta_warehouse_ref="warehouse-ref", declared_value=100)
    shipment.order = SimpleNamespace(order_number="ORD-SYNTH")
    service = _shipment_service(shipment)
    service.operations = SimpleNamespace(get_for_update=lambda *args: None)
    response = service.create_ttn(shipment.workspace_id, shipment.id, uuid4())
    assert not response.success
    assert response.errors == ["NOVA_POSHTA_PROVIDER_WRITES_DISABLED"]
