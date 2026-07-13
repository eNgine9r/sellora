from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.role import RoleName
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.onboarding_repository import OnboardingRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.onboarding import OnboardingNextAction, OnboardingStatusResponse, OnboardingSteps


class OnboardingAccessError(PermissionError):
    pass


class OnboardingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.onboarding = OnboardingRepository(db)
        self.workspaces = WorkspaceRepository(db)
        self.audit_logs = AuditLogRepository(db)

    def get_status(self, workspace_id: UUID, user_id: UUID) -> OnboardingStatusResponse:
        membership = self.workspaces.get_active_membership(workspace_id, user_id)
        if membership is None:
            raise OnboardingAccessError("Workspace access denied")
        workspace = membership.workspace
        steps = OnboardingSteps(
            workspace_configured=self.onboarding.has_configured_workspace(workspace),
            product_created=self.onboarding.has_active_product_and_variant(workspace_id),
            stock_added=self.onboarding.has_positive_stock_transaction(workspace_id),
            lead_or_customer_created=self.onboarding.has_lead_or_customer(workspace_id),
            order_created=self.onboarding.has_order(workspace_id),
        )
        completed = sum(1 for value in steps.model_dump().values() if value)
        total = len(steps.model_dump())
        suggested = self._next_action(steps)
        return OnboardingStatusResponse(
            workspace_id=workspace_id,
            role=RoleName(membership.role.name),
            is_demo_workspace=self.audit_logs.has_demo_workspace_provenance(workspace_id),
            is_empty=completed <= 1 and not any([steps.product_created, steps.stock_added, steps.lead_or_customer_created, steps.order_created]),
            progress_percent=round((completed / total) * 100),
            completed_steps=completed,
            total_steps=total,
            steps=steps,
            suggested_next_action=suggested,
        )

    @staticmethod
    def _next_action(steps: OnboardingSteps) -> OnboardingNextAction:
        if not steps.workspace_configured:
            return OnboardingNextAction.CONFIGURE_WORKSPACE
        if not steps.product_created:
            return OnboardingNextAction.ADD_PRODUCT
        if not steps.stock_added:
            return OnboardingNextAction.ADD_STOCK
        if not steps.lead_or_customer_created:
            return OnboardingNextAction.ADD_LEAD_OR_CUSTOMER
        if not steps.order_created:
            return OnboardingNextAction.CREATE_ORDER
        return OnboardingNextAction.EXPLORE_DASHBOARD
