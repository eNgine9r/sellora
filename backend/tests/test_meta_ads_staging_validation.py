from __future__ import annotations

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
from app.integrations.meta_ads.read_only_client import FakeMetaAdsReadOnlyClient
from app.integrations.meta_ads.token_crypto import encrypt_token
from app.models.meta_ad_connection import MetaAdConnection, MetaAdConnectionStatus
from app.models.role import RoleName
from app.services.meta_ads_staging_validation_service import MetaAdsStagingValidationService


class WriteTrapDb:
    def commit(self) -> None:
        raise AssertionError("staging validation must not commit")

    def flush(self) -> None:
        raise AssertionError("staging validation must not flush")


class FakeConnectionRepository:
    def __init__(self, connection: MetaAdConnection | None = None) -> None:
        self.connection = connection

    def get_current(self, workspace_id: UUID) -> MetaAdConnection | None:
        if self.connection and self.connection.workspace_id == workspace_id:
            return self.connection
        return None


def _settings(**overrides):
    data = {
        "meta_connections_enabled": False,
        "meta_token_storage_enabled": False,
        "meta_sync_enabled": False,
        "meta_staging_validation_enabled": False,
        "meta_token_encryption_key": None,
    }
    data.update(overrides)
    return Settings(_env_file=None, **data)


def _user(workspace_id, role: RoleName):
    return SimpleNamespace(
        id=uuid4(),
        workspaces=[SimpleNamespace(workspace_id=workspace_id, workspace=SimpleNamespace(is_active=True), role=SimpleNamespace(name=role.value))],
    )


def _client(role: RoleName = RoleName.OWNER):
    workspace_id = uuid4()
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    user = _user(workspace_id, role)
    app.dependency_overrides[get_workspace_id] = lambda: workspace_id
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: WriteTrapDb()
    return TestClient(app), workspace_id, user


def _connected(workspace_id: UUID, encrypted_token: str | None) -> MetaAdConnection:
    return MetaAdConnection(
        workspace_id=workspace_id,
        provider="meta_ads",
        connection_status=MetaAdConnectionStatus.CONNECTED.value,
        encrypted_access_token=encrypted_token,
    )


def test_staging_validation_route_is_disabled_by_default(monkeypatch) -> None:
    client, workspace_id, _ = _client(RoleName.OWNER)

    class FakeService:
        def __init__(self, db):
            self.service = MetaAdsStagingValidationService(db, settings=_settings(), connection_repository=FakeConnectionRepository())

        def validate_read_only(self, workspace_id_arg):
            assert workspace_id_arg == workspace_id
            return self.service.validate_read_only(workspace_id_arg)

    monkeypatch.setattr("app.api.v1.meta_ads.MetaAdsStagingValidationService", FakeService)

    response = client.post("/api/v1/integrations/meta-ads/staging/validate-read-only")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ready"] is False
    assert payload["reason"] == "feature_disabled"
    assert payload["sync_active"] is False
    assert payload["writes_performed"] is False
    assert "access_token" not in str(payload)
    assert "encrypted_access_token" not in str(payload)


def test_staging_validation_route_is_owner_only(monkeypatch) -> None:
    class FakeService:
        def __init__(self, db):
            pass

        def validate_read_only(self, workspace_id_arg):
            raise AssertionError("non-owner roles must not reach staging validation service")

    monkeypatch.setattr("app.api.v1.meta_ads.MetaAdsStagingValidationService", FakeService)

    for role in (RoleName.MANAGER, RoleName.ANALYST):
        client, _, _ = _client(role)
        response = client.post("/api/v1/integrations/meta-ads/staging/validate-read-only")
        assert response.status_code == 403


def test_staging_validation_returns_not_ready_when_connection_missing() -> None:
    workspace_id = uuid4()
    service = MetaAdsStagingValidationService(
        WriteTrapDb(),
        settings=_settings(meta_staging_validation_enabled=True, meta_connections_enabled=True),
        connection_repository=FakeConnectionRepository(),
        client=FakeMetaAdsReadOnlyClient(),
    )

    response = service.validate_read_only(workspace_id)

    assert response.ready is False
    assert response.reason == "connection_not_ready"
    assert response.sync_active is False
    assert response.writes_performed is False


def test_staging_validation_returns_not_ready_when_token_missing() -> None:
    workspace_id = uuid4()
    service = MetaAdsStagingValidationService(
        WriteTrapDb(),
        settings=_settings(meta_staging_validation_enabled=True, meta_connections_enabled=True),
        connection_repository=FakeConnectionRepository(_connected(workspace_id, encrypted_token=None)),
        client=FakeMetaAdsReadOnlyClient(),
    )

    response = service.validate_read_only(workspace_id)

    assert response.ready is False
    assert response.reason == "token_missing"
    assert response.sync_active is False
    assert response.writes_performed is False


def test_staging_validation_uses_fake_client_and_never_returns_token() -> None:
    workspace_id = uuid4()
    key = Fernet.generate_key().decode("utf-8")
    encrypted_token = encrypt_token("synthetic-token-for-staging-validation", key)
    service = MetaAdsStagingValidationService(
        WriteTrapDb(),
        settings=_settings(
            meta_staging_validation_enabled=True,
            meta_connections_enabled=True,
            meta_token_storage_enabled=True,
            meta_token_encryption_key=key,
        ),
        connection_repository=FakeConnectionRepository(_connected(workspace_id, encrypted_token=encrypted_token)),
        client=FakeMetaAdsReadOnlyClient(),
    )

    response = service.validate_read_only(workspace_id)
    serialized = response.model_dump_json()

    assert response.ready is True
    assert response.mode == "fake"
    assert response.account_preview_count > 0
    assert response.campaign_preview_count > 0
    assert response.insights_preview_sample_count > 0
    assert response.sync_active is False
    assert response.writes_performed is False
    assert "synthetic-token-for-staging-validation" not in serialized
    assert encrypted_token not in serialized
    assert "access_token" not in serialized
    assert "No Meta data has been imported into Sellora" in serialized
