from pathlib import Path

from app.models.ai_direct import AIWorkspaceSettings


def test_ai_workspace_settings_columns_exist_in_migration_schema():
    migration = Path("alembic/versions/202607180027_ai_direct_intelligence.py").read_text()
    missing = [column.name for column in AIWorkspaceSettings.__table__.columns if f"'{column.name}'" not in migration and f'"{column.name}"' not in migration]
    assert not missing
