from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.workspace_memo import WorkspaceMemo


class WorkspaceMemoRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_workspace(self, workspace_id: UUID, limit: int = 300) -> list[WorkspaceMemo]:
        stmt = (select(WorkspaceMemo)
                .where(WorkspaceMemo.workspace_id == workspace_id, WorkspaceMemo.deleted_at.is_(None))
                .order_by(WorkspaceMemo.is_pinned.desc(), WorkspaceMemo.created_at.desc(), WorkspaceMemo.id.desc())
                .limit(limit))
        return list(self.db.scalars(stmt).all())

    def get(self, workspace_id: UUID, memo_id: UUID) -> WorkspaceMemo | None:
        return self.db.scalar(select(WorkspaceMemo).where(
            WorkspaceMemo.id == memo_id,
            WorkspaceMemo.workspace_id == workspace_id,
            WorkspaceMemo.deleted_at.is_(None),
        ))

    def add(self, memo: WorkspaceMemo) -> WorkspaceMemo:
        self.db.add(memo)
        self.db.flush()
        return memo
