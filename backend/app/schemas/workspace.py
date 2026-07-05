from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.role import RoleName


class CurrencyCode(StrEnum):
    UAH = "UAH"
    USD = "USD"


SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    currency_code: CurrencyCode = CurrencyCode.UAH
    timezone: str = "Europe/Kyiv"
    role: RoleName
    is_active: bool = True


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=2, max_length=120, pattern=SLUG_PATTERN)
    currency_code: CurrencyCode = CurrencyCode.UAH
    timezone: str = Field(default="Europe/Kyiv", min_length=1, max_length=80)

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str) -> str:
        return value.strip().lower()


class WorkspaceSettingsResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    currency_code: CurrencyCode = CurrencyCode.UAH
    timezone: str = "Europe/Kyiv"
    role: RoleName | None = None
    is_active: bool = True


class WorkspaceSettingsUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=2, max_length=120, pattern=SLUG_PATTERN)
    currency_code: CurrencyCode | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=80)

    @field_validator("slug")
    @classmethod
    def normalize_optional_slug(cls, value: str | None) -> str | None:
        return value.strip().lower() if value is not None else None


class WorkspaceUserResponse(BaseModel):
    user_id: UUID
    email: str
    full_name: str
    role: RoleName
    is_active: bool


class WorkspaceUserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    full_name: str = Field(min_length=1, max_length=200)
    role: RoleName
    temporary_password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized:
            raise ValueError("Invalid email")
        return normalized


class WorkspaceUserRoleUpdate(BaseModel):
    role: RoleName
