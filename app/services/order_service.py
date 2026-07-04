from app.crud.order import OrderCrud
from app.models.order import Order
from app.models.order_item import OrderItem
from app.utils.order_utils import generate_order_number, generate_trx_ref
from app.schema.order_schema import OrderListResponse, OrderItemResponse
from typing import Optional
from app.models.product import Product
from sqlalchemy.orm import Session
from datetime import datetime
from fastapi import HTTPException, status
from app.core.exceptions import OrderException
from app.websocket_manager import manager
from app.services.notification_service import NotificationService
import json
import asyncio


ADMIN_FLOW = ["order_received", "packed", "sent_for_delivery", "delivered", "paid"]


class OrderService:
    def __init__(self, db):
        self.crud = OrderCrud(db)
        self.db = db

    def _notify(self, title: str, message: str, user_id: Optional[int] = None):
        notif_service = NotificationService(self.db)
        notif_service.create_notification(title=title, message=message, user_id=user_id)

    def _broadcast(self, data: dict):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(manager.broadcast(json.dumps(data)))
        except RuntimeError:
            pass

    def _get_order_or_404(self, order_id: int) -> Order:
        order = self.db.get(Order, order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        return order

    def place_order(self, user_id: int, shipping_id: int, billing_id: int):
        return self.crud.create_order(user_id, shipping_id, billing_id)

    def place_direct_order(
        self,
        user_id: int,
        items: list[dict],
        total_amount: float,
        shipping_cost: float = 0,
        tax: float = 0,
        discount: float = 0,
        contact_name: str = "",
        contact_phone: str = "",
        contact_email: str = "",
        payment_mode: str = "cod",
    ):
        order = Order(
            user_id=user_id,
            shipping_address_id=None,
            billing_address_id=None,
            order_number=generate_order_number(),
            total_amount=total_amount,
            status="pending",
            tx_ref=generate_trx_ref(),
            order_date=datetime.now(),
            contact_name=contact_name,
            contact_phone=contact_phone,
            contact_email=contact_email,
            payment_mode=payment_mode,
            shipping_cost=shipping_cost,
            tax=tax,
            discount=discount,
        )
        self.db.add(order)
        self.db.flush()

        for item in items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item["product_id"],
                variant_id=item.get("variant_id"),
                unit_price=item["price"],
                quantity=item["quantity"],
            )
            self.db.add(order_item)

        self.db.commit()
        self.db.refresh(order)

        self._notify("New Order", f"Order #{order.order_number} placed by {contact_name} — Rs {total_amount:,.0f}")
        self._notify("Order Placed", f"Your order #{order.order_number} has been placed.", user_id=user_id)
        self._broadcast({"type": "new_order", "order_id": order.id, "order_number": order.order_number, "customer_name": contact_name, "total": total_amount, "status": "pending"})

        return order

    def accept_order(self, order_id: int):
        order = self._get_order_or_404(order_id)
        if order.status != "pending":
            raise HTTPException(status_code=400, detail=f"Cannot accept order with status '{order.status}'")

        items = self.db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
        for item in items:
            product = self.db.get(Product, item.product_id)
            if product:
                if (product.stock_quantity or 0) < item.quantity:
                    raise HTTPException(status_code=400, detail=f"Not enough stock for product #{item.product_id}")
                product.stock_quantity = (product.stock_quantity or 0) - item.quantity

        order.status = "order_received"
        self.db.commit()
        self.db.refresh(order)

        msg = f"Order #{order.order_number} accepted — status: Order Received"
        self._notify("Order Accepted", msg)
        self._notify("Order Update", f"Your order #{order.order_number} has been received and is being processed.", user_id=order.user_id)
        self._broadcast({"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "order_received"})
        return order

    def cancel_order(self, order_id: int, reason: str, cancelled_by: str = "admin"):
        order = self._get_order_or_404(order_id)
        if order.status not in ("pending", "order_received"):
            raise HTTPException(status_code=400, detail=f"Cannot cancel order with status '{order.status}'")

        order.status = "cancelled"
        order.cancel_reason = reason
        order.cancelled_by = cancelled_by
        self.db.commit()
        self.db.refresh(order)

        by_label = "Admin" if cancelled_by == "admin" else "Customer"
        self._notify("Order Cancelled", f"Order #{order.order_number} cancelled by {by_label}. Reason: {reason}")
        self._notify("Order Cancelled", f"Your order #{order.order_number} has been cancelled. Reason: {reason}", user_id=order.user_id)
        self._broadcast({"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "cancelled", "reason": reason})
        return order

    def advance_status(self, order_id: int, next_status: str):
        order = self._get_order_or_404(order_id)
        if next_status not in ADMIN_FLOW:
            raise HTTPException(status_code=400, detail=f"Invalid status transition to '{next_status}'")

        current_idx = ADMIN_FLOW.index(order.status) if order.status in ADMIN_FLOW else -1
        next_idx = ADMIN_FLOW.index(next_status)
        if next_idx != current_idx + 1:
            raise HTTPException(status_code=400, detail=f"Cannot transition from '{order.status}' to '{next_status}'")

        order.status = next_status
        self.db.commit()
        self.db.refresh(order)

        status_labels = {"order_received": "Order Received", "packed": "Packed", "sent_for_delivery": "Sent for Delivery", "delivered": "Delivered", "paid": "Paid"}
        label = status_labels.get(next_status, next_status)
        self._notify("Order Update", f"Order #{order.order_number} — {label}")
        self._notify("Order Update", f"Your order #{order.order_number} is now: {label}", user_id=order.user_id)
        self._broadcast({"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": next_status})

        if next_status == "paid":
            self._notify("Payment Received", f"Payment of Rs {float(order.total_amount):,.0f} received for order #{order.order_number}")

        return order

    def request_refund(self, order_id: int, reason: str):
        order = self._get_order_or_404(order_id)
        if order.status != "delivered":
            raise HTTPException(status_code=400, detail="Can only request refund for delivered orders")

        order.status = "refund_requested"
        order.refund_reason = reason
        self.db.commit()
        self.db.refresh(order)

        self._notify("Refund Requested", f"Refund requested for order #{order.order_number}. Reason: {reason}")
        self._notify("Refund Update", f"Your refund request for order #{order.order_number} has been submitted.", user_id=order.user_id)
        self._broadcast({"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "refund_requested", "reason": reason})
        return order

    def customer_cancel(self, order_id: int, reason: str):
        return self.cancel_order(order_id, reason, cancelled_by="customer")

    def list_orders(self, user_id: int):
        orders = self.crud.get_orders(user_id)
        return [_to_list_response(o) for o in orders]

    def list_all_orders(self):
        orders = (
            self.db.query(Order)
            .order_by(Order.order_date.desc())
            .all()
        )
        return [_to_list_response(o) for o in orders]

    def get_one_order(self, user_id: int, order_id: int):
        return self.crud.get_order_by_id(user_id, order_id)


def _to_list_response(order: Order) -> OrderListResponse:
    return OrderListResponse(
        id=order.id,
        order_number=order.order_number,
        total_amount=float(order.total_amount),
        status=order.status,
        order_date=order.order_date,
        order_items=[
            OrderItemResponse(
                product_id=item.product_id,
                variant_id=item.variant_id,
                quantity=item.quantity,
                unit_price=float(item.unit_price),
            )
            for item in order.order_items
        ],
        contact_name=order.contact_name or "",
        contact_phone=order.contact_phone or "",
        payment_mode=order.payment_mode or "cod",
        cancel_reason=order.cancel_reason,
        cancelled_by=order.cancelled_by,
        refund_reason=order.refund_reason,
    )
