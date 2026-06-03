from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatus
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
)

MONEY_ZERO = Decimal("0.00")
PERCENT_ZERO = Decimal("0.00")


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

    def _orders(self, workspace_id: UUID, start_date: date | None, end_date: date | None) -> list[Order]:
        start_at, end_at = self._resolve_range(start_date, end_date)
        return self.repository.list_orders(workspace_id, start_at, end_at)

    def _metric_date(self, order: Order) -> datetime:
        return order.completed_at or order.created_at

    def _sum(self, values) -> Decimal:
        return self._quantize(sum((Decimal(value or 0) for value in values), MONEY_ZERO))

    def _divide(self, numerator: Decimal, denominator: Decimal) -> Decimal:
        if denominator == 0:
            return MONEY_ZERO
        return self._quantize(numerator / denominator)

    def _quantize(self, value: Decimal) -> Decimal:
        return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
