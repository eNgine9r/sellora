"""Monobank multi-rail evidence: safe dedup, tenant scope, no phantom PAID."""
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from app.schemas.bank_payment_evidence import BankImportRequest, BankImportRow
from app.services.bank_payment_evidence_service import BankPaymentEvidenceService
from app.services.monobank_normalizers import (
    MonobankPayloadError, normalize_paid_invoice, normalize_statement_credit,
)


def transfer(*, ref="mono-payment-01", account="mono-fop-acc-1",
             rail="BANK_IBAN", kind="CUSTOMER_PAYMENT",
             amount=74900, order="SL-1042", hold=False):
    return BankImportRow(
        provider_account_id=account, external_reference=ref, rail=rail, kind=kind,
        amount_minor=amount, order_number=order, is_hold=hold,
        occurred_at=datetime(2026, 11, 11, 8, 0, tzinfo=timezone.utc),
    )


def pending_order(*, revenue="749.00", status="CONFIRMED", payment="PENDING", historical=False):
    return SimpleNamespace(id=uuid4(), revenue=Decimal(revenue), status=status,
                           payment_status=payment, is_historical=historical)


def fake_service(existing=(), orders=None):
    service = BankPaymentEvidenceService.__new__(BankPaymentEvidenceService)
    service._existing_keys = lambda workspace: set(existing)
    service._order = lambda workspace, number: (orders or {}).get(number)
    return service


def test_three_rails_are_supported_without_payment_status_side_effects():
    order = pending_order()
    original = (order.revenue, order.payment_status)
    service = fake_service(orders={"SL-1042": order})
    rows = [transfer(ref="iban"), transfer(ref="card", rail="FOP_CARD"),
            transfer(ref="link", rail="MONO_ACQUIRING_LINK")]
    result = service.preview(uuid4(), BankImportRequest(rows=rows))
    assert result.candidate_count == 3
    assert result.review_count == 3
    assert result.duplicate_count == 0
    assert all(x.reason == "REQUIRES_PROVIDER_AND_RECEIPT_VERIFICATION" for x in result.rows)
    assert (order.revenue, order.payment_status) == original


def test_same_underlying_account_transaction_is_duplicate_even_with_different_rail():
    service = fake_service()
    rows = [transfer(ref="same", rail="FOP_CARD"),
            transfer(ref="same", rail="BANK_IBAN")]
    result = service.preview(uuid4(), BankImportRequest(rows=rows))
    assert result.review_count == 1
    assert result.duplicate_count == 1
    assert result.rows[1].reason == "PROVIDER_ACCOUNT_TRANSACTION_ALREADY_IMPORTED"


def test_existing_same_event_is_idempotent_and_cross_account_does_not_collide():
    service = fake_service(existing={("mono-fop-acc-1", "mono-payment-01")})
    result = service.preview(uuid4(), BankImportRequest(rows=[
        transfer(), transfer(account="mono-fop-acc-2"),
    ]))
    assert result.duplicate_count == 1
    assert result.review_count == 1


@pytest.mark.parametrize("kind,hold,order,expected", [
    ("ACQUIRING_PAYOUT", False, "SL-1042", "PAYOUT_NOT_CUSTOMER_PAYMENT"),
    ("REFUND", False, "SL-1042", "REFUND_NEEDS_PAYMENT_ALLOCATION"),
    ("UNCLASSIFIED_CREDIT", False, "SL-1042", "BANK_CREDIT_CLASSIFICATION_REQUIRED"),
    ("CUSTOMER_PAYMENT", True, "SL-1042", "BANK_HOLD_NOT_SETTLED"),
    ("CUSTOMER_PAYMENT", False, None, "ORDER_REFERENCE_MISSING"),
    ("CUSTOMER_PAYMENT", False, "not-found", "ORDER_NOT_FOUND"),
])
def test_unsafe_cases_stay_unallocated(kind, hold, order, expected):
    res = fake_service(orders={"SL-1042": pending_order()}).preview(
        uuid4(), BankImportRequest(rows=[transfer(kind=kind, hold=hold, order=order)])
    )
    assert res.candidate_count == 0
    assert res.rows[0].reason == expected


@pytest.mark.parametrize("kwargs,expected", [
    ({"amount": 75000}, "ORDER_AMOUNT_MISMATCH"),
    ({"amount": 74900, "status": "CANCELLED"}, "ORDER_CANCELLED_OR_RETURNED"),
    ({"amount": 74900, "status": "RETURNED"}, "ORDER_CANCELLED_OR_RETURNED"),
    ({"amount": 74900, "payment": "PAID"}, "ORDER_PAYMENT_ALREADY_PROCESSED"),
    ({"amount": 74900, "historical": True}, "HISTORICAL_ORDER_NOT_VERIFIED"),
])
def test_mismatched_or_processed_orders_require_review(kwargs, expected):
    amount = kwargs.pop("amount")
    service = fake_service(orders={"SL-1042": pending_order(**kwargs)})
    res = service.preview(uuid4(), BankImportRequest(rows=[transfer(amount=amount)]))
    assert res.rows[0].reason == expected and res.candidate_count == 0


@pytest.mark.parametrize("bad", [
    {"amount_minor": -1},
    {"amount_minor": 0},
    {"amount_minor": 100_000_000_000_000},
    {"currency": "USD"},
    {"rail": "CARD_TO_CARD"},
    {"kind": "UNKNOWN"},
    {"external_reference": "  invalid "},
    {"external_reference": "bad\nvalue"},
    {"provider_account_id": "  "},
    {"occurred_at": datetime(2026, 11, 11, 8, 0)},
    {"bank_verified": True},
])
def test_import_rejects_invalid_or_forged_verified_fields(bad):
    data = transfer().model_dump()
    data.update(bad)
    with pytest.raises(ValidationError):
        BankImportRow(**data)


def test_import_bounded_and_preview_does_not_mutate():
    service = fake_service()
    assert service.preview(uuid4(), BankImportRequest(rows=[transfer()])).review_count == 1
    with pytest.raises(ValidationError):
        BankImportRequest(rows=[transfer(ref=f"event-{i:04}") for i in range(201)])


class Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeDB:
    def __init__(self, workspace_id):
        self.workspace_id = workspace_id
        self.created = []
        self.commits = 0

    def execute(self, stmt):
        return Result(self.workspace_id)

    def add(self, evidence):
        self.created.append(evidence)

    def flush(self):
        for row in self.created:
            if row.id is None:
                row.id = uuid4()

    def commit(self):
        self.commits += 1


def test_import_persists_unverified_evidence_only_and_audit_without_sales():
    workspace_id, actor_id = uuid4(), uuid4()
    order = pending_order()
    service = fake_service(orders={"SL-1042": order})
    service.db = FakeDB(workspace_id)
    audit = []
    service.audit = SimpleNamespace(create=lambda **values: audit.append(values))
    result = service.import_rows(workspace_id, BankImportRequest(rows=[transfer()]), actor_id)
    assert result.inserted_count == 1 and result.candidate_count == 1
    assert service.db.commits == 1 and len(audit) == 1
    record = service.db.created[0]
    assert record.origin == "MANUAL_IMPORT"
    assert record.review_reason == "REQUIRES_PROVIDER_AND_RECEIPT_VERIFICATION"
    assert record.candidate_order_id == order.id
    assert order.payment_status == "PENDING"
    assert order.revenue == Decimal("749.00")
    assert audit[0]["workspace_id"] == workspace_id


def test_order_lookup_sql_is_tenant_scoped_and_excludes_deleted():
    class CaptureDB:
        def __init__(self):
            self.query = None

        def execute(self, stmt):
            self.query = stmt
            return Result(None)

    db = CaptureDB()
    workspace = uuid4()
    service = BankPaymentEvidenceService(db)
    assert service._order(workspace, "SL-1042") is None
    compiled = db.query.compile(dialect=postgresql.dialect())
    assert "orders.workspace_id" in str(compiled)
    assert "orders.deleted_at IS NULL" in str(compiled)
    assert workspace in compiled.params.values()


def test_statement_normalization_does_not_infer_card_or_customer_payment():
    event = {"id": "txn-123", "time": 1794384000, "amount": 74900,
             "currencyCode": 980, "hold": False, "description": "incoming"}
    out = normalize_statement_credit(event, account_id="mono-fop-acc-1")
    assert out.amount_minor == 74900
    assert out.kind.value == "UNCLASSIFIED_CREDIT"
    assert out.rail.value == "UNKNOWN_ACCOUNT_TRANSFER"
    assert normalize_statement_credit({**event, "amount": -200}, account_id="mono-fop-acc-1") is None
    with pytest.raises(MonobankPayloadError):
        normalize_statement_credit({**event, "currencyCode": 840}, account_id="mono-fop-acc-1")


def test_invoice_normalization_requires_success_and_never_assumes_direct_order():
    invoice = {"invoiceId": "p2_invoice_345", "status": "success",
               "amount": 74900, "ccy": 980,
               "modifiedDate": "2026-11-11T08:00:00Z",
               "reference": "not-a-verified-order-number"}
    out = normalize_paid_invoice(invoice, merchant_account_id="mono-merchant-1")
    assert out.invoice_id == "p2_invoice_345"
    assert out.order_number is None
    assert out.rail.value == "MONO_ACQUIRING_LINK"
    assert normalize_paid_invoice({**invoice, "status": "processing"}, merchant_account_id="mono-merchant-1") is None
    with pytest.raises(MonobankPayloadError):
        normalize_paid_invoice({**invoice, "modifiedDate": "nonsense"}, merchant_account_id="mono-merchant-1")
