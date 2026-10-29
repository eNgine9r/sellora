"""Real replay/race tests for the explicitly created disposable subscription DB."""
import importlib.util
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from queue import Queue
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, delete, func, select, text, update
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.models.subscription_payment_event_receipt import SubscriptionPaymentEventReceipt
from app.models.workspace import Workspace
from app.models.workspace_subscription import WorkspaceSubscription
from app.repositories.subscription_payment_event_repository import SubscriptionPaymentEventRepository
from app.schemas.subscription_payment_event import SubscriptionPaymentEvent
from app.services.subscription_payment_event_service import SubscriptionPaymentEventConflict, SubscriptionPaymentEventService

pytestmark = pytest.mark.skipif(os.getenv("SELLORA_SUBSCRIPTIONS_DISPOSABLE_CANARY") != "YES", reason="explicit disposable subscription database required")


@pytest.fixture(scope="module")
def engine():
    url = os.environ["DATABASE_URL"]
    assert make_url(url).database == "sellora_subscriptions_canary_isolated"
    assert make_url(url).get_backend_name() == "postgresql"
    instance = create_engine(url)
    yield instance
    instance.dispose()


@pytest.fixture
def db(engine):
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()


def workspace(db):
    record = Workspace(name="Synthetic receipt canary", slug=f"receipt-canary-{uuid4().hex}", subscription_plan="enterprise")
    db.add(record)
    db.flush()
    return record


def event(**changes):
    return replace(SubscriptionPaymentEvent(
        provider="synthetic", provider_account_id=f"merchant-{uuid4().hex}", external_event_id="evt-1",
        transaction_id="txn-1", event_type="payment.succeeded", amount=Decimal("120.50"),
        currency="UAH", occurred_at=datetime(2026, 10, 29, 12, 30, tzinfo=UTC),
    ), **changes)


def test_persisted_replay_is_exact_and_never_changes_workspace_or_subscription(db):
    first, second = workspace(db), workspace(db)
    start = datetime(2026, 10, 1, tzinfo=UTC)
    term = WorkspaceSubscription(workspace_id=first.id, plan_code="pilot", status="TRIALING",
                                 current_period_start=start, current_period_end=start + timedelta(days=30),
                                 cancel_at_period_end=True)
    db.add(term)
    db.flush()
    original_term = {column.name: getattr(term, column.name) for column in term.__table__.columns}
    service, incoming = SubscriptionPaymentEventService(db), event()
    receipt = service.record(first.id, incoming)
    receipt_id, received_at = receipt.id, receipt.received_at
    db.expire_all()
    replay = service.record(first.id, replace(incoming, amount=Decimal("120.5000000"),
                                            occurred_at=incoming.occurred_at.astimezone(timezone(timedelta(hours=3)))))
    assert replay.id == receipt_id and replay.received_at == received_at
    assert replay.amount == Decimal("120.500000")
    assert SubscriptionPaymentEventRepository(db).get_for_event(second.id, incoming.provider, incoming.provider_account_id, incoming.external_event_id) is None
    assert db.execute(select(func.count()).select_from(SubscriptionPaymentEventReceipt).where(SubscriptionPaymentEventReceipt.workspace_id == first.id)).scalar_one() == 1
    assert first.subscription_plan == "enterprise"
    assert {column.name: getattr(term, column.name) for column in term.__table__.columns} == original_term


def test_foreign_tenant_and_changed_transaction_conflicts_have_identical_generic_errors(db):
    first, second = workspace(db), workspace(db)
    service, incoming = SubscriptionPaymentEventService(db), event()
    original = service.record(first.id, incoming)
    with pytest.raises(SubscriptionPaymentEventConflict) as foreign:
        service.record(second.id, incoming)
    with pytest.raises(SubscriptionPaymentEventConflict) as changed:
        service.record(first.id, replace(incoming, amount=Decimal("120.51")))
    assert str(foreign.value) == str(changed.value) == "Payment event conflicts with an existing receipt"
    assert service.record(first.id, incoming).id == original.id


def test_provider_and_account_namespace_same_external_event_independently(db):
    current = workspace(db)
    service, incoming = SubscriptionPaymentEventService(db), event()
    receipts = [service.record(current.id, candidate) for candidate in (
        incoming, replace(incoming, provider="another"), replace(incoming, provider_account_id="another-merchant"),
    )]
    assert len({receipt.id for receipt in receipts}) == 3


@pytest.mark.parametrize("mutation", ["update", "delete", "truncate"])
def test_database_refuses_receipt_mutation(db, mutation):
    current = workspace(db)
    receipt = SubscriptionPaymentEventService(db).record(current.id, event())
    statements = {
        "update": update(SubscriptionPaymentEventReceipt).where(SubscriptionPaymentEventReceipt.id == receipt.id).values(amount=Decimal("0")),
        "delete": delete(SubscriptionPaymentEventReceipt).where(SubscriptionPaymentEventReceipt.id == receipt.id),
        "truncate": text("TRUNCATE TABLE public.subscription_payment_event_receipts"),
    }
    with pytest.raises(DBAPIError, match="Payment event receipts are immutable"):
        with db.begin_nested():
            db.execute(statements[mutation])
    db.expire_all()
    assert db.get(SubscriptionPaymentEventReceipt, receipt.id).amount == Decimal("120.50")


def test_workspace_hard_delete_cannot_destroy_receipts(db):
    current = workspace(db)
    receipt = SubscriptionPaymentEventService(db).record(current.id, event())
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.execute(delete(Workspace).where(Workspace.id == current.id))
    assert db.get(SubscriptionPaymentEventReceipt, receipt.id) is not None


def test_rls_grants_and_populated_downgrade_preserve_evidence(db):
    current = workspace(db)
    incoming = event()
    receipt = SubscriptionPaymentEventService(db).record(current.id, incoming)
    assert db.execute(text("SELECT relrowsecurity FROM pg_class WHERE oid = 'public.subscription_payment_event_receipts'::regclass")).scalar_one()
    assert not db.execute(text("""SELECT EXISTS (
        SELECT 1 FROM pg_class c, LATERAL aclexplode(coalesce(c.relacl, acldefault('r', c.relowner))) a
        WHERE c.oid = 'public.subscription_payment_event_receipts'::regclass
        AND (a.grantee = 0 OR a.grantee IN (SELECT oid FROM pg_roles WHERE rolname IN ('anon', 'authenticated')))
    )""")).scalar_one()
    path = Path(__file__).resolve().parents[2] / "alembic/versions/202610290052_subscription_payment_event_receipts.py"
    spec = importlib.util.spec_from_file_location("payment_receipt_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with Operations.context(MigrationContext.configure(db.connection())):
        with pytest.raises(RuntimeError, match="data-preserving"):
            migration.downgrade()
    assert SubscriptionPaymentEventService(db).record(current.id, incoming).id == receipt.id


def _wait_for_identity_lock(engine, pid):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        with engine.connect() as connection:
            waiting = connection.execute(text("SELECT wait_event_type FROM pg_stat_activity WHERE pid = :pid"), {"pid": pid}).scalar_one_or_none()
        if waiting == "Lock":
            return
        time.sleep(0.01)
    pytest.fail("Competing insert did not wait on the uncommitted provider event identity")


@pytest.mark.parametrize("mode", ["replay", "changed", "foreign", "rollback"])
def test_concurrent_duplicate_waits_for_first_transaction_and_cannot_overwrite_or_cross_tenant(engine, mode):
    # Separate connections and committed synthetic workspaces are required for a
    # real identity collision. Records remain only in this disposable CI database.
    with Session(engine) as setup:
        first, second = workspace(setup), workspace(setup)
        first_id, second_id = first.id, second.id
        setup.commit()
    incoming = event()
    contender_workspace = second_id if mode in {"foreign", "rollback"} else first_id
    contender_event = replace(incoming, amount=Decimal("120.51")) if mode in {"changed", "rollback"} else incoming
    pids = Queue()

    def contender():
        with Session(engine) as session:
            session.execute(text("SET LOCAL lock_timeout = '10s'"))
            pids.put(session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            try:
                receipt = SubscriptionPaymentEventService(session).record(contender_workspace, contender_event)
                receipt_id = receipt.id
                session.commit()
                return receipt_id
            except SubscriptionPaymentEventConflict as exc:
                session.rollback()
                return str(exc)

    with Session(engine) as first_session:
        original = SubscriptionPaymentEventService(first_session).record(first_id, incoming)
        original_id = original.id
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(contender)
            try:
                _wait_for_identity_lock(engine, pids.get(timeout=5))
                assert not future.done()
            finally:
                if mode == "rollback":
                    first_session.rollback()
                else:
                    first_session.commit()
            result = future.result(timeout=10)
    with Session(engine) as verification:
        repository = SubscriptionPaymentEventRepository(verification)
        if mode == "rollback":
            assert result != original_id
            assert repository.get_for_event(first_id, incoming.provider, incoming.provider_account_id, incoming.external_event_id) is None
            assert repository.get_for_event(second_id, incoming.provider, incoming.provider_account_id, incoming.external_event_id).id == result
        else:
            assert result == (original_id if mode == "replay" else "Payment event conflicts with an existing receipt")
            stored = repository.get_for_event(first_id, incoming.provider, incoming.provider_account_id, incoming.external_event_id)
            assert stored.id == original_id and stored.amount == Decimal("120.50")
            assert repository.get_for_event(second_id, incoming.provider, incoming.provider_account_id, incoming.external_event_id) is None
        assert verification.execute(select(func.count()).select_from(SubscriptionPaymentEventReceipt).where(
            SubscriptionPaymentEventReceipt.provider == incoming.provider,
            SubscriptionPaymentEventReceipt.provider_account_id == incoming.provider_account_id,
            SubscriptionPaymentEventReceipt.external_event_id == incoming.external_event_id,
        )).scalar_one() == 1
