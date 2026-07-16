from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
import pytest

from app.models.integration_connection import IntegrationConnection, IntegrationProvider, IntegrationStatus
from app.models.integration_credential import IntegrationCredential
from app.models.role import RoleName
from app.models.shipment import Shipment, ShipmentCarrier, ShipmentStatus
from app.schemas.integration import NovaPoshtaSettingsRequest, NovaPoshtaWritePermissionRequest
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
    def __init__(self, credential, fail=False, fail_create=False, fail_status=False, sender_error=None):
        self.credential = credential; self.fail = fail; self.fail_create = fail_create; self.fail_status = fail_status; self.sender_error = sender_error; self.create_called = False; self.last_payload = None
    def test_connection(self):
        if self.fail: raise RuntimeError("failed")
        return True
    def search_cities(self, query, limit=20): return [SimpleNamespace(ref="city-ref", description=f"{query} city")]
    def search_warehouses(self, city_ref, query=None, limit=50): return [SimpleNamespace(ref="warehouse-ref", description="Warehouse", number="1"), SimpleNamespace(ref="sender-wh", description="Sender Warehouse", number="7")]
    def counterparty_exists(self, counterparty_ref):
        if self.sender_error == "counterparty": return False
        if self.sender_error == "unavailable": raise RuntimeError("raw provider outage")
        return counterparty_ref == "sender"
    def contact_belongs_to_counterparty(self, counterparty_ref, contact_ref):
        if self.sender_error == "contact": return False
        return counterparty_ref == "sender" and contact_ref == "contact"
    def sender_address_belongs_to_sender(self, sender_ref, address_ref):
        if self.sender_error == "address": return False
        return sender_ref == "sender" and address_ref == "sender-wh"
    def warehouse_belongs_to_city(self, city_ref, warehouse_ref):
        if self.sender_error == "city": return False
        return city_ref == "sender-city" and warehouse_ref == "sender-wh"
    def create_internet_document(self, payload):
        self.create_called = True
        self.last_payload = payload
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
    response = service.save_settings(workspace_id, NovaPoshtaSettingsRequest(sender_city_ref="sender-city", sender_warehouse_ref="sender-wh", sender_counterparty_ref="sender", sender_contact_ref="contact", sender_phone="+380671234567"), uuid4())
    assert decrypt_secret(service.credentials.credential.encrypted_access_token) == "synthetic-credential-value"
    assert response.sender_city_ref == "sender-city"
    assert "synthetic-credential-value" not in str(response.model_dump())
    assert service.audit_logs.records[-1]["action"] == "NOVA_POSHTA_SENDER_SETTINGS_UPDATED"


def test_first_connection_requires_api_key() -> None:
    service = _settings_service(); workspace_id = uuid4()
    with pytest.raises(ValueError):
        service.save_settings(workspace_id, NovaPoshtaSettingsRequest(sender_city_ref="sender-city"), uuid4())

def _complete_settings(api_key: str | None = "synthetic-credential-value", **overrides):
    values = {
        "api_key": api_key,
        "sender_city_ref": "sender-city",
        "sender_warehouse_ref": "sender-wh",
        "sender_counterparty_ref": "sender",
        "sender_contact_ref": "contact",
        "sender_phone": "0671234567",
    }
    values.update(overrides)
    return NovaPoshtaSettingsRequest(**values)


def test_connection_success_and_failure_use_mocked_client() -> None:
    client = FakeClient("credential")
    success = _settings_service(lambda credential: client); workspace_id = uuid4()
    success.save_settings(workspace_id, _complete_settings(), uuid4())
    assert success.test_connection(workspace_id, uuid4()).success
    assert not client.create_called
    failure = _settings_service(lambda credential: FakeClient(credential, fail=True))
    failure.save_settings(workspace_id, _complete_settings(), uuid4())
    response = failure.test_connection(workspace_id, uuid4())
    assert not response.success
    assert response.errors == ["NOVA_POSHTA_API_KEY_INVALID"]
    assert failure.connections.connection.provider_connection_verified_at is None
    assert not failure.connections.connection.provider_writes_allowed


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
    payload = _complete_settings() if sender_settings_complete else NovaPoshtaSettingsRequest(api_key="synthetic-credential-value")
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
    shipment = Shipment(id=uuid4(), workspace_id=uuid4(), order_id=uuid4(), customer_id=uuid4(), carrier=ShipmentCarrier.NOVA_POSHTA.value, status=ShipmentStatus.DRAFT.value, recipient_name="Recipient", recipient_phone="+380671234567", city="City", warehouse="Warehouse", nova_poshta_city_ref="city-ref", nova_poshta_warehouse_ref="warehouse-ref", declared_value=100)
    shipment.order = SimpleNamespace(order_number="ORD-SYNTH")
    service = _shipment_service(shipment, sender_settings_complete=False)
    response = service.create_ttn(shipment.workspace_id, shipment.id, uuid4())
    assert not response.success
    assert response.message == "Sender settings are incomplete. Please fill sender city, warehouse, counterparty, contact person, and phone."
    assert "sender_city_ref is required" in response.errors


def test_create_ttn_updates_shipment_and_does_not_log_credential() -> None:
    shipment = Shipment(id=uuid4(), workspace_id=uuid4(), order_id=uuid4(), customer_id=uuid4(), carrier=ShipmentCarrier.NOVA_POSHTA.value, status=ShipmentStatus.DRAFT.value, recipient_name="Recipient", recipient_phone="+380671234567", city="City", warehouse="Warehouse", nova_poshta_city_ref="city-ref", nova_poshta_warehouse_ref="warehouse-ref", declared_value=100)
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
    shipment = Shipment(id=uuid4(), workspace_id=uuid4(), order_id=uuid4(), customer_id=uuid4(), carrier=ShipmentCarrier.NOVA_POSHTA.value, status=ShipmentStatus.CREATED.value, recipient_name="Recipient", recipient_phone="+380671234567", city="City", warehouse="Warehouse", nova_poshta_city_ref="city-ref", nova_poshta_warehouse_ref="warehouse-ref", declared_value=100, tracking_number="TTN-001", nova_poshta_document_ref="doc-ref", nova_poshta_document_number="TTN-001")
    shipment.order = SimpleNamespace(order_number="ORD-SYNTH")
    service = _shipment_service(shipment)
    response = service.create_ttn(shipment.workspace_id, shipment.id, uuid4())
    assert not response.success
    assert response.tracking_number == "TTN-001"
    assert "ttn already exists" in response.errors


def test_create_ttn_api_failure_uses_safe_error_message_without_raw_payload() -> None:
    shipment = Shipment(id=uuid4(), workspace_id=uuid4(), order_id=uuid4(), customer_id=uuid4(), carrier=ShipmentCarrier.NOVA_POSHTA.value, status=ShipmentStatus.DRAFT.value, recipient_name="Recipient", recipient_phone="+380671234567", city="City", warehouse="Warehouse", nova_poshta_city_ref="city-ref", nova_poshta_warehouse_ref="warehouse-ref", declared_value=100)
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
    shipment = Shipment(id=uuid4(), workspace_id=uuid4(), order_id=uuid4(), customer_id=uuid4(), carrier=ShipmentCarrier.NOVA_POSHTA.value, status=ShipmentStatus.DRAFT.value, recipient_name="Recipient", recipient_phone="+380671234567", city="City", warehouse="Warehouse", nova_poshta_city_ref="city-ref", nova_poshta_warehouse_ref="warehouse-ref", declared_value=100)
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
    shipment = Shipment(id=uuid4(), workspace_id=uuid4(), order_id=uuid4(), customer_id=uuid4(), carrier=ShipmentCarrier.NOVA_POSHTA.value, status=ShipmentStatus.DRAFT.value, recipient_name="Recipient", recipient_phone="+380671234567", city="City", warehouse="Warehouse", nova_poshta_city_ref="city-ref", nova_poshta_warehouse_ref="warehouse-ref", declared_value=100)
    shipment.order = SimpleNamespace(order_number="ORD-SYNTH")
    service = _shipment_service(shipment)

    with pytest.raises(ValueError, match="Nova Poshta is not configured"):
        service.create_ttn(uuid4(), shipment.id, uuid4())


def test_settings_write_gate_requires_environment_workspace_permission_sender_and_verification(monkeypatch) -> None:
    service = _settings_service(); workspace_id = uuid4()
    monkeypatch.setattr("app.services.nova_poshta_service.get_settings", lambda: SimpleNamespace(staging_nova_poshta_allow_writes=True))
    response = service.save_settings(
        workspace_id,
        _complete_settings(),
        uuid4(),
    )
    assert not response.provider_writes_enabled
    assert response.workspace_permission is False
    assert "CONNECTION_NOT_VERIFIED" in response.write_blockers
    service.test_connection(workspace_id, uuid4())
    response = service.get_settings(workspace_id)
    assert "WORKSPACE_PERMISSION_DISABLED" in response.write_blockers
    assert not response.provider_writes_enabled
    response = service.set_write_permission(workspace_id, NovaPoshtaWritePermissionRequest(allowed=True), uuid4())
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


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("api_key", "synthetic-credential-rotated"),
        ("sender_city_ref", "sender-city-new"),
        ("sender_warehouse_ref", "sender-wh-new"),
        ("sender_counterparty_ref", "sender-new"),
        ("sender_contact_ref", "contact-new"),
        ("sender_phone", "0681234567"),
    ],
)
def test_material_settings_change_invalidates_verification_and_permission(monkeypatch, field, value) -> None:
    monkeypatch.setattr("app.services.nova_poshta_service.get_settings", lambda: SimpleNamespace(staging_nova_poshta_allow_writes=True))
    service = _settings_service(); workspace_id = uuid4()
    service.save_settings(workspace_id, _complete_settings(), uuid4())
    assert service.test_connection(workspace_id, uuid4()).success
    service.set_write_permission(workspace_id, NovaPoshtaWritePermissionRequest(allowed=True), uuid4())

    payload = _complete_settings(api_key=value) if field == "api_key" else NovaPoshtaSettingsRequest(**{field: value})
    response = service.save_settings(workspace_id, payload, uuid4())

    assert service.connections.connection.provider_connection_verified_at is None
    assert not service.connections.connection.provider_writes_allowed
    assert "CONNECTION_NOT_VERIFIED" in response.write_blockers
    assert "WORKSPACE_PERMISSION_DISABLED" in response.write_blockers
    assert service.audit_logs.records[-2]["action"] == "NOVA_POSHTA_VERIFICATION_INVALIDATED"


def test_unchanged_sender_settings_do_not_invalidate_verification(monkeypatch) -> None:
    monkeypatch.setattr("app.services.nova_poshta_service.get_settings", lambda: SimpleNamespace(staging_nova_poshta_allow_writes=True))
    service = _settings_service(); workspace_id = uuid4()
    service.save_settings(workspace_id, _complete_settings(), uuid4())
    assert service.test_connection(workspace_id, uuid4()).success
    verified_at = service.connections.connection.provider_connection_verified_at
    service.set_write_permission(workspace_id, NovaPoshtaWritePermissionRequest(allowed=True), uuid4())

    response = service.save_settings(workspace_id, NovaPoshtaSettingsRequest(sender_city_ref="sender-city"), uuid4())

    assert service.connections.connection.provider_connection_verified_at == verified_at
    assert service.connections.connection.provider_writes_allowed
    assert response.provider_writes_enabled
    assert "NOVA_POSHTA_VERIFICATION_INVALIDATED" not in [record["action"] for record in service.audit_logs.records[-2:]]


def test_disconnect_clears_verification_and_permission(monkeypatch) -> None:
    monkeypatch.setattr("app.services.nova_poshta_service.get_settings", lambda: SimpleNamespace(staging_nova_poshta_allow_writes=True))
    service = _settings_service(); workspace_id = uuid4()
    service.save_settings(workspace_id, _complete_settings(), uuid4())
    assert service.test_connection(workspace_id, uuid4()).success
    service.set_write_permission(workspace_id, NovaPoshtaWritePermissionRequest(allowed=True), uuid4())

    service.disconnect(workspace_id, uuid4())

    assert service.connections.connection.provider_connection_verified_at is None
    assert not service.connections.connection.provider_writes_allowed


@pytest.mark.parametrize(
    ("sender_error", "expected_code"),
    [
        ("counterparty", "NOVA_POSHTA_SENDER_COUNTERPARTY_INVALID"),
        ("contact", "NOVA_POSHTA_SENDER_CONTACT_INVALID"),
        ("address", "NOVA_POSHTA_SENDER_ADDRESS_INVALID"),
        ("city", "NOVA_POSHTA_SENDER_CITY_MISMATCH"),
        ("unavailable", "NOVA_POSHTA_SENDER_VALIDATION_UNAVAILABLE"),
    ],
)
def test_sender_tuple_validation_failures_are_sanitized(sender_error, expected_code) -> None:
    service = _settings_service(lambda credential: FakeClient(credential, sender_error=sender_error)); workspace_id = uuid4()
    service.save_settings(workspace_id, _complete_settings(), uuid4())

    response = service.test_connection(workspace_id, uuid4())

    assert not response.success
    assert response.errors == [expected_code]
    dumped = str(response.model_dump())
    assert "sender-wh" not in dumped
    assert "contact" not in dumped
    assert "067" not in dumped
    assert not service.connections.connection.provider_writes_allowed
    assert service.connections.connection.provider_connection_verified_at is None


def test_sender_tuple_invalid_phone_fails_without_provider_write() -> None:
    client = FakeClient("credential")
    service = _settings_service(lambda credential: client); workspace_id = uuid4()
    service.save_settings(workspace_id, _complete_settings(), uuid4())
    service.connections.connection.settings["sender_phone"] = "00380671234567"

    response = service.test_connection(workspace_id, uuid4())

    assert not response.success
    assert response.errors == ["NOVA_POSHTA_SENDER_PHONE_INVALID"]
    assert not client.create_called


def test_permission_gate_environment_and_missing_prerequisites(monkeypatch) -> None:
    service = _settings_service(); workspace_id = uuid4()
    monkeypatch.setattr("app.services.nova_poshta_service.get_settings", lambda: SimpleNamespace(staging_nova_poshta_allow_writes=False))
    service.save_settings(workspace_id, _complete_settings(), uuid4())
    service.test_connection(workspace_id, uuid4())
    with pytest.raises(ValueError):
        service.set_write_permission(workspace_id, NovaPoshtaWritePermissionRequest(allowed=True), uuid4())

    response = service.get_settings(workspace_id)
    assert "ENVIRONMENT_CAPABILITY_DISABLED" in response.write_blockers


def test_permission_gate_missing_credential_sender_and_unverified_block(monkeypatch) -> None:
    monkeypatch.setattr("app.services.nova_poshta_service.get_settings", lambda: SimpleNamespace(staging_nova_poshta_allow_writes=True))
    service = _settings_service(); workspace_id = uuid4()
    service.save_settings(workspace_id, NovaPoshtaSettingsRequest(api_key="synthetic-credential-value"), uuid4())
    service.credentials.credential.deleted_at = datetime.now(UTC)
    response = service.get_settings(workspace_id)
    assert "CONNECTION_NOT_CONFIGURED" in response.write_blockers
    assert "SENDER_NOT_CONFIGURED" in response.write_blockers
    assert "CONNECTION_NOT_VERIFIED" in response.write_blockers


@pytest.mark.parametrize("raw_phone", ["0671234567", "+380671234567", "380671234567", "067 123 45 67", "(067) 123-45-67"])
def test_sender_phone_is_stored_canonically_and_payload_uses_provider_format(raw_phone) -> None:
    service = _settings_service(); workspace_id = uuid4()

    response = service.save_settings(workspace_id, _complete_settings(sender_phone=raw_phone), uuid4())

    assert response.sender_phone == "+380671234567"
    shipment = Shipment(id=uuid4(), workspace_id=workspace_id, order_id=uuid4(), customer_id=uuid4(), carrier=ShipmentCarrier.NOVA_POSHTA.value, status=ShipmentStatus.DRAFT.value, recipient_name="Recipient", recipient_phone=raw_phone, city="City", warehouse="Warehouse", nova_poshta_city_ref="city-ref", nova_poshta_warehouse_ref="warehouse-ref", declared_value=100)
    shipment.order = SimpleNamespace(order_number="ORD-SYNTH")
    payload = NovaPoshtaShipmentService.__new__(NovaPoshtaShipmentService)._document_payload(shipment, service.connections.connection.settings)

    assert payload["SendersPhone"] == "380671234567"
    assert payload["RecipientsPhone"] == "380671234567"


def test_invalid_sender_phone_is_rejected_on_settings_save() -> None:
    service = _settings_service(); workspace_id = uuid4()

    with pytest.raises(ValueError, match="INVALID_UA_PHONE"):
        service.save_settings(workspace_id, _complete_settings(sender_phone="00380671234567"), uuid4())


def test_invalid_recipient_phone_blocks_provider_call(monkeypatch) -> None:
    monkeypatch.setattr("app.services.nova_poshta_service.get_settings", lambda: SimpleNamespace(staging_nova_poshta_allow_writes=True))
    client = FakeClient("credential")
    settings = _settings_service(lambda credential: client); workspace_id = uuid4()
    settings.save_settings(workspace_id, _complete_settings(), uuid4())
    settings.test_connection(workspace_id, uuid4())
    settings.set_write_permission(workspace_id, NovaPoshtaWritePermissionRequest(allowed=True), uuid4())
    shipment = Shipment(id=uuid4(), workspace_id=workspace_id, order_id=uuid4(), customer_id=uuid4(), carrier=ShipmentCarrier.NOVA_POSHTA.value, status=ShipmentStatus.DRAFT.value, recipient_name="Recipient", recipient_phone="not-a-phone", city="City", warehouse="Warehouse", nova_poshta_city_ref="city-ref", nova_poshta_warehouse_ref="warehouse-ref", declared_value=100)
    shipment.order = SimpleNamespace(order_number="ORD-SYNTH")
    service = NovaPoshtaShipmentService.__new__(NovaPoshtaShipmentService)
    service.db = FakeDb(); service.settings = settings; service.audit_logs = FakeAudit(); service.shipments = SimpleNamespace(get=lambda workspace_id, shipment_id: shipment); service.operations = SimpleNamespace(get_for_update=lambda *args: None)

    response = service.create_ttn(workspace_id, shipment.id, uuid4())

    assert not response.success
    assert "NOVA_POSHTA_RECIPIENT_PHONE_INVALID" in response.errors
    assert not client.create_called


def test_legacy_ttn_updates_last_sync_but_not_verification(monkeypatch) -> None:
    monkeypatch.setattr("app.services.nova_poshta_service.get_settings", lambda: SimpleNamespace(staging_nova_poshta_allow_writes=True))
    client = FakeClient("credential")
    shipment = Shipment(id=uuid4(), workspace_id=uuid4(), order_id=uuid4(), customer_id=uuid4(), carrier=ShipmentCarrier.NOVA_POSHTA.value, status=ShipmentStatus.DRAFT.value, recipient_name="Recipient", recipient_phone="+380671234567", city="City", warehouse="Warehouse", nova_poshta_city_ref="city-ref", nova_poshta_warehouse_ref="warehouse-ref", declared_value=100)
    shipment.order = SimpleNamespace(order_number="ORD-SYNTH")
    service = _shipment_service(shipment)
    service.settings.client_factory = lambda credential: client
    connection = service.settings.connections.connection
    connection.provider_connection_verified_at = None

    response = service.create_ttn(shipment.workspace_id, shipment.id, uuid4())

    assert response.success
    assert connection.last_sync_at is not None
    assert connection.provider_connection_verified_at is None
    assert client.last_payload["SendersPhone"] == "380671234567"
    assert client.last_payload["RecipientsPhone"] == "380671234567"


def test_durable_ttn_success_and_failure_do_not_modify_verification(monkeypatch) -> None:
    monkeypatch.setattr("app.services.nova_poshta_service.get_settings", lambda: SimpleNamespace(staging_nova_poshta_allow_writes=True))
    client = FakeClient("credential")
    shipment = Shipment(id=uuid4(), workspace_id=uuid4(), order_id=uuid4(), customer_id=uuid4(), carrier=ShipmentCarrier.NOVA_POSHTA.value, status=ShipmentStatus.DRAFT.value, recipient_name="Recipient", recipient_phone="+380671234567", city="City", warehouse="Warehouse", nova_poshta_city_ref="city-ref", nova_poshta_warehouse_ref="warehouse-ref", declared_value=100)
    shipment.order = SimpleNamespace(order_number="ORD-SYNTH")
    service = _shipment_service(shipment)
    service.settings.client_factory = lambda credential: client
    service.operations = SimpleNamespace(get_for_update=lambda *args: None)
    connection = service.settings.connections.connection
    connection.provider_connection_verified_at = None

    blocked = service.create_ttn(shipment.workspace_id, shipment.id, uuid4())
    assert not blocked.success
    assert connection.provider_connection_verified_at is None


def test_request_fingerprint_uses_provider_formatted_payload() -> None:
    shipment = Shipment(id=uuid4(), workspace_id=uuid4(), order_id=uuid4(), customer_id=uuid4(), carrier=ShipmentCarrier.NOVA_POSHTA.value, status=ShipmentStatus.DRAFT.value, recipient_name="Recipient", recipient_phone="067 123 45 67", city="City", warehouse="Warehouse", nova_poshta_city_ref="city-ref", nova_poshta_warehouse_ref="warehouse-ref", declared_value=100)
    service = NovaPoshtaShipmentService.__new__(NovaPoshtaShipmentService)
    payload = service._document_payload(shipment, {"sender_city_ref": "sender-city", "sender_warehouse_ref": "sender-wh", "sender_counterparty_ref": "sender", "sender_contact_ref": "contact", "sender_phone": "+380671234567"})
    fingerprint = service._request_fingerprint(payload)

    assert payload["SendersPhone"] == "380671234567"
    assert payload["RecipientsPhone"] == "380671234567"
    assert "067 123" not in fingerprint
