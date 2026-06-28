from __future__ import annotations

from datetime import UTC, datetime, time
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.customer import Customer
from app.models.order import Order
from app.models.shipment import Shipment, ShipmentStatus


class ShipmentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_workspace(self, workspace_id: UUID, status: str | None = None, search: str | None = None) -> list[Shipment]:
        stmt: Select[tuple[Shipment]] = select(Shipment).where(Shipment.workspace_id == workspace_id, Shipment.deleted_at.is_(None)).options(selectinload(Shipment.order), selectinload(Shipment.customer))
        if status:
            stmt = stmt.where(Shipment.status == status)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Shipment.tracking_number.ilike(pattern),
                    Shipment.nova_poshta_document_number.ilike(pattern),
                    Shipment.city.ilike(pattern),
                    Shipment.warehouse.ilike(pattern),
                    Shipment.order.has(Order.order_number.ilike(pattern)),
                    Shipment.customer.has(or_(Customer.name.ilike(pattern), Customer.phone.ilike(pattern), Customer.instagram_username.ilike(pattern))),
                )
            )
        return list(self.db.execute(stmt.order_by(Shipment.created_at.desc())).scalars())

    def get(self, workspace_id: UUID, shipment_id: UUID) -> Shipment | None:
        stmt = select(Shipment).where(Shipment.workspace_id == workspace_id, Shipment.id == shipment_id, Shipment.deleted_at.is_(None)).options(selectinload(Shipment.order), selectinload(Shipment.customer))
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_order(self, workspace_id: UUID, order_id: UUID) -> Shipment | None:
        stmt = select(Shipment).where(Shipment.workspace_id == workspace_id, Shipment.order_id == order_id, Shipment.deleted_at.is_(None)).options(selectinload(Shipment.order), selectinload(Shipment.customer))
        return self.db.execute(stmt.order_by(Shipment.created_at.desc())).scalars().first()

    def find_active_by_order(self, workspace_id: UUID, order_id: UUID, exclude_shipment_id: UUID | None = None) -> Shipment | None:
        stmt = select(Shipment).where(Shipment.workspace_id == workspace_id, Shipment.order_id == order_id, Shipment.deleted_at.is_(None), Shipment.status != ShipmentStatus.CANCELLED.value)
        if exclude_shipment_id:
            stmt = stmt.where(Shipment.id != exclude_shipment_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def find_by_tracking_number(self, workspace_id: UUID, tracking_number: str | None, exclude_shipment_id: UUID | None = None) -> Shipment | None:
        if not tracking_number:
            return None
        stmt = select(Shipment).where(Shipment.workspace_id == workspace_id, Shipment.tracking_number == tracking_number, Shipment.deleted_at.is_(None))
        if exclude_shipment_id:
            stmt = stmt.where(Shipment.id != exclude_shipment_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, shipment: Shipment) -> Shipment:
        self.db.add(shipment)
        self.db.flush()
        return shipment

    def summary_counts(self, workspace_id: UUID) -> tuple[int, int, int, int]:
        today = datetime.now(UTC).date()
        today_start = datetime.combine(today, time.min, tzinfo=UTC)
        month_start = datetime(today.year, today.month, 1, tzinfo=UTC)
        stmt = select(
            func.count().filter(Shipment.status == ShipmentStatus.IN_TRANSIT.value),
            func.count().filter(Shipment.status == ShipmentStatus.ARRIVED.value),
            func.count().filter(Shipment.delivered_at >= today_start),
            func.count().filter(Shipment.returned_at >= month_start),
        ).where(Shipment.workspace_id == workspace_id, Shipment.deleted_at.is_(None))
        return self.db.execute(stmt).one()
