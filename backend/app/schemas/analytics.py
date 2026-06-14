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


class SalesReportDailyRow(BaseModel):
    date: date
    orders: int
    revenue: Decimal
    net_profit: Decimal | None = None
    aov: Decimal | None = None
    returns: int = 0
    cancelled: int = 0


class SalesReportResponse(BaseModel):
    can_view_profit: bool
    revenue: Decimal
    net_profit: Decimal | None = None
    orders_count: int
    aov: Decimal | None = None
    margin: Decimal | None = None
    return_rate: Decimal | None = None
    cancelled_orders: int
    delivered_orders: int
    daily_rows: list[SalesReportDailyRow] = Field(default_factory=list)
    order_status_breakdown: dict[str, int] = Field(default_factory=dict)
    payment_status_breakdown: dict[str, int] = Field(default_factory=dict)


class ProductReportRow(BaseModel):
    product_id: UUID
    product_name: str
    sku: str | None = None
    category: str | None = None
    image_url: str | None = None
    quantity_sold: int
    revenue: Decimal
    net_profit: Decimal | None = None
    current_stock: int = 0
    reserved_quantity: int = 0
    status: str


class CategoryReportRow(BaseModel):
    category: str | None = None
    quantity_sold: int
    revenue: Decimal
    net_profit: Decimal | None = None
    revenue_share: Decimal | None = None


class ProductsReportResponse(BaseModel):
    can_view_profit: bool
    top_products: list[ProductReportRow] = Field(default_factory=list)
    top_categories: list[CategoryReportRow] = Field(default_factory=list)
    low_stock_best_sellers: list[ProductReportRow] = Field(default_factory=list)
    slow_moving_products: list[ProductReportRow] = Field(default_factory=list)


class AdvertisingReportCampaignRow(BaseModel):
    campaign_id: UUID
    campaign_name: str
    platform: str
    spend: Decimal
    revenue: Decimal
    net_profit: Decimal | None = None
    roas: Decimal | None = None
    cpa: Decimal | None = None
    cpl: Decimal | None = None
    messages: int
    leads: int
    orders: int


class AdvertisingReportDailyRow(BaseModel):
    date: date
    spend: Decimal
    revenue: Decimal
    net_profit: Decimal | None = None
    roas: Decimal | None = None
    messages: int
    leads: int
    orders: int


class AdvertisingReportResponse(BaseModel):
    can_view_profit: bool
    spend: Decimal
    revenue: Decimal
    net_profit: Decimal | None = None
    roas: Decimal | None = None
    cpa: Decimal | None = None
    cpl: Decimal | None = None
    ctr: Decimal | None = None
    cpm: Decimal | None = None
    messages: int
    leads: int
    orders: int
    campaign_rows: list[AdvertisingReportCampaignRow] = Field(default_factory=list)
    daily_rows: list[AdvertisingReportDailyRow] = Field(default_factory=list)


class CustomerReportRow(BaseModel):
    customer_id: UUID
    name: str
    phone: str | None = None
    instagram_username: str | None = None
    orders_count: int
    total_spent: Decimal
    average_order_value: Decimal | None = None
    last_order_date: date | None = None
    tags: list[str] = Field(default_factory=list)


class CustomersReportResponse(BaseModel):
    new_customers: int
    repeat_customers: int
    customers_with_orders: int
    average_spend_per_customer: Decimal | None = None
    repeat_customer_rate: Decimal | None = None
    lead_conversion_rate: Decimal | None = None
    top_customers_by_revenue: list[CustomerReportRow] = Field(default_factory=list)
    top_customers_by_orders: list[CustomerReportRow] = Field(default_factory=list)


class InventoryReportRow(BaseModel):
    product_id: UUID
    product_name: str
    sku: str | None = None
    category: str | None = None
    image_url: str | None = None
    stock_quantity: int
    reserved_quantity: int
    incoming_quantity: int
    minimum_quantity: int
    status: str
    sales_in_period: int


class InventoryReportResponse(BaseModel):
    can_view_profit: bool
    low_stock_count: int
    out_of_stock_count: int
    reserved_quantity_total: int
    incoming_quantity_total: int
    stock_value: Decimal | None = None
    best_sellers_with_low_stock: list[InventoryReportRow] = Field(default_factory=list)
    products_with_stock_but_no_recent_sales: list[InventoryReportRow] = Field(default_factory=list)
    inventory_rows: list[InventoryReportRow] = Field(default_factory=list)


class BusinessInsightItem(BaseModel):
    key: str
    type: str
    category: str
    title_key: str
    description_key: str
    source_metric: str
    value: str | int | Decimal | None = None
    route: str | None = None
    cta_key: str | None = None


class BusinessInsightsResponse(BaseModel):
    insights: list[BusinessInsightItem] = Field(default_factory=list)


class DashboardSummaryResponse(BaseModel):
    can_view_profit: bool
    sales: SalesReportResponse
    advertising: AdvertisingReportResponse
    inventory: InventoryReportResponse
    products: ProductsReportResponse
    customers: CustomersReportResponse
    business_insights: list[BusinessInsightItem] = Field(default_factory=list)
