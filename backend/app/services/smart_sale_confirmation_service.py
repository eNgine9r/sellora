"""External Nova Poshta TTN -> human-approved Direct sale, exactly once per TTN.

No banking API, no outbound Instagram activity, no provider statement assertions.
A proposal is never automatically recorded as a sale. An explicit manager click
attests to reviewing the details, customer receipt AND actual funds in the bank.
"""
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_direct import DirectConversation
from app.models.customer import CustomerLifecycleStatus
from app.models.direct_order_shipment_link import DirectOrderShipmentLink
from app.models.nova_poshta_external_document import NovaPoshtaExternalDocument
from app.models.order import OrderStatus, PaymentStatus
from app.models.shipment import ShipmentCarrier, ShipmentStatus
from app.models.workspace import Workspace
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.nova_poshta_external_repository import NovaPoshtaExternalRepository
from app.repositories.product_repository import ProductVariantRepository
from app.schemas.order import OrderCreate, OrderItemCreate
from app.schemas.shipment import ShipmentCreate
from app.schemas.smart_sale import SmartSaleCandidate, SmartSaleConfirmRequest, SmartSaleConfirmResult, SmartSaleSuggestion
from app.services.direct_customer_automation_service import DirectCustomerAutomationError, DirectCustomerAutomationService
from app.services.direct_order_proposal_service import DirectOrderProposalService, ProposalConversationNotFound
from app.services.order_service import OrderService, OrderServiceError
from app.services.shipment_service import ShipmentService, ShipmentServiceError


class SmartSaleError(ValueError):
    pass


class SmartSaleConfirmationService:
    def __init__(self, db: Session):
        self.db = db
        self.external = NovaPoshtaExternalRepository(db)
        self.proposals = DirectOrderProposalService(db)
        self.customer_automation = DirectCustomerAutomationService(db)
        self.orders = OrderService(db)
        self.shipments = ShipmentService(db)
        self.audit = AuditLogRepository(db)

    @staticmethod
    def _mask(tracking: str) -> str:
        return tracking[:4] + "••••••" + tracking[-4:]

    def _document(self, workspace_id: UUID, document_id: UUID, *, lock: bool = False):
        stmt = select(NovaPoshtaExternalDocument).where(
            NovaPoshtaExternalDocument.workspace_id == workspace_id,
            NovaPoshtaExternalDocument.id == document_id,
            NovaPoshtaExternalDocument.deleted_at.is_(None),
        )
        if lock:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        return self.db.execute(stmt).scalar_one_or_none()

    def _evidence(self, workspace_id: UUID, document_id: UUID) -> dict:
        return self.external.direct_evidence_by_document(workspace_id, [document_id]).get(document_id, {})

    def _suggestion(self, workspace_id: UUID, conversation_id: UUID) -> SmartSaleSuggestion | None:
        try:
            proposal = self.proposals.get(workspace_id, conversation_id)
        except ProposalConversationNotFound:
            return None
        # The AI analysis is a hint, never a source of final item/price facts.
        # Only a literal inbound SKU and a single unambiguous variant may be
        # presented as a one-click candidate, subject to manager review.
        if proposal.catalog_truncated or proposal.context_truncated:
            return None
        matched = [line for line in proposal.lines
                   if line.source == "INBOUND_SKU" and line.match_status == "MATCHED"
                   and not line.requires_review and len(line.candidates) == 1
                   and line.evidence and not line.candidates_truncated]
        if len(matched) != 1:
            return None
        line, item = matched[0], matched[0].candidates[0]
        if item.price is None or item.price <= 0:
            return None
        if item.available_quantity is None or item.available_quantity < line.quantity:
            return None
        return SmartSaleSuggestion(
            variant_id=item.variant_id, sku=item.sku, product_name=item.product_name,
            quantity=line.quantity, suggested_unit_price=item.price,
            available_quantity=item.available_quantity,
        )

    def list(self, workspace_id: UUID) -> list[SmartSaleCandidate]:
        docs = self.external.list_for_workspace(workspace_id, state=None, limit=100)
        evidence = self.external.direct_evidence_by_document(workspace_id, [doc.id for doc in docs])
        result = []
        for doc in docs:
            if doc.match_state == "LINKED":
                continue
            match = evidence.get(doc.id, {})
            conversation_id = match.get("direct_conversation_id") if match.get("direct_match_state") == "MATCHED" else None
            conversation = self.db.scalar(
                select(DirectConversation).where(
                    DirectConversation.id == conversation_id,
                    DirectConversation.workspace_id == workspace_id,
                    DirectConversation.deleted_at.is_(None),
                )
            ) if conversation_id else None
            customer_id = match.get("direct_customer_id")
            suggestion = self._suggestion(workspace_id, conversation_id) if conversation_id else None
            if doc.match_state != "UNMATCHED":
                reason = "EXTERNAL_TTN_CONFLICT"
            elif doc.matched_shipment_id:
                reason = "EXTERNAL_TTN_ALREADY_LINKED"
            elif match.get("direct_match_state") != "MATCHED":
                reason = "DIRECT_MATCH_AMBIGUOUS_OR_MISSING"
            elif suggestion is None:
                reason = "PRODUCT_OR_PRICE_NEEDS_REVIEW"
            else:
                reason = "READY_FOR_HUMAN_APPROVAL"
            state = "READY_FOR_REVIEW" if reason == "READY_FOR_HUMAN_APPROVAL" else "NEEDS_INFO"
            result.append(SmartSaleCandidate(
                document_id=doc.id, tracking_masked=self._mask(doc.tracking_number),
                provider_status=doc.provider_status, state=state, conversation_id=conversation_id,
                customer_id=customer_id, customer_instagram=(conversation.participant_username if conversation else None),
                suggested_item=suggestion, reason=reason,
            ))
        return result

    def confirm(self, workspace_id: UUID, document_id: UUID, payload: SmartSaleConfirmRequest, actor_id: UUID) -> SmartSaleConfirmResult:
        # Row lock serializes two clicks in one tenant and concurrent NP ingest.
        doc = self._document(workspace_id, document_id, lock=True)
        if doc is None:
            raise SmartSaleError("EXTERNAL_TTN_NOT_FOUND")
        if doc.match_state == "LINKED" and doc.matched_shipment_id:
            from app.models.shipment import Shipment
            shipment = self.db.scalar(select(Shipment).where(
                Shipment.workspace_id == workspace_id, Shipment.id == doc.matched_shipment_id,
                Shipment.deleted_at.is_(None),
            ))
            existing_link = self.db.scalar(select(DirectOrderShipmentLink).where(
                DirectOrderShipmentLink.workspace_id == workspace_id,
                DirectOrderShipmentLink.shipment_id == doc.matched_shipment_id,
                DirectOrderShipmentLink.conversation_id == payload.expected_conversation_id,
                DirectOrderShipmentLink.evidence_type == "EXACT_TTN_HUMAN_APPROVED",
                DirectOrderShipmentLink.deleted_at.is_(None),
            ))
            if shipment and shipment.order_id and shipment.customer_id and existing_link and existing_link.order_id == shipment.order_id:
                from app.models.order import Order
                from app.models.order_item import OrderItem
                order = self.db.scalar(select(Order).where(
                    Order.workspace_id == workspace_id, Order.id == shipment.order_id,
                    Order.payment_status == PaymentStatus.PAID.value, Order.deleted_at.is_(None),
                ))
                lines = self.db.scalars(select(OrderItem).where(
                    OrderItem.workspace_id == workspace_id, OrderItem.order_id == shipment.order_id,
                    OrderItem.deleted_at.is_(None),
                )).all()
                if (order is not None and len(lines) == 1 and
                    lines[0].product_variant_id == payload.product_variant_id and
                    lines[0].quantity == payload.quantity and
                    Decimal(lines[0].unit_price) == payload.unit_price):
                    return SmartSaleConfirmResult(document_id=doc.id, order_id=shipment.order_id,
                        customer_id=shipment.customer_id, shipment_id=shipment.id,
                        payment_status="PAID", already_confirmed=True)
                raise SmartSaleError("SALE_ALREADY_CONFIRMED_WITH_DIFFERENT_DETAILS")
        if doc.match_state != "UNMATCHED" or doc.matched_shipment_id:
            raise SmartSaleError("EXTERNAL_TTN_NOT_ELIGIBLE")
        currency = self.db.scalar(select(Workspace.currency_code).where(Workspace.id == workspace_id))
        if currency != "UAH":
            raise SmartSaleError("ONLY_UAH_WORKSPACES_SUPPORTED")
        match = self._evidence(workspace_id, document_id)
        if match.get("direct_match_state") != "MATCHED" or match.get("direct_conversation_id") != payload.expected_conversation_id:
            raise SmartSaleError("DIRECT_EVIDENCE_CHANGED")
        conversation = self.customer_automation.conversations.get(workspace_id, payload.expected_conversation_id)
        if conversation is None:
            raise SmartSaleError("DIRECT_CONVERSATION_NOT_FOUND")
        # A long-running Instagram thread can produce several independent
        # sales: one DirectConversation.linked_order_id is not an exclusivity
        # constraint. The unique external TTN is the idempotency key.
        if payload.selection_source == "CATALOG_SUGGESTION":
            suggested = self._suggestion(workspace_id, payload.expected_conversation_id)
            if suggested is None or suggested.variant_id != payload.product_variant_id or suggested.quantity != payload.quantity:
                raise SmartSaleError("PRODUCT_EVIDENCE_CHANGED")
        # MANAGER_SELECTED deliberately permits manual selection of a real
        # catalog variant where Direct contains no unambiguous SKU. Existing
        # OrderService.create checks tenant ownership, active variant, stock,
        # amount and price. One-click still requires all human attestations.
        if payload.unit_price <= 0:
            raise SmartSaleError("PRICE_REQUIRED")
        # Do not infer actual negotiated price from catalog: the submitted
        # price is explicitly reviewed/confirmed by the manager.
        try:
            state = self.customer_automation.ensure_candidate(
                workspace_id, payload.expected_conversation_id, actor_id, commit=False,
            )
            customer = state.customer
            if customer is None:
                raise SmartSaleError("CUSTOMER_IDENTITY_MISSING")
            order = self.orders.create(workspace_id, OrderCreate(
                customer_id=customer.id, status=OrderStatus.CONFIRMED,
                payment_status=PaymentStatus.PAID,
                items=[OrderItemCreate(
                    product_variant_id=payload.product_variant_id, quantity=payload.quantity,
                    unit_price=payload.unit_price, unit_cost=Decimal("0"),
                    cost_confirmed=False,
                )],
                notes="Smart Sale: оплата перевірена менеджером після оформлення зовнішньої ТТН; сума та товар підтверджені вручну.",
            ), actor_id, commit=False)
            shipment = self.shipments.create(workspace_id, ShipmentCreate(
                order_id=order.id, customer_id=customer.id, carrier=ShipmentCarrier.NOVA_POSHTA,
                status=ShipmentStatus.CREATED, tracking_number=doc.tracking_number,
            ), actor_id, commit=False)
        except (OrderServiceError, ShipmentServiceError, DirectCustomerAutomationError) as exc:
            raise SmartSaleError(str(exc)) from exc

        # Preserve the authoritative external document; no second TTN created
        # at Nova Poshta, no message sent to Instagram.
        # Preserve carrier reference/status without claiming the label was
        # created by Sellora. Carrier tracking may update status later.
        from app.models.shipment import Shipment
        stored_shipment = self.db.scalar(select(Shipment).where(
            Shipment.id == shipment.id, Shipment.workspace_id == workspace_id,
            Shipment.deleted_at.is_(None),
        ))
        if stored_shipment:
            stored_shipment.external_provider = "NOVA_POSHTA"
            stored_shipment.external_ref = doc.document_ref
            stored_shipment.external_status = (doc.provider_status or "")[:120] or None
            stored_shipment.nova_poshta_document_ref = doc.document_ref
            stored_shipment.nova_poshta_document_number = doc.tracking_number
            stored_shipment.nova_poshta_raw_status = doc.provider_status
        doc.matched_shipment_id = shipment.id
        doc.match_state = "LINKED"
        self.db.add(DirectOrderShipmentLink(
            workspace_id=workspace_id, conversation_id=conversation.id,
            order_id=order.id, shipment_id=shipment.id,
            evidence_type="EXACT_TTN_HUMAN_APPROVED",
            created_by=actor_id,
        ))
        if conversation.linked_order_id is None:
            conversation.linked_order_id = order.id
        # Move prospect to customer without inventing unprovided delivery PII.
        from app.models.customer import Customer
        db_customer = self.db.scalar(select(Customer).where(
            Customer.id == customer.id, Customer.workspace_id == workspace_id,
            Customer.deleted_at.is_(None),
        ))
        if db_customer:
            db_customer.lifecycle_status = CustomerLifecycleStatus.CUSTOMER.value
        self.audit.create(
            workspace_id=workspace_id, user_id=actor_id, entity_type="Order",
            entity_id=order.id, action="SMART_SALE_APPROVED",
            new_value={"source": "NP_EXTERNAL_TTN_AND_DIRECT", "external_document_id": str(doc.id),
                "conversation_id": str(conversation.id), "shipment_id": str(shipment.id),
                "manual_receipt_checked": True, "manual_funds_checked": True,
                "payment_verification": "HUMAN_ATTESTATION_NOT_BANK_API",
                "amount_minor": int(payload.unit_price * payload.quantity * 100),
                "price_source": "MANAGER_REVIEWED",
                "selection_source": payload.selection_source},
        )
        self.db.commit()
        return SmartSaleConfirmResult(document_id=doc.id, order_id=order.id,
            customer_id=customer.id, shipment_id=shipment.id, payment_status="PAID")
