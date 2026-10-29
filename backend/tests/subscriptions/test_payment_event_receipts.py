from dataclasses import FrozenInstanceError, asdict, replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, Inexact, localcontext
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.models.subscription_payment_event_receipt import SubscriptionPaymentEventReceipt
from app.repositories.subscription_payment_event_repository import SubscriptionPaymentEventRepository
from app.schemas.subscription_payment_event import SubscriptionPaymentEvent
from app.services.subscription_payment_event_service import (
    SubscriptionPaymentEventConflict,
    SubscriptionPaymentEventService,
    SubscriptionPaymentEventValidationError,
    normalize_payment_event,
    payment_event_fingerprint,
)

OCCURRED_AT = datetime(2026, 10, 29, 12, 30, tzinfo=UTC)


def event(**changes):
    return replace(SubscriptionPaymentEvent(
        provider="synthetic", provider_account_id="merchant-1", external_event_id="evt-1",
        transaction_id="txn-1", event_type="payment.succeeded", amount=Decimal("120.50"),
        currency="UAH", occurred_at=OCCURRED_AT,
    ), **changes)


class ReceiptStore:
    def __init__(self):
        self.records = {}
        self.lookups = []

    def insert_if_absent(self, receipt):
        identity = (receipt.provider, receipt.provider_account_id, receipt.external_event_id)
        if identity not in self.records:
            receipt.id = uuid4()
            self.records[identity] = receipt

    def get_for_event(self, workspace_id, provider, provider_account_id, external_event_id):
        self.lookups.append(workspace_id)
        receipt = self.records.get((provider, provider_account_id, external_event_id))
        return receipt if receipt is not None and receipt.workspace_id == workspace_id else None


def service():
    instance = SubscriptionPaymentEventService.__new__(SubscriptionPaymentEventService)
    instance.receipts = ReceiptStore()
    return instance


def test_equivalent_money_and_offsets_replay_the_original_immutable_receipt():
    instance, workspace = service(), uuid4()
    first = instance.record(workspace, event())
    replay = instance.record(workspace, event(
        amount=Decimal("120.5000000"),
        occurred_at=OCCURRED_AT.astimezone(timezone(timedelta(hours=3))),
    ))
    assert replay is first
    assert first.amount == Decimal("120.500000")
    assert first.occurred_at == OCCURRED_AT
    assert len(instance.receipts.records) == 1


@pytest.mark.parametrize("changes", [
    {"transaction_id": "txn-2"}, {"event_type": "payment.failed"},
    {"amount": Decimal("120.500001")}, {"currency": "USD"},
    {"occurred_at": OCCURRED_AT + timedelta(microseconds=1)},
])
def test_changed_transaction_conflicts_without_overwriting_first_receipt(changes):
    instance, workspace = service(), uuid4()
    original = instance.record(workspace, event())
    with pytest.raises(SubscriptionPaymentEventConflict, match="^Payment event conflicts with an existing receipt$"):
        instance.record(workspace, event(**changes))
    assert instance.record(workspace, event()) is original


def test_foreign_tenant_conflict_is_generic_and_lookup_remains_workspace_scoped():
    instance, first_workspace, second_workspace = service(), uuid4(), uuid4()
    original = instance.record(first_workspace, event())
    with pytest.raises(SubscriptionPaymentEventConflict) as foreign:
        instance.record(second_workspace, event())
    with pytest.raises(SubscriptionPaymentEventConflict) as changed:
        instance.record(first_workspace, event(transaction_id="txn-other"))
    assert str(foreign.value) == str(changed.value)
    assert str(first_workspace) not in str(foreign.value)
    assert instance.receipts.lookups == [first_workspace, second_workspace, first_workspace]
    assert instance.record(first_workspace, event()) is original


@pytest.mark.parametrize("changes", [
    {"provider": "another"}, {"provider_account_id": "merchant-2"}, {"external_event_id": "evt-2"},
])
def test_provider_account_and_event_are_explicit_independent_namespaces(changes):
    instance, workspace = service(), uuid4()
    first = instance.record(workspace, event())
    second = instance.record(workspace, event(**changes))
    assert first.id != second.id
    assert len(instance.receipts.records) == 2


@pytest.mark.parametrize("changes", [
    {"provider": ""}, {"provider": "Synthetic"}, {"provider": "a" * 41},
    {"provider_account_id": "customer@example.invalid"}, {"provider_account_id": "a" * 129},
    {"external_event_id": " evt"}, {"external_event_id": "a" * 161},
    {"transaction_id": "customer name"}, {"transaction_id": None},
    {"event_type": ""}, {"event_type": "payment\nfailed"},
    {"currency": "uah"}, {"currency": "UAHH"}, {"currency": "12A"},
    {"amount": 120.50}, {"amount": "120.50"}, {"amount": 120}, {"amount": True},
    {"amount": Decimal("NaN")}, {"amount": Decimal("sNaN")}, {"amount": Decimal("Infinity")},
    {"amount": Decimal("-0.000001")}, {"amount": Decimal("0.0000001")},
    {"amount": Decimal("100000000000000")},
    {"occurred_at": OCCURRED_AT.replace(tzinfo=None)}, {"occurred_at": "2026-10-29T12:30:00Z"},
])
def test_invalid_evidence_is_rejected_before_any_repository_operation(changes):
    instance = service()
    with pytest.raises(SubscriptionPaymentEventValidationError):
        instance.record(uuid4(), event(**changes))
    assert not instance.receipts.records and not instance.receipts.lookups


def test_zero_and_six_decimal_money_are_exact_without_interpreting_payment_success():
    for amount in (Decimal("-0"), Decimal("0"), Decimal("0.000001"), Decimal("99999999999999.999999")):
        with localcontext() as context:
            context.prec = 6
            normalized = normalize_payment_event(event(amount=amount, event_type="payment.failed"))
        assert normalized.amount == amount
    assert normalize_payment_event(event(amount=Decimal("-0"))).amount.as_tuple().sign == 0


def test_caller_decimal_traps_cannot_bypass_validation_or_change_canonical_money():
    with localcontext() as context:
        context.prec = 3
        context.traps[Inexact] = True
        with pytest.raises(SubscriptionPaymentEventValidationError, match="precision"):
            normalize_payment_event(event(amount=Decimal("0.0000001")))
        assert normalize_payment_event(event()).amount == Decimal("120.500000")


def test_input_has_no_raw_payload_or_pii_extension_and_is_frozen():
    with pytest.raises(TypeError):
        SubscriptionPaymentEvent(**asdict(event()), raw_payload={})
    with pytest.raises(FrozenInstanceError):
        event().currency = "USD"
    assert set(SubscriptionPaymentEventReceipt.__table__.columns.keys()) == {
        "id", "workspace_id", "provider", "provider_account_id", "external_event_id",
        "transaction_id", "event_type", "amount", "currency", "occurred_at", "fingerprint", "received_at",
    }


def test_canonical_fingerprint_is_stable_and_includes_tenant():
    workspace = uuid4()
    normalized = normalize_payment_event(event())
    assert payment_event_fingerprint(workspace, normalized) == payment_event_fingerprint(workspace, normalize_payment_event(event(amount=Decimal("120.500000"))))
    assert payment_event_fingerprint(workspace, normalized) != payment_event_fingerprint(uuid4(), normalized)


def test_repository_uses_global_conflict_identity_and_workspace_scoped_duplicate_query():
    statements = []
    db = SimpleNamespace(execute=lambda statement: statements.append(statement) or SimpleNamespace(scalar_one_or_none=lambda: None))
    repository = SubscriptionPaymentEventRepository(db)
    workspace = uuid4()
    normalized = normalize_payment_event(event())
    repository.insert_if_absent(SubscriptionPaymentEventReceipt(
        workspace_id=workspace, provider=normalized.provider,
        provider_account_id=normalized.provider_account_id, external_event_id=normalized.external_event_id,
        transaction_id=normalized.transaction_id, event_type=normalized.event_type,
        amount=normalized.amount, currency=normalized.currency, occurred_at=normalized.occurred_at,
        fingerprint=payment_event_fingerprint(workspace, normalized),
    ))
    assert repository.get_for_event(workspace, normalized.provider, normalized.provider_account_id, normalized.external_event_id) is None
    insert = str(statements[0].compile(dialect=postgresql.dialect()))
    assert "ON CONFLICT (provider, provider_account_id, external_event_id) DO NOTHING" in insert
    query = statements[1].compile(dialect=postgresql.dialect())
    assert query.params["workspace_id_1"] == workspace
    assert "subscription_payment_event_receipts.workspace_id =" in str(query)
