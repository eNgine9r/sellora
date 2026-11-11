"""External carrier TTNs can navigate to one verified Direct dialogue, not become orders."""
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy.dialects import postgresql

from app.repositories.nova_poshta_external_repository import NovaPoshtaExternalRepository
from app.services.nova_poshta_external_inbox_service import NovaPoshtaExternalInboxService


class EvidenceDb:
    def __init__(self, matches):
        self.matches = matches
        self.statement = None

    def execute(self, statement):
        self.statement = statement
        return SimpleNamespace(all=lambda: self.matches)


def test_unique_outbound_tracking_links_exactly_one_conversation():
    workspace, document, conversation = uuid4(), uuid4(), uuid4()
    db = EvidenceDb([(document, conversation, uuid4(), None)])
    result = NovaPoshtaExternalRepository(db).direct_evidence_by_document(workspace, [document])
    assert result[document] == {
        "direct_match_state": "MATCHED",
        "direct_conversation_id": conversation,
        "direct_customer_linked": True,
        "direct_order_linked": False,
    }
    sql = str(db.statement.compile(dialect=postgresql.dialect()))
    assert "direct_messages.workspace_id = nova_poshta_external_documents.workspace_id" in sql
    assert "direct_conversations.workspace_id = nova_poshta_external_documents.workspace_id" in sql
    assert "direct_messages.is_synthetic IS false" in sql
    assert "direct_messages.deleted_at IS NULL" in sql
    assert "direct_conversations.deleted_at IS NULL" in sql
    assert "nova_poshta_external_documents.workspace_id" in sql
    assert "direct_messages.direction" in sql


def test_multiple_matching_dialogues_are_not_opened_automatically():
    workspace, document = uuid4(), uuid4()
    db = EvidenceDb([(document, uuid4(), None, None), (document, uuid4(), uuid4(), None)])
    result = NovaPoshtaExternalRepository(db).direct_evidence_by_document(workspace, [document])
    assert result == {document: {"direct_match_state": "AMBIGUOUS"}}


def test_missing_and_empty_scans_return_no_evidence():
    db = EvidenceDb([])
    repo = NovaPoshtaExternalRepository(db)
    assert repo.direct_evidence_by_document(uuid4(), []) == {}
    assert db.statement is None
    assert repo.direct_evidence_by_document(uuid4(), [uuid4()]) == {}


def test_response_keeps_carrier_and_direct_matching_as_separate_dimensions():
    workspace, document, conversation = uuid4(), uuid4(), uuid4()
    now = datetime.now(UTC)
    row = SimpleNamespace(
        id=document,
        tracking_number="20000000000001",
        document_ref=None,
        provider_status=None,
        match_state="UNMATCHED",
        matched_shipment_id=None,
        first_seen_at=now,
        last_seen_at=now,
    )
    service = object.__new__(NovaPoshtaExternalInboxService)
    service.repo = SimpleNamespace(
        list_for_workspace=lambda workspace_id, state: [row],
        direct_evidence_by_document=lambda workspace_id, document_ids: {
            document: {
                "direct_match_state": "MATCHED",
                "direct_conversation_id": conversation,
                "direct_customer_linked": True,
                "direct_order_linked": False,
            }
        },
    )
    rows = service.list_with_direct_evidence(workspace, state="UNMATCHED")
    assert len(rows) == 1
    assert rows[0]["match_state"] == "UNMATCHED"  # Still no CRM shipment/order.
    assert rows[0]["direct_conversation_id"] == conversation
    assert rows[0]["direct_order_linked"] is False
