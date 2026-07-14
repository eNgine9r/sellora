from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.import_job import ImportJob, ImportJobStatus
from app.schemas.import_center import (
    ImportReportResponse,
    ImportValidationIssue,
    ImportValidationReport,
    SuggestMappingResponse,
)
from app.services.import_center_service import (
    IMPORT_ALLOWED_SUFFIXES,
    ExcelParserService,
    HistoricalImportService,
    ImportService as LocalImportService,
    ImportServiceError,
    issue,
    safe_job_snapshot,
)
from app.services.import_source_storage import ImportSourceStorage, ImportSourceStorageError


PILOT_UNSUPPORTED_ENTITY_TYPES = {"shipments"}
HISTORICAL_ORDER_IGNORED_FIELDS = {
    "tracking_number",
    "carrier",
    "city",
    "warehouse",
}


def ensure_pilot_entity_type(entity_type: str) -> None:
    if entity_type in PILOT_UNSUPPORTED_ENTITY_TYPES:
        raise ImportServiceError(
            "Shipments import is not supported in the controlled pilot; create shipment drafts separately"
        )


def pilot_safe_mapping(entity_type: str, mapping: dict[str, str]) -> dict[str, str]:
    """Return the mapping that the controlled pilot is allowed to execute.

    Historical order imports deliberately ignore delivery fields. This prevents
    an old spreadsheet from creating shipment records or triggering delivery
    side effects. Shipment import remains explicitly disabled for the pilot.
    """

    ensure_pilot_entity_type(entity_type)
    if entity_type != "orders_history":
        return dict(mapping)
    return {
        field: column
        for field, column in mapping.items()
        if field not in HISTORICAL_ORDER_IGNORED_FIELDS
    }


def historical_status_issues(
    rows: list[dict],
    mapping: dict[str, str],
) -> list[ImportValidationIssue]:
    """Reject unknown historical status values instead of silently defaulting."""

    issues: list[ImportValidationIssue] = []
    status_fields = (
        ("order_status", HistoricalImportService.order_status_aliases),
        ("payment_status", HistoricalImportService.payment_status_aliases),
    )
    for row_number, row in enumerate(rows, start=2):
        for field, aliases in status_fields:
            column = mapping.get(field)
            if not column:
                continue
            raw_value = row.get(column)
            text = str(raw_value).strip().lower() if raw_value not in (None, "") else ""
            if text and text not in aliases:
                issues.append(
                    issue(
                        row_number,
                        "ERROR",
                        field,
                        f"Unsupported {field}: {text}",
                        raw_value,
                        None,
                    )
                )
    return issues


def append_validation_issues(
    report: ImportValidationReport,
    extra_issues: list[ImportValidationIssue],
) -> ImportValidationReport:
    if not extra_issues:
        return report
    report.issues.extend(extra_issues)
    report.errors.extend(item.message for item in extra_issues)
    report.is_valid = False
    return report


def append_report_issues(
    report: ImportReportResponse,
    extra_issues: list[ImportValidationIssue],
) -> ImportReportResponse:
    if not extra_issues:
        return report

    existing_rows = set(report.errors_by_row)
    for item in extra_issues:
        row_number = item.row_number or 0
        report.errors_by_row.setdefault(row_number, []).append(item)
        existing_rows.add(row_number)
    report.sample_errors.extend(extra_issues[: max(0, 10 - len(report.sample_errors))])
    report.errors_count += len(extra_issues)
    report.error_rows = len(existing_rows)
    report.invalid_rows = max(report.invalid_rows, report.error_rows)
    report.valid_rows = max(report.total_rows - report.error_rows, 0)
    report.ready_to_import_rows = 0
    report.estimated_entities_to_create = 0
    return report


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

    def suggest_mapping(
        self,
        workspace_id: UUID,
        job_id: UUID,
        sheet_name: str,
        entity_type: str,
    ) -> SuggestMappingResponse:
        ensure_pilot_entity_type(entity_type)
        response = super().suggest_mapping(workspace_id, job_id, sheet_name, entity_type)
        if entity_type != "orders_history":
            return response

        removed_columns = [
            response.suggested_mapping[field]
            for field in HISTORICAL_ORDER_IGNORED_FIELDS
            if field in response.suggested_mapping
        ]
        response.suggested_mapping = pilot_safe_mapping(entity_type, response.suggested_mapping)
        response.confidence = {
            field: confidence
            for field, confidence in response.confidence.items()
            if field in response.suggested_mapping
        }
        response.unmapped_columns = list(
            dict.fromkeys([*response.unmapped_columns, *removed_columns])
        )
        return response

    def _historical_issues(
        self,
        workspace_id: UUID,
        job_id: UUID,
        entity_type: str,
        sheet_name: str,
        safe_mapping: dict[str, str],
    ) -> list[ImportValidationIssue]:
        if entity_type != "orders_history":
            return []
        job = self._job(workspace_id, job_id)
        _columns, rows = self.parser.read_rows(job.file_path, sheet_name)
        return historical_status_issues(rows, safe_mapping)

    def validate(
        self,
        workspace_id: UUID,
        job_id: UUID,
        entity_type: str,
        sheet_name: str,
        column_mapping: dict[str, str],
        actor_user_id: UUID | None,
        options: dict | None = None,
    ) -> ImportValidationReport:
        safe_mapping = pilot_safe_mapping(entity_type, column_mapping)
        report = super().validate(
            workspace_id,
            job_id,
            entity_type,
            sheet_name,
            safe_mapping,
            actor_user_id,
            options,
        )
        return append_validation_issues(
            report,
            self._historical_issues(workspace_id, job_id, entity_type, sheet_name, safe_mapping),
        )

    def dry_run(
        self,
        workspace_id: UUID,
        job_id: UUID,
        entity_type: str,
        sheet_name: str,
        column_mapping: dict[str, str],
        actor_user_id: UUID | None = None,
        options: dict | None = None,
    ) -> ImportReportResponse:
        safe_mapping = pilot_safe_mapping(entity_type, column_mapping)
        report = super().dry_run(
            workspace_id,
            job_id,
            entity_type,
            sheet_name,
            safe_mapping,
            actor_user_id,
            options,
        )
        strict_issues = self._historical_issues(
            workspace_id,
            job_id,
            entity_type,
            sheet_name,
            safe_mapping,
        )
        append_report_issues(report, strict_issues)
        if strict_issues:
            job = self._job(workspace_id, job_id)
            job.status = ImportJobStatus.FAILED.value
            self.db.commit()
        return report

    def execute(
        self,
        workspace_id: UUID,
        job_id: UUID,
        entity_type: str,
        sheet_name: str,
        column_mapping: dict[str, str],
        mode: str,
        actor_user_id: UUID | None,
        dry_run: bool = False,
        options: dict | None = None,
    ):
        return super().execute(
            workspace_id,
            job_id,
            entity_type,
            sheet_name,
            pilot_safe_mapping(entity_type, column_mapping),
            mode,
            actor_user_id,
            dry_run,
            options,
        )
