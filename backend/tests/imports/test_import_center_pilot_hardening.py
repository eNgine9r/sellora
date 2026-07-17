from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import asyncio

import pytest

from app.models.import_job import ImportJobStatus
from app.models.role import RoleName
from app.dependencies.rbac import require_roles
from app.services.import_center_service import (
    ExcelParserService,
    ImportService,
    ImportServiceError,
    dry_run_signature,
    escape_csv_formula,
)
from tests.test_import_center import FakeUploadFile, _import_service


def test_import_upload_rejects_macro_binary_and_non_utf8_files(tmp_path, monkeypatch) -> None:
    service = _import_service(tmp_path)
    service.jobs.job = None
    monkeypatch.setattr("app.services.import_center_service.get_settings", lambda: SimpleNamespace(import_max_file_size_mb=20, import_storage_path=str(tmp_path)))

    with pytest.raises(ImportServiceError, match="Only .xlsx and .csv"):
        asyncio.run(async_upload(service, "macro.xlsm", b"PKfake"))
    with pytest.raises(ImportServiceError, match="valid workbook"):
        asyncio.run(async_upload(service, "customers.xlsx", b"not a zip"))
    with pytest.raises(ImportServiceError, match="binary|unsupported|UTF-8"):
        asyncio.run(async_upload(service, "customers.csv", b"\xff\xfe\x00"))


async def async_upload(service: ImportService, filename: str, content: bytes):
    return await service.upload(uuid4(), FakeUploadFile(filename, content), actor_user_id=uuid4())


def test_csv_parser_supports_semicolon_and_rejects_duplicate_headers(tmp_path) -> None:
    valid = tmp_path / "valid.csv"
    valid.write_text("Телефон;Імʼя\n063000000;Синтетична клієнтка\n", encoding="utf-8")
    columns, rows = ExcelParserService().read_rows(str(valid), "CSV")

    assert columns == ["Телефон", "Імʼя"]
    assert rows[0]["Телефон"] == "063000000"

    duplicate = tmp_path / "duplicate.csv"
    duplicate.write_text("Phone, phone \n1,2\n", encoding="utf-8")
    with pytest.raises(ImportServiceError, match="Duplicate header"):
        ExcelParserService().read_rows(str(duplicate), "CSV")


def test_dry_run_sets_validated_status_and_execute_requires_it(tmp_path) -> None:
    service = _import_service(tmp_path)
    job = service.jobs.job

    with pytest.raises(ImportServiceError, match="Successful dry-run"):
        service.execute(job.workspace_id, job.id, "customers", "Customers", {"name": "Name", "phone": "Phone"}, "create_only", actor_user_id=uuid4())

    report = service.dry_run(job.workspace_id, job.id, "customers", "Customers", {"name": "Name", "phone": "Phone"}, actor_user_id=uuid4())

    assert report.error_rows == 0
    assert job.status == ImportJobStatus.VALIDATED.value
    imported = service.execute(job.workspace_id, job.id, "customers", "Customers", {"name": "Name", "phone": "Phone"}, "create_only", actor_user_id=uuid4())
    assert imported.processed_rows == 2


def test_dry_run_signature_is_workspace_and_mapping_scoped(tmp_path) -> None:
    service = _import_service(tmp_path)
    job = service.jobs.job
    base = dry_run_signature(job, "customers", "Customers", {"name": "Name", "phone": "Phone"}, {"duplicate_policy": "SKIP"})
    changed_mapping = dry_run_signature(job, "customers", "Customers", {"name": "Name"}, {"duplicate_policy": "SKIP"})
    changed_policy = dry_run_signature(job, "customers", "Customers", {"name": "Name", "phone": "Phone"}, {"duplicate_policy": "REJECT"})

    assert base != changed_mapping
    assert base != changed_policy


def test_error_report_csv_formula_escaping() -> None:
    assert escape_csv_formula("=HYPERLINK('x')").startswith("'")
    assert escape_csv_formula("+SUM(1,1)").startswith("'")
    assert escape_csv_formula("@cmd").startswith("'")
    assert escape_csv_formula("Synthetic value") == "Synthetic value"


def test_analyst_execute_denied_by_import_rbac_guard() -> None:
    workspace_id = uuid4()
    analyst = SimpleNamespace(workspaces=[SimpleNamespace(workspace_id=workspace_id, workspace=SimpleNamespace(is_active=True), role=SimpleNamespace(name=RoleName.ANALYST.value))])

    with pytest.raises(Exception):
        require_roles(RoleName.OWNER)(analyst, workspace_id)
