from datetime import datetime
from enum import StrEnum
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.order import OrderStatus, PaymentStatus


class HistoricalCostSource(StrEnum):
    SHEET_ROW_MATCH = "SHEET_ROW_MATCH"
    PRICE_MEDIAN = "PRICE_MEDIAN"
    PRICE_BAND = "PRICE_BAND"
    MANUAL = "MANUAL"


class HistoricalCostConfidence(StrEnum):
    MULTI_SIGNAL_MATCH = "MULTI_SIGNAL_MATCH"
    PRICE_ONLY = "PRICE_ONLY"
    LOW = "LOW"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class HistoricalEstimatedCostUpsert(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    source: HistoricalCostSource
    reference: str | None = Field(default=None, max_length=512)


class OrderItemCreate(BaseModel):
    product_variant_id: UUID
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    unit_cost: Decimal = Field(default=0, ge=0)
    cost_confirmed: bool | None = None

    @model_validator(mode="after")
    def validate_confirmation(self):
        if self.cost_confirmed is True and "unit_cost" not in self.model_fields_set:
            raise ValueError("A confirmed cost must be supplied explicitly")
        return self


class OrderCreate(BaseModel):
    customer_id: UUID | None = None
    campaign_id: UUID | None = None
    status: OrderStatus = OrderStatus.NEW
    payment_status: PaymentStatus = PaymentStatus.PENDING
    is_historical: bool = False
    items: list[OrderItemCreate] = Field(min_length=1)
    ad_cost: Decimal = Field(default=0, ge=0)
    shipping_cost: Decimal = Field(default=0, ge=0)
    cod_fee: Decimal = Field(default=0, ge=0)
    other_cost: Decimal = Field(default=0, ge=0)
    notes: str | None = None


class OrderUpdate(BaseModel):
    customer_id: UUID | None = None
    campaign_id: UUID | None = Field(default=None, description="Omit to preserve campaign attribution; null clears it. A supplied campaign must be visible in the order workspace.")
    payment_status: PaymentStatus | None = None
    ad_cost: Decimal | None = Field(default=None, ge=0)
    shipping_cost: Decimal | None = Field(default=None, ge=0)
    cod_fee: Decimal | None = Field(default=None, ge=0)
    other_cost: Decimal | None = Field(default=None, ge=0)
    notes: str | None = None
    items: list[OrderItemCreate] | None = Field(default=None, min_length=1)


class OrderProductCostItem(BaseModel):
    item_id: UUID
    # Null explicitly marks an unknown cost; zero confirms a free item.
    unit_cost: Decimal | None = Field(ge=0, max_digits=12, decimal_places=2)


class OrderProductCostsUpdate(BaseModel):
    items: list[OrderProductCostItem] = Field(min_length=1, max_length=1000)


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    note: str | None = None


class OrderItemResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    order_id: UUID
    product_variant_id: UUID
    sku: str
    product_name: str
    quantity: int
    unit_price: Decimal
    unit_cost: Decimal
    cost_confirmed: bool | None = None
    line_total: Decimal
    line_cost: Decimal

    model_config = ConfigDict(from_attributes=True)


class OrderStatusHistoryResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    order_id: UUID
    from_status: OrderStatus | None
    to_status: OrderStatus
    changed_by: UUID | None
    note: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    order_number: str
    customer_id: UUID | None
    campaign_id: UUID | None
    campaign_name: str | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_instagram_username: str | None = None
    status: OrderStatus
    payment_status: PaymentStatus
    is_historical: bool = False
    revenue: Decimal
    historical_order_value: Decimal | None = None
    historical_value_source: str | None = None
    historical_value_evidence: dict | None = None
    product_cost: Decimal | None
    estimated_product_cost: Decimal | None = None
    estimated_cost_source: HistoricalCostSource | None = None
    estimated_cost_confidence: HistoricalCostConfidence | None = None
    estimated_cost_reference: str | None = None
    ad_cost: Decimal
    shipping_cost: Decimal
    cod_fee: Decimal
    other_cost: Decimal
    net_profit: Decimal | None
    notes: str | None
    completed_at: datetime | None
    items: list[OrderItemResponse] = Field(default_factory=list)
    status_history: list[OrderStatusHistoryResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def hide_unconfirmed_financial_results(self):
        # Keep underlying historical amounts intact, but do not present a
        # calculation based on missing item costs as a confirmed result.
        from app.services.profit_calculation_service import ProfitCalculationService
        if not ProfitCalculationService.order_cost_known(self):
            self.product_cost = None
            if ProfitCalculationService.includes_order(self):
                self.net_profit = None
        return self


class OrderDashboardResponse(BaseModel):
    orders_today: int
    revenue_today: Decimal
    profit_today: Decimal | None
