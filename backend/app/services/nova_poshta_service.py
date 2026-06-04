from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

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
        now = datetime.now(UTC)
        settings = payload.model_dump(exclude={"api_key"})
        if connection is None:
            connection = self.connections.create(IntegrationConnection(workspace_id=workspace_id, provider=IntegrationProvider.NOVA_POSHTA.value, connection_name="Nova Poshta", status=IntegrationStatus.CONNECTED.value, connected_at=now, settings=settings))
        else:
            connection.status = IntegrationStatus.CONNECTED.value
            connection.connected_at = connection.connected_at or now
            connection.settings = settings
        credential = self.credentials.get_active_for_connection(workspace_id, connection.id)
        encrypted = encrypt_secret(payload.api_key)
        if credential is None:
            self.credentials.create(IntegrationCredential(workspace_id=workspace_id, connection_id=connection.id, encrypted_access_token=encrypted))
        else:
            credential.encrypted_access_token = encrypted
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="IntegrationConnection", entity_id=connection.id, action="NOVA_POSHTA_CONNECTED", new_value={"provider": IntegrationProvider.NOVA_POSHTA.value, "status": connection.status})
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
    def __init__(self, db: Session, client_factory=None) -> None:
        self.db = db
        self.shipments = ShipmentRepository(db)
        self.settings = NovaPoshtaSettingsService(db, client_factory)
        self.audit_logs = AuditLogRepository(db)

    def create_ttn(self, workspace_id: UUID, shipment_id: UUID, actor_user_id: UUID | None) -> NovaPoshtaTtnResponse:
        connection, api_key = self.settings._require_connection(workspace_id)
        shipment = self.shipments.get(workspace_id, shipment_id)
        errors = self._validate_for_ttn(shipment, connection.settings or {})
        if errors:
            return NovaPoshtaTtnResponse(success=False, message="Shipment is missing required Nova Poshta fields.", errors=errors)
        payload = self._document_payload(shipment, connection.settings or {})
        try:
            result = self.settings.client_factory(api_key).create_internet_document(payload)
        except Exception as exc:
            self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="Shipment", entity_id=shipment_id, action="NOVA_POSHTA_ERROR", new_value={"provider": IntegrationProvider.NOVA_POSHTA.value})
            self.db.commit()
            return NovaPoshtaTtnResponse(success=False, message="Nova Poshta TTN creation failed.", errors=[str(exc)])
        shipment.external_provider = IntegrationProvider.NOVA_POSHTA.value
        shipment.external_ref = result.document_ref
        shipment.external_status = result.status
        shipment.nova_poshta_document_ref = result.document_ref
        shipment.nova_poshta_document_number = result.tracking_number
        shipment.tracking_number = result.tracking_number
        shipment.status = ShipmentStatus.CREATED.value
        connection.last_sync_at = datetime.now(UTC)
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="Shipment", entity_id=shipment.id, action="NOVA_POSHTA_TTN_CREATED", new_value={"tracking_number": result.tracking_number, "document_ref": result.document_ref})
        self.db.commit()
        return NovaPoshtaTtnResponse(success=True, message="Nova Poshta TTN created.", tracking_number=result.tracking_number, document_ref=result.document_ref, status=result.status)

    def sync_status(self, workspace_id: UUID, shipment_id: UUID, actor_user_id: UUID | None) -> NovaPoshtaStatusResponse:
        _connection, api_key = self.settings._require_connection(workspace_id)
        shipment = self.shipments.get(workspace_id, shipment_id)
        if shipment is None:
            raise NovaPoshtaServiceError("Shipment not found")
        tracking_number = shipment.nova_poshta_document_number or shipment.tracking_number
        if not tracking_number:
            raise NovaPoshtaServiceError("Shipment does not have a Nova Poshta tracking number")
        status = self.settings.client_factory(api_key).get_document_status(tracking_number)
        shipment.nova_poshta_raw_status = status
        shipment.external_status = status
        shipment.nova_poshta_synced_at = datetime.now(UTC)
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="Shipment", entity_id=shipment.id, action="NOVA_POSHTA_STATUS_SYNCED", new_value={"status": status})
        self.db.commit()
        return NovaPoshtaStatusResponse(success=True, message="Nova Poshta status synced.", tracking_number=tracking_number, status=status, synced_at=shipment.nova_poshta_synced_at)

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
