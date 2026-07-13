from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


DEMO_WORKSPACE_CREATE_ACTION = "DEMO_WORKSPACE_CREATE"


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

    def has_demo_workspace_provenance(
        self,
        workspace_id: UUID,
        *,
        creator_user_id: UUID | None = None,
    ) -> bool:
        """Return True only for workspaces created by the server-side demo flow.

        Workspace names, slugs, and record contents are intentionally ignored.
        The provenance marker is the immutable audit event emitted in the same
        database transaction that creates and seeds the demo workspace.
        """

        stmt = select(AuditLog.id).where(
            AuditLog.workspace_id == workspace_id,
            AuditLog.entity_type == "Workspace",
            AuditLog.entity_id == str(workspace_id),
            AuditLog.action == DEMO_WORKSPACE_CREATE_ACTION,
        )
        if creator_user_id is not None:
            stmt = stmt.where(AuditLog.user_id == creator_user_id)
        return self.db.execute(stmt.limit(1)).scalar_one_or_none() is not None
