from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.integrations.meta_ads.live_read_only_client import MetaReadOnlyClientError
from app.integrations.meta_ads.read_only_client import FakeMetaAdsReadOnlyClient, MetaAdsReadOnlyClientProtocol
from app.integrations.meta_ads.token_crypto import MetaTokenCryptoError, decrypt_token
from app.models.meta_ad_connection import MetaAdConnection, MetaAdConnectionStatus
from app.repositories.meta_ads_connection_repository import MetaAdsConnectionRepository
from app.schemas.meta_ads_staging_validation import MetaAdsStagingValidationResponse, MetaAdsValidationCheckDTO

NO_WRITE_VALIDATION_WARNING = "This is a no-write preview. No Meta data has been imported into Sellora."


class MetaAdsStagingValidationService:
    """No-write staging validation gate for future live Meta Ads read-only access."""

    def __init__(
        self,
        db: Session,
        *,
        settings: Settings | None = None,
        connection_repository: MetaAdsConnectionRepository | None = None,
        client: MetaAdsReadOnlyClientProtocol | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.connection_repository = connection_repository or MetaAdsConnectionRepository(db)
        self.client = client

    def validate_read_only(self, workspace_id: UUID) -> MetaAdsStagingValidationResponse:
        checks: list[MetaAdsValidationCheckDTO] = []
        if not self.settings.meta_staging_validation_enabled:
            checks.append(self._check("staging_validation_gate", False, "feature_disabled", "Staging validation gate is disabled."))
            return self._not_ready("feature_disabled", "Meta Ads staging validation is not available yet.", checks, mode="disabled")
        checks.append(self._check("staging_validation_gate", True, None, "Staging validation gate is enabled."))

        if not self.settings.meta_connections_enabled:
            checks.append(self._check("connections_gate", False, "feature_disabled", "Meta Ads connection foundation is disabled."))
            return self._not_ready("feature_disabled", "Meta Ads staging validation is not available yet.", checks)
        checks.append(self._check("connections_gate", True, None, "Meta Ads connection foundation is enabled."))

        connection = self.connection_repository.get_current(workspace_id)
        if connection is None:
            checks.append(self._check("connection_record", False, "connection_not_ready", "Workspace has no Meta Ads connection record."))
            return self._not_ready("connection_not_ready", "Meta Ads staging validation is not available yet.", checks)
        checks.append(self._check("connection_record", True, None, "Workspace has a Meta Ads connection record."))

        connection_status = self._connection_status(connection)
        if connection_status != MetaAdConnectionStatus.CONNECTED:
            checks.append(self._check("connection_status", False, "connection_not_ready", "Meta Ads connection is not connected."))
            return self._not_ready("connection_not_ready", "Meta Ads staging validation is not available yet.", checks)
        checks.append(self._check("connection_status", True, None, "Meta Ads connection status is CONNECTED."))

        if not connection.encrypted_access_token:
            checks.append(self._check("encrypted_token", False, "token_missing", "Encrypted Meta token is not stored for this connection."))
            return self._not_ready("token_missing", "Meta Ads staging validation is not available yet.", checks)
        checks.append(self._check("encrypted_token", True, None, "Encrypted Meta token exists server-side."))

        if not self.settings.meta_token_storage_enabled or not self.settings.meta_token_encryption_key:
            checks.append(self._check("token_storage_gate", False, "config_missing", "Meta token storage/decryption is not configured."))
            return self._not_ready("config_missing", "Meta Ads staging validation is not available yet.", checks)
        checks.append(self._check("token_storage_gate", True, None, "Meta token storage/decryption is configured."))

        try:
            decrypt_token(connection.encrypted_access_token, self.settings.meta_token_encryption_key)
        except MetaTokenCryptoError:
            checks.append(self._check("token_decryption", False, "token_invalid", "Encrypted Meta token could not be decrypted safely."))
            return self._not_ready("token_invalid", "Meta Ads staging validation is not available yet.", checks)
        checks.append(self._check("token_decryption", True, None, "Encrypted Meta token can be decrypted server-side."))

        if self.settings.meta_sync_enabled:
            checks.append(self._check("production_sync_disabled", False, "sync_must_remain_disabled", "Meta Ads production sync must remain disabled for staging validation."))
            return self._not_ready("sync_must_remain_disabled", "Meta Ads staging validation is not available yet.", checks)
        checks.append(self._check("production_sync_disabled", True, None, "Meta Ads production sync is disabled."))

        client = self.client or FakeMetaAdsReadOnlyClient()
        mode = "fake" if isinstance(client, FakeMetaAdsReadOnlyClient) else "live_read_only"
        try:
            accounts = client.list_ad_accounts()
            account_id = accounts[0].external_account_id if accounts else ""
            campaigns = client.list_campaigns(account_id) if account_id else []
            insights = client.get_campaign_insights_preview(account_id, date.today(), date.today()) if account_id else []
        except MetaReadOnlyClientError as exc:
            checks.append(self._check("read_only_client", False, exc.code.value.lower(), str(exc)))
            return MetaAdsStagingValidationResponse(
                ready=False,
                reason=exc.code.value.lower(),
                message=str(exc),
                mode=mode,
                checks=checks,
                warnings=[NO_WRITE_VALIDATION_WARNING],
                errors=[exc.code.value],
                sync_active=False,
                writes_performed=False,
            )
        checks.append(self._check("read_only_client", True, None, "Read-only preview client returned safe preview data."))
        return MetaAdsStagingValidationResponse(
            ready=True,
            reason=None,
            message="Meta Ads staging read-only validation preview is available.",
            mode=mode,
            checks=checks,
            warnings=[NO_WRITE_VALIDATION_WARNING],
            account_preview_count=len(accounts),
            campaign_preview_count=len(campaigns),
            insights_preview_sample_count=len(insights),
            sync_active=False,
            writes_performed=False,
        )

    def _connection_status(self, connection: MetaAdConnection) -> MetaAdConnectionStatus:
        return MetaAdConnectionStatus(connection.connection_status)

    def _not_ready(self, reason: str, message: str, checks: list[MetaAdsValidationCheckDTO], *, mode: str = "not_ready") -> MetaAdsStagingValidationResponse:
        return MetaAdsStagingValidationResponse(
            ready=False,
            reason=reason,
            message=message,
            mode=mode,
            checks=checks,
            warnings=[NO_WRITE_VALIDATION_WARNING],
            sync_active=False,
            writes_performed=False,
        )

    def _check(self, name: str, passed: bool, reason: str | None, message: str) -> MetaAdsValidationCheckDTO:
        return MetaAdsValidationCheckDTO(name=name, passed=passed, reason=reason, message=message)
