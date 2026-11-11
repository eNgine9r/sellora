"""Human bank confirmation without monobank integration and without false provenance."""
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.manual_payment_confirmation import ManualPaymentConfirmation
from app.models.order import OrderStatus, PaymentStatus
from app.models.workspace import Workspace
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.order_repository import OrderRepository
from app.schemas.manual_payment_confirmation import (
    ManualPaymentConfirmRequest, ManualPaymentConfirmationResponse, OrderManualPaymentResult,
)


class ManualPaymentError(ValueError):
    pass


class ManualPaymentConfirmationService:
    def __init__(self, db: Session):
        self.db = db
        self.orders = OrderRepository(db)
        self.audit = AuditLogRepository(db)

    def get(self, workspace_id: UUID, order_id: UUID) -> ManualPaymentConfirmation | None:
        return self.db.scalar(
            select(ManualPaymentConfirmation)
            .where(
                ManualPaymentConfirmation.workspace_id == workspace_id,
                ManualPaymentConfirmation.order_id == order_id,
            )
        )

    @staticmethod
    def response(row: ManualPaymentConfirmation) -> ManualPaymentConfirmationResponse:
        return ManualPaymentConfirmationResponse(
            id=row.id,
            order_id=row.order_id,
            payment_method=row.payment_method,
            amount_minor=row.amount_minor,
            currency=row.currency,
            receipt_checked=row.receipt_checked,
            bank_received_checked=row.bank_received_checked,
            receipt_note=row.receipt_note,
            verified_by_user_id=row.verified_by_user_id,
            verified_at=row.verified_at,
            reference_suffix="••••" + row.transaction_reference[-4:],
        )

    def confirm(
        self,
        workspace_id: UUID,
        order_id: UUID,
        payload: ManualPaymentConfirmRequest,
        actor_id: UUID,
    ) -> OrderManualPaymentResult:
        order = self.orders.get_for_update(workspace_id, order_id)
        if order is None:
            raise ManualPaymentError("ORDER_NOT_FOUND")
        if not payload.receipt_checked or not payload.bank_received_checked:
            raise ManualPaymentError("RECEIPT_AND_BANK_CONFIRMATION_REQUIRED")
        workspace_currency = self.db.scalar(
            select(Workspace.currency_code).where(Workspace.id == workspace_id)
        )
        if workspace_currency != "UAH":
            raise ManualPaymentError("ONLY_UAH_WORKSPACES_SUPPORTED")
        existing = self.get(workspace_id, order_id)
        if existing is not None:
            if (existing.transaction_reference == payload.transaction_reference
                    and existing.amount_minor == payload.amount_minor
                    and existing.payment_method == payload.payment_method.value):
                return OrderManualPaymentResult(confirmation=self.response(existing), payment_status=order.payment_status)
            raise ManualPaymentError("ORDER_PAYMENT_ALREADY_CONFIRMED")
        if order.is_historical or order.status in (OrderStatus.CANCELLED.value, OrderStatus.RETURNED.value):
            raise ManualPaymentError("ORDER_NOT_ELIGIBLE")
        if order.payment_status not in (PaymentStatus.PENDING.value, PaymentStatus.PAID.value):
            raise ManualPaymentError("ORDER_NOT_PENDING_OR_PAID")
        if not order.customer_id or not order.items:
            raise ManualPaymentError("ORDER_CUSTOMER_OR_ITEMS_MISSING")
        if not Decimal(order.revenue or 0).is_finite() or Decimal(order.revenue or 0) <= 0:
            raise ManualPaymentError("ORDER_AMOUNT_NOT_POSITIVE")
        # Full payment only; partial and overpayment must be reviewed separately.
        expected_minor = int(Decimal(order.revenue) * 100)
        if payload.amount_minor != expected_minor:
            raise ManualPaymentError("PAYMENT_AMOUNT_MISMATCH")

        # Preserve existing revenue, order line items, inventory, profit and shipment.
        existing_reference = self.db.scalar(
            select(ManualPaymentConfirmation.id)
            .where(
                ManualPaymentConfirmation.workspace_id == workspace_id,
                ManualPaymentConfirmation.transaction_reference == payload.transaction_reference,
            )
        )
        if existing_reference is not None:
            raise ManualPaymentError("BANK_TRANSACTION_ALREADY_ASSIGNED")

        row = ManualPaymentConfirmation(
            workspace_id=workspace_id,
            order_id=order.id,
            payment_method=payload.payment_method.value,
            transaction_reference=payload.transaction_reference,
            amount_minor=payload.amount_minor,
            currency="UAH",
            receipt_checked=True,
            bank_received_checked=True,
            receipt_note=payload.receipt_note,
            verified_by_user_id=actor_id,
            verified_at=datetime.now(UTC),
        )
        self.db.add(row)
        self.db.flush()
        old_status = order.payment_status
        order.payment_status = PaymentStatus.PAID.value
        self.audit.create(
            workspace_id=workspace_id, user_id=actor_id, entity_type="Order",
            entity_id=order.id, action="ORDER_PAYMENT_MANUALLY_VERIFIED",
            old_value={"payment_status": old_status},
            new_value={"payment_status": PaymentStatus.PAID.value,
                       "confirmation_id": str(row.id),
                       "payment_method": row.payment_method,
                       "amount_minor": payload.amount_minor,
                       "receipt_checked": True, "bank_received_checked": True,
                       "verification_source": "HUMAN_ATTESTATION_NOT_BANK_API"},
        )
        self.db.commit()
        return OrderManualPaymentResult(confirmation=self.response(row), payment_status=order.payment_status)
