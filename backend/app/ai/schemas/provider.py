from typing import Any
from pydantic import BaseModel, Field

class AIProviderRequest(BaseModel):
    prompt_key: str
    prompt_version: str
    model: str
    system_prompt: str
    user_payload: dict[str, Any]
    output_schema: dict[str, Any]
    timeout_seconds: float = 30

class AIProviderResult(BaseModel):
    provider: str
    model: str
    structured_output: dict[str, Any]
    provider_request_id: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0
    latency_ms: int | None = None
    raw_status: str = Field(default="completed")
