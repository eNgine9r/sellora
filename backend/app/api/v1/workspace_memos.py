from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.models.role import RoleName
from app.models.user import User
from app.schemas.workspace_memo import WorkspaceMemoCreate, WorkspaceMemoResponse, WorkspaceMemoUpdate
from app.services.workspace_memo_service import WorkspaceMemoService

router = APIRouter(prefix="/workspace-memos", tags=["Workspace planning"])


@router.get("", response_model=list[WorkspaceMemoResponse], dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def list_workspace_memos(workspace_id: UUID = Depends(get_workspace_id), db: Session = Depends(get_db)):
    return WorkspaceMemoService(db).list(workspace_id)


@router.post("", response_model=WorkspaceMemoResponse, status_code=status.HTTP_201_CREATED)
def create_workspace_memo(
    payload: WorkspaceMemoCreate,
    workspace_id: UUID = Depends(get_workspace_id),
    user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
):
    return WorkspaceMemoService(db).create(workspace_id, payload, user.id)


@router.patch("/{memo_id}", response_model=WorkspaceMemoResponse)
def update_workspace_memo(
    memo_id: UUID,
    payload: WorkspaceMemoUpdate,
    workspace_id: UUID = Depends(get_workspace_id),
    user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
):
    try:
        memo = WorkspaceMemoService(db).update(workspace_id, memo_id, payload, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if memo is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return memo


@router.delete("/{memo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace_memo(
    memo_id: UUID,
    workspace_id: UUID = Depends(get_workspace_id),
    user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
):
    if not WorkspaceMemoService(db).delete(workspace_id, memo_id, user.id):
        raise HTTPException(status_code=404, detail="Note not found")
    return Response(status_code=204)
