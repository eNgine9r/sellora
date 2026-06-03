from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditLogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID | None,
        entity_type: str,
        entity_id: UUID | str,
        action: str,
        old_value: dict[str, Any] | None = None,
        new_value: dict[str, Any] | None = None,
    ) -> AuditLog:
        audit_log = AuditLog(
            workspace_id=workspace_id,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=str(entity_id),
            action=action,
            old_value=old_value,
            new_value=new_value,
        )
        self.db.add(audit_log)
        return audit_log
