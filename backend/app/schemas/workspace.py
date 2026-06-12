from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class CurrencyCode(StrEnum):
    UAH = "UAH"
    USD = "USD"


class WorkspaceSettingsResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    currency_code: CurrencyCode = CurrencyCode.UAH


class WorkspaceSettingsUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    currency_code: CurrencyCode | None = None
