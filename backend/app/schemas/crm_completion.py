from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.attachment import AttachmentEntityType


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    color: str = Field(default="#2563eb", max_length=30)


class TagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    color: str | None = Field(default=None, max_length=30)


class TagResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    color: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerTagResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    customer_id: UUID
    tag_id: UUID
    tag: TagResponse | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerNoteCreate(BaseModel):
    note: str = Field(min_length=1)


class CustomerNoteResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    customer_id: UUID
    note: str
    created_by: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerAddressCreate(BaseModel):
    label: str | None = Field(default=None, max_length=100)
    recipient_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    address_line1: str = Field(min_length=1, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=120)
    region: str | None = Field(default=None, max_length=120)
    postal_code: str | None = Field(default=None, max_length=40)
    country: str | None = Field(default=None, max_length=120)
    notes: str | None = None
    is_default: bool = False


class CustomerAddressUpdate(BaseModel):
    label: str | None = Field(default=None, max_length=100)
    recipient_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    address_line1: str | None = Field(default=None, min_length=1, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=120)
    region: str | None = Field(default=None, max_length=120)
    postal_code: str | None = Field(default=None, max_length=40)
    country: str | None = Field(default=None, max_length=120)
    notes: str | None = None
    is_default: bool | None = None


class CustomerAddressResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    customer_id: UUID
    label: str | None
    recipient_name: str | None
    phone: str | None
    address_line1: str
    address_line2: str | None
    city: str | None
    region: str | None
    postal_code: str | None
    country: str | None
    notes: str | None
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttachmentCreate(BaseModel):
    entity_type: AttachmentEntityType
    entity_id: UUID
    file_url: str = Field(min_length=1, max_length=1000)
    file_name: str | None = Field(default=None, max_length=255)
    content_type: str | None = Field(default=None, max_length=120)


class AttachmentResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    entity_type: AttachmentEntityType
    entity_id: UUID
    file_url: str
    file_name: str | None
    content_type: str | None
    uploaded_by: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
