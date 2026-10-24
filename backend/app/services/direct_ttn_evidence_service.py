"""Workspace-scoped, read-only evidence linking Direct TTNs to existing shipments.

Exact TTNs prove a correspondence to an existing CRM shipment/order, not
provider delivery, actual payment, product contents, or advertising attribution.
No order/lead/customer/financial record is created or mutated.
"""
from __future__ import annotations

import re
from collections import defaultdict
from uuid import UUID

from sqlalchemy import and_, func, select

from app.models.audit_log import AuditLog
from app.models.direct_order_shipment_link import DirectOrderShipmentLink
from sqlalchemy.orm import Session

from app.models.ai_direct import DirectConversation, DirectMessage
from app.models.order import Order
from app.models.shipment import Shipment, ShipmentCarrier

# A Nova Poshta TTN is 14 digits beginning with 20, bounded by non-digits.
_TTN = re.compile(r"(?<!\d)20\d{12}(?!\d)")
_DB_TTN = r"(^|[^0-9])20[0-9]{12}([^0-9]|$)"
_DELIVERY_CONTEXT = re.compile(
    r"(ттн|накладн|відправ|посилк|пошт|poshta|tracking|достав|замовлен)",
    re.IGNORECASE,
)
_MAX_MESSAGES = 500


def mask_tracking(number: str) -> str:
    """Do not expose full customer-linked tracking numbers in preview APIs."""
    return number[:2] + "••••••••" + number[-4:]


def extract_ttns(text: str) -> set[str]:
    """Find standalone provider-shaped numbers, never partial digit sequences."""
    return set(_TTN.findall(text))


class DirectTtnEvidenceService:
    def __init__(self, db: Session):
        self.db = db

    def preview(self, workspace_id: UUID, conversation_id: UUID) -> dict | None:
        conversation = self.db.scalar(
            select(DirectConversation).where(
                DirectConversation.workspace_id == workspace_id,
                DirectConversation.id == conversation_id,
                DirectConversation.deleted_at.is_(None),
            )
        )
        if conversation is None:
            return None

        # Only a bounded number of matching messages is fetched. No raw text
        # leaves the service; incomplete scans are explicitly indicated.
        messages = self.db.execute(
            select(DirectMessage.id, DirectMessage.text)
            .where(
                DirectMessage.workspace_id == workspace_id,
                DirectMessage.conversation_id == conversation_id,
                DirectMessage.deleted_at.is_(None),
                DirectMessage.is_synthetic.is_(False),
                DirectMessage.direction == "OUTBOUND",
                DirectMessage.text.op("~")(_DB_TTN),
            )
            .order_by(DirectMessage.received_at, DirectMessage.id)
            .limit(_MAX_MESSAGES + 1)
        ).all()
        truncated = len(messages) > _MAX_MESSAGES
        first_message_by_code: dict[str, UUID] = {}
        for msg_id, raw_text in messages[:_MAX_MESSAGES]:
            for code in extract_ttns(raw_text or ""):
                # Unknown numbers need delivery context; known shipments can
                # be verified by matching their TTN without assuming meaning.
                first_message_by_code.setdefault(code, msg_id)

        codes = list(first_message_by_code)
        shipment_rows = (
            self.db.execute(
                select(
                    Shipment.id,
                    Shipment.tracking_number,
                    Shipment.customer_id,
                    Shipment.status,
                    Order.id,
                    Order.order_number,
                    Order.status,
                    Order.payment_status,
                    Order.is_historical,
                )
                .join(
                    Order,
                    and_(
                        Order.id == Shipment.order_id,
                        Order.workspace_id == Shipment.workspace_id,
                        Order.deleted_at.is_(None),
                    ),
                )
                .where(
                    Shipment.workspace_id == workspace_id,
                    Shipment.deleted_at.is_(None),
                    Shipment.carrier == ShipmentCarrier.NOVA_POSHTA.value,
                    func.regexp_replace(Shipment.tracking_number, "[^0-9]", "", "g").in_(codes),
                )
            ).all()
            if codes
            else []
        )
        by_code = defaultdict(list)
        for shipment_id, tracking, customer_id, shipment_status, order_id, order_number, order_status, payment_status, historical in shipment_rows:
            digits = re.sub(r"\D", "", tracking or "")
            if digits in first_message_by_code:
                by_code[digits].append({
                    "shipment_id": shipment_id,
                    "shipment_status": shipment_status,
                    "order_id": order_id,
                    "order_number": order_number,
                    "order_status": order_status,
                    "payment_status": payment_status,
                    "is_historical": historical,
                    "customer_id": customer_id,
                })

        verified: list[dict] = []
        needs_review: list[dict] = []
        verified_shipment_ids: set[UUID] = set()
        for code in sorted(codes):
            candidates = by_code.get(code, [])
            message_id = first_message_by_code[code]
            if not candidates:
                # Only surface unknown TTNs when the originating message
                # actually refers to shipping/delivery.
                message_text = next(
                    (t for mid, t in messages[:_MAX_MESSAGES] if mid == message_id),
                    "",
                )
                if _DELIVERY_CONTEXT.search(message_text or ""):
                    needs_review.append({
                        "tracking_masked": mask_tracking(code),
                        "source_message_id": message_id,
                        "reason": "SHIPMENT_NOT_IN_CRM",
                    })
                continue
            if len(candidates) != 1:
                needs_review.append({
                    "tracking_masked": mask_tracking(code),
                    "source_message_id": message_id,
                    "reason": "MULTIPLE_SHIPMENT_MATCHES",
                })
                continue
            match = candidates[0]
            if conversation.linked_customer_id and (
                not match["customer_id"]
                or conversation.linked_customer_id != match["customer_id"]
            ):
                needs_review.append({
                    "tracking_masked": mask_tracking(code),
                    "source_message_id": message_id,
                    "reason": "CUSTOMER_MISMATCH",
                })
                continue
            if match["shipment_id"] in verified_shipment_ids:
                continue
            verified_shipment_ids.add(match["shipment_id"])
            verified.append({
                "order_id": match["order_id"],
                "order_number": match["order_number"],
                "order_status": match["order_status"],
                "payment_status": match["payment_status"],
                "is_historical": match["is_historical"],
                "shipment_id": match["shipment_id"],
                "shipment_status": match["shipment_status"],
                "tracking_masked": mask_tracking(code),
                "source_message_id": message_id,
                "evidence_type": "EXACT_SHIPMENT_TTN",
            })
        linked_shipment_ids = set(
            self.db.scalars(
                select(DirectOrderShipmentLink.shipment_id).where(
                    DirectOrderShipmentLink.workspace_id == workspace_id,
                    DirectOrderShipmentLink.conversation_id == conversation_id,
                    DirectOrderShipmentLink.shipment_id.in_(verified_shipment_ids),
                    DirectOrderShipmentLink.deleted_at.is_(None),
                )
            ).all()
        ) if verified_shipment_ids else set()
        for match in verified:
            match["confirmed_in_crm"] = match["shipment_id"] in linked_shipment_ids

        return {
            "conversation_id": conversation_id,
            "verified_orders": sorted(verified, key=lambda x: x["order_number"]),
            "needs_review": needs_review,
            "has_multiple_orders": len({v["order_id"] for v in verified}) > 1,
            "scan_truncated": truncated,
        }

    def confirm(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        expected_order_ids: set[UUID],
        actor_id: UUID,
    ) -> dict:
        """Persist an explicitly reviewed set of exact TTN matches.

        Locks the conversation for idempotency. The client-supplied expected
        set must still match the latest evidence (no blind confirm/replay).
        This transaction never creates orders, shipments or finance entries.
        """
        conversation = self.db.scalar(
            select(DirectConversation)
            .where(
                DirectConversation.workspace_id == workspace_id,
                DirectConversation.id == conversation_id,
                DirectConversation.deleted_at.is_(None),
            )
            .with_for_update()
        )
        if conversation is None:
            raise ValueError("DIRECT_CONVERSATION_NOT_FOUND")
        preview = self.preview(workspace_id, conversation_id)
        if preview is None or preview["scan_truncated"]:
            raise ValueError("DIRECT_ORDER_EVIDENCE_INCOMPLETE")

        matches = preview["verified_orders"]
        actual_order_ids = {v["order_id"] for v in matches}
        if not actual_order_ids or actual_order_ids != expected_order_ids:
            raise ValueError("DIRECT_ORDER_EVIDENCE_CHANGED")
        if len(actual_order_ids) == 1:
            only = next(iter(actual_order_ids))
            if conversation.linked_order_id is not None and conversation.linked_order_id != only:
                raise ValueError("DIRECT_PRIMARY_ORDER_CONFLICT")

        created = 0
        existing = 0
        for match in matches:
            stored = self.db.scalar(
                select(DirectOrderShipmentLink).where(
                    DirectOrderShipmentLink.workspace_id == workspace_id,
                    DirectOrderShipmentLink.conversation_id == conversation_id,
                    DirectOrderShipmentLink.shipment_id == match["shipment_id"],
                )
            )
            if stored and stored.order_id != match["order_id"]:
                raise ValueError("DIRECT_ORDER_SHIPMENT_CONFLICT")
            if stored and stored.deleted_at is None:
                existing += 1
                continue
            if stored:
                stored.deleted_at = None
                stored.deleted_by = None
                stored.source_message_id = match["source_message_id"]
            else:
                stored = DirectOrderShipmentLink(
                    workspace_id=workspace_id,
                    conversation_id=conversation_id,
                    shipment_id=match["shipment_id"],
                    order_id=match["order_id"],
                    source_message_id=match["source_message_id"],
                    evidence_type="EXACT_SHIPMENT_TTN",
                    created_by=actor_id,
                )
                self.db.add(stored)
            created += 1
            self.db.add(AuditLog(
                workspace_id=workspace_id,
                user_id=actor_id,
                entity_type="DIRECT_ORDER_SHIPMENT_LINK",
                entity_id=str(conversation_id),
                action="CONFIRM_EXACT_TTN",
                old_value=None,
                new_value={
                    "order_id": str(match["order_id"]),
                    "shipment_id": str(match["shipment_id"]),
                    "source_message_id": str(match["source_message_id"]),
                    "evidence_type": "EXACT_SHIPMENT_TTN",
                },
            ))

        primary_updated = False
        # Legacy one-order field is only for an unambiguous single-order dialog;
        # the relation table preserves all multi-order history.
        if len(actual_order_ids) == 1 and conversation.linked_order_id is None:
            conversation.linked_order_id = next(iter(actual_order_ids))
            primary_updated = True
            self.db.add(AuditLog(
                workspace_id=workspace_id,
                user_id=actor_id,
                entity_type="DIRECT_CONVERSATION",
                entity_id=str(conversation_id),
                action="LINK_VERIFIED_ORDER",
                old_value={"linked_order_id": None},
                new_value={"linked_order_id": str(conversation.linked_order_id)},
            ))
        self.db.flush()
        return {
            "confirmed_order_count": len(actual_order_ids),
            "created_links": created,
            "existing_links": existing,
            "primary_order_linked": primary_updated,
        }