from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.models.meta_ad_connection import MetaAdConnectionStatus
from app.schemas.meta_ads_connection import MetaAdsConnectionStatusResponse


def test_meta_feature_gates_are_disabled_by_default_and_optional() -> None:
    settings = Settings(_env_file=None)

    assert settings.meta_live_oauth_enabled is False
    assert settings.meta_connections_enabled is False
    assert settings.meta_token_storage_enabled is False
    assert settings.meta_sync_enabled is False
    assert settings.meta_app_id is None
    assert settings.meta_app_secret is None
    assert settings.meta_oauth_redirect_uri is None
    assert settings.meta_token_encryption_key is None


def test_connection_status_contract_is_english_and_safe() -> None:
    assert [status.value for status in MetaAdConnectionStatus] == [
        "NOT_CONNECTED",
        "MOCK_ONLY",
        "CONNECTING",
        "CONNECTED",
        "NEEDS_REAUTH",
        "PERMISSION_MISSING",
        "TOKEN_EXPIRED",
        "DISCONNECTED",
        "ERROR",
    ]
    forbidden_response_fields = {"encrypted_access_token", "access_token", "refresh_token"}
    assert forbidden_response_fields.isdisjoint(MetaAdsConnectionStatusResponse.model_fields)


def test_meta_ad_connections_migration_has_no_raw_token_or_global_account_assumption() -> None:
    migration = Path("alembic/versions/202607030018_meta_ad_connections.py").read_text()

    assert "meta_ad_connections" in migration
    assert 'sa.Column("encrypted_access_token"' in migration
    assert 'sa.Column("access_token"' not in migration
    assert "refresh_token" not in migration
    assert "ix_meta_ad_connections_workspace_id" in migration
    assert "ix_meta_ad_connections_workspace_status" in migration
    assert "unique=True" not in migration
