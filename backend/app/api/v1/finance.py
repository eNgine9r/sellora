from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.models.finance_adjustment import FinanceAdjustmentCategory, FinanceAdjustmentType
from app.models.role import RoleName
from app.models.user import User
from app.schemas.finance import (
    FinanceAdjustmentCreate,
    FinanceAdjustmentListResponse,
    FinanceAdjustmentResponse,
    FinanceAdjustmentUpdate,
    FinanceBreakdownResponse,
    FinancePeriodComparisonResponse,
    FinanceSummaryResponse,
)
from app.services.finance_service import FinanceService, FinanceServiceError

router = APIRouter(prefix="/finance", tags=["Finance"])


def _bad_request(exc: FinanceServiceError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/summary", response_model=FinanceSummaryResponse, dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def finance_summary(
    workspace_id: UUID = Depends(get_workspace_id),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> FinanceSummaryResponse:
    return FinanceService(db).summary(workspace_id, date_from, date_to)


@router.get("/breakdown", response_model=FinanceBreakdownResponse, dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def finance_breakdown(
    workspace_id: UUID = Depends(get_workspace_id),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> FinanceBreakdownResponse:
    return FinanceService(db).breakdown(workspace_id, date_from, date_to)


@router.get("/trends", response_model=FinancePeriodComparisonResponse, dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def finance_trends(
    workspace_id: UUID = Depends(get_workspace_id),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> FinancePeriodComparisonResponse:
    return FinanceService(db).trends(workspace_id, date_from, date_to)


@router.get("/adjustments", response_model=FinanceAdjustmentListResponse)
def list_finance_adjustments(
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.ANALYST)),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    type: FinanceAdjustmentType | None = Query(default=None),
    category: FinanceAdjustmentCategory | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> FinanceAdjustmentListResponse:
    return FinanceService(db).list_adjustments(workspace_id, date_from, date_to, type, category, limit, offset)


@router.post("/adjustments", response_model=FinanceAdjustmentResponse, status_code=status.HTTP_201_CREATED)
def create_finance_adjustment(
    payload: FinanceAdjustmentCreate,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
) -> FinanceAdjustmentResponse:
    try:
        return FinanceService(db).create_adjustment(workspace_id, payload, current_user.id)
    except FinanceServiceError as exc:
        raise _bad_request(exc)


@router.patch("/adjustments/{adjustment_id}", response_model=FinanceAdjustmentResponse)
def update_finance_adjustment(
    adjustment_id: UUID,
    payload: FinanceAdjustmentUpdate,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
) -> FinanceAdjustmentResponse:
    try:
        return FinanceService(db).update_adjustment(workspace_id, adjustment_id, payload)
    except FinanceServiceError as exc:
        raise _bad_request(exc)


@router.delete("/adjustments/{adjustment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_finance_adjustment(
    adjustment_id: UUID,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
) -> None:
    try:
        FinanceService(db).delete_adjustment(workspace_id, adjustment_id, current_user.id)
    except FinanceServiceError as exc:
        raise _bad_request(exc)
