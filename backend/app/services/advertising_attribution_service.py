"""Deterministic CRM advertising attribution.

Never infer campaign identity from a participant name, message text, Meta conversation
volume, or an ad ID without an authenticated ad→campaign lookup. This module only
inherits an explicitly linked lead's existing campaign for a Direct-linked order.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ad_campaign import AdCampaign
from app.models.ai_direct import DirectConversation
from app.models.lead import Lead
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
