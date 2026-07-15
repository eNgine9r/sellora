from types import SimpleNamespace
from uuid import uuid4

from app.services.import_atomic_execution import AtomicImportSession, persist_rolled_back_import


class FakeSession:
    def __init__(self) -> None:
        self.flushes = 0
        self.commits = 0
        self.refreshed = []

    def flush(self) -> None:
        self.flushes += 1

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, value) -> None:
        self.refreshed.append(value)

    def execute(self, statement):
        return statement


class FakeJobs:
    def __init__(self, job) -> None:
        self.job = job

    def get(self, workspace_id, job_id):
        return self.job if self.job.workspace_id == workspace_id and self.job.id == job_id else None


class FakeAudit:
    def __init__(self) -> None:
        self.records = []

    def create(self, **kwargs):
        self.records.append(kwargs)


def test_atomic_session_converts_nested_commit_to_flush() -> None:
    session = FakeSession()
    atomic = AtomicImportSession(session)

    atomic.commit()
    atomic.execute("query")

    assert session.flushes == 1
    assert session.commits == 0


def test_persist_rolled_back_import_records_zero_committed_business_writes(monkeypatch) -> None:
    workspace_id = uuid4()
    job_id = uuid4()
    job = SimpleNamespace(
        id=job_id,
        workspace_id=workspace_id,
        status="IMPORTING",
        total_rows=2,
        processed_rows=1,
        success_rows=1,
        failed_rows=1,
        completed_at=object(),
    )
    session = FakeSession()
    jobs = FakeJobs(job)
    audit = FakeAudit()

    monkeypatch.setattr("app.services.import_atomic_execution.ImportJobRepository", lambda _db: jobs)
    monkeypatch.setattr("app.services.import_atomic_execution.AuditLogRepository", lambda _db: audit)

    persist_rolled_back_import(
        session,
        workspace_id=workspace_id,
        job_id=job_id,
        actor_user_id=uuid4(),
        total_rows=2,
        reason="controlled failure",
    )

    assert job.status == "FAILED"
    assert job.processed_rows == 0
    assert job.success_rows == 0
    assert job.failed_rows == 2
    assert job.completed_at is None
    assert session.commits == 1
    assert audit.records[0]["action"] == "IMPORT_ROLLED_BACK"
    assert audit.records[0]["new_value"]["business_writes_committed"] is False
