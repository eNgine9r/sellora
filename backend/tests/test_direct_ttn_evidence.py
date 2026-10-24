"""Privacy, provenance and idempotency tests for read-only Direct TTN matching."""
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy.dialects import postgresql

from app.services.direct_ttn_evidence_service import (
    DirectTtnEvidenceService,
    extract_ttns,
    mask_tracking,
)


def test_ttn_extraction_respects_boundaries_and_format():
    assert extract_ttns("ТТН 20451234567890") == {"20451234567890"}
    assert extract_ttns("204512345678901") == set()
    assert extract_ttns("120451234567890") == set()
    assert extract_ttns("12345678901234") == set()
    assert mask_tracking("20451234567890") == "20••••••••7890"


class FakeDB:
    def __init__(self, conversation, messages, shipments):
        self.conversation = conversation
        self.messages = messages
        self.shipments = shipments
        self.queries = []
        self.executions = 0

    def scalar(self, stmt):
        self.queries.append(stmt)
        return self.conversation

    def scalars(self, stmt):
        self.queries.append(stmt)
        return SimpleNamespace(all=lambda: [])

    def execute(self, stmt):
        self.queries.append(stmt)
        self.executions += 1
        value = self.messages if self.executions == 1 else self.shipments
        return SimpleNamespace(all=lambda: value)


def sample_match(code, customer_id=None, order_number="1001"):
    return (
        uuid4(), code, customer_id, "CREATED", uuid4(),
        order_number, "COMPLETED", "PAID", True,
    )


def test_one_verified_order_and_repeat_ttn_deduplicates():
    workspace, conversation_id, message_id, customer = uuid4(), uuid4(), uuid4(), uuid4()
    match = sample_match("20451234567890", customer)
    db = FakeDB(
        SimpleNamespace(id=conversation_id, linked_customer_id=customer),
        [(message_id, "Ваша ТТН 20451234567890"), (uuid4(), "ТТН 20451234567890")],
        [match],
    )
    result = DirectTtnEvidenceService(db).preview(workspace, conversation_id)
    assert len(result["verified_orders"]) == 1
    assert result["verified_orders"][0]["order_id"] == match[4]
    assert result["verified_orders"][0]["evidence_type"] == "EXACT_SHIPMENT_TTN"
    assert result["needs_review"] == []
    assert result["has_multiple_orders"] is False
    assert "20451234567890" not in str(result)
    assert db.executions == 2
    # Every read is workspace-scoped, even when IDs are chosen by an attacker.
    for statement in db.queries:
        compiled = str(statement.compile(dialect=postgresql.dialect()))
        assert "workspace_id" in compiled


def test_multiple_distinct_orders_remain_visible():
    a = sample_match("20451234567890")
    b = sample_match("20459876543210")
    db = FakeDB(
        SimpleNamespace(id=uuid4(), linked_customer_id=None),
        [(uuid4(), "Нова пошта 20451234567890 і 20459876543210")],
        [a, b],
    )
    result = DirectTtnEvidenceService(db).preview(uuid4(), uuid4())
    assert len(result["verified_orders"]) == 2
    assert result["has_multiple_orders"] is True


def test_unmatched_shipping_ttn_not_misclassified_as_no_order():
    db = FakeDB(
        SimpleNamespace(id=uuid4(), linked_customer_id=None),
        [(uuid4(), "ТТН Нова пошта 20451234567890")],
        [],
    )
    result = DirectTtnEvidenceService(db).preview(uuid4(), uuid4())
    assert not result["verified_orders"]
    assert result["needs_review"][0]["reason"] == "SHIPMENT_NOT_IN_CRM"
    assert "20451234567890" not in str(result)


def test_conflict_blocks_verified_order():
    db = FakeDB(
        SimpleNamespace(id=uuid4(), linked_customer_id=uuid4()),
        [(uuid4(), "ТТН 20451234567890")],
        [sample_match("20451234567890", uuid4())],
    )
    result = DirectTtnEvidenceService(db).preview(uuid4(), uuid4())
    assert result["verified_orders"] == []
    assert result["needs_review"][0]["reason"] == "CUSTOMER_MISMATCH"


def test_duplicate_shipment_code_requires_review():
    db = FakeDB(
        SimpleNamespace(id=uuid4(), linked_customer_id=None),
        [(uuid4(), "Нова пошта 20451234567890")],
        [sample_match("20451234567890"), sample_match("20451234567890")],
    )
    result = DirectTtnEvidenceService(db).preview(uuid4(), uuid4())
    assert result["verified_orders"] == []
    assert result["needs_review"][0]["reason"] == "MULTIPLE_SHIPMENT_MATCHES"


def test_missing_conversation_is_not_disclosed():
    db = FakeDB(None, [], [])
    assert DirectTtnEvidenceService(db).preview(uuid4(), uuid4()) is None
    assert db.executions == 0


def test_bounded_scan_never_claims_complete(monkeypatch):
    from app.services import direct_ttn_evidence_service as service
    monkeypatch.setattr(service, "_MAX_MESSAGES", 1)
    db = FakeDB(
        SimpleNamespace(id=uuid4(), linked_customer_id=None),
        [(uuid4(), "ТТН 20451234567890"), (uuid4(), "ТТН 20459876543210")],
        [],
    )
    result = DirectTtnEvidenceService(db).preview(uuid4(), uuid4())
    assert result["scan_truncated"] is True
    assert len(result["needs_review"]) == 1


class ConfirmDB(FakeDB):
    def __init__(self, conversation, messages, shipments):
        super().__init__(conversation, messages, shipments)
        self.added = []
        self.flushed = 0
        self.confirmed_links = {}
        self.scalar_calls = 0

    def scalar(self, stmt):
        self.queries.append(stmt)
        self.scalar_calls += 1
        if self.scalar_calls % 3 in (1, 2):
            return self.conversation
        return self.confirmed_links.get(self.shipments[0][0])

    def execute(self, stmt):
        self.queries.append(stmt)
        self.executions += 1
        value = self.messages if self.executions % 2 == 1 else self.shipments
        return SimpleNamespace(all=lambda: value)

    def add(self, instance):
        self.added.append(instance)
        if type(instance).__name__ == "DirectOrderShipmentLink":
            self.confirmed_links[instance.shipment_id] = instance

    def scalars(self, stmt):
        self.queries.append(stmt)
        return SimpleNamespace(all=lambda: [
            s for s, obj in self.confirmed_links.items() if obj.deleted_at is None
        ])

    def flush(self):
        self.flushed += 1


def test_confirm_persists_exact_provenance_and_legacy_single_order_idempotently():
    from app.models.audit_log import AuditLog
    from app.models.direct_order_shipment_link import DirectOrderShipmentLink

    workspace, conv_id, msg_id, actor = uuid4(), uuid4(), uuid4(), uuid4()
    conversation = SimpleNamespace(id=conv_id, linked_customer_id=None, linked_order_id=None)
    match = sample_match("20451234567890")
    db = ConfirmDB(conversation, [(msg_id, "Нова пошта ТТН 20451234567890")], [match])
    service = DirectTtnEvidenceService(db)

    first = service.confirm(workspace, conv_id, {match[4]}, actor)
    assert first == {
        "confirmed_order_count": 1,
        "created_links": 1,
        "existing_links": 0,
        "primary_order_linked": True,
    }
    assert conversation.linked_order_id == match[4]
    links = [v for v in db.added if isinstance(v, DirectOrderShipmentLink)]
    audits = [v for v in db.added if isinstance(v, AuditLog)]
    assert len(links) == 1
    assert links[0].workspace_id == workspace
    assert links[0].source_message_id == msg_id
    assert links[0].shipment_id == match[0]
    assert links[0].order_id == match[4]
    assert len(audits) == 2
    assert "20451234567890" not in str([a.new_value for a in audits])
    assert db.flushed == 1

    again = service.confirm(workspace, conv_id, {match[4]}, actor)
    assert again["created_links"] == 0
    assert again["existing_links"] == 1
    assert again["primary_order_linked"] is False
    assert len([v for v in db.added if isinstance(v, DirectOrderShipmentLink)]) == 1


def test_confirm_rejects_client_requested_order_without_evidence():
    workspace, conv_id, msg_id = uuid4(), uuid4(), uuid4()
    conversation = SimpleNamespace(id=conv_id, linked_customer_id=None, linked_order_id=None)
    match = sample_match("20451234567890")
    db = ConfirmDB(conversation, [(msg_id, "ТТН 20451234567890")], [match])
    from pytest import raises
    with raises(ValueError, match="DIRECT_ORDER_EVIDENCE_CHANGED"):
        DirectTtnEvidenceService(db).confirm(workspace, conv_id, {uuid4()}, uuid4())
    assert not db.added
    assert not db.flushed


def test_confirm_rejects_existing_legacy_order_conflict():
    conv_id, workspace = uuid4(), uuid4()
    match = sample_match("20451234567890")
    db = ConfirmDB(
        SimpleNamespace(id=conv_id, linked_customer_id=None, linked_order_id=uuid4()),
        [(uuid4(), "ТТН 20451234567890")],
        [match],
    )
    from pytest import raises
    with raises(ValueError, match="DIRECT_PRIMARY_ORDER_CONFLICT"):
        DirectTtnEvidenceService(db).confirm(workspace, conv_id, {match[4]}, uuid4())
    assert not db.added