"""Single, tenant-scoped source for fast operational shipment KPIs.

External Nova Poshta TTNs are shipping evidence only, not revenue or orders.
"""
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.nova_poshta_external_document import NovaPoshtaExternalDocument
from app.models.shipment import Shipment, ShipmentCarrier, ShipmentStatus
from app.services.nova_poshta_external_status import infer_external_shipment_status


@dataclass(frozen=True)
class LiveShipmentCounts:
    in_transit_count: int
    arrived_count: int
    crm_total_count: int
    crm_ready_count: int
    crm_delivered_count: int
    crm_problem_count: int
    provider_tracking_checked_at: datetime | None
    provider_pending_count: int


def compute_counts(shipments, external_documents, *, now: datetime) -> LiveShipmentCounts:
    states: dict[str, ShipmentStatus | None] = {}
    internal = []
    for item in shipments:
        state = ShipmentStatus(item.status)
        internal.append(state)
        tracking = item.nova_poshta_document_number or item.tracking_number
        if item.carrier == ShipmentCarrier.NOVA_POSHTA.value and tracking:
            key = "np:" + tracking
        else:
            key = "crm:" + str(item.id)
        states[key] = state

    last_verified = None
    pending = 0
    for doc in external_documents:
        key = "np:" + doc.tracking_number
        normalized = getattr(doc, "provider_normalized_status", None)
        state = ShipmentStatus(normalized) if normalized else infer_external_shipment_status(doc.provider_status)
        checked = getattr(doc, "provider_tracking_checked_at", None)
        if checked and (last_verified is None or checked > last_verified):
            last_verified = checked
        if state in (ShipmentStatus.CREATED, ShipmentStatus.IN_TRANSIT, ShipmentStatus.ARRIVED):
            if checked is None or checked <= now - timedelta(minutes=35):
                pending += 1
        previous = states.get(key)
        if state is None:
            states.setdefault(key, None)
            continue
        # An older external listing must not regress a terminal internal shipment.
        if previous in (ShipmentStatus.DELIVERED, ShipmentStatus.RETURNED, ShipmentStatus.CANCELLED) and state in (
            ShipmentStatus.DRAFT, ShipmentStatus.CREATED, ShipmentStatus.IN_TRANSIT, ShipmentStatus.ARRIVED,
        ):
            continue
        states[key] = state

    return LiveShipmentCounts(
        in_transit_count=sum(state == ShipmentStatus.IN_TRANSIT for state in states.values()),
        arrived_count=sum(state == ShipmentStatus.ARRIVED for state in states.values()),
        crm_total_count=len(internal),
        crm_ready_count=sum(state in (ShipmentStatus.DRAFT, ShipmentStatus.CREATED) for state in internal),
        crm_delivered_count=sum(state == ShipmentStatus.DELIVERED for state in internal),
        crm_problem_count=sum(state in (ShipmentStatus.RETURNED, ShipmentStatus.CANCELLED) for state in internal),
        provider_tracking_checked_at=last_verified,
        provider_pending_count=pending,
    )


def shipment_live_counts(db: Session, workspace_id: UUID) -> LiveShipmentCounts:
    shipments = db.execute(
        select(Shipment.id, Shipment.carrier, Shipment.status, Shipment.tracking_number, Shipment.nova_poshta_document_number)
        .where(Shipment.workspace_id == workspace_id, Shipment.deleted_at.is_(None))
    ).all()
    external = db.execute(
        select(
            NovaPoshtaExternalDocument.tracking_number, NovaPoshtaExternalDocument.provider_status,
            NovaPoshtaExternalDocument.provider_normalized_status,
            NovaPoshtaExternalDocument.provider_tracking_checked_at,
        ).where(
            NovaPoshtaExternalDocument.workspace_id == workspace_id,
            NovaPoshtaExternalDocument.deleted_at.is_(None),
        )
    ).all()
    return compute_counts(shipments, external, now=datetime.now(UTC))
