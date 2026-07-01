from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID


class MetaAdsDTOError(ValueError):
    """Raised when synthetic Meta Ads DTO data cannot be normalized safely."""


def normalize_decimal(value: Decimal | int | str | float | None, field_name: str) -> Decimal:
    if value is None:
        return Decimal("0")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise MetaAdsDTOError(f"{field_name} must be a decimal value") from exc
    if amount < 0:
        raise MetaAdsDTOError(f"{field_name} cannot be negative")
    return amount.quantize(Decimal("0.01"))


def normalize_int(value: int | str | None, field_name: str) -> int:
    if value is None:
        return 0
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise MetaAdsDTOError(f"{field_name} must be an integer value") from exc
    if number < 0:
        raise MetaAdsDTOError(f"{field_name} cannot be negative")
    return number


@dataclass(frozen=True)
class MetaAdAccountDTO:
    external_account_id: str
    name: str
    currency: str
    timezone: str


@dataclass(frozen=True)
class MetaCampaignDTO:
    external_campaign_id: str
    external_account_id: str
    name: str
    status: str
    objective: str
    platform: str
    created_time: datetime


@dataclass(frozen=True)
class MetaInsightsRowDTO:
    external_campaign_id: str
    date: date
    spend: Decimal | int | str | float | None = Decimal("0")
    impressions: int | str | None = 0
    clicks: int | str | None = 0
    messages: int | str | None = 0
    leads: int | str | None = 0
    currency: str = "UAH"

    @property
    def normalized_spend(self) -> Decimal:
        return normalize_decimal(self.spend, "spend")

    @property
    def normalized_impressions(self) -> int:
        return normalize_int(self.impressions, "impressions")

    @property
    def normalized_clicks(self) -> int:
        return normalize_int(self.clicks, "clicks")

    @property
    def normalized_messages(self) -> int:
        return normalize_int(self.messages, "messages")

    @property
    def normalized_leads(self) -> int:
        return normalize_int(self.leads, "leads")


@dataclass(frozen=True)
class MetaSyncIssueDTO:
    code: str
    message: str
    external_campaign_id: str | None = None


@dataclass(frozen=True)
class AdCampaignSyncCandidate:
    external_source: str
    external_campaign_id: str
    external_account_id: str
    name: str
    platform: str
    status: str
    objective: str
    workspace_id: UUID | None = None


@dataclass(frozen=True)
class AdMetricSyncCandidate:
    external_source: str
    external_campaign_id: str
    metric_date: date
    spend: Decimal
    impressions: int
    clicks: int
    messages: int
    leads: int
    currency: str
    workspace_id: UUID | None = None


@dataclass(frozen=True)
class MetaSyncResultDTO:
    campaigns_seen: int
    metrics_seen: int
    campaigns_to_create: int
    campaigns_to_update: int
    metrics_to_create: int
    metrics_to_update: int
    skipped: int
    issues: list[MetaSyncIssueDTO] = field(default_factory=list)
    dry_run: bool = True
    campaign_candidates: list[AdCampaignSyncCandidate] = field(default_factory=list)
    metric_candidates: list[AdMetricSyncCandidate] = field(default_factory=list)

MetaSyncPreviewStatus = str
WOULD_CREATE = "WOULD_CREATE"
WOULD_UPDATE = "WOULD_UPDATE"
WOULD_SKIP = "WOULD_SKIP"
POTENTIAL_CONFLICT = "POTENTIAL_CONFLICT"
NEEDS_EXTERNAL_ID_SUPPORT = "NEEDS_EXTERNAL_ID_SUPPORT"
INVALID = "INVALID"


@dataclass(frozen=True)
class MetaSyncConflictDTO:
    code: str
    message: str
    external_campaign_id: str | None = None
    existing_id: UUID | None = None


@dataclass(frozen=True)
class MetaCampaignPreviewItemDTO:
    external_campaign_id: str
    name: str
    platform: str
    classification: MetaSyncPreviewStatus
    matched_campaign_id: UUID | None = None
    needs_external_id_support: bool = True
    message: str = ""
    conflicts: list[MetaSyncConflictDTO] = field(default_factory=list)


@dataclass(frozen=True)
class MetaMetricPreviewItemDTO:
    external_campaign_id: str
    metric_date: date
    classification: MetaSyncPreviewStatus
    matched_campaign_id: UUID | None = None
    matched_metric_id: UUID | None = None
    spend: Decimal = Decimal("0.00")
    impressions: int = 0
    clicks: int = 0
    messages: int = 0
    leads: int = 0
    currency: str = "UAH"
    needs_external_id_support: bool = True
    message: str = ""
    conflicts: list[MetaSyncConflictDTO] = field(default_factory=list)


@dataclass(frozen=True)
class MetaSyncPreviewSummaryDTO:
    campaigns_seen: int
    metrics_seen: int
    campaigns_would_create: int
    campaigns_would_update: int
    campaigns_would_skip: int
    metrics_would_create: int
    metrics_would_update: int
    metrics_would_skip: int
    potential_conflicts: int
    needs_external_id_support: int
    invalid_rows: int
    dry_run: bool = True
    db_writes: bool = False


@dataclass(frozen=True)
class MetaSyncPreviewResultDTO:
    summary: MetaSyncPreviewSummaryDTO
    campaign_items: list[MetaCampaignPreviewItemDTO] = field(default_factory=list)
    metric_items: list[MetaMetricPreviewItemDTO] = field(default_factory=list)
    issues: list[MetaSyncIssueDTO] = field(default_factory=list)
    dry_run: bool = True
    db_writes: bool = False
