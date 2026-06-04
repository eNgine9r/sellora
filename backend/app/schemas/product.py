from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProductImageCreate(BaseModel):
    image_url: str = Field(min_length=1, max_length=1000)
    alt_text: str | None = Field(default=None, max_length=255)
    sort_order: int = Field(default=0, ge=0)
    is_primary: bool = False


class ProductImageUpdate(BaseModel):
    image_url: str | None = Field(default=None, min_length=1, max_length=1000)
    alt_text: str | None = Field(default=None, max_length=255)
    sort_order: int | None = Field(default=None, ge=0)
    is_primary: bool | None = None


class ProductImageResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    product_id: UUID
    image_url: str
    alt_text: str | None
    sort_order: int
    is_primary: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    sku: str | None = Field(default=None, max_length=120)
    description: str | None = None
    category: str | None = Field(default=None, max_length=255)
    brand: str | None = Field(default=None, max_length=120)
    is_active: bool = True
    images: list[ProductImageCreate] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    sku: str | None = Field(default=None, max_length=120)
    description: str | None = None
    category: str | None = Field(default=None, max_length=255)
    brand: str | None = Field(default=None, max_length=120)
    is_active: bool | None = None


class ProductResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    sku: str | None
    description: str | None
    category: str | None
    brand: str | None
    is_active: bool
    images: list[ProductImageResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductVariantCreate(BaseModel):
    product_id: UUID
    sku: str = Field(min_length=1, max_length=120)
    color: str | None = Field(default=None, max_length=80)
    size: str | None = Field(default=None, max_length=80)
    price: Decimal | None = Field(default=None, ge=0)
    barcode: str | None = Field(default=None, max_length=120)
    is_active: bool = True
    initial_stock_quantity: int = Field(default=0, ge=0)
    minimum_quantity: int = Field(default=0, ge=0)


class ProductVariantUpdate(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=120)
    color: str | None = Field(default=None, max_length=80)
    size: str | None = Field(default=None, max_length=80)
    price: Decimal | None = Field(default=None, ge=0)
    barcode: str | None = Field(default=None, max_length=120)
    is_active: bool | None = None


class ProductVariantResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    product_id: UUID
    sku: str
    color: str | None
    size: str | None
    price: Decimal | None
    barcode: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
