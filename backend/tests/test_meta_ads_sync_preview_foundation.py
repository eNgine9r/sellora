from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

from app.core.config import Settings
from app.integrations.meta_ads.read_only_client import FakeMetaAdsReadOnlyClient
from app.models.meta_ad_connection import MetaAdConnection, MetaAdConnectionStatus
from app.services.meta_ads_sync_preview_service import MetaAdsSyncPreviewService


class WriteTrapDb:
    def commit(self) -> None:
        raise AssertionError("sync preview must not commit")

    def flush(self) -> None:
        raise AssertionError("sync preview must not flush")


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


def _connection(workspace_id: UUID, status: MetaAdConnectionStatus = MetaAdConnectionStatus.CONNECTED) -> MetaAdConnection:
    return MetaAdConnection(
        workspace_id=workspace_id,
        provider="meta_ads",
        connection_status=status.value,
        encrypted_access_token="encrypted-synthetic-token" if status == MetaAdConnectionStatus.CONNECTED else None,
    )


def test_preview_returns_not_ready_when_connection_missing_or_token_missing() -> None:
    workspace_id = uuid4()
    missing_connection = MetaAdsSyncPreviewService(
        WriteTrapDb(),
        settings=_settings(meta_connections_enabled=True, meta_sync_preview_enabled=True),
        connection_repository=FakeConnectionRepository(),
    )
    missing_token = _connection(workspace_id)
    missing_token.encrypted_access_token = None
    missing_token_service = MetaAdsSyncPreviewService(
        WriteTrapDb(),
        settings=_settings(meta_connections_enabled=True, meta_sync_preview_enabled=True),
        connection_repository=FakeConnectionRepository(missing_token),
    )

    assert missing_connection.preview_insights(workspace_id, date(2026, 7, 1), date(2026, 7, 1)).reason == "connection_not_ready"
    assert missing_token_service.preview_insights(workspace_id, date(2026, 7, 1), date(2026, 7, 1)).reason == "token_missing"


def test_sync_preview_returns_safe_insights_without_raw_ids_or_db_writes() -> None:
    workspace_id = uuid4()
    service = MetaAdsSyncPreviewService(
        WriteTrapDb(),
        settings=_settings(meta_connections_enabled=True, meta_sync_preview_enabled=True),
        connection_repository=FakeConnectionRepository(_connection(workspace_id)),
        client=FakeMetaAdsReadOnlyClient(),
    )

    response = service.preview_insights(workspace_id, date(2026, 7, 1), date(2026, 7, 2))

    assert response.ready is True
    assert response.db_writes is False
    assert response.sync_active is False
    assert response.apply_available is False
    assert len(response.insights) == 4
    assert "fake_campaign_001" not in response.model_dump_json()
    assert "access_token" not in response.model_dump_json()
    assert all(item.warnings for item in response.insights)


def test_preview_blocks_when_production_sync_gate_is_enabled() -> None:
    workspace_id = uuid4()
    service = MetaAdsSyncPreviewService(
        WriteTrapDb(),
        settings=_settings(meta_connections_enabled=True, meta_sync_preview_enabled=True, meta_sync_enabled=True),
        connection_repository=FakeConnectionRepository(_connection(workspace_id)),
    )

    response = service.preview_insights(workspace_id, date(2026, 7, 1), date(2026, 7, 1))

    assert response.ready is False
    assert response.reason == "sync_must_remain_disabled"


def test_invalid_date_range_returns_safe_response() -> None:
    workspace_id = uuid4()
    service = MetaAdsSyncPreviewService(
        WriteTrapDb(),
        settings=_settings(meta_connections_enabled=True, meta_sync_preview_enabled=True),
        connection_repository=FakeConnectionRepository(_connection(workspace_id)),
    )

    response = service.preview_insights(workspace_id, date(2026, 7, 2), date(2026, 7, 1))

    assert response.ready is False
    assert response.reason == "invalid_date_range"
