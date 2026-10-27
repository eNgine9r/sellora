from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.models.cod_payment_evidence import CodEvidenceSource


class CodImportRow(BaseModel):
    source: CodEvidenceSource
    reference: str = Field(min_length=3, max_length=160)
    tracking_number: str | None = Field(default=None, max_length=40)
    gross_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    fee_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    paid_at: AwareDatetime

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_fee(self):
        if self.fee_amount > self.gross_amount:
            raise ValueError("Fee must not exceed gross payment")
        return self


class CodImportRequest(BaseModel):
    rows: list[CodImportRow] = Field(min_length=1, max_length=300)


class CodReviewRow(BaseModel):
    reference: str
    tracking_number: str | None
    amount: Decimal
    status: str
    reason: str | None
    order_id: UUID | None = None


class CodPreviewResponse(BaseModel):
    rows: list[CodReviewRow]
    matched_count: int
    review_count: int
    duplicate_count: int


class CodImportResponse(CodPreviewResponse):
    inserted_count: int


class CodLedgerRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: str
    reference: str
    tracking_number: str | None
    order_id: UUID | None
    gross_amount: Decimal
    fee_amount: Decimal
    paid_at: datetime
    status: str
    review_reason: str | None


class CodLedgerResponse(BaseModel):
    rows: list[CodLedgerRow]
    matched_receipts: Decimal
    review_receipts: Decimal
    pending_historical_amount: Decimal
    historical_amount_unverified_count: int
    unvalued_historical_orders: int
    matched_count: int
    review_count: int
