from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.customer_address import DeliveryProvider
from app.models.order import OrderStatus, PaymentStatus
from app.models.order_fulfillment import OrderFulfillment, OrderFulfillmentResultCode, OrderFulfillmentState
from app.models.order_fulfillment_operation import OrderFulfillmentOperation, OrderFulfillmentOperationState, OrderFulfillmentOperationType
from app.models.shipment import ShipmentCarrier, ShipmentStatus
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.order_fulfillment_operation_repository import OrderFulfillmentOperationRepository
from app.repositories.order_fulfillment_repository import OrderFulfillmentRepository
from app.schemas.crm_completion import CustomerAddressCreate, CustomerAddressUpdate
from app.schemas.customer import CustomerCreate
from app.schemas.order import OrderCreate, OrderResponse
from app.schemas.order_fulfillment import OrderFulfillmentCreate, OrderFulfillmentResponse
from app.schemas.order_fulfillment_operation import FulfillmentExecuteRequest, FulfillmentExecuteResponse, FulfillmentPrepareResponse, FulfillmentRequest, FulfillmentStatusResponse
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
        self.operation_journal = OrderFulfillmentOperationRepository(db)
        self.inventory = InventoryRepository(db)
        self.customers = CustomerService(db)
        self.customer_crm = CustomerCrmService(db)
        self.orders = OrderService(db)
        self.shipments = ShipmentService(db)
        self.nova_poshta_service_factory = nova_poshta_service_factory or NovaPoshtaProviderShipmentService


    def prepare_fulfillment(self, workspace_id: UUID, order_id: UUID, payload: FulfillmentRequest) -> FulfillmentPrepareResponse:
        order = self.orders.get(workspace_id, order_id)
        blockers: list[str] = []
        warnings: list[str] = []
        if order is None:
            blockers.append("ORDER_NOT_FOUND")
            return FulfillmentPrepareResponse(ready=False, blockers=blockers, inventory={}, provider_readiness={}, finance_preview={})
        if OrderStatus(order.status) in {OrderStatus.CANCELLED, OrderStatus.RETURNED}:
            blockers.append("ORDER_NOT_FULFILLABLE")
        if not order.items:
            blockers.append("ORDER_HAS_NO_ITEMS")
        if payload.customer_id and order.customer_id and payload.customer_id != order.customer_id:
            blockers.append("CUSTOMER_DOES_NOT_MATCH_ORDER")
        inventory_rows = self.inventory.list_by_variants(workspace_id, [item.product_variant_id for item in order.items])
        inventory_by_variant = {row.product_variant_id: row for row in inventory_rows}
        item_summaries = []
        for item in sorted(order.items, key=lambda row: str(row.product_variant_id)):
            row = inventory_by_variant.get(item.product_variant_id)
            available = None if row is None else row.stock_quantity - row.reserved_quantity
            if row is None:
                blockers.append("INVENTORY_NOT_FOUND")
            elif available < 0:
                blockers.append("INVENTORY_NEGATIVE_AVAILABLE")
            item_summaries.append({"product_variant_id": str(item.product_variant_id), "quantity": item.quantity, "available_quantity": available, "reserved_quantity": row.reserved_quantity if row else None})
        if not payload.delivery.city_ref or not payload.delivery.warehouse_ref:
            blockers.append("DESTINATION_NOT_VERIFIED")
        if payload.payment.cod_amount > order.revenue - payload.payment.already_paid:
            blockers.append("COD_AMOUNT_EXCEEDS_PAYABLE")
        existing = self.operation_journal.get_active_for_order(workspace_id, order_id)
        if existing:
            warnings.append("ACTIVE_FULFILLMENT_OPERATION_EXISTS")
        return FulfillmentPrepareResponse(
            ready=not blockers,
            blockers=sorted(set(blockers)),
            warnings=warnings,
            inventory={"items": item_summaries},
            provider_readiness={"provider": payload.delivery.provider.value, "destination_verified": bool(payload.delivery.city_ref and payload.delivery.warehouse_ref)},
            finance_preview={"order_total": str(order.revenue), "already_paid": str(payload.payment.already_paid), "cod_amount": str(payload.payment.cod_amount), "recognized_revenue": "0"},
            existing_operation={"operation_id": str(existing.id), "state": existing.state} if existing else None,
        )

    def execute_fulfillment(self, workspace_id: UUID, order_id: UUID, payload: FulfillmentExecuteRequest, idempotency_key: str, actor_user_id: UUID | None) -> FulfillmentExecuteResponse:
        fingerprint = self._operation_fingerprint(workspace_id, order_id, payload)
        operation = self.operation_journal.get_by_key(workspace_id, idempotency_key, for_update=True)
        reused = operation is not None
        if operation and operation.request_fingerprint != fingerprint:
            raise OrderFulfillmentConflictError("IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_REQUEST")
        if operation and operation.state == OrderFulfillmentOperationState.COMPLETED.value:
            return self._operation_response(operation, True, "Fulfillment result already exists.")
        completed = self.operation_journal.get_completed_by_fingerprint(workspace_id, order_id, fingerprint)
        if completed is not None:
            return self._operation_response(completed, True, "Fulfillment result already exists for this request.")
        active = self.operation_journal.get_active_for_order(workspace_id, order_id, for_update=True)
        if active is not None and (operation is None or active.id != operation.id):
            raise OrderFulfillmentConflictError("ACTIVE_FULFILLMENT_OPERATION_EXISTS")
        order = self.orders.orders.get_for_update(workspace_id, order_id)
        if order is None:
            raise OrderFulfillmentValidationError("ORDER_NOT_FOUND")
        if operation is None:
            operation = self.operation_journal.create(OrderFulfillmentOperation(workspace_id=workspace_id, order_id=order_id, idempotency_key=idempotency_key, request_fingerprint=fingerprint, operation_type=OrderFulfillmentOperationType.ORDER_SHIPMENT_TTN.value if payload.create_provider_document else OrderFulfillmentOperationType.LOCAL_SHIPMENT.value, state=OrderFulfillmentOperationState.VALIDATING.value, started_at=datetime.now(UTC), created_by=actor_user_id))
            self.db.flush()
        prepare = self.prepare_fulfillment(workspace_id, order_id, payload)
        prepare.blockers = [blocker for blocker in prepare.blockers if blocker != "ACTIVE_FULFILLMENT_OPERATION_EXISTS"]
        if prepare.blockers:
            operation.state = OrderFulfillmentOperationState.FAILED_SAFE.value
            operation.safe_error_code = prepare.blockers[0]
            operation.safe_error_message = "Fulfillment validation failed safely."
            operation.failed_at = datetime.now(UTC)
            self.db.commit()
            raise OrderFulfillmentValidationError(operation.safe_error_code)
        operation.state = OrderFulfillmentOperationState.RESERVING_STOCK.value
        if not operation.reservation_applied:
            inventory_rows = self.inventory.list_by_variants_for_update(workspace_id, [item.product_variant_id for item in order.items])
            inventory_by_variant = {row.product_variant_id: row for row in inventory_rows}
            for item in sorted(order.items, key=lambda row: str(row.product_variant_id)):
                row = inventory_by_variant.get(item.product_variant_id)
                if row is None or row.stock_quantity < row.reserved_quantity or row.reserved_quantity < item.quantity:
                    operation.state = OrderFulfillmentOperationState.FAILED_SAFE.value
                    operation.safe_error_code = "ORDER_RESERVATION_NOT_AVAILABLE"
                    operation.failed_at = datetime.now(UTC)
                    self.db.commit()
                    raise OrderFulfillmentValidationError("ORDER_RESERVATION_NOT_AVAILABLE")
            operation.reservation_applied = True
        operation.state = OrderFulfillmentOperationState.CREATING_SHIPMENT.value
        existing_shipment = self.shipments.shipments.find_active_by_order(workspace_id, order_id)
        if existing_shipment is None:
            shipment = self.shipments.create(workspace_id, ShipmentCreate(order_id=order.id, customer_id=order.customer_id, carrier=payload.delivery.provider, status=ShipmentStatus.DRAFT, recipient_name=payload.recipient.name, recipient_phone=payload.recipient.phone, city=payload.delivery.city_description, warehouse=payload.delivery.warehouse_description, cod_amount=payload.payment.cod_amount, declared_value=payload.delivery.declared_value or order.revenue, nova_poshta_city_ref=payload.delivery.city_ref, nova_poshta_warehouse_ref=payload.delivery.warehouse_ref), actor_user_id, commit=False)
            operation.shipment_created = True
            operation.shipment_id = shipment.id
        else:
            operation.shipment_id = existing_shipment.id
        operation.state = OrderFulfillmentOperationState.SHIPMENT_READY.value
        operation.local_persistence_completed = True
        self.db.commit()
        if not payload.create_provider_document:
            operation = self.operation_journal.get_by_key(workspace_id, idempotency_key, for_update=True)
            operation.state = OrderFulfillmentOperationState.COMPLETED.value
            operation.completed_at = datetime.now(UTC)
            self.db.commit()
            return self._operation_response(operation, reused, "Відправлення створено без ТТН. Створення ТТН вимкнено для цього запиту.")
        operation = self.operation_journal.get_by_key(workspace_id, idempotency_key, for_update=True)
        operation.state = OrderFulfillmentOperationState.RECONCILIATION_REQUIRED.value
        operation.provider_request_started = False
        operation.manual_reconciliation_required = True
        operation.blind_retry_blocked = True
        operation.safe_error_code = "PROVIDER_CREATE_REQUIRES_CONTROLLED_GATE"
        operation.safe_error_message = "Provider write is blocked until controlled production gate is verified."
        self.db.commit()
        return self._operation_response(operation, reused, "Створення ТТН заблоковано до підтвердження production gate. Не повторюйте blind retry.")

    def get_fulfillment_status(self, workspace_id: UUID, order_id: UUID) -> FulfillmentStatusResponse:
        operation = self.operation_journal.get_active_for_order(workspace_id, order_id) or self.operation_journal.get_latest_for_order(workspace_id, order_id)
        if operation is None:
            return FulfillmentStatusResponse()
        return FulfillmentStatusResponse(operation_id=operation.id, state=OrderFulfillmentOperationState(operation.state), shipment_id=operation.shipment_id, tracking_number=operation.provider_document_number, document_ref=operation.provider_document_ref, manual_reconciliation_required=operation.manual_reconciliation_required, blind_retry_blocked=operation.blind_retry_blocked, safe_error_code=operation.safe_error_code, safe_error_message=operation.safe_error_message)

    def reconcile_fulfillment(self, workspace_id: UUID, order_id: UUID, actor_user_id: UUID | None) -> FulfillmentExecuteResponse:
        operation = self.operation_journal.get_active_for_order(workspace_id, order_id, for_update=True)
        if operation is None:
            raise OrderFulfillmentValidationError("FULFILLMENT_OPERATION_NOT_FOUND")
        operation.state = OrderFulfillmentOperationState.RECONCILING.value
        operation.last_reconciled_at = datetime.now(UTC)
        operation.manual_reconciliation_required = True
        operation.blind_retry_blocked = True
        self.db.commit()
        return self._operation_response(operation, True, "Результат потребує ручного звірення з Новою Поштою без повторного створення ТТН.")

    def cancel_fulfillment(self, workspace_id: UUID, order_id: UUID, reason: str | None, actor_user_id: UUID | None) -> FulfillmentStatusResponse:
        operation = self.operation_journal.get_active_for_order(workspace_id, order_id, for_update=True)
        if operation is None:
            raise OrderFulfillmentValidationError("FULFILLMENT_OPERATION_NOT_FOUND")
        operation.state = OrderFulfillmentOperationState.CANCELLED.value
        operation.safe_error_message = reason
        self.db.commit()
        return self.get_fulfillment_status(workspace_id, order_id)

    def _operation_response(self, operation: OrderFulfillmentOperation, reused: bool, message: str) -> FulfillmentExecuteResponse:
        return FulfillmentExecuteResponse(operation_id=operation.id, state=OrderFulfillmentOperationState(operation.state), reused=reused, shipment_id=operation.shipment_id, tracking_number=operation.provider_document_number, document_ref=operation.provider_document_ref, manual_reconciliation_required=operation.manual_reconciliation_required, blind_retry_blocked=operation.blind_retry_blocked, inventory_reserved=operation.reservation_applied, safe_message=message)

    def _operation_fingerprint(self, workspace_id: UUID, order_id: UUID, payload: FulfillmentRequest) -> str:
        order = self.orders.get(workspace_id, order_id)
        items = [] if order is None else sorted(({"product_variant_id": str(item.product_variant_id), "quantity": item.quantity} for item in order.items), key=lambda row: row["product_variant_id"])
        body = payload.model_dump(mode="json")
        body.update({"workspace_id": str(workspace_id), "order_id": str(order_id), "items": items})
        encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

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
