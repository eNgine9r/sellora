from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.role import RoleName
from app.schemas.onboarding import OnboardingNextAction
from app.services.onboarding_service import OnboardingAccessError, OnboardingService


class FakeWorkspaces:
    def __init__(self, membership):
        self.membership = membership

    def get_active_membership(self, workspace_id, user_id):
        if self.membership and self.membership.workspace_id == workspace_id and self.membership.user_id == user_id:
            return self.membership
        return None


class FakeAuditLogs:
    def __init__(self, demo_workspace_ids=None):
        self.demo_workspace_ids = set(demo_workspace_ids or [])

    def has_demo_workspace_provenance(self, workspace_id, *, creator_user_id=None):
        return workspace_id in self.demo_workspace_ids


class FakeOnboarding:
    def __init__(self, *, configured=True, product=False, stock=False, lead=False, order=False):
        self.configured = configured
        self.product = product
        self.stock = stock
        self.lead = lead
        self.order = order

    def has_configured_workspace(self, _workspace):
        return self.configured

    def has_active_product_and_variant(self, _workspace_id):
        return self.product

    def has_positive_stock_transaction(self, _workspace_id):
        return self.stock

    def has_lead_or_customer(self, _workspace_id):
        return self.lead

    def has_order(self, _workspace_id):
        return self.order


def _membership(workspace_id, user_id, role=RoleName.OWNER, slug="shop-a"):
    return SimpleNamespace(
        workspace_id=workspace_id,
        user_id=user_id,
        role=SimpleNamespace(name=role.value),
        workspace=SimpleNamespace(id=workspace_id, name="Shop A", slug=slug, currency_code="UAH", timezone="Europe/Kyiv", is_active=True),
    )


def _service(membership, onboarding, *, demo=False):
    service = OnboardingService.__new__(OnboardingService)
    service.workspaces = FakeWorkspaces(membership)
    service.onboarding = onboarding
    service.audit_logs = FakeAuditLogs([membership.workspace_id] if membership and demo else [])
    return service


def test_empty_workspace_status_is_workspace_scoped_and_actionable() -> None:
    workspace_id = uuid4()
    user_id = uuid4()
    service = _service(_membership(workspace_id, user_id), FakeOnboarding())

    status = service.get_status(workspace_id, user_id)

    assert status.workspace_id == workspace_id
    assert status.role == RoleName.OWNER
    assert status.is_empty is True
    assert status.completed_steps == 1
    assert status.progress_percent == 20
    assert status.steps.product_created is False
    assert status.suggested_next_action == OnboardingNextAction.ADD_PRODUCT


def test_partial_workspace_status_uses_real_completion_conditions() -> None:
    workspace_id = uuid4()
    user_id = uuid4()
    service = _service(_membership(workspace_id, user_id, RoleName.MANAGER), FakeOnboarding(product=True, stock=True, lead=True))

    status = service.get_status(workspace_id, user_id)

    assert status.role == RoleName.MANAGER
    assert status.is_empty is False
    assert status.completed_steps == 4
    assert status.suggested_next_action == OnboardingNextAction.CREATE_ORDER


def test_completed_demo_workspace_status_is_labeled_by_provenance() -> None:
    workspace_id = uuid4()
    user_id = uuid4()
    service = _service(
        _membership(workspace_id, user_id, RoleName.ANALYST, slug="ordinary-looking-slug"),
        FakeOnboarding(product=True, stock=True, lead=True, order=True),
        demo=True,
    )

    status = service.get_status(workspace_id, user_id)

    assert status.role == RoleName.ANALYST
    assert status.is_demo_workspace is True
    assert status.progress_percent == 100
    assert status.suggested_next_action == OnboardingNextAction.EXPLORE_DASHBOARD


def test_demo_looking_slug_without_provenance_is_not_demo() -> None:
    workspace_id = uuid4()
    user_id = uuid4()
    service = _service(
        _membership(workspace_id, user_id, slug="demo-sellora-forged"),
        FakeOnboarding(product=True),
        demo=False,
    )

    assert service.get_status(workspace_id, user_id).is_demo_workspace is False


def test_status_denies_missing_membership() -> None:
    service = _service(None, FakeOnboarding())

    with pytest.raises(OnboardingAccessError):
        service.get_status(uuid4(), uuid4())
