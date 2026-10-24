"""Deterministic CRM advertising attribution.

Never infer campaign identity from a participant name, message text, Meta conversation
volume, or an ad ID without an authenticated ad→campaign lookup. This module only
inherits an explicitly linked lead's existing campaign for a Direct-linked order.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.models.ad_campaign import AdCampaign
from app.models.ai_direct import DirectConversation
from app.models.lead import Lead
from app.models.order import Order, OrderStatus, PaymentStatus
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.order_repository import OrderRepository


class AdvertisingAttributionService:
    """Read-only report and safe, idempotent direct lead→order attribution."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.orders = OrderRepository(db)
        self.audit = AuditLogRepository(db)

    def inherit_verified_direct_lead(
        self,
        workspace_id: UUID,
        conversation: DirectConversation,
        customer_id: UUID,
        order_id: UUID,
        actor_user_id: UUID | None,
    ) -> bool:
        """Populate only an empty campaign, from an explicitly linked live lead.

        The caller's transaction owns commit/rollback. Every lookup is workspace scoped,
        and existing manual/explicit attribution always takes precedence.
        """
        if conversation.workspace_id != workspace_id or not conversation.linked_lead_id:
            return False
        order = self.orders.get_for_update(workspace_id, order_id)
        if not order or order.campaign_id is not None or order.customer_id != customer_id:
            return False

        lead = self.db.execute(
            select(Lead).where(
                Lead.id == conversation.linked_lead_id,
                Lead.workspace_id == workspace_id,
                Lead.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
        if not lead or not lead.campaign_id:
            return False

        campaign = self.db.execute(
            select(AdCampaign.id).where(
                AdCampaign.id == lead.campaign_id,
                AdCampaign.workspace_id == workspace_id,
                AdCampaign.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
        if not campaign:
            return False

        order.campaign_id = campaign
        self.audit.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="Order",
            entity_id=order.id,
            action="DIRECT_LEAD_CAMPAIGN_INHERITED",
            old_value={"campaign_id": None},
            new_value={
                "campaign_id": str(campaign),
                "lead_id": str(lead.id),
                "conversation_id": str(conversation.id),
                "evidence": "EXPLICIT_DIRECT_LEAD_LINK",
            },
        )
        self.db.flush()
        return True

    def summary(
        self, workspace_id: UUID, start_date: date, end_date: date, *, limit: int = 8
    ) -> dict:
        """Separate source-of-truth CRM orders from provider AdMetric aggregates.

        Date basis: order.created_at UTC day. Realized revenue only includes orders
        that are BOTH COMPLETED and PAID; returned/cancelled/refunded never count.
        """
        if start_date > end_date:
            raise ValueError("INVALID_DATE_RANGE")
        beginning = datetime.combine(start_date, time.min, tzinfo=UTC)
        end_exclusive = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=UTC)
        eligible = and_(
            Order.status.notin_((OrderStatus.CANCELLED.value, OrderStatus.RETURNED.value)),
            Order.payment_status != PaymentStatus.REFUNDED.value,
        )
        completed_paid = and_(
            Order.status == OrderStatus.COMPLETED.value,
            Order.payment_status == PaymentStatus.PAID.value,
        )
        base = (
            Order.workspace_id == workspace_id,
            Order.deleted_at.is_(None),
            Order.created_at >= beginning,
            Order.created_at < end_exclusive,
        )
        all_counts = self.db.execute(
            select(
                func.count(Order.id).filter(and_(eligible, Order.campaign_id.is_not(None))),
                func.count(Order.id).filter(and_(completed_paid, Order.campaign_id.is_not(None))),
                func.coalesce(
                    func.sum(case((and_(completed_paid, Order.campaign_id.is_not(None)), Order.revenue), else_=Decimal("0"))),
                    Decimal("0"),
                ),
                func.count(Order.id).filter(and_(completed_paid, Order.campaign_id.is_(None))),
            ).where(*base)
        ).one()

        grouped = self.db.execute(
            select(
                AdCampaign.id,
                AdCampaign.name,
                func.count(Order.id).filter(eligible),
                func.count(Order.id).filter(completed_paid),
                func.coalesce(func.sum(case((completed_paid, Order.revenue), else_=Decimal("0"))), Decimal("0")),
            )
            .join(
                AdCampaign,
                and_(
                    Order.campaign_id == AdCampaign.id,
                    AdCampaign.workspace_id == workspace_id,
                    AdCampaign.deleted_at.is_(None),
                ),
            )
            .where(*base)
            .group_by(AdCampaign.id, AdCampaign.name)
            .order_by(func.count(Order.id).filter(eligible).desc(), AdCampaign.id)
            .limit(limit)
        ).all()

        return {
            "source": "crm_orders",
            "date_basis": "order_created_at_utc",
            "linked_orders": int(all_counts[0] or 0),
            "completed_paid_orders": int(all_counts[1] or 0),
            "completed_paid_revenue": all_counts[2] or Decimal("0"),
            "unattributed_completed_paid_orders": int(all_counts[3] or 0),
            "campaigns": [
                {
                    "campaign_id": campaign_id,
                    "campaign_name": name,
                    "linked_orders": int(linked or 0),
                    "completed_paid_orders": int(confirmed or 0),
                    "completed_paid_revenue": revenue or Decimal("0"),
                }
                for campaign_id, name, linked, confirmed, revenue in grouped
            ],
        }
