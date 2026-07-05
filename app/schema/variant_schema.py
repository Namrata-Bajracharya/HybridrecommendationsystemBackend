from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


class VariantAttribute(BaseModel):
    name: str = Field(..., description="Attribute name e.g. color, size, shape")
    value: str = Field(..., description="Attribute value e.g. Red, 8, Round")


class VariantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    attributes: Optional[list[VariantAttribute]] = None
    price: Optional[float] = Field(None, gt=0)
    buying_price: Optional[float] = Field(None, ge=0)
    selling_price: Optional[float] = Field(None, ge=0)
    stock_quantity: int = Field(default=0, ge=0)
    sku: Optional[str] = None
    image_document_id: Optional[str] = None
    image_data_url: Optional[str] = None
    sort_order: int = 0


class VariantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    attributes: Optional[list[VariantAttribute]] = None
    price: Optional[float] = Field(None, gt=0)
    buying_price: Optional[float] = Field(None, ge=0)
    selling_price: Optional[float] = Field(None, ge=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    sku: Optional[str] = None
    image_document_id: Optional[str] = None
    sort_order: Optional[int] = None


class VariantBulkCreate(BaseModel):
    variants: list[VariantCreate]


class DocumentRef(BaseModel):
    id: str
    relative_path: str

    model_config = {"from_attributes": True}


class VariantPublic(BaseModel):
    id: int
    product_id: int
    name: str
    attributes: Optional[Any] = None
    price: Optional[float] = None
    buying_price: Optional[float] = None
    selling_price: Optional[float] = None
    stock_quantity: int
    sku: Optional[str] = None
    image_document_id: Optional[str] = None
    sort_order: int
    created_at: datetime
    document: Optional[DocumentRef] = None

    model_config = {"from_attributes": True}
