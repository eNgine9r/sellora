"""All data access for the workspace-isolated Nova Poshta external inbox."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

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
