from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.dependencies.rbac import require_min_role
from app.models.ad_campaign import AdCampaign, AdCampaignStatus
from app.models.ad_metric import AdMetric
from app.models.role import RoleName
from app.schemas.advertising import AdCampaignCreate, AdCampaignUpdate, AdMetricCreate
from app.services.advertising_service import AdCampaignService, AdMetricService, AdvertisingAnalyticsService, AdvertisingServiceError


class FakeDb:
    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, obj) -> None:
        pass


class FakeCampaignRepo:
    def __init__(self, workspace_id):
        self.workspace_id = workspace_id
        self.campaign = AdCampaign(id=uuid4(), workspace_id=workspace_id, name="Synthetic Campaign", platform="INSTAGRAM", status="ACTIVE", objective="MESSAGES", budget_type="MANUAL")
        self.created = []

    def list(self, workspace_id):
        return [self.campaign] if workspace_id == self.workspace_id and self.campaign.deleted_at is None else []

    def get(self, workspace_id, campaign_id):
        return self.campaign if workspace_id == self.workspace_id and campaign_id == self.campaign.id and self.campaign.deleted_at is None else None

    def create(self, campaign):
        campaign.id = campaign.id or uuid4()
        self.created.append(campaign)
        self.campaign = campaign
        return campaign


class FakeMetricRepo:
    def __init__(self, workspace_id, campaign_id):
        self.workspace_id = workspace_id
        self.campaign_id = campaign_id
        self.metric = None

    def list(self, workspace_id):
        return [self.metric] if self.metric and workspace_id == self.workspace_id and self.metric.deleted_at is None else []

    def list_for_campaign(self, workspace_id, campaign_id):
        return [self.metric] if self.metric and workspace_id == self.workspace_id and campaign_id == self.campaign_id and self.metric.deleted_at is None else []

    def get(self, workspace_id, metric_id):
        return self.metric if self.metric and workspace_id == self.workspace_id and self.metric.id == metric_id and self.metric.deleted_at is None else None

    def find_by_campaign_date(self, workspace_id, campaign_id, metric_date):
        if self.metric and workspace_id == self.workspace_id and campaign_id == self.campaign_id and metric_date == self.metric.metric_date and self.metric.deleted_at is None:
            return self.metric
        return None

    def create(self, metric):
        metric.id = metric.id or uuid4()
        self.metric = metric
        return metric


class FakeAuditLogs:
    def __init__(self) -> None:
        self.actions = []

    def create(self, **kwargs):
        self.actions.append(kwargs["action"])
        return SimpleNamespace(**kwargs)


class FakeAnalyticsRepo:
    def __init__(self, workspace_id, other_workspace_id):
        self.workspace_id = workspace_id
        self.campaign = AdCampaign(id=uuid4(), workspace_id=workspace_id, name="Synthetic Campaign", platform="INSTAGRAM", status="ACTIVE", objective="MESSAGES", budget_type="MANUAL")
        self.other_campaign = AdCampaign(id=uuid4(), workspace_id=other_workspace_id, name="Other Synthetic Campaign", platform="META", status="ACTIVE", objective="SALES", budget_type="MANUAL")
        today = date.today()
        self.metrics = [
            AdMetric(id=uuid4(), workspace_id=workspace_id, campaign_id=self.campaign.id, campaign=self.campaign, metric_date=today, spend=Decimal("100"), impressions=10000, reach=8000, clicks=500, messages=100, leads=25, orders=5, revenue=Decimal("500"), net_profit=Decimal("150")),
            AdMetric(id=uuid4(), workspace_id=workspace_id, campaign_id=self.campaign.id, campaign=self.campaign, metric_date=today - timedelta(days=1), spend=Decimal("50"), impressions=5000, reach=4000, clicks=250, messages=50, leads=10, orders=0, revenue=Decimal("0"), net_profit=Decimal("-25")),
            AdMetric(id=uuid4(), workspace_id=other_workspace_id, campaign_id=self.other_campaign.id, campaign=self.other_campaign, metric_date=today, spend=Decimal("999"), impressions=1, reach=1, clicks=1, messages=1, leads=1, orders=1, revenue=Decimal("999"), net_profit=Decimal("999")),
        ]

    def list_metrics(self, workspace_id, start_date, end_date):
        return [metric for metric in self.metrics if metric.workspace_id == workspace_id and start_date <= metric.metric_date <= end_date]


def _campaign_service():
    workspace_id = uuid4()
    service = AdCampaignService.__new__(AdCampaignService)
    service.db = FakeDb()
    service.campaigns = FakeCampaignRepo(workspace_id)
    service.audit_logs = FakeAuditLogs()
    return service, workspace_id


def _metric_service():
    campaign_service, workspace_id = _campaign_service()
    service = AdMetricService.__new__(AdMetricService)
    service.db = FakeDb()
    service.campaigns = campaign_service.campaigns
    service.metrics = FakeMetricRepo(workspace_id, campaign_service.campaigns.campaign.id)
    service.audit_logs = FakeAuditLogs()
    return service, workspace_id, campaign_service.campaigns.campaign.id


def _analytics_service():
    workspace_id = uuid4()
    other_workspace_id = uuid4()
    service = AdvertisingAnalyticsService.__new__(AdvertisingAnalyticsService)
    service.repository = FakeAnalyticsRepo(workspace_id, other_workspace_id)
    return service, workspace_id, other_workspace_id


def test_campaign_creation_update_and_soft_delete() -> None:
    service, workspace_id = _campaign_service()
    actor_id = uuid4()
    campaign = service.create(workspace_id, AdCampaignCreate(name="Synthetic Awareness"), actor_id)
    assert campaign.status == AdCampaignStatus.ACTIVE.value
    assert "AD_CAMPAIGN_CREATE" in service.audit_logs.actions

    updated = service.update(workspace_id, campaign.id, AdCampaignUpdate(status=AdCampaignStatus.PAUSED), actor_id)
    assert updated.status == AdCampaignStatus.PAUSED.value
    assert "AD_CAMPAIGN_UPDATE" in service.audit_logs.actions

    service.delete(workspace_id, campaign.id, actor_id)
    assert campaign.deleted_at is not None
    assert campaign.deleted_by == actor_id
    assert campaign.status == AdCampaignStatus.ARCHIVED.value
    assert "AD_CAMPAIGN_DELETE" in service.audit_logs.actions


def test_metric_creation_duplicate_and_validation() -> None:
    service, workspace_id, campaign_id = _metric_service()
    actor_id = uuid4()
    payload = AdMetricCreate(campaign_id=campaign_id, metric_date=date.today(), spend=Decimal("100"), impressions=1000, clicks=100, leads=10, orders=2, revenue=Decimal("300"), net_profit=Decimal("120"))

    metric = service.create(workspace_id, payload, actor_id)
    assert metric.cpa == Decimal("50.00")
    assert metric.cpl == Decimal("10.00")
    assert metric.cpc == Decimal("1.00")
    assert metric.cpm == Decimal("100.00")
    assert metric.ctr == Decimal("10.00")
    assert metric.roas == Decimal("3.00")
    assert metric.roi == Decimal("120.00")
    assert "AD_METRIC_CREATE" in service.audit_logs.actions

    with pytest.raises(AdvertisingServiceError):
        service.create(workspace_id, payload, actor_id)
    with pytest.raises(ValidationError):
        AdMetricCreate(campaign_id=campaign_id, metric_date=date.today(), spend=Decimal("-1"))


def test_summary_calculations_and_workspace_isolation() -> None:
    service, workspace_id, other_workspace_id = _analytics_service()
    summary = service.summary(workspace_id, None, None, include_sensitive=True)

    assert summary.total_spend == Decimal("150")
    assert summary.total_impressions == 15000
    assert summary.total_reach == 12000
    assert summary.total_clicks == 750
    assert summary.total_messages == 150
    assert summary.total_leads == 35
    assert summary.total_orders == 5
    assert summary.total_revenue == Decimal("500")
    assert summary.total_net_profit == Decimal("125")
    assert summary.average_cpa == Decimal("30.00")
    assert summary.average_cpl == Decimal("4.29")
    assert summary.average_cpc == Decimal("0.20")
    assert summary.average_cpm == Decimal("10.00")
    assert summary.average_ctr == Decimal("5.00")
    assert summary.roas == Decimal("3.33")
    assert summary.roi == Decimal("83.33")

    isolated = service.summary(other_workspace_id, None, None, include_sensitive=True)
    assert isolated.total_spend == Decimal("999")


def test_campaign_performance_and_trend_sensitive_filtering() -> None:
    service, workspace_id, _other_workspace_id = _analytics_service()
    owner_rows = service.campaign_performance(workspace_id, None, None, limit=10, include_sensitive=True)
    manager_rows = service.campaign_performance(workspace_id, None, None, limit=10, include_sensitive=False)
    owner_trend = service.trend(workspace_id, None, None, include_sensitive=True)
    manager_trend = service.trend(workspace_id, None, None, include_sensitive=False)

    assert owner_rows[0].net_profit == Decimal("125")
    assert owner_rows[0].roi == Decimal("83.33")
    assert manager_rows[0].net_profit is None
    assert manager_rows[0].roi is None
    assert any(point.net_profit == Decimal("150") for point in owner_trend)
    assert all(point.net_profit is None for point in manager_trend)


def test_owner_analyst_and_manager_rbac_read_access() -> None:
    workspace_id = uuid4()
    owner = _user(workspace_id, RoleName.OWNER)
    analyst = _user(workspace_id, RoleName.ANALYST)
    manager = _user(workspace_id, RoleName.MANAGER)
    guard = require_min_role(RoleName.ANALYST)

    assert guard(owner, workspace_id) is owner
    assert guard(analyst, workspace_id) is analyst
    assert guard(manager, workspace_id) is manager
    assert service_sensitive_for_role(RoleName.OWNER)
    assert service_sensitive_for_role(RoleName.ANALYST)
    assert not service_sensitive_for_role(RoleName.MANAGER)


def test_deleted_metric_audit_action() -> None:
    service, workspace_id, campaign_id = _metric_service()
    actor_id = uuid4()
    payload = AdMetricCreate(campaign_id=campaign_id, metric_date=date.today(), spend=Decimal("1"))
    service.create(workspace_id, payload, actor_id)
    metric_id = service.metrics.metric.id

    service.delete(workspace_id, metric_id, actor_id)

    assert service.metrics.metric.deleted_at is not None
    assert "AD_METRIC_DELETE" in service.audit_logs.actions


def _user(workspace_id, role_name):
    return SimpleNamespace(workspaces=[SimpleNamespace(workspace_id=workspace_id, workspace=SimpleNamespace(is_active=True), role=SimpleNamespace(name=role_name.value))])


def service_sensitive_for_role(role_name: RoleName) -> bool:
    return role_name in {RoleName.OWNER, RoleName.ANALYST}
