from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.import_job import ImportJobStatus
from app.schemas.import_center import ImportReportResponse, ImportValidationIssue, ImportValidationReport
from app.services.import_center_service import ImportServiceError, issue
from app.services.import_durable_service import (
    DurableImportService,
    append_report_issues,
    append_validation_issues,
    pilot_safe_mapping,
)
from app.services.import_source_storage import ImportSourceStorage


SAFE_SIGNED_NUMBER = re.compile(r"^[+-]?\d+(?:[.,]\d+)?$")
SAFE_INTERNATIONAL_PHONE = re.compile(r"^\+\d{7,15}$")


def is_formula_injection_risk(value: object) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text:
        return False
    if text[0] not in {"=", "+", "-", "@"}:
        return False
    if SAFE_SIGNED_NUMBER.fullmatch(text) or SAFE_INTERNATIONAL_PHONE.fullmatch(text):
        return False
    return True


def formula_injection_issues(
    rows: list[dict],
    mapping: dict[str, str],
) -> list[ImportValidationIssue]:
    issues: list[ImportValidationIssue] = []
    for row_number, row in enumerate(rows, start=2):
        for field, column in mapping.items():
            if not column:
                continue
            raw_value = row.get(column)
            if is_formula_injection_risk(raw_value):
                issues.append(
                    issue(
                        row_number,
                        "ERROR",
                        field,
                        "Formula-prefixed CSV values are not allowed",
                        raw_value,
                        None,
                    )
                )
    return issues


class PilotSafeImportService(DurableImportService):
    """Durable Import Center service with controlled-pilot input safety."""

    def __init__(self, db: Session, source_storage: ImportSourceStorage | None = None) -> None:
        super().__init__(db, source_storage=source_storage)

    def _formula_issues(
        self,
        workspace_id: UUID,
        job_id: UUID,
        entity_type: str,
        sheet_name: str,
        column_mapping: dict[str, str],
    ) -> list[ImportValidationIssue]:
        safe_mapping = pilot_safe_mapping(entity_type, column_mapping)
        job = self._job(workspace_id, job_id)
        _columns, rows = self.parser.read_rows(job.file_path, sheet_name)
        return formula_injection_issues(rows, safe_mapping)

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
        report = super().validate(
            workspace_id,
            job_id,
            entity_type,
            sheet_name,
            column_mapping,
            actor_user_id,
            options,
        )
        return append_validation_issues(
            report,
            self._formula_issues(
                workspace_id,
                job_id,
                entity_type,
                sheet_name,
                column_mapping,
            ),
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
        report = super().dry_run(
            workspace_id,
            job_id,
            entity_type,
            sheet_name,
            column_mapping,
            actor_user_id,
            options,
        )
        unsafe = self._formula_issues(
            workspace_id,
            job_id,
            entity_type,
            sheet_name,
            column_mapping,
        )
        append_report_issues(report, unsafe)
        if unsafe:
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
        if not dry_run and self._formula_issues(
            workspace_id,
            job_id,
            entity_type,
            sheet_name,
            column_mapping,
        ):
            raise ImportServiceError(
                "Formula-prefixed values are not allowed; correct the source file and run dry-run again"
            )
        return super().execute(
            workspace_id,
            job_id,
            entity_type,
            sheet_name,
            column_mapping,
            mode,
            actor_user_id,
            dry_run,
            options,
        )
