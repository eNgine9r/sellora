from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import UniqueConstraint
from sqlalchemy.exc import IntegrityError

from app.api.v1 import orders as orders_api
from app.models.order import Order
from app.schemas.order import OrderCreate, OrderItemCreate
from app.services.order_service import OrderService

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "202607130021_workspace_scoped_order_numbers.py"
)
MIGRATION_TEXT = MIGRATION_PATH.read_text(encoding="utf-8")


class FirstOrderSequence:
    def next_sequence_for_year(self, workspace_id, year):
        return 1


class RollbackTrackingDb:
    def __init__(self) -> None:
        self.rollback_called = False

    def rollback(self) -> None:
        self.rollback_called = True


def test_order_model_uses_workspace_scoped_number_uniqueness() -> None:
    unique_constraints = [
        constraint
        for constraint in Order.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    ]
    constrained_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in unique_constraints
    }

    assert ("workspace_id", "order_number") in constrained_columns
    assert ("order_number",) not in constrained_columns
    assert Order.__table__.c.order_number.unique is not True


def test_two_workspaces_can_generate_the_same_first_local_order_number() -> None:
    service = OrderService.__new__(OrderService)
    service.orders = FirstOrderSequence()

    first_workspace_number = service._generate_order_number(uuid4())
    second_workspace_number = service._generate_order_number(uuid4())

    assert first_workspace_number == second_workspace_number
    assert first_workspace_number.endswith("-000001")


def test_workspace_scoped_order_number_migration_contract() -> None:
    assert MIGRATION_PATH.exists()
    assert 'revision: str = "202607130021"' in MIGRATION_TEXT
    assert 'down_revision: str | None = "202607080020"' in MIGRATION_TEXT
    assert 'OLD_CONSTRAINT = "uq_orders_order_number"' in MIGRATION_TEXT
    assert 'NEW_CONSTRAINT = "uq_orders_workspace_id_order_number"' in MIGRATION_TEXT
    assert 'op.drop_constraint(OLD_CONSTRAINT, "orders", type_="unique")' in MIGRATION_TEXT
    assert '["workspace_id", "order_number"]' in MIGRATION_TEXT
    assert 'op.drop_constraint(NEW_CONSTRAINT, "orders", type_="unique")' in MIGRATION_TEXT


def test_order_create_integrity_error_rolls_back_and_returns_conflict(monkeypatch) -> None:
    db = RollbackTrackingDb()

    def raise_integrity_error(self, workspace_id, payload, actor_user_id):
        raise IntegrityError("INSERT INTO orders", {}, Exception("duplicate order number"))

    monkeypatch.setattr(orders_api.OrderService, "create", raise_integrity_error)

    payload = OrderCreate(
        customer_id=uuid4(),
        items=[
            OrderItemCreate(
                product_variant_id=uuid4(),
                quantity=1,
                unit_price=100,
                unit_cost=40,
            )
        ],
    )

    with pytest.raises(HTTPException) as exc_info:
        orders_api.create_order(
            payload,
            uuid4(),
            SimpleNamespace(id=uuid4()),
            db,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Order number conflict in this workspace. Please retry."
    assert db.rollback_called is True
