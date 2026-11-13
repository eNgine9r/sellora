from collections.abc import Callable
from typing import Annotated, Literal, TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, SecretStr
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.platform_admin import PlatformSession, require_platform_mfa_challenge, require_platform_permission
from app.schemas.platform_admin import (
    PlatformIdentity,
    PlatformSummary,
    PlatformUserDetail,
    PlatformUserPage,
    PlatformUserSearchParams,
    PlatformUserSummary,
    PlatformWorkspaceDetail,
    PlatformWorkspaceListParams,
    PlatformWorkspacePage,
    PlatformWorkspaceRequestError,
    PlatformWorkspaceSearchParams,
    PlatformWorkspaceTeamPage,
)
from app.schemas.product_usage import ProductUsageReport
from app.schemas.subscription import SubscriptionStatusResponse
from app.services.platform_admin_service import (
    InvalidPlatformCursor, PlatformAuditService, PlatformUserService, PlatformWorkspaceArchiveService,
    PlatformWorkspaceService, WorkspaceArchiveConflict,
)

from app.services.platform_mfa_service import PlatformMfaError, PlatformMfaService
from app.services.product_usage_service import ProductUsageService

router = APIRouter(prefix="/platform-admin", tags=["Platform Admin"])
Result = TypeVar("Result")

ME = "READ_PLATFORM_IDENTITY"
SUMMARY = "READ_PLATFORM_SUMMARY"
ACTIVITY_SUMMARY = "READ_ACTIVITY_SUMMARY"
WORKSPACE_ACTIVITY = "READ_WORKSPACE_ACTIVITY"
WORKSPACES = "LIST_WORKSPACES"
WORKSPACE = "READ_WORKSPACE"
SUBSCRIPTION = "READ_SUBSCRIPTION"
WORKSPACE_REQUEST_ERRORS = {422: {"model": PlatformWorkspaceRequestError}}


def _audited_read(
    db: Session, actor: PlatformIdentity, action: str, read: Callable[[], Result | None],
    workspace_id: UUID | None = None, *, target_user_id: UUID | None = None,
) -> Result:
    try:
        result = read()
        PlatformAuditService(db).record_read(
            actor.operator_id, actor.role, action, "NOT_FOUND" if result is None else "ALLOWED", workspace_id,
            target_user_id=target_user_id,
        )
    except InvalidPlatformCursor as exc:
        raise HTTPException(status_code=422, detail="Invalid cursor") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Platform data unavailable") from exc
    if result is None:
        raise HTTPException(status_code=404, detail="User not found" if target_user_id else "Workspace not found")
    return result


class PlatformMfaCode(BaseModel):
    code: SecretStr


@router.post("/mfa/verify")
def verify_platform_mfa(
    body: PlatformMfaCode,
    request: Request,
    operator: PlatformSession = Depends(require_platform_mfa_challenge),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if request.query_params:
        raise HTTPException(status_code=422, detail="Invalid MFA request")
    try:
        proof = PlatformMfaService(db).verify(
            operator.identity.operator_id, operator.identity.role, operator.session_id,
            operator.granted_at, body.code.get_secret_value(),
        )
    except PlatformMfaError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from None
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Platform access unavailable") from exc
    return {"proof": proof}


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


@router.get("/workspaces", response_model=PlatformWorkspacePage, responses=WORKSPACE_REQUEST_ERRORS)
def list_platform_workspaces(
    params: Annotated[PlatformWorkspaceListParams, Query()],
    actor: PlatformIdentity = Depends(require_platform_permission("workspaces.read", WORKSPACES)),
    db: Session = Depends(get_db),
) -> PlatformWorkspacePage:
    service = PlatformWorkspaceService(db)
    return _audited_read(db, actor, WORKSPACES, lambda: service.list_workspaces(
        search=None, active=params.active, demo=params.demo, cursor=None, limit=params.limit,
    ))


@router.post("/workspaces/search", response_model=PlatformWorkspacePage, responses=WORKSPACE_REQUEST_ERRORS)
def search_platform_workspaces(
    params: PlatformWorkspaceSearchParams,
    request: Request,
    actor: PlatformIdentity = Depends(require_platform_permission("workspaces.read", WORKSPACES)),
    db: Session = Depends(get_db),
) -> PlatformWorkspacePage:
    if request.query_params:
        raise HTTPException(status_code=422, detail="Workspace search accepts filters in the request body")
    service = PlatformWorkspaceService(db)
    return _audited_read(db, actor, WORKSPACES, lambda: service.list_workspaces(
        search=params.q, active=params.active, demo=params.demo, cursor=params.cursor, limit=params.limit,
        subscription_status=params.subscription_status, archived=params.archived,
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


@router.get("/activity/summary", response_model=ProductUsageReport)
def get_platform_activity(
    actor: PlatformIdentity = Depends(require_platform_permission("activity.read", ACTIVITY_SUMMARY)),
    db: Session = Depends(get_db),
    days: Literal["7", "30"] = "7",
) -> ProductUsageReport:
    period = 7 if days == "7" else 30
    return _audited_read(db, actor, ACTIVITY_SUMMARY, lambda: ProductUsageService(db).get_report(period))


@router.get("/workspaces/{workspace_id}/activity", response_model=ProductUsageReport)
def get_workspace_activity(
    workspace_id: UUID,
    actor: PlatformIdentity = Depends(require_platform_permission("activity.read", WORKSPACE_ACTIVITY)),
    db: Session = Depends(get_db),
    days: Literal["7", "30"] = "7",
) -> ProductUsageReport:
    period = 7 if days == "7" else 30
    return _audited_read(
        db, actor, WORKSPACE_ACTIVITY,
        lambda: ProductUsageService(db).get_report(period, workspace_id=workspace_id),
        workspace_id,
    )


@router.get("/workspaces/{workspace_id}/team", response_model=PlatformWorkspaceTeamPage)
def get_platform_workspace_team(
    workspace_id: UUID,
    cursor: UUID | None = None,
    actor: PlatformIdentity = Depends(require_platform_permission("users.read", "READ_WORKSPACE_TEAM")),
    db: Session = Depends(get_db),
) -> PlatformWorkspaceTeamPage:
    return _audited_read(
        db, actor, "READ_WORKSPACE_TEAM", lambda: PlatformWorkspaceService(db).get_team(workspace_id, cursor),
        workspace_id,
    )


@router.post("/users/search", response_model=PlatformUserPage, responses=WORKSPACE_REQUEST_ERRORS)
def search_platform_users(
    params: PlatformUserSearchParams,
    request: Request,
    actor: PlatformIdentity = Depends(require_platform_permission("users.read", "LIST_USERS")),
    db: Session = Depends(get_db),
) -> PlatformUserPage:
    if request.query_params:
        raise HTTPException(status_code=422, detail="User search accepts filters in the request body")
    service = PlatformUserService(db)
    return _audited_read(db, actor, "LIST_USERS", lambda: service.list_users(
        search=params.q, without_workspaces=params.without_workspaces, cursor=params.cursor, limit=params.limit,
        segment=params.segment, active=params.active,
    ))


@router.get("/users/summary", response_model=PlatformUserSummary)
def get_platform_users_summary(
    actor: PlatformIdentity = Depends(require_platform_permission("users.read", "READ_USERS_SUMMARY")),
    db: Session = Depends(get_db),
) -> PlatformUserSummary:
    return _audited_read(db, actor, "READ_USERS_SUMMARY", PlatformUserService(db).summarize)


@router.get("/users/{user_id}", response_model=PlatformUserDetail)
def get_platform_user(
    user_id: UUID,
    cursor: Annotated[str | None, Query(min_length=1, max_length=900)] = None,
    actor: PlatformIdentity = Depends(require_platform_permission("users.read", "READ_USER")),
    db: Session = Depends(get_db),
) -> PlatformUserDetail:
    return _audited_read(db, actor, "READ_USER", lambda: PlatformUserService(db).get_user(user_id, cursor),
                         target_user_id=user_id)


def _set_workspace_archived(db: Session, workspace_id: UUID, actor: PlatformIdentity, *, archived: bool) -> Response:
    try:
        PlatformWorkspaceArchiveService(db).set_archived(workspace_id, actor, archived=archived)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Workspace not found") from exc
    except WorkspaceArchiveConflict as exc:
        raise HTTPException(status_code=409, detail="Workspace cannot be archived") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Platform data unavailable") from exc
    return Response(status_code=204)


@router.post("/workspaces/{workspace_id}/archive", status_code=204)
def archive_platform_workspace(
    workspace_id: UUID,
    actor: PlatformIdentity = Depends(require_platform_permission("workspaces.archive", "ARCHIVE_WORKSPACE")),
    db: Session = Depends(get_db),
) -> Response:
    return _set_workspace_archived(db, workspace_id, actor, archived=True)


@router.post("/workspaces/{workspace_id}/restore", status_code=204)
def restore_platform_workspace(
    workspace_id: UUID,
    actor: PlatformIdentity = Depends(require_platform_permission("workspaces.archive", "RESTORE_WORKSPACE")),
    db: Session = Depends(get_db),
) -> Response:
    return _set_workspace_archived(db, workspace_id, actor, archived=False)
