import base64
import binascii
import hashlib
import hmac
import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.platform_admin import PlatformAuditEvent, PlatformRole
from app.repositories.platform_admin_repository import PlatformAuditRepository, PlatformUserRepository, PlatformWorkspaceRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.schemas.platform_admin import (
    PlatformIdentity, PlatformSummary, PlatformUser, PlatformUserDetail, PlatformUserPage, PlatformUserSegment,
    PlatformUserSummary, PlatformUserWorkspace,
    PlatformWorkspace, PlatformWorkspaceDetail, PlatformWorkspacePage,
)
from app.schemas.subscription import SubscriptionDisplayStatus, SubscriptionStatusResponse
from app.services.subscription_service import describe_subscription

CAPABILITIES = {
    PlatformRole.ADMIN: (
        "platform.access", "workspaces.read", "subscriptions.read", "activity.read",
        "users.read", "workspaces.archive",
    ),
    PlatformRole.SUPPORT: ("platform.access", "workspaces.read", "subscriptions.read", "activity.read"),
    PlatformRole.AUDITOR: ("platform.access",),
}


class InvalidPlatformCursor(ValueError):
    pass


def _cursor_signature(payload: bytes, filters: tuple) -> bytes:
    context = json.dumps(filters, separators=(",", ":")).encode()
    return hmac.digest(
        get_settings().jwt_secret.encode(),
        b"sellora-platform-workspaces-v2:" + context + b"\x00" + payload,
        hashlib.sha256,
    )


def _encode_cursor(created_at: datetime, record_id: UUID, filters: tuple) -> str:
    payload = json.dumps([created_at.isoformat(), str(record_id)], separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(_cursor_signature(payload, filters) + payload).decode()


def _decode_cursor(cursor: str, filters: tuple) -> tuple[datetime, UUID]:
    try:
        signed = base64.b64decode(cursor, altchars=b"-_", validate=True)
        signature, payload = signed[:32], signed[32:]
        if not hmac.compare_digest(signature, _cursor_signature(payload, filters)):
            raise ValueError
        created_at, workspace_id = json.loads(payload)
        instant = datetime.fromisoformat(created_at)
        if instant.tzinfo is None:
            raise ValueError
        return instant, UUID(workspace_id)
    except (ValueError, TypeError, binascii.Error) as exc:
        raise InvalidPlatformCursor("Invalid workspace cursor") from exc


class PlatformWorkspaceService:
    def __init__(self, db: Session) -> None:
        self.workspaces = PlatformWorkspaceRepository(db)
        self.subscriptions = SubscriptionRepository(db)

    @staticmethod
    def _project(row, now: datetime) -> PlatformWorkspace:
        workspace, demo, subscription = row
        return PlatformWorkspace(
            id=workspace.id, name=workspace.name, slug=workspace.slug, is_active=workspace.is_active,
            is_demo=demo, created_at=workspace.created_at, archived_at=workspace.archived_at,
            subscription=describe_subscription(workspace.id, subscription, now=now),
        )

    def list_workspaces(
        self, *, search: str | None, active: bool | None, demo: bool | None, cursor: str | None, limit: int,
        subscription_status: SubscriptionDisplayStatus | None = None, archived: bool | None = None,
    ) -> PlatformWorkspacePage:
        search = search.strip() or None if search else None
        filters = (search, active, demo)
        if subscription_status is not None:
            filters += (subscription_status.value,)
        if archived is not None:
            filters += ("archived", archived)
        before = _decode_cursor(cursor, filters) if cursor else None
        now = datetime.now(UTC)
        rows = self.workspaces.list_workspaces(
            search=search, active=active, demo=demo, before=before, limit=limit + 1,
            subscription_status=subscription_status, now=now, archived=archived,
        )
        items = [self._project(row, now) for row in rows[:limit]]
        return PlatformWorkspacePage(
            items=items, as_of=now,
            next_cursor=_encode_cursor(items[-1].created_at, items[-1].id, filters) if len(rows) > limit else None,
        )

    def get_workspace(self, workspace_id: UUID) -> PlatformWorkspaceDetail | None:
        row = self.workspaces.get_workspace(workspace_id)
        if row is None:
            return None
        workspace, demo, subscription = row
        return PlatformWorkspaceDetail(
            **self._project(row, datetime.now(UTC)).model_dump(),
            currency_code=workspace.currency_code, timezone=workspace.timezone,
            active_member_count=self.workspaces.count_active_members(workspace_id),
            archive_allowed=workspace.archived_at is None and subscription is None and (demo or not workspace.is_active),
        )

    def get_subscription(self, workspace_id: UUID) -> SubscriptionStatusResponse | None:
        if not self.workspaces.exists(workspace_id):
            return None
        return describe_subscription(
            workspace_id, self.subscriptions.get_for_workspace(workspace_id), now=datetime.now(UTC)
        )

    def get_summary(self) -> PlatformSummary:
        now = datetime.now(UTC)
        return PlatformSummary(as_of=now, **self.workspaces.summarize(now))


class WorkspaceArchiveConflict(ValueError):
    pass


class PlatformWorkspaceArchiveService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.workspaces = PlatformWorkspaceRepository(db)
        self.audit = PlatformAuditRepository(db)

    def set_archived(self, workspace_id: UUID, actor: PlatformIdentity, *, archived: bool) -> None:
        action = "ARCHIVE_WORKSPACE" if archived else "RESTORE_WORKSPACE"
        workspace = self.workspaces.lock_workspace(workspace_id)
        outcome = "ALLOWED"
        if workspace is None:
            outcome = "NOT_FOUND"
        elif archived and workspace.archived_at is None:
            demo, has_subscription = self.workspaces.archive_facts(workspace_id)
            if has_subscription or (workspace.is_active and not demo):
                outcome = "DENIED"
            else:
                workspace.archived_was_active = workspace.is_active
                workspace.archived_at = datetime.now(UTC)
                workspace.is_active = False
        elif not archived and workspace.archived_at is not None:
            workspace.is_active = workspace.archived_was_active is True
            workspace.archived_at = None
            workspace.archived_was_active = None
        else:
            # Repeated requests leave both lifecycle state and audit unchanged.
            self.db.rollback()
            return

        self.audit.add(PlatformAuditEvent(
            actor_user_id=actor.operator_id, actor_role=actor.role, action=action, outcome=outcome,
            workspace_id=workspace_id,
        ))
        self.db.commit()
        if outcome == "NOT_FOUND":
            raise LookupError("Workspace not found")
        if outcome == "DENIED":
            raise WorkspaceArchiveConflict("Workspace cannot be archived")


class PlatformUserService:
    def __init__(self, db: Session) -> None:
        self.users = PlatformUserRepository(db)

    @staticmethod
    def _project(user, counts) -> PlatformUser:
        segment: PlatformUserSegment = "NO_ENABLED_WORKSPACE"
        if counts and counts["standard_count"]:
            segment = "STANDARD"
        elif counts and counts["demo_count"]:
            segment = "DEMO_ONLY"
        return PlatformUser(
            **user, segment=segment, owned_workspace_count=counts["owned_count"] if counts else 0,
        )

    def summarize(self) -> PlatformUserSummary:
        return PlatformUserSummary(**self.users.summarize())

    def list_users(
        self, *, search: str | None, without_workspaces: bool, cursor: str | None, limit: int,
        segment: PlatformUserSegment | None = None, active: bool | None = None,
    ) -> PlatformUserPage:
        search = (search or "").strip() or None
        filters = ("users", search, without_workspaces)
        if segment is not None or active is not None:
            filters += (segment, active)
        before = _decode_cursor(cursor, filters) if cursor else None
        rows = self.users.list_users(
            search=search, without_workspaces=without_workspaces, segment=segment,
            active=active, before=before, limit=limit + 1,
        )
        visible = rows[:limit]
        counts = self.users.workspace_counts([row["id"] for row in visible]) if visible else {}
        items = [self._project(row, counts.get(row["id"])) for row in visible]
        return PlatformUserPage(
            items=items,
            next_cursor=_encode_cursor(items[-1].created_at, items[-1].id, filters) if len(rows) > limit else None,
        )

    def get_user(self, user_id: UUID, cursor: str | None) -> PlatformUserDetail | None:
        filters = ("user-workspaces", str(user_id))
        before = _decode_cursor(cursor, filters) if cursor else None
        user = self.users.get_user(user_id)
        if user is None:
            return None
        limit = 20
        rows = self.users.list_user_workspaces(user_id, before=before, limit=limit + 1)
        items = [PlatformUserWorkspace(**row) for row in rows[:limit]]
        projection = self._project(user, self.users.workspace_counts([user_id]).get(user_id))
        return PlatformUserDetail(
            **projection.model_dump(), workspaces=items,
            next_cursor=_encode_cursor(rows[limit - 1]["created_at"], items[-1].id, filters) if len(rows) > limit else None,
        )


class PlatformAuditService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = PlatformAuditRepository(db)

    def record_read(
        self, actor_id: UUID, role: PlatformRole | None, action: str, outcome: str,
        workspace_id: UUID | None = None, *, target_user_id: UUID | None = None,
    ) -> None:
        if outcome == "DENIED" and self.audit.recently_denied(actor_id, action, datetime.now(UTC)):
            return
        self.audit.add(PlatformAuditEvent(
            actor_user_id=actor_id, actor_role=role, action=action, outcome=outcome, workspace_id=workspace_id,
            target_user_id=target_user_id,
        ))
        self.db.commit()


def platform_identity(operator_id: UUID, role: PlatformRole) -> PlatformIdentity:
    return PlatformIdentity(operator_id=operator_id, role=role, capabilities=list(CAPABILITIES[role]))
