from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import json
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.integrations.nova_poshta_client import (
    NovaPoshtaClient,
    NovaPoshtaClientError,
    NovaPoshtaDocumentResult,
)
from app.models.integration_connection import IntegrationConnection, IntegrationProvider, IntegrationStatus
from app.models.integration_credential import IntegrationCredential
from app.models.nova_poshta_operation import (
    NovaPoshtaOperation,
    NovaPoshtaOperationState,
    NovaPoshtaOperationType,
)
from app.models.shipment import ShipmentCarrier, ShipmentStatus
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.integration_repository import IntegrationConnectionRepository, IntegrationCredentialRepository
from app.repositories.nova_poshta_operation_repository import NovaPoshtaOperationRepository
from app.repositories.shipment_repository import ShipmentRepository
from app.schemas.integration import (
    NovaPoshtaDirectoryItem,
    NovaPoshtaSettingsRequest,
    NovaPoshtaSettingsResponse,
    NovaPoshtaStatusResponse,
    NovaPoshtaTestConnectionResponse,
    NovaPoshtaTtnResponse,
)
from app.utils.secrets import decrypt_secret, encrypt_secret, mask_secret


class NovaPoshtaServiceError(ValueError):
    pass


class NovaPoshtaClientProtocol(Protocol):
    def test_connection(self) -> bool: ...
    def search_cities(self, query: str, limit: int = 20): ...
    def search_warehouses(self, city_ref: str, query: str | None = None, limit: int = 50): ...
    def create_internet_document(self, payload: dict): ...
    def find_internet_document(self, marker: str, date_from: datetime, date_to: datetime): ...
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
            return NovaPoshtaSettingsResponse(
                status=IntegrationStatus.DISCONNECTED,
                provider_writes_enabled=get_settings().staging_nova_poshta_allow_writes,
            )
        credential = self.credentials.get_active_for_connection(workspace_id, connection.id)
        api_key = decrypt_secret(credential.encrypted_access_token) if credential else None
        settings = connection.settings or {}
        required_sender_fields = (
            "sender_city_ref",
            "sender_warehouse_ref",
            "sender_counterparty_ref",
            "sender_contact_ref",
            "sender_phone",
        )
        return NovaPoshtaSettingsResponse(
            status=IntegrationStatus(connection.status),
            connection_name=connection.connection_name,
            connected_at=connection.connected_at,
            last_sync_at=connection.last_sync_at,
            masked_api_key=mask_secret(api_key),
            provider_writes_enabled=get_settings().staging_nova_poshta_allow_writes,
            sender_configured=all(bool(settings.get(field)) for field in required_sender_fields),
            **settings,
        )

    def save_settings(
        self,
        workspace_id: UUID,
        payload: NovaPoshtaSettingsRequest,
        actor_user_id: UUID | None,
    ) -> NovaPoshtaSettingsResponse:
        connection = self.connections.get_by_provider(workspace_id, IntegrationProvider.NOVA_POSHTA.value)
        if connection is None and not payload.api_key:
            raise NovaPoshtaServiceError("Nova Poshta API key is required for the first connection")
        now = datetime.now(UTC)
        existing_settings = dict(connection.settings or {}) if connection else {}
        updates = payload.model_dump(exclude={"api_key"}, exclude_unset=True)
        settings = {**existing_settings, **{key: value for key, value in updates.items() if value is not None}}
        if connection is None:
            connection = self.connections.create(
                IntegrationConnection(
                    workspace_id=workspace_id,
                    provider=IntegrationProvider.NOVA_POSHTA.value,
                    connection_name="Nova Poshta",
                    status=IntegrationStatus.CONNECTED.value,
                    connected_at=now,
                    settings=settings,
                )
            )
        else:
            connection.status = IntegrationStatus.CONNECTED.value
            connection.connected_at = connection.connected_at or now
            connection.settings = settings
        credential = self.credentials.get_active_for_connection(workspace_id, connection.id)
        if payload.api_key:
            encrypted = encrypt_secret(payload.api_key)
            if credential is None:
                self.credentials.create(
                    IntegrationCredential(
                        workspace_id=workspace_id,
                        connection_id=connection.id,
                        encrypted_access_token=encrypted,
                    )
                )
            else:
                credential.encrypted_access_token = encrypted
        elif credential is None:
            raise NovaPoshtaServiceError("Nova Poshta API key is required for the first connection")
        audit_action = "NOVA_POSHTA_CONNECTED" if payload.api_key else "NOVA_POSHTA_SENDER_SETTINGS_UPDATED"
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="IntegrationConnection",
            entity_id=connection.id,
            action=audit_action,
            new_value={
                "provider": IntegrationProvider.NOVA_POSHTA.value,
                "status": connection.status,
                "sender_settings_saved": True,
                "credential_rotated": bool(payload.api_key),
            },
        )
        self.db.commit()
        return self.get_settings(workspace_id)

    def test_connection(
        self,
        workspace_id: UUID,
        actor_user_id: UUID | None,
    ) -> NovaPoshtaTestConnectionResponse:
        connection, api_key = self._require_connection(workspace_id)
        try:
            self.client_factory(api_key).test_connection()
        except Exception:
            connection.status = IntegrationStatus.ERROR.value
            self.audit_logs.create(
                workspace_id=workspace_id,
                user_id=actor_user_id,
                entity_type="IntegrationConnection",
                entity_id=connection.id,
                action="NOVA_POSHTA_ERROR",
                new_value={
                    "provider": IntegrationProvider.NOVA_POSHTA.value,
                    "safe_error": "CONNECTION_TEST_FAILED",
                },
            )
            self.db.commit()
            return NovaPoshtaTestConnectionResponse(
                success=False,
                message="Nova Poshta connection failed.",
                status=IntegrationStatus.ERROR,
            )
        connection.status = IntegrationStatus.CONNECTED.value
        connection.last_sync_at = datetime.now(UTC)
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="IntegrationConnection",
            entity_id=connection.id,
            action="NOVA_POSHTA_CONNECTION_TESTED",
            new_value={"provider": IntegrationProvider.NOVA_POSHTA.value, "success": True},
        )
        self.db.commit()
        return NovaPoshtaTestConnectionResponse(
            success=True,
            message="Nova Poshta connection is active.",
            status=IntegrationStatus.CONNECTED,
        )

    def disconnect(self, workspace_id: UUID, actor_user_id: UUID | None) -> NovaPoshtaSettingsResponse:
        connection = self.connections.get_by_provider(workspace_id, IntegrationProvider.NOVA_POSHTA.value)
        if connection:
            connection.status = IntegrationStatus.DISCONNECTED.value
            connection.deleted_at = datetime.now(UTC)
            connection.deleted_by = actor_user_id
            for credential in connection.credentials:
                credential.deleted_at = connection.deleted_at
                credential.deleted_by = actor_user_id
            self.audit_logs.create(
                workspace_id=workspace_id,
                user_id=actor_user_id,
                entity_type="IntegrationConnection",
                entity_id=connection.id,
                action="NOVA_POSHTA_DISCONNECTED",
                new_value={"provider": IntegrationProvider.NOVA_POSHTA.value},
            )
            self.db.commit()
        return NovaPoshtaSettingsResponse(
            status=IntegrationStatus.DISCONNECTED,
            provider_writes_enabled=get_settings().staging_nova_poshta_allow_writes,
        )

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

    def search_cities(
        self,
        workspace_id: UUID,
        query: str,
        limit: int = 20,
    ) -> list[NovaPoshtaDirectoryItem]:
        _connection, api_key = self.settings._require_connection(workspace_id)
        try:
            cities = self.settings.client_factory(api_key).search_cities(query, limit)
        except NovaPoshtaClientError as exc:
            raise NovaPoshtaServiceError("Nova Poshta city search is temporarily unavailable") from exc
        return [NovaPoshtaDirectoryItem(ref=city.ref, description=city.description) for city in cities]

    def search_warehouses(
        self,
        workspace_id: UUID,
        city_ref: str,
        query: str | None = None,
        limit: int = 50,
    ) -> list[NovaPoshtaDirectoryItem]:
        _connection, api_key = self.settings._require_connection(workspace_id)
        try:
            warehouses = self.settings.client_factory(api_key).search_warehouses(city_ref, query, limit)
        except NovaPoshtaClientError as exc:
            raise NovaPoshtaServiceError("Nova Poshta warehouse search is temporarily unavailable") from exc
        return [
            NovaPoshtaDirectoryItem(ref=item.ref, description=item.description, number=item.number)
            for item in warehouses
        ]


class NovaPoshtaShipmentService:
    def __init__(
        self,
        db: Session,
        client_factory=None,
        provider_writes_enabled: bool | None = None,
    ) -> None:
        self.db = db
        self.shipments = ShipmentRepository(db)
        self.operations = NovaPoshtaOperationRepository(db)
        self.settings = NovaPoshtaSettingsService(db, client_factory)
        self.audit_logs = AuditLogRepository(db)
        self.provider_writes_enabled = provider_writes_enabled

    def create_ttn(
        self,
        workspace_id: UUID,
        shipment_id: UUID,
        actor_user_id: UUID | None,
    ) -> NovaPoshtaTtnResponse:
        connection, api_key = self.settings._require_connection(workspace_id)
        shipment = self._get_shipment_for_update(workspace_id, shipment_id)
        errors = self._validate_for_ttn(shipment, connection.settings or {})
        if errors:
            sender_fields = {
                "sender_city_ref is required",
                "sender_warehouse_ref is required",
                "sender_counterparty_ref is required",
                "sender_contact_ref is required",
                "sender_phone is required",
            }
            message = (
                "Sender settings are incomplete. Please fill sender city, warehouse, counterparty, contact person, and phone."
                if any(error in sender_fields for error in errors)
                else "Shipment is missing required Nova Poshta fields."
            )
            return NovaPoshtaTtnResponse(success=False, message=message, errors=errors)
        assert shipment is not None
        if shipment.tracking_number or shipment.nova_poshta_document_number or shipment.nova_poshta_document_ref:
            response = self._existing_result(shipment)
            if not hasattr(self, "operations"):
                response.success = False
                response.blind_retry_blocked = True
                response.errors = ["ttn already exists"]
            return response
        if not self._provider_writes_allowed():
            shipment.nova_poshta_create_state = "WRITES_DISABLED"
            shipment.nova_poshta_last_error_code = "NOVA_POSHTA_PROVIDER_WRITES_DISABLED"
            self.audit_logs.create(
                workspace_id=workspace_id,
                user_id=actor_user_id,
                entity_type="Shipment",
                entity_id=shipment_id,
                action="NOVA_POSHTA_TTN_BLOCKED",
                new_value={
                    "provider": IntegrationProvider.NOVA_POSHTA.value,
                    "safe_error": "PROVIDER_WRITES_DISABLED",
                },
            )
            self.db.commit()
            return NovaPoshtaTtnResponse(
                success=False,
                message="Nova Poshta provider writes are disabled for this environment.",
                operation_state="WRITES_DISABLED",
                blind_retry_blocked=True,
                errors=["NOVA_POSHTA_PROVIDER_WRITES_DISABLED"],
            )

        # Compatibility for isolated legacy unit fakes. Production instances always own the durable repository.
        if not hasattr(self, "operations"):
            return self._legacy_create_ttn(connection, api_key, shipment, actor_user_id)

        base_payload = self._document_payload(shipment, connection.settings or {})
        fingerprint = self._request_fingerprint(base_payload)
        operation = self._get_or_create_operation(
            workspace_id,
            shipment,
            fingerprint,
            actor_user_id,
        )
        if operation.state in {
            NovaPoshtaOperationState.COMPLETED.value,
            NovaPoshtaOperationState.PROVIDER_ACCEPTED.value,
        } and operation.provider_document_number and operation.provider_document_ref:
            return self._bind_provider_result(
                shipment,
                connection,
                operation,
                NovaPoshtaDocumentResult(
                    tracking_number=operation.provider_document_number,
                    document_ref=operation.provider_document_ref,
                    status=operation.provider_status,
                ),
                actor_user_id,
                reused=True,
                reconciled=operation.state != NovaPoshtaOperationState.COMPLETED.value,
            )
        if operation.state in {
            NovaPoshtaOperationState.CALLING_PROVIDER.value,
            NovaPoshtaOperationState.RECONCILIATION_REQUIRED.value,
        }:
            return self._reconcile_operation(
                workspace_id,
                shipment,
                connection,
                operation,
                api_key,
                actor_user_id,
            )

        operation.request_fingerprint = fingerprint
        operation.state = NovaPoshtaOperationState.CALLING_PROVIDER.value
        operation.attempt_count += 1
        operation.provider_called_at = datetime.now(UTC)
        operation.last_error_code = None
        operation.last_error_message = None
        shipment.nova_poshta_create_state = operation.state
        shipment.nova_poshta_manual_reconciliation_required = False
        shipment.nova_poshta_last_error_code = None
        self.db.commit()

        payload = {**base_payload, "Description": operation.provider_marker}
        client = self.settings.client_factory(api_key)
        try:
            result = client.create_internet_document(payload)
        except NovaPoshtaClientError as exc:
            if exc.ambiguous:
                self._mark_reconciliation_required(
                    shipment,
                    operation,
                    actor_user_id,
                    exc.code,
                )
                return self._reconcile_operation(
                    workspace_id,
                    shipment,
                    connection,
                    operation,
                    api_key,
                    actor_user_id,
                )
            operation.state = NovaPoshtaOperationState.FAILED_SAFE.value
            operation.last_error_code = exc.code
            operation.last_error_message = "Provider explicitly rejected the request before document confirmation."
            shipment.nova_poshta_create_state = operation.state
            shipment.nova_poshta_last_error_code = exc.code
            self.audit_logs.create(
                workspace_id=workspace_id,
                user_id=actor_user_id,
                entity_type="Shipment",
                entity_id=shipment.id,
                action="NOVA_POSHTA_ERROR",
                new_value={"provider": IntegrationProvider.NOVA_POSHTA.value, "safe_error": exc.code},
            )
            self.db.commit()
            return NovaPoshtaTtnResponse(
                success=False,
                message="Nova Poshta rejected TTN creation. Check recipient, warehouse and sender settings.",
                operation_state=operation.state,
                errors=[exc.code],
            )
        except Exception:
            self._mark_reconciliation_required(
                shipment,
                operation,
                actor_user_id,
                "NOVA_POSHTA_PROVIDER_RESPONSE_AMBIGUOUS",
            )
            return self._reconcile_operation(
                workspace_id,
                shipment,
                connection,
                operation,
                api_key,
                actor_user_id,
            )

        if not result.tracking_number or not result.document_ref:
            self._mark_reconciliation_required(
                shipment,
                operation,
                actor_user_id,
                "NOVA_POSHTA_TTN_INCOMPLETE",
            )
            return self._reconcile_operation(
                workspace_id,
                shipment,
                connection,
                operation,
                api_key,
                actor_user_id,
            )
        return self._bind_provider_result(
            shipment,
            connection,
            operation,
            result,
            actor_user_id,
        )

    def reconcile_ttn(
        self,
        workspace_id: UUID,
        shipment_id: UUID,
        actor_user_id: UUID | None,
    ) -> NovaPoshtaTtnResponse:
        connection, api_key = self.settings._require_connection(workspace_id)
        shipment = self._get_shipment_for_update(workspace_id, shipment_id)
        if shipment is None:
            raise NovaPoshtaServiceError("Shipment not found")
        if shipment.tracking_number or shipment.nova_poshta_document_number or shipment.nova_poshta_document_ref:
            return self._existing_result(shipment)
        operation = self.operations.get_for_update(workspace_id, shipment_id)
        if operation is None:
            raise NovaPoshtaServiceError("Nova Poshta TTN operation does not exist")
        return self._reconcile_operation(
            workspace_id,
            shipment,
            connection,
            operation,
            api_key,
            actor_user_id,
        )

    def sync_status(
        self,
        workspace_id: UUID,
        shipment_id: UUID,
        actor_user_id: UUID | None,
    ) -> NovaPoshtaStatusResponse:
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
            self.audit_logs.create(
                workspace_id=workspace_id,
                user_id=actor_user_id,
                entity_type="Shipment",
                entity_id=shipment.id,
                action="NOVA_POSHTA_ERROR",
                new_value={
                    "provider": IntegrationProvider.NOVA_POSHTA.value,
                    "safe_error": "STATUS_SYNC_FAILED",
                },
            )
            self.db.commit()
            return NovaPoshtaStatusResponse(
                success=False,
                message="Nova Poshta status sync is unavailable. Please try again later.",
                tracking_number=tracking_number,
                status=shipment.external_status,
                raw_status=shipment.nova_poshta_raw_status,
                normalized_status=shipment.status,
                synced_at=shipment.nova_poshta_synced_at,
            )
        if not status:
            self.audit_logs.create(
                workspace_id=workspace_id,
                user_id=actor_user_id,
                entity_type="Shipment",
                entity_id=shipment.id,
                action="NOVA_POSHTA_STATUS_UNAVAILABLE",
                new_value={"provider": IntegrationProvider.NOVA_POSHTA.value},
            )
            self.db.commit()
            return NovaPoshtaStatusResponse(
                success=False,
                message="Nova Poshta status sync is unavailable. Please try again later.",
                tracking_number=tracking_number,
                status=shipment.external_status,
                raw_status=shipment.nova_poshta_raw_status,
                normalized_status=shipment.status,
                synced_at=shipment.nova_poshta_synced_at,
            )
        normalized_status = self._normalize_provider_status(status)
        previous_normalized_status = shipment.status
        shipment.nova_poshta_raw_status = status
        shipment.external_status = status
        if normalized_status is not None:
            shipment.status = normalized_status.value
        shipment.nova_poshta_synced_at = datetime.now(UTC)
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="Shipment",
            entity_id=shipment.id,
            action="NOVA_POSHTA_STATUS_SYNCED",
            new_value={
                "raw_status": status,
                "normalized_status": normalized_status.value if normalized_status else None,
                "previous_normalized_status": previous_normalized_status,
                "manual_review_required": normalized_status is None,
            },
        )
        self.db.commit()
        return NovaPoshtaStatusResponse(
            success=True,
            message=(
                "Nova Poshta status synced."
                if normalized_status is not None
                else "Nova Poshta returned an unknown status. Previous normalized status was preserved."
            ),
            tracking_number=tracking_number,
            status=status,
            raw_status=status,
            normalized_status=shipment.status,
            manual_review_required=normalized_status is None,
            synced_at=shipment.nova_poshta_synced_at,
        )


    def _get_shipment_for_update(self, workspace_id: UUID, shipment_id: UUID):
        getter = getattr(self.shipments, "get_for_update", None)
        if callable(getter):
            return getter(workspace_id, shipment_id)
        return self.shipments.get(workspace_id, shipment_id)

    def _get_or_create_operation(
        self,
        workspace_id: UUID,
        shipment,
        fingerprint: str,
        actor_user_id: UUID | None,
    ) -> NovaPoshtaOperation:
        operation = self.operations.get_for_update(workspace_id, shipment.id)
        if operation is not None:
            return operation
        operation_id = uuid4()
        operation = NovaPoshtaOperation(
            id=operation_id,
            workspace_id=workspace_id,
            shipment_id=shipment.id,
            operation_type=NovaPoshtaOperationType.CREATE_TTN.value,
            state=NovaPoshtaOperationState.PREPARED.value,
            idempotency_key=f"np-create-ttn:{workspace_id}:{shipment.id}",
            request_fingerprint=fingerprint,
            provider_marker=f"SELLORA:{operation_id}",
            actor_user_id=actor_user_id,
        )
        self.operations.create(operation)
        shipment.nova_poshta_create_state = operation.state
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            existing = self.operations.get_for_update(workspace_id, shipment.id)
            if existing is None:
                raise
            return existing
        return operation

    def _reconcile_operation(
        self,
        workspace_id: UUID,
        shipment,
        connection,
        operation: NovaPoshtaOperation,
        api_key: str,
        actor_user_id: UUID | None,
    ) -> NovaPoshtaTtnResponse:
        client = self.settings.client_factory(api_key)
        finder = getattr(client, "find_internet_document", None)
        result = None
        if callable(finder):
            now = datetime.now(UTC)
            fallback_from = now - timedelta(hours=get_settings().nova_poshta_reconciliation_window_hours)
            date_from = operation.provider_called_at or operation.created_at or fallback_from
            try:
                result = finder(operation.provider_marker, date_from - timedelta(minutes=5), now)
            except NovaPoshtaClientError:
                result = None
        if result is not None:
            operation.reconciled_at = datetime.now(UTC)
            return self._bind_provider_result(
                shipment,
                connection,
                operation,
                result,
                actor_user_id,
                reused=True,
                reconciled=True,
            )
        self._mark_reconciliation_required(
            shipment,
            operation,
            actor_user_id,
            "NOVA_POSHTA_MANUAL_RECONCILIATION_REQUIRED",
            commit=False,
        )
        operation.reconciled_at = datetime.now(UTC)
        self.db.commit()
        return NovaPoshtaTtnResponse(
            success=False,
            message=(
                "Nova Poshta document state is ambiguous. Blind retry is blocked; verify the provider cabinet and reconcile this shipment manually."
            ),
            operation_state=operation.state,
            reconciliation_attempted=True,
            manual_reconciliation_required=True,
            blind_retry_blocked=True,
            errors=["NOVA_POSHTA_MANUAL_RECONCILIATION_REQUIRED"],
        )

    def _bind_provider_result(
        self,
        shipment,
        connection,
        operation: NovaPoshtaOperation,
        result: NovaPoshtaDocumentResult,
        actor_user_id: UUID | None,
        *,
        reused: bool = False,
        reconciled: bool = False,
    ) -> NovaPoshtaTtnResponse:
        now = datetime.now(UTC)
        operation.state = NovaPoshtaOperationState.PROVIDER_ACCEPTED.value
        operation.provider_document_ref = result.document_ref
        operation.provider_document_number = result.tracking_number
        operation.provider_status = result.status
        operation.provider_responded_at = operation.provider_responded_at or now
        shipment.external_provider = IntegrationProvider.NOVA_POSHTA.value
        shipment.external_ref = result.document_ref
        shipment.external_status = result.status
        shipment.nova_poshta_document_ref = result.document_ref
        shipment.nova_poshta_document_number = result.tracking_number
        shipment.tracking_number = result.tracking_number
        shipment.status = ShipmentStatus.CREATED.value
        shipment.nova_poshta_create_state = NovaPoshtaOperationState.COMPLETED.value
        shipment.nova_poshta_manual_reconciliation_required = False
        shipment.nova_poshta_last_error_code = None
        operation.state = NovaPoshtaOperationState.COMPLETED.value
        operation.completed_at = now
        operation.last_error_code = None
        operation.last_error_message = None
        connection.last_sync_at = now
        self.audit_logs.create(
            workspace_id=shipment.workspace_id,
            user_id=actor_user_id,
            entity_type="Shipment",
            entity_id=shipment.id,
            action="NOVA_POSHTA_TTN_RECONCILED" if reconciled else "NOVA_POSHTA_TTN_CREATED",
            new_value={
                "tracking_number": result.tracking_number,
                "document_ref": result.document_ref,
                "reused_existing_result": reused,
            },
        )
        try:
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
            self._best_effort_mark_manual_reconciliation(
                shipment.workspace_id,
                shipment.id,
                actor_user_id,
                "NOVA_POSHTA_LOCAL_PERSISTENCE_FAILED",
            )
            return NovaPoshtaTtnResponse(
                success=False,
                message="Nova Poshta accepted the document, but Sellora could not confirm local persistence. Blind retry is blocked.",
                operation_state=NovaPoshtaOperationState.RECONCILIATION_REQUIRED.value,
                reconciliation_attempted=False,
                manual_reconciliation_required=True,
                blind_retry_blocked=True,
                errors=["NOVA_POSHTA_LOCAL_PERSISTENCE_FAILED"],
            )
        return NovaPoshtaTtnResponse(
            success=True,
            message="Nova Poshta TTN restored from provider reconciliation." if reconciled else "Nova Poshta TTN created.",
            tracking_number=result.tracking_number,
            document_ref=result.document_ref,
            status=result.status,
            operation_state=operation.state,
            reused_existing_result=reused,
            reconciliation_attempted=reconciled,
        )

    def _mark_reconciliation_required(
        self,
        shipment,
        operation: NovaPoshtaOperation,
        actor_user_id: UUID | None,
        error_code: str,
        *,
        commit: bool = True,
    ) -> None:
        operation.state = NovaPoshtaOperationState.RECONCILIATION_REQUIRED.value
        operation.last_error_code = error_code
        operation.last_error_message = "Provider result requires reconciliation before another create attempt."
        shipment.nova_poshta_create_state = operation.state
        shipment.nova_poshta_manual_reconciliation_required = True
        shipment.nova_poshta_last_error_code = error_code
        self.audit_logs.create(
            workspace_id=shipment.workspace_id,
            user_id=actor_user_id,
            entity_type="Shipment",
            entity_id=shipment.id,
            action="NOVA_POSHTA_RECONCILIATION_REQUIRED",
            new_value={
                "provider": IntegrationProvider.NOVA_POSHTA.value,
                "safe_error": error_code,
                "blind_retry_blocked": True,
            },
        )
        if commit:
            self.db.commit()

    def _best_effort_mark_manual_reconciliation(
        self,
        workspace_id: UUID,
        shipment_id: UUID,
        actor_user_id: UUID | None,
        error_code: str,
    ) -> None:
        try:
            shipment = self._get_shipment_for_update(workspace_id, shipment_id)
            operation = self.operations.get_for_update(workspace_id, shipment_id)
            if shipment is None or operation is None:
                return
            self._mark_reconciliation_required(
                shipment,
                operation,
                actor_user_id,
                error_code,
            )
        except Exception:
            self.db.rollback()

    def _existing_result(self, shipment) -> NovaPoshtaTtnResponse:
        return NovaPoshtaTtnResponse(
            success=True,
            message="Nova Poshta TTN already exists for this shipment.",
            tracking_number=shipment.nova_poshta_document_number or shipment.tracking_number,
            document_ref=shipment.nova_poshta_document_ref,
            status=shipment.external_status,
            operation_state=shipment.nova_poshta_create_state or NovaPoshtaOperationState.COMPLETED.value,
            reused_existing_result=True,
        )

    def _provider_writes_allowed(self) -> bool:
        override = getattr(self, "provider_writes_enabled", None)
        if override is not None:
            return override
        if not hasattr(self, "operations"):
            return True
        return get_settings().staging_nova_poshta_allow_writes

    def _legacy_create_ttn(
        self,
        connection,
        api_key: str,
        shipment,
        actor_user_id: UUID | None,
    ) -> NovaPoshtaTtnResponse:
        payload = self._document_payload(shipment, connection.settings or {})
        try:
            result = self.settings.client_factory(api_key).create_internet_document(payload)
        except Exception:
            self.audit_logs.create(
                workspace_id=shipment.workspace_id,
                user_id=actor_user_id,
                entity_type="Shipment",
                entity_id=shipment.id,
                action="NOVA_POSHTA_ERROR",
                new_value={
                    "provider": IntegrationProvider.NOVA_POSHTA.value,
                    "safe_error": "TTN_CREATE_FAILED",
                },
            )
            self.db.commit()
            return NovaPoshtaTtnResponse(
                success=False,
                message="Nova Poshta TTN creation failed. Please check the API key and sender settings, then try again.",
                errors=["NOVA_POSHTA_TTN_FAILED"],
            )
        if not getattr(result, "tracking_number", None) or not getattr(result, "document_ref", None):
            self.audit_logs.create(
                workspace_id=shipment.workspace_id,
                user_id=actor_user_id,
                entity_type="Shipment",
                entity_id=shipment.id,
                action="NOVA_POSHTA_ERROR",
                new_value={
                    "provider": IntegrationProvider.NOVA_POSHTA.value,
                    "safe_error": "TTN_CREATE_INCOMPLETE",
                },
            )
            self.db.commit()
            return NovaPoshtaTtnResponse(
                success=False,
                message="Nova Poshta TTN creation returned an incomplete response. Provider reconciliation is required.",
                manual_reconciliation_required=True,
                blind_retry_blocked=True,
                errors=["NOVA_POSHTA_TTN_INCOMPLETE"],
            )
        shipment.external_provider = IntegrationProvider.NOVA_POSHTA.value
        shipment.external_ref = result.document_ref
        shipment.external_status = result.status
        shipment.nova_poshta_document_ref = result.document_ref
        shipment.nova_poshta_document_number = result.tracking_number
        shipment.tracking_number = result.tracking_number
        shipment.status = ShipmentStatus.CREATED.value
        connection.last_sync_at = datetime.now(UTC)
        self.db.commit()
        return NovaPoshtaTtnResponse(
            success=True,
            message="Nova Poshta TTN created.",
            tracking_number=result.tracking_number,
            document_ref=result.document_ref,
            status=result.status,
        )

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
        for field in (
            "sender_city_ref",
            "sender_warehouse_ref",
            "sender_counterparty_ref",
            "sender_contact_ref",
            "sender_phone",
        ):
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

    def _request_fingerprint(self, payload: dict) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _normalize_provider_status(self, provider_status: str) -> ShipmentStatus | None:
        normalized = provider_status.casefold().strip()
        delivered_markers = ("delivered", "\u043e\u0442\u0440\u0438\u043c\u0430\u043d\u043e", "\u0434\u043e\u0441\u0442\u0430\u0432\u043b\u0435\u043d\u043e", "\u0432\u0440\u0443\u0447\u0435\u043d\u043e")
        returned_markers = ("return", "\u043f\u043e\u0432\u0435\u0440", "\u0432\u0456\u0434\u043c\u043e\u0432\u0430")
        in_transit_markers = ("in transit", "\u0434\u043e\u0440\u043e\u0437", "\u043f\u0440\u044f\u043c\u0443", "\u0432\u0456\u0434\u043f\u0440\u0430\u0432")
        arrived_markers = ("arrived", "\u043f\u0440\u0438\u0431\u0443\u043b", "\u0432\u0456\u0434\u0434\u0456\u043b\u0435\u043d")
        created_markers = ("created", "\u0441\u0442\u0432\u043e\u0440\u0435\u043d\u043e", "\u043d\u043e\u0432\u0430 \u043d\u0430\u043a\u043b\u0430\u0434\u043d\u0430")
        if any(marker in normalized for marker in delivered_markers):
            return ShipmentStatus.DELIVERED
        if any(marker in normalized for marker in returned_markers):
            return ShipmentStatus.RETURNED
        if any(marker in normalized for marker in in_transit_markers):
            return ShipmentStatus.IN_TRANSIT
        if any(marker in normalized for marker in arrived_markers):
            return ShipmentStatus.ARRIVED
        if any(marker in normalized for marker in created_markers):
            return ShipmentStatus.CREATED
        return None
