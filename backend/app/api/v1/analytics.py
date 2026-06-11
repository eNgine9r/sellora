from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.rbac import get_user_role_for_workspace, get_workspace_id, require_min_role, require_roles
from app.models.role import RoleName
from app.models.user import User
from app.schemas.analytics import (
    DashboardAnalyticsResponse,
    InventorySummaryResponse,
    ProfitSummaryResponse,
    SalesSummaryResponse,
    SalesTrendItem,
    TopProductItem,
    CustomersSummaryResponse,
    AdvertisingReportResponse,
    BusinessInsightsResponse,
    CustomersReportResponse,
    DashboardSummaryResponse,
    InventoryReportResponse,
    ProductsReportResponse,
    SalesReportResponse,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _start_date(start_date: date | None = Query(default=None)) -> date | None:
    return start_date


def _end_date(end_date: date | None = Query(default=None)) -> date | None:
    return end_date


def _date_from(date_from: date | None = Query(default=None)) -> date | None:
    return date_from


def _date_to(date_to: date | None = Query(default=None)) -> date | None:
    return date_to


def _can_view_profit(user: User, workspace_id: UUID) -> bool:
    role = get_user_role_for_workspace(user, workspace_id)
    return role in {RoleName.OWNER, RoleName.ANALYST}


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


@router.get("/sales-report", response_model=SalesReportResponse, dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def sales_report(
    workspace_id: UUID = Depends(get_workspace_id),
    date_from: date | None = Depends(_date_from),
    date_to: date | None = Depends(_date_to),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SalesReportResponse:
    return AnalyticsService(db).sales_report(workspace_id, _can_view_profit(user, workspace_id), date_from, date_to)


@router.get("/products-report", response_model=ProductsReportResponse, dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def products_report(
    workspace_id: UUID = Depends(get_workspace_id),
    date_from: date | None = Depends(_date_from),
    date_to: date | None = Depends(_date_to),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProductsReportResponse:
    return AnalyticsService(db).products_report(workspace_id, _can_view_profit(user, workspace_id), date_from, date_to)


@router.get("/advertising-report", response_model=AdvertisingReportResponse, dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def advertising_report(
    workspace_id: UUID = Depends(get_workspace_id),
    date_from: date | None = Depends(_date_from),
    date_to: date | None = Depends(_date_to),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdvertisingReportResponse:
    return AnalyticsService(db).advertising_report(workspace_id, _can_view_profit(user, workspace_id), date_from, date_to)


@router.get("/customers-report", response_model=CustomersReportResponse, dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def customers_report(
    workspace_id: UUID = Depends(get_workspace_id),
    date_from: date | None = Depends(_date_from),
    date_to: date | None = Depends(_date_to),
    db: Session = Depends(get_db),
) -> CustomersReportResponse:
    return AnalyticsService(db).customers_report(workspace_id, date_from, date_to)


@router.get("/inventory-report", response_model=InventoryReportResponse, dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def inventory_report(
    workspace_id: UUID = Depends(get_workspace_id),
    date_from: date | None = Depends(_date_from),
    date_to: date | None = Depends(_date_to),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InventoryReportResponse:
    return AnalyticsService(db).inventory_report(workspace_id, _can_view_profit(user, workspace_id), date_from, date_to)


@router.get("/business-insights", response_model=BusinessInsightsResponse, dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def business_insights(
    workspace_id: UUID = Depends(get_workspace_id),
    date_from: date | None = Depends(_date_from),
    date_to: date | None = Depends(_date_to),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BusinessInsightsResponse:
    return AnalyticsService(db).business_insights(workspace_id, _can_view_profit(user, workspace_id), date_from, date_to)


@router.get("/dashboard-summary", response_model=DashboardSummaryResponse, dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def dashboard_summary(
    workspace_id: UUID = Depends(get_workspace_id),
    date_from: date | None = Depends(_date_from),
    date_to: date | None = Depends(_date_to),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardSummaryResponse:
    return AnalyticsService(db).dashboard_summary(workspace_id, _can_view_profit(user, workspace_id), date_from, date_to)
