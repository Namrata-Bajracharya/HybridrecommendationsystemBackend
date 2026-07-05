from fastapi import APIRouter, Depends
from app.schema.user_schema import UserPublic
from app.services.order_service import OrderService
from app.dependencies import get_current_user, get_order_service_dep, get_optional_user
from app.schema.order_schema import (
    OrderCreateRequest, OrderResponse, DirectOrderRequest,
    OrderListResponse, CancelOrderRequest, RefundRequest, RejectOrderRequest,
    RefundActionRequest,
)
from typing import Annotated
from app.dependencies import get_db
from sqlalchemy.orm import Session

router = APIRouter(tags=["Orders"])

user_dependency = Annotated[UserPublic, Depends(get_current_user)]
order_dependency = Annotated[OrderService, Depends(get_order_service_dep)]


@router.post("", response_model=OrderResponse)
def place_order(
    payload: OrderCreateRequest,
    current_user: user_dependency,
    order_service: order_dependency,
):
    return order_service.place_order(
        user_id=current_user.id,
        shipping_id=payload.shipping_address_id,
        billing_id=payload.billing_address_id,
    )


@router.post("/direct", response_model=OrderResponse)
def place_direct_order(
    payload: DirectOrderRequest,
    current_user: user_dependency,
    order_service: order_dependency,
):
    return order_service.place_direct_order(
        user_id=current_user.id,
        items=[i.model_dump() for i in payload.items],
        total_amount=payload.total_amount,
        shipping_cost=payload.shipping_cost,
        tax=payload.tax,
        discount=payload.discount,
        contact_name=payload.contact_name,
        contact_phone=payload.contact_phone,
        contact_email=payload.contact_email,
        payment_mode=payload.payment_mode,
    )


@router.get("", response_model=list[OrderListResponse])
def list_orders(
    current_user: user_dependency,
    order_service: order_dependency,
):
    return order_service.list_orders(current_user.id)


@router.get("/admin/all", response_model=list[OrderListResponse])
def list_all_orders(
    _: user_dependency,
    order_service: order_dependency,
):
    return order_service.list_all_orders()


@router.get("/admin/{order_id}", response_model=OrderListResponse)
def get_admin_order(
    _: user_dependency,
    order_service: order_dependency,
    order_id: int,
):
    return order_service.get_admin_order(order_id)


@router.patch("/{order_id}/accept", response_model=OrderListResponse)
def accept_order(
    order_id: int,
    current_user: user_dependency,
    order_service: order_dependency,
):
    return order_service.accept_order(order_id)


@router.patch("/{order_id}/reject", response_model=OrderListResponse)
def reject_order(
    order_id: int,
    payload: RejectOrderRequest,
    current_user: user_dependency,
    order_service: order_dependency,
):
    return order_service.reject_order(order_id, reason=payload.reason)


@router.patch("/{order_id}/cancel", response_model=OrderListResponse)
def cancel_order(
    order_id: int,
    payload: CancelOrderRequest,
    current_user: user_dependency,
    order_service: order_dependency,
):
    return order_service.cancel_order(order_id, reason=payload.reason, cancelled_by=payload.cancelled_by)


@router.patch("/{order_id}/advance", response_model=OrderListResponse)
def advance_order(
    order_id: int,
    payload: dict,
    current_user: user_dependency,
    order_service: order_dependency,
):
    next_status = payload.get("status", "")
    return order_service.advance_status(order_id, next_status)


@router.post("/{order_id}/refund-request", response_model=OrderListResponse)
def request_refund(
    order_id: int,
    payload: RefundRequest,
    current_user: user_dependency,
    order_service: order_dependency,
):
    return order_service.request_refund(order_id, reason=payload.reason, description=payload.description, proof_images=payload.proof_images)


@router.patch("/{order_id}/refund/accept", response_model=OrderListResponse)
def accept_refund(
    order_id: int,
    current_user: user_dependency,
    order_service: order_dependency,
):
    return order_service.accept_refund(order_id)


@router.patch("/{order_id}/refund/item-retrieved-from-customer", response_model=OrderListResponse)
def item_retrieved_from_customer(
    order_id: int,
    current_user: user_dependency,
    order_service: order_dependency,
):
    return order_service.mark_item_retrieved_from_customer(order_id)


@router.patch("/{order_id}/refund/item-retrieved-by-admin", response_model=OrderListResponse)
def item_retrieved_by_admin(
    order_id: int,
    current_user: user_dependency,
    order_service: order_dependency,
):
    return order_service.mark_item_retrieved_by_admin(order_id)


@router.patch("/{order_id}/refund/initiate-payment", response_model=OrderListResponse)
def initiate_refund_payment(
    order_id: int,
    payload: RefundActionRequest,
    current_user: user_dependency,
    order_service: order_dependency,
):
    return order_service.initiate_refund_payment(order_id, proof_image=payload.proof_image)


@router.patch("/{order_id}/refund/complete", response_model=OrderListResponse)
def complete_refund(
    order_id: int,
    payload: RefundActionRequest,
    current_user: user_dependency,
    order_service: order_dependency,
):
    return order_service.complete_refund(order_id, proof_image=payload.proof_image)


@router.patch("/{order_id}/customer-cancel", response_model=OrderListResponse)
def customer_cancel(
    order_id: int,
    payload: CancelOrderRequest,
    current_user: user_dependency,
    order_service: order_dependency,
):
    return order_service.customer_cancel(order_id, payload.reason)


@router.get("/by-number/{order_number}", response_model=OrderListResponse)
def get_order_by_number(
    _: user_dependency, order_service: order_dependency, order_number: str
):
    return order_service.get_order_by_number(order_number)


@router.get("/{order_id}", response_model=OrderResponse)
def get_single_order(
    current_user: user_dependency, order_service: order_dependency, order_id: int
):
    return order_service.get_one_order(current_user.id, order_id)


@router.get("/{order_id}/invoice", response_model=OrderListResponse)
def get_order_invoice(
    current_user: user_dependency, order_service: order_dependency, order_id: int
):
    try:
        return order_service.get_one_order(current_user.id, order_id)
    except Exception:
        if current_user.role == "admin":
            return order_service.get_admin_order(order_id)
        raise HTTPException(status_code=404, detail="Order not found")
