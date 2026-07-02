from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sellora"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    database_url: str = Field(default="postgresql+psycopg://sellora:sellora@postgres:5432/sellora", alias="DATABASE_URL")
    secret_key: str = Field(default="change-me", alias="SECRET_KEY")
    jwt_secret: str = Field(default="change-me-too", alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = Field(default=30, alias="JWT_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    import_storage_path: str = Field(default="storage/imports", alias="IMPORT_STORAGE_PATH")
    import_max_file_size_mb: int = Field(default=20, alias="IMPORT_MAX_FILE_SIZE_MB")
    nova_poshta_api_url: str = Field(default="https://api.novaposhta.ua/v2.0/json/", alias="NOVA_POSHTA_API_URL")
    meta_ads_mock_oauth_api_enabled: bool = Field(default=False, alias="META_ADS_MOCK_OAUTH_API_ENABLED")

    initial_admin_email: str = Field(default="admin@sellora.local", alias="INITIAL_ADMIN_EMAIL")
    initial_admin_password: str = Field(default="ChangeMe123!", alias="INITIAL_ADMIN_PASSWORD")
    initial_admin_first_name: str = Field(default="Sellora", alias="INITIAL_ADMIN_FIRST_NAME")
    initial_admin_last_name: str = Field(default="Admin", alias="INITIAL_ADMIN_LAST_NAME")
    initial_workspace_name: str = Field(default="Sellora Workspace", alias="INITIAL_WORKSPACE_NAME")
    initial_workspace_slug: str = Field(default="sellora", alias="INITIAL_WORKSPACE_SLUG")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", populate_by_name=True, extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
