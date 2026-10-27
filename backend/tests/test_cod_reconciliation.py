"""NovaPay register import safety and source-of-truth invariants."""
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.cod_reconciliation import CodImportRequest, CodImportRow
from app.services.cod_reconciliation_service import CodReconciliationService


def row(reference="payment-001", tracking="20451234567890", amount="579.00", source="NOVAPAY_REGISTER", fee="5.00"):
    return CodImportRow(
        source=source, reference=reference, tracking_number=tracking,
        gross_amount=Decimal(amount), fee_amount=Decimal(fee),
        paid_at=datetime(2026, 5, 6, 12, tzinfo=timezone.utc),
    )


def shipment_pair(*, expected="579.00", order_status="DELIVERED", historical=True):
    order = SimpleNamespace(
        id=uuid4(), status=order_status, is_historical=historical,
        revenue=Decimal("0"), net_profit=Decimal("0"),
        payment_status="PENDING", product_cost=Decimal("0"),
    )
    shipment = SimpleNamespace(id=uuid4(), cod_amount=Decimal(expected))
    return shipment, order


def fake_service(matches=None, existing=None):
    instance = CodReconciliationService.__new__(CodReconciliationService)
    instance._existing_rows = lambda workspace_id: list(existing if existing is not None else [])
    instance._shipment_matches = lambda workspace_id, ttn: list((matches or []) if ttn else [])
    return instance


def test_valid_novapay_register_matches_exact_cod_without_updating_finance():
    shp, order = shipment_pair()
    before = (order.revenue, order.net_profit, order.payment_status, order.product_cost)
    response = fake_service([(shp, order)]).preview(uuid4(), CodImportRequest(rows=[row()]))
    assert response.matched_count == 1
    assert response.review_count == response.duplicate_count == 0
    assert response.rows[0].order_id == order.id
    assert (order.revenue, order.net_profit, order.payment_status, order.product_cost) == before


@pytest.mark.parametrize("amount,expected,status,reason", [
    ("579.00", "0.00", "DELIVERED", "NO_COD_IN_SHIPMENT"),
    ("679.00", "579.00", "DELIVERED", "COD_AMOUNT_MISMATCH"),
    ("579.00", "579.00", "RETURNED", "CANCELLED_OR_RETURNED"),
    ("579.00", "579.00", "CANCELLED", "CANCELLED_OR_RETURNED"),
])
def test_ambiguous_or_invalid_payment_is_review(amount, expected, status, reason):
    shp, order = shipment_pair(expected=expected, order_status=status)
    result = fake_service([(shp, order)]).preview(uuid4(), CodImportRequest(rows=[row(amount=amount)]))
    assert result.review_count == 1
    assert result.rows[0].reason == reason


def test_bank_record_without_ttn_remains_manual_review():
    service = fake_service()
    outcome = service.preview(uuid4(), CodImportRequest(rows=[row(source="BANK_STATEMENT", tracking=None)]))
    assert outcome.review_count == 1
    assert outcome.rows[0].reason == "NO_VALID_TTN"


def test_unmatched_ttn_remains_review_and_no_revenue():
    outcome = fake_service().preview(uuid4(), CodImportRequest(rows=[row()]))
    assert outcome.review_count == 1
    assert outcome.rows[0].reason == "NO_UNIQUE_SHIPMENT"


def test_same_source_reference_is_idempotently_skipped():
    existing = SimpleNamespace(
        source="NOVAPAY_REGISTER", external_reference="payment-001",
        status="MATCHED", tracking_number="20451234567890",
    )
    res = fake_service(existing=[existing]).preview(uuid4(), CodImportRequest(rows=[row()]))
    assert res.duplicate_count == 1 and res.matched_count == 0


def test_bank_and_novapay_same_ttn_are_not_counted_twice_in_single_file():
    shipment, order = shipment_pair()
    records = [row("first", source="NOVAPAY_REGISTER"), row("second", source="BANK_STATEMENT")]
    res = fake_service([(shipment, order)]).preview(uuid4(), CodImportRequest(rows=records))
    assert res.matched_count == 1
    assert res.review_count == 1
    assert res.rows[1].reason == "POSSIBLE_DUPLICATE_RECEIPT"


def test_existing_matched_ttn_rejects_second_source_as_new_cash():
    shipment, order = shipment_pair()
    existing = SimpleNamespace(source="NOVAPAY_REGISTER", external_reference="payment-001", status="MATCHED", tracking_number="20451234567890")
    res = fake_service([(shipment, order)], [existing]).preview(uuid4(), CodImportRequest(rows=[row("bank-id", source="BANK_STATEMENT")]))
    assert res.matched_count == 0
    assert res.review_count == 1
    assert res.rows[0].reason == "POSSIBLE_DUPLICATE_RECEIPT"


def test_amount_validations_and_bounded_batch():
    with pytest.raises(ValidationError):
        row(amount="0")
    with pytest.raises(ValidationError):
        row(amount="10.123")
    with pytest.raises(ValidationError):
        row(amount="10.00", fee="20.00")
    with pytest.raises(ValidationError):
        CodImportRequest(rows=[row(reference=f"row-{i:04}") for i in range(301)])


def test_reference_is_strict_and_unrecognized_provider_rejected():
    with pytest.raises(ValidationError):
        row(reference="a")
    with pytest.raises(ValidationError):
        row(source="UNTRUSTED_COD_SOURCE")


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeDB:
    def __init__(self, workspace_id):
        self.workspace_id = workspace_id
        self.records = []
        self.commits = 0

    def execute(self, stmt):
        return FakeResult(self.workspace_id)

    def add(self, record):
        self.records.append(record)

    def flush(self):
        for record in self.records:
            if record.id is None:
                record.id = uuid4()

    def commit(self):
        self.commits += 1


def test_import_creates_evidence_and_audit_only_not_sales():
    shp, order = shipment_pair()
    wid, actor = uuid4(), uuid4()
    db = FakeDB(wid)
    service = fake_service([(shp, order)])
    service.db = db
    events = []
    service.audit = SimpleNamespace(create=lambda **kwargs: events.append(kwargs))
    result = service.import_rows(wid, CodImportRequest(rows=[row()]), actor)
    assert result.inserted_count == 1
    assert result.matched_count == 1
    assert db.commits == 1
    assert len(db.records) == 1 and len(events) == 1
    assert db.records[0].status == "MATCHED"
    assert events[0]["action"] == "COD_PAYMENT_EVIDENCE_IMPORTED"
    assert order.revenue == 0
    assert order.payment_status == "PENDING"
