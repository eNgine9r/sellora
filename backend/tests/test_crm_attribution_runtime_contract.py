"""Reconciled live Raspberry contract: CRM orders and Meta metrics remain distinct."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.advertising_service import AdvertisingAnalyticsService, AdvertisingServiceError


def _service(order_rows, metric_rows):
    obj = AdvertisingAnalyticsService.__new__(AdvertisingAnalyticsService)
    repo = SimpleNamespace(
        group_crm_orders=lambda workspace, start, end: order_rows,
        group_visible_metrics=lambda workspace, start, end: metric_rows,
    )
    obj.repository = repo
    return obj


def test_live_report_counts_current_states_and_keeps_meta_metrics_distinct():
    campaign = uuid4()
    orders = [
        dict(campaign_id=campaign, campaign_name="Campaign A", campaign_status="ACTIVE", status="COMPLETED",
             payment_status="PAID", orders=2, revenue=Decimal("700")),
        dict(campaign_id=campaign, campaign_name="Campaign A", campaign_status="ACTIVE", status="CANCELLED",
             payment_status="PAID", orders=1, revenue=Decimal("300")),
        dict(campaign_id=campaign, campaign_name="Campaign A", campaign_status="ACTIVE", status="RETURNED",
             payment_status="REFUNDED", orders=1, revenue=Decimal("300")),
        dict(campaign_id=None, campaign_name=None, campaign_status=None, status="DELIVERED",
             payment_status="PAID", orders=1, revenue=Decimal("120")),
    ]
    metrics = [dict(campaign_id=campaign, campaign_name="Campaign A", campaign_status="ACTIVE",
                    spend=Decimal("200"), declared_orders=9, declared_revenue=Decimal("1400"))]
    report = _service(orders, metrics).crm_attribution(uuid4(), date(2026, 10, 1), date(2026, 10, 24))
    assert report.source == "crm_manual_campaign_link"
    assert report.date_basis == "order_created_at_utc"
    assert report.attributed_orders == 4
    assert report.unattributed_orders == 1
    assert report.totals.placed_orders == 5
    assert report.totals.paid_fulfilled_revenue == Decimal("820")
    assert report.unattributed.paid_fulfilled_revenue == Decimal("120")
    assert report.campaigns[0].paid_fulfilled_revenue == Decimal("700")
    assert report.campaigns[0].active_orders == 2
    assert report.campaigns[0].returned_refunded_orders == 1
    assert report.campaigns[0].cancelled_orders == 1
    assert report.campaigns[0].metric_declared_orders == 9
    assert report.campaigns[0].metric_declared_revenue == Decimal("1400")
    assert report.campaigns[0].spend == Decimal("200")
    assert report.campaigns[0].paid_fulfilled_revenue != report.campaigns[0].metric_declared_revenue


def test_orphan_campaign_order_counts_as_unattributed():
    orders=[dict(campaign_id=None, campaign_name=None, campaign_status=None, status="COMPLETED",
                 payment_status="PAID", orders=2, revenue=Decimal("400"))]
    report=_service(orders, []).crm_attribution(uuid4(), date(2026, 10, 1), date(2026, 10, 24))
    assert report.unattributed_orders == 2
    assert report.attributed_orders == 0
    assert report.campaigns == []
    assert report.attribution_coverage_percent == 0


@pytest.mark.parametrize("start,end", [(date(2026, 10, 25), date(2026, 10, 24)), (date(2026, 10, 1), date.max)])
def test_invalid_dates_rejected(start, end):
    with pytest.raises(AdvertisingServiceError):
        _service([], []).crm_attribution(uuid4(), start, end)
