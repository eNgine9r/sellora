"""Regression for stale NP tracking: 10 unverified TTNs must not starve all other shipments."""
from datetime import UTC, datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy.dialects import postgresql


def worker():
    from importlib import import_module
    return import_module("app.services.nova_poshta_tracking_worker")


def test_selection_is_ordered_by_last_attempt_and_is_workspace_scoped():
    module = worker()
    class DB:
        statement = None
        def execute(self, stmt):
            self.statement = stmt
            return SimpleNamespace(all=lambda: [])
    db = DB()
    assert module.pending_tracking_ids(db, now=datetime.now(UTC)) == []
    sql = str(db.statement.compile(dialect=postgresql.dialect()))
    assert "LEFT OUTER JOIN" in sql
    assert "audit_logs" in sql
    assert "max(audit_logs.created_at)" in sql
    assert "anon_1.last_attempt" in sql
    assert "anon_1.workspace_id = shipments.workspace_id" in sql
    assert "anon_1.entity_id = CAST(shipments.id AS VARCHAR)" in sql


def test_unknown_provider_status_is_unverified_not_synced(monkeypatch):
    module = worker()
    workspace_id = uuid4()
    rows = [(workspace_id, uuid4()), (workspace_id, uuid4())]
    class Lock:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def scalar(self, *_args, **_kwargs): return True
        def execute(self, *_args, **_kwargs): return None
    class DB:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def execute(self, _stmt): return SimpleNamespace(all=lambda: rows)
        def scalar(self, _stmt):
            return SimpleNamespace(status="CREATED", nova_poshta_synced_at=None)
    responses = [
        SimpleNamespace(success=True, manual_review_required=True, synced_at=None),
        SimpleNamespace(success=True, manual_review_required=False, synced_at=datetime.now(UTC)),
    ]
    class Provider:
        def sync_status(self, *_args): return responses.pop(0)
    monkeypatch.setattr(module, "engine", SimpleNamespace(connect=Lock))
    monkeypatch.setattr(module, "SessionLocal", DB)
    monkeypatch.setattr(module, "enabled", lambda: True)
    monkeypatch.setattr(module, "NovaPoshtaProviderShipmentService", lambda _db: Provider())
    stats = module.run_once()
    assert stats["eligible"] == 2
    assert stats["checked"] == 2
    assert stats["synced"] == 1
    assert stats["unverified"] == 1
    assert stats["failed"] == 0


def test_provider_code_3_has_daily_cooldown_in_candidate_sql():
    module = worker()
    class DB:
        statement = None
        def execute(self, stmt):
            self.statement = stmt
            return SimpleNamespace(all=lambda: [])
    db = DB()
    assert module.pending_tracking_ids(db, now=datetime.now(UTC)) == []
    sql = str(db.statement.compile(dialect=postgresql.dialect()))
    assert 'last_not_found' in sql
    assert 'provider_status_code' in sql
    assert 'new_value' in sql
    assert module.NOT_FOUND_RETRY_INTERVAL.total_seconds() == 24 * 3600
