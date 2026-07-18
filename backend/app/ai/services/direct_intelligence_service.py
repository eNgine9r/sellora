from datetime import UTC, datetime
from uuid import UUID
from app.ai.exceptions import AIError
from app.ai.prompts.registry import get_prompt
from app.ai.schemas.provider import AIProviderRequest
from app.ai.schemas.structured_output import DirectMessageAnalysisOutput
from app.ai.services.ai_gateway_service import AIGatewayService
from app.ai.services.context_builder_service import AIContextBuilderService
from app.ai.services.usage_service import AIUsageService
from app.core.config import get_settings
from app.models.ai_direct import AIAnalysis, AIAnalysisStatus, AISuggestion, AISuggestionStatus, AISuggestionType, DirectAIProcessingStatus
from app.repositories.ai_direct_repository import AIRepository, DirectConversationRepository, DirectMessageRepository

class DirectIntelligenceService:
    def __init__(self, ai_repo: AIRepository, conversations: DirectConversationRepository, messages: DirectMessageRepository, gateway: AIGatewayService | None = None) -> None:
        self.ai_repo=ai_repo; self.conversations=conversations; self.messages=messages; self.gateway=gateway or AIGatewayService()
    async def analyze(self, workspace_id: UUID, conversation_id: UUID, user_id: UUID | None) -> AIAnalysis:
        settings_obj = get_settings(); settings = self.ai_repo.get_or_create_settings(workspace_id)
        conversation = self.conversations.get(workspace_id, conversation_id)
        if not conversation: raise AIError('Direct conversation not found', 'DIRECT_CONVERSATION_NOT_FOUND')
        source = self.messages.latest_analyzable(workspace_id, conversation_id)
        if not source: raise AIError('Direct message not found', 'DIRECT_MESSAGE_NOT_FOUND')
        context = AIContextBuilderService(self.messages).build(workspace_id, conversation_id, settings.max_context_messages, settings.max_input_characters)
        AIUsageService(self.ai_repo).preflight(settings, context['input_characters'], settings_obj.ai_feature_enabled)
        prompt = get_prompt('DIRECT_MESSAGE_ANALYSIS')
        now=datetime.now(UTC)
        analysis = self.ai_repo.create_analysis(AIAnalysis(workspace_id=workspace_id, conversation_id=conversation_id, source_message_id=source.id, provider=settings_obj.ai_provider, model=settings_obj.ai_fast_model, prompt_key=prompt.prompt_key, prompt_version=prompt.prompt_version, status=AIAnalysisStatus.PROCESSING.value, structured_result={}, started_at=now, created_at=now, created_by=user_id))
        try:
            result = await self.gateway.generate_structured_response(AIProviderRequest(prompt_key=prompt.prompt_key, prompt_version=prompt.prompt_version, model=settings_obj.ai_fast_model, system_prompt=prompt.system_prompt, user_payload=context, output_schema=prompt.output_schema, timeout_seconds=settings_obj.ai_request_timeout_seconds))
            structured = DirectMessageAnalysisOutput.model_validate(result.structured_output)
            analysis.status=AIAnalysisStatus.COMPLETED.value; analysis.structured_result=structured.model_dump(mode='json')
            analysis.detected_language=structured.language; analysis.detected_intent=structured.intent.value; analysis.intent_confidence=structured.intent_confidence; analysis.sentiment=structured.sentiment.value; analysis.sentiment_confidence=structured.sentiment_confidence; analysis.urgency=structured.urgency.value; analysis.requires_human=True; analysis.clarification_required=structured.clarification_required; analysis.provider_request_id=result.provider_request_id; analysis.input_tokens=result.input_tokens; analysis.output_tokens=result.output_tokens; analysis.total_tokens=result.total_tokens; analysis.estimated_cost_usd=result.estimated_cost_usd; analysis.latency_ms=result.latency_ms; analysis.completed_at=datetime.now(UTC)
            conversation.ai_processing_status=DirectAIProcessingStatus.REVIEW_REQUIRED.value; conversation.latest_ai_analysis_id=analysis.id
            if structured.suggested_reply:
                self.ai_repo.create_suggestion(AISuggestion(workspace_id=workspace_id, conversation_id=conversation_id, analysis_id=analysis.id, suggestion_type=AISuggestionType.REPLY_DRAFT.value, status=AISuggestionStatus.REVIEW_REQUIRED.value, title='Чернетка відповіді AI', summary=structured.summary, draft_text=structured.suggested_reply, structured_payload=structured.model_dump(mode='json'), confidence=structured.intent_confidence))
            AIUsageService(self.ai_repo).record(workspace_id,result.provider,result.model,'DIRECT_MESSAGE_ANALYSIS','COMPLETED',user_id,conversation_id,analysis.id,result.input_tokens,result.output_tokens,result.estimated_cost_usd,result.latency_ms)
        except Exception as exc:
            code = getattr(exc, 'safe_code', 'AI_INVALID_STRUCTURED_OUTPUT')
            analysis.status=AIAnalysisStatus.FAILED_SAFE.value; analysis.safe_error_code=code; analysis.safe_error_message='AI analysis failed safely'; analysis.completed_at=datetime.now(UTC); conversation.ai_processing_status=DirectAIProcessingStatus.FAILED.value
            AIUsageService(self.ai_repo).record(workspace_id,settings_obj.ai_provider,settings_obj.ai_fast_model,'DIRECT_MESSAGE_ANALYSIS',code,user_id,conversation_id,analysis.id)
        return analysis
