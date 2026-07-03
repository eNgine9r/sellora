from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.models.role import RoleName
from app.models.user import User
from app.schemas.meta_ads_connection import (
    MetaAdsConnectionStatusResponse,
    MetaAdsDisconnectResponse,
    MetaAdsOAuthCallbackRequest,
    MetaAdsOAuthCallbackResponse,
    MetaAdsOAuthStartResponse,
)
from app.services.meta_ads_connection_service import MetaAdsConnectionService, MetaAdsConnectionServiceError

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
