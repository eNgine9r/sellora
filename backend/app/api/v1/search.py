from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.models.role import RoleName
from app.services.global_search_service import global_search

router = APIRouter(prefix="/search", tags=["Search"], dependencies=[Depends(require_min_role(RoleName.ANALYST))])


class SearchResult(BaseModel):
    kind: str
    id: str
    title: str
    subtitle: str
    href: str


@router.get("", response_model=list[SearchResult])
def search_records(
    q: str = Query(min_length=2, max_length=80),
    workspace_id: UUID = Depends(get_workspace_id),
    db: Session = Depends(get_db),
) -> list[SearchResult]:
    return [SearchResult(**item) for item in global_search(db, workspace_id, q)]
