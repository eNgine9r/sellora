from uuid import UUID

from sqlalchemy.orm import Session

from app.models.lead_source import LeadSource
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.lead_source_repository import LeadSourceRepository
from app.schemas.lead_source import LeadSourceCreate, LeadSourceUpdate
from app.services.business_utils import snapshot


class LeadSourceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.lead_sources = LeadSourceRepository(db)
        self.audit_logs = AuditLogRepository(db)

    def list(self, workspace_id: UUID, search: str | None = None, include_inactive: bool = False) -> list[LeadSource]:
        return self.lead_sources.list(workspace_id, search, include_inactive)

    def get(self, workspace_id: UUID, lead_source_id: UUID) -> LeadSource | None:
        return self.lead_sources.get(workspace_id, lead_source_id)

    def create(self, workspace_id: UUID, payload: LeadSourceCreate, actor_user_id: UUID | None) -> LeadSource:
        lead_source = self.lead_sources.create(LeadSource(workspace_id=workspace_id, **payload.model_dump()))
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="LeadSource",
            entity_id=lead_source.id,
            action="CREATE",
            new_value=snapshot(lead_source),
        )
        self.db.commit()
        self.db.refresh(lead_source)
        return lead_source

    def update(self, workspace_id: UUID, lead_source_id: UUID, payload: LeadSourceUpdate, actor_user_id: UUID | None) -> LeadSource | None:
        lead_source = self.get(workspace_id, lead_source_id)
        if lead_source is None:
            return None
        old_value = snapshot(lead_source)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(lead_source, field, value)
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="LeadSource",
            entity_id=lead_source.id,
            action="UPDATE",
            old_value=old_value,
            new_value=snapshot(lead_source),
        )
        self.db.commit()
        self.db.refresh(lead_source)
        return lead_source

    def delete(self, workspace_id: UUID, lead_source_id: UUID, actor_user_id: UUID | None) -> bool:
        lead_source = self.get(workspace_id, lead_source_id)
        if lead_source is None:
            return False
        old_value = snapshot(lead_source)
        self.lead_sources.soft_delete(lead_source, actor_user_id)
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="LeadSource",
            entity_id=lead_source.id,
            action="DELETE",
            old_value=old_value,
            new_value=snapshot(lead_source),
        )
        self.db.commit()
        return True
