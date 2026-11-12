from collections.abc import Callable
from typing import TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.platform_admin import require_platform_permission
from app.schemas.platform_admin import PlatformIdentity, PlatformSummary, PlatformWorkspaceDetail, PlatformWorkspacePage
from app.schemas.subscription import SubscriptionStatusResponse
from app.services.platform_admin_service import InvalidPlatformCursor, PlatformAuditService, PlatformWorkspaceService

router = APIRouter(prefix="/platform-admin", tags=["Platform Admin"])
Result = TypeVar("Result")

ME = "READ_PLATFORM_IDENTITY"
SUMMARY = "READ_PLATFORM_SUMMARY"
WORKSPACES = "LIST_WORKSPACES"
WORKSPACE = "READ_WORKSPACE"
SUBSCRIPTION = "READ_SUBSCRIPTION"


def _audited_read(
    db: Session, actor: PlatformIdentity, action: str, read: Callable[[], Result | None],
    workspace_id: UUID | None = None,
) -> Result:
    try:
        result = read()
        PlatformAuditService(db).record_read(
            actor.operator_id, actor.role, action, "NOT_FOUND" if result is None else "ALLOWED", workspace_id
        )
    except InvalidPlatformCursor as exc:
        raise HTTPException(status_code=422, detail="Invalid workspace cursor") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Platform data unavailable") from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return result


@router.get("/me", response_model=PlatformIdentity)
def get_platform_identity(
    actor: PlatformIdentity = Depends(require_platform_permission("platform.access", ME)),
    db: Session = Depends(get_db),
) -> PlatformIdentity:
    return _audited_read(db, actor, ME, lambda: actor)


@router.get("/summary", response_model=PlatformSummary)
def get_platform_summary(
    actor: PlatformIdentity = Depends(require_platform_permission("workspaces.read", SUMMARY)),
    db: Session = Depends(get_db),
) -> PlatformSummary:
    return _audited_read(db, actor, SUMMARY, PlatformWorkspaceService(db).get_summary)


@router.get("/workspaces", response_model=PlatformWorkspacePage)
def list_platform_workspaces(
    actor: PlatformIdentity = Depends(require_platform_permission("workspaces.read", WORKSPACES)),
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, max_length=120),
    active: bool | None = None,
    demo: bool | None = None,
    cursor: str | None = Query(default=None, min_length=1, max_length=900),
    limit: int = Query(default=50, ge=1, le=100),
) -> PlatformWorkspacePage:
    service = PlatformWorkspaceService(db)
    return _audited_read(db, actor, WORKSPACES, lambda: service.list_workspaces(
        search=q, active=active, demo=demo, cursor=cursor, limit=limit
    ))


@router.get("/workspaces/{workspace_id}", response_model=PlatformWorkspaceDetail)
def get_platform_workspace(
    workspace_id: UUID,
    actor: PlatformIdentity = Depends(require_platform_permission("workspaces.read", WORKSPACE)),
    db: Session = Depends(get_db),
) -> PlatformWorkspaceDetail:
    service = PlatformWorkspaceService(db)
    return _audited_read(db, actor, WORKSPACE, lambda: service.get_workspace(workspace_id), workspace_id)


@router.get("/workspaces/{workspace_id}/subscription", response_model=SubscriptionStatusResponse)
def get_platform_subscription(
    workspace_id: UUID,
    actor: PlatformIdentity = Depends(require_platform_permission("subscriptions.read", SUBSCRIPTION)),
    db: Session = Depends(get_db),
) -> SubscriptionStatusResponse:
    service = PlatformWorkspaceService(db)
    return _audited_read(db, actor, SUBSCRIPTION, lambda: service.get_subscription(workspace_id), workspace_id)
