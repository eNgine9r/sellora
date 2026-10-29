"""Run only against the explicitly created disposable subscription canary database."""
import importlib.util
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.workspace import Workspace
from app.models.workspace_subscription import WorkspaceSubscription
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.subscription_service import describe_subscription

pytestmark = pytest.mark.skipif(os.getenv("SELLORA_SUBSCRIPTIONS_DISPOSABLE_CANARY") != "YES", reason="explicit disposable subscription database required")


@pytest.fixture
def db():
    url = os.environ["DATABASE_URL"]
    assert make_url(url).database == "sellora_subscriptions_canary_isolated"
    engine = create_engine(url)
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()
    engine.dispose()


def workspace(db):
    record = Workspace(name="Synthetic subscription canary", slug=f"sub-canary-{uuid4().hex}", subscription_plan="enterprise")
    db.add(record)
    db.flush()
    return record


def subscription(current_workspace_id, **changes):
    start = datetime(2026, 10, 1, tzinfo=UTC)
    values = dict(workspace_id=current_workspace_id, plan_code="pilot", status="ACTIVE", current_period_start=start,
                  current_period_end=start + timedelta(days=30), cancel_at_period_end=False)
    values.update(changes)
    return WorkspaceSubscription(**values)


def test_persisted_subscription_is_workspace_scoped_and_existing_plan_does_not_enroll(db):
    first, second = workspace(db), workspace(db)
    repository = SubscriptionRepository(db)
    assert repository.get_for_workspace(first.id) is None
    assert repository.get_for_workspace(second.id) is None
    record = subscription(first.id)
    db.add(record)
    db.flush()
    assert repository.get_for_workspace(first.id).id == record.id
    assert repository.get_for_workspace(second.id) is None
    db.expire_all()
    persisted = repository.get_for_workspace(first.id)
    result = describe_subscription(first.id, persisted, now=persisted.current_period_end)
    assert result.status.value == "EXPIRED" and not result.has_current_term
    assert first.subscription_plan == "enterprise"


@pytest.mark.parametrize("changes", [
    {"status": "FREE"}, {"plan_code": "   "},
    {"current_period_end": datetime(2026, 9, 1, tzinfo=UTC)},
    {"status": "PAST_DUE", "cancel_at_period_end": True}, {"workspace_id": uuid4()},
])
def test_database_rejects_invalid_subscription_state(db, changes):
    current = workspace(db)
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.add(subscription(current.id, **changes))
            db.flush()


def test_one_current_subscription_per_workspace(db):
    current = workspace(db)
    db.add(subscription(current.id))
    db.flush()
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.add(subscription(current.id))
            db.flush()


def test_rls_is_enabled_and_populated_downgrade_preserves_records(db):
    current = workspace(db)
    db.add(subscription(current.id))
    db.flush()
    assert db.execute(text("SELECT relrowsecurity FROM pg_class WHERE oid = 'public.workspace_subscriptions'::regclass")).scalar_one()
    path = Path(__file__).resolve().parents[2] / "alembic/versions/202610290051_workspace_subscriptions.py"
    spec = importlib.util.spec_from_file_location("subscription_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with Operations.context(MigrationContext.configure(db.connection())):
        with pytest.raises(RuntimeError, match="data-preserving"):
            migration.downgrade()
    assert db.execute(select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == current.id)).scalar_one()
