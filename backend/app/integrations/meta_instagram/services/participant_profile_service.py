from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.integrations.meta_instagram.crypto import decrypt_instagram_token
from app.integrations.meta_instagram.exceptions import MetaInstagramError
from app.integrations.meta_instagram.profile_client import (
    InstagramParticipantProfileClient,
    InstagramParticipantProfileClientProtocol,
)
from app.integrations.meta_instagram.repositories.connection_repository import InstagramConnectionRepository
from app.integrations.meta_instagram.repositories.participant_profile_repository import InstagramParticipantProfileRepository
from app.models.ai_direct import DirectChannel
from app.models.instagram_participant_profile import (
    InstagramParticipantProfile,
    InstagramParticipantProfileStatus,
)
from app.models.meta_instagram import InstagramConnectionStatus
from app.repositories.ai_direct_repository import DirectConversationRepository


PROFILE_FRESHNESS = timedelta(hours=24)
PROFILE_PICTURE_CACHE_TTL = timedelta(hours=48)
PROFILE_UNAVAILABLE_RETRY = timedelta(hours=24)


class InstagramParticipantProfileService:
    def __init__(
        self,
        db: Session,
        client_factory=None,
        conversations=None,
        connections=None,
        profiles=None,
    ) -> None:
        self.db = db
        self.client_factory = client_factory
        self.conversations = conversations or DirectConversationRepository(db)
        self.connections = connections or InstagramConnectionRepository(db)
        self.profiles = profiles or InstagramParticipantProfileRepository(db)

    def enrich_if_due(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
    ) -> InstagramParticipantProfile | None:
        return self._enrich(workspace_id, conversation_id, force=False)

    def refresh(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
    ) -> InstagramParticipantProfile:
        profile = self._enrich(workspace_id, conversation_id, force=True)
        if profile is None:
            raise MetaInstagramError(
                "META_PARTICIPANT_PROFILE_NOT_ELIGIBLE",
                "This conversation is not eligible for Instagram profile enrichment.",
                409,
            )
        return profile

    def _enrich(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        *,
        force: bool,
    ) -> InstagramParticipantProfile | None:
        conversation = self.conversations.get(workspace_id, conversation_id)
        if (
            not conversation
            or conversation.channel != DirectChannel.INSTAGRAM.value
            or not conversation.instagram_connection_id
            or not conversation.participant_scoped_id
        ):
            return None

        now = datetime.now(UTC)
        profile = self.profiles.get_by_conversation_for_update(workspace_id, conversation_id)
        if profile is None:
            profile = self.profiles.create(
                InstagramParticipantProfile(
                    workspace_id=workspace_id,
                    conversation_id=conversation.id,
                    instagram_connection_id=conversation.instagram_connection_id,
                    participant_scoped_id=conversation.participant_scoped_id,
                    status=InstagramParticipantProfileStatus.PENDING.value,
                )
            )

        if not force and not self._is_due(profile, now):
            return profile

        connection = self.connections.get(workspace_id, conversation.instagram_connection_id)
        if (
            not connection
            or connection.status != InstagramConnectionStatus.CONNECTED.value
            or not connection.access_token_ciphertext
        ):
            self._mark_unavailable(
                profile,
                now,
                "META_CONNECTION_NOT_READY",
                "Instagram connection is not ready for participant profile enrichment.",
            )
            return profile

        profile.attempt_count = (profile.attempt_count or 0) + 1
        token = decrypt_instagram_token(connection.access_token_ciphertext)
        client = self._client(token)
        try:
            result = client.fetch_profile(conversation.participant_scoped_id)
        except MetaInstagramError as exc:
            if exc.status_code in {429, 500, 502, 503, 504}:
                self._mark_retry(profile, now, exc)
            else:
                self._mark_unavailable(profile, now, exc.code, exc.message)
            return profile

        profile.display_name = result.name
        profile.username = result.username
        profile.profile_picture_url = result.profile_picture_url
        profile.profile_picture_expires_at = (
            now + PROFILE_PICTURE_CACHE_TTL if result.profile_picture_url else None
        )
        profile.follower_count = result.follower_count
        profile.is_verified_user = result.is_verified_user
        profile.is_user_follow_business = result.is_user_follow_business
        profile.is_business_follow_user = result.is_business_follow_user
        profile.status = InstagramParticipantProfileStatus.READY.value
        profile.last_synced_at = now
        profile.next_retry_at = None
        profile.last_error_code = None
        profile.last_error_message = None

        conversation.participant_display_name = (
            result.name
            or result.username
            or conversation.participant_display_name
            or "Instagram customer"
        )
        if result.username:
            conversation.participant_username = result.username
        conversation.provider_sync_status = "PROFILE_READY"
        self.db.flush()
        return profile

    def _is_due(self, profile: InstagramParticipantProfile, now: datetime) -> bool:
        if profile.next_retry_at and profile.next_retry_at > now:
            return False
        if profile.status != InstagramParticipantProfileStatus.READY.value:
            return True
        if not profile.last_synced_at or profile.last_synced_at + PROFILE_FRESHNESS <= now:
            return True
        if (
            profile.profile_picture_url
            and profile.profile_picture_expires_at
            and profile.profile_picture_expires_at <= now + timedelta(hours=6)
        ):
            return True
        return False

    def _mark_retry(
        self,
        profile: InstagramParticipantProfile,
        now: datetime,
        exc: MetaInstagramError,
    ) -> None:
        minutes = min(2 ** min(profile.attempt_count or 1, 8), 360)
        profile.status = InstagramParticipantProfileStatus.RETRY_PENDING.value
        profile.next_retry_at = now + timedelta(minutes=minutes)
        profile.last_error_code = exc.code
        profile.last_error_message = exc.message[:300]
        self.db.flush()

    def _mark_unavailable(
        self,
        profile: InstagramParticipantProfile,
        now: datetime,
        code: str,
        message: str,
    ) -> None:
        profile.status = InstagramParticipantProfileStatus.UNAVAILABLE.value
        profile.next_retry_at = now + PROFILE_UNAVAILABLE_RETRY
        profile.last_error_code = code
        profile.last_error_message = message[:300]
        self.db.flush()

    def _client(self, access_token: str) -> InstagramParticipantProfileClientProtocol:
        if self.client_factory:
            return self.client_factory(access_token)
        settings = get_settings()
        return InstagramParticipantProfileClient(
            settings.meta_graph_api_base_url,
            settings.meta_graph_api_version,
            access_token,
        )
