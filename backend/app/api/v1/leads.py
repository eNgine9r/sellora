from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.models.lead import LeadStatus
from app.models.role import RoleName
from app.models.user import User
from app.schemas.customer import CustomerResponse
from app.schemas.lead import LeadAssignRequest, LeadCreate, LeadMarkLostRequest, LeadResponse, LeadUpdate
from app.services.lead_service import LeadService, LeadServiceError

router = APIRouter(prefix="/leads", tags=["Leads"])


def _bad_request(exc: LeadServiceError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("", response_model=list[LeadResponse], dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def list_leads(
    workspace_id: UUID = Depends(get_workspace_id),
    search: str | None = Query(default=None),
    lead_status: LeadStatus | None = Query(default=None, alias="status"),
    lead_source_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[LeadResponse]:
    return LeadService(db).list(workspace_id, search, lead_status, lead_source_id)


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead(
    payload: LeadCreate,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
) -> LeadResponse:
    try:
        return LeadService(db).create(workspace_id, payload, current_user.id)
    except LeadServiceError as exc:
        raise _bad_request(exc)


@router.put("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: UUID,
    payload: LeadUpdate,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
) -> LeadResponse:
    try:
        lead = LeadService(db).update(workspace_id, lead_id, payload, current_user.id)
    except LeadServiceError as exc:
        raise _bad_request(exc)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(
    lead_id: UUID,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
) -> Response:
    deleted = LeadService(db).delete(workspace_id, lead_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{lead_id}/assign", response_model=LeadResponse)
def assign_lead(
    lead_id: UUID,
    payload: LeadAssignRequest,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
) -> LeadResponse:
    try:
        lead = LeadService(db).assign(workspace_id, lead_id, payload, current_user.id)
    except LeadServiceError as exc:
        raise _bad_request(exc)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead


@router.post("/{lead_id}/convert", response_model=CustomerResponse)
def convert_lead(
    lead_id: UUID,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
) -> CustomerResponse:
    try:
        customer = LeadService(db).convert_lead_to_customer(workspace_id, lead_id, current_user.id)
    except LeadServiceError as exc:
        raise _bad_request(exc)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return customer


@router.post("/{lead_id}/mark-lost", response_model=LeadResponse)
def mark_lead_lost(
    lead_id: UUID,
    payload: LeadMarkLostRequest,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
) -> LeadResponse:
    lead = LeadService(db).mark_lost(workspace_id, lead_id, payload, current_user.id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead
