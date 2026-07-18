from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field

class SyntheticConversationCreate(BaseModel):
    participant_display_name: str = Field(min_length=1, max_length=255)
    participant_username: str | None = Field(default=None, max_length=160)
    initial_message: str = Field(min_length=1, max_length=4000)
    language: str = Field(default='uk', max_length=12)
    scenario_tag: str | None = Field(default=None, max_length=80)

class DirectMessageCreate(BaseModel):
    text: str = Field(min_length=1, max_length=4000)

class DirectConversationResponse(BaseModel):
    id: UUID; workspace_id: UUID; channel: str; participant_username: str | None; participant_display_name: str | None; status: str; priority: str; unread_count: int; ai_processing_status: str; last_message_at: datetime | None; created_at: datetime; updated_at: datetime
    model_config = {'from_attributes': True}

class DirectMessageResponse(BaseModel):
    id: UUID; workspace_id: UUID; conversation_id: UUID; direction: str; sender_type: str; message_type: str; text: str | None; safe_text_hash: str | None; received_at: datetime; processing_status: str; is_synthetic: bool
    model_config = {'from_attributes': True}

class AIAnalysisResponse(BaseModel):
    id: UUID; workspace_id: UUID; conversation_id: UUID; source_message_id: UUID; provider: str; model: str; prompt_key: str; prompt_version: str; status: str; detected_language: str | None; detected_intent: str | None; intent_confidence: float | None; sentiment: str | None; urgency: str | None; requires_human: bool; clarification_required: bool; structured_result: dict[str, Any]; safe_error_code: str | None; safe_error_message: str | None; input_tokens: int | None; output_tokens: int | None; total_tokens: int | None; estimated_cost_usd: float | None; latency_ms: int | None; created_at: datetime
    model_config = {'from_attributes': True}

class AISuggestionResponse(BaseModel):
    id: UUID; workspace_id: UUID; conversation_id: UUID; analysis_id: UUID; suggestion_type: str; status: str; title: str; summary: str | None; draft_text: str | None; structured_payload: dict[str, Any] | None; confidence: float | None; reviewed_at: datetime | None; rejection_reason: str | None
    model_config = {'from_attributes': True}

class AISuggestionPatch(BaseModel):
    draft_text: str | None = Field(default=None, max_length=2000)
    structured_payload: dict[str, Any] | None = None

class RejectRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)

class AISettingsResponse(BaseModel):
    workspace_id: UUID; enabled: bool; synthetic_inbox_enabled: bool; direct_intelligence_enabled: bool; auto_analysis_enabled: bool; reply_suggestions_enabled: bool; action_drafts_enabled: bool; daily_request_limit: int; daily_token_limit: int; monthly_budget_usd: float; max_context_messages: int; max_input_characters: int; minimum_action_confidence: float; minimum_product_match_confidence: float
    model_config = {'from_attributes': True}

class AISettingsUpdate(BaseModel):
    enabled: bool | None = None; direct_intelligence_enabled: bool | None = None; daily_request_limit: int | None = Field(default=None, ge=1, le=10000); daily_token_limit: int | None = Field(default=None, ge=1, le=5000000); monthly_budget_usd: float | None = Field(default=None, ge=0, le=10000); max_context_messages: int | None = Field(default=None, ge=1, le=50); max_input_characters: int | None = Field(default=None, ge=100, le=50000)

class AIHealthResponse(BaseModel):
    feature_configured: bool; provider_selected: str; credential_present: bool; ai_enabled: bool; safe_configuration_status: str
