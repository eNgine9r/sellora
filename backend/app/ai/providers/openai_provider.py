import asyncio, time, uuid
from app.ai.exceptions import AIError
from app.ai.providers.base import AIProvider
from app.ai.schemas.provider import AIProviderRequest, AIProviderResult

class OpenAIProvider(AIProvider):
    name = "openai"
    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key
    async def generate_structured_response(self, request: AIProviderRequest) -> AIProviderResult:
        if not self.api_key:
            raise AIError("AI provider credential is not configured", "AI_PROVIDER_NOT_CONFIGURED")
        started = time.perf_counter()
        await asyncio.sleep(0)
        raise AIError("Live OpenAI calls are intentionally disabled in default Sprint 9 implementation", "AI_PROVIDER_UNAVAILABLE")
