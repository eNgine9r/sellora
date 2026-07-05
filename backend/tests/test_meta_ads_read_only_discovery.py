from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.meta_ads import router
from app.core.config import Settings
from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.rbac import get_workspace_id
from app.integrations.meta_ads.read_only_client import FakeMetaAdsReadOnlyClient
from app.models.meta_ad_connection import MetaAdConnection, MetaAdConnectionStatus
from app.models.role import RoleName
from app.services.meta_ads_sync_preview_service import MetaAdsSyncPreviewService


class WriteTrapDb:
    def commit(self) -> None:
        raise AssertionError("read-only discovery must not commit")

    def flush(self) -> None:
        raise AssertionError("read-only discovery must not flush")


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
        "meta_sync_preview_enabled": False,
        "meta_sync_enabled": False,
    }
    data.update(overrides)
    return Settings(_env_file=None, **data)


def _connected(workspace_id: UUID) -> MetaAdConnection:
    return MetaAdConnection(
        workspace_id=workspace_id,
        provider="meta_ads",
        connection_status=MetaAdConnectionStatus.CONNECTED.value,
        encrypted_access_token="encrypted-synthetic-token",
    )


def _user(workspace_id, role: RoleName):
    return SimpleNamespace(
        id=uuid4(),
        workspaces=[SimpleNamespace(workspace_id=workspace_id, workspace=SimpleNamespace(is_active=True), role=SimpleNamespace(name=role.value))],
    )


def _client(role: RoleName = RoleName.ANALYST):
    workspace_id = uuid4()
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    user = _user(workspace_id, role)
    app.dependency_overrides[get_workspace_id] = lambda: workspace_id
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: WriteTrapDb()
    return TestClient(app), workspace_id, user


def test_discovery_routes_return_safe_disabled_response_by_default(monkeypatch) -> None:
    client, workspace_id, _ = _client()

    class FakeService:
        def __init__(self, db):
            self.service = MetaAdsSyncPreviewService(db, settings=_settings(), connection_repository=FakeConnectionRepository())

        def discover_accounts(self, workspace_id_arg):
            assert workspace_id_arg == workspace_id
            return self.service.discover_accounts(workspace_id_arg)

        def discover_campaigns(self, workspace_id_arg, account_id=None):
            return self.service.discover_campaigns(workspace_id_arg, account_id)

        def preview_insights(self, workspace_id_arg, date_from, date_to, account_id=None):
            return self.service.preview_insights(workspace_id_arg, date_from, date_to, account_id)

    monkeypatch.setattr("app.api.v1.meta_ads.MetaAdsSyncPreviewService", FakeService)

    accounts = client.get("/api/v1/integrations/meta-ads/discovery/accounts")
    campaigns = client.get("/api/v1/integrations/meta-ads/discovery/campaigns")
    preview = client.get("/api/v1/integrations/meta-ads/sync/preview?date_from=2026-07-01&date_to=2026-07-02")

    for response in (accounts, campaigns, preview):
        assert response.status_code == 200
        payload = response.json()
        assert payload["ready"] is False
        assert payload["reason"] == "feature_disabled"
        assert payload["db_writes"] is False
        assert payload["sync_active"] is False
        assert "access_token" not in str(payload)
        assert "encrypted_access_token" not in str(payload)


def test_fake_read_only_client_is_deterministic_and_has_no_write_methods() -> None:
    client = FakeMetaAdsReadOnlyClient()

    accounts = client.list_ad_accounts()
    campaigns = client.list_campaigns(accounts[0].external_account_id)
    insights = client.get_campaign_insights_preview(accounts[0].external_account_id, date(2026, 7, 1), date(2026, 7, 1))

    assert accounts[0].external_account_id == "fake_act_001"
    assert [campaign.external_campaign_id for campaign in campaigns] == ["fake_campaign_001", "fake_campaign_002", "fake_campaign_003"]
    assert len(insights) == 2
    assert not hasattr(client, "create_campaign")
    assert not hasattr(client, "update_campaign")


def test_account_and_campaign_discovery_masks_external_ids_and_does_not_write() -> None:
    workspace_id = uuid4()
    service = MetaAdsSyncPreviewService(
        WriteTrapDb(),
        settings=_settings(meta_connections_enabled=True, meta_sync_preview_enabled=True),
        connection_repository=FakeConnectionRepository(_connected(workspace_id)),
        client=FakeMetaAdsReadOnlyClient(),
    )

    accounts = service.discover_accounts(workspace_id)
    campaigns = service.discover_campaigns(workspace_id)

    assert accounts.ready is True
    assert accounts.accounts[0].external_account_id_masked != "fake_act_001"
    assert "fake_act_001" not in accounts.model_dump_json()
    assert campaigns.ready is True
    assert "fake_campaign_001" not in campaigns.model_dump_json()
    assert all(item.warnings for item in campaigns.campaigns)
