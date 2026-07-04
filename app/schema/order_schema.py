from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class OrderItemResponse(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: int
    unit_price: float

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: int
    order_number: str
    total_amount: float
    status: str
    order_date: datetime
    order_items: List[OrderItemResponse]

    model_config = {"from_attributes": True}


class OrderCreateRequest(BaseModel):
    shipping_address_id: int
    billing_address_id: int


class DirectOrderItem(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    name: str
    price: float
    quantity: int


class DirectOrderRequest(BaseModel):
    items: List[DirectOrderItem]
    total_amount: float
    shipping_cost: float
    tax: float
    discount: float = 0
    contact_name: str
    contact_phone: str
    contact_email: str
    payment_mode: str = "cod"
    shipping_address: Optional[str] = None
    shipping_district: Optional[str] = None
    shipping_zone: Optional[str] = None


class OrderListResponse(BaseModel):
    id: int
    order_number: str
    total_amount: float
    status: str
    order_date: datetime
    order_items: List[OrderItemResponse]
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    payment_mode: str = "cod"
    cancel_reason: Optional[str] = None
    cancelled_by: Optional[str] = None
    refund_reason: Optional[str] = None

    model_config = {"from_attributes": True}


class CancelOrderRequest(BaseModel):
    reason: str
    cancelled_by: str = "admin"


class RefundRequest(BaseModel):
    reason: str
