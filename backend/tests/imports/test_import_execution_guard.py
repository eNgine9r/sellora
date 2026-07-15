from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.import_execution_guard import ImportExecutionGuard, ImportExecutionGuardError


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


def build_guard(tmp_path):
    source = tmp_path / "customers.csv"
    source.write_text("Name,Phone\nQA Customer,+380000000001\n", encoding="utf-8")
    job = SimpleNamespace(
        id=uuid4(),
        workspace_id=uuid4(),
        file_name=source.name,
        file_type="csv",
        file_path=str(source),
    )
    db = FakeDb()
    jobs = FakeJobs(job)
    audits = FakeAuditLogs()
    return job, source, db, jobs, audits


def test_persisted_signature_survives_new_guard_instance(tmp_path) -> None:
    job, _source, db, jobs, audits = build_guard(tmp_path)
    mapping = {"name": "Name", "phone": "Phone"}
    options = {"duplicate_policy": "SKIP"}

    first_process = ImportExecutionGuard(db, jobs=jobs, audit_logs=audits)
    first_process.record_successful_dry_run(
        workspace_id=job.workspace_id,
        job_id=job.id,
        entity_type="customers",
        sheet_name="CSV",
        column_mapping=mapping,
        options=options,
        actor_user_id=uuid4(),
        total_rows=1,
    )

    second_process = ImportExecutionGuard(db, jobs=jobs, audit_logs=audits)
    second_process.require_matching_dry_run(
        workspace_id=job.workspace_id,
        job_id=job.id,
        entity_type="customers",
        sheet_name="CSV",
        column_mapping=mapping,
        options=options,
    )

    assert db.commits == 1


@pytest.mark.parametrize(
    ("entity_type", "sheet_name", "mapping", "options"),
    [
        ("customers", "Other", {"name": "Name", "phone": "Phone"}, {"duplicate_policy": "SKIP"}),
        ("customers", "CSV", {"name": "Name"}, {"duplicate_policy": "SKIP"}),
        ("customers", "CSV", {"name": "Name", "phone": "Phone"}, {"duplicate_policy": "REJECT"}),
        ("products", "CSV", {"name": "Name", "phone": "Phone"}, {"duplicate_policy": "SKIP"}),
    ],
)
def test_changed_inputs_require_new_dry_run(tmp_path, entity_type, sheet_name, mapping, options) -> None:
    job, _source, db, jobs, audits = build_guard(tmp_path)
    guard = ImportExecutionGuard(db, jobs=jobs, audit_logs=audits)
    guard.record_successful_dry_run(
        workspace_id=job.workspace_id,
        job_id=job.id,
        entity_type="customers",
        sheet_name="CSV",
        column_mapping={"name": "Name", "phone": "Phone"},
        options={"duplicate_policy": "SKIP"},
        actor_user_id=uuid4(),
        total_rows=1,
    )

    with pytest.raises(ImportExecutionGuardError, match="inputs changed"):
        guard.require_matching_dry_run(
            workspace_id=job.workspace_id,
            job_id=job.id,
            entity_type=entity_type,
            sheet_name=sheet_name,
            column_mapping=mapping,
            options=options,
        )


def test_changed_file_bytes_require_new_dry_run(tmp_path) -> None:
    job, source, db, jobs, audits = build_guard(tmp_path)
    guard = ImportExecutionGuard(db, jobs=jobs, audit_logs=audits)
    mapping = {"name": "Name", "phone": "Phone"}
    guard.record_successful_dry_run(
        workspace_id=job.workspace_id,
        job_id=job.id,
        entity_type="customers",
        sheet_name="CSV",
        column_mapping=mapping,
        options=None,
        actor_user_id=uuid4(),
        total_rows=1,
    )

    source.write_text("Name,Phone\nChanged,+380000000002\n", encoding="utf-8")

    with pytest.raises(ImportExecutionGuardError, match="inputs changed"):
        guard.require_matching_dry_run(
            workspace_id=job.workspace_id,
            job_id=job.id,
            entity_type="customers",
            sheet_name="CSV",
            column_mapping=mapping,
            options=None,
        )


def test_missing_or_cross_workspace_approval_is_rejected(tmp_path) -> None:
    job, _source, db, jobs, audits = build_guard(tmp_path)
    guard = ImportExecutionGuard(db, jobs=jobs, audit_logs=audits)

    with pytest.raises(ImportExecutionGuardError, match="persisted dry-run"):
        guard.require_matching_dry_run(
            workspace_id=job.workspace_id,
            job_id=job.id,
            entity_type="customers",
            sheet_name="CSV",
            column_mapping={"name": "Name"},
            options=None,
        )

    with pytest.raises(ImportExecutionGuardError, match="not found"):
        guard.require_matching_dry_run(
            workspace_id=uuid4(),
            job_id=job.id,
            entity_type="customers",
            sheet_name="CSV",
            column_mapping={"name": "Name"},
            options=None,
        )
