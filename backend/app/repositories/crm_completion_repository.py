from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.models.attachment import Attachment
from app.models.customer_address import CustomerAddress
from app.models.customer_note import CustomerNote
from app.models.customer_tag import CustomerTag
from app.models.tag import Tag


class TagRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_workspace(self, workspace_id: UUID) -> list[Tag]:
        stmt = (
            select(Tag)
            .where(Tag.workspace_id == workspace_id, Tag.deleted_at.is_(None))
            .order_by(Tag.name)
        )
        return list(self.db.execute(stmt).scalars())

    def get(self, workspace_id: UUID, tag_id: UUID) -> Tag | None:
        stmt = select(Tag).where(
            Tag.workspace_id == workspace_id,
            Tag.id == tag_id,
            Tag.deleted_at.is_(None),
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, tag: Tag) -> Tag:
        self.db.add(tag)
        self.db.flush()
        return tag

    def soft_delete(self, tag: Tag, deleted_by: UUID | None) -> None:
        tag.deleted_at = datetime.now(UTC)
        tag.deleted_by = deleted_by
        self.db.flush()


class CustomerCrmRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_tags(self, workspace_id: UUID, customer_id: UUID) -> list[CustomerTag]:
        stmt = (
            select(CustomerTag)
            .where(
                CustomerTag.workspace_id == workspace_id,
                CustomerTag.customer_id == customer_id,
                CustomerTag.deleted_at.is_(None),
            )
            .options(selectinload(CustomerTag.tag))
        )
        return list(self.db.execute(stmt).scalars())

    def get_customer_tag(self, workspace_id: UUID, customer_id: UUID, tag_id: UUID) -> CustomerTag | None:
        stmt = select(CustomerTag).where(
            CustomerTag.workspace_id == workspace_id,
            CustomerTag.customer_id == customer_id,
            CustomerTag.tag_id == tag_id,
            CustomerTag.deleted_at.is_(None),
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def add_tag(self, customer_tag: CustomerTag) -> CustomerTag:
        self.db.add(customer_tag)
        self.db.flush()
        return customer_tag

    def list_notes(self, workspace_id: UUID, customer_id: UUID) -> list[CustomerNote]:
        stmt = (
            select(CustomerNote)
            .where(
                CustomerNote.workspace_id == workspace_id,
                CustomerNote.customer_id == customer_id,
                CustomerNote.deleted_at.is_(None),
            )
            .order_by(CustomerNote.created_at.desc())
        )
        return list(self.db.execute(stmt).scalars())

    def add_note(self, note: CustomerNote) -> CustomerNote:
        self.db.add(note)
        self.db.flush()
        return note

    def list_addresses(self, workspace_id: UUID, customer_id: UUID) -> list[CustomerAddress]:
        stmt = (
            select(CustomerAddress)
            .where(
                CustomerAddress.workspace_id == workspace_id,
                CustomerAddress.customer_id == customer_id,
                CustomerAddress.deleted_at.is_(None),
            )
            .order_by(CustomerAddress.is_default.desc(), CustomerAddress.created_at.desc())
        )
        return list(self.db.execute(stmt).scalars())

    def get_address(self, workspace_id: UUID, customer_id: UUID, address_id: UUID) -> CustomerAddress | None:
        stmt = select(CustomerAddress).where(
            CustomerAddress.workspace_id == workspace_id,
            CustomerAddress.customer_id == customer_id,
            CustomerAddress.id == address_id,
            CustomerAddress.deleted_at.is_(None),
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def add_address(self, address: CustomerAddress) -> CustomerAddress:
        self.db.add(address)
        self.db.flush()
        return address

    def clear_default_addresses(
        self,
        workspace_id: UUID,
        customer_id: UUID,
        except_address_id: UUID | None = None,
    ) -> None:
        for address in self.list_addresses(workspace_id, customer_id):
            if except_address_id is None or address.id != except_address_id:
                address.is_default = False
        self.db.flush()


class AttachmentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_workspace(
        self,
        workspace_id: UUID,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
    ) -> list[Attachment]:
        stmt: Select[tuple[Attachment]] = select(Attachment).where(
            Attachment.workspace_id == workspace_id,
            Attachment.deleted_at.is_(None),
        )
        if entity_type:
            stmt = stmt.where(Attachment.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(Attachment.entity_id == entity_id)
        return list(self.db.execute(stmt.order_by(Attachment.created_at.desc())).scalars())

    def get(self, workspace_id: UUID, attachment_id: UUID) -> Attachment | None:
        stmt = select(Attachment).where(
            Attachment.workspace_id == workspace_id,
            Attachment.id == attachment_id,
            Attachment.deleted_at.is_(None),
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, attachment: Attachment) -> Attachment:
        self.db.add(attachment)
        self.db.flush()
        return attachment

    def soft_delete(self, attachment: Attachment, deleted_by: UUID | None) -> None:
        attachment.deleted_at = datetime.now(UTC)
        attachment.deleted_by = deleted_by
        self.db.flush()
