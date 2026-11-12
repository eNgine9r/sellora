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
from app.repositories.platform_admin_repository import PlatformAuditRepository, PlatformWorkspaceRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.schemas.platform_admin import PlatformIdentity, PlatformSummary, PlatformWorkspace, PlatformWorkspaceDetail, PlatformWorkspacePage
from app.schemas.subscription import SubscriptionStatusResponse
from app.services.subscription_service import describe_subscription

CAPABILITIES = {
    PlatformRole.ADMIN: ("platform.access", "workspaces.read", "subscriptions.read"),
    PlatformRole.SUPPORT: ("platform.access", "workspaces.read", "subscriptions.read"),
    PlatformRole.AUDITOR: ("platform.access",),
}


class InvalidPlatformCursor(ValueError):
    pass


def _cursor_signature(payload: bytes) -> bytes:
    return hmac.digest(get_settings().jwt_secret.encode(), b"sellora-platform-workspaces:" + payload, hashlib.sha256)


def _encode_cursor(workspace: PlatformWorkspace, filters: tuple) -> str:
    payload = json.dumps([workspace.created_at.isoformat(), str(workspace.id), filters], separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(_cursor_signature(payload) + payload).decode()


def _decode_cursor(cursor: str, filters: tuple) -> tuple[datetime, UUID]:
    try:
        signed = base64.b64decode(cursor, altchars=b"-_", validate=True)
        signature, payload = signed[:32], signed[32:]
        if not hmac.compare_digest(signature, _cursor_signature(payload)):
            raise ValueError
        created_at, workspace_id, cursor_filters = json.loads(payload)
        if cursor_filters != list(filters):
            raise ValueError
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
            is_demo=demo, created_at=workspace.created_at,
            subscription=describe_subscription(workspace.id, subscription, now=now),
        )

    def list_workspaces(
        self, *, search: str | None, active: bool | None, demo: bool | None, cursor: str | None, limit: int,
    ) -> PlatformWorkspacePage:
        search = search.strip() or None if search else None
        filters = (search, active, demo)
        before = _decode_cursor(cursor, filters) if cursor else None
        now = datetime.now(UTC)
        rows = self.workspaces.list_workspaces(search=search, active=active, demo=demo, before=before, limit=limit + 1)
        items = [self._project(row, now) for row in rows[:limit]]
        return PlatformWorkspacePage(
            items=items, as_of=now,
            next_cursor=_encode_cursor(items[-1], filters) if len(rows) > limit else None,
        )

    def get_workspace(self, workspace_id: UUID) -> PlatformWorkspaceDetail | None:
        row = self.workspaces.get_workspace(workspace_id)
        if row is None:
            return None
        workspace = row[0]
        return PlatformWorkspaceDetail(
            **self._project(row, datetime.now(UTC)).model_dump(),
            currency_code=workspace.currency_code, timezone=workspace.timezone,
            active_member_count=self.workspaces.count_active_members(workspace_id),
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


class PlatformAuditService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = PlatformAuditRepository(db)

    def record_read(
        self, actor_id: UUID, role: PlatformRole | None, action: str, outcome: str,
        workspace_id: UUID | None = None,
    ) -> None:
        if outcome == "DENIED" and self.audit.recently_denied(actor_id, action, datetime.now(UTC)):
            return
        self.audit.add(PlatformAuditEvent(
            actor_user_id=actor_id, actor_role=role, action=action, outcome=outcome, workspace_id=workspace_id
        ))
        self.db.commit()


def platform_identity(operator_id: UUID, role: PlatformRole) -> PlatformIdentity:
    return PlatformIdentity(operator_id=operator_id, role=role, capabilities=list(CAPABILITIES[role]))
