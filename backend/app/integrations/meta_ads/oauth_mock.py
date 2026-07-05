from __future__ import annotations

from datetime import datetime
from urllib.parse import urlencode
from uuid import UUID

from app.integrations.meta_ads.oauth_state import generate_mock_oauth_state, validate_mock_oauth_state
from app.integrations.meta_ads.schemas import (
    MetaConnectionStatusDTO,
    MetaDisconnectMockResultDTO,
    MetaOAuthMockCallbackInputDTO,
    MetaOAuthMockCallbackResultDTO,
    MetaOAuthMockStartResultDTO,
    MetaSyncIssueDTO,
    MetaTokenSafetyCheckDTO,
)
from app.integrations.meta_ads.token_safety import assert_no_raw_token_in_response, mask_token, safe_token_fingerprint
from app.models.role import RoleName

MOCK_META_OAUTH_AUTHORIZE_URL = "https://mock.meta.local/oauth/authorize"
PROVIDER = "meta_ads"
CONNECTION_MODE = "mock"


class MetaAdsMockOAuthPermissionError(PermissionError):
    """Raised when a non-OWNER role attempts mock connect/disconnect."""


class MetaAdsMockOAuthError(ValueError):
    """Raised when mock OAuth callback input is invalid."""


class MetaAdsMockOAuthService:
    """Service-level mock OAuth contract for future Meta Ads integration.

    This service intentionally has no database dependency, performs no writes,
    does not expose production routes, does not call live Meta APIs, and never
    stores token-like values. The mock authorization URL uses a non-live domain.
    """

    def start_mock_connect(self, workspace_id: UUID, user_id: UUID, role: RoleName, now: datetime | None = None) -> MetaOAuthMockStartResultDTO:
        self._require_owner(role)
        state, payload = generate_mock_oauth_state(workspace_id=workspace_id, user_id=user_id, now=now)
        authorization_url = f"{MOCK_META_OAUTH_AUTHORIZE_URL}?{urlencode({'state': state, 'mode': CONNECTION_MODE, 'provider': PROVIDER})}"
        result = MetaOAuthMockStartResultDTO(
            status="MOCK_OAUTH_READY",
            provider=PROVIDER,
            workspace_id=workspace_id,
            connection_mode=CONNECTION_MODE,
            authorization_url=authorization_url,
            state_expires_at=payload.expires_at,
            message="Mock-only Meta Ads authorization URL generated. No live Meta account is connected.",
            issues=[MetaSyncIssueDTO(code="mock_only", message="This is a mock OAuth contract. Live Meta OAuth is not active.")],
        )
        assert_no_raw_token_in_response(result)
        return result

    def simulate_callback(self, workspace_id: UUID, user_id: UUID, role: RoleName, payload: MetaOAuthMockCallbackInputDTO, now: datetime | None = None) -> MetaOAuthMockCallbackResultDTO:
        self._require_owner(role)
        validate_mock_oauth_state(payload.state, workspace_id=workspace_id, user_id=user_id, now=now)
        if not payload.code.startswith("mock_code_"):
            raise MetaAdsMockOAuthError("Invalid mock OAuth callback code.")
        synthetic_token = self._synthetic_token_for_callback(payload.code)
        safety = MetaTokenSafetyCheckDTO(
            status="REDACTED",
            masked_value=mask_token(synthetic_token),
            fingerprint=safe_token_fingerprint(synthetic_token),
            token_stored=False,
            raw_token_returned=False,
            message="Synthetic callback token was redacted and discarded; no token storage occurred.",
        )
        result = MetaOAuthMockCallbackResultDTO(
            status="MOCK_CALLBACK_VALIDATED",
            provider=PROVIDER,
            workspace_id=workspace_id,
            connection_mode=CONNECTION_MODE,
            message="Mock callback validated. Live OAuth, token storage, and Meta API calls remain inactive.",
            token_safety=safety,
            issues=[MetaSyncIssueDTO(code="no_token_storage", message="Synthetic token-like value was masked and discarded.")],
        )
        assert_no_raw_token_in_response(result)
        return result

    def simulate_disconnect(self, workspace_id: UUID, role: RoleName) -> MetaDisconnectMockResultDTO:
        self._require_owner(role)
        result = MetaDisconnectMockResultDTO(
            status="MOCK_DISCONNECTED",
            provider=PROVIDER,
            workspace_id=workspace_id,
            message="Mock disconnect acknowledged. No live Meta connection or token storage existed.",
        )
        assert_no_raw_token_in_response(result)
        return result

    def status(self, workspace_id: UUID) -> MetaConnectionStatusDTO:
        return MetaConnectionStatusDTO(
            status="NOT_ACTIVE",
            provider=PROVIDER,
            workspace_id=workspace_id,
            message="Meta Ads API is not active. Manual entry and CSV import remain the active advertising source.",
        )

    def _require_owner(self, role: RoleName) -> None:
        if role != RoleName.OWNER:
            raise MetaAdsMockOAuthPermissionError("Only OWNER can start or change the mock Meta Ads connection flow.")

    def _synthetic_token_for_callback(self, code: str) -> str:
        return "mock_token_" + safe_token_fingerprint(code) + "abcd"
