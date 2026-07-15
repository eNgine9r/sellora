from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.import_job import ImportJobStatus
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.import_center_repository import ImportJobRepository


class AtomicImportSession:
    """Session proxy that prevents nested services from committing an import early.

    Existing domain services may call ``commit()`` as part of normal interactive
    workflows. During an Import Center execution those calls must only flush;
    the API transaction boundary performs the one real commit after every row
    and side effect has succeeded.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def commit(self) -> None:
        self._session.flush()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._session, name)


def persist_rolled_back_import(
    db: Session,
    *,
    workspace_id: UUID,
    job_id: UUID,
    actor_user_id: UUID | None,
    total_rows: int,
    reason: str,
) -> None:
    """Persist only the failed job state after all business writes were rolled back."""

    job = ImportJobRepository(db).get(workspace_id, job_id)
    if job is None:
        return
    job.status = ImportJobStatus.FAILED.value
    job.total_rows = total_rows
    job.processed_rows = 0
    job.success_rows = 0
    job.failed_rows = total_rows
    job.completed_at = None
    AuditLogRepository(db).create(
        workspace_id=workspace_id,
        user_id=actor_user_id,
        entity_type="ImportJob",
        entity_id=job_id,
        action="IMPORT_ROLLED_BACK",
        new_value={
            "total_rows": total_rows,
            "business_writes_committed": False,
            "reason": reason[:500],
        },
    )
    db.commit()
    db.refresh(job)
