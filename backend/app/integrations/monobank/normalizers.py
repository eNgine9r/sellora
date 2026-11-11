"""Normalize merchant statement API results without declaring sale receipts paid.

The bank's merchant **settlement amount** is not the original checkout amount;
never add both the checkout and the following FOP account credit to revenue.
"""
from datetime import datetime
from typing import Any

from app.models.bank_payment_evidence import BankPaymentKind, BankPaymentRail
from app.schemas.bank_payment_evidence import BankImportRow
from app.services.monobank_normalizers import MonobankPayloadError


def merchant_statement_item(item: dict[str, Any], *, merchant_account_id: str) -> BankImportRow | None:
    if not isinstance(item, dict):
        raise MonobankPayloadError("Invalid statement entry")
    if item.get("status") != "success":
        return None
    amount = item.get("amount")
    currency = item.get("ccy")
    if type(amount) is not int or not 0 < amount < 100_000_000_000_000:
        raise MonobankPayloadError("Invalid statement amount")
    if type(currency) is not int or currency != 980:
        raise MonobankPayloadError("Unsupported currency")
    invoice_id = item.get("invoiceId")
    if not isinstance(invoice_id, str) or not 5 <= len(invoice_id) <= 120:
        raise MonobankPayloadError("Invalid invoice ID")
    try:
        dt = datetime.fromisoformat(str(item.get("date", "")).replace("Z", "+00:00"))
    except ValueError as exc:
        raise MonobankPayloadError("Invalid statement date") from None
    if dt.tzinfo is None:
        raise MonobankPayloadError("Statement date has no timezone")
    # A cancellation list indicates a possible partial/full reversal. Any
    # allocation must review refunds separately and must not mark PAID.
    if item.get("cancelList"):
        raise MonobankPayloadError("Merchant invoice has cancellation history; review required")
    try:
        return BankImportRow(
            provider_account_id=merchant_account_id,
            external_reference=invoice_id,
            rail=BankPaymentRail.MONO_ACQUIRING_LINK,
            kind=BankPaymentKind.CUSTOMER_PAYMENT,
            amount_minor=amount,
            occurred_at=dt,
            invoice_id=invoice_id,
        )
    except ValueError as exc:
        raise MonobankPayloadError("Invalid merchant statement row") from None
