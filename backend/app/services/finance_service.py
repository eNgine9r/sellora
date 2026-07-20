from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.finance_adjustment import FinanceAdjustment, FinanceAdjustmentCategory, FinanceAdjustmentType
from app.models.order import Order, OrderStatus, PaymentStatus
from app.repositories.finance_repository import FinanceRepository
from app.schemas.finance import (
    FinanceAdjustmentCreate,
    FinanceAdjustmentListResponse,
    FinanceAdjustmentResponse,
    FinanceAdjustmentUpdate,
    FinanceBreakdownItem,
    FinanceBreakdownResponse,
    FinanceComparisonMetric,
    FinanceDataQualityWarning,
    FinancePeriod,
    FinancePeriodComparisonResponse,
    FinanceSummaryResponse,
)

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


class FinanceServiceError(ValueError):
    pass


class FinanceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = FinanceRepository(db)

    def summary(self, workspace_id: UUID, date_from: date | None = None, date_to: date | None = None) -> FinanceSummaryResponse:
        start_at, end_at = self._resolve_range(date_from, date_to)
        return self._summary_for_range(workspace_id, start_at, end_at)

    def breakdown(self, workspace_id: UUID, date_from: date | None = None, date_to: date | None = None) -> FinanceBreakdownResponse:
        start_at, end_at = self._resolve_range(date_from, date_to)
        summary = self._summary_for_range(workspace_id, start_at, end_at)
        return FinanceBreakdownResponse(period=summary.period, items=summary.breakdown)

    def trends(self, workspace_id: UUID, date_from: date | None = None, date_to: date | None = None) -> FinancePeriodComparisonResponse:
        start_at, end_at = self._resolve_range(date_from, date_to)
        days = max(1, (end_at.date() - start_at.date()).days + 1)
        previous_end = datetime.combine(start_at.date() - timedelta(days=1), time.max, tzinfo=UTC)
        previous_start = datetime.combine(previous_end.date() - timedelta(days=days - 1), time.min, tzinfo=UTC)
        current = self._summary_for_range(workspace_id, start_at, end_at)
        previous = self._summary_for_range(workspace_id, previous_start, previous_end)
        return FinancePeriodComparisonResponse(
            current_period=current.period,
            previous_period=previous.period,
            revenue_change=self._comparison(current.revenue, previous.revenue),
            gross_profit_change=self._comparison(current.gross_profit, previous.gross_profit),
            net_profit_change=self._comparison(current.net_profit, previous.net_profit),
            orders_count_change=self._comparison(Decimal(current.orders_count), Decimal(previous.orders_count)),
            ad_spend_change=self._comparison(current.ad_spend, previous.ad_spend),
            profit_margin_change=self._comparison(current.profit_margin, previous.profit_margin),
        )

    def list_adjustments(
        self,
        workspace_id: UUID,
        date_from: date | None = None,
        date_to: date | None = None,
        adjustment_type: FinanceAdjustmentType | None = None,
        category: FinanceAdjustmentCategory | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> FinanceAdjustmentListResponse:
        start_at, end_at = self._optional_range(date_from, date_to)
        items, total = self.repository.list_adjustments(
            workspace_id,
            start_at,
            end_at,
            adjustment_type.value if adjustment_type else None,
            category.value if category else None,
            limit,
            offset,
        )
        return FinanceAdjustmentListResponse(items=[FinanceAdjustmentResponse.model_validate(item) for item in items], total=total, limit=limit, offset=offset)

    def create_adjustment(self, workspace_id: UUID, payload: FinanceAdjustmentCreate, actor_user_id: UUID | None) -> FinanceAdjustmentResponse:
        self._validate_order_scope(workspace_id, payload.order_id)
        adjustment = FinanceAdjustment(
            workspace_id=workspace_id,
            type=payload.type.value,
            category=payload.category.value,
            amount=payload.amount,
            currency=payload.currency.upper(),
            occurred_at=payload.occurred_at,
            title=payload.title,
            description=payload.description,
            order_id=payload.order_id,
            created_by_user_id=actor_user_id,
        )
        self.repository.create_adjustment(adjustment)
        self.db.commit()
        self.db.refresh(adjustment)
        return FinanceAdjustmentResponse.model_validate(adjustment)

    def update_adjustment(self, workspace_id: UUID, adjustment_id: UUID, payload: FinanceAdjustmentUpdate) -> FinanceAdjustmentResponse:
        adjustment = self._get_adjustment(workspace_id, adjustment_id)
        values = payload.model_dump(exclude_unset=True)
        if "order_id" in values:
            self._validate_order_scope(workspace_id, values["order_id"])
        for field, value in values.items():
            if field in {"type", "category"} and value is not None:
                value = value.value
            if field == "currency" and value is not None:
                value = value.upper()
            setattr(adjustment, field, value)
        self.db.commit()
        self.db.refresh(adjustment)
        return FinanceAdjustmentResponse.model_validate(adjustment)

    def delete_adjustment(self, workspace_id: UUID, adjustment_id: UUID, actor_user_id: UUID | None) -> None:
        adjustment = self._get_adjustment(workspace_id, adjustment_id)
        adjustment.deleted_at = datetime.now(UTC)
        adjustment.deleted_by = actor_user_id
        self.db.commit()

    def _get_adjustment(self, workspace_id: UUID, adjustment_id: UUID) -> FinanceAdjustment:
        adjustment = self.repository.get_adjustment(workspace_id, adjustment_id)
        if adjustment is None:
            raise FinanceServiceError("Finance adjustment not found")
        return adjustment

    def _validate_order_scope(self, workspace_id: UUID, order_id: UUID | None) -> None:
        if order_id is None:
            return
        if not self.repository.order_exists(workspace_id, order_id):
            raise FinanceServiceError("Order not found in workspace")

    def _summary_for_range(self, workspace_id: UUID, start_at: datetime, end_at: datetime) -> FinanceSummaryResponse:
        orders = self.repository.list_orders(workspace_id, start_at, end_at)
        shipments = self.repository.list_shipments(workspace_id, start_at, end_at)
        ad_metrics = self.repository.list_manual_ad_metrics(workspace_id, start_at, end_at)
        adjustments = self.repository.list_adjustments_for_period(workspace_id, start_at, end_at)

        warnings: list[FinanceDataQualityWarning] = [
            self._warning(
                "finance_uses_order_allocated_costs",
                "Finance net profit uses costs allocated to orders. Campaign spend in Advertising is a separate source and may differ until all spend is allocated.",
                "Чистий прибуток у Finance використовує витрати, розподілені на замовлення. Витрати кампаній у Advertising є окремим джерелом і можуть відрізнятися, доки всі витрати не розподілено.",
            ),
            self._warning(
                "meta_ads_not_active",
                "Meta Ads API is not active and is not used for finance metrics.",
                "Meta Ads API не активний і не використовується для фінансових метрик.",
            ),
            self._warning(
                "manual_adjustments_may_be_incomplete",
                "Manual finance adjustments may be incomplete until the owner records expenses, refunds, discounts, and fees.",
                "Ручні фінансові коригування можуть бути неповними, доки власник не внесе витрати, повернення, знижки та комісії.",
            ),
        ]

        valid_orders = [order for order in orders if self._is_valid_revenue_order(order)]
        excluded_orders = [order for order in orders if self._is_excluded_order(order)]
        if not valid_orders:
            warnings.append(self._warning("no_orders_in_period", "No valid orders were found for the selected period.", "За вибраний період не знайдено валідних замовлень."))

        revenue = self._sum(order.revenue for order in valid_orders)
        cogs, missing_cost_count = self._calculate_cogs(valid_orders)
        if missing_cost_count:
            warnings.append(self._warning("missing_product_cost", f"Product cost is missing for {missing_cost_count} order item(s), so COGS may be understated.", f"Для {missing_cost_count} позицій замовлень відсутня собівартість, тому COGS може бути заниженим."))

        ad_spend = self._sum(getattr(order, "ad_cost", MONEY_ZERO) for order in valid_orders)
        reported_campaign_spend = self._sum(metric.spend for metric in ad_metrics)
        if reported_campaign_spend != ad_spend:
            warnings.append(
                self._warning(
                    "campaign_spend_not_fully_allocated",
                    f"Advertising reports contain {reported_campaign_spend} of campaign spend, while {ad_spend} is allocated to orders and used in Finance net profit.",
                    f"Звіти Advertising містять {reported_campaign_spend} витрат кампаній, тоді як {ad_spend} розподілено на замовлення та використано в чистому прибутку Finance.",
                )
            )

        shipping_cost = self._sum(getattr(order, "shipping_cost", MONEY_ZERO) for order in valid_orders)
        provider_shipping_cost, missing_shipping_count = self._calculate_shipping_cost(valid_orders, shipments)
        if provider_shipping_cost != shipping_cost:
            warnings.append(
                self._warning(
                    "shipment_cost_differs_from_order_allocation",
                    f"Shipment records contain {provider_shipping_cost} of delivery cost, while {shipping_cost} is allocated to orders and used in the canonical net-profit formula.",
                    f"У записах відправлень міститься {provider_shipping_cost} вартості доставки, тоді як {shipping_cost} розподілено на замовлення та використано в канонічній формулі чистого прибутку.",
                )
            )
        manual_shipping_adjustments = self._sum(adjustment.amount for adjustment in adjustments if adjustment.type == FinanceAdjustmentType.SHIPPING_ADJUSTMENT.value)
        shipping_cost += manual_shipping_adjustments
        if missing_shipping_count:
            warnings.append(self._warning("missing_shipment_cost", f"Shipping cost is missing for {missing_shipping_count} order(s), so delivery expenses may be understated.", f"Для {missing_shipping_count} замовлень відсутня вартість доставки, тому витрати на доставку можуть бути занижені."))

        discounts = MONEY_ZERO
        refunds = MONEY_ZERO
        if excluded_orders:
            warnings.append(self._warning("cancelled_refunded_orders_excluded", "Cancelled, returned, and refunded orders are excluded from revenue; add a manual REFUND adjustment only when money was actually returned and must reduce profit.", "Скасовані, повернені та відшкодовані замовлення виключені з доходу; додавайте ручне REFUND-коригування лише коли кошти реально повернені й мають зменшити прибуток."))
        cod_fees = self._sum(getattr(order, "cod_fee", MONEY_ZERO) for order in valid_orders)
        order_other_costs = self._sum(getattr(order, "other_cost", MONEY_ZERO) for order in valid_orders)
        other_expenses = cod_fees + order_other_costs

        manual_expenses = self._sum(adjustment.amount for adjustment in adjustments if adjustment.type in {FinanceAdjustmentType.EXPENSE.value, FinanceAdjustmentType.OTHER.value, FinanceAdjustmentType.CORRECTION.value})
        manual_refunds = self._sum(adjustment.amount for adjustment in adjustments if adjustment.type == FinanceAdjustmentType.REFUND.value)
        manual_discounts = self._sum(adjustment.amount for adjustment in adjustments if adjustment.type == FinanceAdjustmentType.DISCOUNT.value)
        manual_fees = self._sum(adjustment.amount for adjustment in adjustments if adjustment.type == FinanceAdjustmentType.FEE.value)
        if not any(adjustment.type in {FinanceAdjustmentType.REFUND.value, FinanceAdjustmentType.DISCOUNT.value} for adjustment in adjustments):
            warnings.append(self._warning("refunds_discounts_manual", "Refunds and discounts are manual adjustments until dedicated refund/discount workflows exist.", "Повернення та знижки є ручними коригуваннями, доки немає окремих workflows для повернень і знижок."))

        finance_adjustments_total = manual_expenses + manual_refunds + manual_discounts + manual_fees + manual_shipping_adjustments
        gross_profit = revenue - cogs
        net_profit = revenue - cogs - ad_spend - shipping_cost - discounts - refunds - other_expenses - manual_expenses - manual_refunds - manual_discounts - manual_fees
        orders_count = len(valid_orders)
        paid_orders_count = sum(1 for order in valid_orders if order.payment_status in PAID_PAYMENT_STATUSES)
        average_denominator = paid_orders_count or orders_count
        average_order_value = self._divide(revenue, Decimal(average_denominator)) if average_denominator else None
        profit_margin = self._divide(net_profit, revenue) * Decimal("100") if revenue else None

        summary = FinanceSummaryResponse(
            period=FinancePeriod(date_from=start_at.date(), date_to=end_at.date()),
            revenue=self._quantize(revenue),
            cogs=self._quantize(cogs),
            gross_profit=self._quantize(gross_profit),
            ad_spend=self._quantize(ad_spend),
            shipping_cost=self._quantize(shipping_cost),
            discounts=self._quantize(discounts),
            refunds=self._quantize(refunds),
            other_expenses=self._quantize(other_expenses),
            manual_expenses=self._quantize(manual_expenses),
            manual_refunds=self._quantize(manual_refunds),
            manual_discounts=self._quantize(manual_discounts),
            manual_fees=self._quantize(manual_fees),
            finance_adjustments_total=self._quantize(finance_adjustments_total),
            net_profit=self._quantize(net_profit),
            profit_margin=self._quantize(profit_margin) if profit_margin is not None else None,
            orders_count=orders_count,
            paid_orders_count=paid_orders_count,
            average_order_value=self._quantize(average_order_value) if average_order_value is not None else None,
            data_quality_warnings=warnings,
        )
        summary.breakdown = self._breakdown_items(summary)
        return summary

    def _breakdown_items(self, summary: FinanceSummaryResponse) -> list[FinanceBreakdownItem]:
        return [
            self._breakdown_item("revenue", "Revenue", summary.revenue, "income", summary.revenue),
            self._breakdown_item("cogs", "COGS", summary.cogs, "expense", summary.revenue),
            self._breakdown_item("ad_spend", "Allocated ad cost", summary.ad_spend, "expense", summary.revenue),
            self._breakdown_item("shipping_cost", "Shipping cost", summary.shipping_cost, "expense", summary.revenue),
            self._breakdown_item("other_expenses", "COD and other order costs", summary.other_expenses, "expense", summary.revenue),
            self._breakdown_item("manual_expenses", "Manual expenses", summary.manual_expenses, "expense", summary.revenue),
            self._breakdown_item("manual_refunds", "Manual refunds", summary.manual_refunds, "expense", summary.revenue),
            self._breakdown_item("manual_discounts", "Manual discounts", summary.manual_discounts, "expense", summary.revenue),
            self._breakdown_item("manual_fees", "Manual fees", summary.manual_fees, "expense", summary.revenue),
            self._breakdown_item("net_profit", "Net profit", summary.net_profit, "result", summary.revenue),
        ]

    def _breakdown_item(self, key: str, label: str, amount: Decimal, direction: str, revenue: Decimal) -> FinanceBreakdownItem:
        share = self._divide(amount, revenue) * Decimal("100") if revenue else None
        return FinanceBreakdownItem(key=key, label=label, amount=self._quantize(amount), direction=direction, share_of_revenue=self._quantize(share) if share is not None else None)

    def _comparison(self, current: Decimal | int | None, previous: Decimal | int | None) -> FinanceComparisonMetric:
        current_decimal = Decimal(current) if current is not None else None
        previous_decimal = Decimal(previous) if previous is not None else None
        if current_decimal is None or previous_decimal is None:
            return FinanceComparisonMetric(current=current, previous=previous, change=None, change_percent=None)
        change = current_decimal - previous_decimal
        change_percent = self._divide(change, previous_decimal) * Decimal("100") if previous_decimal else None
        return FinanceComparisonMetric(current=self._quantize(current_decimal), previous=self._quantize(previous_decimal), change=self._quantize(change), change_percent=self._quantize(change_percent) if change_percent is not None else None)

    def _resolve_range(self, date_from: date | None, date_to: date | None) -> tuple[datetime, datetime]:
        today = datetime.now(UTC).date()
        resolved_to = date_to or today
        resolved_from = date_from or (resolved_to - timedelta(days=30))
        self._validate_date_order(resolved_from, resolved_to)
        return datetime.combine(resolved_from, time.min, tzinfo=UTC), datetime.combine(resolved_to, time.max, tzinfo=UTC)

    def _optional_range(self, date_from: date | None, date_to: date | None) -> tuple[datetime | None, datetime | None]:
        if date_from is not None and date_to is not None:
            self._validate_date_order(date_from, date_to)
        start_at = datetime.combine(date_from, time.min, tzinfo=UTC) if date_from else None
        end_at = datetime.combine(date_to, time.max, tzinfo=UTC) if date_to else None
        return start_at, end_at

    def _validate_date_order(self, date_from: date, date_to: date) -> None:
        if date_from > date_to:
            raise FinanceServiceError("date_from must be before or equal to date_to")

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
