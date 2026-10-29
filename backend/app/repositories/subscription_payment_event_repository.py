from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.subscription_payment_event_receipt import SubscriptionPaymentEventReceipt


class SubscriptionPaymentEventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def insert_if_absent(self, receipt: SubscriptionPaymentEventReceipt) -> None:
        # DO NOTHING waits for a competing identity's transaction. It never changes
        # the first receipt, including when that identity belongs to another tenant.
        statement = insert(SubscriptionPaymentEventReceipt).values(
            workspace_id=receipt.workspace_id,
            provider=receipt.provider,
            provider_account_id=receipt.provider_account_id,
            external_event_id=receipt.external_event_id,
            transaction_id=receipt.transaction_id,
            event_type=receipt.event_type,
            amount=receipt.amount,
            currency=receipt.currency,
            occurred_at=receipt.occurred_at,
            fingerprint=receipt.fingerprint,
        ).on_conflict_do_nothing(index_elements=["provider", "provider_account_id", "external_event_id"])
        self.db.execute(statement)

    def get_for_event(self, workspace_id: UUID, provider: str, provider_account_id: str,
                      external_event_id: str) -> SubscriptionPaymentEventReceipt | None:
        statement = select(SubscriptionPaymentEventReceipt).where(
            SubscriptionPaymentEventReceipt.workspace_id == workspace_id,
            SubscriptionPaymentEventReceipt.provider == provider,
            SubscriptionPaymentEventReceipt.provider_account_id == provider_account_id,
            SubscriptionPaymentEventReceipt.external_event_id == external_event_id,
        )
        return self.db.execute(statement).scalar_one_or_none()
