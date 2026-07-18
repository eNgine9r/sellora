from pydantic import BaseModel
from app.core.config import get_settings

REQUIRED_BASIC_PERMISSION = "instagram_business_basic"
REQUIRED_MESSAGING_PERMISSION = "instagram_business_manage_messages"
OAUTH_REQUIRED_SCOPES = [REQUIRED_BASIC_PERMISSION, REQUIRED_MESSAGING_PERMISSION]
WEBHOOK_SUBSCRIPTIONS = ["messages", "messaging_postbacks"]
PROFESSIONAL_ACCOUNT_TYPES = {"BUSINESS", "CREATOR"}

class MetaInstagramConfig(BaseModel):
    app_id: str | None
    app_secret_configured: bool
    graph_api_version: str
    graph_api_base_url: str
    oauth_redirect_uri: str | None
    send_enabled: bool
    webhook_processing_enabled: bool
    auto_analysis_enabled: bool
    auto_send_enabled: bool
    human_agent_enabled: bool
    webhook_max_body_bytes: int


def get_meta_instagram_config() -> MetaInstagramConfig:
    s = get_settings()
    return MetaInstagramConfig(
        app_id=s.meta_app_id,
        app_secret_configured=bool(s.meta_app_secret),
        graph_api_version=s.meta_graph_api_version,
        graph_api_base_url=s.meta_graph_api_base_url.rstrip("/"),
        oauth_redirect_uri=s.meta_oauth_redirect_uri,
        send_enabled=s.meta_instagram_send_enabled,
        webhook_processing_enabled=s.meta_instagram_webhook_processing_enabled,
        auto_analysis_enabled=s.meta_instagram_auto_analysis_enabled,
        auto_send_enabled=s.meta_instagram_auto_send_enabled,
        human_agent_enabled=s.meta_human_agent_enabled,
        webhook_max_body_bytes=s.meta_webhook_max_body_bytes,
    )
