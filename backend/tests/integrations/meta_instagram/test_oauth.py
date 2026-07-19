from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.integrations.meta_instagram.client import MetaAccountProfile, MetaTokenResult, MetaWebhookSubscriptionResult
from app.integrations.meta_instagram.config import OAUTH_REQUIRED_SCOPES, REQUIRED_BASIC_PERMISSION, REQUIRED_MESSAGING_PERMISSION, WEBHOOK_SUBSCRIPTIONS
from app.integrations.meta_instagram.exceptions import MetaInstagramError
from app.integrations.meta_instagram.services.connection_service import InstagramConnectionService
from app.models.meta_instagram import InstagramConnection


class FakeWebhookClient:
    subscribe_success = True
    confirmed_fields = list(WEBHOOK_SUBSCRIPTIONS)
    fail_code: str | None = None
    calls: list[tuple] = []

    def __init__(self, base_url, version, access_token):
        self.base_url = base_url
        self.version = version
        self.access_token = access_token

    @classmethod
    def reset(cls):
        cls.subscribe_success = True
        cls.confirmed_fields = list(WEBHOOK_SUBSCRIPTIONS)
        cls.fail_code = None
        cls.calls = []

    async def subscribe_webhooks(self, instagram_account_id, subscribed_fields):
        self.__class__.calls.append(("subscribe", instagram_account_id, tuple(subscribed_fields), self.access_token))
        if self.fail_code:
            raise MetaInstagramError(self.fail_code, "Webhook subscription failed.", 400)
        return MetaWebhookSubscriptionResult(self.subscribe_success, list(subscribed_fields), "trace-subscribe")

    async def get_webhook_subscription(self, instagram_account_id):
        self.__class__.calls.append(("get", instagram_account_id, tuple(self.confirmed_fields), self.access_token))
        return MetaWebhookSubscriptionResult(True, list(self.confirmed_fields), "trace-get")

    async def unsubscribe_webhooks(self, instagram_account_id):
        self.__class__.calls.append(("unsubscribe", instagram_account_id, (), self.access_token))
        return MetaWebhookSubscriptionResult(True, [], "trace-delete")


@pytest.fixture(autouse=True)
def fake_webhook_client(monkeypatch):
    FakeWebhookClient.reset()
    import app.integrations.meta_instagram.services.connection_service as module
    monkeypatch.setattr(module, "MetaInstagramClient", FakeWebhookClient)
    yield FakeWebhookClient


class FakeOAuthStateService:
    def __init__(self, db):
        pass

    def validate_state(self, state):
        return SimpleNamespace(workspace_id=uuid4(), user_id=uuid4(), redirect_uri="https://app/callback", consumed_at=None)


class FakeRepo:
    def __init__(self, db):
        self.connection = None

    def get_active(self, workspace_id):
        return self.connection

    def get_connected_in_other_workspace(self, instagram_account_id, workspace_id):
        return None

    def create(self, connection):
        self.connection = connection
        return connection


class FakeClient:
    def __init__(self, permissions=None, account_type="BUSINESS", token="real-token"):
        self.permissions = list(OAUTH_REQUIRED_SCOPES) if permissions is None else permissions
        self.account_type = account_type
        self.token = token
        self.calls = []

    async def exchange_code(self, *, code, redirect_uri):
        self.calls.append(("exchange", code, redirect_uri))
        return MetaTokenResult(access_token=self.token, user_id="ig-1", expires_at=datetime.now(UTC) + timedelta(days=30), granted_permissions=self.permissions)

    async def exchange_long_lived(self, *, access_token):
        self.calls.append(("long", access_token))
        return MetaTokenResult(access_token=access_token + "-long", user_id="ig-1", expires_at=datetime.now(UTC) + timedelta(days=60), granted_permissions=self.permissions)

    async def inspect_account(self, *, access_token, token_user_id=None):
        self.calls.append(("inspect", access_token))
        return MetaAccountProfile("ig-1", "shop", self.account_type, self.permissions)


@pytest.mark.asyncio
async def test_oauth_exchanges_code_and_never_stores_code(monkeypatch):
    monkeypatch.setenv("META_APP_ID", "app")
    monkeypatch.setenv("META_APP_SECRET", "secret")
    monkeypatch.setenv("META_TOKEN_ENCRYPTION_KEY", "vuyQfS5xPfYx7yUxsaTpWFjYjwjzFNEsk3KN519QcSY=")
    from app.core.config import get_settings
    get_settings.cache_clear()
    import app.integrations.meta_instagram.services.connection_service as module
    repo = FakeRepo(None)
    monkeypatch.setattr(module, "InstagramOAuthService", FakeOAuthStateService)
    monkeypatch.setattr(module, "InstagramConnectionRepository", lambda db: repo)
    client = FakeClient(token="authorization-code-must-not-be-stored")
    connection = await InstagramConnectionService(SimpleNamespace(), client).complete_callback("state", "code-value")
    assert connection.status == "CONNECTED"
    assert connection.access_token_ciphertext != "code-value"
    assert connection.access_token_ciphertext != "authorization-code-must-not-be-stored"
    assert ("exchange", "code-value", "https://app/callback") in client.calls
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_oauth_permission_missing_does_not_connect(monkeypatch):
    monkeypatch.setenv("META_APP_ID", "app")
    monkeypatch.setenv("META_APP_SECRET", "secret")
    from app.core.config import get_settings
    get_settings.cache_clear()
    import app.integrations.meta_instagram.services.connection_service as module
    monkeypatch.setattr(module, "InstagramOAuthService", FakeOAuthStateService)
    monkeypatch.setattr(module, "InstagramConnectionRepository", lambda db: FakeRepo(db))
    connection = await InstagramConnectionService(SimpleNamespace(), FakeClient(permissions=[])).complete_callback("state", "code-value")
    assert connection.status == "PERMISSION_MISSING"
    assert connection.access_token_ciphertext is None
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_oauth_non_professional_account_rejected(monkeypatch):
    monkeypatch.setenv("META_APP_ID", "app")
    monkeypatch.setenv("META_APP_SECRET", "secret")
    import app.integrations.meta_instagram.services.connection_service as module
    monkeypatch.setattr(module, "InstagramOAuthService", FakeOAuthStateService)
    monkeypatch.setattr(module, "InstagramConnectionRepository", lambda db: FakeRepo(db))
    with pytest.raises(MetaInstagramError) as exc:
        await InstagramConnectionService(SimpleNamespace(), FakeClient(account_type="PERSONAL")).complete_callback("state", "code-value")
    assert exc.value.code == "META_ACCOUNT_NOT_PROFESSIONAL"


def test_oauth_start_requests_basic_and_messaging_only(monkeypatch):
    monkeypatch.setenv("META_APP_ID", "app")
    monkeypatch.setenv("META_OAUTH_REDIRECT_URI", "https://api/callback")
    monkeypatch.setenv("META_INSTAGRAM_OAUTH_AUTHORIZE_URL", "https://instagram.example/oauth")
    from app.core.config import get_settings
    get_settings.cache_clear()
    from app.integrations.meta_instagram.services.oauth_service import InstagramOAuthService
    created = []

    class StateRepo:
        def __init__(self, db):
            pass

        def create(self, row):
            created.append(row)
            return row

    import app.integrations.meta_instagram.services.oauth_service as module
    monkeypatch.setattr(module, "MetaOAuthStateRepository", StateRepo)
    url, _ = InstagramOAuthService(SimpleNamespace()).start(uuid4(), uuid4())
    assert "scope=instagram_business_basic%2Cinstagram_business_manage_messages" in url
    assert "instagram_business_basic" in url
    assert "instagram_business_manage_messages" in url
    assert "instagram_basic" not in url
    assert "pages_show_list" not in url
    assert created
    get_settings.cache_clear()


def test_token_result_preserves_provider_identity_and_permissions():
    result = MetaTokenResult(access_token="token", user_id="ig-user", expires_at=datetime.now(UTC), granted_permissions=list(OAUTH_REQUIRED_SCOPES))
    assert result.access_token == "token"
    assert result.user_id == "ig-user"
    assert result.granted_permissions == list(OAUTH_REQUIRED_SCOPES)


@pytest.mark.asyncio
async def test_oauth_creator_account_connects(monkeypatch):
    monkeypatch.setenv("META_APP_ID", "app")
    monkeypatch.setenv("META_APP_SECRET", "secret")
    monkeypatch.setenv("META_TOKEN_ENCRYPTION_KEY", "vuyQfS5xPfYx7yUxsaTpWFjYjwjzFNEsk3KN519QcSY=")
    from app.core.config import get_settings
    get_settings.cache_clear()
    import app.integrations.meta_instagram.services.connection_service as module
    monkeypatch.setattr(module, "InstagramOAuthService", FakeOAuthStateService)
    monkeypatch.setattr(module, "InstagramConnectionRepository", lambda db: FakeRepo(db))
    connection = await InstagramConnectionService(SimpleNamespace(), FakeClient(account_type="CREATOR")).complete_callback("state", "code-value")
    assert connection.status == "CONNECTED"
    assert connection.instagram_account_type == "CREATOR"
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_oauth_missing_basic_permission_does_not_connect(monkeypatch):
    monkeypatch.setenv("META_APP_ID", "app")
    monkeypatch.setenv("META_APP_SECRET", "secret")
    from app.core.config import get_settings
    get_settings.cache_clear()
    import app.integrations.meta_instagram.services.connection_service as module
    monkeypatch.setattr(module, "InstagramOAuthService", FakeOAuthStateService)
    monkeypatch.setattr(module, "InstagramConnectionRepository", lambda db: FakeRepo(db))
    connection = await InstagramConnectionService(SimpleNamespace(), FakeClient(permissions=[REQUIRED_MESSAGING_PERMISSION])).complete_callback("state", "code-value")
    assert connection.status == "PERMISSION_MISSING"
    assert connection.access_token_ciphertext is None
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_oauth_missing_messaging_permission_does_not_connect(monkeypatch):
    monkeypatch.setenv("META_APP_ID", "app")
    monkeypatch.setenv("META_APP_SECRET", "secret")
    from app.core.config import get_settings
    get_settings.cache_clear()
    import app.integrations.meta_instagram.services.connection_service as module
    monkeypatch.setattr(module, "InstagramOAuthService", FakeOAuthStateService)
    monkeypatch.setattr(module, "InstagramConnectionRepository", lambda db: FakeRepo(db))
    connection = await InstagramConnectionService(SimpleNamespace(), FakeClient(permissions=[REQUIRED_BASIC_PERMISSION])).complete_callback("state", "code-value")
    assert connection.status == "PERMISSION_MISSING"
    assert connection.access_token_ciphertext is None
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_oauth_profile_failure_uses_precise_safe_error(monkeypatch):
    class ProfileFailureClient(FakeClient):
        async def inspect_account(self, *, access_token, token_user_id=None):
            raise MetaInstagramError("META_ACCOUNT_PROFILE_VALIDATION_FAILED", "Meta account profile validation failed.")

    monkeypatch.setenv("META_APP_ID", "app")
    monkeypatch.setenv("META_APP_SECRET", "secret")
    import app.integrations.meta_instagram.services.connection_service as module
    repo = FakeRepo(None)
    monkeypatch.setattr(module, "InstagramOAuthService", FakeOAuthStateService)
    monkeypatch.setattr(module, "InstagramConnectionRepository", lambda db: repo)
    with pytest.raises(MetaInstagramError) as exc:
        await InstagramConnectionService(SimpleNamespace(), ProfileFailureClient()).complete_callback("state", "code-value")
    assert exc.value.code == "META_ACCOUNT_PROFILE_VALIDATION_FAILED"
    assert repo.connection.status == "FAILED"
    assert repo.connection.access_token_ciphertext is None
    assert repo.connection.last_error_code == exc.value.code


@pytest.mark.asyncio
async def test_oauth_permission_failure_uses_precise_safe_error(monkeypatch):
    class PermissionFailureClient(FakeClient):
        async def inspect_account(self, *, access_token, token_user_id=None):
            raise MetaInstagramError("META_PERMISSION_VALIDATION_FAILED", "Meta permission validation failed.")

    monkeypatch.setenv("META_APP_ID", "app")
    monkeypatch.setenv("META_APP_SECRET", "secret")
    import app.integrations.meta_instagram.services.connection_service as module
    repo = FakeRepo(None)
    monkeypatch.setattr(module, "InstagramOAuthService", FakeOAuthStateService)
    monkeypatch.setattr(module, "InstagramConnectionRepository", lambda db: repo)
    with pytest.raises(MetaInstagramError) as exc:
        await InstagramConnectionService(SimpleNamespace(), PermissionFailureClient()).complete_callback("state", "code-value")
    assert exc.value.code == "META_PERMISSION_VALIDATION_FAILED"
    assert repo.connection.status == "FAILED"
    assert repo.connection.access_token_ciphertext is None
    assert repo.connection.last_error_code == exc.value.code


def test_permissions_hint_avoids_facebook_login_permissions_endpoint(monkeypatch):
    from app.integrations.meta_instagram.client import MetaInstagramOAuthClient
    client = MetaInstagramOAuthClient(app_id="app", app_secret="secret", token_url="https://token", graph_base_url="https://graph.example", graph_version="v1")
    payload = {"access_token": "token", "user_id": "ig-1", "scope": "instagram_business_basic,instagram_business_manage_messages"}
    permissions = client._permissions_from_payload(payload)
    assert permissions == list(OAUTH_REQUIRED_SCOPES)


@pytest.mark.asyncio
async def test_inspect_account_uses_scope_evidence_without_permissions_endpoint(monkeypatch):
    from app.integrations.meta_instagram.client import MetaInstagramOAuthClient

    class Response:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"id": "ig-1", "username": "shop", "account_type": "BUSINESS"}

    class AsyncClient:
        calls = []

        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, headers=None, params=None):
            self.calls.append((url, params))
            assert not url.endswith("/me/permissions")
            assert headers == {"Authorization": "Bearer token"}
            return Response()

    import app.integrations.meta_instagram.client as module
    monkeypatch.setattr(module.httpx, "AsyncClient", AsyncClient)
    client = MetaInstagramOAuthClient(app_id="app", app_secret="secret", token_url="https://token", graph_base_url="https://graph.example", graph_version="v1")
    client._last_granted_permissions = list(OAUTH_REQUIRED_SCOPES)
    profile = await client.inspect_account(access_token="token")
    assert profile.instagram_account_id == "ig-1"
    assert profile.granted_permissions == list(OAUTH_REQUIRED_SCOPES)
