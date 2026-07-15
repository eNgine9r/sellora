from __future__ import annotations

from datetime import UTC, datetime
from inspect import signature
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.order import OrderStatus
from app.models.shipment import Shipment, ShipmentStatus
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.shipment_repository import ShipmentRepository
from app.schemas.order import OrderStatusUpdate
from app.schemas.shipment import ShipmentCreate, ShipmentResponse, ShipmentSummaryResponse, ShipmentUpdate
from app.services.business_utils import snapshot
from app.services.order_service import OrderService, OrderServiceError


class ShipmentServiceError(ValueError):
    pass


class ShipmentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.shipments = ShipmentRepository(db)
        self.orders = OrderRepository(db)
        self.audit_logs = AuditLogRepository(db)
        self.order_service = OrderService(db)

    def _get_shipment_for_update(self, workspace_id: UUID, shipment_id: UUID) -> Shipment | None:
        getter = getattr(self.shipments, "get_for_update", None)
        return getter(workspace_id, shipment_id) if getter else self.shipments.get(workspace_id, shipment_id)

    def _get_order_for_update(self, workspace_id: UUID, order_id: UUID):
        getter = getattr(self.orders, "get_for_update", None)
        return getter(workspace_id, order_id) if getter else self.orders.get(workspace_id, order_id)

    def _change_order_status(self, workspace_id: UUID, order_id: UUID, status: OrderStatus, note: str, actor_user_id: UUID | None):
        method = self.order_service.change_status
        payload = OrderStatusUpdate(status=status, note=note)
        if "commit" in signature(method).parameters:
            return method(workspace_id, order_id, payload, actor_user_id, commit=False)
        return method(workspace_id, order_id, payload, actor_user_id)

    def list(self, workspace_id: UUID, status: ShipmentStatus | None = None, search: str | None = None) -> list[ShipmentResponse]:
        return [self._response(shipment) for shipment in self.shipments.list_for_workspace(workspace_id, status.value if status else None, search)]

    def get(self, workspace_id: UUID, shipment_id: UUID) -> ShipmentResponse | None:
        shipment = self.shipments.get(workspace_id, shipment_id)
        return self._response(shipment) if shipment else None

    def get_for_order(self, workspace_id: UUID, order_id: UUID) -> ShipmentResponse | None:
        if self.orders.get(workspace_id, order_id) is None:
            raise ShipmentServiceError("Order not found")
        shipment = self.shipments.get_by_order(workspace_id, order_id)
        return self._response(shipment) if shipment else None

    def create(self, workspace_id: UUID, payload: ShipmentCreate, actor_user_id: UUID | None) -> ShipmentResponse:
        order = self._get_order_for_update(workspace_id, payload.order_id)
        if order is None:
            raise ShipmentServiceError("Order not found in this workspace")
        if OrderStatus(order.status) in {OrderStatus.CANCELLED, OrderStatus.RETURNED}:
            raise ShipmentServiceError("Cannot create shipment for cancelled or returned order")
        customer_id = self._validated_customer_id(workspace_id, payload.customer_id, order.customer_id)
        self._validate_tracking(workspace_id, payload.tracking_number, payload.status)
        if self.shipments.find_active_by_order(workspace_id, payload.order_id):
            raise ShipmentServiceError("Active shipment already exists for this order")
        shipment = self.shipments.create(
            Shipment(
                workspace_id=workspace_id,
                order_id=payload.order_id,
                customer_id=customer_id,
                tracking_number=payload.tracking_number,
                carrier=payload.carrier.value,
                status=payload.status.value,
                recipient_name=payload.recipient_name,
                recipient_phone=payload.recipient_phone,
                city=payload.city,
                warehouse=payload.warehouse,
                shipping_cost=payload.shipping_cost,
                cod_amount=payload.cod_amount,
                declared_value=payload.declared_value,
                notes=payload.notes,
                nova_poshta_city_ref=payload.nova_poshta_city_ref,
                nova_poshta_warehouse_ref=payload.nova_poshta_warehouse_ref,
            )
        )
        self._stamp_status(shipment, payload.status)
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="Shipment", entity_id=shipment.id, action="SHIPMENT_CREATE", new_value=snapshot(shipment))
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ShipmentServiceError("Active shipment or tracking number already exists in this workspace") from exc
        self.db.refresh(shipment)
        return self._response(self.shipments.get(workspace_id, shipment.id) or shipment)

    def update(self, workspace_id: UUID, shipment_id: UUID, payload: ShipmentUpdate, actor_user_id: UUID | None) -> ShipmentResponse | None:
        shipment = self._get_shipment_for_update(workspace_id, shipment_id)
        if shipment is None:
            return None
        old_value = snapshot(shipment)
        changes = payload.model_dump(exclude_unset=True)
        if "customer_id" in changes:
            order = self._get_order_for_update(workspace_id, shipment.order_id)
            if order is None:
                raise ShipmentServiceError("Order not found in this workspace")
            changes["customer_id"] = self._validated_customer_id(workspace_id, changes.get("customer_id"), order.customer_id)
        next_status = ShipmentStatus(changes.get("status", shipment.status))
        next_tracking = changes.get("tracking_number", shipment.tracking_number)
        self._validate_tracking(workspace_id, next_tracking, next_status, shipment.id)
        if self.shipments.find_active_by_order(workspace_id, shipment.order_id, shipment.id):
            raise ShipmentServiceError("Active shipment already exists for this order")
        for field, value in changes.items():
            setattr(shipment, field, value.value if hasattr(value, "value") else value)
        self._stamp_status(shipment, ShipmentStatus(shipment.status))
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="Shipment", entity_id=shipment.id, action="SHIPMENT_UPDATE", old_value=old_value, new_value=snapshot(shipment))
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ShipmentServiceError("Active shipment or tracking number already exists in this workspace") from exc
        self.db.refresh(shipment)
        return self._response(shipment)

    def delete(self, workspace_id: UUID, shipment_id: UUID, actor_user_id: UUID | None) -> bool:
        shipment = self._get_shipment_for_update(workspace_id, shipment_id)
        if shipment is None:
            return False
        old_value = snapshot(shipment)
        shipment.deleted_at = datetime.now(UTC)
        shipment.deleted_by = actor_user_id
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="Shipment", entity_id=shipment.id, action="SHIPMENT_DELETE", old_value=old_value, new_value=snapshot(shipment))
        self.db.commit()
        return True

    def change_status(self, workspace_id: UUID, shipment_id: UUID, status: ShipmentStatus, actor_user_id: UUID | None) -> ShipmentResponse | None:
        shipment = self._get_shipment_for_update(workspace_id, shipment_id)
        if shipment is None:
            return None
        self._validate_tracking(workspace_id, shipment.tracking_number, status, shipment.id)
        old_value = snapshot(shipment)
        old_status = ShipmentStatus(shipment.status)
        if old_status == status:
            return self._response(shipment)

        shipment.status = status.value
        self._stamp_status(shipment, status)
        self._apply_order_transition(workspace_id, shipment, status, actor_user_id)
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="Shipment", entity_id=shipment.id, action="SHIPMENT_STATUS_CHANGE", old_value=old_value, new_value=snapshot(shipment))
        if status == ShipmentStatus.DELIVERED:
            self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="Shipment", entity_id=shipment.id, action="SHIPMENT_DELIVERED", new_value={"status": status.value})
        if status == ShipmentStatus.RETURNED:
            self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="Shipment", entity_id=shipment.id, action="SHIPMENT_RETURNED", new_value={"status": status.value})
        self.db.commit()
        self.db.refresh(shipment)
        return self._response(self.shipments.get(workspace_id, shipment.id) or shipment)

    def summary(self, workspace_id: UUID) -> ShipmentSummaryResponse:
        in_transit, arrived, delivered_today, returned_this_month = self.shipments.summary_counts(workspace_id)
        return ShipmentSummaryResponse(in_transit_count=in_transit, arrived_count=arrived, delivered_today=delivered_today, returned_this_month=returned_this_month)

    def _validated_customer_id(self, workspace_id: UUID, customer_id: UUID | None, order_customer_id: UUID | None) -> UUID:
        selected_customer_id = customer_id or order_customer_id
        if selected_customer_id is None:
            raise ShipmentServiceError("Cannot create shipment: order does not have a customer. Select a customer on the order and try again.")
        if order_customer_id is not None and selected_customer_id != order_customer_id:
            raise ShipmentServiceError("Shipment customer must match the order customer")
        customer = self.db.get(Customer, selected_customer_id)
        if customer is None or customer.workspace_id != workspace_id or customer.deleted_at is not None:
            raise ShipmentServiceError("Customer not found in this workspace")
        return selected_customer_id

    def _validate_tracking(self, workspace_id: UUID, tracking_number: str | None, status: ShipmentStatus, shipment_id: UUID | None = None) -> None:
        if status != ShipmentStatus.DRAFT and not tracking_number:
            raise ShipmentServiceError("tracking_number is required for non-draft shipments")
        if self.shipments.find_by_tracking_number(workspace_id, tracking_number, shipment_id):
            raise ShipmentServiceError("tracking_number already exists in this workspace")

    def _stamp_status(self, shipment: Shipment, status: ShipmentStatus) -> None:
        now = datetime.now(UTC)
        if status == ShipmentStatus.IN_TRANSIT and shipment.shipped_at is None:
            shipment.shipped_at = now
        if status == ShipmentStatus.DELIVERED and shipment.delivered_at is None:
            shipment.delivered_at = now
        if status == ShipmentStatus.RETURNED and shipment.returned_at is None:
            shipment.returned_at = now

    def _apply_order_transition(self, workspace_id: UUID, shipment: Shipment, status: ShipmentStatus, actor_user_id: UUID | None) -> None:
        order = self._get_order_for_update(workspace_id, shipment.order_id)
        if order is None:
            raise ShipmentServiceError("Order not found in this workspace")
        try:
            current_status = OrderStatus(order.status)
            if status == ShipmentStatus.IN_TRANSIT and current_status in {OrderStatus.NEW, OrderStatus.CONFIRMED}:
                self._change_order_status(workspace_id, order.id, OrderStatus.SHIPPED, "Shipment marked in transit", actor_user_id)
            elif status == ShipmentStatus.DELIVERED:
                if current_status in {OrderStatus.NEW, OrderStatus.CONFIRMED}:
                    self._change_order_status(workspace_id, order.id, OrderStatus.SHIPPED, "Shipment delivered after transit", actor_user_id)
                    current_status = OrderStatus.SHIPPED
                if current_status == OrderStatus.SHIPPED:
                    self._change_order_status(workspace_id, order.id, OrderStatus.DELIVERED, "Shipment delivered", actor_user_id)
            elif status == ShipmentStatus.RETURNED:
                if current_status in {OrderStatus.NEW, OrderStatus.CONFIRMED}:
                    self._change_order_status(workspace_id, order.id, OrderStatus.SHIPPED, "Shipment returned after transit", actor_user_id)
                    current_status = OrderStatus.SHIPPED
                if current_status in {OrderStatus.SHIPPED, OrderStatus.DELIVERED, OrderStatus.COMPLETED}:
                    self._change_order_status(workspace_id, order.id, OrderStatus.RETURNED, "Shipment returned", actor_user_id)
        except OrderServiceError as exc:
            raise ShipmentServiceError(str(exc)) from exc

    def _response(self, shipment: Shipment) -> ShipmentResponse:
        if shipment.nova_poshta_manual_reconciliation_required is None:
            shipment.nova_poshta_manual_reconciliation_required = False
        return ShipmentResponse.model_validate(shipment, from_attributes=True).model_copy(update={
            "order_number": shipment.order.order_number if shipment.order else None,
            "order_status": shipment.order.status if shipment.order else None,
            "order_payment_status": shipment.order.payment_status if shipment.order else None,
            "order_total": shipment.order.revenue if shipment.order else None,
            "customer_name": shipment.customer.name if shipment.customer else None,
            "customer_phone": shipment.customer.phone if shipment.customer else None,
            "customer_instagram_username": shipment.customer.instagram_username if shipment.customer else None,
        })
