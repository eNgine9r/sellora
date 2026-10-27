from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.workspace_memo import WorkspaceMemo
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.workspace_memo_repository import WorkspaceMemoRepository
from app.schemas.workspace_memo import WorkspaceMemoCreate, WorkspaceMemoUpdate


class WorkspaceMemoService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.memos = WorkspaceMemoRepository(db)
        self.audit = AuditLogRepository(db)

    def list(self, workspace_id: UUID) -> list[WorkspaceMemo]:
        return self.memos.list_for_workspace(workspace_id)

    def create(self, workspace_id: UUID, payload: WorkspaceMemoCreate, user_id: UUID) -> WorkspaceMemo:
        memo = self.memos.add(WorkspaceMemo(
            workspace_id=workspace_id, **payload.model_dump(), created_by=user_id, updated_by=user_id,
        ))
        self._log(workspace_id, memo.id, user_id, "CREATE", memo.kind)
        self.db.commit()
        self.db.refresh(memo)
        return memo

    def update(self, workspace_id: UUID, memo_id: UUID, payload: WorkspaceMemoUpdate, user_id: UUID) -> WorkspaceMemo | None:
        memo = self.memos.get(workspace_id, memo_id)
        if memo is None:
            return None
        changes = payload.model_dump(exclude_unset=True)
        if ("title" in changes and changes["title"] is None) or ("body" in changes and changes["body"] is None) or ("is_pinned" in changes and changes["is_pinned"] is None) or ("is_done" in changes and changes["is_done"] is None):
            raise ValueError("Required fields cannot be null")
        if memo.kind != "TASK" and (changes.get("due_on") is not None or changes.get("is_done") is not None):
            raise ValueError("Only tasks may have a deadline or completion state")
        for field, value in changes.items():
            setattr(memo, field, value)
        memo.updated_by = user_id
        self._log(workspace_id, memo.id, user_id, "UPDATE", memo.kind)
        self.db.commit()
        self.db.refresh(memo)
        return memo

    def delete(self, workspace_id: UUID, memo_id: UUID, user_id: UUID) -> bool:
        memo = self.memos.get(workspace_id, memo_id)
        if memo is None:
            return False
        memo.deleted_at = datetime.now(UTC)
        memo.deleted_by = user_id
        self._log(workspace_id, memo.id, user_id, "DELETE", memo.kind)
        self.db.commit()
        return True

    def _log(self, workspace_id: UUID, memo_id: UUID, user_id: UUID, action: str, kind: str) -> None:
        # Do not copy free-text note content into audit logs.
        self.audit.create(
            workspace_id=workspace_id, user_id=user_id, entity_type="WorkspaceMemo",
            entity_id=memo_id, action=action, new_value={"kind": kind, "action": action},
        )
