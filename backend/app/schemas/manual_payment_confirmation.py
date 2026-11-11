"""Explicit *manual attestation* only: never let request label bank API verified."""
from datetime import datetime
from uuid import UUID
import re

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

from app.models.manual_payment_confirmation import ManualPaymentMethod


class ManualPaymentConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_method: ManualPaymentMethod
    transaction_reference: str = Field(min_length=6, max_length=160)
    amount_minor: StrictInt = Field(gt=0, lt=100_000_000_000_000)
    receipt_checked: bool
    bank_received_checked: bool
    receipt_note: str | None = Field(default=None, max_length=240)

    @field_validator("transaction_reference")
    @classmethod
    def valid_transaction(cls, value: str) -> str:
        # Reject raw card numbers, PAN, IBAN, payment links and untrusted markup.
        if (value != value.strip() or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_\-/.]{5,159}", value)
                or re.fullmatch(r"\d{13,19}", value) or re.fullmatch(r"UA\d+", value, re.I)):
            raise ValueError("Use only the unique bank transaction ID, not card number, IBAN or URL")
        return value

    @field_validator("receipt_note")
    @classmethod
    def valid_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        note = value.strip()
        if not note or any(c in note for c in "<>\x00\r\n"):
            raise ValueError("Receipt note must be a short plain-text reference")
        return note


class ManualPaymentConfirmationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    payment_method: ManualPaymentMethod
    amount_minor: int
    currency: str
    receipt_checked: bool
    bank_received_checked: bool
    receipt_note: str | None
    verified_by_user_id: UUID | None
    verified_at: datetime
    # Account and bank IDs are only shown as masked suffix; no raw reference.
    reference_suffix: str


class OrderManualPaymentResult(BaseModel):
    confirmation: ManualPaymentConfirmationResponse
    payment_status: str
