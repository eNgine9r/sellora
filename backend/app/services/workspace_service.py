from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.workspace import Workspace
from app.repositories.audit_log_repository import AuditLogRepository
from app.schemas.workspace import WorkspaceSettingsUpdate
from app.services.business_utils import snapshot


class WorkspaceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit_logs = AuditLogRepository(db)

    def get_settings(self, workspace_id: UUID) -> Workspace | None:
        return self.db.get(Workspace, workspace_id)

    def update_settings(self, workspace_id: UUID, payload: WorkspaceSettingsUpdate, actor_user_id: UUID | None) -> Workspace | None:
        workspace = self.get_settings(workspace_id)
        if workspace is None or not workspace.is_active:
            return None
        old_value = snapshot(workspace)
        changes = payload.model_dump(exclude_unset=True)
        currency_changed = "currency_code" in changes and changes["currency_code"] is not None and changes["currency_code"].value != workspace.currency_code
        if "name" in changes and changes["name"] is not None:
            workspace.name = changes["name"]
        if "currency_code" in changes and changes["currency_code"] is not None:
            workspace.currency_code = changes["currency_code"].value
        action = "WORKSPACE_CURRENCY_UPDATE" if currency_changed else "WORKSPACE_UPDATE"
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="Workspace", entity_id=workspace.id, action=action, old_value=old_value, new_value=snapshot(workspace))
        self.db.commit()
        self.db.refresh(workspace)
        return workspace
