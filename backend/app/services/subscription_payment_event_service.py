"""Receipt ingestion only. Authentication and billing policy are separate boundaries."""
import hashlib
import json
import re
from datetime import UTC, datetime
from decimal import Context, Decimal, localcontext
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.subscription_payment_event_receipt import SubscriptionPaymentEventReceipt
from app.repositories.subscription_payment_event_repository import SubscriptionPaymentEventRepository
from app.schemas.subscription_payment_event import SubscriptionPaymentEvent

_OPAQUE_REFERENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]*", re.ASCII)
_PROVIDER = re.compile(r"[a-z][a-z0-9_-]*", re.ASCII)
_CURRENCY = re.compile(r"[A-Z]{3}", re.ASCII)
_AMOUNT_QUANTUM = Decimal("0.000001")
_AMOUNT_LIMIT = Decimal("100000000000000")


class SubscriptionPaymentEventValidationError(ValueError):
    pass


class SubscriptionPaymentEventConflict(ValueError):
    def __init__(self) -> None:
        # Deliberately identical for a changed transaction and a foreign workspace.
        super().__init__("Payment event conflicts with an existing receipt")


def _reference(value: str, field: str, limit: int, pattern: re.Pattern = _OPAQUE_REFERENCE) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= limit or pattern.fullmatch(value) is None:
        raise SubscriptionPaymentEventValidationError(f"Invalid {field}")
    return value


def normalize_payment_event(event: SubscriptionPaymentEvent) -> SubscriptionPaymentEvent:
    if not isinstance(event, SubscriptionPaymentEvent):
        raise SubscriptionPaymentEventValidationError("Normalized payment event required")
    provider = _reference(event.provider, "provider", 40, _PROVIDER)
    account = _reference(event.provider_account_id, "provider_account_id", 128)
    event_id = _reference(event.external_event_id, "external_event_id", 160)
    transaction_id = _reference(event.transaction_id, "transaction_id", 160)
    event_type = _reference(event.event_type, "event_type", 64)
    currency = _reference(event.currency, "currency", 3, _CURRENCY)
    amount = event.amount
    if not isinstance(amount, Decimal) or not amount.is_finite() or not 0 <= amount < _AMOUNT_LIMIT:
        raise SubscriptionPaymentEventValidationError("Invalid amount")
    # Fixed precision is a storage contract, not a currency pricing/rounding rule.
    # Never round away provider evidence, and do not depend on caller Decimal context.
    with localcontext(Context(prec=28)):
        normalized_amount = amount.quantize(_AMOUNT_QUANTUM)
    if amount != normalized_amount:
        raise SubscriptionPaymentEventValidationError("Amount exceeds supported precision")
    if normalized_amount == 0:
        normalized_amount = Decimal("0.000000")
    occurred_at = event.occurred_at
    if not isinstance(occurred_at, datetime) or occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
        raise SubscriptionPaymentEventValidationError("occurred_at must have a timezone")
    return SubscriptionPaymentEvent(provider, account, event_id, transaction_id, event_type,
                                    normalized_amount, currency, occurred_at.astimezone(UTC))


def payment_event_fingerprint(workspace_id: UUID, event: SubscriptionPaymentEvent) -> str:
    """Stable canonical v1 representation of the explicitly whitelisted fields."""
    fields = {
        "version": 1,
        "workspace_id": str(workspace_id),
        "provider": event.provider,
        "provider_account_id": event.provider_account_id,
        "external_event_id": event.external_event_id,
        "transaction_id": event.transaction_id,
        "event_type": event.event_type,
        "amount": format(event.amount, ".6f"),
        "currency": event.currency,
        "occurred_at": event.occurred_at.isoformat(timespec="microseconds"),
    }
    return hashlib.sha256(json.dumps(fields, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")).hexdigest()


class SubscriptionPaymentEventService:
    def __init__(self, db: Session) -> None:
        self.receipts = SubscriptionPaymentEventRepository(db)

    def record(self, workspace_id: UUID, event: SubscriptionPaymentEvent) -> SubscriptionPaymentEventReceipt:
        """Caller must authenticate PSP signature and merchant/workspace association.

        No public callback, PSP verification, entitlement or commit occurs here.
        Caller owns the transaction; retry serialization failures as a whole.
        """
        if not isinstance(workspace_id, UUID):
            raise SubscriptionPaymentEventValidationError("Invalid workspace_id")
        event = normalize_payment_event(event)
        fingerprint = payment_event_fingerprint(workspace_id, event)
        self.receipts.insert_if_absent(SubscriptionPaymentEventReceipt(
            workspace_id=workspace_id,
            provider=event.provider,
            provider_account_id=event.provider_account_id,
            external_event_id=event.external_event_id,
            transaction_id=event.transaction_id,
            event_type=event.event_type,
            amount=event.amount,
            currency=event.currency,
            occurred_at=event.occurred_at,
            fingerprint=fingerprint,
        ))
        receipt = self.receipts.get_for_event(workspace_id, event.provider, event.provider_account_id, event.external_event_id)
        if receipt is None or receipt.fingerprint != fingerprint:
            raise SubscriptionPaymentEventConflict()
        return receipt
