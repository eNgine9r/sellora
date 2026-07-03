from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.models.role import RoleName
from app.models.user import User
from app.schemas.meta_ads_read_only import MetaAdAccountDiscoveryResponse, MetaCampaignDiscoveryResponse, MetaInsightsPreviewResponse
from app.schemas.meta_ads_connection import (
    MetaAdsConnectionStatusResponse,
    MetaAdsDisconnectResponse,
    MetaAdsOAuthCallbackRequest,
    MetaAdsOAuthCallbackResponse,
    MetaAdsOAuthStartResponse,
)
from app.services.meta_ads_connection_service import MetaAdsConnectionService, MetaAdsConnectionServiceError
from app.services.meta_ads_sync_preview_service import MetaAdsSyncPreviewService

router = APIRouter(prefix="/integrations/meta-ads", tags=["Meta Ads"])


def _service_error(exc: MetaAdsConnectionServiceError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message})


@router.get("/status", response_model=MetaAdsConnectionStatusResponse)
def get_meta_ads_status(
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.ANALYST)),
    db: Session = Depends(get_db),
) -> MetaAdsConnectionStatusResponse:
    return MetaAdsConnectionService(db).get_status(workspace_id, current_user.id)


@router.post("/oauth/start", response_model=MetaAdsOAuthStartResponse)
def start_meta_ads_oauth(
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.OWNER)),
    db: Session = Depends(get_db),
) -> MetaAdsOAuthStartResponse:
    try:
        return MetaAdsConnectionService(db).start_oauth(workspace_id, current_user.id)
    except MetaAdsConnectionServiceError as exc:
        raise _service_error(exc)


@router.post("/oauth/callback", response_model=MetaAdsOAuthCallbackResponse)
def complete_meta_ads_oauth_callback(
    payload: MetaAdsOAuthCallbackRequest,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.OWNER)),
    db: Session = Depends(get_db),
) -> MetaAdsOAuthCallbackResponse:
    try:
        return MetaAdsConnectionService(db).complete_callback(workspace_id, current_user.id, state=payload.state, code=payload.code)
    except (MetaAdsConnectionServiceError, ValueError) as exc:
        if isinstance(exc, MetaAdsConnectionServiceError):
            raise _service_error(exc)
        raise HTTPException(status_code=400, detail={"code": "invalid_state", "message": "Invalid Meta OAuth state."})


@router.get("/discovery/accounts", response_model=MetaAdAccountDiscoveryResponse)
def discover_meta_ads_accounts(
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.ANALYST)),
    db: Session = Depends(get_db),
) -> MetaAdAccountDiscoveryResponse:
    return MetaAdsSyncPreviewService(db).discover_accounts(workspace_id)


@router.get("/discovery/campaigns", response_model=MetaCampaignDiscoveryResponse)
def discover_meta_ads_campaigns(
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.ANALYST)),
    account_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> MetaCampaignDiscoveryResponse:
    return MetaAdsSyncPreviewService(db).discover_campaigns(workspace_id, account_id=account_id)


@router.get("/sync/preview", response_model=MetaInsightsPreviewResponse)
def preview_meta_ads_sync(
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.ANALYST)),
    date_from: date = Query(...),
    date_to: date = Query(...),
    account_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> MetaInsightsPreviewResponse:
    return MetaAdsSyncPreviewService(db).preview_insights(workspace_id, date_from=date_from, date_to=date_to, account_id=account_id)


@router.post("/disconnect", response_model=MetaAdsDisconnectResponse)
def disconnect_meta_ads(
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.OWNER)),
    db: Session = Depends(get_db),
) -> MetaAdsDisconnectResponse:
    try:
        return MetaAdsConnectionService(db).disconnect(workspace_id, current_user.id)
    except MetaAdsConnectionServiceError as exc:
        raise _service_error(exc)
