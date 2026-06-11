from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class DateRange(BaseModel):
    start_date: date
    end_date: date


class SalesSummaryResponse(BaseModel):
    total_orders: int
    total_revenue: Decimal
    average_order_value: Decimal
    completed_orders: int
    cancelled_orders: int
    returned_orders: int


class ProfitSummaryResponse(BaseModel):
    total_revenue: Decimal
    total_product_cost: Decimal
    total_ad_cost: Decimal
    total_shipping_cost: Decimal
    total_cod_fee: Decimal
    total_other_cost: Decimal
    total_net_profit: Decimal
    margin_percent: Decimal


class SalesTrendItem(BaseModel):
    date: date
    orders_count: int
    revenue: Decimal
    net_profit: Decimal


class TopProductItem(BaseModel):
    product_id: UUID
    product_name: str
    variant_id: UUID
    variant_sku: str
    color: str | None
    size: str | None
    quantity_sold: int
    revenue: Decimal
    net_profit: Decimal


class TopCustomerItem(BaseModel):
    customer_id: UUID
    name: str
    phone: str | None
    instagram_username: str | None
    total_orders: int
    total_spent: Decimal


class CustomersSummaryResponse(BaseModel):
    total_customers: int
    new_customers: int
    repeat_customers: int
    repeat_purchase_rate: Decimal
    top_customers: list[TopCustomerItem] = Field(default_factory=list)


class LowStockItem(BaseModel):
    product_id: UUID
    product_name: str
    variant_id: UUID
    variant_sku: str
    color: str | None
    size: str | None
    stock_quantity: int
    reserved_quantity: int
    incoming_quantity: int = 0
    minimum_quantity: int


class InventorySummaryResponse(BaseModel):
    total_variants: int
    low_stock_count: int
    out_of_stock_count: int
    total_stock_units: int
    low_stock_items: list[LowStockItem] = Field(default_factory=list)


class DashboardAnalyticsResponse(BaseModel):
    today_orders: int
    today_revenue: Decimal
    today_profit: Decimal
    month_orders: int
    month_revenue: Decimal
    month_profit: Decimal
    average_order_value: Decimal
    low_stock_count: int
    top_products: list[TopProductItem] = Field(default_factory=list)
    top_customers: list[TopCustomerItem] = Field(default_factory=list)
    sales_trend: list[SalesTrendItem] = Field(default_factory=list)
