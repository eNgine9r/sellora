from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.finance_adjustment import FinanceAdjustmentCategory, FinanceAdjustmentType
from app.schemas.finance import FinanceAdjustmentCreate
from app.services.finance_service import FinanceService, FinanceServiceError


class FakeFinanceRepo:
    def __init__(self, workspace_id, other_workspace_order_id) -> None:
        self.workspace_id = workspace_id
        self.other_workspace_order_id = other_workspace_order_id
        self.created = []

    def order_exists(self, workspace_id, order_id) -> bool:
        return workspace_id == self.workspace_id and order_id != self.other_workspace_order_id

    def create_adjustment(self, adjustment):
        self.created.append(adjustment)
        adjustment.id = adjustment.id or uuid4()
        return adjustment

    def list_orders(self, workspace_id, start_at, end_at):
        assert workspace_id == self.workspace_id
        return []

    def list_shipments(self, workspace_id, start_at, end_at):
        assert workspace_id == self.workspace_id
        return []

    def list_manual_ad_metrics(self, workspace_id, start_at, end_at):
        assert workspace_id == self.workspace_id
        return []

    def list_adjustments_for_period(self, workspace_id, start_at, end_at):
        assert workspace_id == self.workspace_id
        return []


class FakeDb:
    def commit(self) -> None:
        pass

    def refresh(self, model) -> None:
        pass


def test_finance_adjustment_rejects_cross_workspace_order_reference() -> None:
    workspace_a = uuid4()
    workspace_b_order = uuid4()
    service = FinanceService.__new__(FinanceService)
    service.db = FakeDb()
    service.repository = FakeFinanceRepo(workspace_a, workspace_b_order)

    with pytest.raises(FinanceServiceError, match="Order not found in workspace"):
        service.create_adjustment(
            workspace_a,
            FinanceAdjustmentCreate(
                type=FinanceAdjustmentType.EXPENSE,
                category=FinanceAdjustmentCategory.OTHER,
                amount=Decimal("100.00"),
                currency="UAH",
                occurred_at=datetime.now(UTC),
                title="Synthetic security adjustment",
                order_id=workspace_b_order,
            ),
            actor_user_id=uuid4(),
        )

    assert service.repository.created == []


def test_finance_summary_uses_workspace_scoped_repository_calls_only() -> None:
    workspace_a = uuid4()
    service = FinanceService.__new__(FinanceService)
    service.db = FakeDb()
    service.repository = FakeFinanceRepo(workspace_a, uuid4())

    summary = service.summary(workspace_a)

    assert summary.revenue == Decimal("0.00")
    assert summary.orders_count == 0
    assert summary.data_quality_warnings
