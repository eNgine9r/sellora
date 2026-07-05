from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.meta_ads import router
from app.core.config import Settings
from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.rbac import get_workspace_id
from app.integrations.meta_ads.live_oauth_client import MetaTokenExchangeResult
from app.integrations.meta_ads.oauth_state import generate_live_oauth_state
from app.integrations.meta_ads.token_crypto import decrypt_token
from app.models.meta_ad_connection import MetaAdConnection, MetaAdConnectionStatus
from app.models.role import RoleName
from app.services.meta_ads_connection_service import MetaAdsConnectionService


class StubDb:
    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1


class FakeRepository:
    def __init__(self) -> None:
        self.connection: MetaAdConnection | None = None

    def get_current(self, workspace_id: UUID) -> MetaAdConnection | None:
        if self.connection and self.connection.workspace_id == workspace_id:
            return self.connection
        return None

    def get_or_create(self, workspace_id: UUID) -> MetaAdConnection:
        current = self.get_current(workspace_id)
        if current:
            return current
        self.connection = MetaAdConnection(workspace_id=workspace_id, provider="meta_ads")
        return self.connection


class FakeExchangeClient:
    def exchange_code_for_token(self, *, code: str, redirect_uri: str) -> MetaTokenExchangeResult:
        assert code == "synthetic-code"
        assert redirect_uri == "https://backend.example.test/api/v1/integrations/meta-ads/oauth/callback"
        return MetaTokenExchangeResult(
            access_token="synthetic_meta_access_token_for_tests_only",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            scopes=("ads_read",),
        )


def _settings(**overrides):
    data = {
        "meta_connections_enabled": False,
        "meta_live_oauth_enabled": False,
        "meta_token_storage_enabled": False,
        "meta_sync_enabled": False,
        "meta_app_id": None,
        "meta_app_secret": None,
        "meta_oauth_redirect_uri": None,
        "meta_oauth_authorize_url": None,
        "meta_token_encryption_key": None,
    }
    data.update(overrides)
    return Settings(_env_file=None, **data)


def _user(workspace_id, role: RoleName):
    return SimpleNamespace(
        id=uuid4(),
        workspaces=[SimpleNamespace(workspace_id=workspace_id, workspace=SimpleNamespace(is_active=True), role=SimpleNamespace(name=role.value))],
    )


def _client(role: RoleName):
    workspace_id = uuid4()
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    user = _user(workspace_id, role)
    app.dependency_overrides[get_workspace_id] = lambda: workspace_id
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: StubDb()
    return TestClient(app), workspace_id, user


def test_status_route_is_safe_when_feature_gates_are_disabled(monkeypatch) -> None:
    client, workspace_id, _ = _client(RoleName.ANALYST)

    class FakeService:
        def __init__(self, db):
            pass

        def get_status(self, workspace_id_arg, user_id):
            assert workspace_id_arg == workspace_id
            return MetaAdsConnectionService(StubDb(), settings=_settings(), repository=FakeRepository()).get_status(workspace_id_arg, user_id)

    monkeypatch.setattr("app.api.v1.meta_ads.MetaAdsConnectionService", FakeService)
    response = client.get("/api/v1/integrations/meta-ads/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["connection_status"] == "NOT_CONNECTED"
    assert payload["live_oauth_enabled"] is False
    assert payload["connected"] is False
    assert "access_token" not in str(payload)
    assert "encrypted_access_token" not in str(payload)


def test_start_route_is_owner_only_and_disabled_safely(monkeypatch) -> None:
    class FakeService:
        def __init__(self, db):
            pass

        def start_oauth(self, workspace_id, user_id):
            return MetaAdsConnectionService(StubDb(), settings=_settings(), repository=FakeRepository()).start_oauth(workspace_id, user_id)

    monkeypatch.setattr("app.api.v1.meta_ads.MetaAdsConnectionService", FakeService)
    owner_client, _, _ = _client(RoleName.OWNER)
    manager_client, _, _ = _client(RoleName.MANAGER)
    analyst_client, _, _ = _client(RoleName.ANALYST)

    assert owner_client.post("/api/v1/integrations/meta-ads/oauth/start").status_code == 403
    assert manager_client.post("/api/v1/integrations/meta-ads/oauth/start").status_code == 403
    assert analyst_client.post("/api/v1/integrations/meta-ads/oauth/start").status_code == 403


def test_start_requires_config_when_enabled() -> None:
    service = MetaAdsConnectionService(
        StubDb(),
        settings=_settings(meta_connections_enabled=True, meta_live_oauth_enabled=True),
        repository=FakeRepository(),
    )

    try:
        service.start_oauth(uuid4(), uuid4())
    except Exception as exc:
        assert "not available" in str(exc)
    else:
        raise AssertionError("missing OAuth config should block start")


def test_start_can_create_connecting_state_when_explicitly_enabled_and_configured() -> None:
    repo = FakeRepository()
    service = MetaAdsConnectionService(
        StubDb(),
        settings=_settings(
            meta_connections_enabled=True,
            meta_live_oauth_enabled=True,
            meta_app_id="test-app-id",
            meta_oauth_redirect_uri="https://backend.example.test/api/v1/integrations/meta-ads/oauth/callback",
            meta_oauth_authorize_url="https://meta-oauth.example.test/authorize",
        ),
        repository=repo,
    )

    response = service.start_oauth(uuid4(), uuid4())

    assert response.authorization_url is not None
    assert response.authorization_url.startswith("https://meta-oauth.example.test/authorize")
    assert "test-app-id" in response.authorization_url
    assert "app_secret" not in response.authorization_url
    assert repo.connection is not None
    assert repo.connection.connection_status == MetaAdConnectionStatus.CONNECTING.value


def test_callback_rejects_invalid_state_and_persists_only_encrypted_synthetic_token() -> None:
    workspace_id = uuid4()
    user_id = uuid4()
    key = Fernet.generate_key().decode("utf-8")
    repo = FakeRepository()
    service = MetaAdsConnectionService(
        StubDb(),
        settings=_settings(
            meta_connections_enabled=True,
            meta_live_oauth_enabled=True,
            meta_token_storage_enabled=True,
            meta_oauth_redirect_uri="https://backend.example.test/api/v1/integrations/meta-ads/oauth/callback",
            meta_token_encryption_key=key,
        ),
        repository=repo,
        token_exchange_client=FakeExchangeClient(),
    )

    try:
        service.complete_callback(workspace_id, user_id, state="invalid", code="synthetic-code")
    except Exception as exc:
        assert "state" in str(exc).lower()
    else:
        raise AssertionError("invalid state should fail")

    state, _ = generate_live_oauth_state(workspace_id, user_id)
    response = service.complete_callback(workspace_id, user_id, state=state, code="synthetic-code")

    assert response.connected is True
    assert response.token_stored is True
    assert response.token_fingerprint
    assert "synthetic_meta_access_token" not in response.model_dump_json()
    assert repo.connection is not None
    assert repo.connection.encrypted_access_token is not None
    assert "synthetic_meta_access_token" not in repo.connection.encrypted_access_token
    assert decrypt_token(repo.connection.encrypted_access_token, key) == "synthetic_meta_access_token_for_tests_only"


def test_disconnect_marks_connection_safely_without_returning_token() -> None:
    workspace_id = uuid4()
    repo = FakeRepository()
    connection = repo.get_or_create(workspace_id)
    connection.connection_status = MetaAdConnectionStatus.CONNECTED.value
    connection.encrypted_access_token = "encrypted-value"
    connection.token_fingerprint = "fingerprint"
    service = MetaAdsConnectionService(StubDb(), settings=_settings(meta_connections_enabled=True), repository=repo)

    response = service.disconnect(workspace_id, uuid4())

    assert response.connection_status == "DISCONNECTED"
    assert response.disconnected is True
    assert connection.encrypted_access_token is None
    assert connection.token_fingerprint is None
    assert "encrypted-value" not in response.model_dump_json()
