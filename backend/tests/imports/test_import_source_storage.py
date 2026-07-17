from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.services.import_center_service import ExcelParserService
from app.services.import_durable_service import DurableExcelParserService
from app.services.import_execution_guard import ImportExecutionGuard, ImportExecutionGuardError
from app.services.import_source_storage import ImportSourceStorage, ImportSourceStorageError


class FakeBucket:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.upload_options: dict[str, dict] = {}

    def upload(self, path: str, file, file_options: dict | None = None):
        if path in self.objects and (file_options or {}).get("upsert") != "true":
            raise RuntimeError("duplicate object")
        self.objects[path] = bytes(file)
        self.upload_options[path] = file_options or {}
        return {"path": path}

    def download(self, path: str) -> bytes:
        if path not in self.objects:
            raise RuntimeError("not found")
        return self.objects[path]

    def remove(self, paths: list[str]):
        for path in paths:
            self.objects.pop(path, None)
        return paths


class FakeDb:
    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1


class FakeJobs:
    def __init__(self, job) -> None:
        self.job = job

    def get(self, workspace_id, job_id):
        if workspace_id == self.job.workspace_id and job_id == self.job.id:
            return self.job
        return None


class FakeAuditLogs:
    def __init__(self) -> None:
        self.records: list[dict] = []

    def create(self, **kwargs):
        self.records.append(kwargs)
        return SimpleNamespace(**kwargs)

    def latest_action_value(self, *, workspace_id, entity_type, entity_id, action):
        for record in reversed(self.records):
            if (
                record["workspace_id"] == workspace_id
                and record["entity_type"] == entity_type
                and str(record["entity_id"]) == str(entity_id)
                and record["action"] == action
            ):
                return record["new_value"]
        return None


def supabase_settings() -> Settings:
    return Settings(
        import_storage_backend="supabase",
        import_storage_bucket="sellora-import-sources",
        supabase_url="https://example.supabase.co",
        supabase_secret_key="test-secret",
    )


def test_private_object_round_trip_materialization_and_delete() -> None:
    workspace_id = uuid4()
    job_id = uuid4()
    bucket = FakeBucket()
    storage = ImportSourceStorage(supabase_settings(), bucket=bucket)
    content = b"Name,Phone\nQA Customer,+380000000001\n"

    location = storage.store(workspace_id, job_id, "customers.csv", content)

    assert location == f"supabase://sellora-import-sources/{workspace_id}/{job_id}/customers.csv"
    assert storage.read_bytes(location) == content
    assert bucket.upload_options[f"{workspace_id}/{job_id}/customers.csv"]["content-type"] == "text/csv"
    assert bucket.upload_options[f"{workspace_id}/{job_id}/customers.csv"]["upsert"] == "false"

    with storage.materialize(location) as file_path:
        assert open(file_path, "rb").read() == content
    assert not __import__("pathlib").Path(file_path).exists()

    storage.delete(location)
    with pytest.raises(ImportSourceStorageError, match="unavailable"):
        storage.read_bytes(location)


def test_remote_location_is_bound_to_workspace_and_job() -> None:
    workspace_id = uuid4()
    job_id = uuid4()
    storage = ImportSourceStorage(supabase_settings(), bucket=FakeBucket())
    location = f"supabase://sellora-import-sources/{workspace_id}/{job_id}/customers.csv"

    storage.assert_workspace_job_location(location, workspace_id, job_id)

    with pytest.raises(ImportSourceStorageError, match="does not match"):
        storage.assert_workspace_job_location(location, uuid4(), job_id)
    with pytest.raises(ImportSourceStorageError, match="does not match"):
        storage.assert_workspace_job_location(location, workspace_id, uuid4())
    with pytest.raises(ImportSourceStorageError, match="bucket"):
        storage.read_bytes(location.replace("sellora-import-sources", "foreign-bucket"))


def test_parser_materializes_remote_csv_without_persisting_temp_file() -> None:
    workspace_id = uuid4()
    job_id = uuid4()
    bucket = FakeBucket()
    storage = ImportSourceStorage(supabase_settings(), bucket=bucket)
    location = storage.store(workspace_id, job_id, "customers.csv", b"Name,Phone\nQA,+380000000001\n")
    parser = DurableExcelParserService(ExcelParserService(), storage)

    assert parser.list_sheets(location) == ["CSV"]
    columns, rows = parser.read_rows(location, "CSV")

    assert columns == ["Name", "Phone"]
    assert rows == [{"Name": "QA", "Phone": "+380000000001"}]


def test_durable_approval_survives_new_service_instance_and_detects_mutation() -> None:
    workspace_id = uuid4()
    job_id = uuid4()
    bucket = FakeBucket()
    first_storage = ImportSourceStorage(supabase_settings(), bucket=bucket)
    location = first_storage.store(
        workspace_id,
        job_id,
        "customers.csv",
        b"Name,Phone\nQA Customer,+380000000001\n",
    )
    job = SimpleNamespace(
        id=job_id,
        workspace_id=workspace_id,
        file_name="customers.csv",
        file_type="csv",
        file_path=location,
    )
    db = FakeDb()
    jobs = FakeJobs(job)
    audits = FakeAuditLogs()
    mapping = {"name": "Name", "phone": "Phone"}

    first_process = ImportExecutionGuard(
        db,
        jobs=jobs,
        audit_logs=audits,
        source_storage=first_storage,
    )
    first_process.record_successful_dry_run(
        workspace_id=workspace_id,
        job_id=job_id,
        entity_type="customers",
        sheet_name="CSV",
        column_mapping=mapping,
        options={"duplicate_policy": "SKIP"},
        actor_user_id=uuid4(),
        total_rows=1,
    )

    second_storage = ImportSourceStorage(supabase_settings(), bucket=bucket)
    second_process = ImportExecutionGuard(
        db,
        jobs=jobs,
        audit_logs=audits,
        source_storage=second_storage,
    )
    second_process.require_matching_dry_run(
        workspace_id=workspace_id,
        job_id=job_id,
        entity_type="customers",
        sheet_name="CSV",
        column_mapping=mapping,
        options={"duplicate_policy": "SKIP"},
    )

    bucket.objects[f"{workspace_id}/{job_id}/customers.csv"] = b"Name,Phone\nChanged,+380000000002\n"
    with pytest.raises(ImportExecutionGuardError, match="inputs changed"):
        second_process.require_matching_dry_run(
            workspace_id=workspace_id,
            job_id=job_id,
            entity_type="customers",
            sheet_name="CSV",
            column_mapping=mapping,
            options={"duplicate_policy": "SKIP"},
        )
