from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class FinancePeriod(BaseModel):
    date_from: date
    date_to: date


class FinanceDataQualityWarning(BaseModel):
    code: str
    message: str
    message_uk: str


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
    net_profit: Decimal
    profit_margin: Decimal | None = None
    orders_count: int
    paid_orders_count: int
    average_order_value: Decimal | None = None
    data_quality_warnings: list[FinanceDataQualityWarning] = Field(default_factory=list)
