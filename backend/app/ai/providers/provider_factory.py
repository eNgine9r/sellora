from app.ai.providers.base import AIProvider
from app.ai.providers.openai_provider import OpenAIProvider
from app.core.config import get_settings


def get_ai_provider() -> AIProvider:
    settings = get_settings()
    provider = (settings.ai_provider or "openai").lower()
    if provider == "openai":
        return OpenAIProvider(
            settings.ai_api_key,
            base_url=settings.ai_api_base_url,
            max_retries=settings.ai_max_retries,
        )
    return OpenAIProvider(
        settings.ai_api_key,
        base_url=settings.ai_api_base_url,
        max_retries=settings.ai_max_retries,
    )
