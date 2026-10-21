"""Meta signed batch ingestion must be atomic, tenant-scoped, and replay-safe."""
from contextlib import contextmanager
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.integrations.meta_instagram.exceptions import MetaInstagramError
from app.integrations.meta_instagram.services.webhook_service import InstagramWebhookService
from app.integrations.meta_instagram.services.inbound_message_service import InstagramInboundMessageService


class EventRepo:
    def __init__(self):
        self.rows = []
    def get_duplicate(self, provider, external, digest, bucket):
        return next((e for e in self.rows if (
            e.provider == provider and
            (e.event_external_id == external if external else e.payload_hash == digest and e.event_date_bucket == bucket)
        )), None)
    def create(self, event):
        event.id = uuid4()
        self.rows.append(event)
        return event


def _batch(entries):
    return {"object": "instagram", "entry": entries}


def _entry(business, *messages):
    return {"id": business, "messaging": [
        {"timestamp":1000+i, "sender":{"id":f"customer-{i}"}, "recipient":{"id":business},
         "message":{"mid":mid, "text":"Хочу замовити"}} for i,mid in enumerate(messages)
    ]}


def _service(monkeypatch):
    workspace_a,workspace_b = uuid4(),uuid4()
    connections = {
        "business-a":SimpleNamespace(id=uuid4(),workspace_id=workspace_a,instagram_account_id="business-a",status="CONNECTED"),
        "business-b":SimpleNamespace(id=uuid4(),workspace_id=workspace_b,instagram_account_id="business-b",status="CONNECTED"),
    }
    import app.integrations.meta_instagram.services.webhook_service as module
    monkeypatch.setattr(module,"InstagramConnectionRepository", lambda db:
        SimpleNamespace(get_by_account=lambda account: connections.get(account)))
    svc=InstagramWebhookService.__new__(InstagramWebhookService)
    svc.db=None
    svc.repo=EventRepo()
    return svc,connections


def test_two_accounts_in_one_webhook_are_scoped_to_different_workspaces(monkeypatch):
    svc,connections=_service(monkeypatch)
    payload=_batch([_entry("business-a","mid-a"),_entry("business-b","mid-b")])
    raw=json.dumps(payload).encode()
    rows=svc.persist_verified_events(raw,payload)
    assert len(rows)==2
    assert {row.workspace_id for row in rows}=={c.workspace_id for c in connections.values()}
    assert {row.instagram_connection_id for row in rows}=={c.id for c in connections.values()}
    assert all(row.signature_verified and row.status=="VERIFIED" for row in rows)
    assert all(len(row.payload["entry"])==1 for row in rows)
    assert all(len(row.payload["entry"][0]["messaging"])==1 for row in rows)
    assert [r.id for r in svc.persist_verified_events(raw,payload)]==[r.id for r in rows]
    # A provider resend of a single item shares the same event ID; no duplicate.
    single=_batch([_entry("business-b","mid-b")])
    assert svc.persist_verified_events(json.dumps(single).encode(),single)[0].id==rows[1].id
    assert len(svc.repo.rows)==2


def test_several_messages_from_same_account_survive_partial_replay(monkeypatch):
    svc,_=_service(monkeypatch)
    payload=_batch([_entry("business-a","mid-a","mid-b","mid-c")])
    rows=svc.persist_verified_events(json.dumps(payload).encode(),payload)
    assert len(rows)==3
    assert len({r.event_external_id for r in rows})==3
    reattempt=_batch([_entry("business-a","mid-a","mid-b","mid-c","mid-d")])
    current=svc.persist_verified_events(json.dumps(reattempt).encode(),reattempt)
    assert [r.id for r in current[:3]]==[r.id for r in rows]
    assert len(svc.repo.rows)==4


def test_unknown_account_stays_unassigned(monkeypatch):
    svc,conns=_service(monkeypatch)
    payload=_batch([_entry("business-a","mid-a"),_entry("unlinked-business","mid-foreign")])
    rows=svc.persist_verified_events(json.dumps(payload).encode(),payload)
    assert rows[0].status=="VERIFIED"
    assert rows[1].status=="IGNORED"
    assert rows[1].workspace_id is None
    assert rows[1].safe_error_code=="META_CONNECTION_NOT_READY"


@pytest.mark.parametrize("invalid",[
    _batch([{"id":"business-a","messaging":"not-a-list"}]),
    _batch([_entry("business-a","mid-a"),{"id":"business-b","messaging":[42]}]),
    {"entry":"not-a-list"},
])
def test_malformed_signed_batch_fails_without_partial_writes(monkeypatch, invalid):
    svc,_=_service(monkeypatch)
    with pytest.raises(MetaInstagramError) as exc:
        svc.persist_verified_events(json.dumps(invalid).encode(),invalid)
    assert exc.value.code=="META_WEBHOOK_PAYLOAD_INVALID"
    assert svc.repo.rows==[]


def test_inbound_processor_skips_foreign_business_entries(monkeypatch):
    _,connections=_service(monkeypatch)
    import app.integrations.meta_instagram.services.inbound_message_service as module
    monkeypatch.setattr(module,"InstagramConnectionRepository",lambda db:
        SimpleNamespace(get_active=lambda w:connections["business-a"]))
    svc=InstagramInboundMessageService.__new__(InstagramInboundMessageService)
    svc.db=None
    observed=[]
    svc._process_item=lambda event,connection,item,account_id=None: observed.append((account_id,item["message"]["mid"])) or 1
    payload=_batch([_entry("business-a","mid-a"),_entry("business-b","mid-b")])
    event=SimpleNamespace(workspace_id=connections["business-a"].workspace_id,
        instagram_connection_id=connections["business-a"].id,payload=payload,
        status="VERIFIED",safe_error_code=None,processed_at=None)
    count=svc.process_event(event)
    assert count==1
    assert observed==[("business-a","mid-a")]
    assert event.status=="PROCESSED"


def test_inbound_processor_skips_stale_connection_bindings(monkeypatch):
    _,connections=_service(monkeypatch)
    import app.integrations.meta_instagram.services.inbound_message_service as module
    monkeypatch.setattr(module,"InstagramConnectionRepository",lambda db:
        SimpleNamespace(get_active=lambda w:connections["business-a"]))
    svc=InstagramInboundMessageService.__new__(InstagramInboundMessageService)
    svc.db=None
    event=SimpleNamespace(workspace_id=connections["business-a"].workspace_id,
        instagram_connection_id=connections["business-b"].id,
        payload=_batch([_entry("business-a","mid-a")]),status="VERIFIED",safe_error_code=None,processed_at=None)
    assert svc.process_event(event)==0
    assert event.status=="IGNORED"
    assert event.safe_error_code=="META_CONNECTION_NOT_READY"


def test_customer_automation_failure_is_isolated_by_savepoint():
    class Db:
        nested=0
        @contextmanager
        def begin_nested(self):
            self.nested+=1
            yield
    svc=InstagramInboundMessageService.__new__(InstagramInboundMessageService)
    db=Db()
    svc.db=db
    svc.customer_automation=SimpleNamespace(ensure_from_inbound_order_intent=lambda *args: 1/0)
    c=SimpleNamespace(id=uuid4(),provider_sync_status=None)
    svc._ensure_customer_safe(uuid4(),c,"Куплю")
    assert db.nested==1
    assert c.provider_sync_status=="CUSTOMER_AUTOMATION_FAILED_SAFE"

def test_single_message_in_multi_account_envelope_is_not_assigned_to_empty_first_entry(monkeypatch):
    svc,connections=_service(monkeypatch)
    payload=_batch([{"id":"business-a","messaging":[]},_entry("business-b","mid-b")])
    rows=svc.persist_verified_events(json.dumps(payload).encode(),payload)
    assert len(rows)==1
    assert rows[0].workspace_id==connections["business-b"].workspace_id
    assert rows[0].instagram_connection_id==connections["business-b"].id

def test_same_provider_message_id_from_two_business_accounts_never_collides(monkeypatch):
    svc,conns=_service(monkeypatch)
    payload=_batch([_entry("business-a","shared-mid"),_entry("business-b","shared-mid")])
    rows=svc.persist_verified_events(json.dumps(payload).encode(),payload)
    assert len(rows)==2
    assert rows[0].event_external_id != rows[1].event_external_id
    assert rows[0].workspace_id==conns["business-a"].workspace_id
    assert rows[1].workspace_id==conns["business-b"].workspace_id
    assert len(svc.repo.rows)==2


def test_legacy_processed_event_replays_without_duplicate(monkeypatch):
    svc,_=_service(monkeypatch)
    payload=_batch([_entry("business-a","legacy-mid")])
    legacy_id=svc._event_id(payload)
    # Simulate a recorded legacy provider event from the previous release.
    old=SimpleNamespace(provider="INSTAGRAM",event_external_id=legacy_id,
        status="PROCESSED",payload=payload,id=uuid4())
    svc.repo.rows.append(old)
    rows=svc.persist_verified_events(json.dumps(payload).encode(),payload)
    assert rows[0].id==old.id
    assert len(svc.repo.rows)==1
