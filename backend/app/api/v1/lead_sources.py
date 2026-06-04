from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.models.role import RoleName
from app.models.user import User
from app.schemas.lead_source import LeadSourceCreate, LeadSourceResponse, LeadSourceUpdate
from app.services.lead_source_service import LeadSourceService

router = APIRouter(prefix="/lead-sources", tags=["Lead Sources"])


@router.get("", response_model=list[LeadSourceResponse], dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def list_lead_sources(
    workspace_id: UUID = Depends(get_workspace_id),
    search: str | None = Query(default=None),
    include_inactive: bool = False,
    db: Session = Depends(get_db),
) -> list[LeadSourceResponse]:
    return LeadSourceService(db).list(workspace_id, search, include_inactive)


@router.post("", response_model=LeadSourceResponse, status_code=status.HTTP_201_CREATED)
def create_lead_source(
    payload: LeadSourceCreate,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
) -> LeadSourceResponse:
    return LeadSourceService(db).create(workspace_id, payload, current_user.id)


@router.put("/{lead_source_id}", response_model=LeadSourceResponse)
def update_lead_source(
    lead_source_id: UUID,
    payload: LeadSourceUpdate,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
) -> LeadSourceResponse:
    lead_source = LeadSourceService(db).update(workspace_id, lead_source_id, payload, current_user.id)
    if lead_source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead source not found")
    return lead_source


@router.delete("/{lead_source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead_source(
    lead_source_id: UUID,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
) -> Response:
    deleted = LeadSourceService(db).delete(workspace_id, lead_source_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead source not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
