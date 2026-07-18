from typing import Protocol
from app.ai.schemas.provider import AIProviderRequest, AIProviderResult

class AIProvider(Protocol):
    name: str
    async def generate_structured_response(self, request: AIProviderRequest) -> AIProviderResult: ...
