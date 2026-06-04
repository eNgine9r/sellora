from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.rbac import get_user_role_for_workspace, get_workspace_id, require_min_role, require_roles
from app.models.role import RoleName
from app.models.user import User
from app.schemas.advertising import (
    AdCampaignCreate,
    AdCampaignResponse,
    AdCampaignUpdate,
    AdMetricCreate,
    AdMetricResponse,
    AdMetricUpdate,
    AdvertisingSummaryResponse,
    AdvertisingTrendPoint,
    CampaignPerformanceResponse,
)
from app.services.advertising_service import AdCampaignService, AdMetricService, AdvertisingAnalyticsService, AdvertisingServiceError

router = APIRouter(prefix="/advertising", tags=["Advertising"])


def _bad_request(exc: AdvertisingServiceError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _include_sensitive(user: User, workspace_id: UUID) -> bool:
    return get_user_role_for_workspace(user, workspace_id) in {RoleName.OWNER, RoleName.ANALYST}


@router.get("/campaigns", response_model=list[AdCampaignResponse])
def list_campaigns(workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.ANALYST)), db: Session = Depends(get_db)) -> list[AdCampaignResponse]:
    return AdCampaignService(db).list(workspace_id)


@router.post("/campaigns", response_model=AdCampaignResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(payload: AdCampaignCreate, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_roles(RoleName.OWNER)), db: Session = Depends(get_db)) -> AdCampaignResponse:
    try:
        return AdCampaignService(db).create(workspace_id, payload, current_user.id)
    except AdvertisingServiceError as exc:
        raise _bad_request(exc)


@router.get("/campaigns/{campaign_id}", response_model=AdCampaignResponse)
def get_campaign(campaign_id: UUID, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.ANALYST)), db: Session = Depends(get_db)) -> AdCampaignResponse:
    try:
        return AdCampaignService(db).get(workspace_id, campaign_id)
    except AdvertisingServiceError as exc:
        raise _bad_request(exc)


@router.put("/campaigns/{campaign_id}", response_model=AdCampaignResponse)
def update_campaign(campaign_id: UUID, payload: AdCampaignUpdate, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_roles(RoleName.OWNER)), db: Session = Depends(get_db)) -> AdCampaignResponse:
    try:
        return AdCampaignService(db).update(workspace_id, campaign_id, payload, current_user.id)
    except AdvertisingServiceError as exc:
        raise _bad_request(exc)


@router.delete("/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(campaign_id: UUID, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_roles(RoleName.OWNER)), db: Session = Depends(get_db)) -> None:
    try:
        AdCampaignService(db).delete(workspace_id, campaign_id, current_user.id)
    except AdvertisingServiceError as exc:
        raise _bad_request(exc)


@router.get("/metrics", response_model=list[AdMetricResponse])
def list_metrics(workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.ANALYST)), db: Session = Depends(get_db)) -> list[AdMetricResponse]:
    return AdMetricService(db).list(workspace_id, _include_sensitive(current_user, workspace_id))


@router.post("/metrics", response_model=AdMetricResponse, status_code=status.HTTP_201_CREATED)
def create_metric(payload: AdMetricCreate, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_roles(RoleName.OWNER)), db: Session = Depends(get_db)) -> AdMetricResponse:
    try:
        return AdMetricService(db).create(workspace_id, payload, current_user.id)
    except AdvertisingServiceError as exc:
        raise _bad_request(exc)


@router.put("/metrics/{metric_id}", response_model=AdMetricResponse)
def update_metric(metric_id: UUID, payload: AdMetricUpdate, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_roles(RoleName.OWNER)), db: Session = Depends(get_db)) -> AdMetricResponse:
    try:
        return AdMetricService(db).update(workspace_id, metric_id, payload, current_user.id, _include_sensitive(current_user, workspace_id))
    except AdvertisingServiceError as exc:
        raise _bad_request(exc)


@router.get("/campaigns/{campaign_id}/metrics", response_model=list[AdMetricResponse])
def list_campaign_metrics(campaign_id: UUID, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.ANALYST)), db: Session = Depends(get_db)) -> list[AdMetricResponse]:
    try:
        return AdMetricService(db).list_for_campaign(workspace_id, campaign_id, _include_sensitive(current_user, workspace_id))
    except AdvertisingServiceError as exc:
        raise _bad_request(exc)


@router.delete("/metrics/{metric_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_metric(metric_id: UUID, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_roles(RoleName.OWNER)), db: Session = Depends(get_db)) -> None:
    try:
        AdMetricService(db).delete(workspace_id, metric_id, current_user.id)
    except AdvertisingServiceError as exc:
        raise _bad_request(exc)


@router.get("/summary", response_model=AdvertisingSummaryResponse)
def advertising_summary(start_date: date | None = None, end_date: date | None = None, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.ANALYST)), db: Session = Depends(get_db)) -> AdvertisingSummaryResponse:
    return AdvertisingAnalyticsService(db).summary(workspace_id, start_date, end_date, _include_sensitive(current_user, workspace_id))


@router.get("/campaign-performance", response_model=list[CampaignPerformanceResponse])
def campaign_performance(start_date: date | None = None, end_date: date | None = None, limit: int = Query(default=10, ge=1, le=100), workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.ANALYST)), db: Session = Depends(get_db)) -> list[CampaignPerformanceResponse]:
    return AdvertisingAnalyticsService(db).campaign_performance(workspace_id, start_date, end_date, limit, _include_sensitive(current_user, workspace_id))


@router.get("/trend", response_model=list[AdvertisingTrendPoint])
def advertising_trend(start_date: date | None = None, end_date: date | None = None, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.ANALYST)), db: Session = Depends(get_db)) -> list[AdvertisingTrendPoint]:
    return AdvertisingAnalyticsService(db).trend(workspace_id, start_date, end_date, _include_sensitive(current_user, workspace_id))
