from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.dependencies.rbac import require_min_role
from app.models.finance_adjustment import FinanceAdjustment, FinanceAdjustmentCategory, FinanceAdjustmentType
from app.models.role import RoleName
from app.schemas.finance import FinanceAdjustmentCreate, FinanceAdjustmentUpdate
from app.services.finance_service import FinanceService, FinanceServiceError


class FakeDb:
    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, obj) -> None:
        pass


class FakeAdjustmentRepo:
    def __init__(self, workspace_id):
        self.workspace_id = workspace_id
        self.adjustments: list[FinanceAdjustment] = []

    def list_adjustments(self, workspace_id, start_at=None, end_at=None, adjustment_type=None, category=None, limit=50, offset=0):
        rows = [item for item in self.adjustments if item.workspace_id == workspace_id and item.deleted_at is None]
        if start_at is not None:
            rows = [item for item in rows if item.occurred_at >= start_at]
        if end_at is not None:
            rows = [item for item in rows if item.occurred_at <= end_at]
        if adjustment_type:
            rows = [item for item in rows if item.type == adjustment_type]
        if category:
            rows = [item for item in rows if item.category == category]
        total = len(rows)
        return rows[offset:offset + limit], total

    def get_adjustment(self, workspace_id, adjustment_id):
        for item in self.adjustments:
            if item.workspace_id == workspace_id and item.id == adjustment_id and item.deleted_at is None:
                return item
        return None

    def create_adjustment(self, adjustment):
        now = datetime.now(UTC)
        adjustment.id = adjustment.id or uuid4()
        adjustment.created_at = now
        adjustment.updated_at = now
        adjustment.source = "MANUAL"
        adjustment.deleted_at = None
        adjustment.deleted_by = None
        self.adjustments.append(adjustment)
        return adjustment

    def order_exists(self, workspace_id, order_id):
        return order_id == getattr(self, "allowed_order_id", None)


def make_service(workspace_id):
    service = FinanceService.__new__(FinanceService)
    service.db = FakeDb()
    service.repository = FakeAdjustmentRepo(workspace_id)
    return service


def payload(type=FinanceAdjustmentType.EXPENSE, category=FinanceAdjustmentCategory.PACKAGING, amount="25.00", title="Packaging"):
    return FinanceAdjustmentCreate(type=type, category=category, amount=Decimal(amount), currency="UAH", occurred_at=datetime(2026, 7, 2, tzinfo=UTC), title=title, description="Synthetic manual finance adjustment")


@pytest.mark.parametrize("adjustment_type", [FinanceAdjustmentType.EXPENSE, FinanceAdjustmentType.REFUND, FinanceAdjustmentType.DISCOUNT, FinanceAdjustmentType.FEE])
def test_create_manual_finance_adjustment_types(adjustment_type):
    workspace_id = uuid4()
    service = make_service(workspace_id)

    created = service.create_adjustment(workspace_id, payload(type=adjustment_type, category=FinanceAdjustmentCategory.OTHER), uuid4())

    assert created.workspace_id == workspace_id
    assert created.type == adjustment_type
    assert created.amount == Decimal("25.00")
    assert created.source == "MANUAL"
    assert service.db.commits == 1


def test_create_adjustment_rejects_cross_workspace_order_link():
    workspace_id = uuid4()
    service = make_service(workspace_id)

    with pytest.raises(FinanceServiceError):
        service.create_adjustment(workspace_id, payload().model_copy(update={"order_id": uuid4()}), uuid4())


def test_create_adjustment_accepts_workspace_scoped_order_link():
    workspace_id = uuid4()
    service = make_service(workspace_id)
    order_id = uuid4()
    service.repository.allowed_order_id = order_id

    created = service.create_adjustment(workspace_id, payload().model_copy(update={"order_id": order_id}), uuid4())

    assert created.order_id == order_id


def test_create_rejects_non_positive_amount():
    with pytest.raises(ValidationError):
        payload(amount="0.00")


def test_list_adjustments_filters_by_workspace_period_type_and_category():
    workspace_id = uuid4()
    other_workspace_id = uuid4()
    service = make_service(workspace_id)
    actor_id = uuid4()
    own = service.create_adjustment(workspace_id, payload(type=FinanceAdjustmentType.EXPENSE, category=FinanceAdjustmentCategory.PACKAGING, title="Packaging"), actor_id)
    service.create_adjustment(workspace_id, payload(type=FinanceAdjustmentType.FEE, category=FinanceAdjustmentCategory.PAYMENT_FEE, title="Fee"), actor_id)
    service.repository.create_adjustment(FinanceAdjustment(workspace_id=other_workspace_id, type="EXPENSE", category="PACKAGING", amount=Decimal("999.00"), currency="UAH", occurred_at=datetime(2026, 7, 2, tzinfo=UTC), title="Other workspace", source="MANUAL"))

    listed = service.list_adjustments(workspace_id, date(2026, 7, 1), date(2026, 7, 31), FinanceAdjustmentType.EXPENSE, FinanceAdjustmentCategory.PACKAGING)

    assert listed.total == 1
    assert listed.items[0].id == own.id
    assert listed.items[0].workspace_id == workspace_id


def test_update_adjustment_and_soft_delete():
    workspace_id = uuid4()
    service = make_service(workspace_id)
    created = service.create_adjustment(workspace_id, payload(), uuid4())

    updated = service.update_adjustment(workspace_id, created.id, FinanceAdjustmentUpdate(amount=Decimal("45.00"), title="Updated packaging"))
    service.delete_adjustment(workspace_id, created.id, uuid4())

    assert updated.amount == Decimal("45.00")
    assert service.repository.adjustments[0].deleted_at is not None
    assert service.db.commits == 3


def test_cross_workspace_update_is_rejected():
    workspace_id = uuid4()
    other_workspace_id = uuid4()
    service = make_service(workspace_id)
    created = service.create_adjustment(workspace_id, payload(), uuid4())

    with pytest.raises(FinanceServiceError):
        service.update_adjustment(other_workspace_id, created.id, FinanceAdjustmentUpdate(title="Forbidden"))


def test_analyst_read_only_and_manager_write_policy_is_enforced_by_rbac_dependencies():
    analyst_guard = require_min_role(RoleName.ANALYST)
    manager_guard = require_min_role(RoleName.MANAGER)
    owner_user = type("User", (), {"workspaces": [type("Membership", (), {"workspace_id": uuid4(), "workspace": type("Workspace", (), {"is_active": True})(), "role": type("Role", (), {"name": RoleName.ANALYST.value})()})()]})()
    workspace_id = owner_user.workspaces[0].workspace_id

    assert analyst_guard(owner_user, workspace_id) is owner_user
    with pytest.raises(HTTPException):
        manager_guard(owner_user, workspace_id)


def test_finance_adjustments_migration_contract_is_safe():
    migration = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "202607020017_finance_adjustments.py"
    text = migration.read_text()

    assert 'revision: str = "202607020017"' in text
    assert 'down_revision: str | None = "202607010016"' in text
    assert "finance_adjustments" in text
    assert "workspace_id" in text
    assert "occurred_at" in text
    assert "order_id" in text
    assert "deleted_at" in text
    assert "amount > 0" in text
    assert "op.drop_table(\"finance_adjustments\")" in text
    assert "Meta" not in text
