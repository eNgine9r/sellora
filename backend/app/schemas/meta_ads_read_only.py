from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

SourceType = Literal["fake", "live_read_only"]


class MetaReadOnlyNotReadyResponse(BaseModel):
    ready: bool = False
    reason: str | None = "feature_disabled"
    message: str = "Meta Ads discovery is not available yet."
    db_writes: bool = False
    sync_active: bool = False
    apply_available: bool = False


class MetaAdAccountPreviewDTO(BaseModel):
    external_account_id_masked: str
    name: str
    currency: str
    timezone: str
    status: str = "PREVIEW_ONLY"
    source: SourceType = "fake"
    can_be_selected: bool = False
    warnings: list[str] = Field(default_factory=list)


class MetaCampaignDiscoveryPreviewDTO(BaseModel):
    external_campaign_id_masked: str
    name: str
    status: str
    objective: str
    start_time: datetime | None = None
    stop_time: datetime | None = None
    source: SourceType = "fake"
    warnings: list[str] = Field(default_factory=list)


class MetaInsightsPreviewDTO(BaseModel):
    date: date
    campaign_name: str
    external_campaign_id_masked: str
    spend: Decimal
    impressions: int | None = None
    clicks: int | None = None
    reach: int | None = None
    messages: int | None = None
    source: SourceType = "fake"
    warnings: list[str] = Field(default_factory=list)


class MetaAdAccountDiscoveryResponse(MetaReadOnlyNotReadyResponse):
    accounts: list[MetaAdAccountPreviewDTO] = Field(default_factory=list)


class MetaCampaignDiscoveryResponse(MetaReadOnlyNotReadyResponse):
    campaigns: list[MetaCampaignDiscoveryPreviewDTO] = Field(default_factory=list)


class MetaInsightsPreviewResponse(MetaReadOnlyNotReadyResponse):
    insights: list[MetaInsightsPreviewDTO] = Field(default_factory=list)
