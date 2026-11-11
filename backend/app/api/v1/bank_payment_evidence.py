"""Manual evidence intake: bank integration is NOT connected in this phase."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.models.role import RoleName
from app.models.user import User
from app.schemas.bank_payment_evidence import (
    BankImportRequest, BankImportResponse, BankLedgerResponse, BankPreviewResponse,
)
from app.services.bank_payment_evidence_service import BankPaymentEvidenceService

router = APIRouter(prefix="/finance/bank-evidence", tags=["Finance bank payment evidence"])


@router.get("", response_model=BankLedgerResponse)
def list_evidence(
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return BankPaymentEvidenceService(db).ledger(workspace_id, limit, offset)


@router.post("/preview", response_model=BankPreviewResponse)
def preview_import(
    payload: BankImportRequest,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
):
    return BankPaymentEvidenceService(db).preview(workspace_id, payload)


@router.post("/import", response_model=BankImportResponse)
def import_manual_evidence(
    payload: BankImportRequest,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.OWNER)),
    db: Session = Depends(get_db),
):
    try:
        return BankPaymentEvidenceService(db).import_rows(workspace_id, payload, current_user.id)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Concurrent bank evidence import; preview and retry.") from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
