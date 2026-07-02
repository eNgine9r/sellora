from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatus, PaymentStatus
from app.repositories.finance_repository import FinanceRepository
from app.schemas.finance import FinanceDataQualityWarning, FinancePeriod, FinanceSummaryResponse

MONEY_ZERO = Decimal("0.00")
VALID_REVENUE_STATUSES = {
    OrderStatus.NEW.value,
    OrderStatus.CONFIRMED.value,
    OrderStatus.SHIPPED.value,
    OrderStatus.DELIVERED.value,
    OrderStatus.COMPLETED.value,
}
PAID_PAYMENT_STATUSES = {PaymentStatus.PAID.value, PaymentStatus.COD.value}
EXCLUDED_ORDER_STATUSES = {OrderStatus.CANCELLED.value, OrderStatus.RETURNED.value}


class FinanceService:
    def __init__(self, db: Session) -> None:
        self.repository = FinanceRepository(db)

    def summary(self, workspace_id: UUID, date_from: date | None = None, date_to: date | None = None) -> FinanceSummaryResponse:
        start_at, end_at = self._resolve_range(date_from, date_to)
        orders = self.repository.list_orders(workspace_id, start_at, end_at)
        shipments = self.repository.list_shipments(workspace_id, start_at, end_at)
        ad_metrics = self.repository.list_manual_ad_metrics(workspace_id, start_at, end_at)

        warnings: list[FinanceDataQualityWarning] = [
            self._warning(
                "advertising_manual_csv_source",
                "Advertising spend uses manual/CSV metrics only until Advertising runtime/staging blockers are resolved.",
                "Рекламні витрати беруться лише з ручних або CSV-метрик, доки runtime/staging блокери Advertising не закриті.",
            ),
            self._warning(
                "meta_ads_not_active",
                "Meta Ads API is not active and is not used for finance metrics.",
                "Meta Ads API не активний і не використовується для фінансових метрик.",
            ),
        ]

        valid_orders = [order for order in orders if self._is_valid_revenue_order(order)]
        excluded_orders = [order for order in orders if self._is_excluded_order(order)]
        if not valid_orders:
            warnings.append(
                self._warning(
                    "no_orders_in_period",
                    "No valid orders were found for the selected period.",
                    "За вибраний період не знайдено валідних замовлень.",
                )
            )

        revenue = self._sum(order.revenue for order in valid_orders)
        cogs, missing_cost_count = self._calculate_cogs(valid_orders)
        if missing_cost_count:
            warnings.append(
                self._warning(
                    "missing_product_cost",
                    f"Product cost is missing for {missing_cost_count} order item(s), so COGS may be understated.",
                    f"Для {missing_cost_count} позицій замовлень відсутня собівартість, тому COGS може бути заниженим.",
                )
            )

        ad_spend = self._sum(metric.spend for metric in ad_metrics)
        shipping_cost, missing_shipping_count = self._calculate_shipping_cost(valid_orders, shipments)
        if missing_shipping_count:
            warnings.append(
                self._warning(
                    "missing_shipment_cost",
                    f"Shipping cost is missing for {missing_shipping_count} order(s), so delivery expenses may be understated.",
                    f"Для {missing_shipping_count} замовлень відсутня вартість доставки, тому витрати на доставку можуть бути занижені.",
                )
            )

        discounts = MONEY_ZERO
        warnings.append(
            self._warning(
                "discounts_unavailable",
                "Discount fields are not available yet, so discounts are treated as 0 for the MVP finance summary.",
                "Поля знижок ще недоступні, тому у MVP-фінансах знижки враховано як 0.",
            )
        )
        refunds = MONEY_ZERO
        if excluded_orders:
            warnings.append(
                self._warning(
                    "cancelled_refunded_orders_excluded",
                    "Cancelled, returned, and refunded orders are excluded from revenue to avoid double-counting refunds.",
                    "Скасовані, повернені та відшкодовані замовлення виключені з доходу, щоб не дублювати повернення.",
                )
            )
        other_expenses = self._sum((order.cod_fee or MONEY_ZERO) + (order.other_cost or MONEY_ZERO) for order in valid_orders)
        if other_expenses == MONEY_ZERO:
            warnings.append(
                self._warning(
                    "other_expenses_limited",
                    "Other expenses are limited to order COD fees and order-level other costs; full accounting expenses are future work.",
                    "Інші витрати обмежені комісіями накладеного платежу та витратами в замовленні; повна бухгалтерія — майбутня робота.",
                )
            )

        gross_profit = revenue - cogs
        net_profit = revenue - cogs - ad_spend - shipping_cost - discounts - refunds - other_expenses
        orders_count = len(valid_orders)
        paid_orders_count = sum(1 for order in valid_orders if order.payment_status in PAID_PAYMENT_STATUSES)
        average_denominator = paid_orders_count or orders_count
        average_order_value = self._divide(revenue, Decimal(average_denominator)) if average_denominator else None
        profit_margin = self._divide(net_profit, revenue) * Decimal("100") if revenue else None

        return FinanceSummaryResponse(
            period=FinancePeriod(date_from=start_at.date(), date_to=end_at.date()),
            revenue=self._quantize(revenue),
            cogs=self._quantize(cogs),
            gross_profit=self._quantize(gross_profit),
            ad_spend=self._quantize(ad_spend),
            shipping_cost=self._quantize(shipping_cost),
            discounts=self._quantize(discounts),
            refunds=self._quantize(refunds),
            other_expenses=self._quantize(other_expenses),
            net_profit=self._quantize(net_profit),
            profit_margin=self._quantize(profit_margin) if profit_margin is not None else None,
            orders_count=orders_count,
            paid_orders_count=paid_orders_count,
            average_order_value=self._quantize(average_order_value) if average_order_value is not None else None,
            data_quality_warnings=warnings,
        )

    def _resolve_range(self, date_from: date | None, date_to: date | None) -> tuple[datetime, datetime]:
        today = datetime.now(UTC).date()
        resolved_to = date_to or today
        resolved_from = date_from or (resolved_to - timedelta(days=30))
        return datetime.combine(resolved_from, time.min, tzinfo=UTC), datetime.combine(resolved_to, time.max, tzinfo=UTC)

    def _is_valid_revenue_order(self, order: Order) -> bool:
        return order.status in VALID_REVENUE_STATUSES and order.payment_status != PaymentStatus.REFUNDED.value

    def _is_excluded_order(self, order: Order) -> bool:
        return order.status in EXCLUDED_ORDER_STATUSES or order.payment_status == PaymentStatus.REFUNDED.value

    def _calculate_cogs(self, orders: list[Order]) -> tuple[Decimal, int]:
        total = MONEY_ZERO
        missing = 0
        for order in orders:
            items = list(getattr(order, "items", []) or [])
            if items:
                for item in items:
                    line_cost = Decimal(item.line_cost or 0)
                    if line_cost == MONEY_ZERO and Decimal(item.line_total or 0) > MONEY_ZERO:
                        missing += 1
                    total += line_cost
            else:
                order_cost = Decimal(order.product_cost or 0)
                if order_cost == MONEY_ZERO and Decimal(order.revenue or 0) > MONEY_ZERO:
                    missing += 1
                total += order_cost
        return total, missing

    def _calculate_shipping_cost(self, orders: list[Order], shipments: list[object]) -> tuple[Decimal, int]:
        shipment_costs_by_order: dict[UUID, Decimal] = {}
        for shipment in shipments:
            if shipment.order_id is None:
                continue
            shipment_costs_by_order[shipment.order_id] = shipment_costs_by_order.get(shipment.order_id, MONEY_ZERO) + Decimal(shipment.shipping_cost or 0)
        total = MONEY_ZERO
        missing = 0
        for order in orders:
            if order.id in shipment_costs_by_order:
                total += shipment_costs_by_order[order.id]
                continue
            fallback = Decimal(order.shipping_cost or 0)
            total += fallback
            if fallback == MONEY_ZERO and Decimal(order.revenue or 0) > MONEY_ZERO:
                missing += 1
        return total, missing

    def _sum(self, values) -> Decimal:
        total = MONEY_ZERO
        for value in values:
            total += Decimal(value or 0)
        return self._quantize(total)

    def _divide(self, numerator: Decimal, denominator: Decimal) -> Decimal:
        if denominator == 0:
            return MONEY_ZERO
        return numerator / denominator

    def _quantize(self, value: Decimal) -> Decimal:
        return Decimal(value or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _warning(self, code: str, message: str, message_uk: str) -> FinanceDataQualityWarning:
        return FinanceDataQualityWarning(code=code, message=message, message_uk=message_uk)
