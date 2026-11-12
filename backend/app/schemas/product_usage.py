from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class ProductUsageTotals(BaseModel):
    active_workspaces: int
    active_workspace_days: int
    activated_workspaces: int
    first_products: int
    first_orders: int
    orders_created: int
    integration_days: int


class ProductUsageReport(BaseModel):
    days: Literal[7, 30]
    from_day: date
    to_day: date
    as_of: datetime
    coverage_from: datetime | None
    coverage: Literal["complete", "partial", "unavailable"]
    dropped_operations: int | None = None
    totals: ProductUsageTotals | None = None
