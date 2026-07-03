from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ValidationMode = Literal["disabled", "not_ready", "fake", "live_read_only"]


class MetaAdsValidationCheckDTO(BaseModel):
    name: str
    passed: bool
    reason: str | None = None
    message: str


class MetaAdsStagingValidationResponse(BaseModel):
    ready: bool = False
    reason: str | None = "feature_disabled"
    message: str = "Meta Ads staging validation is not available yet."
    mode: ValidationMode = "disabled"
    checks: list[MetaAdsValidationCheckDTO] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    account_preview_count: int = 0
    campaign_preview_count: int = 0
    insights_preview_sample_count: int = 0
    sync_active: bool = False
    writes_performed: bool = False
