"""Read-only COD evidence classification followed by explicitly requested import.

Neither preview nor import mutates Order.revenue, Order.payment_status, confirmed
profit, inventory or historical cost snapshots. Confirmed deposits are displayed
in a SEPARATE cash receipt metric and are never added to sales revenue.
"""
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.cod_payment_evidence import CodEvidenceStatus, CodPaymentEvidence
from app.models.order import Order, OrderStatus
from app.models.shipment import Shipment, ShipmentCarrier
from app.repositories.audit_log_repository import AuditLogRepository
from app.schemas.cod_reconciliation import (
    CodImportRequest, CodImportResponse, CodLedgerResponse, CodLedgerRow,
    CodPreviewResponse, CodReviewRow,
)


class CodReconciliationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditLogRepository(db)

    @staticmethod
    def normalized_ttn(ttn: str | None) -> str | None:
        if ttn is None or not ttn.strip():
            return None
        value = "".join(ttn.split())
        return value if value.isdigit() and len(value) == 14 else None

    @staticmethod
    def classify(
        *,
        tracking_number: str | None,
        matches: list[tuple[Shipment, Order]],
        prior_receipt: bool,
        gross_amount: Decimal,
    ) -> tuple[str, str | None, UUID | None, UUID | None]:
        if tracking_number is None:
            return "REVIEW", "NO_VALID_TTN", None, None
        if len(matches) != 1:
            return "REVIEW", "NO_UNIQUE_SHIPMENT", None, None
        shipment, order = matches[0]
        if order.status in {OrderStatus.CANCELLED.value, OrderStatus.RETURNED.value}:
            return "REVIEW", "CANCELLED_OR_RETURNED", order.id, shipment.id
        if prior_receipt:
            return "REVIEW", "POSSIBLE_DUPLICATE_RECEIPT", order.id, shipment.id
        expected = Decimal(shipment.cod_amount or 0)
        if expected <= 0:
            return "REVIEW", "NO_COD_IN_SHIPMENT", order.id, shipment.id
        if expected != gross_amount:
            return "REVIEW", "COD_AMOUNT_MISMATCH", order.id, shipment.id
        # A matched register is evidence of actual COD only; not evidence of
        # full sale price when the buyer paid a deposit outside NovaPay.
        return "MATCHED", None, order.id, shipment.id

    def _shipment_matches(self, workspace_id: UUID, ttn: str | None):
        if not ttn:
            return []
        stmt = (
            select(Shipment, Order)
            .join(Order, and_(Shipment.order_id == Order.id,
                              Shipment.workspace_id == Order.workspace_id))
            .where(
                Shipment.workspace_id == workspace_id, Shipment.deleted_at.is_(None),
                Order.deleted_at.is_(None), Order.workspace_id == workspace_id,
                Shipment.carrier == ShipmentCarrier.NOVA_POSHTA.value,
                Shipment.tracking_number == ttn,
            )
        )
        return list(self.db.execute(stmt).all())

    def _existing_rows(self, workspace_id: UUID):
        return list(self.db.execute(
            select(CodPaymentEvidence)
            .where(CodPaymentEvidence.workspace_id == workspace_id)
        ).scalars().all())

    def _classify_batch(self, workspace_id: UUID, payload: CodImportRequest):
        existing = self._existing_rows(workspace_id)
        seen_references = {(x.source, x.external_reference) for x in existing}
        seen_matched_ttn = {x.tracking_number for x in existing if x.status == "MATCHED" and x.tracking_number}
        result: list[CodReviewRow] = []
        insertable = []
        for incoming in payload.rows:
            source = incoming.source.value
            reference = incoming.reference.strip()
            ttn = self.normalized_ttn(incoming.tracking_number)
            source_key = (source, reference)
            if source_key in seen_references:
                result.append(CodReviewRow(
                    reference=reference, tracking_number=ttn,
                    amount=incoming.gross_amount, status="DUPLICATE",
                    reason="REFERENCE_ALREADY_IMPORTED",
                ))
                continue
            seen_references.add(source_key)
            matches = self._shipment_matches(workspace_id, ttn)
            status, reason, order_id, shipment_id = self.classify(
                tracking_number=ttn,
                matches=matches,
                prior_receipt=ttn in seen_matched_ttn,
                gross_amount=incoming.gross_amount,
            )
            # The source is already chosen by the shop owner explicitly.
            # Bank statements without a TTN must never match by amount alone.
            if status == "MATCHED":
                seen_matched_ttn.add(ttn)
            row = CodReviewRow(
                reference=reference, tracking_number=ttn,
                amount=incoming.gross_amount, status=status,
                reason=reason, order_id=order_id,
            )
            result.append(row)
            insertable.append((incoming, row, shipment_id))
        return result, insertable

    @staticmethod
    def _preview(rows):
        return CodPreviewResponse(
            rows=rows,
            matched_count=sum(x.status == "MATCHED" for x in rows),
            review_count=sum(x.status == "REVIEW" for x in rows),
            duplicate_count=sum(x.status == "DUPLICATE" for x in rows),
        )

    def preview(self, workspace_id: UUID, payload: CodImportRequest) -> CodPreviewResponse:
        rows, _ = self._classify_batch(workspace_id, payload)
        return self._preview(rows)

    def import_rows(self, workspace_id: UUID, payload: CodImportRequest, actor_user_id: UUID) -> CodImportResponse:
        # Lock the workspace row for serial import and re-evaluate duplicate
        # keys/TTNs inside this transaction. Prevent concurrent repeat uploads.
        from app.models.workspace import Workspace
        scoped = self.db.execute(
            select(Workspace.id).where(Workspace.id == workspace_id).with_for_update()
        ).scalar_one_or_none()
        if scoped is None:
            raise ValueError("Workspace not found")
        rows, insertable = self._classify_batch(workspace_id, payload)
        for incoming, outcome, shipment_id in insertable:
            record = CodPaymentEvidence(
                workspace_id=workspace_id,
                source=incoming.source.value,
                external_reference=incoming.reference.strip(),
                tracking_number=outcome.tracking_number,
                order_id=outcome.order_id,
                shipment_id=shipment_id,
                gross_amount=incoming.gross_amount,
                fee_amount=incoming.fee_amount,
                paid_at=incoming.paid_at,
                status=outcome.status,
                review_reason=outcome.reason,
                created_by_user_id=actor_user_id,
            )
            self.db.add(record)
            self.db.flush()
            self.audit.create(
                workspace_id=workspace_id, user_id=actor_user_id,
                entity_type="CodPaymentEvidence", entity_id=record.id,
                action="COD_PAYMENT_EVIDENCE_IMPORTED",
                new_value={
                    "source": record.source, "reference": record.external_reference,
                    "tracking_number": record.tracking_number, "order_id": str(record.order_id) if record.order_id else None,
                    "amount": str(record.gross_amount), "status": record.status,
                },
            )
        self.db.commit()
        summary = self._preview(rows)
        return CodImportResponse(**summary.model_dump(), inserted_count=len(insertable))

    def ledger(self, workspace_id: UUID, date_from: datetime | None = None, date_to: datetime | None = None) -> CodLedgerResponse:
        stmt = select(CodPaymentEvidence).where(CodPaymentEvidence.workspace_id == workspace_id)
        if date_from is not None:
            stmt = stmt.where(CodPaymentEvidence.paid_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(CodPaymentEvidence.paid_at <= date_to)
        entries = list(self.db.execute(stmt.order_by(CodPaymentEvidence.paid_at.desc()).limit(250)).scalars().all())
        # Summary must use ALL matching entries, not just the 250 visible rows.
        sums = select(
            CodPaymentEvidence.status,
            func.coalesce(func.sum(CodPaymentEvidence.gross_amount), 0),
            func.count(CodPaymentEvidence.id),
        ).where(CodPaymentEvidence.workspace_id == workspace_id)
        if date_from is not None:
            sums = sums.where(CodPaymentEvidence.paid_at >= date_from)
        if date_to is not None:
            sums = sums.where(CodPaymentEvidence.paid_at <= date_to)
        totals = {r[0]: (r[1], r[2]) for r in self.db.execute(sums.group_by(CodPaymentEvidence.status)).all()}
        # Unverified value is historical evidence only, never recognized cash.
        pending_stmt = select(
            func.coalesce(func.sum(Order.historical_order_value), 0),
            func.count(Order.id),
        ).where(
            Order.workspace_id == workspace_id, Order.deleted_at.is_(None),
            Order.is_historical.is_(True), Order.revenue == 0,
            Order.historical_order_value > 0,
            ~select(CodPaymentEvidence.id).where(
                CodPaymentEvidence.workspace_id == workspace_id,
                CodPaymentEvidence.order_id == Order.id,
                CodPaymentEvidence.status == "MATCHED",
            ).exists(),
        )
        unvalued_stmt = select(func.count(Order.id)).where(
            Order.workspace_id == workspace_id, Order.deleted_at.is_(None),
            Order.is_historical.is_(True), Order.revenue == 0,
            or_(Order.historical_order_value.is_(None), Order.historical_order_value == 0),
        )
        pending, pending_count = self.db.execute(pending_stmt).one()
        unvalued = self.db.execute(unvalued_stmt).scalar_one()
        return CodLedgerResponse(
            rows=[
                CodLedgerRow(
                    id=x.id, source=x.source, reference=x.external_reference,
                    tracking_number=x.tracking_number, order_id=x.order_id,
                    gross_amount=x.gross_amount, fee_amount=x.fee_amount,
                    paid_at=x.paid_at, status=x.status,
                    review_reason=x.review_reason,
                ) for x in entries
            ],
            matched_receipts=totals.get("MATCHED", (Decimal(0), 0))[0],
            review_receipts=totals.get("REVIEW", (Decimal(0), 0))[0],
            matched_count=totals.get("MATCHED", (Decimal(0), 0))[1],
            review_count=totals.get("REVIEW", (Decimal(0), 0))[1],
            pending_historical_amount=pending,
            historical_amount_unverified_count=pending_count,
            unvalued_historical_orders=unvalued,
        )
