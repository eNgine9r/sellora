from __future__ import annotations

import hmac
import json
from hashlib import sha256
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.import_job import ImportJob
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.import_center_repository import ImportJobRepository
from app.services.import_source_storage import ImportSourceStorage, ImportSourceStorageError


IMPORT_DRY_RUN_APPROVED_ACTION = "IMPORT_DRY_RUN_APPROVED"


class ImportExecutionGuardError(ValueError):
    pass


def _file_fingerprint(path_value: str, source_storage: ImportSourceStorage | None = None) -> tuple[str, int]:
    storage = source_storage or ImportSourceStorage()
    try:
        content = storage.read_bytes(path_value)
    except ImportSourceStorageError as exc:
        raise ImportExecutionGuardError("Import source file is unavailable; upload and dry-run again") from exc
    return sha256(content).hexdigest(), len(content)


def build_import_execution_signature(
    job: ImportJob,
    *,
    entity_type: str,
    sheet_name: str,
    column_mapping: dict[str, str],
    options: dict[str, Any] | None,
    source_storage: ImportSourceStorage | None = None,
) -> tuple[str, str, int]:
    storage = source_storage or ImportSourceStorage()
    try:
        storage.assert_workspace_job_location(job.file_path, job.workspace_id, job.id)
    except ImportSourceStorageError as exc:
        raise ImportExecutionGuardError("Import source location does not match the workspace and job") from exc
    file_sha256, file_size = _file_fingerprint(job.file_path, storage)
    payload = {
        "workspace_id": str(job.workspace_id),
        "job_id": str(job.id),
        "file_name": job.file_name,
        "file_type": job.file_type,
        "file_sha256": file_sha256,
        "file_size": file_size,
        "entity_type": entity_type,
        "sheet_name": sheet_name,
        "column_mapping": dict(sorted(column_mapping.items())),
        "options": options or {},
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return sha256(serialized.encode("utf-8")).hexdigest(), file_sha256, file_size


class ImportExecutionGuard:
    """Durable dry-run approval gate backed by workspace-scoped audit records.

    The approval survives Render process restarts because the signature is stored
    in PostgreSQL and source bytes are stored in durable private storage. Execute
    recomputes the signature from the immutable job identity, current file bytes,
    sheet, mapping, and options.
    """

    def __init__(
        self,
        db: Session,
        *,
        jobs: ImportJobRepository | None = None,
        audit_logs: AuditLogRepository | None = None,
        source_storage: ImportSourceStorage | None = None,
    ) -> None:
        self.db = db
        self.jobs = jobs or ImportJobRepository(db)
        self.audit_logs = audit_logs or AuditLogRepository(db)
        self.source_storage = source_storage or ImportSourceStorage()

    def record_successful_dry_run(
        self,
        *,
        workspace_id: UUID,
        job_id: UUID,
        entity_type: str,
        sheet_name: str,
        column_mapping: dict[str, str],
        options: dict[str, Any] | None,
        actor_user_id: UUID | None,
        total_rows: int,
    ) -> str:
        job = self._job(workspace_id, job_id)
        signature, file_sha256, file_size = build_import_execution_signature(
            job,
            entity_type=entity_type,
            sheet_name=sheet_name,
            column_mapping=column_mapping,
            options=options,
            source_storage=self.source_storage,
        )
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="ImportJob",
            entity_id=job_id,
            action=IMPORT_DRY_RUN_APPROVED_ACTION,
            new_value={
                "signature": signature,
                "file_sha256": file_sha256,
                "file_size": file_size,
                "entity_type": entity_type,
                "sheet_name": sheet_name,
                "mapping_fields": sorted(column_mapping),
                "total_rows": total_rows,
            },
        )
        self.db.commit()
        return signature

    def require_matching_dry_run(
        self,
        *,
        workspace_id: UUID,
        job_id: UUID,
        entity_type: str,
        sheet_name: str,
        column_mapping: dict[str, str],
        options: dict[str, Any] | None,
    ) -> None:
        job = self._job(workspace_id, job_id)
        approved = self.audit_logs.latest_action_value(
            workspace_id=workspace_id,
            entity_type="ImportJob",
            entity_id=job_id,
            action=IMPORT_DRY_RUN_APPROVED_ACTION,
        )
        approved_signature = approved.get("signature") if approved else None
        if not isinstance(approved_signature, str) or not approved_signature:
            raise ImportExecutionGuardError("Successful persisted dry-run is required before import execution")
        current_signature, _file_sha256, _file_size = build_import_execution_signature(
            job,
            entity_type=entity_type,
            sheet_name=sheet_name,
            column_mapping=column_mapping,
            options=options,
            source_storage=self.source_storage,
        )
        if not hmac.compare_digest(approved_signature, current_signature):
            raise ImportExecutionGuardError(
                "Import inputs changed after dry-run; run dry-run again with the current workspace, file, sheet, mapping, and options"
            )

    def _job(self, workspace_id: UUID, job_id: UUID) -> ImportJob:
        job = self.jobs.get(workspace_id, job_id)
        if job is None:
            raise ImportExecutionGuardError("Import job not found")
        return job
