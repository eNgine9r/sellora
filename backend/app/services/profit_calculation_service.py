from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Protocol

from app.models.order import OrderStatus, PaymentStatus


MONEY_ZERO = Decimal("0.00")


class ProfitOrder(Protocol):
    status: str
    payment_status: str
    revenue: Decimal
    product_cost: Decimal
    ad_cost: Decimal
    shipping_cost: Decimal
    cod_fee: Decimal
    other_cost: Decimal


@dataclass(frozen=True)
class ProfitComponents:
    revenue: Decimal
    product_cost: Decimal
    advertising_cost: Decimal
    delivery_cost: Decimal
    payment_fees: Decimal
    other_cost: Decimal
    refunds: Decimal = MONEY_ZERO
    returns: Decimal = MONEY_ZERO

    @property
    def net_profit(self) -> Decimal:
        return ProfitCalculationService.money(
            self.revenue
            - self.product_cost
            - self.advertising_cost
            - self.delivery_cost
            - self.payment_fees
            - self.other_cost
            - self.refunds
            - self.returns
        )


class ProfitCalculationService:
    """Canonical source of truth for order-derived revenue and net profit."""

    REVENUE_STATUSES = frozenset(
        {
            OrderStatus.NEW.value,
            OrderStatus.CONFIRMED.value,
            OrderStatus.SHIPPED.value,
            OrderStatus.DELIVERED.value,
            OrderStatus.COMPLETED.value,
        }
    )

    @staticmethod
    def money(value: Decimal | int | float | None) -> Decimal:
        return Decimal(value or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def includes_order(cls, order: ProfitOrder) -> bool:
        status = order.status or OrderStatus.NEW.value
        payment_status = order.payment_status or PaymentStatus.PENDING.value
        return status in cls.REVENUE_STATUSES and payment_status != PaymentStatus.REFUNDED.value

    @classmethod
    def components(cls, order: ProfitOrder) -> ProfitComponents:
        if not cls.includes_order(order):
            return ProfitComponents(MONEY_ZERO, MONEY_ZERO, MONEY_ZERO, MONEY_ZERO, MONEY_ZERO, MONEY_ZERO)
        return ProfitComponents(
            revenue=cls.money(order.revenue),
            product_cost=cls.money(order.product_cost),
            advertising_cost=cls.money(order.ad_cost),
            delivery_cost=cls.money(order.shipping_cost),
            payment_fees=cls.money(order.cod_fee),
            other_cost=cls.money(order.other_cost),
        )

    @classmethod
    def order_net_profit(cls, order: ProfitOrder) -> Decimal:
        return cls.components(order).net_profit

    @classmethod
    def included_orders(cls, orders: Iterable[ProfitOrder]) -> list[ProfitOrder]:
        return [order for order in orders if cls.includes_order(order)]
