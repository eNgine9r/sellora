from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.lead import Lead


class LeadRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_workspace(self, workspace_id: UUID, search: str | None = None, status: str | None = None, lead_source_id: UUID | None = None) -> list[Lead]:
        stmt: Select[tuple[Lead]] = select(Lead).where(Lead.workspace_id == workspace_id, Lead.deleted_at.is_(None)).options(
            selectinload(Lead.lead_source),
            selectinload(Lead.campaign),
            selectinload(Lead.assigned_user),
        )
        if search:
            query = f"%{search}%"
            stmt = stmt.where(or_(Lead.name.ilike(query), Lead.phone.ilike(query), Lead.instagram_username.ilike(query)))
        if status:
            stmt = stmt.where(Lead.status == status)
        if lead_source_id:
            stmt = stmt.where(Lead.lead_source_id == lead_source_id)
        return list(self.db.execute(stmt.order_by(Lead.created_at.desc())).scalars())

    def get(self, workspace_id: UUID, lead_id: UUID) -> Lead | None:
        stmt = select(Lead).where(Lead.workspace_id == workspace_id, Lead.id == lead_id, Lead.deleted_at.is_(None)).options(
            selectinload(Lead.lead_source),
            selectinload(Lead.campaign),
            selectinload(Lead.assigned_user),
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, lead: Lead) -> Lead:
        self.db.add(lead)
        self.db.flush()
        return lead

    def soft_delete(self, lead: Lead, deleted_by: UUID | None) -> Lead:
        lead.deleted_at = datetime.now(UTC)
        lead.deleted_by = deleted_by
        self.db.flush()
        return lead
