"""Manual bank attestation must be tenant scoped, double-checked and immutable."""
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from app.schemas.manual_payment_confirmation import ManualPaymentConfirmRequest
from app.services.manual_payment_confirmation_service import (
    ManualPaymentConfirmationService, ManualPaymentError,
)


def request(**kwargs):
    raw = {
        "payment_method": "BANK_IBAN",
        "transaction_reference": "mono-event-74900-a",
        "amount_minor": 74900,
        "receipt_checked": True,
        "bank_received_checked": True,
        "receipt_note": "Квитанцію звірено в Direct",
    }
    raw.update(kwargs)
    return ManualPaymentConfirmRequest(**raw)


def order(**kwargs):
    raw = {
        "id": uuid4(), "customer_id": uuid4(), "items": [SimpleNamespace(quantity=1)],
        "status": "CONFIRMED", "payment_status": "PENDING",
        "is_historical": False, "revenue": Decimal("749.00"),
    }
    raw.update(kwargs)
    return SimpleNamespace(**raw)


class FakeDb:
    def __init__(self, existing_ref=None, currency="UAH"):
        self.added = []
        self.commits = 0
        self.existing_ref = existing_ref
        self.currency = currency
        self.statements = []

    def scalar(self, statement):
        self.statements.append(statement)
        if "workspaces.currency_code" in str(statement):
            return self.currency
        return self.existing_ref

    def add(self, obj):
        obj.id = uuid4()
        self.added.append(obj)

    def flush(self):
        pass

    def commit(self):
        self.commits += 1


def service(target, *, existing=None, existing_ref=None):
    s = ManualPaymentConfirmationService.__new__(ManualPaymentConfirmationService)
    s.db = FakeDb(existing_ref)
    s.orders = SimpleNamespace(get_for_update=lambda workspace, order_id: target)
    s.get = lambda workspace, order_id: existing
    audit = []
    s.audit = SimpleNamespace(create=lambda **values: audit.append(values))
    return s, audit


def test_manual_confirmation_marks_paid_only_after_both_human_checks():
    obj = order()
    s, audit = service(obj)
    wid, actor = uuid4(), uuid4()
    result = s.confirm(wid, obj.id, request(), actor)
    assert result.payment_status == "PAID"
    assert result.confirmation.verified_by_user_id == actor
    assert result.confirmation.reference_suffix == "••••00-a"
    assert result.confirmation.receipt_checked and result.confirmation.bank_received_checked
    assert obj.revenue == Decimal("749.00")
    assert obj.items[0].quantity == 1
    assert s.db.commits == 1 and len(audit) == 1
    assert audit[0]["action"] == "ORDER_PAYMENT_MANUALLY_VERIFIED"
    assert audit[0]["new_value"]["verification_source"] == "HUMAN_ATTESTATION_NOT_BANK_API"
    assert "mono-event-74900-a" not in str(audit[0])


@pytest.mark.parametrize("flags", [
    {"receipt_checked": False},
    {"bank_received_checked": False},
    {"receipt_checked": False, "bank_received_checked": False},
])
def test_either_check_missing_never_marks_paid(flags):
    obj = order()
    s, audit = service(obj)
    with pytest.raises(ManualPaymentError, match="RECEIPT_AND_BANK"):
        s.confirm(uuid4(), obj.id, request(**flags), uuid4())
    assert obj.payment_status == "PENDING"
    assert s.db.commits == 0 and not audit


@pytest.mark.parametrize("target,error", [
    (None, "ORDER_NOT_FOUND"),
    (order(is_historical=True), "ORDER_NOT_ELIGIBLE"),
    (order(status="CANCELLED"), "ORDER_NOT_ELIGIBLE"),
    (order(status="RETURNED"), "ORDER_NOT_ELIGIBLE"),
    (order(payment_status="COD"), "ORDER_NOT_PENDING_OR_PAID"),
    (order(customer_id=None), "ORDER_CUSTOMER_OR_ITEMS_MISSING"),
    (order(items=[]), "ORDER_CUSTOMER_OR_ITEMS_MISSING"),
    (order(revenue=Decimal("0.00")), "ORDER_AMOUNT_NOT_POSITIVE"),
    (order(revenue=Decimal("700")), "PAYMENT_AMOUNT_MISMATCH"),
])
def test_unqualified_orders_never_marked_paid(target, error):
    s, audit = service(target)
    with pytest.raises(ManualPaymentError, match=error):
        s.confirm(uuid4(), target.id if target else uuid4(), request(), uuid4())
    assert s.db.commits == 0
    assert not audit


def test_same_reference_cannot_be_assigned_to_different_order():
    obj = order()
    s, _ = service(obj, existing_ref=uuid4())
    with pytest.raises(ManualPaymentError, match="BANK_TRANSACTION_ALREADY_ASSIGNED"):
        s.confirm(uuid4(), obj.id, request(), uuid4())
    assert obj.payment_status == "PENDING"


def test_existing_paid_order_can_receive_receipt_and_bank_attestation_without_new_sale():
    obj = order(payment_status="PAID")
    s, audit = service(obj)
    result = s.confirm(uuid4(), obj.id, request(), uuid4())
    assert result.payment_status == "PAID"
    assert obj.revenue == Decimal("749.00")
    assert s.db.commits == 1 and len(audit) == 1
    assert audit[0]["old_value"]["payment_status"] == "PAID"


def test_duplicate_order_different_transaction_is_rejected():
    obj = order(payment_status="PAID")
    previous = SimpleNamespace(
        id=uuid4(), order_id=obj.id, transaction_reference="mono-event-74900-a",
        payment_method="BANK_IBAN", amount_minor=74900, currency="UAH",
        receipt_checked=True, bank_received_checked=True, receipt_note=None,
        verified_by_user_id=uuid4(), verified_at=datetime.now(timezone.utc),
    )
    s, _ = service(obj, existing=previous)
    first = s.confirm(uuid4(), obj.id, request(), uuid4())
    assert first.payment_status == "PAID" and s.db.commits == 0
    with pytest.raises(ManualPaymentError, match="ORDER_PAYMENT_ALREADY_CONFIRMED"):
        s.confirm(uuid4(), obj.id, request(transaction_reference="other-payment-123"), uuid4())


@pytest.mark.parametrize("reference", [
    "4000000000000000", "UA1234567890", "https://mono.com/pay/receipt",
    "../", "test\nheader", "=HYPERLINK('x')", "mono tx with spaces", "abcd",
])
def test_no_sensitive_or_unstable_payment_reference(reference):
    with pytest.raises(ValidationError):
        request(transaction_reference=reference)


@pytest.mark.parametrize("kind", [
    {"bank_verified": True},
    {"bank_api_confirmed": True},
    {"payment_method": "CASH"},
    {"amount_minor": -1},
    {"amount_minor": 749.0},
    {"amount_minor": 0},
    {"receipt_note": "<script>bad</script>"},
])
def test_untrusted_payload_rejected(kind):
    with pytest.raises(ValidationError):
        request(**kind)


def test_get_is_strictly_workspace_and_order_scoped():
    class Capture:
        query = None

        def scalar(self, stmt):
            self.query = stmt
            return None
    db = Capture()
    s = ManualPaymentConfirmationService.__new__(ManualPaymentConfirmationService)
    s.db = db
    workspace, obj = uuid4(), uuid4()
    assert s.get(workspace, obj) is None
    query = db.query.compile(dialect=postgresql.dialect())
    assert "manual_payment_confirmations.workspace_id" in str(query)
    assert "manual_payment_confirmations.order_id" in str(query)
    assert workspace in query.params.values()
    assert obj in query.params.values()


def test_non_uah_workspace_is_rejected():
    obj = order()
    s, audit = service(obj)
    s.db.currency = "EUR"
    with pytest.raises(ManualPaymentError, match="ONLY_UAH"):
        s.confirm(uuid4(), obj.id, request(), uuid4())
    assert obj.payment_status == "PENDING"
    assert not audit and s.db.commits == 0


def test_reference_uniqueness_sql_is_workspace_scoped():
    obj = order()
    s, _ = service(obj)
    s.confirm(uuid4(), obj.id, request(), uuid4())
    statement = s.db.statements[-1].compile(dialect=postgresql.dialect())
    assert "manual_payment_confirmations.workspace_id" in str(statement)
    assert "manual_payment_confirmations.transaction_reference" in str(statement)
