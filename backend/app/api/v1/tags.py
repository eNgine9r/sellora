from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.models.role import RoleName
from app.models.user import User
from app.schemas.crm_completion import TagCreate, TagResponse, TagUpdate
from app.services.crm_completion_service import TagService

router = APIRouter(prefix="/tags", tags=["Tags"])


@router.get("", response_model=list[TagResponse], dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def list_tags(
    workspace_id: UUID = Depends(get_workspace_id),
    db: Session = Depends(get_db),
) -> list[TagResponse]:
    return TagService(db).list(workspace_id)


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
def create_tag(
    payload: TagCreate,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
) -> TagResponse:
    return TagService(db).create(workspace_id, payload, current_user.id)


@router.put("/{tag_id}", response_model=TagResponse)
def update_tag(
    tag_id: UUID,
    payload: TagUpdate,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
) -> TagResponse:
    tag = TagService(db).update(workspace_id, tag_id, payload, current_user.id)
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    return tag


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    tag_id: UUID,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
) -> Response:
    if not TagService(db).delete(workspace_id, tag_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
