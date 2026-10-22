from __future__ import annotations

from uuid import UUID
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.order import Order, OrderStatus, PaymentStatus
from app.models.shipment import Shipment
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate
from app.services.business_utils import snapshot


class CustomerService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.customers = CustomerRepository(db)
        self.audit_logs = AuditLogRepository(db)

    def list(self, workspace_id: UUID, search: str | None = None) -> list[CustomerResponse]:
        customers = self.customers.list_for_workspace(workspace_id, search)
        return self._with_order_metrics(workspace_id, customers)

    def get(self, workspace_id: UUID, customer_id: UUID) -> Customer | None:
        return self.customers.get(workspace_id, customer_id)

    def get_with_metrics(self, workspace_id: UUID, customer_id: UUID) -> CustomerResponse | None:
        customer = self.get(workspace_id, customer_id)
        return self._with_order_metrics(workspace_id, [customer])[0] if customer else None

    def _with_order_metrics(self, workspace_id: UUID, customers: list[Customer]) -> list[CustomerResponse]:
        if not customers:
            return []
        customer_ids = [customer.id for customer in customers]
        # One scoped bulk query; no N+1 and no mutation of persisted counters.
        rows = self.db.execute(
            select(
                Order.customer_id, Order.order_number, Order.status, Order.payment_status,
                Order.revenue, Order.is_historical, Order.created_at, Order.id,
            ).where(
                Order.workspace_id == workspace_id,
                Order.customer_id.in_(customer_ids),
                Order.deleted_at.is_(None),
            ).order_by(Order.created_at.desc(), Order.id.desc())
        ).all()
        metrics = defaultdict(lambda: {
            "total_orders": 0, "paid_orders": 0,
            "total_spent": Decimal("0.00"), "unpriced_orders": 0,
            "last_order_at": None, "last_order_number": None,
            "last_order_status": None, "last_order_payment_status": None,
        })
        for customer_id, order_number, status, payment_status, revenue, historical, created_at, _order_id in rows:
            summary = metrics[customer_id]
            summary["total_orders"] += 1
            # Only explicitly PAID and non-returned/non-cancelled orders are
            # counted as paid purchases; delivery and COD alone prove no payment.
            if payment_status == PaymentStatus.PAID.value and status not in (OrderStatus.CANCELLED.value, OrderStatus.RETURNED.value):
                summary["paid_orders"] += 1
                summary["total_spent"] += revenue or Decimal("0.00")
            if historical and (revenue is None or revenue == 0):
                summary["unpriced_orders"] += 1
            if summary["last_order_at"] is None:
                summary["last_order_at"] = created_at
                summary["last_order_number"] = order_number
                summary["last_order_status"] = status
                summary["last_order_payment_status"] = payment_status
        return [
            CustomerResponse.model_validate(customer).model_copy(update=metrics[customer.id])
            for customer in customers
        ]

    def list_orders(self, workspace_id: UUID, customer_id: UUID) -> list[dict]:
        if self.customers.get(workspace_id, customer_id) is None:
            return []
        orders = list(self.db.scalars(
            select(Order).where(
                Order.workspace_id == workspace_id,
                Order.customer_id == customer_id,
                Order.deleted_at.is_(None),
            ).options(selectinload(Order.items)).order_by(Order.created_at.desc(), Order.id.desc()).limit(100)
        ))
        if not orders:
            return []
        by_order: dict[UUID, Shipment] = {}
        for shipment in self.db.scalars(
            select(Shipment).where(
                Shipment.workspace_id == workspace_id,
                Shipment.order_id.in_([order.id for order in orders]),
                Shipment.deleted_at.is_(None),
            ).order_by(Shipment.created_at.desc())
        ):
            by_order.setdefault(shipment.order_id, shipment)
        return [{
            "id": order.id,
            "order_number": order.order_number,
            "status": order.status,
            "payment_status": order.payment_status,
            "is_historical": order.is_historical,
            "revenue": order.revenue,
            "created_at": order.created_at,
            "shipment_tracking": by_order[order.id].tracking_number if order.id in by_order else None,
            "shipment_status": by_order[order.id].status if order.id in by_order else None,
            "shipment_city": by_order[order.id].city if order.id in by_order else None,
            "products": [{"name": item.product_name, "quantity": item.quantity} for item in order.items],
        } for order in orders]

    def create(self, workspace_id: UUID, payload: CustomerCreate, actor_user_id: UUID | None, *, commit: bool = True) -> Customer:
        customer = self.customers.create(Customer(workspace_id=workspace_id, **payload.model_dump()))
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="Customer",
            entity_id=customer.id,
            action="CREATE",
            new_value=snapshot(customer),
        )
        if commit:
            self.db.commit()
            self.db.refresh(customer)
        else:
            self.db.flush()
        return customer

    def update(self, workspace_id: UUID, customer_id: UUID, payload: CustomerUpdate, actor_user_id: UUID | None) -> Customer | None:
        customer = self.get(workspace_id, customer_id)
        if customer is None:
            return None
        old_value = snapshot(customer)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(customer, field, value)
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="Customer",
            entity_id=customer.id,
            action="CUSTOMER_UPDATE",
            old_value=old_value,
            new_value=snapshot(customer),
        )
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def delete(self, workspace_id: UUID, customer_id: UUID, actor_user_id: UUID | None) -> bool:
        customer = self.get(workspace_id, customer_id)
        if customer is None:
            return False
        old_value = snapshot(customer)
        self.customers.soft_delete(customer, actor_user_id)
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="Customer",
            entity_id=customer.id,
            action="CUSTOMER_ARCHIVE",
            old_value=old_value,
            new_value=snapshot(customer),
        )
        self.db.commit()
        return True
