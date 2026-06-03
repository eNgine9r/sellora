from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.lead_source import LeadSource


class LeadSourceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_workspace(self, workspace_id: UUID, search: str | None = None, include_inactive: bool = False) -> list[LeadSource]:
        stmt: Select[tuple[LeadSource]] = select(LeadSource).where(LeadSource.workspace_id == workspace_id, LeadSource.deleted_at.is_(None))
        if search:
            stmt = stmt.where(LeadSource.name.ilike(f"%{search}%"))
        if not include_inactive:
            stmt = stmt.where(LeadSource.is_active.is_(True))
        return list(self.db.execute(stmt.order_by(LeadSource.name)).scalars())

    def get(self, workspace_id: UUID, lead_source_id: UUID) -> LeadSource | None:
        stmt = select(LeadSource).where(LeadSource.workspace_id == workspace_id, LeadSource.id == lead_source_id, LeadSource.deleted_at.is_(None))
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, lead_source: LeadSource) -> LeadSource:
        self.db.add(lead_source)
        self.db.flush()
        return lead_source

    def soft_delete(self, lead_source: LeadSource, deleted_by: UUID | None) -> LeadSource:
        lead_source.deleted_at = datetime.now(UTC)
        lead_source.deleted_by = deleted_by
        self.db.flush()
        return lead_source
