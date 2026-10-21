from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
import pytest

from app.models.integration_connection import IntegrationConnection, IntegrationProvider, IntegrationStatus
from app.models.integration_credential import IntegrationCredential
from app.models.nova_poshta_operation import NovaPoshtaOperationState, NovaPoshtaOperationType
from app.models.role import RoleName
from app.models.shipment import Shipment, ShipmentCarrier, ShipmentStatus
from app.schemas.integration import NovaPoshtaSettingsRequest, NovaPoshtaWritePermissionRequest
from app.services.nova_poshta_service import NovaPoshtaDirectoryService, NovaPoshtaSettingsService, NovaPoshtaShipmentService
from app.integrations.nova_poshta_client import NovaPoshtaClientError
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
        self.credential = credential; self.fail = fail; self.fail_create = fail_create; self.fail_status = fail_status; self.sender_error = sender_error; self.create_called = False; self.delete_called = False; self.last_payload = None
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
    def delete_internet_document(self, document_ref):
        self.delete_called = True
        if self.fail_create:
            raise NovaPoshtaClientError("ambiguous", code="NOVA_POSHTA_PROVIDER_RESPONSE_AMBIGUOUS", ambiguous=True)
        return True


class FakeOperations:
    def __init__(self): self.items = {}
    def get_for_update(self, workspace_id, shipment_id, operation_type=NovaPoshtaOperationType.CREATE_TTN.value):
        return self.items.get((workspace_id, shipment_id, operation_type))
    def create(self, operation):
        self.items[(operation.workspace_id, operation.shipment_id, operation.operation_type)] = operation
        return operation


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


def test_readiness_exposes_write_gate_without_credentials_or_sender_references(monkeypatch) -> None:
    monkeypatch.setattr("app.services.nova_poshta_service.get_settings", lambda: SimpleNamespace(staging_nova_poshta_allow_writes=True))
    service = _settings_service()
    workspace_id = uuid4()
    service.save_settings(workspace_id, _complete_settings(), uuid4())
    service.test_connection(workspace_id, uuid4())
    service.set_write_permission(workspace_id, NovaPoshtaWritePermissionRequest(allowed=True), uuid4())

    response = service.get_readiness(workspace_id)
    payload = response.model_dump()

    assert response.provider_writes_enabled
    assert set(payload) == {
        "provider",
        "status",
        "environment_capability",
        "workspace_permission",
        "provider_writes_enabled",
        "sender_configured",
        "connection_verified",
        "write_blockers",
    }
    serialized = str(payload)
    assert "synthetic-credential-value" not in serialized
    assert "sender-wh" not in serialized
    assert "contact" not in serialized


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


def test_cod_payment_mode_change_invalidates_live_write_permission(monkeypatch) -> None:
    monkeypatch.setattr("app.services.nova_poshta_service.get_settings", lambda: SimpleNamespace(staging_nova_poshta_allow_writes=True))
    service = _settings_service()
    workspace_id = uuid4()
    service.save_settings(workspace_id, _complete_settings(), uuid4())
    assert service.get_settings(workspace_id).cod_payment_mode == "MONEY_RETURN"
    assert service.test_connection(workspace_id, uuid4()).success
    service.set_write_permission(workspace_id, NovaPoshtaWritePermissionRequest(allowed=True), uuid4())

    updated = service.save_settings(
        workspace_id,
        NovaPoshtaSettingsRequest(cod_payment_mode="PAYMENT_CONTROL"),
        uuid4(),
    )
    assert updated.cod_payment_mode == "PAYMENT_CONTROL"
    assert updated.connection_verified is False
    assert updated.provider_writes_enabled is False
    assert updated.workspace_permission is False
    assert service.audit_logs.records[-2]["action"] == "NOVA_POSHTA_VERIFICATION_INVALIDATED"
    assert service.audit_logs.records[-1]["action"] == "NOVA_POSHTA_PAYMENT_SETTINGS_UPDATED"
    assert service.test_connection(workspace_id, uuid4()).success
    service.set_write_permission(workspace_id, NovaPoshtaWritePermissionRequest(allowed=True), uuid4())
    repeat = service.save_settings(
        workspace_id,
        NovaPoshtaSettingsRequest(cod_payment_mode="PAYMENT_CONTROL"),
        uuid4(),
    )
    assert repeat.provider_writes_enabled is True


def test_cargo_description_can_be_configured_without_disabling_ttn(monkeypatch) -> None:
    monkeypatch.setattr("app.services.nova_poshta_service.get_settings", lambda: SimpleNamespace(staging_nova_poshta_allow_writes=True))
    service = _settings_service()
    workspace_id = uuid4()
    service.save_settings(workspace_id, _complete_settings(), uuid4())
    service.test_connection(workspace_id, uuid4())
    service.set_write_permission(workspace_id, NovaPoshtaWritePermissionRequest(allowed=True), uuid4())

    updated = service.save_settings(
        workspace_id,
        NovaPoshtaSettingsRequest(cargo_description="  Біжутерія  "),
        uuid4(),
    )

    assert updated.cargo_description == "Біжутерія"
    assert updated.provider_writes_enabled
    assert updated.connection_verified
    assert updated.workspace_permission


def test_cargo_description_mode_can_be_enabled_without_disabling_ttn(monkeypatch) -> None:
    monkeypatch.setattr("app.services.nova_poshta_service.get_settings", lambda: SimpleNamespace(staging_nova_poshta_allow_writes=True))
    service = _settings_service()
    workspace_id = uuid4()
    service.save_settings(workspace_id, _complete_settings(), uuid4())
    service.test_connection(workspace_id, uuid4())
    service.set_write_permission(workspace_id, NovaPoshtaWritePermissionRequest(allowed=True), uuid4())
    updated = service.save_settings(
        workspace_id, NovaPoshtaSettingsRequest(cargo_description_mode="AUTO_ACCESSORIES"), uuid4()
    )
    assert updated.cargo_description_mode == "AUTO_ACCESSORIES"
    assert updated.provider_writes_enabled


def test_cargo_description_mode_rejects_unknown_value() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        NovaPoshtaSettingsRequest(cargo_description_mode="UNSAFE")


def test_cod_payment_mode_rejects_unknown_mode() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        NovaPoshtaSettingsRequest(cod_payment_mode="INVALID")


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


def test_cancel_ttn_is_provider_confirmed_and_idempotent(monkeypatch) -> None:
    monkeypatch.setattr("app.services.nova_poshta_service.get_settings", lambda: SimpleNamespace(staging_nova_poshta_allow_writes=True))
    client = FakeClient("credential")
    shipment = Shipment(id=uuid4(), workspace_id=uuid4(), order_id=uuid4(), customer_id=uuid4(), carrier=ShipmentCarrier.NOVA_POSHTA.value, status=ShipmentStatus.CREATED.value, nova_poshta_document_ref="doc-ref", nova_poshta_document_number="TTN-001", tracking_number="TTN-001")
    service = _shipment_service(shipment)
    service.settings.client_factory = lambda credential: client
    service.settings.test_connection(shipment.workspace_id, uuid4())
    service.settings.set_write_permission(shipment.workspace_id, NovaPoshtaWritePermissionRequest(allowed=True), uuid4())
    service.operations = FakeOperations()

    first = service.cancel_ttn(shipment.workspace_id, shipment.id, uuid4())
    second = service.cancel_ttn(shipment.workspace_id, shipment.id, uuid4())

    assert first.success and second.success
    assert client.delete_called
    assert second.reused_existing_result
    assert shipment.status == ShipmentStatus.CANCELLED.value
    operation = service.operations.get_for_update(shipment.workspace_id, shipment.id, NovaPoshtaOperationType.CANCEL_TTN.value)
    assert operation.state == NovaPoshtaOperationState.CANCELLED.value
    assert operation.attempt_count == 1


def test_cancel_ttn_ambiguous_result_blocks_blind_retry(monkeypatch) -> None:
    monkeypatch.setattr("app.services.nova_poshta_service.get_settings", lambda: SimpleNamespace(staging_nova_poshta_allow_writes=True))
    client = FakeClient("credential", fail_create=True)
    shipment = Shipment(id=uuid4(), workspace_id=uuid4(), order_id=uuid4(), customer_id=uuid4(), carrier=ShipmentCarrier.NOVA_POSHTA.value, status=ShipmentStatus.CREATED.value, nova_poshta_document_ref="doc-ref", nova_poshta_document_number="TTN-001", tracking_number="TTN-001")
    service = _shipment_service(shipment)
    service.settings.client_factory = lambda credential: client
    service.settings.test_connection(shipment.workspace_id, uuid4())
    service.settings.set_write_permission(shipment.workspace_id, NovaPoshtaWritePermissionRequest(allowed=True), uuid4())
    service.operations = FakeOperations()

    first = service.cancel_ttn(shipment.workspace_id, shipment.id, uuid4())
    second = service.cancel_ttn(shipment.workspace_id, shipment.id, uuid4())

    assert not first.success and not second.success
    assert first.manual_reconciliation_required and second.blind_retry_blocked
    operation = service.operations.get_for_update(shipment.workspace_id, shipment.id, NovaPoshtaOperationType.CANCEL_TTN.value)
    assert operation.attempt_count == 1
    assert shipment.status == ShipmentStatus.CREATED.value


def test_onboarding_blank_key_preserves_credential_and_verification():
    service = _settings_service(); workspace = uuid4()
    service.save_settings(workspace, _complete_settings(), uuid4())
    service.test_connection(workspace, uuid4())
    encrypted = service.credentials.credential.encrypted_access_token
    response = service.save_settings(workspace, NovaPoshtaSettingsRequest(api_key="   "), uuid4())
    assert service.credentials.credential.encrypted_access_token == encrypted
    assert response.connection_verified
    assert not response.workspace_permission


def test_onboarding_sender_change_clears_old_contact_and_verification():
    service = _settings_service(); workspace = uuid4()
    service.save_settings(workspace, _complete_settings(), uuid4())
    service.test_connection(workspace, uuid4())
    response = service.save_settings(workspace, NovaPoshtaSettingsRequest(sender_counterparty_ref="other"), uuid4())
    assert response.sender_contact_ref is None
    assert not response.connection_verified
    assert not response.workspace_permission


def test_onboarding_lookup_shapes_are_sender_only_read_only_and_bounded():
    from app.integrations.nova_poshta_client import NovaPoshtaClient
    client = NovaPoshtaClient("synthetic-test-key")
    calls = []
    def call(model, method, props):
        calls.append((model, method, props))
        return {"data": [{"Ref": str(i), "Description": f"Name {i}"} for i in range(60)]}
    client._call = call
    assert len(client.search_senders("Shop", 2, 3)) == 2
    assert calls[-1] == ("Counterparty", "getCounterparties", {"CounterpartyProperty": "Sender", "Page": "3", "Limit": "2", "FindByString": "Shop"})
    assert len(client.search_sender_contacts("0", 2)) == 2
    assert calls[-1] == ("Counterparty", "getCounterpartyContactPersons", {"Ref": "0", "Page": "1"})
    assert client.counterparty_exists("0")
    assert calls[-1][2]["CounterpartyProperty"] == "Sender"
    assert all(method.startswith("get") for _, method, _ in calls)


def test_onboarding_lookup_rejects_arbitrary_sender_and_isolates_workspace():
    service = _settings_service(); workspace = uuid4()
    service.save_settings(workspace, _complete_settings(), uuid4())
    directory = NovaPoshtaDirectoryService.__new__(NovaPoshtaDirectoryService)
    directory.settings = service
    with pytest.raises(ValueError, match="COUNTERPARTY_INVALID"):
        directory.search_sender_contacts(workspace, "arbitrary-ref")
    with pytest.raises(ValueError, match="not configured"):
        directory.search_senders(uuid4())


def test_onboarding_lookup_failure_never_reflects_provider_secret():
    class FailedClient(FakeClient):
        def search_senders(self, *args):
            raise RuntimeError("synthetic-secret-provider-response")
    service = _settings_service(lambda key: FailedClient(key)); workspace = uuid4()
    service.save_settings(workspace, _complete_settings(), uuid4())
    directory = NovaPoshtaDirectoryService.__new__(NovaPoshtaDirectoryService); directory.settings = service
    with pytest.raises(ValueError, match="^NOVA_POSHTA_SENDER_LOOKUP_UNAVAILABLE$"):
        directory.search_senders(workspace)


def test_onboarding_lookup_routes_require_owner():
    from app.api.v1.nova_poshta import router
    for route in router.routes:
        if route.path.endswith(("/senders", "/sender-contacts")):
            role_dependency = next(d.call for d in route.dependant.dependencies if d.name == "current_user")
            for role in (RoleName.MANAGER, RoleName.ANALYST):
                with pytest.raises(HTTPException) as error:
                    role_dependency(SimpleNamespace(workspaces=[SimpleNamespace(workspace_id=(workspace := uuid4()), workspace=SimpleNamespace(is_active=True), role=SimpleNamespace(name=role.value))]), workspace)
                assert error.value.status_code == 403


@pytest.mark.parametrize("field", ["sender_counterparty_ref", "sender_contact_ref", "sender_city_ref", "sender_warehouse_ref", "sender_phone"])
def test_explicit_sender_null_clears_verified_permitted_settings(monkeypatch, field):
    monkeypatch.setattr("app.services.nova_poshta_service.get_settings", lambda: SimpleNamespace(staging_nova_poshta_allow_writes=True))
    service = _settings_service(); workspace = uuid4()
    service.save_settings(workspace, _complete_settings(), uuid4())
    assert service.test_connection(workspace, uuid4()).success
    service.set_write_permission(workspace, NovaPoshtaWritePermissionRequest(allowed=True), uuid4())
    assert service.get_settings(workspace).provider_writes_enabled
    encrypted = service.credentials.credential.encrypted_access_token
    result = service.save_settings(workspace, NovaPoshtaSettingsRequest(**{field: None}, api_key=""), uuid4())
    assert getattr(result, field) is None
    assert service.connections.connection.settings[field] is None
    if field == "sender_counterparty_ref":
        assert result.sender_contact_ref is None
    if field == "sender_city_ref":
        assert result.sender_warehouse_ref is None
    assert not result.sender_configured
    assert not result.connection_verified
    assert not result.workspace_permission
    assert not result.provider_writes_enabled
    assert service.credentials.credential.encrypted_access_token == encrypted


def test_blank_key_only_preserves_verified_permitted_settings(monkeypatch):
    monkeypatch.setattr("app.services.nova_poshta_service.get_settings", lambda: SimpleNamespace(staging_nova_poshta_allow_writes=True))
    service = _settings_service(); workspace = uuid4()
    service.save_settings(workspace, _complete_settings(), uuid4())
    assert service.test_connection(workspace, uuid4()).success
    service.set_write_permission(workspace, NovaPoshtaWritePermissionRequest(allowed=True), uuid4())
    assert service.get_settings(workspace).provider_writes_enabled
    settings = dict(service.connections.connection.settings)
    credential = service.credentials.credential.encrypted_access_token
    result = service.save_settings(workspace, NovaPoshtaSettingsRequest(api_key="   "), uuid4())
    assert result.connection_verified
    assert result.workspace_permission
    assert result.provider_writes_enabled
    assert service.connections.connection.settings == settings
    assert service.credentials.credential.encrypted_access_token == credential


@pytest.mark.parametrize("bad_field,error", [
    (None, None),
    ("sender_counterparty_ref", "NOVA_POSHTA_SENDER_COUNTERPARTY_INVALID"),
    ("sender_contact_ref", "NOVA_POSHTA_SENDER_CONTACT_INVALID"),
    ("sender_city_ref", "NOVA_POSHTA_SENDER_CITY_MISMATCH"),
    ("sender_warehouse_ref", "NOVA_POSHTA_SENDER_CITY_MISMATCH"),
])
def test_warehouse_sender_tuple_through_real_client_transport(monkeypatch, bad_field, error):
    import json
    from app.integrations.nova_poshta_client import NovaPoshtaClient
    from app.services.nova_poshta_service import NovaPoshtaShipmentService
    sender = "11111111-1111-4111-8111-111111111111"
    contact = "22222222-2222-4222-8222-222222222222"
    city = "33333333-3333-4333-8333-333333333333"
    warehouse = "44444444-4444-4444-8444-444444444444"
    street_address = "55555555-5555-4555-8555-555555555555"
    calls = []
    def transport(request, timeout):
        payload = json.loads(request.data)
        assert request.get_method() == "POST"
        assert payload["apiKey"] == "synthetic-transport-key"
        model, method, props = payload["modelName"], payload["calledMethod"], payload["methodProperties"]
        calls.append((model, method, props))
        if method == "getAreas": data = [{"Ref": "synthetic-area"}]
        elif method == "getCounterparties":
            assert props["CounterpartyProperty"] == "Sender"
            data = [{"Ref": sender, "Description": "Синтетичний магазин"}]
        elif method == "getCounterpartyContactPersons":
            data = [{"Ref": contact, "Description": "Олена Тестова"}] if props["Ref"] == sender else []
        elif method == "getCounterpartyAddresses":
            data = [{"Ref": street_address, "CityRef": city, "Description": "вул. Тестова, 10"}]
        elif method == "getWarehouses":
            data = [{"Ref": warehouse, "CityRef": city, "Description": "Відділення №1", "Number": "1"}] if props["CityRef"] == city else []
        else: raise AssertionError(f"Unexpected provider call: {model}/{method}")
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return json.dumps({"success": True, "data": data}).encode()
        return Response()
    monkeypatch.setattr("app.integrations.nova_poshta_client.request.urlopen", transport)
    service = _settings_service(lambda key: NovaPoshtaClient(key))
    workspace = uuid4()
    values = dict(api_key="synthetic-transport-key", sender_counterparty_ref=sender, sender_contact_ref=contact,
                  sender_city_ref=city, sender_warehouse_ref=warehouse, sender_phone="0671234567")
    client = NovaPoshtaClient("synthetic-transport-key")
    # Street-address and directory-warehouse identities are deliberately distinct.
    assert not client.sender_address_belongs_to_sender(sender, warehouse)
    directory = NovaPoshtaDirectoryService.__new__(NovaPoshtaDirectoryService); directory.settings = service
    service.save_settings(workspace, NovaPoshtaSettingsRequest(**values), uuid4())
    assert directory.search_senders(workspace)[0].ref == sender
    assert directory.search_sender_contacts(workspace, sender)[0].ref == contact
    assert directory.search_warehouses(workspace, city)[0].ref == warehouse
    if bad_field:
        # A valid sender street-address Ref is still invalid as a warehouse Ref.
        values[bad_field] = street_address
        service.save_settings(workspace, NovaPoshtaSettingsRequest(**values), uuid4())
    response = service.test_connection(workspace, uuid4())
    assert response.success is (error is None)
    assert response.errors == ([error] if error else [])
    assert service.get_settings(workspace).connection_verified is (error is None)
    assert not service.get_settings(workspace).workspace_permission
    if error is None:
        shipment = SimpleNamespace(declared_value=100, nova_poshta_city_ref=city, nova_poshta_warehouse_ref=warehouse,
                                   recipient_phone="0671234567", recipient_name="Одержувач", cod_amount=0)
        payload = NovaPoshtaShipmentService.__new__(NovaPoshtaShipmentService)._document_payload(shipment, values)
        assert payload["ServiceType"] == "WarehouseWarehouse"
        assert payload["SenderAddress"] == warehouse
        assert payload["SenderAddress"] != street_address
    assert all(method.startswith(("get", "search")) for _, method, _ in calls)
