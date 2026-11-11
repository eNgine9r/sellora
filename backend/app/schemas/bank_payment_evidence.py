"""Read-only-safe phase-one bank evidence APIs. No user-supplied 'verified' flag."""
from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from app.models.bank_payment_evidence import BankPaymentKind, BankPaymentRail


class BankReviewStatus(StrEnum):
    REVIEW = "REVIEW"
    DUPLICATE = "DUPLICATE"


class BankImportRow(BaseModel):
    provider_account_id: str = Field(min_length=3, max_length=128)
    external_reference: str = Field(min_length=3, max_length=160)
    rail: BankPaymentRail
    kind: BankPaymentKind
    amount_minor: int = Field(gt=0, lt=100_000_000_000_000)
    currency: Literal["UAH"] = "UAH"
    occurred_at: AwareDatetime
    is_hold: bool = False
    invoice_id: str | None = Field(default=None, min_length=3, max_length=160)
    order_number: str | None = Field(default=None, min_length=1, max_length=30)

    model_config = ConfigDict(extra="forbid")

    @field_validator("provider_account_id", "external_reference", "invoice_id", "order_number")
    @classmethod
    def validate_reference(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip() or value != value.strip() or any(ch in value for ch in "\r\n\0"):
            raise ValueError("Reference cannot be blank, padded, or multiline")
        return value


class BankImportRequest(BaseModel):
    rows: list[BankImportRow] = Field(min_length=1, max_length=200)


class BankReviewRow(BaseModel):
    provider_account_id: str
    external_reference: str
    rail: BankPaymentRail
    kind: BankPaymentKind
    amount_minor: int
    status: BankReviewStatus
    reason: str
    candidate_order_id: UUID | None = None


class BankPreviewResponse(BaseModel):
    rows: list[BankReviewRow]
    candidate_count: int
    review_count: int
    duplicate_count: int


class BankImportResponse(BankPreviewResponse):
    inserted_count: int


class BankLedgerRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: str
    provider_account_id: str
    external_reference: str
    rail: BankPaymentRail
    kind: BankPaymentKind
    origin: str
    amount_minor: int
    currency: str
    occurred_at: datetime
    is_hold: bool
    invoice_id: str | None
    order_number: str | None
    candidate_order_id: UUID | None
    review_reason: str


class BankLedgerResponse(BaseModel):
    rows: list[BankLedgerRow]
    total_count: int
