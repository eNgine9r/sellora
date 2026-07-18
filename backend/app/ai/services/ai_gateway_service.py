from app.ai.exceptions import AIError
from app.ai.providers.provider_factory import get_ai_provider
from app.ai.schemas.provider import AIProviderRequest, AIProviderResult

class AIGatewayService:
    async def generate_structured_response(self, request: AIProviderRequest) -> AIProviderResult:
        provider = get_ai_provider()
        try:
            return await provider.generate_structured_response(request)
        except AIError:
            raise
        except TimeoutError as exc:
            raise AIError("AI provider timeout", "AI_REQUEST_TIMEOUT") from exc
        except Exception as exc:
            raise AIError("AI provider unavailable", "AI_PROVIDER_UNAVAILABLE") from exc
