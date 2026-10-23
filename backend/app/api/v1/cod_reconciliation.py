from datetime import date, datetime, time, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.models.role import RoleName
from app.models.user import User
from app.schemas.cod_reconciliation import CodImportRequest, CodImportResponse, CodLedgerResponse, CodPreviewResponse
from app.services.cod_reconciliation_service import CodReconciliationService

router = APIRouter(prefix="/finance/cod-reconciliation", tags=["Finance COD reconciliation"])


@router.get("", response_model=CodLedgerResponse)
def list_cod_evidence(
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.ANALYST)),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="Invalid date range")
    start = datetime.combine(date_from, time.min, timezone.utc) if date_from else None
    end = datetime.combine(date_to, time.max, timezone.utc) if date_to else None
    return CodReconciliationService(db).ledger(workspace_id, start, end)


@router.post("/preview", response_model=CodPreviewResponse)
def preview_cod_import(
    payload: CodImportRequest,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
):
    return CodReconciliationService(db).preview(workspace_id, payload)


@router.post("/import", response_model=CodImportResponse)
def import_cod_evidence(
    payload: CodImportRequest,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
):
    try:
        return CodReconciliationService(db).import_rows(workspace_id, payload, current_user.id)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Concurrent or duplicate payment import. Preview and retry.") from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
