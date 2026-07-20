from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.ai.exceptions import AIError
from app.ai.services.direct_conversation_service import DirectConversationService
from app.ai.services.direct_intelligence_service import DirectIntelligenceService
from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role, require_roles
from app.integrations.meta_instagram.exceptions import MetaInstagramError
from app.integrations.meta_instagram.repositories.participant_profile_repository import InstagramParticipantProfileRepository
from app.integrations.meta_instagram.schemas import (
    MessageOperationResponse,
    ReplyPrepareRequest,
    ReplyPrepareResponse,
    ReplySendRequest,
    ReplySendResponse,
)
from app.integrations.meta_instagram.services.outbound_message_service import InstagramOutboundMessageService
from app.integrations.meta_instagram.services.participant_profile_service import InstagramParticipantProfileService
from app.integrations.meta_instagram.services.reconciliation_service import InstagramReconciliationService
from app.models.role import RoleName
from app.models.user import User
from app.repositories.ai_direct_repository import (
    AIRepository,
    DirectConversationRepository,
    DirectMessageRepository,
)
from app.schemas.ai_direct import (
    AIAnalysisResponse,
    AISuggestionResponse,
    DirectConversationResponse,
    DirectMessageCreate,
    DirectMessageResponse,
    SyntheticConversationCreate,
)


router = APIRouter(prefix="/direct", tags=["direct-intelligence"])


def deps(db: Session):
    return DirectConversationRepository(db), DirectMessageRepository(db), AIRepository(db)


def conversation_response(conversation, profile=None) -> DirectConversationResponse:
    data = DirectConversationResponse.model_validate(conversation).model_dump()
    if profile:
        data.update(
            participant_profile_picture_url=profile.profile_picture_url,
            participant_profile_picture_expires_at=profile.profile_picture_expires_at,
            participant_follower_count=profile.follower_count,
            participant_is_verified_user=profile.is_verified_user,
            participant_is_user_follow_business=profile.is_user_follow_business,
            participant_is_business_follow_user=profile.is_business_follow_user,
            participant_profile_status=profile.status,
            participant_profile_last_synced_at=profile.last_synced_at,
            participant_profile_next_retry_at=profile.next_retry_at,
            participant_profile_error_code=profile.last_error_code,
        )
    return DirectConversationResponse(**data)


@router.get("/conversations", response_model=list[DirectConversationResponse])
def list_conversations(
    workspace_id: UUID = Depends(get_workspace_id),
    _: User = Depends(require_min_role(RoleName.ANALYST)),
    db: Session = Depends(get_db),
):
    conversations = DirectConversationRepository(db).list(workspace_id)
    profiles = InstagramParticipantProfileRepository(db).list_for_conversations(
        workspace_id,
        [conversation.id for conversation in conversations],
    )
    return [
        conversation_response(conversation, profiles.get(conversation.id))
        for conversation in conversations
    ]


@router.post("/conversations", response_model=DirectConversationResponse)
def create_conversation(
    payload: SyntheticConversationCreate,
    workspace_id: UUID = Depends(get_workspace_id),
    user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
):
    service = DirectConversationService(
        DirectConversationRepository(db),
        DirectMessageRepository(db),
    )
    conversation = service.create_synthetic(
        workspace_id,
        user.id,
        payload.participant_display_name,
        payload.participant_username,
        payload.initial_message,
    )
    db.commit()
    db.refresh(conversation)
    return conversation_response(conversation)


@router.get("/conversations/{conversation_id}", response_model=DirectConversationResponse)
def get_conversation(
    conversation_id: UUID,
    workspace_id: UUID = Depends(get_workspace_id),
    _: User = Depends(require_min_role(RoleName.ANALYST)),
    db: Session = Depends(get_db),
):
    conversation = DirectConversationRepository(db).get(workspace_id, conversation_id)
    if not conversation:
        raise HTTPException(404, "DIRECT_CONVERSATION_NOT_FOUND")
    profile = InstagramParticipantProfileRepository(db).get_by_conversation(
        workspace_id,
        conversation_id,
    )
    return conversation_response(conversation, profile)


@router.post(
    "/conversations/{conversation_id}/participant-profile/refresh",
    response_model=DirectConversationResponse,
)
def refresh_participant_profile(
    conversation_id: UUID,
    workspace_id: UUID = Depends(get_workspace_id),
    _: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
):
    try:
        profile = InstagramParticipantProfileService(db).refresh(
            workspace_id,
            conversation_id,
        )
        conversation = DirectConversationRepository(db).get(workspace_id, conversation_id)
        if not conversation:
            raise HTTPException(404, "DIRECT_CONVERSATION_NOT_FOUND")
        db.commit()
        return conversation_response(conversation, profile)
    except MetaInstagramError as exc:
        db.rollback()
        raise HTTPException(
            exc.status_code,
            {"code": exc.code, "message": exc.message},
        ) from exc


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[DirectMessageResponse],
)
def list_messages(
    conversation_id: UUID,
    workspace_id: UUID = Depends(get_workspace_id),
    _: User = Depends(require_min_role(RoleName.ANALYST)),
    db: Session = Depends(get_db),
):
    return DirectMessageRepository(db).list_for_conversation(workspace_id, conversation_id)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=DirectMessageResponse,
)
def add_message(
    conversation_id: UUID,
    payload: DirectMessageCreate,
    workspace_id: UUID = Depends(get_workspace_id),
    _: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
):
    try:
        message = DirectConversationService(
            DirectConversationRepository(db),
            DirectMessageRepository(db),
        ).add_message(workspace_id, conversation_id, payload.text)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    db.commit()
    db.refresh(message)
    return message


@router.post("/conversations/{conversation_id}/analyze", response_model=AIAnalysisResponse)
async def analyze(
    conversation_id: UUID,
    workspace_id: UUID = Depends(get_workspace_id),
    user: User = Depends(require_roles(RoleName.OWNER, RoleName.MANAGER)),
    db: Session = Depends(get_db),
):
    service = DirectIntelligenceService(
        AIRepository(db),
        DirectConversationRepository(db),
        DirectMessageRepository(db),
    )
    try:
        analysis = await service.analyze(workspace_id, conversation_id, user.id)
    except AIError as exc:
        raise HTTPException(400, exc.safe_code) from exc
    db.commit()
    db.refresh(analysis)
    return analysis


@router.get(
    "/conversations/{conversation_id}/analyses",
    response_model=list[AIAnalysisResponse],
)
def analyses(
    conversation_id: UUID,
    workspace_id: UUID = Depends(get_workspace_id),
    _: User = Depends(require_min_role(RoleName.ANALYST)),
    db: Session = Depends(get_db),
):
    return AIRepository(db).list_analyses(workspace_id, conversation_id)


@router.get(
    "/conversations/{conversation_id}/suggestions",
    response_model=list[AISuggestionResponse],
)
def suggestions(
    conversation_id: UUID,
    workspace_id: UUID = Depends(get_workspace_id),
    _: User = Depends(require_min_role(RoleName.ANALYST)),
    db: Session = Depends(get_db),
):
    return AIRepository(db).list_suggestions(workspace_id, conversation_id)


@router.post(
    "/conversations/{conversation_id}/reply/prepare",
    response_model=ReplyPrepareResponse,
)
def prepare_reply(
    conversation_id: UUID,
    payload: ReplyPrepareRequest,
    workspace_id: UUID = Depends(get_workspace_id),
    _: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
):
    ready, blockers, warnings = InstagramOutboundMessageService(db).prepare(
        workspace_id,
        conversation_id,
        payload.message_text,
        payload.human_agent_requested,
    )
    return ReplyPrepareResponse(
        ready=ready,
        blockers=blockers,
        warnings=warnings,
        message_preview=payload.message_text,
        human_agent_eligible=payload.human_agent_requested and not blockers,
    )


@router.post(
    "/conversations/{conversation_id}/reply/send",
    response_model=ReplySendResponse,
)
async def send_reply(
    conversation_id: UUID,
    payload: ReplySendRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    workspace_id: UUID = Depends(get_workspace_id),
    user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
):
    if not idempotency_key:
        raise HTTPException(400, "META_IDEMPOTENCY_KEY_REUSED")
    service = InstagramOutboundMessageService(db)
    try:
        prepared = service.prepare_operation(
            workspace_id,
            conversation_id,
            user.id,
            payload.message_text,
            idempotency_key,
            payload.human_agent_requested,
        )
        db.commit()
        operation_id = prepared.operation.id
        if not prepared.should_call_provider:
            operation = prepared.operation
            return ReplySendResponse(
                operation_id=operation.id,
                status=operation.status,
                provider_message_id=operation.provider_message_id,
                direct_message_id=operation.direct_message_id,
            )
    except MetaInstagramError as exc:
        db.rollback()
        raise HTTPException(
            exc.status_code,
            {"code": exc.code, "message": exc.message},
        ) from exc
    try:
        result = await service.call_provider(workspace_id, operation_id, payload.message_text)
        operation = service.finalize_success(
            workspace_id,
            operation_id,
            payload.message_text,
            result,
        )
        db.commit()
        db.refresh(operation)
        return ReplySendResponse(
            operation_id=operation.id,
            status=operation.status,
            provider_message_id=operation.provider_message_id,
            direct_message_id=operation.direct_message_id,
        )
    except MetaInstagramError as exc:
        operation = service.finalize_failure(workspace_id, operation_id, exc)
        db.commit()
        db.refresh(operation)
        return ReplySendResponse(
            operation_id=operation.id,
            status=operation.status,
            provider_message_id=operation.provider_message_id,
            direct_message_id=operation.direct_message_id,
        )


@router.get("/message-operations/{operation_id}", response_model=MessageOperationResponse)
def message_operation_status(
    operation_id: UUID,
    workspace_id: UUID = Depends(get_workspace_id),
    _: User = Depends(require_min_role(RoleName.ANALYST)),
    db: Session = Depends(get_db),
):
    try:
        return InstagramReconciliationService(db).status(workspace_id, operation_id)
    except MetaInstagramError as exc:
        raise HTTPException(
            exc.status_code,
            {"code": exc.code, "message": exc.message},
        ) from exc


@router.post(
    "/message-operations/{operation_id}/reconcile",
    response_model=MessageOperationResponse,
)
def reconcile_message_operation(
    operation_id: UUID,
    workspace_id: UUID = Depends(get_workspace_id),
    _: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
):
    try:
        operation = InstagramReconciliationService(db).reconcile(
            workspace_id,
            operation_id,
        )
        db.commit()
        db.refresh(operation)
        return operation
    except MetaInstagramError as exc:
        db.rollback()
        raise HTTPException(
            exc.status_code,
            {"code": exc.code, "message": exc.message},
        ) from exc
