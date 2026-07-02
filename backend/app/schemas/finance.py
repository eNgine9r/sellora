from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.finance_adjustment import FinanceAdjustmentCategory, FinanceAdjustmentSource, FinanceAdjustmentType


class FinancePeriod(BaseModel):
    date_from: date
    date_to: date


class FinanceDataQualityWarning(BaseModel):
    code: str
    message: str
    message_uk: str


class FinanceAdjustmentCreate(BaseModel):
    type: FinanceAdjustmentType
    category: FinanceAdjustmentCategory = FinanceAdjustmentCategory.OTHER
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="UAH", min_length=3, max_length=3)
    occurred_at: datetime
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    order_id: UUID | None = None


class FinanceAdjustmentUpdate(BaseModel):
    type: FinanceAdjustmentType | None = None
    category: FinanceAdjustmentCategory | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    occurred_at: datetime | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    order_id: UUID | None = None


class FinanceAdjustmentResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    type: FinanceAdjustmentType
    category: FinanceAdjustmentCategory
    amount: Decimal
    currency: str
    occurred_at: datetime
    title: str
    description: str | None = None
    order_id: UUID | None = None
    source: FinanceAdjustmentSource
    created_by_user_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FinanceAdjustmentListResponse(BaseModel):
    items: list[FinanceAdjustmentResponse]
    total: int
    limit: int
    offset: int


class FinanceBreakdownItem(BaseModel):
    key: str
    label: str
    amount: Decimal
    direction: str
    share_of_revenue: Decimal | None = None


class FinanceBreakdownResponse(BaseModel):
    period: FinancePeriod
    items: list[FinanceBreakdownItem]


class FinanceComparisonMetric(BaseModel):
    current: Decimal | int | None = None
    previous: Decimal | int | None = None
    change: Decimal | None = None
    change_percent: Decimal | None = None


class FinancePeriodComparisonResponse(BaseModel):
    current_period: FinancePeriod
    previous_period: FinancePeriod
    revenue_change: FinanceComparisonMetric
    gross_profit_change: FinanceComparisonMetric
    net_profit_change: FinanceComparisonMetric
    orders_count_change: FinanceComparisonMetric
    ad_spend_change: FinanceComparisonMetric
    profit_margin_change: FinanceComparisonMetric


class FinanceSummaryResponse(BaseModel):
    period: FinancePeriod
    revenue: Decimal
    cogs: Decimal
    gross_profit: Decimal
    ad_spend: Decimal
    shipping_cost: Decimal
    discounts: Decimal
    refunds: Decimal
    other_expenses: Decimal
    manual_expenses: Decimal
    manual_refunds: Decimal
    manual_discounts: Decimal
    manual_fees: Decimal
    finance_adjustments_total: Decimal
    net_profit: Decimal
    profit_margin: Decimal | None = None
    orders_count: int
    paid_orders_count: int
    average_order_value: Decimal | None = None
    breakdown: list[FinanceBreakdownItem] = Field(default_factory=list)
    data_quality_warnings: list[FinanceDataQualityWarning] = Field(default_factory=list)
