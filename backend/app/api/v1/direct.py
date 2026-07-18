from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role, require_roles
from app.models.role import RoleName
from app.models.user import User
from app.repositories.ai_direct_repository import AIRepository, DirectConversationRepository, DirectMessageRepository
from app.schemas.ai_direct import SyntheticConversationCreate, DirectConversationResponse, DirectMessageCreate, DirectMessageResponse, AIAnalysisResponse, AISuggestionResponse
from app.ai.services.direct_conversation_service import DirectConversationService
from app.ai.services.direct_intelligence_service import DirectIntelligenceService
from app.ai.exceptions import AIError
from app.integrations.meta_instagram.exceptions import MetaInstagramError
from app.integrations.meta_instagram.schemas import MessageOperationResponse, ReplyPrepareRequest, ReplyPrepareResponse, ReplySendRequest, ReplySendResponse
from app.integrations.meta_instagram.services.outbound_message_service import InstagramOutboundMessageService
from app.integrations.meta_instagram.services.reconciliation_service import InstagramReconciliationService

router=APIRouter(prefix='/direct', tags=['direct-intelligence'])

def deps(db: Session):
    return DirectConversationRepository(db), DirectMessageRepository(db), AIRepository(db)

@router.get('/conversations', response_model=list[DirectConversationResponse])
def list_conversations(workspace_id: UUID=Depends(get_workspace_id), _: User=Depends(require_min_role(RoleName.ANALYST)), db: Session=Depends(get_db)):
    return DirectConversationRepository(db).list(workspace_id)

@router.post('/conversations', response_model=DirectConversationResponse)
def create_conversation(payload: SyntheticConversationCreate, workspace_id: UUID=Depends(get_workspace_id), user: User=Depends(require_min_role(RoleName.MANAGER)), db: Session=Depends(get_db)):
    service=DirectConversationService(DirectConversationRepository(db), DirectMessageRepository(db)); c=service.create_synthetic(workspace_id,user.id,payload.participant_display_name,payload.participant_username,payload.initial_message); db.commit(); db.refresh(c); return c

@router.get('/conversations/{conversation_id}', response_model=DirectConversationResponse)
def get_conversation(conversation_id: UUID, workspace_id: UUID=Depends(get_workspace_id), _: User=Depends(require_min_role(RoleName.ANALYST)), db: Session=Depends(get_db)):
    c=DirectConversationRepository(db).get(workspace_id, conversation_id)
    if not c: raise HTTPException(404, 'DIRECT_CONVERSATION_NOT_FOUND')
    return c

@router.get('/conversations/{conversation_id}/messages', response_model=list[DirectMessageResponse])
def list_messages(conversation_id: UUID, workspace_id: UUID=Depends(get_workspace_id), _: User=Depends(require_min_role(RoleName.ANALYST)), db: Session=Depends(get_db)):
    return DirectMessageRepository(db).list_for_conversation(workspace_id, conversation_id)

@router.post('/conversations/{conversation_id}/messages', response_model=DirectMessageResponse)
def add_message(conversation_id: UUID, payload: DirectMessageCreate, workspace_id: UUID=Depends(get_workspace_id), _: User=Depends(require_min_role(RoleName.MANAGER)), db: Session=Depends(get_db)):
    try: msg=DirectConversationService(DirectConversationRepository(db), DirectMessageRepository(db)).add_message(workspace_id, conversation_id, payload.text)
    except ValueError as exc: raise HTTPException(404, str(exc)) from exc
    db.commit(); db.refresh(msg); return msg

@router.post('/conversations/{conversation_id}/analyze', response_model=AIAnalysisResponse)
async def analyze(conversation_id: UUID, workspace_id: UUID=Depends(get_workspace_id), user: User=Depends(require_roles(RoleName.OWNER, RoleName.MANAGER)), db: Session=Depends(get_db)):
    service=DirectIntelligenceService(AIRepository(db), DirectConversationRepository(db), DirectMessageRepository(db))
    try: analysis=await service.analyze(workspace_id, conversation_id, user.id)
    except AIError as exc: raise HTTPException(400, exc.safe_code) from exc
    db.commit(); db.refresh(analysis); return analysis

@router.get('/conversations/{conversation_id}/analyses', response_model=list[AIAnalysisResponse])
def analyses(conversation_id: UUID, workspace_id: UUID=Depends(get_workspace_id), _: User=Depends(require_min_role(RoleName.ANALYST)), db: Session=Depends(get_db)):
    return AIRepository(db).list_analyses(workspace_id, conversation_id)

@router.get('/conversations/{conversation_id}/suggestions', response_model=list[AISuggestionResponse])
def suggestions(conversation_id: UUID, workspace_id: UUID=Depends(get_workspace_id), _: User=Depends(require_min_role(RoleName.ANALYST)), db: Session=Depends(get_db)):
    return AIRepository(db).list_suggestions(workspace_id, conversation_id)


@router.post('/conversations/{conversation_id}/reply/prepare', response_model=ReplyPrepareResponse)
def prepare_reply(conversation_id: UUID, payload: ReplyPrepareRequest, workspace_id: UUID=Depends(get_workspace_id), _: User=Depends(require_min_role(RoleName.MANAGER)), db: Session=Depends(get_db)):
    ready, blockers, warnings = InstagramOutboundMessageService(db).prepare(workspace_id, conversation_id, payload.message_text, payload.human_agent_requested)
    return ReplyPrepareResponse(ready=ready, blockers=blockers, warnings=warnings, message_preview=payload.message_text, human_agent_eligible=payload.human_agent_requested and not blockers)

@router.post('/conversations/{conversation_id}/reply/send', response_model=ReplySendResponse)
async def send_reply(conversation_id: UUID, payload: ReplySendRequest, idempotency_key: str | None=Header(default=None, alias='Idempotency-Key'), workspace_id: UUID=Depends(get_workspace_id), user: User=Depends(require_min_role(RoleName.MANAGER)), db: Session=Depends(get_db)):
    if not idempotency_key:
        raise HTTPException(400, 'META_IDEMPOTENCY_KEY_REUSED')
    service = InstagramOutboundMessageService(db)
    try:
        op = service.prepare_operation(workspace_id, conversation_id, user.id, payload.message_text, idempotency_key, payload.human_agent_requested)
        db.commit(); operation_id = op.id
    except MetaInstagramError as exc:
        db.rollback(); raise HTTPException(exc.status_code, {'code': exc.code, 'message': exc.message}) from exc
    try:
        result = await service.call_provider(workspace_id, operation_id, payload.message_text)
        op = service.finalize_success(workspace_id, operation_id, payload.message_text, result); db.commit(); db.refresh(op)
        return ReplySendResponse(operation_id=op.id, status=op.status, provider_message_id=op.provider_message_id, direct_message_id=op.direct_message_id)
    except MetaInstagramError as exc:
        op = service.finalize_failure(workspace_id, operation_id, exc); db.commit(); db.refresh(op)
        return ReplySendResponse(operation_id=op.id, status=op.status, provider_message_id=op.provider_message_id, direct_message_id=op.direct_message_id)

@router.get('/message-operations/{operation_id}', response_model=MessageOperationResponse)
def message_operation_status(operation_id: UUID, workspace_id: UUID=Depends(get_workspace_id), _: User=Depends(require_min_role(RoleName.ANALYST)), db: Session=Depends(get_db)):
    try: return InstagramReconciliationService(db).status(workspace_id, operation_id)
    except MetaInstagramError as exc: raise HTTPException(exc.status_code, {'code': exc.code, 'message': exc.message}) from exc

@router.post('/message-operations/{operation_id}/reconcile', response_model=MessageOperationResponse)
def reconcile_message_operation(operation_id: UUID, workspace_id: UUID=Depends(get_workspace_id), _: User=Depends(require_min_role(RoleName.MANAGER)), db: Session=Depends(get_db)):
    try:
        op = InstagramReconciliationService(db).reconcile(workspace_id, operation_id); db.commit(); db.refresh(op); return op
    except MetaInstagramError as exc:
        db.rollback(); raise HTTPException(exc.status_code, {'code': exc.code, 'message': exc.message}) from exc
