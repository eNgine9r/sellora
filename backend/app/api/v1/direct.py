from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
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
