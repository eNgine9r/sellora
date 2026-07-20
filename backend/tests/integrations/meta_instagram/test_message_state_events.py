from types import SimpleNamespace
from uuid import uuid4

from app.integrations.meta_instagram.services.inbound_message_service import InstagramInboundMessageService


class FakeMessageRepo:
    def __init__(self, workspace_id, message):
        self.workspace_id = workspace_id
        self.message = message

    def get_by_provider_message(self, workspace_id, provider, provider_message_id):
        if workspace_id != self.workspace_id or provider != "INSTAGRAM" or provider_message_id != self.message.provider_message_id:
            return None
        return self.message


class FakeStateRepo:
    def __init__(self):
        self.state = None

    def get_or_create(self, workspace_id, direct_message_id, provider_message_id):
        if self.state is None:
            self.state = SimpleNamespace(
                workspace_id=workspace_id,
                direct_message_id=direct_message_id,
                provider_message_id=provider_message_id,
                seen_at=None,
                edited_at=None,
                edit_count=0,
                reaction=None,
                reaction_actor_scoped_id=None,
                reaction_updated_at=None,
            )
        return self.state


def make_service():
    workspace_id = uuid4()
    message = SimpleNamespace(
        id=uuid4(),
        workspace_id=workspace_id,
        provider_message_id="mid-1",
        delivery_status="PROVIDER_ACCEPTED",
        text="Початковий текст",
        safe_text_hash="old",
        message_type="TEXT",
        message_payload_type="TEXT",
    )
    service = InstagramInboundMessageService(SimpleNamespace())
    service.messages = FakeMessageRepo(workspace_id, message)
    service.message_states = FakeStateRepo()
    event = SimpleNamespace(workspace_id=workspace_id)
    return workspace_id, message, event, service


def test_seen_event_marks_exact_provider_message_as_seen():
    _, message, event, service = make_service()
    service._process_seen(event, {"timestamp": 1784538000000, "read": {"mid": "mid-1"}})
    assert message.delivery_status == "SEEN"
    assert service.message_states.state.seen_at is not None


def test_reaction_event_and_unreact_are_durable():
    _, _, event, service = make_service()
    service._process_reaction(
        event,
        {
            "timestamp": 1784538000000,
            "sender": {"id": "customer-1"},
            "reaction": {"mid": "mid-1", "action": "react", "emoji": "❤"},
        },
    )
    assert service.message_states.state.reaction == "❤"
    assert service.message_states.state.reaction_actor_scoped_id == "customer-1"

    service._process_reaction(
        event,
        {"timestamp": 1784538001000, "reaction": {"mid": "mid-1", "action": "unreact"}},
    )
    assert service.message_states.state.reaction is None
    assert service.message_states.state.reaction_actor_scoped_id is None


def test_edit_event_updates_text_hash_and_edit_count():
    _, message, event, service = make_service()
    service._process_edit(
        event,
        {
            "timestamp": 1784538000000,
            "message_edit": {"mid": "mid-1", "text": "Виправлений текст", "num_edit": 2},
        },
    )
    assert message.text == "Виправлений текст"
    assert message.safe_text_hash != "old"
    assert service.message_states.state.edit_count == 2
    assert service.message_states.state.edited_at is not None


def test_message_state_event_does_not_cross_workspace_boundary():
    workspace_id, message, event, service = make_service()
    event.workspace_id = uuid4()
    service._process_seen(event, {"timestamp": 1784538000000, "read": {"mid": "mid-1"}})
    assert message.delivery_status == "PROVIDER_ACCEPTED"
    assert service.message_states.state is None
    assert event.workspace_id != workspace_id
