from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.ad_campaign import AdCampaignBudgetType, AdCampaignObjective, AdCampaignPlatform, AdCampaignStatus


class AdCampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    platform: AdCampaignPlatform = AdCampaignPlatform.INSTAGRAM
    status: AdCampaignStatus = AdCampaignStatus.ACTIVE
    objective: AdCampaignObjective = AdCampaignObjective.MESSAGES
    budget_type: AdCampaignBudgetType = AdCampaignBudgetType.MANUAL
    daily_budget: Decimal | None = Field(default=None, ge=0)
    total_budget: Decimal | None = Field(default=None, ge=0)
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None


class AdCampaignUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    platform: AdCampaignPlatform | None = None
    status: AdCampaignStatus | None = None
    objective: AdCampaignObjective | None = None
    budget_type: AdCampaignBudgetType | None = None
    daily_budget: Decimal | None = Field(default=None, ge=0)
    total_budget: Decimal | None = Field(default=None, ge=0)
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None


class AdCampaignResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    platform: AdCampaignPlatform
    status: AdCampaignStatus
    objective: AdCampaignObjective
    budget_type: AdCampaignBudgetType
    daily_budget: Decimal | None
    total_budget: Decimal | None
    start_date: date | None
    end_date: date | None
    notes: str | None
    model_config = ConfigDict(from_attributes=True)


class AdMetricCreate(BaseModel):
    campaign_id: UUID
    metric_date: date
    spend: Decimal = Field(default=Decimal("0"), ge=0)
    impressions: int = Field(default=0, ge=0)
    reach: int = Field(default=0, ge=0)
    clicks: int = Field(default=0, ge=0)
    messages: int = Field(default=0, ge=0)
    leads: int = Field(default=0, ge=0)
    orders: int = Field(default=0, ge=0)
    revenue: Decimal = Field(default=Decimal("0"), ge=0)
    net_profit: Decimal = Decimal("0")


class AdMetricResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    campaign_id: UUID
    metric_date: date
    spend: Decimal
    impressions: int
    reach: int
    clicks: int
    messages: int
    leads: int
    orders: int
    revenue: Decimal
    net_profit: Decimal | None = None
    cpa: Decimal | None = None
    cpl: Decimal | None = None
    cpc: Decimal | None = None
    cpm: Decimal | None = None
    ctr: Decimal | None = None
    roas: Decimal | None = None
    roi: Decimal | None = None
    model_config = ConfigDict(from_attributes=True)


class AdvertisingSummaryResponse(BaseModel):
    total_spend: Decimal
    total_impressions: int
    total_reach: int
    total_clicks: int
    total_messages: int
    total_leads: int
    total_orders: int
    total_revenue: Decimal
    total_net_profit: Decimal | None = None
    average_cpa: Decimal | None = None
    average_cpl: Decimal | None = None
    average_cpc: Decimal | None = None
    average_cpm: Decimal | None = None
    average_ctr: Decimal | None = None
    roas: Decimal | None = None
    roi: Decimal | None = None


class CampaignPerformanceResponse(BaseModel):
    campaign_id: UUID
    campaign_name: str
    platform: str
    status: str
    spend: Decimal
    revenue: Decimal
    net_profit: Decimal | None = None
    orders: int
    leads: int
    messages: int
    cpa: Decimal | None = None
    cpl: Decimal | None = None
    roas: Decimal | None = None
    roi: Decimal | None = None


class AdvertisingTrendPoint(BaseModel):
    date: date
    spend: Decimal
    revenue: Decimal
    net_profit: Decimal | None = None
    orders: int
    leads: int
    cpa: Decimal | None = None
    roas: Decimal | None = None
