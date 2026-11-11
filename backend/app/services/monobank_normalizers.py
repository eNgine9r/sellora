"""Pure untrusted-payload normalizers for future bank-approved read-only adapters.

Call only *after* fetching via an authorized integration with provenance tracked.
These parsers DO NOT authenticate payloads, create transactions or update orders.
In particular, an inbound account credit may be an acquiring payout rather than
a customer payment, and must not be credited to an order based on amount alone.
"""
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from app.models.bank_payment_evidence import BankPaymentKind, BankPaymentRail
from app.schemas.bank_payment_evidence import BankImportRow


class MonobankPayloadError(ValueError):
    pass


def _positive_minor(value: Any) -> int:
    if type(value) is not int or not 0 < value < 100_000_000_000_000:
        raise MonobankPayloadError("Invalid amount in minor currency units")
    return value


def _uah(value: Any) -> None:
    if type(value) is not int or value != 980:
        raise MonobankPayloadError("Only UAH currency code 980 is supported")


def _checked_row(**kwargs: Any) -> BankImportRow:
    try:
        return BankImportRow(**kwargs)
    except (ValueError, ValidationError) as exc:
        raise MonobankPayloadError("Invalid bank event fields") from exc


def normalize_statement_credit(event: dict[str, Any], *, account_id: str) -> BankImportRow | None:
    """Return positive account credit; negative debits are intentionally skipped.

    NEVER classify arbitrary credit as CUSTOMER_PAYMENT automatically. Provider
    FOP card and IBAN credits may share the same underlying bank account.
    """
    amount = event.get("amount")
    if type(amount) is not int:
        raise MonobankPayloadError("Invalid account statement amount")
    if amount <= 0:
        return None
    _uah(event.get("currencyCode"))
    timestamp = event.get("time")
    if type(timestamp) is not int or not 0 < timestamp < 4_102_444_800:
        raise MonobankPayloadError("Invalid statement time")
    return _checked_row(
        provider_account_id=account_id,
        external_reference=event.get("id"),
        rail=BankPaymentRail.UNKNOWN_ACCOUNT_TRANSFER,
        kind=BankPaymentKind.UNCLASSIFIED_CREDIT,
        amount_minor=_positive_minor(amount),
        occurred_at=datetime.fromtimestamp(timestamp, timezone.utc),
        is_hold=event.get("hold") is True,
    )


def normalize_paid_invoice(event: dict[str, Any], *, merchant_account_id: str) -> BankImportRow | None:
    """Normalize merchant invoice status (authenticated/verified elsewhere).

    Do not infer Order.order_number from arbitrary merchant reference values.
    Webhook signature, stale modifiedDate and provider status re-fetch must be
    implemented before this can act as any bank-verified payment.
    """
    if event.get("status") != "success":
        return None
    _uah(event.get("ccy"))
    modified = event.get("modifiedDate")
    if not isinstance(modified, str):
        raise MonobankPayloadError("Invalid merchant modifiedDate")
    try:
        occurred_at = datetime.fromisoformat(modified.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MonobankPayloadError("Invalid merchant modifiedDate") from exc
    if occurred_at.tzinfo is None:
        raise MonobankPayloadError("Merchant modifiedDate must have timezone")
    invoice_id = event.get("invoiceId")
    return _checked_row(
        provider_account_id=merchant_account_id,
        external_reference=invoice_id,
        rail=BankPaymentRail.MONO_ACQUIRING_LINK,
        kind=BankPaymentKind.CUSTOMER_PAYMENT,
        amount_minor=_positive_minor(event.get("finalAmount", event.get("amount"))),
        occurred_at=occurred_at,
        invoice_id=invoice_id,
    )
