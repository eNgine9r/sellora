"""Nova Poshta -> Direct -> human approved sale, no banking API and no AI hallucinations."""
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from app.schemas.smart_sale import SmartSaleCandidate, SmartSaleConfirmRequest, SmartSaleSuggestion
from app.services.smart_sale_confirmation_service import SmartSaleConfirmationService, SmartSaleError


def request(conversation_id=None, variant_id=None, **kwargs):
    fields = {
        "expected_conversation_id": conversation_id or uuid4(),
        "product_variant_id": variant_id or uuid4(),
        "quantity": 1,
        "unit_price": "749.00",
        "receipt_checked_in_direct": True,
        "funds_received_in_bank": True,
        "details_reviewed": True,
    }
    fields.update(kwargs)
    return SmartSaleConfirmRequest(**fields)


def suggestion(variant_id):
    return SmartSaleSuggestion(variant_id=variant_id, sku="SKU-1", product_name="Watch",
                               quantity=1, suggested_unit_price=Decimal("749.00"), available_quantity=7)


@pytest.mark.parametrize("flags", [
    {"receipt_checked_in_direct": False},
    {"funds_received_in_bank": False},
    {"details_reviewed": False},
    {"receipt_checked_in_direct": None},
    {"bank_verified": True},
    {"price_source": "FAKE_PROVIDER"},
    {"quantity": 0},
    {"unit_price": "0"},
    {"unit_price": "749.999"},
    {"unit_price": "1e99"},
])
def test_confirmation_must_be_explicit_review_and_valid_amount(flags):
    with pytest.raises(ValidationError):
        request(**flags)


@pytest.mark.parametrize("lines,matched,expected", [
    ([], False, None),
    ([SimpleNamespace(source="ANALYSIS_CONTEXT", match_status="MATCHED", requires_review=True,
                      candidates=[SimpleNamespace(variant_id=uuid4(), price=Decimal("749.00"))], evidence=[object()],
                      candidates_truncated=False)], False, None),
])
def test_ai_only_or_no_sku_is_not_auto_eligible(lines, matched, expected):
    service = SmartSaleConfirmationService.__new__(SmartSaleConfirmationService)
    service.proposals = SimpleNamespace(get=lambda workspace, conversation: SimpleNamespace(
        catalog_truncated=False, context_truncated=False, lines=lines,
    ))
    assert service._suggestion(uuid4(), uuid4()) is None


def test_exact_sku_unique_and_available_is_just_a_catalog_suggestion():
    variant_id = uuid4()
    candidate = SimpleNamespace(variant_id=variant_id, sku="WATCH-001", product_name="Watch",
                                price=Decimal("749.00"), available_quantity=7)
    line = SimpleNamespace(source="INBOUND_SKU", match_status="MATCHED", requires_review=False,
                           candidates=[candidate], quantity=1, evidence=[object()], candidates_truncated=False)
    service = SmartSaleConfirmationService.__new__(SmartSaleConfirmationService)
    service.proposals = SimpleNamespace(get=lambda w, c: SimpleNamespace(
        catalog_truncated=False, context_truncated=False, lines=[line],
    ))
    result = service._suggestion(uuid4(), uuid4())
    assert result is not None
    assert result.variant_id == variant_id
    assert result.price_source == "CATALOG_SUGGESTION"
    assert result.suggested_unit_price == Decimal("749.00")
    service.proposals = SimpleNamespace(get=lambda w, c: SimpleNamespace(
        catalog_truncated=True, context_truncated=False, lines=[line],
    ))
    assert service._suggestion(uuid4(), uuid4()) is None
    candidate.available_quantity = 0
    service.proposals = SimpleNamespace(get=lambda w, c: SimpleNamespace(
        catalog_truncated=False, context_truncated=False, lines=[line],
    ))
    assert service._suggestion(uuid4(), uuid4()) is None


class CaptureDb:
    def __init__(self, customer_id):
        self.customer_id = customer_id
        self.commits = 0
        self.added = []
        self.stored_shipment = None
        self.customer = SimpleNamespace(id=customer_id, lifecycle_status="PROSPECT")

    def scalar(self, statement):
        sql = str(statement)
        if "workspaces.currency_code" in sql:
            return "UAH"
        if "FROM customers" in sql:
            return self.customer
        if "FROM shipments" in sql:
            return self.stored_shipment
        return None

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1


def build_confirmation_service(doc=None, match=None, suggested=None):
    workspace, actor, conversation_id, customer_id, variant_id = (uuid4() for _ in range(5))
    doc = doc or SimpleNamespace(
        id=uuid4(), workspace_id=workspace,
        tracking_number="20450000000000", document_ref="np-ref-001",
        provider_status="Створено", match_state="UNMATCHED", matched_shipment_id=None,
    )
    conversation = SimpleNamespace(id=conversation_id, linked_order_id=None)
    customer = SimpleNamespace(id=customer_id)
    payload = request(conversation_id, variant_id)
    matched = match if match is not None else {
        "direct_match_state": "MATCHED", "direct_conversation_id": conversation_id,
        "direct_customer_id": customer_id, "direct_order_linked": False,
    }
    service = SmartSaleConfirmationService.__new__(SmartSaleConfirmationService)
    db = CaptureDb(customer_id)
    service.db = db
    service._document = lambda w, doc_id, lock=False: doc if w == workspace and doc_id == doc.id else None
    service._evidence = lambda w, doc_id: matched
    service._suggestion = lambda w, conv: suggested if suggested is not None else suggestion(variant_id)
    service.customer_automation = SimpleNamespace(
        conversations=SimpleNamespace(get=lambda w, cid: conversation if cid == conversation_id else None),
        ensure_candidate=lambda w, cid, actor, commit: SimpleNamespace(customer=customer),
    )
    order_id, shipment_id = uuid4(), uuid4()
    created = []
    service.orders = SimpleNamespace(create=lambda w, data, act, commit: (
        created.append(("order", data, commit)) or SimpleNamespace(id=order_id, customer_id=customer_id)))
    service.shipments = SimpleNamespace(create=lambda w, data, act, commit: (
        created.append(("shipment", data, commit)) or SimpleNamespace(id=shipment_id)))
    audits = []
    service.audit = SimpleNamespace(create=lambda **kwargs: audits.append(kwargs))
    db.stored_shipment = SimpleNamespace(id=shipment_id, external_provider=None,
        external_ref=None, external_status=None, nova_poshta_document_ref=None,
        nova_poshta_document_number=None, nova_poshta_raw_status=None)
    return service, payload, workspace, actor, doc, conversation, db, created, audits


def test_one_click_creates_order_customer_shipment_and_links_in_one_commit():
    s, payload, workspace, actor, doc, conv, db, created, audits = build_confirmation_service()
    result = s.confirm(workspace, doc.id, payload, actor)
    assert result.payment_status == "PAID" and not result.already_confirmed
    assert db.commits == 1
    assert [item[0] for item in created] == ["order", "shipment"]
    assert all(item[-1] is False for item in created)
    order_payload = created[0][1]
    assert order_payload.payment_status.value == "PAID"
    assert order_payload.items[0].unit_price == Decimal("749.00")
    assert order_payload.items[0].cost_confirmed is False
    assert created[1][1].tracking_number == doc.tracking_number
    assert created[1][1].status.value == "CREATED"
    assert doc.match_state == "LINKED"
    assert doc.matched_shipment_id == result.shipment_id
    assert conv.linked_order_id == result.order_id
    assert db.customer.lifecycle_status == "CUSTOMER"
    assert db.stored_shipment.external_ref == "np-ref-001"
    assert db.stored_shipment.nova_poshta_document_number == doc.tracking_number
    assert len(audits) == 1
    assert audits[0]["action"] == "SMART_SALE_APPROVED"
    assert audits[0]["new_value"]["payment_verification"] == "HUMAN_ATTESTATION_NOT_BANK_API"
    assert any(getattr(obj, "evidence_type", None) == "EXACT_TTN_HUMAN_APPROVED" for obj in db.added)


@pytest.mark.parametrize("state,evidence,reason", [
    ("CONFLICT", None, "EXTERNAL_TTN_NOT_ELIGIBLE"),
    ("LINKED", None, "EXTERNAL_TTN_NOT_ELIGIBLE"),
    ("UNMATCHED", {"direct_match_state": "AMBIGUOUS"}, "DIRECT_EVIDENCE_CHANGED"),
    ("UNMATCHED", {"direct_match_state": "NONE"}, "DIRECT_EVIDENCE_CHANGED"),
])
def test_bad_ttn_or_ambiguous_direct_never_creates_sale(state, evidence, reason):
    s, payload, workspace, actor, doc, conv, db, created, audits = build_confirmation_service(match=evidence)
    doc.match_state = state
    with pytest.raises(SmartSaleError, match=reason):
        s.confirm(workspace, doc.id, payload, actor)
    assert not created and db.commits == 0 and not audits


def test_stale_conversation_or_unknown_sku_fails_before_sale():
    s, payload, workspace, actor, doc, conv, db, created, audits = build_confirmation_service()
    with pytest.raises(SmartSaleError, match="DIRECT_EVIDENCE_CHANGED"):
        s.confirm(workspace, doc.id, payload.model_copy(update={"expected_conversation_id": uuid4()}), actor)
    with pytest.raises(SmartSaleError, match="PRODUCT_EVIDENCE_CHANGED"):
        s.confirm(workspace, doc.id, payload.model_copy(update={"product_variant_id": uuid4()}), actor)
    assert not created and db.commits == 0


def test_existing_direct_order_does_not_block_new_distinct_ttn_sale():
    s, payload, workspace, actor, doc, conv, db, created, audits = build_confirmation_service()
    conv.linked_order_id = uuid4()
    order_before = conv.linked_order_id
    result = s.confirm(workspace, doc.id, payload, actor)
    assert result.order_id is not None
    assert conv.linked_order_id == order_before
    assert db.commits == 1


def test_manager_can_select_real_catalog_variant_when_no_sku_detected():
    s, payload, workspace, actor, doc, conv, db, created, audits = build_confirmation_service()
    s._suggestion = lambda w, c: None
    manual = payload.model_copy(update={"selection_source": "MANAGER_SELECTED"})
    result = s.confirm(workspace, doc.id, manual, actor)
    assert result.order_id and db.commits == 1
    assert created[0][1].items[0].product_variant_id == manual.product_variant_id
    assert audits[0]["new_value"]["selection_source"] == "MANAGER_SELECTED"


def test_proposal_uses_only_direct_customer_and_catalog_data_not_bank():
    s, payload, workspace, actor, doc, conv, db, created, audits = build_confirmation_service()
    result = s.confirm(workspace, doc.id, payload, actor)
    assert result.order_id and result.shipment_id
    assert not hasattr(s, "bank_api") and not hasattr(s, "send_direct")


def test_list_marks_ambiguous_direct_needs_info_and_safe_mask():
    doc = SimpleNamespace(id=uuid4(), match_state="UNMATCHED", matched_shipment_id=None,
                          tracking_number="20450000000000", provider_status="Created")
    service = SmartSaleConfirmationService.__new__(SmartSaleConfirmationService)
    service.external = SimpleNamespace(
        list_for_workspace=lambda wid, state, limit: [doc],
        direct_evidence_by_document=lambda wid, ids: {doc.id: {"direct_match_state": "AMBIGUOUS"}},
    )
    result = service.list(uuid4())
    assert len(result) == 1
    assert result[0].state == "NEEDS_INFO"
    assert "000000" not in result[0].tracking_masked
    assert result[0].reason == "DIRECT_MATCH_AMBIGUOUS_OR_MISSING"


def test_consistent_confirm_request_contains_no_bank_secret_or_unrestricted_metadata():
    data = request().model_dump()
    assert not {"bank_token", "bank_verified", "provider_refund", "source_statement"} & data.keys()
