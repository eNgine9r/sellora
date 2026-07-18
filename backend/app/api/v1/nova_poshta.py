from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.models.role import RoleName
from app.models.user import User
from app.schemas.integration import (
    NovaPoshtaDirectoryItem,
    NovaPoshtaReadinessResponse,
    NovaPoshtaSettingsRequest,
    NovaPoshtaSettingsResponse,
    NovaPoshtaTestConnectionResponse,
    NovaPoshtaWritePermissionRequest,
)
from app.services.nova_poshta_service import (
    NovaPoshtaDirectoryService,
    NovaPoshtaServiceError,
    NovaPoshtaSettingsService,
)

router = APIRouter(prefix="/integrations/nova-poshta", tags=["Nova Poshta"])


def _bad_request(exc: NovaPoshtaServiceError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/settings", response_model=NovaPoshtaSettingsResponse)
def get_settings(
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.OWNER)),
    db: Session = Depends(get_db),
) -> NovaPoshtaSettingsResponse:
    return NovaPoshtaSettingsService(db).get_settings(workspace_id)


@router.get("/readiness", response_model=NovaPoshtaReadinessResponse)
def get_readiness(
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
) -> NovaPoshtaReadinessResponse:
    return NovaPoshtaSettingsService(db).get_readiness(workspace_id)


@router.post("/settings", response_model=NovaPoshtaSettingsResponse)
def save_settings(
    payload: NovaPoshtaSettingsRequest,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.OWNER)),
    db: Session = Depends(get_db),
) -> NovaPoshtaSettingsResponse:
    try:
        return NovaPoshtaSettingsService(db).save_settings(workspace_id, payload, current_user.id)
    except NovaPoshtaServiceError as exc:
        raise _bad_request(exc)


@router.patch("/write-permission", response_model=NovaPoshtaSettingsResponse)
def update_write_permission(
    payload: NovaPoshtaWritePermissionRequest,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.OWNER)),
    db: Session = Depends(get_db),
) -> NovaPoshtaSettingsResponse:
    try:
        return NovaPoshtaSettingsService(db).set_write_permission(workspace_id, payload, current_user.id)
    except NovaPoshtaServiceError as exc:
        raise _bad_request(exc)


@router.post("/test-connection", response_model=NovaPoshtaTestConnectionResponse)
def test_connection(
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.OWNER)),
    db: Session = Depends(get_db),
) -> NovaPoshtaTestConnectionResponse:
    try:
        return NovaPoshtaSettingsService(db).test_connection(workspace_id, current_user.id)
    except NovaPoshtaServiceError as exc:
        raise _bad_request(exc)


@router.delete("/disconnect", response_model=NovaPoshtaSettingsResponse)
def disconnect(
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.OWNER)),
    db: Session = Depends(get_db),
) -> NovaPoshtaSettingsResponse:
    return NovaPoshtaSettingsService(db).disconnect(workspace_id, current_user.id)


@router.get("/cities", response_model=list[NovaPoshtaDirectoryItem])
def search_cities(
    q: str = Query(min_length=2),
    limit: int = Query(default=20, ge=1, le=50),
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
) -> list[NovaPoshtaDirectoryItem]:
    try:
        return NovaPoshtaDirectoryService(db).search_cities(workspace_id, q, limit)
    except NovaPoshtaServiceError as exc:
        raise _bad_request(exc)


@router.get("/warehouses", response_model=list[NovaPoshtaDirectoryItem])
def search_warehouses(
    city_ref: str = Query(min_length=1),
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
) -> list[NovaPoshtaDirectoryItem]:
    try:
        return NovaPoshtaDirectoryService(db).search_warehouses(workspace_id, city_ref, q, limit)
    except NovaPoshtaServiceError as exc:
        raise _bad_request(exc)
