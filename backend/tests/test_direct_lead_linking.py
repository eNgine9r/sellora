from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.ai_direct import DirectConversation
from app.models.lead import LeadStatus
from app.services.direct_lead_service import DirectLeadError, DirectLeadService


class FakeDB:
    def begin_nested(self):
        return nullcontext()


class FakeConversationRepository:
    def __init__(self, rows):
        self.rows = rows
        self.locked = []

    def get(self, workspace_id, conversation_id):
        return next((c for c in self.rows if c.workspace_id == workspace_id and c.id == conversation_id), None)

    get_for_update = get

    def lock_instagram_participant(self, workspace_id, connection_id, scoped_id):
        self.locked.append((workspace_id, connection_id, scoped_id))

    def find_lead_for_instagram_participant(self, workspace_id, connection_id, scoped_id):
        return next((c for c in self.rows
                     if c.workspace_id == workspace_id
                     and c.instagram_connection_id == connection_id
                     and c.participant_scoped_id == scoped_id
                     and c.linked_lead_id), None)


class FakeLeads:
    def __init__(self):
        self.rows = []

    def get(self, workspace_id, lead_id):
        return next((l for l in self.rows if l.workspace_id == workspace_id and l.id == lead_id and l.deleted_at is None), None)

    def create(self, lead):
        lead.id = uuid4()
        lead.deleted_at = None
        self.rows.append(lead)
        return lead


class FakeMessages:
    def __init__(self):
        self.rows = {}

    def latest_instagram_inbound(self, workspace_id, conversation_id):
        return self.rows.get((workspace_id, conversation_id))


class FakeAudit:
    def __init__(self):
        self.rows = []

    def create(self, **values):
        self.rows.append(values)


def make_conversation(workspace_id=None, connection_id=None, participant='buyer-1', channel='INSTAGRAM'):
    return DirectConversation(
        id=uuid4(), workspace_id=workspace_id or uuid4(),
        channel=channel, instagram_connection_id=connection_id or uuid4(),
        participant_scoped_id=participant, participant_username='buyer_1',
        participant_display_name='Покупець', status='OPEN', priority='NORMAL',
        ai_processing_status='NOT_REQUESTED', unread_count=1,
    )


def make_service(conversations):
    service = DirectLeadService.__new__(DirectLeadService)
    service.db = FakeDB()
    service.conversations = FakeConversationRepository(conversations)
    service.messages = FakeMessages()
    service.leads = FakeLeads()
    service.audit = FakeAudit()
    return service


def test_qualified_inbound_creates_single_linked_lead_and_audit():
    conversation = make_conversation()
    service = make_service([conversation])
    when = datetime.now(UTC) - timedelta(hours=2)
    a = service.ensure_from_inbound_order_intent(conversation.workspace_id, conversation.id, 'Хочу замовити', when)
    b = service.ensure_from_inbound_order_intent(conversation.workspace_id, conversation.id, 'Беру цей', when)
    assert a.id == b.id == conversation.linked_lead_id
    assert a.workspace_id == conversation.workspace_id
    assert a.status == LeadStatus.NEW.value
    assert a.first_contact_at == when
    assert a.instagram_username == 'buyer_1'
    assert len(service.leads.rows) == len(service.audit.rows) == 1
    assert service.audit.rows[0]['action'] == 'DIRECT_LEAD_CREATE'
    assert len(service.conversations.locked) == 2


@pytest.mark.parametrize('text', ['Привіт', 'Дякую', '', None, '[image Instagram message]'])
def test_nonqualifying_message_does_not_create_lead(text):
    c = make_conversation()
    service = make_service([c])
    assert service.ensure_from_inbound_order_intent(c.workspace_id, c.id, text) is None
    assert not service.leads.rows and c.linked_lead_id is None


def test_other_workspace_cannot_access_a_conversation():
    c = make_conversation()
    service = make_service([c])
    with pytest.raises(DirectLeadError, match='DIRECT_CONVERSATION_NOT_FOUND'):
        service.ensure_from_inbound_order_intent(uuid4(), c.id, 'Хочу купити')
    assert not service.leads.rows


def test_same_participant_across_threads_reuses_lead_only_within_connection():
    first = make_conversation()
    second = make_conversation(first.workspace_id, first.instagram_connection_id)
    third = make_conversation(first.workspace_id, uuid4())
    fourth = make_conversation(uuid4(), first.instagram_connection_id)
    service = make_service([first, second, third, fourth])
    lead_a = service.ensure_from_inbound_order_intent(first.workspace_id, first.id, 'Замовляю')
    lead_b = service.ensure_from_inbound_order_intent(second.workspace_id, second.id, 'Куплю')
    lead_c = service.ensure_from_inbound_order_intent(third.workspace_id, third.id, 'Беру цей')
    lead_d = service.ensure_from_inbound_order_intent(fourth.workspace_id, fourth.id, 'Замовляю')
    assert lead_a.id == lead_b.id
    assert lead_c.id != lead_a.id and lead_d.id != lead_a.id
    assert len(service.leads.rows) == 3


def test_manual_link_requires_real_inbound_provider_message():
    c = make_conversation()
    service = make_service([c])
    with pytest.raises(DirectLeadError, match='DIRECT_LEAD_INBOUND_REQUIRED'):
        service.ensure_manually(c.workspace_id, c.id, uuid4())
    service.messages.rows[(c.workspace_id,c.id)] = SimpleNamespace(received_at=datetime.now(UTC))
    actor = uuid4()
    a = service.ensure_manually(c.workspace_id, c.id, actor)
    b = service.ensure_manually(c.workspace_id, c.id, actor)
    assert a.id == b.id
    assert len(service.leads.rows) == 1
    assert service.audit.rows[0]['user_id'] == actor


def test_manual_action_rejects_synthetic_conversation_even_if_message_exists():
    c = make_conversation(channel='SYNTHETIC')
    service = make_service([c])
    service.messages.rows[(c.workspace_id,c.id)] = SimpleNamespace(received_at=datetime.now(UTC))
    with pytest.raises(DirectLeadError, match='DIRECT_LEAD_INSTAGRAM_REQUIRED'):
        service.ensure_manually(c.workspace_id, c.id, uuid4())


def test_qualifying_lead_does_not_create_order_or_customer():
    c = make_conversation()
    service = make_service([c])
    service.ensure_from_inbound_order_intent(c.workspace_id, c.id, 'Оформіть замовлення')
    assert c.linked_lead_id is not None
    assert c.linked_order_id is None
    assert c.linked_customer_id is None


def test_deleted_previous_lead_is_not_resurrected():
    c = make_conversation()
    service = make_service([c])
    old = service.ensure_from_inbound_order_intent(c.workspace_id, c.id, 'Замовлю')
    old.deleted_at = datetime.now(UTC)
    fresh = service.ensure_from_inbound_order_intent(c.workspace_id, c.id, 'Куплю')
    assert fresh.id != old.id
    assert c.linked_lead_id == fresh.id


def test_lost_lead_requires_new_opportunity():
    c = make_conversation()
    service = make_service([c])
    old = service.ensure_from_inbound_order_intent(c.workspace_id,c.id,'Замовляю')
    old.status = LeadStatus.LOST.value
    fresh = service.ensure_from_inbound_order_intent(c.workspace_id,c.id,'Хочу купити')
    assert fresh.id != old.id
    assert c.linked_lead_id == fresh.id


def test_webhook_inbound_qualified_message_links_once_and_preserves_replay(monkeypatch):
    from app.integrations.meta_instagram.services.inbound_message_service import InstagramInboundMessageService
    import app.integrations.meta_instagram.services.inbound_message_service as inbound_module
    monkeypatch.setattr(inbound_module, "MetaMessageOperationRepository", lambda db: SimpleNamespace(get_by_provider_message=lambda *_: None))

    class Messages:
        def __init__(self):
            self.rows = []
        def get_by_provider_message(self, workspace_id, provider, mid):
            return next((m for m in self.rows if m.workspace_id == workspace_id and m.provider_message_id == mid), None)
        def create(self, message):
            message.id = uuid4()
            self.rows.append(message)

    class Conversations:
        def __init__(self, conversation):
            self.row = conversation
        def get_by_instagram_participant(self, workspace_id, connection_id, scoped_id):
            if (self.row.workspace_id, self.row.instagram_connection_id, self.row.participant_scoped_id) == (workspace_id, connection_id, scoped_id):
                return self.row
            return None

    class Spy:
        def __init__(self):
            self.calls = []
        def ensure_from_inbound_order_intent(self, *args):
            self.calls.append(args)

    conversation = make_conversation()
    message_repository = Messages()
    spy = Spy()
    inbound = InstagramInboundMessageService.__new__(InstagramInboundMessageService)
    inbound.db = FakeDB()
    inbound.conversations = Conversations(conversation)
    inbound.messages = message_repository
    inbound.lead_service = spy
    inbound._enrich_profile_safe = lambda *args: None
    inbound._ensure_customer_safe = lambda *args: None
    event = SimpleNamespace(workspace_id=conversation.workspace_id, event_external_id='event-1',
                            payload={'entry':[{'id':'business-id'}]})
    connection = SimpleNamespace(id=conversation.instagram_connection_id, last_message_received_at=None)
    incoming = {'sender': {'id': conversation.participant_scoped_id},
                'recipient': {'id':'business-id'}, 'timestamp': 1784538000000,
                'message': {'mid':'mid-qualified-1', 'text':'Хочу купити'}}
    assert inbound._process_item(event, connection, incoming) == 1
    assert inbound._process_item(event, connection, incoming) == 0
    assert len(message_repository.rows) == 1
    assert len(spy.calls) == 1
    assert spy.calls[0][0:2] == (conversation.workspace_id, conversation.id)
    assert len(spy.calls[0]) == 4

    outgoing = {'sender': {'id': 'business-id'},
                'recipient': {'id': conversation.participant_scoped_id},
                'message': {'mid':'mid-outgoing-2', 'text':'Оформіть замовлення', 'is_echo':True}}
    assert inbound._process_item(event, connection, outgoing) == 1
    assert len(spy.calls) == 1


def test_lead_failure_does_not_drop_verified_incoming_message():
    from app.integrations.meta_instagram.services.inbound_message_service import InstagramInboundMessageService

    class MessageStore:
        rows = []
        def get_by_provider_message(self, workspace_id, provider, mid):
            return None
        def create(self, message):
            message.id = uuid4()
            self.rows.append(message)

    class ConvRepo:
        def __init__(self, c):
            self.c = c
        def get_by_instagram_participant(self, *_):
            return self.c

    class FailingLead:
        def ensure_from_inbound_order_intent(self, *_):
            raise ValueError('synthetic-error')

    c=make_conversation()
    inbound=InstagramInboundMessageService.__new__(InstagramInboundMessageService)
    inbound.db=FakeDB()
    inbound.conversations=ConvRepo(c)
    inbound.messages=MessageStore()
    inbound.lead_service=FailingLead()
    inbound._enrich_profile_safe=lambda *a:None
    inbound._ensure_customer_safe=lambda *a:None
    event=SimpleNamespace(workspace_id=c.workspace_id,event_external_id='evt',payload={'entry':[{'id':'shop'}]})
    connection=SimpleNamespace(id=c.instagram_connection_id,last_message_received_at=None)
    msg={'sender':{'id':c.participant_scoped_id},'recipient':{'id':'shop'},
         'message':{'mid':'mid-1','text':'Куплю'}}
    assert inbound._process_item(event,connection,msg)==1
    assert len(inbound.messages.rows)==1
    assert c.provider_sync_status=='LEAD_AUTOMATION_FAILED_SAFE'


def test_converted_lead_starts_new_repeat_sale_opportunity():
    c = make_conversation()
    service = make_service([c])
    previous = service.ensure_from_inbound_order_intent(c.workspace_id, c.id, "Замовляю")
    previous.status = LeadStatus.CONVERTED.value
    new = service.ensure_from_inbound_order_intent(c.workspace_id, c.id, "Хочу купити")
    assert new.id != previous.id
    assert new.status == LeadStatus.NEW.value
    assert c.linked_lead_id == new.id
