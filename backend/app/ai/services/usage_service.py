from datetime import UTC, datetime
from uuid import UUID
from app.ai.exceptions import AIError
from app.models.ai_direct import AIUsageEvent, AIWorkspaceSettings
from app.repositories.ai_direct_repository import AIRepository

class AIUsageService:
    def __init__(self, repo: AIRepository) -> None: self.repo = repo
    def preflight(self, settings: AIWorkspaceSettings, input_characters: int, platform_enabled: bool) -> None:
        if not platform_enabled: raise AIError("AI feature disabled", "AI_FEATURE_DISABLED")
        if not settings.enabled or not settings.direct_intelligence_enabled: raise AIError("Workspace AI disabled", "AI_FEATURE_DISABLED")
        if input_characters > settings.max_input_characters: raise AIError("AI input too large", "AI_INPUT_TOO_LARGE")
        if settings.daily_request_limit <= 0 or settings.daily_token_limit <= 0 or float(settings.monthly_budget_usd) < 0: raise AIError("Unsafe AI limits", "AI_DAILY_LIMIT_EXCEEDED")
    def record(self, workspace_id: UUID, provider: str, model: str, request_type: str, status: str, user_id: UUID | None = None, conversation_id: UUID | None = None, analysis_id: UUID | None = None, input_tokens: int = 0, output_tokens: int = 0, estimated_cost_usd: float = 0, latency_ms: int | None = None) -> AIUsageEvent:
        return self.repo.record_usage(AIUsageEvent(workspace_id=workspace_id,user_id=user_id,conversation_id=conversation_id,analysis_id=analysis_id,provider=provider,model=model,request_type=request_type,status=status,input_tokens=input_tokens,output_tokens=output_tokens,total_tokens=input_tokens+output_tokens,estimated_cost_usd=estimated_cost_usd,latency_ms=latency_ms,created_at=datetime.now(UTC)))
