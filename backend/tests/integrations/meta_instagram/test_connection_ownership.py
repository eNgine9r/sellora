from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.integrations.meta_instagram.client import MetaAccountProfile, MetaTokenResult
from app.integrations.meta_instagram.config import OAUTH_REQUIRED_SCOPES
from app.integrations.meta_instagram.exceptions import MetaInstagramError
from app.integrations.meta_instagram.services.connection_service import InstagramConnectionService
from app.models.meta_instagram import InstagramConnection


class OAuthStateService:
    workspace_id = uuid4()
    user_id = uuid4()

    def __init__(self, db) -> None:
        pass

    def validate_state(self, state):
        return SimpleNamespace(
            workspace_id=self.workspace_id,
            user_id=self.user_id,
            redirect_uri="https://api.example/oauth/callback",
            consumed_at=None,
        )


class ConflictingOAuthClient:
    async def exchange_code(self, *, code, redirect_uri):
        return MetaTokenResult(
            access_token="candidate-token",
            user_id="candidate-account",
            expires_at=datetime.now(UTC) + timedelta(days=30),
            granted_permissions=list(OAUTH_REQUIRED_SCOPES),
        )

    async def exchange_long_lived(self, *, access_token):
        return MetaTokenResult(
            access_token="candidate-token-long",
            user_id="candidate-account",
            expires_at=datetime.now(UTC) + timedelta(days=60),
            granted_permissions=list(OAUTH_REQUIRED_SCOPES),
        )

    async def inspect_account(self, *, access_token, token_user_id=None):
        return MetaAccountProfile(
            instagram_account_id="candidate-account",
            username="candidate_shop",
            account_type="BUSINESS",
            granted_permissions=list(OAUTH_REQUIRED_SCOPES),
        )


class Repository:
    def __init__(self, existing) -> None:
        self.existing = existing
        self.created = []

    def get_active(self, workspace_id):
        return self.existing

    def get_connected_in_other_workspace(self, instagram_account_id, workspace_id):
        return SimpleNamespace(id=uuid4(), workspace_id=uuid4())

    def create(self, connection):
        self.created.append(connection)
        return connection


@pytest.mark.asyncio
async def test_conflicting_oauth_preserves_existing_connected_account(monkeypatch):
    existing = InstagramConnection(
        workspace_id=OAuthStateService.workspace_id,
        status="CONNECTED",
        instagram_account_id="existing-account",
        instagram_username="existing_shop",
        instagram_account_type="BUSINESS",
        granted_permissions=list(OAUTH_REQUIRED_SCOPES),
        subscribed_webhook_fields=["messages", "messaging_postbacks"],
        access_token_ciphertext="encrypted-existing-token",
        access_token_key_version="v1",
        connected_at=datetime.now(UTC),
    )
    existing.last_error_code = None
    existing.last_error_message = None
    repository = Repository(existing)

    import app.integrations.meta_instagram.services.connection_service as module
    monkeypatch.setattr(module, "InstagramOAuthService", OAuthStateService)

    service = InstagramConnectionService(SimpleNamespace(), ConflictingOAuthClient())
    service.repo = repository

    with pytest.raises(MetaInstagramError) as exc:
        await service.complete_callback("fresh-state", "fresh-code")

    assert exc.value.code == "META_ACCOUNT_ALREADY_CONNECTED"
    assert repository.created == []
    assert existing.status == "CONNECTED"
    assert existing.instagram_account_id == "existing-account"
    assert existing.instagram_username == "existing_shop"
    assert existing.access_token_ciphertext == "encrypted-existing-token"
    assert existing.subscribed_webhook_fields == ["messages", "messaging_postbacks"]
    assert existing.last_error_code is None
    assert existing.last_error_message is None
