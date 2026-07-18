from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.integrations.meta_instagram.client import MetaAccountProfile, MetaTokenResult
from app.integrations.meta_instagram.config import REQUIRED_MESSAGING_PERMISSION
from app.integrations.meta_instagram.exceptions import MetaInstagramError
from app.integrations.meta_instagram.services.connection_service import InstagramConnectionService
from app.models.meta_instagram import InstagramConnection


class FakeOAuthStateService:
    def __init__(self, db): pass
    def validate_state(self, state):
        return SimpleNamespace(workspace_id=uuid4(), user_id=uuid4(), redirect_uri="https://app/callback", consumed_at=None)

class FakeRepo:
    def __init__(self, db): self.connection = None
    def get_active(self, workspace_id): return self.connection
    def create(self, connection): self.connection = connection; return connection

class FakeClient:
    def __init__(self, permissions=None, account_type="BUSINESS", token="real-token"):
        self.permissions = [REQUIRED_MESSAGING_PERMISSION] if permissions is None else permissions
        self.account_type = account_type
        self.token = token
        self.calls = []
    async def exchange_code(self, *, code, redirect_uri):
        self.calls.append(("exchange", code, redirect_uri)); return MetaTokenResult(access_token=self.token, expires_at=datetime.now(UTC)+timedelta(days=30))
    async def exchange_long_lived(self, *, access_token):
        self.calls.append(("long", access_token)); return MetaTokenResult(access_token=access_token+"-long", expires_at=datetime.now(UTC)+timedelta(days=60))
    async def inspect_account(self, *, access_token):
        self.calls.append(("inspect", access_token)); return MetaAccountProfile("ig-1", "shop", self.account_type, self.permissions)

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
