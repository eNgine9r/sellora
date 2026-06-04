from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import OrderStatus, PaymentStatus


class OrderItemCreate(BaseModel):
    product_variant_id: UUID
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    unit_cost: Decimal = Field(default=0, ge=0)


class OrderCreate(BaseModel):
    customer_id: UUID | None = None
    payment_status: PaymentStatus = PaymentStatus.PENDING
    items: list[OrderItemCreate] = Field(min_length=1)
    ad_cost: Decimal = Field(default=0, ge=0)
    shipping_cost: Decimal = Field(default=0, ge=0)
    cod_fee: Decimal = Field(default=0, ge=0)
    other_cost: Decimal = Field(default=0, ge=0)
    notes: str | None = None


class OrderUpdate(BaseModel):
    payment_status: PaymentStatus | None = None
    ad_cost: Decimal | None = Field(default=None, ge=0)
    shipping_cost: Decimal | None = Field(default=None, ge=0)
    cod_fee: Decimal | None = Field(default=None, ge=0)
    other_cost: Decimal | None = Field(default=None, ge=0)
    notes: str | None = None
    items: list[OrderItemCreate] | None = Field(default=None, min_length=1)


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
    status: OrderStatus
    payment_status: PaymentStatus
    revenue: Decimal
    product_cost: Decimal
    ad_cost: Decimal
    shipping_cost: Decimal
    cod_fee: Decimal
    other_cost: Decimal
    net_profit: Decimal
    notes: str | None
    completed_at: datetime | None
    items: list[OrderItemResponse] = Field(default_factory=list)
    status_history: list[OrderStatusHistoryResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderDashboardResponse(BaseModel):
    orders_today: int
    revenue_today: Decimal
    profit_today: Decimal
