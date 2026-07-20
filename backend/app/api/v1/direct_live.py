from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.ai.services.direct_order_intent_service import detect_direct_order_intent
from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.models.role import RoleName
from app.models.user import User
from app.repositories.ai_direct_repository import (
    DirectConversationRepository,
    DirectMessageRepository,
)
from app.schemas.ai_direct import (
    DirectConversationResponse,
    DirectLiveEventResponse,
    DirectLiveSummaryResponse,
)


router = APIRouter(prefix="/direct", tags=["direct-live"])


@router.get("/live-summary", response_model=DirectLiveSummaryResponse)
def direct_live_summary(
    limit: int = Query(default=20, ge=1, le=50),
    workspace_id: UUID = Depends(get_workspace_id),
    _: User = Depends(require_min_role(RoleName.ANALYST)),
    db: Session = Depends(get_db),
):
    conversation_repository = DirectConversationRepository(db)
    rows = DirectMessageRepository(db).recent_unread_inbound(
        workspace_id,
        limit=limit,
    )
    events: list[DirectLiveEventResponse] = []
    for message, conversation in rows:
        signal = detect_direct_order_intent(message.text)
        preview = " ".join((message.text or "Instagram message").split())[:220]
        events.append(
            DirectLiveEventResponse(
                message_id=message.id,
                conversation_id=conversation.id,
                participant_display_name=conversation.participant_display_name,
                participant_username=conversation.participant_username,
                text_preview=preview,
                received_at=message.received_at,
                unread_count=conversation.unread_count,
                order_intent=signal.detected,
                order_intent_confidence=signal.confidence,
                order_intent_reason=signal.reason,
            )
        )

    return DirectLiveSummaryResponse(
        server_time=datetime.now(UTC),
        unread_total=conversation_repository.unread_total(workspace_id),
        order_intent_count=sum(1 for event in events if event.order_intent),
        events=events,
    )


@router.post(
    "/conversations/{conversation_id}/read",
    response_model=DirectConversationResponse,
)
def mark_direct_conversation_read(
    conversation_id: UUID,
    workspace_id: UUID = Depends(get_workspace_id),
    _: User = Depends(require_min_role(RoleName.ANALYST)),
    db: Session = Depends(get_db),
):
    repository = DirectConversationRepository(db)
    conversation = repository.mark_read(workspace_id, conversation_id)
    if not conversation:
        db.rollback()
        raise HTTPException(404, "DIRECT_CONVERSATION_NOT_FOUND")
    db.commit()
    refreshed = repository.get(workspace_id, conversation_id)
    if not refreshed:
        raise HTTPException(404, "DIRECT_CONVERSATION_NOT_FOUND")
    return refreshed
