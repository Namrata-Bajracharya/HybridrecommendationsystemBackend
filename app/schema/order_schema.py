from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class OrderItemResponse(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: int
    unit_price: float
    unit_cost: Optional[float] = None
    name: Optional[str] = None
    size: Optional[str] = None
    variant_name: Optional[str] = None

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: int
    order_number: str
    total_amount: float
    status: str
    order_date: datetime
    order_items: List[OrderItemResponse]
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    payment_mode: str = "cod"
    cancel_reason: Optional[str] = None
    cancelled_by: Optional[str] = None
    reject_reason: Optional[str] = None
    accepted_at: Optional[datetime] = None
    packed_at: Optional[datetime] = None
    on_delivery_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    refund_requested_at: Optional[datetime] = None
    refund_out_for_pickup_at: Optional[datetime] = None
    item_retrieved_from_customer_at: Optional[datetime] = None
    item_retrieved_by_admin_at: Optional[datetime] = None
    refund_on_the_way_at: Optional[datetime] = None
    refund_successful_at: Optional[datetime] = None

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
    contact_email: Optional[str] = None
    payment_mode: str = "cod"
    shipping_cost: float = 0
    tax: float = 0
    discount: float = 0
    shipping_address: Optional[dict] = None
    cancel_reason: Optional[str] = None
    cancelled_by: Optional[str] = None
    reject_reason: Optional[str] = None
    refund_reason: Optional[str] = None
    refund_description: Optional[str] = None
    refund_proof_images: Optional[str] = None
    refund_payment_proof: Optional[str] = None
    accepted_at: Optional[datetime] = None
    packed_at: Optional[datetime] = None
    on_delivery_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    refund_requested_at: Optional[datetime] = None
    refund_out_for_pickup_at: Optional[datetime] = None
    item_retrieved_from_customer_at: Optional[datetime] = None
    item_retrieved_by_admin_at: Optional[datetime] = None
    refund_on_the_way_at: Optional[datetime] = None
    refund_successful_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CancelOrderRequest(BaseModel):
    reason: str
    cancelled_by: str = "admin"


class RejectOrderRequest(BaseModel):
    reason: str


class RefundRequest(BaseModel):
    reason: str
    description: Optional[str] = None
    proof_images: Optional[list[str]] = None


class RefundActionRequest(BaseModel):
    proof_image: Optional[str] = None
