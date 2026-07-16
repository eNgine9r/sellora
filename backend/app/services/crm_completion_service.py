from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.attachment import Attachment, AttachmentEntityType
from app.models.customer import Customer
from app.models.customer_address import CustomerAddress
from app.models.customer_note import CustomerNote
from app.models.customer_tag import CustomerTag
from app.models.lead import Lead
from app.models.order import Order
from app.models.product import Product
from app.models.tag import Tag
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.crm_completion_repository import AttachmentRepository, CustomerCrmRepository, TagRepository
from app.schemas.crm_completion import (
    AttachmentCreate,
    CustomerAddressCreate,
    CustomerAddressUpdate,
    CustomerNoteCreate,
    TagCreate,
    TagUpdate,
)
from app.services.business_utils import snapshot


class CrmCompletionServiceError(ValueError):
    pass


class TagService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.tags = TagRepository(db)
        self.audit_logs = AuditLogRepository(db)

    def list(self, workspace_id: UUID) -> list[Tag]:
        return self.tags.list_for_workspace(workspace_id)

    def create(self, workspace_id: UUID, payload: TagCreate, actor_user_id: UUID | None) -> Tag:
        tag = self.tags.create(Tag(workspace_id=workspace_id, **payload.model_dump()))
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="Tag",
            entity_id=tag.id,
            action="CREATE",
            new_value=snapshot(tag),
        )
        self.db.commit()
        self.db.refresh(tag)
        return tag

    def update(self, workspace_id: UUID, tag_id: UUID, payload: TagUpdate, actor_user_id: UUID | None) -> Tag | None:
        tag = self.tags.get(workspace_id, tag_id)
        if tag is None:
            return None

        old_value = snapshot(tag)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(tag, field, value)

        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="Tag",
            entity_id=tag.id,
            action="UPDATE",
            old_value=old_value,
            new_value=snapshot(tag),
        )
        self.db.commit()
        self.db.refresh(tag)
        return tag

    def delete(self, workspace_id: UUID, tag_id: UUID, actor_user_id: UUID | None) -> bool:
        tag = self.tags.get(workspace_id, tag_id)
        if tag is None:
            return False

        old_value = snapshot(tag)
        self.tags.soft_delete(tag, actor_user_id)
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="Tag",
            entity_id=tag.id,
            action="DELETE",
            old_value=old_value,
            new_value=snapshot(tag),
        )
        self.db.commit()
        return True


class CustomerCrmService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.tags = TagRepository(db)
        self.customer_crm = CustomerCrmRepository(db)
        self.audit_logs = AuditLogRepository(db)

    def list_customer_tags(self, workspace_id: UUID, customer_id: UUID) -> list[CustomerTag]:
        self._require_customer(workspace_id, customer_id)
        return self.customer_crm.list_tags(workspace_id, customer_id)

    def add_customer_tag(
        self,
        workspace_id: UUID,
        customer_id: UUID,
        tag_id: UUID,
        actor_user_id: UUID | None,
    ) -> CustomerTag:
        self._require_customer(workspace_id, customer_id)
        if self.tags.get(workspace_id, tag_id) is None:
            raise CrmCompletionServiceError("Tag does not exist in this workspace")

        existing = self.customer_crm.get_customer_tag(workspace_id, customer_id, tag_id)
        if existing:
            return existing

        customer_tag = self.customer_crm.add_tag(
            CustomerTag(workspace_id=workspace_id, customer_id=customer_id, tag_id=tag_id)
        )
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="CustomerTag",
            entity_id=customer_tag.id,
            action="CREATE",
            new_value=snapshot(customer_tag),
        )
        self.db.commit()
        self.db.refresh(customer_tag)
        return customer_tag

    def remove_customer_tag(
        self,
        workspace_id: UUID,
        customer_id: UUID,
        tag_id: UUID,
        actor_user_id: UUID | None,
    ) -> bool:
        customer_tag = self.customer_crm.get_customer_tag(workspace_id, customer_id, tag_id)
        if customer_tag is None:
            return False

        old_value = snapshot(customer_tag)
        customer_tag.deleted_at = datetime.now(UTC)
        customer_tag.deleted_by = actor_user_id
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="CustomerTag",
            entity_id=customer_tag.id,
            action="DELETE",
            old_value=old_value,
            new_value=snapshot(customer_tag),
        )
        self.db.commit()
        return True

    def list_notes(self, workspace_id: UUID, customer_id: UUID) -> list[CustomerNote]:
        self._require_customer(workspace_id, customer_id)
        return self.customer_crm.list_notes(workspace_id, customer_id)

    def add_note(
        self,
        workspace_id: UUID,
        customer_id: UUID,
        payload: CustomerNoteCreate,
        actor_user_id: UUID | None,
    ) -> CustomerNote:
        self._require_customer(workspace_id, customer_id)
        note = self.customer_crm.add_note(
            CustomerNote(
                workspace_id=workspace_id,
                customer_id=customer_id,
                note=payload.note,
                created_by=actor_user_id,
            )
        )
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="CustomerNote",
            entity_id=note.id,
            action="CREATE",
            new_value=snapshot(note),
        )
        self.db.commit()
        self.db.refresh(note)
        return note

    def list_addresses(self, workspace_id: UUID, customer_id: UUID) -> list[CustomerAddress]:
        self._require_customer(workspace_id, customer_id)
        return self.customer_crm.list_addresses(workspace_id, customer_id)

    def add_address(
        self,
        workspace_id: UUID,
        customer_id: UUID,
        payload: CustomerAddressCreate,
        actor_user_id: UUID | None,
    ) -> CustomerAddress:
        self._require_customer(workspace_id, customer_id)
        if payload.is_default:
            self.customer_crm.clear_default_addresses(workspace_id, customer_id)

        address = self.customer_crm.add_address(
            CustomerAddress(workspace_id=workspace_id, customer_id=customer_id, **payload.model_dump())
        )
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="CustomerAddress",
            entity_id=address.id,
            action="CREATE",
            new_value=snapshot(address),
        )
        self.db.commit()
        self.db.refresh(address)
        return address

    def update_address(
        self,
        workspace_id: UUID,
        customer_id: UUID,
        address_id: UUID,
        payload: CustomerAddressUpdate,
        actor_user_id: UUID | None,
    ) -> CustomerAddress | None:
        address = self.customer_crm.get_address(workspace_id, customer_id, address_id)
        if address is None:
            return None

        old_value = snapshot(address)
        values = payload.model_dump(exclude_unset=True)
        is_nova_poshta_address = (
            values.get("delivery_provider", address.delivery_provider) == "NOVA_POSHTA"
            or bool(address.nova_poshta_city_ref)
            or bool(values.get("nova_poshta_city_ref"))
        )
        city_changed = "nova_poshta_city_ref" in values and values.get("nova_poshta_city_ref") != address.nova_poshta_city_ref
        if is_nova_poshta_address and city_changed:
            if not values.get("nova_poshta_warehouse_ref"):
                raise CrmCompletionServiceError("NOVA_POSHTA_WAREHOUSE_REQUIRED_AFTER_CITY_CHANGE")
            if not values.get("address_line1"):
                raise CrmCompletionServiceError("NOVA_POSHTA_WAREHOUSE_DESCRIPTION_REQUIRED")
        if is_nova_poshta_address and "nova_poshta_warehouse_ref" in values and not values.get("address_line1"):
            raise CrmCompletionServiceError("NOVA_POSHTA_WAREHOUSE_DESCRIPTION_REQUIRED")
        if values.get("is_default") is True:
            self.customer_crm.clear_default_addresses(workspace_id, customer_id, address.id)
        for field, value in values.items():
            setattr(address, field, value)

        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="CustomerAddress",
            entity_id=address.id,
            action="UPDATE",
            old_value=old_value,
            new_value=snapshot(address),
        )
        self.db.commit()
        self.db.refresh(address)
        return address

    def delete_address(
        self,
        workspace_id: UUID,
        customer_id: UUID,
        address_id: UUID,
        actor_user_id: UUID | None,
    ) -> bool:
        address = self.customer_crm.get_address(workspace_id, customer_id, address_id)
        if address is None:
            return False

        old_value = snapshot(address)
        address.deleted_at = datetime.now(UTC)
        address.deleted_by = actor_user_id
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="CustomerAddress",
            entity_id=address.id,
            action="DELETE",
            old_value=old_value,
            new_value=snapshot(address),
        )
        self.db.commit()
        return True

    def _require_customer(self, workspace_id: UUID, customer_id: UUID) -> Customer:
        customer = self.db.get(Customer, customer_id)
        if customer is None or customer.workspace_id != workspace_id or customer.deleted_at is not None:
            raise CrmCompletionServiceError("Customer does not exist in this workspace")
        return customer


class AttachmentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.attachments = AttachmentRepository(db)
        self.audit_logs = AuditLogRepository(db)

    def list(
        self,
        workspace_id: UUID,
        entity_type: AttachmentEntityType | None = None,
        entity_id: UUID | None = None,
    ) -> list[Attachment]:
        return self.attachments.list_for_workspace(workspace_id, entity_type.value if entity_type else None, entity_id)

    def create(self, workspace_id: UUID, payload: AttachmentCreate, actor_user_id: UUID | None) -> Attachment:
        self._validate_entity(workspace_id, payload.entity_type, payload.entity_id)
        attachment = self.attachments.create(
            Attachment(
                workspace_id=workspace_id,
                entity_type=payload.entity_type.value,
                entity_id=payload.entity_id,
                file_url=payload.file_url,
                file_name=payload.file_name,
                content_type=payload.content_type,
                uploaded_by=actor_user_id,
            )
        )
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="Attachment",
            entity_id=attachment.id,
            action="CREATE",
            new_value=snapshot(attachment),
        )
        self.db.commit()
        self.db.refresh(attachment)
        return attachment

    def delete(self, workspace_id: UUID, attachment_id: UUID, actor_user_id: UUID | None) -> bool:
        attachment = self.attachments.get(workspace_id, attachment_id)
        if attachment is None:
            return False

        old_value = snapshot(attachment)
        self.attachments.soft_delete(attachment, actor_user_id)
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="Attachment",
            entity_id=attachment.id,
            action="DELETE",
            old_value=old_value,
            new_value=snapshot(attachment),
        )
        self.db.commit()
        return True

    def _validate_entity(self, workspace_id: UUID, entity_type: AttachmentEntityType, entity_id: UUID) -> None:
        model_map = {
            AttachmentEntityType.CUSTOMER: Customer,
            AttachmentEntityType.LEAD: Lead,
            AttachmentEntityType.ORDER: Order,
            AttachmentEntityType.PRODUCT: Product,
        }
        model = model_map.get(entity_type)
        if model is None:
            return

        entity = self.db.get(model, entity_id)
        if entity is None or entity.workspace_id != workspace_id or entity.deleted_at is not None:
            raise CrmCompletionServiceError(f"{entity_type.value} does not exist in this workspace")
