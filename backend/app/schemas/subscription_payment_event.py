"""Internal normalized input from a future authenticated PSP adapter, not an API schema."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class SubscriptionPaymentEvent:
    # These must be opaque provider/merchant references, never customer PII.
    provider: str
    provider_account_id: str
    external_event_id: str
    transaction_id: str
    event_type: str
    amount: Decimal
    currency: str
    occurred_at: datetime
