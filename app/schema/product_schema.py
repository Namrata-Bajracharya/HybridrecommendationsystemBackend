from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from app.schema.category_schema import CategoryPublic


class DocumentRef(BaseModel):
    id: str
    original_filename: str
    stored_filename: str
    relative_path: str
    absolute_path: str
    mime_type: str | None = None
    size: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductImagePublic(BaseModel):
    id: int
    document_id: str
    sort_order: int
    document: Optional[DocumentRef] = None

    model_config = {"from_attributes": True}


class ProductBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    stock_quantity: Optional[int] = Field(0, ge=0)
    field_values: Optional[dict[str, Any]] = None
    category_id: Optional[int] = None
    is_active: Optional[bool] = True


class ProductCreate(ProductBase):
    image_document_ids: Optional[list[str]] = None
    image_data_urls: Optional[list[str]] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Cotton Kurtha",
                    "description": "Comfortable cotton kurtha",
                    "price": "1000",
                    "stock_quantity": 10,
                    "field_values": {"fabric": "cotton", "origin_place": "India"},
                    "category_id": 1,
                    "image_document_ids": ["uuid1", "uuid2"],
                }
            ]
        }
    }


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    sku: Optional[str] = Field(None, max_length=100)
    field_values: Optional[dict[str, Any]] = None
    category_id: Optional[int] = None
    is_active: Optional[bool] = None
    image_document_ids: Optional[list[str]] = None
    image_data_urls: Optional[list[str]] = None


class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    slug: str
    sku: str
    category: Optional[CategoryPublic] = None
    images: list[ProductImagePublic] = []
    average_rating: Optional[float] = Field(None, ge=0, le=5, description="Average rating from reviews (0-5)")
    review_count: int = Field(default=0, ge=0, description="Total number of reviews")
    in_stock: bool = Field(description="Whether product is currently in stock")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Cotton Kurtha",
                    "description": "Comfortable cotton kurtha",
                    "price": 1000,
                    "stock_quantity": 10,
                    "field_values": {"fabric": "cotton", "origin_place": "India"},
                    "category_id": 1,
                    "is_active": True,
                    "id": 1,
                    "created_at": "2025-11-14T08:21:58",
                    "slug": "cotton-kurtha-1",
                    "sku": "PRD-COTT-ONKU",
                    "images": [],
                    "average_rating": 4.5,
                    "review_count": 24,
                    "in_stock": True,
                }
            ]
        },
    }
