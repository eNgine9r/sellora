from app.ai.providers.base import AIProvider
from app.ai.providers.openai_provider import OpenAIProvider
from app.core.config import get_settings

def get_ai_provider() -> AIProvider:
    settings = get_settings()
    provider = (settings.ai_provider or "openai").lower()
    if provider == "openai":
        return OpenAIProvider(settings.ai_api_key)
    return OpenAIProvider(settings.ai_api_key)
