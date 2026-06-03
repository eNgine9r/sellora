from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.models.attachment import AttachmentEntityType
from app.models.role import RoleName
from app.models.user import User
from app.schemas.crm_completion import AttachmentCreate, AttachmentResponse
from app.services.crm_completion_service import AttachmentService, CrmCompletionServiceError

router = APIRouter(prefix="/attachments", tags=["Attachments"])


@router.get("", response_model=list[AttachmentResponse], dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def list_attachments(
    workspace_id: UUID = Depends(get_workspace_id),
    entity_type: AttachmentEntityType | None = Query(default=None),
    entity_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[AttachmentResponse]:
    return AttachmentService(db).list(workspace_id, entity_type, entity_id)


@router.post("", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
def create_attachment(
    payload: AttachmentCreate,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
) -> AttachmentResponse:
    try:
        return AttachmentService(db).create(workspace_id, payload, current_user.id)
    except CrmCompletionServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(
    attachment_id: UUID,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
) -> Response:
    if not AttachmentService(db).delete(workspace_id, attachment_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
