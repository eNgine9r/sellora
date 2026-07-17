from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.customer_address import DeliveryProvider
from app.models.order import OrderStatus, PaymentStatus
from app.models.order_fulfillment import OrderFulfillment, OrderFulfillmentResultCode, OrderFulfillmentState
from app.models.shipment import ShipmentCarrier, ShipmentStatus
from app.repositories.order_fulfillment_repository import OrderFulfillmentRepository
from app.schemas.crm_completion import CustomerAddressCreate, CustomerAddressUpdate
from app.schemas.customer import CustomerCreate
from app.schemas.order import OrderCreate, OrderResponse
from app.schemas.order_fulfillment import OrderFulfillmentCreate, OrderFulfillmentResponse
from app.schemas.shipment import ShipmentCreate
from app.services.crm_completion_service import CustomerCrmService, CrmCompletionServiceError
from app.services.customer_service import CustomerService
from app.services.nova_poshta_provider_service import NovaPoshtaProviderShipmentService
from app.services.nova_poshta_service import NovaPoshtaServiceError
from app.services.order_service import OrderService, OrderServiceError
from app.services.shipment_service import ShipmentService, ShipmentServiceError


class OrderFulfillmentServiceError(ValueError):
    pass


class OrderFulfillmentConflictError(OrderFulfillmentServiceError):
    pass


class OrderFulfillmentValidationError(OrderFulfillmentServiceError):
    pass


class OrderFulfillmentService:
    def __init__(self, db: Session, nova_poshta_service_factory=None) -> None:
        self.db = db
        self.operations = OrderFulfillmentRepository(db)
        self.customers = CustomerService(db)
        self.customer_crm = CustomerCrmService(db)
        self.orders = OrderService(db)
        self.shipments = ShipmentService(db)
        self.nova_poshta_service_factory = nova_poshta_service_factory or NovaPoshtaProviderShipmentService

    def create(self, workspace_id: UUID, payload: OrderFulfillmentCreate, actor_user_id: UUID | None) -> OrderFulfillmentResponse:
        fingerprint = self._fingerprint(payload)
        operation, replay = self._prepare_operation(workspace_id, payload.idempotency_key, fingerprint, actor_user_id)
        completed_result = (
            OrderFulfillmentResultCode(operation.result_code)
            if operation.result_code
            else None
        )
        if (
            completed_result
            and operation.order_id
            and operation.shipment_id
            and (
                completed_result != OrderFulfillmentResultCode.ORDER_CREATED_TTN_PENDING
                or not payload.create_ttn
            )
        ):
            return self._stored_response(workspace_id, operation, idempotent_replay=True)

        if not operation.order_id or not operation.shipment_id:
            operation = self.operations.get_by_key(
                workspace_id,
                payload.idempotency_key,
                for_update=True,
            )
            if operation is None:
                raise OrderFulfillmentServiceError("FULFILLMENT_STATE_LOST")
            replay = replay or bool(operation.order_id or operation.shipment_id)

        if not operation.order_id or not operation.shipment_id:
            try:
                customer_id, address_id = self._create_business_records(workspace_id, payload, actor_user_id, operation)
                operation.customer_id = customer_id
                operation.address_id = address_id
                operation.state = OrderFulfillmentState.SHIPMENT_CREATED.value
                operation.last_error_code = None
                operation.last_error_message = None
                self.db.commit()
            except (OrderServiceError, ShipmentServiceError, CrmCompletionServiceError, ValueError, IntegrityError) as exc:
                self.db.rollback()
                failed = self.operations.get_by_key(workspace_id, payload.idempotency_key, for_update=True)
                if failed is not None and failed.order_id is None:
                    failed.state = OrderFulfillmentState.FAILED_VALIDATION.value
                    failed.last_error_code = "VALIDATION_FAILED"
                    failed.last_error_message = str(exc)
                    self.db.commit()
                raise OrderFulfillmentValidationError(str(exc)) from exc

        operation = self.operations.get_by_key(workspace_id, payload.idempotency_key, for_update=True)
        if operation is None or operation.order_id is None or operation.shipment_id is None:
            raise OrderFulfillmentServiceError("FULFILLMENT_STATE_LOST")

        if not payload.create_ttn:
            return self._complete(
                workspace_id,
                operation,
                OrderFulfillmentResultCode.ORDER_CREATED_TTN_PENDING,
                message="Order and shipment draft created. TTN creation was postponed.",
                retry_available=True,
                replay=replay,
            )

        try:
            ttn = self.nova_poshta_service_factory(self.db).create_ttn(workspace_id, operation.shipment_id, actor_user_id)
        except NovaPoshtaServiceError as exc:
            return self._complete(
                workspace_id,
                operation,
                OrderFulfillmentResultCode.ORDER_CREATED_TTN_PENDING,
                message="Order and shipment were created, but Nova Poshta is not ready.",
                error_code=str(exc),
                retry_available=True,
                replay=replay,
            )

        if ttn.success and ttn.tracking_number:
            operation.tracking_number = ttn.tracking_number
            return self._complete(
                workspace_id,
                operation,
                OrderFulfillmentResultCode.ORDER_AND_TTN_CREATED,
                message="Order, shipment and Nova Poshta TTN created.",
                replay=replay or bool(ttn.reused_existing_result),
            )
        error_code = next(iter(ttn.errors or []), None)
        if ttn.manual_reconciliation_required or (
            ttn.blind_retry_blocked and error_code != "NOVA_POSHTA_PROVIDER_WRITES_DISABLED"
        ):
            return self._complete(
                workspace_id,
                operation,
                OrderFulfillmentResultCode.ORDER_CREATED_PROVIDER_RECONCILIATION_REQUIRED,
                message="Order is safe, but the Nova Poshta document requires reconciliation.",
                error_code=error_code,
                retry_available=False,
                replay=replay,
            )
        return self._complete(
            workspace_id,
            operation,
            OrderFulfillmentResultCode.ORDER_CREATED_TTN_PENDING,
            message="Order and shipment were created. Fix the Nova Poshta data and retry TTN creation.",
            error_code=error_code,
            retry_available=True,
            replay=replay,
        )

    def _prepare_operation(self, workspace_id: UUID, key: str, fingerprint: str, actor_user_id: UUID | None) -> tuple[OrderFulfillment, bool]:
        operation = self.operations.get_by_key(workspace_id, key, for_update=True)
        if operation is not None:
            if operation.request_fingerprint != fingerprint:
                if operation.state == OrderFulfillmentState.FAILED_VALIDATION.value and operation.order_id is None:
                    operation.request_fingerprint = fingerprint
                    operation.state = OrderFulfillmentState.PREPARED.value
                    operation.last_error_code = None
                    operation.last_error_message = None
                    self.db.commit()
                    return operation, False
                raise OrderFulfillmentConflictError("IDEMPOTENCY_KEY_PAYLOAD_MISMATCH")
            return operation, True
        try:
            operation = self.operations.create(
                OrderFulfillment(
                    workspace_id=workspace_id,
                    idempotency_key=key,
                    request_fingerprint=fingerprint,
                    state=OrderFulfillmentState.PREPARED.value,
                    created_by=actor_user_id,
                )
            )
            self.db.commit()
            return operation, False
        except IntegrityError:
            self.db.rollback()
            operation = self.operations.get_by_key(workspace_id, key, for_update=True)
            if operation is None or operation.request_fingerprint != fingerprint:
                raise OrderFulfillmentConflictError("IDEMPOTENCY_KEY_CONFLICT")
            return operation, True

    def _create_business_records(self, workspace_id: UUID, payload: OrderFulfillmentCreate, actor_user_id: UUID | None, operation: OrderFulfillment) -> tuple[UUID, UUID | None]:
        if payload.customer_id:
            customer = self.customers.get(workspace_id, payload.customer_id)
            if customer is None:
                raise OrderFulfillmentValidationError("CUSTOMER_NOT_FOUND")
        else:
            customer = self.customers.create(
                workspace_id,
                CustomerCreate(
                    name=(payload.customer_name or "").strip(),
                    phone=payload.customer_phone or payload.recipient_phone,
                    instagram_username=payload.instagram_username,
                    city=payload.city,
                    region=None,
                ),
                actor_user_id,
                commit=False,
            )

        address_id = None
        if payload.save_address_as_default:
            address_values = dict(
                label="Нова Пошта",
                recipient_name=payload.recipient_name,
                phone=payload.recipient_phone,
                address_line1=payload.warehouse,
                city=payload.city,
                country="Україна",
                is_default=True,
                delivery_provider=DeliveryProvider.NOVA_POSHTA,
                nova_poshta_city_ref=payload.nova_poshta_city_ref,
                nova_poshta_warehouse_ref=payload.nova_poshta_warehouse_ref,
                warehouse_number=payload.warehouse_number,
            )
            addresses = self.customer_crm.list_addresses(workspace_id, customer.id)
            selected = next((item for item in addresses if item.id == payload.address_id), None)
            if payload.address_id and selected is None:
                raise OrderFulfillmentValidationError("CUSTOMER_ADDRESS_NOT_FOUND")
            selected = selected or next((item for item in addresses if item.is_default), None)
            if selected:
                updated = self.customer_crm.update_address(
                    workspace_id,
                    customer.id,
                    selected.id,
                    CustomerAddressUpdate(**address_values),
                    actor_user_id,
                    commit=False,
                )
                address_id = updated.id if updated else None
            else:
                address = self.customer_crm.add_address(
                    workspace_id,
                    customer.id,
                    CustomerAddressCreate(**address_values),
                    actor_user_id,
                    commit=False,
                )
                address_id = address.id

        order = self.orders.create(
            workspace_id,
            OrderCreate(
                customer_id=customer.id,
                campaign_id=payload.campaign_id,
                status=OrderStatus.NEW,
                payment_status=payload.payment_status,
                items=payload.items,
                ad_cost=payload.ad_cost,
                shipping_cost=payload.shipping_cost,
                cod_fee=payload.cod_fee,
                other_cost=payload.other_cost,
                notes=payload.notes,
            ),
            actor_user_id,
            commit=False,
        )
        total = sum((item.unit_price * item.quantity for item in payload.items), Decimal("0"))
        cod_amount = payload.cod_amount if payload.cod_amount is not None else (
            total if payload.payment_status == PaymentStatus.COD else Decimal("0")
        )
        declared_value = payload.declared_value if payload.declared_value is not None else total
        shipment = self.shipments.create(
            workspace_id,
            ShipmentCreate(
                order_id=order.id,
                customer_id=customer.id,
                carrier=ShipmentCarrier.NOVA_POSHTA,
                status=ShipmentStatus.DRAFT,
                recipient_name=payload.recipient_name,
                recipient_phone=payload.recipient_phone,
                city=payload.city,
                warehouse=payload.warehouse,
                shipping_cost=payload.shipping_cost,
                cod_amount=cod_amount,
                declared_value=declared_value,
                notes=payload.notes,
                nova_poshta_city_ref=payload.nova_poshta_city_ref,
                nova_poshta_warehouse_ref=payload.nova_poshta_warehouse_ref,
            ),
            actor_user_id,
            commit=False,
        )
        operation.customer_id = customer.id
        operation.address_id = address_id
        operation.order_id = order.id
        operation.shipment_id = shipment.id
        return customer.id, address_id

    def _complete(self, workspace_id: UUID, operation: OrderFulfillment, result_code: OrderFulfillmentResultCode, *, message: str, error_code: str | None = None, retry_available: bool = False, replay: bool = False) -> OrderFulfillmentResponse:
        operation.result_code = result_code.value
        operation.state = OrderFulfillmentState.COMPLETED.value
        operation.last_error_code = error_code
        operation.last_error_message = message if error_code else None
        self.db.commit()
        return self._stored_response(workspace_id, operation, idempotent_replay=replay, message=message, retry_available=retry_available)

    def _stored_response(self, workspace_id: UUID, operation: OrderFulfillment, *, idempotent_replay: bool, message: str | None = None, retry_available: bool | None = None) -> OrderFulfillmentResponse:
        if not operation.order_id or not operation.shipment_id or not operation.result_code:
            raise OrderFulfillmentServiceError("FULFILLMENT_RESULT_INCOMPLETE")
        order = self.orders.get(workspace_id, operation.order_id)
        shipment = self.shipments.get(workspace_id, operation.shipment_id)
        if order is None or shipment is None:
            raise OrderFulfillmentServiceError("FULFILLMENT_RESULT_NOT_FOUND")
        result_code = OrderFulfillmentResultCode(operation.result_code)
        default_retry = result_code == OrderFulfillmentResultCode.ORDER_CREATED_TTN_PENDING
        return OrderFulfillmentResponse(
            result_code=result_code,
            idempotency_key=operation.idempotency_key,
            idempotent_replay=idempotent_replay,
            order=OrderResponse.model_validate(order, from_attributes=True),
            shipment=shipment,
            tracking_number=operation.tracking_number or shipment.tracking_number or shipment.nova_poshta_document_number,
            provider_error_code=operation.last_error_code,
            retry_available=default_retry if retry_available is None else retry_available,
            message=message or operation.last_error_message or self._default_message(result_code),
        )

    @staticmethod
    def _fingerprint(payload: OrderFulfillmentCreate) -> str:
        body = payload.model_dump(mode="json", exclude={"idempotency_key", "create_ttn"})
        encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _default_message(result_code: OrderFulfillmentResultCode) -> str:
        if result_code == OrderFulfillmentResultCode.ORDER_AND_TTN_CREATED:
            return "Order, shipment and Nova Poshta TTN already exist."
        if result_code == OrderFulfillmentResultCode.ORDER_CREATED_PROVIDER_RECONCILIATION_REQUIRED:
            return "Order is safe, but Nova Poshta reconciliation is required."
        return "Order and shipment already exist; TTN is pending."
