from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role, require_roles
from app.models.role import RoleName
from app.schemas.analytics import (
    DashboardAnalyticsResponse,
    InventorySummaryResponse,
    ProfitSummaryResponse,
    SalesSummaryResponse,
    SalesTrendItem,
    TopProductItem,
    CustomersSummaryResponse,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _start_date(start_date: date | None = Query(default=None)) -> date | None:
    return start_date


def _end_date(end_date: date | None = Query(default=None)) -> date | None:
    return end_date


@router.get("/sales-summary", response_model=SalesSummaryResponse, dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def sales_summary(
    workspace_id: UUID = Depends(get_workspace_id),
    start_date: date | None = Depends(_start_date),
    end_date: date | None = Depends(_end_date),
    db: Session = Depends(get_db),
) -> SalesSummaryResponse:
    return AnalyticsService(db).sales_summary(workspace_id, start_date, end_date)


@router.get("/profit-summary", response_model=ProfitSummaryResponse, dependencies=[Depends(require_roles(RoleName.OWNER, RoleName.ANALYST))])
def profit_summary(
    workspace_id: UUID = Depends(get_workspace_id),
    start_date: date | None = Depends(_start_date),
    end_date: date | None = Depends(_end_date),
    db: Session = Depends(get_db),
) -> ProfitSummaryResponse:
    return AnalyticsService(db).profit_summary(workspace_id, start_date, end_date)


@router.get("/sales-trend", response_model=list[SalesTrendItem], dependencies=[Depends(require_roles(RoleName.OWNER, RoleName.ANALYST))])
def sales_trend(
    workspace_id: UUID = Depends(get_workspace_id),
    start_date: date | None = Depends(_start_date),
    end_date: date | None = Depends(_end_date),
    db: Session = Depends(get_db),
) -> list[SalesTrendItem]:
    return AnalyticsService(db).sales_trend(workspace_id, start_date, end_date)


@router.get("/top-products", response_model=list[TopProductItem], dependencies=[Depends(require_roles(RoleName.OWNER, RoleName.ANALYST))])
def top_products(
    workspace_id: UUID = Depends(get_workspace_id),
    start_date: date | None = Depends(_start_date),
    end_date: date | None = Depends(_end_date),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[TopProductItem]:
    return AnalyticsService(db).top_products(workspace_id, start_date, end_date, limit)


@router.get("/customers-summary", response_model=CustomersSummaryResponse, dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def customers_summary(
    workspace_id: UUID = Depends(get_workspace_id),
    start_date: date | None = Depends(_start_date),
    end_date: date | None = Depends(_end_date),
    db: Session = Depends(get_db),
) -> CustomersSummaryResponse:
    return AnalyticsService(db).customers_summary(workspace_id, start_date, end_date)


@router.get("/inventory-summary", response_model=InventorySummaryResponse, dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def inventory_summary(
    workspace_id: UUID = Depends(get_workspace_id),
    start_date: date | None = Depends(_start_date),
    end_date: date | None = Depends(_end_date),
    db: Session = Depends(get_db),
) -> InventorySummaryResponse:
    return AnalyticsService(db).inventory_summary(workspace_id)


@router.get("/dashboard", response_model=DashboardAnalyticsResponse, dependencies=[Depends(require_roles(RoleName.OWNER, RoleName.ANALYST))])
def dashboard(
    workspace_id: UUID = Depends(get_workspace_id),
    start_date: date | None = Depends(_start_date),
    end_date: date | None = Depends(_end_date),
    db: Session = Depends(get_db),
) -> DashboardAnalyticsResponse:
    return AnalyticsService(db).dashboard(workspace_id)
