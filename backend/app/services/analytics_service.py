from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatus
from app.models.lead import LeadStatus
from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import (
    DashboardAnalyticsResponse,
    InventorySummaryResponse,
    LowStockItem,
    ProfitSummaryResponse,
    SalesSummaryResponse,
    SalesTrendItem,
    TopCustomerItem,
    TopProductItem,
    CustomersSummaryResponse,
    AdvertisingReportCampaignRow,
    AdvertisingReportDailyRow,
    AdvertisingReportResponse,
    BusinessInsightItem,
    BusinessInsightsResponse,
    CategoryReportRow,
    CustomersReportResponse,
    CustomerReportRow,
    DashboardSummaryResponse,
    InventoryReportResponse,
    InventoryReportRow,
    ProductReportRow,
    ProductsReportResponse,
    SalesReportDailyRow,
    SalesReportResponse,
)

MONEY_ZERO = Decimal("0.00")
PERCENT_ZERO = Decimal("0.00")
REVENUE_INCLUDED_STATUSES = {
    OrderStatus.NEW.value,
    OrderStatus.CONFIRMED.value,
    OrderStatus.SHIPPED.value,
    OrderStatus.DELIVERED.value,
    OrderStatus.COMPLETED.value,
}


class AnalyticsService:
    def __init__(self, db: Session) -> None:
        self.repository = AnalyticsRepository(db)

    def _resolve_range(self, start_date: date | None, end_date: date | None) -> tuple[datetime, datetime]:
        today = datetime.now(UTC).date()
        resolved_end = end_date or today
        resolved_start = start_date or (resolved_end - timedelta(days=30))
        start_at = datetime.combine(resolved_start, time.min, tzinfo=UTC)
        end_at = datetime.combine(resolved_end, time.max, tzinfo=UTC)
        return start_at, end_at

    def sales_summary(self, workspace_id: UUID, start_date: date | None = None, end_date: date | None = None) -> SalesSummaryResponse:
        orders = self._orders(workspace_id, start_date, end_date)
        total_orders = len(orders)
        total_revenue = self._sum(order.revenue for order in orders)
        average_order_value = self._divide(total_revenue, Decimal(total_orders)) if total_orders else MONEY_ZERO
        return SalesSummaryResponse(
            total_orders=total_orders,
            total_revenue=total_revenue,
            average_order_value=average_order_value,
            completed_orders=sum(1 for order in orders if order.status == OrderStatus.COMPLETED.value),
            cancelled_orders=sum(1 for order in orders if order.status == OrderStatus.CANCELLED.value),
            returned_orders=sum(1 for order in orders if order.status == OrderStatus.RETURNED.value),
        )

    def profit_summary(self, workspace_id: UUID, start_date: date | None = None, end_date: date | None = None) -> ProfitSummaryResponse:
        orders = self._orders(workspace_id, start_date, end_date)
        total_revenue = self._sum(order.revenue for order in orders)
        total_net_profit = self._sum(order.net_profit for order in orders)
        margin_percent = (total_net_profit / total_revenue * Decimal("100")) if total_revenue else PERCENT_ZERO
        return ProfitSummaryResponse(
            total_revenue=total_revenue,
            total_product_cost=self._sum(order.product_cost for order in orders),
            total_ad_cost=self._sum(order.ad_cost for order in orders),
            total_shipping_cost=self._sum(order.shipping_cost for order in orders),
            total_cod_fee=self._sum(order.cod_fee for order in orders),
            total_other_cost=self._sum(order.other_cost for order in orders),
            total_net_profit=total_net_profit,
            margin_percent=self._quantize(margin_percent),
        )

    def sales_trend(self, workspace_id: UUID, start_date: date | None = None, end_date: date | None = None) -> list[SalesTrendItem]:
        orders = self._orders(workspace_id, start_date, end_date)
        grouped: dict[date, dict[str, Decimal | int]] = defaultdict(lambda: {"orders_count": 0, "revenue": MONEY_ZERO, "net_profit": MONEY_ZERO})
        for order in orders:
            metric_date = self._metric_date(order).date()
            grouped[metric_date]["orders_count"] += 1
            grouped[metric_date]["revenue"] += Decimal(order.revenue or 0)
            grouped[metric_date]["net_profit"] += Decimal(order.net_profit or 0)
        return [
            SalesTrendItem(
                date=day,
                orders_count=int(values["orders_count"]),
                revenue=self._quantize(Decimal(values["revenue"])),
                net_profit=self._quantize(Decimal(values["net_profit"])),
            )
            for day, values in sorted(grouped.items())
        ]

    def top_products(self, workspace_id: UUID, start_date: date | None = None, end_date: date | None = None, limit: int = 10) -> list[TopProductItem]:
        start_at, end_at = self._resolve_range(start_date, end_date)
        grouped: dict[UUID, dict[str, object]] = {}
        for item, _order, variant, product in self.repository.list_order_items(workspace_id, start_at, end_at):
            key = variant.id
            if key not in grouped:
                grouped[key] = {
                    "product_id": product.id,
                    "product_name": product.name,
                    "variant_id": variant.id,
                    "variant_sku": variant.sku,
                    "color": variant.color,
                    "size": variant.size,
                    "quantity_sold": 0,
                    "revenue": MONEY_ZERO,
                    "net_profit": MONEY_ZERO,
                }
            grouped[key]["quantity_sold"] = int(grouped[key]["quantity_sold"]) + item.quantity
            grouped[key]["revenue"] = Decimal(grouped[key]["revenue"]) + Decimal(item.line_total or 0)
            grouped[key]["net_profit"] = Decimal(grouped[key]["net_profit"]) + (Decimal(item.line_total or 0) - Decimal(item.line_cost or 0))
        rows = sorted(grouped.values(), key=lambda row: (Decimal(row["revenue"]), Decimal(row["net_profit"]), int(row["quantity_sold"])), reverse=True)[:limit]
        return [
            TopProductItem(
                product_id=row["product_id"],
                product_name=str(row["product_name"]),
                variant_id=row["variant_id"],
                variant_sku=str(row["variant_sku"]),
                color=row["color"],
                size=row["size"],
                quantity_sold=int(row["quantity_sold"]),
                revenue=self._quantize(Decimal(row["revenue"])),
                net_profit=self._quantize(Decimal(row["net_profit"])),
            )
            for row in rows
        ]

    def customers_summary(self, workspace_id: UUID, start_date: date | None = None, end_date: date | None = None, limit: int = 10) -> CustomersSummaryResponse:
        start_at, end_at = self._resolve_range(start_date, end_date)
        customers = self.repository.list_customers(workspace_id)
        total_customers = len(customers)
        new_customers = sum(1 for customer in customers if start_at <= customer.created_at <= end_at)
        repeat_customers = sum(1 for customer in customers if customer.total_orders >= 2)
        repeat_purchase_rate = self._divide(Decimal(repeat_customers), Decimal(total_customers)) * Decimal("100") if total_customers else PERCENT_ZERO
        top_customers = sorted(customers, key=lambda customer: (customer.total_spent, customer.total_orders), reverse=True)[:limit]
        return CustomersSummaryResponse(
            total_customers=total_customers,
            new_customers=new_customers,
            repeat_customers=repeat_customers,
            repeat_purchase_rate=self._quantize(repeat_purchase_rate),
            top_customers=[
                TopCustomerItem(
                    customer_id=customer.id,
                    name=customer.name,
                    phone=customer.phone,
                    instagram_username=customer.instagram_username,
                    total_orders=customer.total_orders,
                    total_spent=self._quantize(Decimal(customer.total_spent or 0)),
                )
                for customer in top_customers
            ],
        )

    def inventory_summary(self, workspace_id: UUID) -> InventorySummaryResponse:
        rows = self.repository.list_inventory_items(workspace_id)
        low_stock_items = [
            LowStockItem(
                product_id=product.id,
                product_name=product.name,
                variant_id=variant.id,
                variant_sku=variant.sku,
                color=variant.color,
                size=variant.size,
                stock_quantity=inventory.stock_quantity,
                reserved_quantity=inventory.reserved_quantity,
                minimum_quantity=inventory.minimum_quantity,
            )
            for inventory, variant, product in rows
            if inventory.stock_quantity <= inventory.minimum_quantity
        ]
        return InventorySummaryResponse(
            total_variants=len(rows),
            low_stock_count=len(low_stock_items),
            out_of_stock_count=sum(1 for inventory, _variant, _product in rows if inventory.stock_quantity <= 0),
            total_stock_units=sum(inventory.stock_quantity for inventory, _variant, _product in rows),
            low_stock_items=low_stock_items,
        )

    def dashboard(self, workspace_id: UUID) -> DashboardAnalyticsResponse:
        today = datetime.now(UTC).date()
        month_start = today.replace(day=1)
        today_orders = self._orders(workspace_id, today, today)
        month_orders = self._orders(workspace_id, month_start, today)
        month_total_orders = len(month_orders)
        month_revenue = self._sum(order.revenue for order in month_orders)
        return DashboardAnalyticsResponse(
            today_orders=len(today_orders),
            today_revenue=self._sum(order.revenue for order in today_orders),
            today_profit=self._sum(order.net_profit for order in today_orders),
            month_orders=month_total_orders,
            month_revenue=month_revenue,
            month_profit=self._sum(order.net_profit for order in month_orders),
            average_order_value=self._divide(month_revenue, Decimal(month_total_orders)) if month_total_orders else MONEY_ZERO,
            low_stock_count=self.inventory_summary(workspace_id).low_stock_count,
            top_products=self.top_products(workspace_id, month_start, today, limit=5),
            top_customers=self.customers_summary(workspace_id, month_start, today, limit=5).top_customers,
            sales_trend=self.sales_trend(workspace_id, month_start, today),
        )


    def sales_report(self, workspace_id: UUID, can_view_profit: bool, start_date: date | None = None, end_date: date | None = None) -> SalesReportResponse:
        orders = self._orders(workspace_id, start_date, end_date)
        revenue_orders = [order for order in orders if order.status in REVENUE_INCLUDED_STATUSES]
        revenue = self._sum(order.revenue for order in revenue_orders)
        net_profit = self._sum(order.net_profit for order in revenue_orders) if can_view_profit else None
        orders_count = len(revenue_orders)
        shipped_or_delivered = sum(1 for order in orders if order.status in {OrderStatus.SHIPPED.value, OrderStatus.DELIVERED.value, OrderStatus.COMPLETED.value, OrderStatus.RETURNED.value})
        returned_orders = sum(1 for order in orders if order.status == OrderStatus.RETURNED.value)
        grouped: dict[date, dict[str, Decimal | int]] = defaultdict(lambda: {"orders": 0, "revenue": MONEY_ZERO, "net_profit": MONEY_ZERO, "returns": 0, "cancelled": 0})
        for order in orders:
            day = self._metric_date(order).date()
            if order.status in REVENUE_INCLUDED_STATUSES:
                grouped[day]["orders"] += 1
                grouped[day]["revenue"] += Decimal(order.revenue or 0)
                grouped[day]["net_profit"] += Decimal(order.net_profit or 0)
            if order.status == OrderStatus.RETURNED.value:
                grouped[day]["returns"] += 1
            if order.status == OrderStatus.CANCELLED.value:
                grouped[day]["cancelled"] += 1
        return SalesReportResponse(
            can_view_profit=can_view_profit,
            revenue=revenue,
            net_profit=net_profit,
            orders_count=orders_count,
            aov=self._safe_divide(revenue, Decimal(orders_count)),
            margin=self._safe_divide(net_profit, revenue) if can_view_profit and net_profit is not None else None,
            return_rate=self._safe_divide(Decimal(returned_orders), Decimal(shipped_or_delivered)),
            cancelled_orders=sum(1 for order in orders if order.status == OrderStatus.CANCELLED.value),
            delivered_orders=sum(1 for order in orders if order.status in {OrderStatus.DELIVERED.value, OrderStatus.COMPLETED.value}),
            daily_rows=[
                SalesReportDailyRow(
                    date=day,
                    orders=int(values["orders"]),
                    revenue=self._quantize(Decimal(values["revenue"])),
                    net_profit=self._quantize(Decimal(values["net_profit"])) if can_view_profit else None,
                    aov=self._safe_divide(Decimal(values["revenue"]), Decimal(values["orders"])),
                    returns=int(values["returns"]),
                    cancelled=int(values["cancelled"]),
                )
                for day, values in sorted(grouped.items())
            ],
            order_status_breakdown={status.value: sum(1 for order in orders if order.status == status.value) for status in OrderStatus},
            payment_status_breakdown=self._payment_status_breakdown(orders),
        )

    def products_report(self, workspace_id: UUID, can_view_profit: bool, start_date: date | None = None, end_date: date | None = None, limit: int = 10) -> ProductsReportResponse:
        start_at, end_at = self._resolve_range(start_date, end_date)
        inventory_lookup = {variant.id: inventory for inventory, variant, _product in self.repository.list_inventory_items(workspace_id)}
        grouped: dict[UUID, dict[str, object]] = {}
        categories: dict[str, dict[str, Decimal | int | None]] = {}
        for item, order, variant, product in self.repository.list_order_items(workspace_id, start_at, end_at):
            if order.status not in REVENUE_INCLUDED_STATUSES:
                continue
            key = variant.id
            inventory = inventory_lookup.get(variant.id)
            if key not in grouped:
                grouped[key] = {
                    "product_id": product.id,
                    "product_name": product.name,
                    "sku": variant.sku or item.sku,
                    "category": product.category,
                    "quantity_sold": 0,
                    "revenue": MONEY_ZERO,
                    "net_profit": MONEY_ZERO,
                    "current_stock": inventory.stock_quantity if inventory else 0,
                    "reserved_quantity": inventory.reserved_quantity if inventory else 0,
                    "status": self._stock_status(inventory.stock_quantity if inventory else 0, inventory.minimum_quantity if inventory else 0),
                }
            grouped[key]["quantity_sold"] = int(grouped[key]["quantity_sold"]) + item.quantity
            grouped[key]["revenue"] = Decimal(grouped[key]["revenue"]) + Decimal(item.line_total or 0)
            grouped[key]["net_profit"] = Decimal(grouped[key]["net_profit"]) + (Decimal(item.line_total or 0) - Decimal(item.line_cost or 0))
            category_key = product.category or "other"
            if category_key not in categories:
                categories[category_key] = {"category": product.category, "quantity_sold": 0, "revenue": MONEY_ZERO, "net_profit": MONEY_ZERO}
            categories[category_key]["quantity_sold"] = int(categories[category_key]["quantity_sold"] or 0) + item.quantity
            categories[category_key]["revenue"] = Decimal(categories[category_key]["revenue"] or 0) + Decimal(item.line_total or 0)
            categories[category_key]["net_profit"] = Decimal(categories[category_key]["net_profit"] or 0) + (Decimal(item.line_total or 0) - Decimal(item.line_cost or 0))
        product_rows = [self._product_report_row(row, can_view_profit) for row in grouped.values()]
        product_rows.sort(key=lambda row: (row.revenue, row.quantity_sold), reverse=True)
        total_revenue = self._sum(row.revenue for row in product_rows)
        category_rows = [
            CategoryReportRow(
                category=values["category"],
                quantity_sold=int(values["quantity_sold"] or 0),
                revenue=self._quantize(Decimal(values["revenue"] or 0)),
                net_profit=self._quantize(Decimal(values["net_profit"] or 0)) if can_view_profit else None,
                revenue_share=self._safe_divide(Decimal(values["revenue"] or 0), total_revenue),
            )
            for values in categories.values()
        ]
        category_rows.sort(key=lambda row: row.revenue, reverse=True)
        low_stock_best_sellers = [row for row in product_rows if row.status in {"LOW_STOCK", "OUT_OF_STOCK"}]
        return ProductsReportResponse(
            can_view_profit=can_view_profit,
            top_products=product_rows[:limit],
            top_categories=category_rows[:limit],
            low_stock_best_sellers=low_stock_best_sellers[:limit],
            slow_moving_products=[],
        )

    def advertising_report(self, workspace_id: UUID, can_view_profit: bool, start_date: date | None = None, end_date: date | None = None) -> AdvertisingReportResponse:
        start_at, end_at = self._resolve_range(start_date, end_date)
        rows = self.repository.list_ad_metrics(workspace_id, start_at, end_at)
        spend = self._sum(metric.spend for metric, _campaign in rows)
        revenue = self._sum(metric.revenue for metric, _campaign in rows)
        net_profit = self._sum(metric.net_profit for metric, _campaign in rows) if can_view_profit else None
        messages = sum(metric.messages for metric, _campaign in rows)
        leads = sum(metric.leads for metric, _campaign in rows)
        orders = sum(metric.orders for metric, _campaign in rows)
        clicks = sum(metric.clicks for metric, _campaign in rows)
        impressions = sum(metric.impressions for metric, _campaign in rows)
        campaign_grouped: dict[UUID, dict[str, object]] = {}
        daily_grouped: dict[date, dict[str, Decimal | int]] = defaultdict(lambda: {"spend": MONEY_ZERO, "revenue": MONEY_ZERO, "net_profit": MONEY_ZERO, "messages": 0, "leads": 0, "orders": 0})
        for metric, campaign in rows:
            if campaign.id not in campaign_grouped:
                campaign_grouped[campaign.id] = {"campaign_id": campaign.id, "campaign_name": campaign.name, "platform": campaign.platform, "spend": MONEY_ZERO, "revenue": MONEY_ZERO, "net_profit": MONEY_ZERO, "messages": 0, "leads": 0, "orders": 0}
            row = campaign_grouped[campaign.id]
            row["spend"] = Decimal(row["spend"]) + Decimal(metric.spend or 0)
            row["revenue"] = Decimal(row["revenue"]) + Decimal(metric.revenue or 0)
            row["net_profit"] = Decimal(row["net_profit"]) + Decimal(metric.net_profit or 0)
            row["messages"] = int(row["messages"]) + metric.messages
            row["leads"] = int(row["leads"]) + metric.leads
            row["orders"] = int(row["orders"]) + metric.orders
            day = metric.metric_date
            daily_grouped[day]["spend"] += Decimal(metric.spend or 0)
            daily_grouped[day]["revenue"] += Decimal(metric.revenue or 0)
            daily_grouped[day]["net_profit"] += Decimal(metric.net_profit or 0)
            daily_grouped[day]["messages"] += metric.messages
            daily_grouped[day]["leads"] += metric.leads
            daily_grouped[day]["orders"] += metric.orders
        campaign_rows = [
            AdvertisingReportCampaignRow(
                campaign_id=row["campaign_id"],
                campaign_name=str(row["campaign_name"]),
                platform=str(row["platform"]),
                spend=self._quantize(Decimal(row["spend"])),
                revenue=self._quantize(Decimal(row["revenue"])),
                net_profit=self._quantize(Decimal(row["net_profit"])) if can_view_profit else None,
                roas=self._safe_divide(Decimal(row["revenue"]), Decimal(row["spend"])),
                cpa=self._safe_divide(Decimal(row["spend"]), Decimal(row["orders"])),
                cpl=self._safe_divide(Decimal(row["spend"]), Decimal(row["leads"])),
                messages=int(row["messages"]),
                leads=int(row["leads"]),
                orders=int(row["orders"]),
            )
            for row in campaign_grouped.values()
        ]
        campaign_rows.sort(key=lambda row: row.spend, reverse=True)
        return AdvertisingReportResponse(
            can_view_profit=can_view_profit,
            spend=spend,
            revenue=revenue,
            net_profit=net_profit,
            roas=self._safe_divide(revenue, spend),
            cpa=self._safe_divide(spend, Decimal(orders)),
            cpl=self._safe_divide(spend, Decimal(leads)),
            ctr=self._safe_divide(Decimal(clicks), Decimal(impressions)),
            cpm=self._safe_divide(spend * Decimal("1000"), Decimal(impressions)),
            messages=messages,
            leads=leads,
            orders=orders,
            campaign_rows=campaign_rows,
            daily_rows=[
                AdvertisingReportDailyRow(
                    date=day,
                    spend=self._quantize(Decimal(values["spend"])),
                    revenue=self._quantize(Decimal(values["revenue"])),
                    net_profit=self._quantize(Decimal(values["net_profit"])) if can_view_profit else None,
                    roas=self._safe_divide(Decimal(values["revenue"]), Decimal(values["spend"])),
                    messages=int(values["messages"]),
                    leads=int(values["leads"]),
                    orders=int(values["orders"]),
                )
                for day, values in sorted(daily_grouped.items())
            ],
        )

    def customers_report(self, workspace_id: UUID, start_date: date | None = None, end_date: date | None = None, limit: int = 10) -> CustomersReportResponse:
        start_at, end_at = self._resolve_range(start_date, end_date)
        customers = self.repository.list_customers(workspace_id)
        leads = self.repository.list_leads(workspace_id, start_at, end_at)
        customers_with_orders = [customer for customer in customers if customer.total_orders > 0]
        repeat_customers = [customer for customer in customers_with_orders if customer.total_orders >= 2]
        customer_rows = [
            CustomerReportRow(
                customer_id=customer.id,
                name=customer.name,
                phone=customer.phone,
                instagram_username=customer.instagram_username,
                orders_count=customer.total_orders,
                total_spent=self._quantize(Decimal(customer.total_spent or 0)),
                average_order_value=self._safe_divide(Decimal(customer.total_spent or 0), Decimal(customer.total_orders)),
                last_order_date=customer.last_order_at.date() if customer.last_order_at else None,
                tags=[],
            )
            for customer in customers_with_orders
        ]
        return CustomersReportResponse(
            new_customers=sum(1 for customer in customers if start_at <= customer.created_at <= end_at),
            repeat_customers=len(repeat_customers),
            customers_with_orders=len(customers_with_orders),
            average_spend_per_customer=self._safe_divide(self._sum(customer.total_spent for customer in customers_with_orders), Decimal(len(customers_with_orders))),
            repeat_customer_rate=self._safe_divide(Decimal(len(repeat_customers)), Decimal(len(customers_with_orders))),
            lead_conversion_rate=self._safe_divide(Decimal(sum(1 for lead in leads if lead.status == LeadStatus.CONVERTED.value)), Decimal(len(leads))),
            top_customers_by_revenue=sorted(customer_rows, key=lambda row: row.total_spent, reverse=True)[:limit],
            top_customers_by_orders=sorted(customer_rows, key=lambda row: row.orders_count, reverse=True)[:limit],
        )

    def inventory_report(self, workspace_id: UUID, can_view_profit: bool, start_date: date | None = None, end_date: date | None = None) -> InventoryReportResponse:
        start_at, end_at = self._resolve_range(start_date, end_date)
        sales_by_variant: dict[UUID, int] = defaultdict(int)
        for item, order, variant, _product in self.repository.list_order_items(workspace_id, start_at, end_at):
            if order.status in REVENUE_INCLUDED_STATUSES:
                sales_by_variant[variant.id] += item.quantity
        rows = []
        for inventory, variant, product in self.repository.list_inventory_items(workspace_id):
            rows.append(
                InventoryReportRow(
                    product_id=product.id,
                    product_name=product.name,
                    sku=variant.sku,
                    category=product.category,
                    image_url=None,
                    stock_quantity=inventory.stock_quantity,
                    reserved_quantity=inventory.reserved_quantity,
                    incoming_quantity=inventory.incoming_quantity or 0,
                    minimum_quantity=inventory.minimum_quantity,
                    status=self._stock_status(inventory.stock_quantity, inventory.minimum_quantity),
                    sales_in_period=sales_by_variant.get(variant.id, 0),
                )
            )
        rows.sort(key=lambda row: (row.status == "OUT_OF_STOCK", row.status == "LOW_STOCK", row.sales_in_period), reverse=True)
        return InventoryReportResponse(
            can_view_profit=can_view_profit,
            low_stock_count=sum(1 for row in rows if row.stock_quantity <= row.minimum_quantity),
            out_of_stock_count=sum(1 for row in rows if row.stock_quantity <= 0),
            reserved_quantity_total=sum(row.reserved_quantity for row in rows),
            incoming_quantity_total=sum(row.incoming_quantity for row in rows),
            stock_value=None,
            best_sellers_with_low_stock=[row for row in rows if row.status in {"LOW_STOCK", "OUT_OF_STOCK"} and row.sales_in_period > 0][:10],
            products_with_stock_but_no_recent_sales=[row for row in rows if row.stock_quantity > row.minimum_quantity and row.sales_in_period == 0][:10],
            inventory_rows=rows,
        )

    def business_insights(self, workspace_id: UUID, can_view_profit: bool, start_date: date | None = None, end_date: date | None = None) -> BusinessInsightsResponse:
        sales = self.sales_report(workspace_id, can_view_profit, start_date, end_date)
        advertising = self.advertising_report(workspace_id, can_view_profit, start_date, end_date)
        inventory = self.inventory_report(workspace_id, can_view_profit, start_date, end_date)
        insights: list[BusinessInsightItem] = []
        if inventory.best_sellers_with_low_stock:
            insights.append(BusinessInsightItem(key="low_stock_best_seller", type="critical", category="inventory", title_key="analytics.insights.lowStockTitle", description_key="analytics.insights.lowStockDescription", source_metric="best_sellers_with_low_stock", value=len(inventory.best_sellers_with_low_stock), route="/inventory", cta_key="analytics.insights.ctaInventory"))
        if advertising.spend > MONEY_ZERO and advertising.orders == 0:
            insights.append(BusinessInsightItem(key="ad_spend_without_orders", type="warning", category="advertising", title_key="analytics.insights.adSpendNoOrdersTitle", description_key="analytics.insights.adSpendNoOrdersDescription", source_metric="advertising.orders", value=advertising.spend, route="/advertising", cta_key="analytics.insights.ctaAdvertising"))
        if advertising.roas is not None and advertising.roas < Decimal("1.00"):
            insights.append(BusinessInsightItem(key="roas_below_one", type="warning", category="advertising", title_key="analytics.insights.lowRoasTitle", description_key="analytics.insights.lowRoasDescription", source_metric="advertising.roas", value=advertising.roas, route="/advertising", cta_key="analytics.insights.ctaAdvertising"))
        if sales.return_rate is not None and sales.return_rate > Decimal("0.20"):
            insights.append(BusinessInsightItem(key="high_return_activity", type="warning", category="sales", title_key="analytics.insights.returnsTitle", description_key="analytics.insights.returnsDescription", source_metric="sales.return_rate", value=sales.return_rate, route="/orders", cta_key="analytics.insights.ctaOrders"))
        if not insights:
            insights.append(BusinessInsightItem(key="healthy_analytics", type="positive", category="operations", title_key="analytics.insights.healthyTitle", description_key="analytics.insights.healthyDescription", source_metric="analytics.health", value=None, route="/dashboard", cta_key="analytics.insights.title"))
        return BusinessInsightsResponse(insights=insights)

    def dashboard_summary(self, workspace_id: UUID, can_view_profit: bool, start_date: date | None = None, end_date: date | None = None) -> DashboardSummaryResponse:
        return DashboardSummaryResponse(
            can_view_profit=can_view_profit,
            sales=self.sales_report(workspace_id, can_view_profit, start_date, end_date),
            advertising=self.advertising_report(workspace_id, can_view_profit, start_date, end_date),
            inventory=self.inventory_report(workspace_id, can_view_profit, start_date, end_date),
            products=self.products_report(workspace_id, can_view_profit, start_date, end_date, limit=5),
            customers=self.customers_report(workspace_id, start_date, end_date, limit=5),
            business_insights=self.business_insights(workspace_id, can_view_profit, start_date, end_date).insights,
        )

    def _orders(self, workspace_id: UUID, start_date: date | None, end_date: date | None) -> list[Order]:
        start_at, end_at = self._resolve_range(start_date, end_date)
        return self.repository.list_orders(workspace_id, start_at, end_at)

    def _metric_date(self, order: Order) -> datetime:
        return order.completed_at or order.created_at

    def _sum(self, values) -> Decimal:
        return self._quantize(sum((Decimal(value or 0) for value in values), MONEY_ZERO))



    def _safe_divide(self, numerator: Decimal | None, denominator: Decimal | None) -> Decimal | None:
        if numerator is None or denominator is None or denominator == 0:
            return None
        return self._quantize(Decimal(numerator) / Decimal(denominator))

    def _payment_status_breakdown(self, orders: list[Order]) -> dict[str, int]:
        grouped: dict[str, int] = defaultdict(int)
        for order in orders:
            grouped[order.payment_status or "UNKNOWN"] += 1
        return dict(grouped)

    def _stock_status(self, stock_quantity: int, minimum_quantity: int) -> str:
        if stock_quantity <= 0:
            return "OUT_OF_STOCK"
        if stock_quantity <= minimum_quantity:
            return "LOW_STOCK"
        return "IN_STOCK"

    def _product_report_row(self, row: dict[str, object], can_view_profit: bool) -> ProductReportRow:
        return ProductReportRow(
            product_id=row["product_id"],
            product_name=str(row["product_name"]),
            sku=str(row["sku"]) if row.get("sku") is not None else None,
            category=str(row["category"]) if row.get("category") is not None else None,
            image_url=None,
            quantity_sold=int(row["quantity_sold"]),
            revenue=self._quantize(Decimal(row["revenue"])),
            net_profit=self._quantize(Decimal(row["net_profit"])) if can_view_profit else None,
            current_stock=int(row["current_stock"]),
            reserved_quantity=int(row["reserved_quantity"]),
            status=str(row["status"]),
        )

    def _divide(self, numerator: Decimal, denominator: Decimal) -> Decimal:
        if denominator == 0:
            return MONEY_ZERO
        return self._quantize(numerator / denominator)

    def _quantize(self, value: Decimal) -> Decimal:
        return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
