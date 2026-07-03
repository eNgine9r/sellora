from __future__ import annotations

from pathlib import Path

from app.models.ad_campaign import AdCampaign
from app.models.ad_metric import AdMetric

MIGRATION_PATH = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "202607010016_meta_ads_external_identity_fields.py"
MIGRATION_TEXT = MIGRATION_PATH.read_text()

CAMPAIGN_FIELDS = [
    "external_source",
    "external_account_id",
    "external_campaign_id",
    "external_status",
    "external_objective",
    "last_synced_at",
    "sync_source",
]
METRIC_FIELDS = [
    "source_type",
    "external_source",
    "external_account_id",
    "external_campaign_id",
    "last_synced_at",
    "sync_run_id",
]


def test_meta_ads_external_identity_migration_file_exists_and_is_nullable_first() -> None:
    assert MIGRATION_PATH.exists()
    assert 'revision: str = "202607010016"' in MIGRATION_TEXT
    assert 'down_revision: str | None = "202607010015"' in MIGRATION_TEXT

    for field in [*CAMPAIGN_FIELDS, *METRIC_FIELDS]:
        assert f'"{field}"' in MIGRATION_TEXT
    assert MIGRATION_TEXT.count("nullable=True") >= len(CAMPAIGN_FIELDS) + len(METRIC_FIELDS)
    assert "nullable=False" not in MIGRATION_TEXT
    assert "server_default" not in MIGRATION_TEXT


def test_meta_ads_external_identity_migration_indexes_and_downgrade_are_safe() -> None:
    assert "ix_ad_campaigns_workspace_external_identity" in MIGRATION_TEXT
    assert "ix_ad_metrics_workspace_external_identity_date" in MIGRATION_TEXT
    assert '["workspace_id", "external_source", "external_account_id", "external_campaign_id"]' in MIGRATION_TEXT
    assert '["workspace_id", "external_source", "external_account_id", "external_campaign_id", "metric_date"]' in MIGRATION_TEXT
    assert "unique=False" in MIGRATION_TEXT

    for field in [*CAMPAIGN_FIELDS, *METRIC_FIELDS]:
        assert f'op.drop_column("ad_' in MIGRATION_TEXT and f'"{field}"' in MIGRATION_TEXT
    assert "op.drop_index" in MIGRATION_TEXT


def test_meta_ads_external_identity_migration_does_not_add_forbidden_scope() -> None:
    forbidden_markers = [
        "meta_ad_connections",
        "token_encrypted_ref",
        "access_token",
        "refresh_token",
        "oauth",
        "scheduled_job",
        "GOOD",
        "WATCH",
        "PROBLEM",
        "NO_DATA",
    ]
    for marker in forbidden_markers:
        assert marker not in MIGRATION_TEXT


def test_models_expose_nullable_external_identity_fields() -> None:
    for field in CAMPAIGN_FIELDS:
        column = AdCampaign.__table__.c[field]
        assert column.nullable is True

    for field in METRIC_FIELDS:
        column = AdMetric.__table__.c[field]
        assert column.nullable is True

    assert AdCampaign.__table__.c.external_source.type.length == 50
    assert AdCampaign.__table__.c.external_account_id.type.length == 128
    assert AdCampaign.__table__.c.external_campaign_id.type.length == 128
    assert AdMetric.__table__.c.source_type.type.length == 32
    assert AdMetric.__table__.c.external_source.type.length == 50
    assert AdMetric.__table__.c.external_account_id.type.length == 128
    assert AdMetric.__table__.c.external_campaign_id.type.length == 128
