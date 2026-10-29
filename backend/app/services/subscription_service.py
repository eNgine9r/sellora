from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.role import RoleName
from app.models.workspace_subscription import SubscriptionStatus, WorkspaceSubscription
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.subscription import SubscriptionDisplayStatus, SubscriptionStatusResponse


class SubscriptionAccessError(PermissionError):
    pass


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Subscription timestamps must have a timezone")
    return value.astimezone(UTC)


def describe_subscription(
    workspace_id: UUID,
    subscription: WorkspaceSubscription | None,
    *,
    now: datetime,
) -> SubscriptionStatusResponse:
    """Describe a half-open [start, end) term without persisting transitions.

    Absence is UNMANAGED, not an implicit trial or a paid/free entitlement.
    Cancel-at-period-end retains the remaining term; CANCELED is immediate.
    PAST_DUE has no grace entitlement until a separate policy is approved.
    """
    instant = _utc(now)
    if subscription is None:
        return SubscriptionStatusResponse(workspace_id=workspace_id, status=SubscriptionDisplayStatus.UNMANAGED)
    if subscription.workspace_id != workspace_id:
        raise SubscriptionAccessError("Workspace access denied")
    start, end = _utc(subscription.current_period_start), _utc(subscription.current_period_end)
    if end <= start:
        raise ValueError("Subscription term must have a positive duration")
    stored_status = SubscriptionStatus(subscription.status)
    status = SubscriptionDisplayStatus(stored_status.value)
    term_statuses = {SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING}
    has_current_term = stored_status in term_statuses and start <= instant < end
    if stored_status in term_statuses:
        if instant < start:
            status = SubscriptionDisplayStatus.PENDING
        elif instant >= end:
            status = SubscriptionDisplayStatus.EXPIRED
    return SubscriptionStatusResponse(
        workspace_id=workspace_id,
        status=status,
        plan_code=subscription.plan_code,
        current_period_start=start,
        current_period_end=end,
        cancel_at_period_end=subscription.cancel_at_period_end,
        has_current_term=has_current_term,
    )


class SubscriptionService:
    def __init__(self, db: Session) -> None:
        self.workspaces = WorkspaceRepository(db)
        self.subscriptions = SubscriptionRepository(db)

    def get_status(self, workspace_id: UUID, user_id: UUID) -> SubscriptionStatusResponse:
        membership = self.workspaces.get_active_membership(workspace_id, user_id)
        if membership is None or membership.role.name != RoleName.OWNER.value:
            raise SubscriptionAccessError("Workspace access denied")
        subscription = self.subscriptions.get_for_workspace(workspace_id)
        return describe_subscription(workspace_id, subscription, now=datetime.now(UTC))
