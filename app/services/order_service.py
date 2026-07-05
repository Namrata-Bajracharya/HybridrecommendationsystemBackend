from app.crud.order import OrderCrud
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.user import User
from app.utils.order_utils import generate_order_number, generate_trx_ref
from app.schema.order_schema import OrderListResponse, OrderItemResponse
from typing import Optional
from app.models.product import Product
from sqlalchemy.orm import Session
from datetime import datetime
from fastapi import HTTPException, status
from app.core.exceptions import OrderException
from app.websocket_manager import manager
from app.socketio_server import sio
from app.services.notification_service import NotificationService
from app.services import email_service
import json
import asyncio


ADMIN_FLOW = ["accepted", "packed", "on_delivery", "delivered"]


class OrderService:
    def __init__(self, db):
        self.crud = OrderCrud(db)
        self.db = db

    def _get_admin_emails(self) -> list[str]:
        admins = self.db.query(User).filter(User.role == "admin").all()
        return [a.email for a in admins if a.email]

    def _notify(self, title: str, message: str, user_id: Optional[int] = None):
        notif_service = NotificationService(self.db)
        notif_service.create_notification(title=title, message=message, user_id=user_id)

    def _broadcast(self, data: dict):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(manager.broadcast(data))
        except RuntimeError:
            pass

    def _notify_user(self, user_id: int, data: dict):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(sio.emit("message", data, room=f"user:{user_id}"))
        except RuntimeError:
            pass

    def _notify_admins(self, data: dict):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(sio.emit("message", data, room="admins"))
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
        self._notify_admins({"type": "new_order", "order_id": order.id, "order_number": order.order_number, "customer_name": contact_name, "total": total_amount, "status": "pending"})
        self._notify_user(user_id, {"type": "order_placed", "order_id": order.id, "order_number": order.order_number, "status": "pending"})

        for admin_email in self._get_admin_emails():
            try:
                email_service.send_order_status_email(
                    to_email=admin_email,
                    subject=f"New Order #{order.order_number}",
                    heading="New Order Received",
                    body_lines=[
                        f"Customer: {contact_name} ({contact_email})",
                        f"Total: Rs {total_amount:,.0f}",
                        f"Payment: {payment_mode}",
                        f"Order #{order.order_number} is pending your review.",
                    ],
                )
            except Exception:
                pass

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

        order.status = "accepted"
        self.db.commit()
        self.db.refresh(order)

        self._notify("Order Accepted", f"Order #{order.order_number} has been accepted")
        self._notify("Order Update", f"Your order #{order.order_number} has been accepted and is being processed.", user_id=order.user_id)
        self._notify_admins({"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "accepted"})
        self._notify_user(order.user_id, {"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "accepted"})

        email_to = order.contact_email
        if email_to:
            try:
                email_service.send_order_status_email(
                    to_email=email_to,
                    subject=f"Order #{order.order_number} Accepted",
                    heading="Your Order Has Been Accepted!",
                    body_lines=[
                        f"Order #{order.order_number} has been accepted and is being processed.",
                        "We will update you as it progresses.",
                    ],
                )
            except Exception:
                pass

        return order

    def reject_order(self, order_id: int, reason: str):
        order = self._get_order_or_404(order_id)
        if order.status != "pending":
            raise HTTPException(status_code=400, detail=f"Cannot reject order with status '{order.status}'")

        order.status = "rejected"
        order.reject_reason = reason
        self.db.commit()
        self.db.refresh(order)

        self._notify("Order Rejected", f"Order #{order.order_number} rejected. Reason: {reason}")
        self._notify("Order Update", f"Your order #{order.order_number} has been rejected. Reason: {reason}", user_id=order.user_id)
        self._notify_admins({"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "rejected", "reason": reason})
        self._notify_user(order.user_id, {"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "rejected", "reason": reason})

        email_to = order.contact_email
        if email_to:
            try:
                email_service.send_order_status_email(
                    to_email=email_to,
                    subject=f"Order #{order.order_number} Rejected",
                    heading="Your Order Has Been Rejected",
                    body_lines=[
                        f"Order #{order.order_number} could not be accepted.",
                        f"Reason: {reason}",
                        "If you have any questions, please contact us.",
                    ],
                )
            except Exception:
                pass

        return order

    def cancel_order(self, order_id: int, reason: str, cancelled_by: str = "admin"):
        order = self._get_order_or_404(order_id)
        if order.status != "pending":
            raise HTTPException(status_code=400, detail=f"Cannot cancel order with status '{order.status}'")

        order.status = "cancelled"
        order.cancel_reason = reason
        order.cancelled_by = cancelled_by
        self.db.commit()
        self.db.refresh(order)

        by_label = "Admin" if cancelled_by == "admin" else "Customer"
        self._notify("Order Cancelled", f"Order #{order.order_number} cancelled by {by_label}. Reason: {reason}")
        self._notify("Order Cancelled", f"Your order #{order.order_number} has been cancelled. Reason: {reason}", user_id=order.user_id)
        self._notify_admins({"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "cancelled", "reason": reason})
        self._notify_user(order.user_id, {"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "cancelled", "reason": reason})

        email_to = order.contact_email
        if cancelled_by == "admin" and email_to:
            try:
                email_service.send_order_status_email(
                    to_email=email_to,
                    subject=f"Order #{order.order_number} Cancelled",
                    heading="Your Order Has Been Cancelled",
                    body_lines=[
                        f"Order #{order.order_number} has been cancelled.",
                        f"Reason: {reason}",
                    ],
                )
            except Exception:
                pass

        if cancelled_by == "customer":
            for admin_email in self._get_admin_emails():
                try:
                    email_service.send_order_status_email(
                        to_email=admin_email,
                        subject=f"Order #{order.order_number} Cancelled by Customer",
                        heading="Order Cancelled by Customer",
                        body_lines=[
                            f"Order #{order.order_number} has been cancelled by the customer.",
                            f"Reason: {reason}",
                        ],
                    )
                except Exception:
                    pass

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

        if next_status == "delivered":
            order.delivered_at = datetime.now()
            items = self.db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
            for item in items:
                product = self.db.get(Product, item.product_id)
                if product:
                    if (product.stock_quantity or 0) < item.quantity:
                        raise HTTPException(status_code=400, detail=f"Not enough stock for product #{item.product_id}")
                    product.stock_quantity = (product.stock_quantity or 0) - item.quantity

        self.db.commit()
        self.db.refresh(order)

        status_labels = {"accepted": "Accepted", "packed": "Packed", "on_delivery": "On Delivery", "delivered": "Delivered"}
        label = status_labels.get(next_status, next_status)
        self._notify("Order Update", f"Order #{order.order_number} — {label}")
        self._notify("Order Update", f"Your order #{order.order_number} is now: {label}", user_id=order.user_id)
        self._notify_admins({"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": next_status})
        self._notify_user(order.user_id, {"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": next_status})

        if next_status == "delivered":
            email_to = order.contact_email
            if email_to:
                try:
                    email_service.send_order_status_email(
                        to_email=email_to,
                        subject=f"Order #{order.order_number} Delivered",
                        heading="Your Order Has Been Delivered!",
                        body_lines=[
                            f"Order #{order.order_number} has been delivered successfully.",
                            "Thank you for shopping with Kallee Nepal!",
                        ],
                    )
                except Exception:
                    pass

        return order

    def request_refund(self, order_id: int, reason: str, description: str | None = None, proof_images: list[str] | None = None):
        order = self._get_order_or_404(order_id)
        if order.status != "delivered":
            raise HTTPException(status_code=400, detail="Can only request refund for delivered orders")

        order.status = "refund_requested"
        order.refund_reason = reason
        order.refund_description = description
        order.refund_proof_images = json.dumps(proof_images or [])
        self.db.commit()
        self.db.refresh(order)

        self._notify("Refund Requested", f"Refund requested for order #{order.order_number}. Reason: {reason}")
        self._notify("Refund Update", f"Your refund request for order #{order.order_number} has been submitted.", user_id=order.user_id)
        self._notify_admins({"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "refund_requested", "reason": reason, "description": description})
        self._notify_user(order.user_id, {"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "refund_requested", "reason": reason})

        for admin_email in self._get_admin_emails():
            try:
                email_service.send_order_status_email(
                    to_email=admin_email,
                    subject=f"Refund Request for Order #{order.order_number}",
                    heading="Refund Request Received",
                    body_lines=[
                        f"Order #{order.order_number} — Refund requested by customer.",
                        f"Reason: {reason}",
                        f"Description: {description or 'N/A'}",
                    ],
                )
            except Exception:
                pass

        return order

    def accept_refund(self, order_id: int):
        order = self._get_order_or_404(order_id)
        if order.status != "refund_requested":
            raise HTTPException(status_code=400, detail=f"Cannot accept refund for order with status '{order.status}'")

        order.status = "refund_out_for_pickup"
        self.db.commit()
        self.db.refresh(order)

        self._notify("Refund Accepted", f"Refund for Order #{order.order_number} accepted — pickup initiated")
        self._notify("Refund Update", f"Your refund for order #{order.order_number} has been accepted. Delivery boy will pick up the item.", user_id=order.user_id)
        self._notify_admins({"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "refund_out_for_pickup"})
        self._notify_user(order.user_id, {"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "refund_out_for_pickup"})

        email_to = order.contact_email
        if email_to:
            try:
                email_service.send_order_status_email(
                    to_email=email_to,
                    subject=f"Refund Accepted for Order #{order.order_number}",
                    heading="Refund Request Accepted",
                    body_lines=[
                        f"Your refund request for order #{order.order_number} has been accepted.",
                        "A delivery boy will come to pick up the item.",
                    ],
                )
            except Exception:
                pass

        return order

    def mark_item_retrieved_from_customer(self, order_id: int):
        order = self._get_order_or_404(order_id)
        if order.status != "refund_out_for_pickup":
            raise HTTPException(status_code=400, detail=f"Cannot mark item retrieved with status '{order.status}'")

        order.status = "item_retrieved_from_customer"
        self.db.commit()
        self.db.refresh(order)

        self._notify("Item Retrieved", f"Item for Order #{order.order_number} retrieved from customer")
        self._notify("Refund Update", f"The item for order #{order.order_number} has been picked up from you.", user_id=order.user_id)
        self._notify_admins({"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "item_retrieved_from_customer"})
        self._notify_user(order.user_id, {"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "item_retrieved_from_customer"})
        return order

    def mark_item_retrieved_by_admin(self, order_id: int):
        order = self._get_order_or_404(order_id)
        if order.status != "item_retrieved_from_customer":
            raise HTTPException(status_code=400, detail=f"Cannot mark admin retrieval with status '{order.status}'")

        order.status = "item_retrieved_by_admin"
        self.db.commit()
        self.db.refresh(order)

        self._notify("Item Received", f"Item for Order #{order.order_number} received by admin")
        self._notify("Refund Update", f"The returned item for order #{order.order_number} has been received.", user_id=order.user_id)
        self._notify_admins({"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "item_retrieved_by_admin"})
        self._notify_user(order.user_id, {"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "item_retrieved_by_admin"})
        return order

    def initiate_refund_payment(self, order_id: int, proof_image: str | None = None):
        order = self._get_order_or_404(order_id)
        if order.status != "item_retrieved_by_admin":
            raise HTTPException(status_code=400, detail=f"Cannot initiate refund payment with status '{order.status}'")

        order.status = "refund_on_the_way"
        order.refund_payment_proof = proof_image
        self.db.commit()
        self.db.refresh(order)

        self._notify("Refund Payment Initiated", f"Refund payment for Order #{order.order_number} is on the way")
        self._notify("Refund Update", f"Your refund for order #{order.order_number} is on the way!", user_id=order.user_id)
        self._notify_admins({"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "refund_on_the_way"})
        self._notify_user(order.user_id, {"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "refund_on_the_way"})

        email_to = order.contact_email
        if email_to:
            try:
                email_service.send_order_status_email(
                    to_email=email_to,
                    subject=f"Refund on the Way — Order #{order.order_number}",
                    heading="Refund Payment Initiated",
                    body_lines=[
                        f"Your refund for order #{order.order_number} is on the way.",
                        "It should reflect in your account shortly.",
                    ],
                )
            except Exception:
                pass

        return order

    def complete_refund(self, order_id: int, proof_image: str | None = None):
        order = self._get_order_or_404(order_id)
        if order.status != "refund_on_the_way":
            raise HTTPException(status_code=400, detail=f"Cannot complete refund with status '{order.status}'")

        order.status = "refund_successful"
        if proof_image:
            order.refund_payment_proof = proof_image
        self.db.commit()
        self.db.refresh(order)

        self._notify("Refund Complete", f"Refund for Order #{order.order_number} completed successfully")
        self._notify("Refund Update", f"Your refund for order #{order.order_number} has been completed!", user_id=order.user_id)
        self._notify_admins({"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "refund_successful"})
        self._notify_user(order.user_id, {"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "refund_successful"})

        email_to = order.contact_email
        if email_to:
            try:
                email_service.send_order_status_email(
                    to_email=email_to,
                    subject=f"Refund Successful — Order #{order.order_number}",
                    heading="Refund Completed Successfully",
                    body_lines=[
                        f"Your refund for order #{order.order_number} has been completed.",
                        "Thank you for your patience.",
                    ],
                )
            except Exception:
                pass

        return order

    def customer_cancel(self, order_id: int, reason: str):
        order = self._get_order_or_404(order_id)
        if order.status != "pending":
            raise HTTPException(status_code=400, detail="You can only cancel an order while it is pending")
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
        reject_reason=order.reject_reason,
        refund_reason=order.refund_reason,
        refund_description=order.refund_description,
        refund_proof_images=order.refund_proof_images,
        refund_payment_proof=order.refund_payment_proof,
        delivered_at=order.delivered_at,
    )
