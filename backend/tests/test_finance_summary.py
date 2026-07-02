from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.models.order import OrderStatus, PaymentStatus
from app.services.finance_service import FinanceService


class FakeFinanceRepository:
    def __init__(self, orders=None, shipments=None, ad_metrics=None):
        self.orders = orders or []
        self.shipments = shipments or []
        self.ad_metrics = ad_metrics or []
        self.calls = []

    def list_orders(self, workspace_id, start_at, end_at):
        self.calls.append(("orders", workspace_id, start_at, end_at))
        return [order for order in self.orders if order.workspace_id == workspace_id]

    def list_shipments(self, workspace_id, start_at, end_at):
        self.calls.append(("shipments", workspace_id, start_at, end_at))
        return [shipment for shipment in self.shipments if shipment.workspace_id == workspace_id]

    def list_manual_ad_metrics(self, workspace_id, start_at, end_at):
        self.calls.append(("ad_metrics", workspace_id, start_at, end_at))
        return [metric for metric in self.ad_metrics if metric.workspace_id == workspace_id and getattr(metric, "source_type", None) in (None, "manual", "csv_import") and getattr(metric, "external_source", None) != "meta_ads"]


def make_service(repository: FakeFinanceRepository) -> FinanceService:
    service = FinanceService.__new__(FinanceService)
    service.repository = repository
    return service


def order(workspace_id, revenue="100.00", status=OrderStatus.COMPLETED.value, payment_status=PaymentStatus.PAID.value, items=None, shipping_cost="0.00", cod_fee="0.00", other_cost="0.00"):
    return SimpleNamespace(
        id=uuid4(),
        workspace_id=workspace_id,
        status=status,
        payment_status=payment_status,
        revenue=Decimal(revenue),
        product_cost=Decimal("0.00"),
        shipping_cost=Decimal(shipping_cost),
        cod_fee=Decimal(cod_fee),
        other_cost=Decimal(other_cost),
        items=items or [],
    )


def item(line_total="100.00", line_cost="40.00"):
    return SimpleNamespace(line_total=Decimal(line_total), line_cost=Decimal(line_cost))


def shipment(workspace_id, order_id, shipping_cost="12.00"):
    return SimpleNamespace(workspace_id=workspace_id, order_id=order_id, shipping_cost=Decimal(shipping_cost))


def ad_metric(workspace_id, spend="25.00", source_type="manual", external_source=None):
    return SimpleNamespace(workspace_id=workspace_id, spend=Decimal(spend), source_type=source_type, external_source=external_source)


def test_finance_summary_calculates_core_metrics_from_orders_ad_metrics_and_shipments():
    workspace_id = uuid4()
    first_order = order(workspace_id, revenue="200.00", items=[item("120.00", "50.00"), item("80.00", "30.00")])
    second_order = order(workspace_id, revenue="100.00", payment_status=PaymentStatus.COD.value, items=[item("100.00", "45.00")], cod_fee="5.00")
    repo = FakeFinanceRepository(
        orders=[first_order, second_order],
        shipments=[shipment(workspace_id, first_order.id, "12.00"), shipment(workspace_id, second_order.id, "8.00")],
        ad_metrics=[ad_metric(workspace_id, "60.00", "csv_import")],
    )

    summary = make_service(repo).summary(workspace_id, date(2026, 7, 1), date(2026, 7, 31))

    assert summary.revenue == Decimal("300.00")
    assert summary.cogs == Decimal("125.00")
    assert summary.gross_profit == Decimal("175.00")
    assert summary.ad_spend == Decimal("60.00")
    assert summary.shipping_cost == Decimal("20.00")
    assert summary.other_expenses == Decimal("5.00")
    assert summary.net_profit == Decimal("90.00")
    assert summary.profit_margin == Decimal("30.00")
    assert summary.orders_count == 2
    assert summary.paid_orders_count == 2
    assert summary.average_order_value == Decimal("150.00")


def test_finance_summary_handles_zero_revenue_without_nan_or_infinity():
    workspace_id = uuid4()
    summary = make_service(FakeFinanceRepository()).summary(workspace_id)

    assert summary.revenue == Decimal("0.00")
    assert summary.profit_margin is None
    assert summary.average_order_value is None
    assert any(warning.code == "no_orders_in_period" for warning in summary.data_quality_warnings)


def test_finance_summary_warns_for_missing_product_and_shipment_costs():
    workspace_id = uuid4()
    repo = FakeFinanceRepository(orders=[order(workspace_id, revenue="90.00", items=[item("90.00", "0.00")])])

    summary = make_service(repo).summary(workspace_id)

    codes = {warning.code for warning in summary.data_quality_warnings}
    assert "missing_product_cost" in codes
    assert "missing_shipment_cost" in codes


def test_finance_summary_keeps_workspace_isolation_and_manual_csv_ad_spend_only():
    workspace_id = uuid4()
    other_workspace_id = uuid4()
    own_order = order(workspace_id, revenue="100.00", items=[item("100.00", "40.00")])
    other_order = order(other_workspace_id, revenue="999.00", items=[item("999.00", "1.00")])
    repo = FakeFinanceRepository(
        orders=[own_order, other_order],
        shipments=[shipment(workspace_id, own_order.id, "10.00"), shipment(other_workspace_id, other_order.id, "99.00")],
        ad_metrics=[ad_metric(workspace_id, "20.00"), ad_metric(workspace_id, "999.00", "meta_sync", "meta_ads"), ad_metric(other_workspace_id, "999.00")],
    )

    summary = make_service(repo).summary(workspace_id)

    assert summary.revenue == Decimal("100.00")
    assert summary.ad_spend == Decimal("20.00")
    assert all(call[1] == workspace_id for call in repo.calls)


def test_finance_summary_excludes_cancelled_returned_and_refunded_orders_from_revenue():
    workspace_id = uuid4()
    repo = FakeFinanceRepository(
        orders=[
            order(workspace_id, revenue="100.00", items=[item("100.00", "40.00")]),
            order(workspace_id, revenue="200.00", status=OrderStatus.CANCELLED.value, items=[item("200.00", "80.00")]),
            order(workspace_id, revenue="300.00", status=OrderStatus.RETURNED.value, items=[item("300.00", "120.00")]),
            order(workspace_id, revenue="400.00", payment_status=PaymentStatus.REFUNDED.value, items=[item("400.00", "160.00")]),
        ]
    )

    summary = make_service(repo).summary(workspace_id)

    assert summary.revenue == Decimal("100.00")
    assert summary.orders_count == 1
    assert summary.refunds == Decimal("0.00")
    assert any(warning.code == "cancelled_refunded_orders_excluded" for warning in summary.data_quality_warnings)


def test_finance_summary_endpoint_is_read_only_and_has_no_meta_live_dependency():
    backend_root = Path(__file__).resolve().parents[1]
    source_paths = [
        backend_root / "app/api/v1/finance.py",
        backend_root / "app/repositories/finance_repository.py",
        backend_root / "app/services/finance_service.py",
    ]
    source = "\n".join(path.read_text() for path in source_paths)

    assert ".commit(" not in source
    assert ".flush(" not in source
    assert ".add(" not in source
    assert "httpx" not in source
    assert "requests" not in source
    assert "facebook.com" not in source
    assert "graph.facebook.com" not in source
