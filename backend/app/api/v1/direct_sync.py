from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.integrations.meta_instagram.exceptions import MetaInstagramError
from app.integrations.meta_instagram.repositories.inbox_sync_repository import (
    InstagramMessageStateRepository,
)
from app.integrations.meta_instagram.schemas import (
    InstagramHistorySyncRequest,
    InstagramHistorySyncResponse,
)
from app.integrations.meta_instagram.services.history_sync_service import (
    InstagramHistorySyncService,
)
from app.models.role import RoleName
from app.models.user import User
from app.repositories.ai_direct_repository import (
    DirectConversationRepository,
    DirectMessageRepository,
)
from app.schemas.ai_direct import DirectMessageResponse


router = APIRouter(prefix="/direct", tags=["direct-instagram-sync"])


def message_response(message, state=None) -> DirectMessageResponse:
    data = DirectMessageResponse.model_validate(message).model_dump()
    if state:
        data.update(
            seen_at=state.seen_at,
            edited_at=state.edited_at,
            edit_count=state.edit_count,
            reaction=state.reaction,
            reaction_updated_at=state.reaction_updated_at,
        )
    return DirectMessageResponse(**data)


@router.get(
    "/history-sync",
    response_model=InstagramHistorySyncResponse | None,
)
def history_sync_status(
    workspace_id: UUID = Depends(get_workspace_id),
    _: User = Depends(require_min_role(RoleName.ANALYST)),
    db: Session = Depends(get_db),
):
    return InstagramHistorySyncService(db).status(workspace_id)


@router.post(
    "/history-sync",
    response_model=InstagramHistorySyncResponse,
)
def request_history_sync(
    payload: InstagramHistorySyncRequest,
    workspace_id: UUID = Depends(get_workspace_id),
    user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
):
    try:
        sync = InstagramHistorySyncService(db).request_sync(
            workspace_id,
            user.id,
            conversation_limit=payload.conversation_limit,
            messages_per_conversation=payload.messages_per_conversation,
        )
        db.commit()
        db.refresh(sync)
        return sync
    except MetaInstagramError as exc:
        db.rollback()
        raise HTTPException(
            exc.status_code,
            {"code": exc.code, "message": exc.message},
        ) from exc


@router.get(
    "/conversations/{conversation_id}/message-timeline",
    response_model=list[DirectMessageResponse],
)
def message_timeline(
    conversation_id: UUID,
    workspace_id: UUID = Depends(get_workspace_id),
    _: User = Depends(require_min_role(RoleName.ANALYST)),
    db: Session = Depends(get_db),
):
    conversation = DirectConversationRepository(db).get(workspace_id, conversation_id)
    if not conversation:
        raise HTTPException(404, "DIRECT_CONVERSATION_NOT_FOUND")
    messages = DirectMessageRepository(db).list_for_conversation(
        workspace_id,
        conversation_id,
    )
    states = InstagramMessageStateRepository(db).list_for_messages(
        workspace_id,
        [message.id for message in messages],
    )
    return [message_response(message, states.get(message.id)) for message in messages]
