from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.import_job import ImportJob, ImportJobStatus
from app.services.import_center_service import (
    IMPORT_ALLOWED_SUFFIXES,
    ExcelParserService,
    ImportService as LocalImportService,
    ImportServiceError,
    safe_job_snapshot,
)
from app.services.import_source_storage import ImportSourceStorage, ImportSourceStorageError


class DurableExcelParserService:
    """Materializes a private object only for the duration of parser work."""

    def __init__(self, parser: ExcelParserService, storage: ImportSourceStorage) -> None:
        self.parser = parser
        self.storage = storage

    def list_sheets(self, location: str) -> list[str]:
        with self.storage.materialize(location) as file_path:
            return self.parser.list_sheets(file_path)

    def preview(self, location: str, sheet_name: str, limit: int = 20) -> tuple[list[str], list[dict]]:
        with self.storage.materialize(location) as file_path:
            return self.parser.preview(file_path, sheet_name, limit)

    def read_rows(self, location: str, sheet_name: str, limit: int | None = None) -> tuple[list[str], list[dict]]:
        with self.storage.materialize(location) as file_path:
            return self.parser.read_rows(file_path, sheet_name, limit)


class DurableImportService(LocalImportService):
    """Import Center service with restart-safe private source storage."""

    def __init__(self, db: Session, source_storage: ImportSourceStorage | None = None) -> None:
        super().__init__(db)
        self.source_storage = source_storage or ImportSourceStorage()
        self.parser = DurableExcelParserService(self.parser, self.source_storage)

    async def upload(self, workspace_id: UUID, file: UploadFile, actor_user_id: UUID | None) -> ImportJob:
        safe_name = self._safe_filename(file.filename or "import.xlsx")
        suffix = Path(safe_name).suffix.lower()
        if suffix not in IMPORT_ALLOWED_SUFFIXES:
            raise ImportServiceError("Only .xlsx and .csv files are supported")

        content = await file.read()
        self._validate_upload_content(safe_name, content)
        if len(content) > min(get_settings().import_max_file_size_mb, 10) * 1024 * 1024:
            raise ImportServiceError("Import file exceeds size limit")

        job = self.jobs.create(
            ImportJob(
                workspace_id=workspace_id,
                file_name=safe_name,
                file_type=suffix.removeprefix("."),
                file_path="pending",
                status=ImportJobStatus.UPLOADED.value,
                created_by=actor_user_id,
            )
        )
        location: str | None = None
        try:
            location = self.source_storage.store(workspace_id, job.id, safe_name, content)
            self.source_storage.assert_workspace_job_location(location, workspace_id, job.id)
            job.file_path = location
            self.audit_logs.create(
                workspace_id=workspace_id,
                user_id=actor_user_id,
                entity_type="ImportJob",
                entity_id=job.id,
                action="IMPORT_UPLOAD",
                new_value=safe_job_snapshot(job),
            )
            self.db.commit()
            self.db.refresh(job)
            return job
        except ImportSourceStorageError as exc:
            self.db.rollback()
            raise ImportServiceError(str(exc)) from exc
        except Exception:
            self.db.rollback()
            if location is not None:
                try:
                    self.source_storage.delete(location)
                except ImportSourceStorageError:
                    pass
            raise
