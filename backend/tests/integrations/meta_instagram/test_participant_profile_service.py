from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.integrations.meta_instagram.exceptions import MetaInstagramError
from app.integrations.meta_instagram.profile_client import InstagramParticipantProfileResult
from app.integrations.meta_instagram.services.participant_profile_service import InstagramParticipantProfileService
from app.models.instagram_participant_profile import InstagramParticipantProfileStatus


class FakeDB:
    def flush(self):
        return None


class FakeConversationRepo:
    def __init__(self, workspace_id, conversation):
        self.workspace_id = workspace_id
        self.conversation = conversation

    def get(self, workspace_id, conversation_id):
        if workspace_id != self.workspace_id or conversation_id != self.conversation.id:
            return None
        return self.conversation


class FakeConnectionRepo:
    def __init__(self, workspace_id, connection):
        self.workspace_id = workspace_id
        self.connection = connection

    def get(self, workspace_id, connection_id):
        if workspace_id != self.workspace_id or connection_id != self.connection.id:
            return None
        return self.connection


class FakeProfileRepo:
    def __init__(self):
        self.profile = None

    def get_by_conversation_for_update(self, workspace_id, conversation_id):
        if self.profile and self.profile.workspace_id == workspace_id and self.profile.conversation_id == conversation_id:
            return self.profile
        return None

    def create(self, profile):
        self.profile = profile
        return profile


class FakeClient:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = 0

    def fetch_profile(self, participant_scoped_id):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


def make_context():
    workspace_id = uuid4()
    connection_id = uuid4()
    conversation = SimpleNamespace(
        id=uuid4(),
        workspace_id=workspace_id,
        channel="INSTAGRAM",
        instagram_connection_id=connection_id,
        participant_scoped_id="ig-scoped-123",
        participant_display_name="Instagram customer",
        participant_username=None,
        provider_sync_status="PROFILE_PENDING",
    )
    connection = SimpleNamespace(
        id=connection_id,
        workspace_id=workspace_id,
        status="CONNECTED",
        access_token_ciphertext="encrypted-token",
    )
    profiles = FakeProfileRepo()
    return workspace_id, conversation, connection, profiles


def make_service(monkeypatch, client):
    workspace_id, conversation, connection, profiles = make_context()
    monkeypatch.setattr(
        "app.integrations.meta_instagram.services.participant_profile_service.decrypt_instagram_token",
        lambda _: "plain-token",
    )
    service = InstagramParticipantProfileService(
        FakeDB(),
        client_factory=lambda token: client,
        conversations=FakeConversationRepo(workspace_id, conversation),
        connections=FakeConnectionRepo(workspace_id, connection),
        profiles=profiles,
    )
    return workspace_id, conversation, profiles, service


def test_enrichment_updates_conversation_and_cached_profile(monkeypatch):
    result = InstagramParticipantProfileResult(
        participant_scoped_id="ig-scoped-123",
        name="Марія Коваль",
        username="maria.shop",
        profile_picture_url="https://example.test/avatar.jpg",
        follower_count=1240,
        is_verified_user=True,
        is_user_follow_business=True,
        is_business_follow_user=False,
    )
    client = FakeClient(result=result)
    workspace_id, conversation, profiles, service = make_service(monkeypatch, client)

    profile = service.refresh(workspace_id, conversation.id)

    assert client.calls == 1
    assert profile.status == InstagramParticipantProfileStatus.READY.value
    assert profile.display_name == "Марія Коваль"
    assert profile.username == "maria.shop"
    assert profile.profile_picture_url.endswith("avatar.jpg")
    assert profile.profile_picture_expires_at > datetime.now(UTC)
    assert profile.follower_count == 1240
    assert profile.is_verified_user is True
    assert profile.is_user_follow_business is True
    assert profile.is_business_follow_user is False
    assert profile.last_error_code is None
    assert conversation.participant_display_name == "Марія Коваль"
    assert conversation.participant_username == "maria.shop"
    assert conversation.provider_sync_status == "PROFILE_READY"
    assert profiles.profile is profile


def test_rate_limit_is_stored_as_bounded_retry(monkeypatch):
    client = FakeClient(
        error=MetaInstagramError(
            "META_PARTICIPANT_PROFILE_RATE_LIMITED",
            "Meta rate limited participant profile enrichment.",
            429,
        )
    )
    workspace_id, conversation, _, service = make_service(monkeypatch, client)

    profile = service.refresh(workspace_id, conversation.id)

    assert profile.status == InstagramParticipantProfileStatus.RETRY_PENDING.value
    assert profile.next_retry_at > datetime.now(UTC)
    assert profile.last_error_code == "META_PARTICIPANT_PROFILE_RATE_LIMITED"
    assert conversation.participant_display_name == "Instagram customer"


def test_unavailable_profile_keeps_truthful_fallback(monkeypatch):
    client = FakeClient(
        error=MetaInstagramError(
            "META_PARTICIPANT_PROFILE_UNAVAILABLE",
            "Instagram participant profile is unavailable for this conversation.",
            409,
        )
    )
    workspace_id, conversation, _, service = make_service(monkeypatch, client)

    profile = service.refresh(workspace_id, conversation.id)

    assert profile.status == InstagramParticipantProfileStatus.UNAVAILABLE.value
    assert profile.next_retry_at > datetime.now(UTC)
    assert profile.last_error_code == "META_PARTICIPANT_PROFILE_UNAVAILABLE"
    assert conversation.participant_display_name == "Instagram customer"
    assert conversation.participant_username is None


def test_cross_workspace_conversation_is_not_enriched(monkeypatch):
    client = FakeClient(result=None)
    workspace_id, conversation, _, service = make_service(monkeypatch, client)

    with pytest.raises(MetaInstagramError) as exc_info:
        service.refresh(uuid4(), conversation.id)

    assert exc_info.value.code == "META_PARTICIPANT_PROFILE_NOT_ELIGIBLE"
    assert client.calls == 0
