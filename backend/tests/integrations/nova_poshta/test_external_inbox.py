"""External TTN inbox regression: safe, bounded and tenant-scoped."""
from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.integrations.nova_poshta_client import NovaPoshtaClient, NovaPoshtaClientError, NovaPoshtaDocumentResult
from app.services.nova_poshta_external_inbox_service import NovaPoshtaExternalInboxService
from app.services.nova_poshta_inbox_worker import enabled


def document(n, ref="ref"):
    return NovaPoshtaDocumentResult(tracking_number=n, document_ref=ref, status="Created")


class FakeClient:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def list_internet_documents(self, first, last, *, page, limit):
        self.calls.append((first, last, page, limit))
        return self.rows.get((first, page), [])


class FakeRepo:
    def __init__(self, workspace, matches):
        self.workspace = workspace
        self.matches = matches
        self.rows = {}

    def matching_shipment_ids(self, workspace, number):
        assert workspace == self.workspace
        return self.matches.get(number, [])

    def upsert(self, workspace, number, ref, provider_status, match_state, shipment_id, now):
        assert workspace == self.workspace
        self.rows[(workspace, number)] = (match_state, shipment_id)


class FakeDB:
    def __init__(self):
        self.commits = self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def build(rows, matches=None, connected=True):
    workspace = uuid4()
    obj = NovaPoshtaExternalInboxService.__new__(NovaPoshtaExternalInboxService)
    obj.db = FakeDB()
    obj.repo = FakeRepo(workspace, matches or {})
    client = FakeClient(rows)
    obj.client_factory = lambda key: client
    obj.settings = SimpleNamespace(_require_connection=lambda workspace_id: (
        SimpleNamespace(status="CONNECTED" if connected else "ERROR"), "fake-key"
    ))
    return obj, workspace, client


def test_client_get_document_list_never_exposes_recipient():
    client = NovaPoshtaClient("fake")
    seen = []
    client._call = lambda name, method, props: (
        seen.append((name, method, props)),
        {"data": [{"IntDocNumber": "20400000000001", "Ref": "abc", "StateName": "Created", "RecipientPhone": "SENSITIVE"}]}
    )[1]
    items = client.list_internet_documents(date(2026, 10, 27), date(2026, 10, 27), page=2)
    assert items == [document("20400000000001", "abc")]
    assert seen[0][0:2] == ("InternetDocument", "getDocumentList")
    assert seen[0][2]["GetFullList"] == "0"
    assert seen[0][2]["Page"] == "2"
    assert "SENSITIVE" not in repr(items)


def test_client_rejects_malformed_listing():
    client = NovaPoshtaClient("fake")
    client._call = lambda *args: {"data": [{"IntDocNumber": "bad"}]}
    with pytest.raises(NovaPoshtaClientError):
        client.list_internet_documents(date(2026, 10, 27), date(2026, 10, 27))


def test_ingest_unmatched_and_exact_link_without_any_order_creation():
    today = date(2026, 10, 27)
    linked_id = uuid4()
    service, workspace, client = build(
        {(today, 1): [document("20400000000001"), document("20400000000002")]},
        {"20400000000002": [linked_id]},
    )
    first = service.collect(workspace, today, today)
    second = service.collect(workspace, today, today)
    assert first["scanned"] == second["scanned"] == 2
    assert first["unmatched"] == 1 and first["linked"] == 1
    assert len(service.repo.rows) == 2
    assert service.repo.rows[(workspace, "20400000000001")] == ("UNMATCHED", None)
    assert service.repo.rows[(workspace, "20400000000002")] == ("LINKED", linked_id)
    assert service.db.commits == 2


def test_dry_run_never_persists():
    today = date(2026, 10, 27)
    service, workspace, client = build({(today, 1): [document("20400000000001")]})
    result = service.collect(workspace, today, today, dry_run=True)
    assert result["dry_run"] and result["scanned"] == 1
    assert not service.repo.rows
    assert service.db.commits == 0 and service.db.rollbacks == 1


def test_duplicate_matches_are_quarantined():
    today = date(2026, 10, 27)
    service, workspace, _ = build({(today, 1): [document("20400000000001")]},
        {"20400000000001": [uuid4(), uuid4()]})
    assert service.collect(workspace, today, today)["conflicts"] == 1
    assert service.repo.rows[(workspace, "20400000000001")] == ("CONFLICT", None)


def test_full_pages_without_termination_fail_closed():
    today = date(2026, 10, 27)
    entries = [document(f"20{i:012d}") for i in range(100)]
    service, workspace, _ = build({(today, p): entries for p in range(1, 11)})
    with pytest.raises(NovaPoshtaClientError, match="truncated"):
        service.collect(workspace, today, today)
    assert service.repo.rows == {} and service.db.commits == 0


def test_disconnected_cannot_fetch_provider_data():
    today = date(2026, 10, 27)
    service, workspace, client = build({}, connected=False)
    with pytest.raises(ValueError, match="NOT_CONNECTED"):
        service.collect(workspace, today, today)
    assert client.calls == []


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("SELLORA_NP_EXTERNAL_SYNC_ENABLED", raising=False)
    assert not enabled()
    monkeypatch.setenv("SELLORA_NP_EXTERNAL_SYNC_ENABLED", "true")
    assert enabled()
