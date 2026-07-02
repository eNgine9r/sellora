from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.models.role import RoleName
from app.schemas.finance import FinanceSummaryResponse
from app.services.finance_service import FinanceService

router = APIRouter(prefix="/finance", tags=["Finance"])


@router.get("/summary", response_model=FinanceSummaryResponse, dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def finance_summary(
    workspace_id: UUID = Depends(get_workspace_id),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> FinanceSummaryResponse:
    return FinanceService(db).summary(workspace_id, date_from, date_to)
