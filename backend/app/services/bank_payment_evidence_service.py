"""Idempotent evidence-only monobank importer.

This module NEVER sets Order.payment_status, Order.revenue, profit or stock.
MANUAL_IMPORT is not bank attestation, even for a unique amount/order reference.
Settlement payouts must never masquerade as a second customer payment.
"""
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.bank_payment_evidence import BankPaymentEvidence, BankPaymentKind, BankPaymentOrigin
from app.models.order import Order, OrderStatus, PaymentStatus
from app.models.workspace import Workspace
from app.repositories.audit_log_repository import AuditLogRepository
from app.schemas.bank_payment_evidence import (
    BankImportRequest, BankImportResponse, BankLedgerResponse, BankPreviewResponse,
    BankReviewRow, BankReviewStatus,
)


class BankPaymentEvidenceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditLogRepository(db)

    @staticmethod
    def minor_to_uah(amount_minor: int) -> Decimal:
        return Decimal(amount_minor) / Decimal(100)

    def _existing_keys(self, workspace_id: UUID) -> set[tuple[str, str]]:
        rows = self.db.execute(
            select(BankPaymentEvidence.provider_account_id, BankPaymentEvidence.external_reference)
            .where(BankPaymentEvidence.workspace_id == workspace_id,
                   BankPaymentEvidence.provider == "MONOBANK")
        ).all()
        return set(rows)

    def _order(self, workspace_id: UUID, order_number: str | None) -> Order | None:
        if not order_number:
            return None
        return self.db.execute(
            select(Order)
            .where(Order.workspace_id == workspace_id, Order.order_number == order_number,
                   Order.deleted_at.is_(None))
        ).scalar_one_or_none()

    @staticmethod
    def classify(row, order: Order | None) -> tuple[str, UUID | None]:
        # No import of funds is bank verified in this phase.
        if row.kind == BankPaymentKind.UNCLASSIFIED_CREDIT:
            return "BANK_CREDIT_CLASSIFICATION_REQUIRED", None
        if row.kind == BankPaymentKind.ACQUIRING_PAYOUT:
            return "PAYOUT_NOT_CUSTOMER_PAYMENT", None
        if row.kind == BankPaymentKind.REFUND:
            return "REFUND_NEEDS_PAYMENT_ALLOCATION", None
        if row.is_hold:
            return "BANK_HOLD_NOT_SETTLED", None
        if not row.order_number:
            return "ORDER_REFERENCE_MISSING", None
        if order is None:
            return "ORDER_NOT_FOUND", None
        if order.is_historical:
            return "HISTORICAL_ORDER_NOT_VERIFIED", None
        if order.status in {OrderStatus.CANCELLED.value, OrderStatus.RETURNED.value}:
            return "ORDER_CANCELLED_OR_RETURNED", None
        if order.payment_status != PaymentStatus.PENDING.value:
            return "ORDER_PAYMENT_ALREADY_PROCESSED", None
        if Decimal(order.revenue) != BankPaymentEvidenceService.minor_to_uah(row.amount_minor):
            return "ORDER_AMOUNT_MISMATCH", None
        # This is only a potential match, *not* an allocation or payment.
        return "REQUIRES_PROVIDER_AND_RECEIPT_VERIFICATION", order.id

    def _classify_batch(self, workspace_id: UUID, payload: BankImportRequest):
        seen = self._existing_keys(workspace_id)
        result: list[BankReviewRow] = []
        insertable = []
        for row in payload.rows:
            key = (row.provider_account_id, row.external_reference)
            if key in seen:
                result.append(BankReviewRow(
                    provider_account_id=row.provider_account_id,
                    external_reference=row.external_reference,
                    rail=row.rail, kind=row.kind, amount_minor=row.amount_minor,
                    status=BankReviewStatus.DUPLICATE,
                    reason="PROVIDER_ACCOUNT_TRANSACTION_ALREADY_IMPORTED",
                ))
                continue
            seen.add(key)
            reason, order_id = self.classify(row, self._order(workspace_id, row.order_number))
            result.append(BankReviewRow(
                provider_account_id=row.provider_account_id, external_reference=row.external_reference,
                rail=row.rail, kind=row.kind, amount_minor=row.amount_minor,
                status=BankReviewStatus.REVIEW, reason=reason, candidate_order_id=order_id,
            ))
            insertable.append((row, reason, order_id))
        return result, insertable

    @staticmethod
    def _preview(result: list[BankReviewRow]) -> BankPreviewResponse:
        return BankPreviewResponse(
            rows=result,
            candidate_count=sum(x.candidate_order_id is not None for x in result),
            review_count=sum(x.status == BankReviewStatus.REVIEW for x in result),
            duplicate_count=sum(x.status == BankReviewStatus.DUPLICATE for x in result),
        )

    def preview(self, workspace_id: UUID, payload: BankImportRequest) -> BankPreviewResponse:
        result, _ = self._classify_batch(workspace_id, payload)
        return self._preview(result)

    def import_rows(self, workspace_id: UUID, payload: BankImportRequest, actor_user_id: UUID) -> BankImportResponse:
        # Serialize against concurrent import requests in one tenant.
        exists = self.db.execute(
            select(Workspace.id).where(Workspace.id == workspace_id).with_for_update()
        ).scalar_one_or_none()
        if exists is None:
            raise ValueError("Workspace not found")
        result, insertable = self._classify_batch(workspace_id, payload)
        for row, reason, order_id in insertable:
            evidence = BankPaymentEvidence(
                workspace_id=workspace_id,
                provider="MONOBANK",
                provider_account_id=row.provider_account_id,
                external_reference=row.external_reference,
                rail=row.rail.value,
                kind=row.kind.value,
                origin=BankPaymentOrigin.MANUAL_IMPORT.value,
                amount_minor=row.amount_minor,
                currency=row.currency,
                occurred_at=row.occurred_at,
                is_hold=row.is_hold,
                invoice_id=row.invoice_id,
                order_number=row.order_number,
                candidate_order_id=order_id,
                review_reason=reason,
                created_by_user_id=actor_user_id,
            )
            self.db.add(evidence)
            self.db.flush()
            self.audit.create(
                workspace_id=workspace_id, user_id=actor_user_id,
                entity_type="BankPaymentEvidence", entity_id=evidence.id,
                action="BANK_PAYMENT_EVIDENCE_IMPORTED",
                new_value={"origin": "MANUAL_IMPORT", "kind": row.kind.value,
                           "review_reason": reason, "candidate_order_id": str(order_id) if order_id else None},
            )
        self.db.commit()
        preview = self._preview(result)
        return BankImportResponse(**preview.model_dump(), inserted_count=len(insertable))

    def ledger(self, workspace_id: UUID, limit: int = 50, offset: int = 0) -> BankLedgerResponse:
        scoped = BankPaymentEvidence.workspace_id == workspace_id
        total = self.db.execute(select(func.count()).select_from(BankPaymentEvidence).where(scoped)).scalar_one()
        rows = self.db.execute(
            select(BankPaymentEvidence).where(scoped)
            .order_by(BankPaymentEvidence.occurred_at.desc(), BankPaymentEvidence.id.desc())
            .limit(limit).offset(offset)
        ).scalars().all()
        return BankLedgerResponse(rows=rows, total_count=total)
