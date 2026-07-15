from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.integrations.nova_poshta_client import NovaPoshtaClient, NovaPoshtaClientError
from app.models.integration_connection import IntegrationConnection, IntegrationProvider, IntegrationStatus
from app.models.integration_credential import IntegrationCredential
from app.models.shipment import ShipmentCarrier, ShipmentStatus
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.integration_repository import IntegrationConnectionRepository, IntegrationCredentialRepository
from app.repositories.shipment_repository import ShipmentRepository
from app.schemas.integration import NovaPoshtaDirectoryItem, NovaPoshtaSettingsRequest, NovaPoshtaSettingsResponse, NovaPoshtaTestConnectionResponse, NovaPoshtaTtnResponse, NovaPoshtaStatusResponse
from app.services.business_utils import snapshot
from app.utils.secrets import decrypt_secret, encrypt_secret, mask_secret


class NovaPoshtaServiceError(ValueError):
    pass


class NovaPoshtaClientProtocol(Protocol):
    def test_connection(self) -> bool: ...
    def search_cities(self, query: str, limit: int = 20): ...
    def search_warehouses(self, city_ref: str, query: str | None = None, limit: int = 50): ...
    def create_internet_document(self, payload: dict): ...
    def get_document_status(self, tracking_number: str) -> str | None: ...


class NovaPoshtaSettingsService:
    def __init__(self, db: Session, client_factory=None) -> None:
        self.db = db
        self.connections = IntegrationConnectionRepository(db)
        self.credentials = IntegrationCredentialRepository(db)
        self.audit_logs = AuditLogRepository(db)
        self.client_factory = client_factory or (lambda api_key: NovaPoshtaClient(api_key))

    def get_settings(self, workspace_id: UUID) -> NovaPoshtaSettingsResponse:
        connection = self.connections.get_by_provider(workspace_id, IntegrationProvider.NOVA_POSHTA.value)
        if connection is None or connection.status == IntegrationStatus.DISCONNECTED.value:
            return NovaPoshtaSettingsResponse(status=IntegrationStatus.DISCONNECTED)
        credential = self.credentials.get_active_for_connection(workspace_id, connection.id)
        api_key = decrypt_secret(credential.encrypted_access_token) if credential else None
        settings = connection.settings or {}
        return NovaPoshtaSettingsResponse(
            status=IntegrationStatus(connection.status),
            connection_name=connection.connection_name,
            connected_at=connection.connected_at,
            last_sync_at=connection.last_sync_at,
            masked_api_key=mask_secret(api_key),
            **settings,
        )

    def save_settings(self, workspace_id: UUID, payload: NovaPoshtaSettingsRequest, actor_user_id: UUID | None) -> NovaPoshtaSettingsResponse:
        connection = self.connections.get_by_provider(workspace_id, IntegrationProvider.NOVA_POSHTA.value)
        if connection is None and not payload.api_key:
            raise NovaPoshtaServiceError("Nova Poshta API key is required for the first connection")
        now = datetime.now(UTC)
        settings = payload.model_dump(exclude={"api_key"})
        if connection is None:
            connection = self.connections.create(IntegrationConnection(workspace_id=workspace_id, provider=IntegrationProvider.NOVA_POSHTA.value, connection_name="Nova Poshta", status=IntegrationStatus.CONNECTED.value, connected_at=now, settings=settings))
        else:
            connection.status = IntegrationStatus.CONNECTED.value
            connection.connected_at = connection.connected_at or now
            connection.settings = settings
        credential = self.credentials.get_active_for_connection(workspace_id, connection.id)
        if payload.api_key:
            encrypted = encrypt_secret(payload.api_key)
            if credential is None:
                self.credentials.create(IntegrationCredential(workspace_id=workspace_id, connection_id=connection.id, encrypted_access_token=encrypted))
            else:
                credential.encrypted_access_token = encrypted
        elif credential is None:
            raise NovaPoshtaServiceError("Nova Poshta API key is required for the first connection")
        audit_action = "NOVA_POSHTA_CONNECTED" if payload.api_key else "NOVA_POSHTA_SENDER_SETTINGS_UPDATED"
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="IntegrationConnection", entity_id=connection.id, action=audit_action, new_value={"provider": IntegrationProvider.NOVA_POSHTA.value, "status": connection.status, "sender_settings_saved": True, "credential_rotated": bool(payload.api_key)})
        self.db.commit()
        return self.get_settings(workspace_id)

    def test_connection(self, workspace_id: UUID, actor_user_id: UUID | None) -> NovaPoshtaTestConnectionResponse:
        connection, api_key = self._require_connection(workspace_id)
        try:
            self.client_factory(api_key).test_connection()
        except Exception:
            connection.status = IntegrationStatus.ERROR.value
            self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="IntegrationConnection", entity_id=connection.id, action="NOVA_POSHTA_ERROR", new_value={"provider": IntegrationProvider.NOVA_POSHTA.value})
            self.db.commit()
            return NovaPoshtaTestConnectionResponse(success=False, message="Nova Poshta connection failed.", status=IntegrationStatus.ERROR)
        connection.status = IntegrationStatus.CONNECTED.value
        connection.last_sync_at = datetime.now(UTC)
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="IntegrationConnection", entity_id=connection.id, action="NOVA_POSHTA_CONNECTION_TESTED", new_value={"provider": IntegrationProvider.NOVA_POSHTA.value, "success": True})
        self.db.commit()
        return NovaPoshtaTestConnectionResponse(success=True, message="Nova Poshta connection is active.", status=IntegrationStatus.CONNECTED)

    def disconnect(self, workspace_id: UUID, actor_user_id: UUID | None) -> NovaPoshtaSettingsResponse:
        connection = self.connections.get_by_provider(workspace_id, IntegrationProvider.NOVA_POSHTA.value)
        if connection:
            connection.status = IntegrationStatus.DISCONNECTED.value
            connection.deleted_at = datetime.now(UTC)
            connection.deleted_by = actor_user_id
            for credential in connection.credentials:
                credential.deleted_at = connection.deleted_at
                credential.deleted_by = actor_user_id
            self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="IntegrationConnection", entity_id=connection.id, action="NOVA_POSHTA_DISCONNECTED", new_value={"provider": IntegrationProvider.NOVA_POSHTA.value})
            self.db.commit()
        return NovaPoshtaSettingsResponse(status=IntegrationStatus.DISCONNECTED)

    def _require_connection(self, workspace_id: UUID) -> tuple[IntegrationConnection, str]:
        connection = self.connections.get_by_provider(workspace_id, IntegrationProvider.NOVA_POSHTA.value)
        if connection is None or connection.status == IntegrationStatus.DISCONNECTED.value:
            raise NovaPoshtaServiceError("Nova Poshta is not configured")
        credential = self.credentials.get_active_for_connection(workspace_id, connection.id)
        if credential is None:
            raise NovaPoshtaServiceError("Nova Poshta API key is not configured")
        return connection, decrypt_secret(credential.encrypted_access_token)


class NovaPoshtaDirectoryService:
    def __init__(self, db: Session, client_factory=None) -> None:
        self.settings = NovaPoshtaSettingsService(db, client_factory)

    def search_cities(self, workspace_id: UUID, query: str, limit: int = 20) -> list[NovaPoshtaDirectoryItem]:
        _connection, api_key = self.settings._require_connection(workspace_id)
        cities = self.settings.client_factory(api_key).search_cities(query, limit)
        return [NovaPoshtaDirectoryItem(ref=city.ref, description=city.description) for city in cities]

    def search_warehouses(self, workspace_id: UUID, city_ref: str, query: str | None = None, limit: int = 50) -> list[NovaPoshtaDirectoryItem]:
        _connection, api_key = self.settings._require_connection(workspace_id)
        warehouses = self.settings.client_factory(api_key).search_warehouses(city_ref, query, limit)
        return [NovaPoshtaDirectoryItem(ref=item.ref, description=item.description, number=item.number) for item in warehouses]


class NovaPoshtaShipmentService:
    _in_progress_ttn_keys: set[tuple[UUID, UUID]] = set()

    def __init__(self, db: Session, client_factory=None, provider_writes_enabled: bool | None = None) -> None:
        self.db = db
        self.shipments = ShipmentRepository(db)
        self.settings = NovaPoshtaSettingsService(db, client_factory)
        self.audit_logs = AuditLogRepository(db)
        self.provider_writes_enabled = provider_writes_enabled

    def create_ttn(self, workspace_id: UUID, shipment_id: UUID, actor_user_id: UUID | None) -> NovaPoshtaTtnResponse:
        connection, api_key = self.settings._require_connection(workspace_id)
        shipment = self.shipments.get(workspace_id, shipment_id)
        errors = self._validate_for_ttn(shipment, connection.settings or {})
        if errors:
            sender_fields = {"sender_city_ref is required", "sender_warehouse_ref is required", "sender_counterparty_ref is required", "sender_contact_ref is required", "sender_phone is required"}
            message = "Sender settings are incomplete. Please fill sender city, warehouse, counterparty, contact person, and phone." if any(error in sender_fields for error in errors) else "Shipment is missing required Nova Poshta fields."
            return NovaPoshtaTtnResponse(success=False, message=message, errors=errors)
        if shipment.tracking_number or shipment.nova_poshta_document_number or shipment.nova_poshta_document_ref:
            return NovaPoshtaTtnResponse(success=False, message="Nova Poshta TTN already exists for this shipment.", tracking_number=shipment.nova_poshta_document_number or shipment.tracking_number, document_ref=shipment.nova_poshta_document_ref, status=shipment.external_status, errors=["ttn already exists"])
        if not self._provider_writes_allowed():
            self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="Shipment", entity_id=shipment_id, action="NOVA_POSHTA_TTN_BLOCKED", new_value={"provider": IntegrationProvider.NOVA_POSHTA.value, "safe_error": "PROVIDER_WRITES_DISABLED"})
            self.db.commit()
            return NovaPoshtaTtnResponse(success=False, message="Nova Poshta provider writes are disabled for this environment.", errors=["NOVA_POSHTA_PROVIDER_WRITES_DISABLED"])
        key = (workspace_id, shipment_id)
        if key in self._in_progress_ttn_keys:
            return NovaPoshtaTtnResponse(success=False, message="Nova Poshta TTN creation is already in progress for this shipment.", errors=["NOVA_POSHTA_TTN_IN_PROGRESS"])
        payload = self._document_payload(shipment, connection.settings or {})
        self._in_progress_ttn_keys.add(key)
        try:
            result = self.settings.client_factory(api_key).create_internet_document(payload)
        except Exception:
            self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="Shipment", entity_id=shipment_id, action="NOVA_POSHTA_ERROR", new_value={"provider": IntegrationProvider.NOVA_POSHTA.value, "safe_error": "TTN_CREATE_FAILED"})
            self.db.commit()
            return NovaPoshtaTtnResponse(success=False, message="Nova Poshta TTN creation failed. Please check the API key and sender settings, then try again.", errors=["NOVA_POSHTA_TTN_FAILED"])
        finally:
            self._in_progress_ttn_keys.discard(key)
        tracking_number = getattr(result, "tracking_number", None)
        document_ref = getattr(result, "document_ref", None)
        external_status = getattr(result, "status", None)
        if not tracking_number or not document_ref:
            self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="Shipment", entity_id=shipment_id, action="NOVA_POSHTA_ERROR", new_value={"provider": IntegrationProvider.NOVA_POSHTA.value, "safe_error": "TTN_CREATE_INCOMPLETE"})
            self.db.commit()
            return NovaPoshtaTtnResponse(success=False, message="Nova Poshta TTN creation returned an incomplete response. Please try again or check Nova Poshta cabinet before retrying.", errors=["NOVA_POSHTA_TTN_INCOMPLETE"])
        shipment.external_provider = IntegrationProvider.NOVA_POSHTA.value
        shipment.external_ref = document_ref
        shipment.external_status = external_status
        shipment.nova_poshta_document_ref = document_ref
        shipment.nova_poshta_document_number = tracking_number
        shipment.tracking_number = tracking_number
        shipment.status = ShipmentStatus.CREATED.value
        connection.last_sync_at = datetime.now(UTC)
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="Shipment", entity_id=shipment.id, action="NOVA_POSHTA_TTN_CREATED", new_value={"tracking_number": tracking_number, "document_ref": document_ref})
        self.db.commit()
        return NovaPoshtaTtnResponse(success=True, message="Nova Poshta TTN created.", tracking_number=tracking_number, document_ref=document_ref, status=external_status)

    def sync_status(self, workspace_id: UUID, shipment_id: UUID, actor_user_id: UUID | None) -> NovaPoshtaStatusResponse:
        _connection, api_key = self.settings._require_connection(workspace_id)
        shipment = self.shipments.get(workspace_id, shipment_id)
        if shipment is None:
            raise NovaPoshtaServiceError("Shipment not found")
        tracking_number = shipment.nova_poshta_document_number or shipment.tracking_number
        if not tracking_number:
            raise NovaPoshtaServiceError("Shipment does not have a Nova Poshta tracking number")
        try:
            status = self.settings.client_factory(api_key).get_document_status(tracking_number)
        except Exception:
            self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="Shipment", entity_id=shipment.id, action="NOVA_POSHTA_ERROR", new_value={"provider": IntegrationProvider.NOVA_POSHTA.value, "safe_error": "STATUS_SYNC_FAILED"})
            self.db.commit()
            return NovaPoshtaStatusResponse(success=False, message="Nova Poshta status sync is unavailable. Please try again later.", tracking_number=tracking_number, status=shipment.external_status, synced_at=shipment.nova_poshta_synced_at)
        if not status:
            self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="Shipment", entity_id=shipment.id, action="NOVA_POSHTA_STATUS_UNAVAILABLE", new_value={"provider": IntegrationProvider.NOVA_POSHTA.value})
            self.db.commit()
            return NovaPoshtaStatusResponse(success=False, message="Nova Poshta status sync is unavailable. Please try again later.", tracking_number=tracking_number, status=shipment.external_status, synced_at=shipment.nova_poshta_synced_at)
        normalized_status = self._normalize_provider_status(status)
        shipment.nova_poshta_raw_status = status
        shipment.external_status = status
        if normalized_status is not None:
            shipment.status = normalized_status.value
        shipment.nova_poshta_synced_at = datetime.now(UTC)
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="Shipment", entity_id=shipment.id, action="NOVA_POSHTA_STATUS_SYNCED", new_value={"status": status, "normalized_status": normalized_status.value if normalized_status else None})
        self.db.commit()
        return NovaPoshtaStatusResponse(success=True, message="Nova Poshta status synced.", tracking_number=tracking_number, status=status, synced_at=shipment.nova_poshta_synced_at)

    def _provider_writes_allowed(self) -> bool:
        if self.provider_writes_enabled is not None:
            return self.provider_writes_enabled
        return get_settings().staging_nova_poshta_allow_writes

    def _normalize_provider_status(self, provider_status: str) -> ShipmentStatus | None:
        normalized = provider_status.casefold()
        delivered_markers = ("delivered", "отримано", "доставлено")
        returned_markers = ("return", "повер", "відмова")
        in_transit_markers = ("in transit", "дороз", "пряму", "відправ")
        arrived_markers = ("arrived", "прибул", "відділен")
        if any(marker in normalized for marker in delivered_markers):
            return ShipmentStatus.DELIVERED
        if any(marker in normalized for marker in returned_markers):
            return ShipmentStatus.RETURNED
        if any(marker in normalized for marker in in_transit_markers):
            return ShipmentStatus.IN_TRANSIT
        if any(marker in normalized for marker in arrived_markers):
            return ShipmentStatus.ARRIVED
        return None

    def _validate_for_ttn(self, shipment, settings: dict) -> list[str]:
        if shipment is None:
            return ["shipment not found"]
        errors = []
        if shipment.carrier != ShipmentCarrier.NOVA_POSHTA.value:
            errors.append("carrier must be NOVA_POSHTA")
        if not shipment.order:
            errors.append("order is required")
        if not shipment.customer_id:
            errors.append("customer is required")
        if not shipment.recipient_name:
            errors.append("recipient_name is required")
        if not shipment.recipient_phone:
            errors.append("recipient_phone is required")
        if not (shipment.city or shipment.nova_poshta_city_ref):
            errors.append("city is required")
        if not (shipment.warehouse or shipment.nova_poshta_warehouse_ref):
            errors.append("warehouse is required")
        if shipment.declared_value is None:
            errors.append("declared_value is required")
        for field in ("sender_city_ref", "sender_warehouse_ref", "sender_counterparty_ref", "sender_contact_ref", "sender_phone"):
            if not settings.get(field):
                errors.append(f"{field} is required")
        return errors

    def _document_payload(self, shipment, settings: dict) -> dict:
        return {
            "PayerType": "Recipient",
            "PaymentMethod": "Cash",
            "CargoType": "Parcel",
            "ServiceType": "WarehouseWarehouse",
            "Cost": str(shipment.declared_value or 0),
            "CitySender": settings.get("sender_city_ref"),
            "Sender": settings.get("sender_counterparty_ref"),
            "SenderAddress": settings.get("sender_warehouse_ref"),
            "ContactSender": settings.get("sender_contact_ref"),
            "SendersPhone": settings.get("sender_phone"),
            "CityRecipient": shipment.nova_poshta_city_ref,
            "RecipientAddress": shipment.nova_poshta_warehouse_ref,
            "RecipientsPhone": shipment.recipient_phone,
            "RecipientName": shipment.recipient_name,
        }
