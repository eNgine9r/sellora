from __future__ import annotations

from dataclasses import asdict
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.integrations.meta_ads.audit_stub import build_meta_ads_mock_audit_event
from app.integrations.meta_ads.oauth_mock import MetaAdsMockOAuthError, MetaAdsMockOAuthPermissionError, MetaAdsMockOAuthService
from app.integrations.meta_ads.oauth_state import MetaOAuthStateError
from app.integrations.meta_ads.schemas import MetaOAuthMockCallbackInputDTO
from app.models.role import RoleName
from app.models.user import User
from app.schemas.meta_ads_mock import (
    MetaAdsMockAuditEventResponse,
    MetaAdsMockCallbackRequest,
    MetaAdsMockCallbackResponse,
    MetaAdsMockDisconnectResponse,
    MetaAdsMockIssueResponse,
    MetaAdsMockStartResponse,
    MetaAdsMockStatusResponse,
    MetaTokenSafetyResponse,
)

router = APIRouter(prefix="/integrations/meta-ads/mock", tags=["Meta Ads Mock"])
require_meta_ads_mock_status_view = require_min_role(RoleName.ANALYST)
require_meta_ads_mock_owner = require_min_role(RoleName.OWNER)


def _service() -> MetaAdsMockOAuthService:
    return MetaAdsMockOAuthService()


def _ensure_mock_api_enabled(settings: Settings) -> None:
    if not settings.meta_ads_mock_oauth_api_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Meta Ads mock OAuth API is disabled.")


def _issues(issues: list[object]) -> list[MetaAdsMockIssueResponse]:
    return [MetaAdsMockIssueResponse(**asdict(issue)) for issue in issues]


def _audit_response(event: object) -> MetaAdsMockAuditEventResponse:
    return MetaAdsMockAuditEventResponse(**asdict(event))


def _role_for_service(_: User, role: RoleName = RoleName.OWNER) -> RoleName:
    # Route-level dependencies already enforce the concrete role. Passing an
    # explicit role keeps the existing service-level OWNER contract active.
    return role


@router.get("/status", response_model=MetaAdsMockStatusResponse)
def get_meta_ads_mock_status(
    workspace_id=Depends(get_workspace_id),
    current_user: User = Depends(require_meta_ads_mock_status_view),
    settings: Settings = Depends(get_settings),
    service: MetaAdsMockOAuthService = Depends(_service),
) -> MetaAdsMockStatusResponse:
    result = service.status(workspace_id)
    audit_event = build_meta_ads_mock_audit_event(
        event="meta_ads_mock_status_viewed",
        workspace_id=workspace_id,
        user_id=current_user.id,
        outcome="viewed_disabled" if not settings.meta_ads_mock_oauth_api_enabled else "viewed_enabled",
        payload={"mock_api_enabled": settings.meta_ads_mock_oauth_api_enabled, "authorization_url_returned": False},
    )
    return MetaAdsMockStatusResponse(
        status=result.status,
        provider=result.provider,
        workspace_id=result.workspace_id,
        connection_mode=result.connection_mode,
        mock_api_enabled=settings.meta_ads_mock_oauth_api_enabled,
        connected=result.connected,
        requires_live_setup=result.requires_live_setup,
        token_stored=result.token_stored,
        live_api_enabled=result.live_api_enabled,
        message=result.message,
        issues=_issues(result.issues),
        audit_event=_audit_response(audit_event),
    )


@router.post("/oauth/start", response_model=MetaAdsMockStartResponse)
def start_meta_ads_mock_oauth(
    workspace_id=Depends(get_workspace_id),
    current_user: User = Depends(require_meta_ads_mock_owner),
    settings: Settings = Depends(get_settings),
    service: MetaAdsMockOAuthService = Depends(_service),
) -> MetaAdsMockStartResponse:
    _ensure_mock_api_enabled(settings)
    try:
        result = service.start_mock_connect(workspace_id=workspace_id, user_id=current_user.id, role=_role_for_service(current_user))
    except MetaAdsMockOAuthPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    host = urlparse(result.authorization_url).hostname
    audit_event = build_meta_ads_mock_audit_event(
        event="meta_ads_mock_connect_started",
        workspace_id=workspace_id,
        user_id=current_user.id,
        outcome="mock_authorization_url_generated",
        payload={"mock_url_host": host, "token_returned": False, "db_write": False},
    )
    return MetaAdsMockStartResponse(
        status=result.status,
        provider=result.provider,
        workspace_id=result.workspace_id,
        connection_mode=result.connection_mode,
        authorization_url=result.authorization_url,
        state_expires_at=result.state_expires_at,
        connected=result.connected,
        requires_live_setup=result.requires_live_setup,
        token_stored=result.token_stored,
        live_api_enabled=result.live_api_enabled,
        message=result.message,
        issues=_issues(result.issues),
        audit_event=_audit_response(audit_event),
    )


@router.post("/oauth/callback", response_model=MetaAdsMockCallbackResponse)
def validate_meta_ads_mock_oauth_callback(
    payload: MetaAdsMockCallbackRequest,
    workspace_id=Depends(get_workspace_id),
    current_user: User = Depends(require_meta_ads_mock_owner),
    settings: Settings = Depends(get_settings),
    service: MetaAdsMockOAuthService = Depends(_service),
) -> MetaAdsMockCallbackResponse:
    _ensure_mock_api_enabled(settings)
    try:
        result = service.simulate_callback(
            workspace_id=workspace_id,
            user_id=current_user.id,
            role=_role_for_service(current_user),
            payload=MetaOAuthMockCallbackInputDTO(state=payload.state, code=payload.code),
        )
    except MetaAdsMockOAuthPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (MetaAdsMockOAuthError, MetaOAuthStateError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    audit_event = build_meta_ads_mock_audit_event(
        event="meta_ads_mock_connect_callback_validated",
        workspace_id=workspace_id,
        user_id=current_user.id,
        outcome="validated_without_storage",
        payload={"token_stored": False, "live_api_enabled": False, "db_write": False},
    )
    return MetaAdsMockCallbackResponse(
        status=result.status,
        provider=result.provider,
        workspace_id=result.workspace_id,
        connection_mode=result.connection_mode,
        connected=result.connected,
        requires_live_setup=result.requires_live_setup,
        token_stored=result.token_stored,
        live_api_enabled=result.live_api_enabled,
        message=result.message,
        token_safety=MetaTokenSafetyResponse(**asdict(result.token_safety)) if result.token_safety else None,
        issues=_issues(result.issues),
        audit_event=_audit_response(audit_event),
    )


@router.post("/disconnect", response_model=MetaAdsMockDisconnectResponse)
def disconnect_meta_ads_mock(
    workspace_id=Depends(get_workspace_id),
    current_user: User = Depends(require_meta_ads_mock_owner),
    settings: Settings = Depends(get_settings),
    service: MetaAdsMockOAuthService = Depends(_service),
) -> MetaAdsMockDisconnectResponse:
    _ensure_mock_api_enabled(settings)
    try:
        result = service.simulate_disconnect(workspace_id=workspace_id, role=_role_for_service(current_user))
    except MetaAdsMockOAuthPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    audit_event = build_meta_ads_mock_audit_event(
        event="meta_ads_mock_disconnected",
        workspace_id=workspace_id,
        user_id=current_user.id,
        outcome="mock_disconnect_acknowledged",
        payload={"token_revoked": False, "connection_deleted": False, "db_write": False},
    )
    return MetaAdsMockDisconnectResponse(
        status=result.status,
        provider=result.provider,
        workspace_id=result.workspace_id,
        connection_mode=result.connection_mode,
        connected=result.connected,
        token_stored=result.token_stored,
        live_api_enabled=result.live_api_enabled,
        message=result.message,
        issues=_issues(result.issues),
        audit_event=_audit_response(audit_event),
    )
