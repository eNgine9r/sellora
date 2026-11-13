from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, case, func, or_, select, text
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.platform_admin import PlatformAuditEvent, PlatformGrant
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_subscription import SubscriptionStatus, WorkspaceSubscription
from app.models.workspace_user import WorkspaceUser
from app.repositories.audit_log_repository import DEMO_WORKSPACE_CREATE_ACTION
from app.schemas.subscription import SubscriptionDisplayStatus


class PlatformGrantRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, user_id: UUID) -> PlatformGrant | None:
        return self.db.get(PlatformGrant, user_id)

    def lock_changes(self) -> None:
        # Serializes bootstrap and grant administration across processes.
        self.db.execute(text("SELECT pg_advisory_xact_lock(4817925031171101)"))

    def add(self, grant: PlatformGrant) -> None:
        self.db.add(grant)


class PlatformAuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, event: PlatformAuditEvent) -> None:
        self.db.add(event)

    def has_bootstrap(self) -> bool:
        return self.db.scalar(select(PlatformAuditEvent.id).where(PlatformAuditEvent.action == "BOOTSTRAP").limit(1)) is not None

    def recently_denied(self, actor_id: UUID, action: str, now: datetime) -> bool:
        statement = select(PlatformAuditEvent.id).where(
            PlatformAuditEvent.actor_user_id == actor_id,
            PlatformAuditEvent.action == action,
            PlatformAuditEvent.outcome == "DENIED",
            PlatformAuditEvent.created_at >= now - timedelta(minutes=1),
        ).limit(1)
        return self.db.scalar(statement) is not None


class PlatformWorkspaceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _is_demo():
        return select(AuditLog.id).where(
            AuditLog.workspace_id == Workspace.id,
            AuditLog.entity_type == "Workspace",
            AuditLog.entity_id == func.cast(Workspace.id, AuditLog.entity_id.type),
            AuditLog.action == DEMO_WORKSPACE_CREATE_ACTION,
        ).exists()

    def _with_subscription(self):
        return select(Workspace, self._is_demo().label("is_demo"), WorkspaceSubscription).outerjoin(
            WorkspaceSubscription, WorkspaceSubscription.workspace_id == Workspace.id
        )

    def list_workspaces(
        self, *, search: str | None, active: bool | None, demo: bool | None,
        before: tuple[datetime, UUID] | None, limit: int,
        subscription_status: SubscriptionDisplayStatus | None, now: datetime,
    ):
        statement = self._with_subscription()
        if search:
            filters = [Workspace.name.icontains(search, autoescape=True), Workspace.slug.icontains(search, autoescape=True)]
            try:
                filters.append(Workspace.id == UUID(search))
            except ValueError:
                pass
            statement = statement.where(or_(*filters))
        if active is not None:
            statement = statement.where(Workspace.is_active == active)
        if demo is not None:
            statement = statement.where(self._is_demo() if demo else ~self._is_demo())
        if subscription_status is not None:
            subscription = WorkspaceSubscription
            # Match describe_subscription at the same instant used to project the results.
            has_term = subscription.status.in_((SubscriptionStatus.ACTIVE.value, SubscriptionStatus.TRIALING.value))
            display_status = case(
                (subscription.workspace_id.is_(None), SubscriptionDisplayStatus.UNMANAGED.value),
                (and_(has_term, subscription.current_period_start > now), SubscriptionDisplayStatus.PENDING.value),
                (and_(has_term, subscription.current_period_end <= now), SubscriptionDisplayStatus.EXPIRED.value),
                else_=subscription.status,
            )
            statement = statement.where(display_status == subscription_status.value)
        if before:
            created_at, workspace_id = before
            statement = statement.where(or_(
                Workspace.created_at < created_at,
                and_(Workspace.created_at == created_at, Workspace.id < workspace_id),
            ))
        return self.db.execute(
            statement.order_by(Workspace.created_at.desc(), Workspace.id.desc()).limit(limit)
        ).all()

    def get_workspace(self, workspace_id: UUID):
        return self.db.execute(self._with_subscription().where(Workspace.id == workspace_id)).one_or_none()

    def exists(self, workspace_id: UUID) -> bool:
        return self.db.scalar(select(Workspace.id).where(Workspace.id == workspace_id)) is not None

    def count_active_members(self, workspace_id: UUID) -> int:
        return self.db.execute(
            select(func.count()).select_from(WorkspaceUser).join(User, User.id == WorkspaceUser.user_id).where(
                WorkspaceUser.workspace_id == workspace_id,
                WorkspaceUser.is_active.is_(True),
                WorkspaceUser.deleted_at.is_(None),
                User.is_active.is_(True),
            )
        ).scalar_one()

    def summarize(self, now: datetime):
        current_term = and_(
            WorkspaceSubscription.status.in_((SubscriptionStatus.ACTIVE.value, SubscriptionStatus.TRIALING.value)),
            WorkspaceSubscription.current_period_start <= now,
            WorkspaceSubscription.current_period_end > now,
        )
        return self.db.execute(select(
            func.count(Workspace.id).label("total_workspaces"),
            func.count(Workspace.id).filter(Workspace.is_active).label("enabled_workspaces"),
            func.count(Workspace.id).filter(self._is_demo()).label("demo_workspaces"),
            func.count(Workspace.id).filter(current_term).label("workspaces_with_current_term"),
        ).select_from(Workspace).outerjoin(
            WorkspaceSubscription, WorkspaceSubscription.workspace_id == Workspace.id
        )).mappings().one()
