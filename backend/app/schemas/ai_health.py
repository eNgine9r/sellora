from pydantic import BaseModel


class AIHealthResponse(BaseModel):
    feature_configured: bool
    provider_selected: str
    credential_present: bool
    ai_enabled: bool
    safe_configuration_status: str
