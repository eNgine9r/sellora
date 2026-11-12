"""All data access for the workspace-isolated Nova Poshta external inbox."""
from datetime import datetime, timedelta
from collections import defaultdict
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.ai_direct import DirectConversation, DirectMessage
from app.models.integration_connection import IntegrationConnection, IntegrationProvider, IntegrationStatus
from app.models.nova_poshta_external_document import NovaPoshtaExternalDocument
from app.models.shipment import Shipment, ShipmentCarrier
from app.models.workspace import Workspace


class NovaPoshtaExternalRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def workspaces_ready(self, limit: int = 50) -> list[UUID]:
        statement = (
            select(Workspace.id)
            .join(IntegrationConnection, IntegrationConnection.workspace_id == Workspace.id)
            .where(
                Workspace.is_active.is_(True),
                IntegrationConnection.provider == IntegrationProvider.NOVA_POSHTA.value,
                IntegrationConnection.status == IntegrationStatus.CONNECTED.value,
                IntegrationConnection.deleted_at.is_(None),
            )
            .distinct().order_by(Workspace.id).limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def matching_shipment_ids(self, workspace_id: UUID, number: str) -> list[UUID]:
        stmt = select(Shipment.id).where(
            Shipment.workspace_id == workspace_id,
            Shipment.deleted_at.is_(None),
            Shipment.carrier == ShipmentCarrier.NOVA_POSHTA.value,
            or_(Shipment.tracking_number == number, Shipment.nova_poshta_document_number == number),
        ).limit(2)
        return list(self.db.scalars(stmt).all())

    def upsert(
        self, workspace_id: UUID, number: str, ref: str | None, status: str | None,
        match_state: str, matched_shipment_id: UUID | None, now: datetime,
    ) -> None:
        # Unique workspace+TTN conflict protection also covers overlapping worker runs.
        values = dict(
            id=uuid4(), workspace_id=workspace_id, tracking_number=number,
            document_ref=ref, provider_status=status, match_state=match_state,
            matched_shipment_id=matched_shipment_id, first_seen_at=now, last_seen_at=now,
        )
        stmt = insert(NovaPoshtaExternalDocument).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["workspace_id", "tracking_number"],
            set_={
                "document_ref": func.coalesce(stmt.excluded.document_ref, NovaPoshtaExternalDocument.document_ref),
                "provider_status": func.coalesce(stmt.excluded.provider_status, NovaPoshtaExternalDocument.provider_status),
                "match_state": stmt.excluded.match_state,
                "matched_shipment_id": stmt.excluded.matched_shipment_id,
                "last_seen_at": stmt.excluded.last_seen_at,
                "updated_at": now,
            },
            where=NovaPoshtaExternalDocument.deleted_at.is_(None),
        )
        self.db.execute(stmt)

    def list_for_workspace(self, workspace_id: UUID, *, state: str | None = None, limit: int = 100) -> list[NovaPoshtaExternalDocument]:
        stmt = select(NovaPoshtaExternalDocument).where(
            NovaPoshtaExternalDocument.workspace_id == workspace_id,
            NovaPoshtaExternalDocument.deleted_at.is_(None),
        )
        if state:
            stmt = stmt.where(NovaPoshtaExternalDocument.match_state == state)
        return list(self.db.scalars(stmt.order_by(NovaPoshtaExternalDocument.last_seen_at.desc()).limit(min(limit, 100))).all())

    def tracking_candidates(self, workspace_id: UUID, *, now: datetime, limit: int = 12) -> list[NovaPoshtaExternalDocument]:
        """Only active/unknown tracking, with a retry ceiling and stable tenant scope."""
        doc = NovaPoshtaExternalDocument
        terminal_text = or_(
            doc.provider_status.ilike("%отримано%"),
            doc.provider_status.ilike("%вручено%"),
            doc.provider_status.ilike("%відмова%"),
            doc.provider_status.ilike("%повернен%"),
        )
        stmt = (
            select(doc)
            .where(
                doc.workspace_id == workspace_id,
                doc.deleted_at.is_(None),
                doc.first_seen_at >= now - timedelta(days=90),
                or_(doc.provider_tracking_checked_at.is_(None),
                    doc.provider_tracking_checked_at <= now - timedelta(minutes=14)),
                or_(
                    doc.provider_normalized_status.in_(("CREATED", "IN_TRANSIT", "ARRIVED")),
                    and_(doc.provider_normalized_status.is_(None), or_(doc.provider_status.is_(None), ~terminal_text)),
                ),
            )
            .order_by(
                doc.provider_tracking_checked_at.asc().nullsfirst(),
                doc.last_seen_at.desc(),
                doc.id,
            )
            .limit(min(max(limit, 1), 12))
        )
        return list(self.db.scalars(stmt).all())

    def direct_evidence_by_document(self, workspace_id: UUID, document_ids: list[UUID]) -> dict[UUID, dict]:
        """Find the unique Instagram thread where this sender-owned TTN was sent.

        Read-only: a matching outbound tracking number is delivery evidence,
        never an order, a payment, or confirmation of purchased products.
        Tenant scope is enforced at each join; ambiguous threads stay unlinked.
        """
        if not document_ids:
            return {}
        query = (
            select(
                NovaPoshtaExternalDocument.id,
                DirectConversation.id,
                DirectConversation.linked_customer_id,
                DirectConversation.linked_order_id,
            )
            .join(
                DirectMessage,
                and_(
                    DirectMessage.workspace_id == NovaPoshtaExternalDocument.workspace_id,
                    DirectMessage.deleted_at.is_(None),
                    DirectMessage.is_synthetic.is_(False),
                    DirectMessage.direction == "OUTBOUND",
                    DirectMessage.text.contains(NovaPoshtaExternalDocument.tracking_number),
                ),
            )
            .join(
                DirectConversation,
                and_(
                    DirectConversation.id == DirectMessage.conversation_id,
                    DirectConversation.workspace_id == NovaPoshtaExternalDocument.workspace_id,
                    DirectConversation.deleted_at.is_(None),
                    DirectConversation.channel == "INSTAGRAM",
                ),
            )
            .where(
                NovaPoshtaExternalDocument.workspace_id == workspace_id,
                NovaPoshtaExternalDocument.id.in_(document_ids),
                NovaPoshtaExternalDocument.deleted_at.is_(None),
            )
            .distinct()
        )
        conversations: dict[UUID, dict[UUID, tuple[UUID | None, bool]]] = defaultdict(dict)
        for document_id, conversation_id, customer_id, order_id in self.db.execute(query).all():
            conversations[document_id][conversation_id] = (customer_id, order_id is not None)
        result = {}
        for document_id, matches in conversations.items():
            if len(matches) != 1:
                result[document_id] = {"direct_match_state": "AMBIGUOUS"}
                continue
            conversation_id, (customer_id, has_order) = next(iter(matches.items()))
            result[document_id] = {
                "direct_match_state": "MATCHED",
                "direct_conversation_id": conversation_id,
                "direct_customer_linked": customer_id is not None,
                "direct_customer_id": customer_id,
                "direct_order_linked": has_order,
            }
        return result
