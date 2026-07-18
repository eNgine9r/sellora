from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role, require_roles
from app.models.role import RoleName
from app.models.user import User
from app.repositories.ai_direct_repository import AIRepository
from app.schemas.ai_direct import AIAnalysisResponse, AISuggestionResponse, AISuggestionPatch, RejectRequest, AISettingsResponse, AISettingsUpdate, AIHealthResponse
from app.ai.services.ai_action_service import AIActionService
from app.ai.exceptions import AIError

router=APIRouter(prefix='/ai', tags=['ai'])

@router.get('/health', response_model=AIHealthResponse)
def health(workspace_id: UUID=Depends(get_workspace_id), _: User=Depends(require_min_role(RoleName.ANALYST)), db: Session=Depends(get_db)):
    settings=get_settings(); ws=AIRepository(db).get_or_create_settings(workspace_id)
    return AIHealthResponse(feature_configured=settings.ai_feature_enabled, provider_selected=settings.ai_provider, credential_present=bool(settings.ai_api_key), ai_enabled=ws.enabled, safe_configuration_status='CONFIGURED' if settings.ai_feature_enabled and settings.ai_api_key else 'DISABLED_OR_MISSING_CREDENTIAL')

@router.get('/settings', response_model=AISettingsResponse)
def get_ai_settings(workspace_id: UUID=Depends(get_workspace_id), _: User=Depends(require_min_role(RoleName.ANALYST)), db: Session=Depends(get_db)):
    return AIRepository(db).get_or_create_settings(workspace_id)

@router.patch('/settings', response_model=AISettingsResponse)
def update_ai_settings(payload: AISettingsUpdate, workspace_id: UUID=Depends(get_workspace_id), user: User=Depends(require_roles(RoleName.OWNER)), db: Session=Depends(get_db)):
    settings=AIRepository(db).get_or_create_settings(workspace_id)
    for field, value in payload.model_dump(exclude_unset=True).items(): setattr(settings, field, value)
    settings.updated_by=user.id; db.commit(); db.refresh(settings); return settings

@router.get('/analyses/{analysis_id}', response_model=AIAnalysisResponse)
def get_analysis(analysis_id: UUID, workspace_id: UUID=Depends(get_workspace_id), _: User=Depends(require_min_role(RoleName.ANALYST)), db: Session=Depends(get_db)):
    item=AIRepository(db).get_analysis(workspace_id, analysis_id)
    if not item: raise HTTPException(404, 'AI_ANALYSIS_NOT_FOUND')
    return item

@router.get('/suggestions/{suggestion_id}', response_model=AISuggestionResponse)
def get_suggestion(suggestion_id: UUID, workspace_id: UUID=Depends(get_workspace_id), _: User=Depends(require_min_role(RoleName.ANALYST)), db: Session=Depends(get_db)):
    item=AIRepository(db).get_suggestion(workspace_id, suggestion_id)
    if not item: raise HTTPException(404, 'AI_SUGGESTION_NOT_FOUND')
    return item

@router.patch('/suggestions/{suggestion_id}', response_model=AISuggestionResponse)
def patch_suggestion(suggestion_id: UUID, payload: AISuggestionPatch, workspace_id: UUID=Depends(get_workspace_id), _: User=Depends(require_min_role(RoleName.MANAGER)), db: Session=Depends(get_db)):
    item=AIRepository(db).get_suggestion(workspace_id, suggestion_id)
    if not item: raise HTTPException(404, 'AI_SUGGESTION_NOT_FOUND')
    if payload.draft_text is not None: item.draft_text=payload.draft_text
    if payload.structured_payload is not None: item.structured_payload=payload.structured_payload
    db.commit(); db.refresh(item); return item

@router.post('/suggestions/{suggestion_id}/approve', response_model=AISuggestionResponse)
def approve_suggestion(suggestion_id: UUID, workspace_id: UUID=Depends(get_workspace_id), user: User=Depends(require_min_role(RoleName.MANAGER)), db: Session=Depends(get_db)):
    try: item=AIActionService(AIRepository(db)).approve_suggestion(workspace_id, suggestion_id, user.id)
    except AIError as exc: raise HTTPException(404, exc.safe_code) from exc
    db.commit(); db.refresh(item); return item

@router.post('/suggestions/{suggestion_id}/reject', response_model=AISuggestionResponse)
def reject_suggestion(suggestion_id: UUID, payload: RejectRequest, workspace_id: UUID=Depends(get_workspace_id), user: User=Depends(require_min_role(RoleName.MANAGER)), db: Session=Depends(get_db)):
    try: item=AIActionService(AIRepository(db)).reject_suggestion(workspace_id, suggestion_id, user.id, payload.reason)
    except AIError as exc: raise HTTPException(404, exc.safe_code) from exc
    db.commit(); db.refresh(item); return item

@router.get('/usage/events')
def usage_events(workspace_id: UUID=Depends(get_workspace_id), _: User=Depends(require_min_role(RoleName.ANALYST)), db: Session=Depends(get_db)):
    return AIRepository(db).usage_events(workspace_id)

@router.get('/usage/summary')
def usage_summary(workspace_id: UUID=Depends(get_workspace_id), _: User=Depends(require_min_role(RoleName.ANALYST)), db: Session=Depends(get_db)):
    events=AIRepository(db).usage_events(workspace_id)
    return {'requests_today': len(events), 'tokens_today': sum(e.total_tokens for e in events), 'estimated_cost_today': float(sum(e.estimated_cost_usd for e in events)), 'estimated_cost_month': float(sum(e.estimated_cost_usd for e in events)), 'average_latency_ms': None}

@router.post('/action-drafts/{action_draft_id}/apply')
def apply_action(action_draft_id: UUID, idempotency_key: str | None=Header(default=None, alias='Idempotency-Key'), workspace_id: UUID=Depends(get_workspace_id), _: User=Depends(require_min_role(RoleName.MANAGER)), db: Session=Depends(get_db)):
    if not idempotency_key: raise HTTPException(400, 'AI_IDEMPOTENCY_KEY_REUSED')
    try: item=AIActionService(AIRepository(db)).apply_action(workspace_id, action_draft_id, idempotency_key)
    except AIError as exc: raise HTTPException(400, exc.safe_code) from exc
    db.commit(); return {'id': item.id, 'status': item.status, 'result_entity_type': item.result_entity_type, 'result_entity_id': item.result_entity_id}
