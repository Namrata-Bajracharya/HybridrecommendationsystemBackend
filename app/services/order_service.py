from app.crud.order import OrderCrud
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.user import User
from app.models.address import Address
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
from app.services.shipping_service import calculate_shipping
import json
import asyncio
import threading


ADMIN_FLOW = ["accepted", "packed", "on_delivery", "delivered"]

_main_loop = None
_loop_lock = threading.Lock()


def set_main_loop(loop):
    global _main_loop
    with _loop_lock:
        _main_loop = loop


def _get_main_loop():
    global _main_loop
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        with _loop_lock:
            if _main_loop is not None:
                return _main_loop
            try:
                return asyncio.get_event_loop()
            except RuntimeError:
                return asyncio.new_event_loop()


class OrderService:
    def __init__(self, db):
        self.crud = OrderCrud(db)
        self.db = db

    def _get_admin_emails(self) -> list[str]:
        admins = self.db.query(User).filter(User.role == "admin").all()
        return [a.email for a in admins if a.email]

    def _notify(self, title: str, message: str, user_id: Optional[int] = None, type: Optional[str] = None, order_id: Optional[int] = None):
        notif_service = NotificationService(self.db)
        notif_service.create_notification(title=title, message=message, user_id=user_id, type=type, order_id=order_id)

    @staticmethod
    def _run_async(coro):
        loop = _get_main_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, loop)
        else:
            try:
                asyncio.ensure_future(coro)
            except RuntimeError:
                pass

    def _broadcast(self, data: dict):
        self._run_async(manager.broadcast(data))

    def _notify_user(self, user_id: int, data: dict):
        self._run_async(sio.emit("message", data, room=f"user:{user_id}"))

    def _notify_admins(self, data: dict):
        self._run_async(sio.emit("message", data, room="admins"))

    def _get_order_or_404(self, order_id: int) -> Order:
        order = self.db.get(Order, order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        return order

    FREE_SHIPPING_MIN = 2000.0

    def place_order(self, user_id: int, shipping_id: int, billing_id: int):
        address = self.db.get(Address, shipping_id)

        shipping_cost = 0.0
        if address and address.district:
            result = calculate_shipping(
                self.db,
                customer_lat=address.latitude or 0,
                customer_lng=address.longitude or 0,
                customer_district=address.district,
                customer_zone=address.zone,
            )
            shipping_cost = result["cost"]

        subtotal = sum(
            self.crud._resolve_cart_item_price(i) * i.quantity
            for i in self.crud.get_cart_items(user_id)
        )

        if subtotal >= self.FREE_SHIPPING_MIN:
            shipping_cost = 0.0

        order = self.crud.create_order(user_id, shipping_id, billing_id, shipping_cost)

        user = self.db.get(User, user_id)
        contact_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or f"User #{user_id}"

        self._notify("New Order", f"Order #{order.order_number} placed by {contact_name} — Rs {order.total_amount:,.0f}", type="new_order", order_id=order.id)
        self._notify_admins({"type": "new_order", "order_id": order.id, "order_number": order.order_number, "customer_name": contact_name, "total": float(order.total_amount), "status": "pending"})

        for admin_email in self._get_admin_emails():
            try:
                email_service.send_order_status_email(
                    to_email=admin_email,
                    subject=f"New Order #{order.order_number}",
                    heading="New Order Received",
                    body_lines=[
                        f"Customer: {contact_name} ({user.email})",
                        f"Total: Rs {order.total_amount:,.0f}",
                        f"Order #{order.order_number} is pending your review.",
                    ],
                )
            except Exception:
                pass

        return order

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
        shipping_district: str | None = None,
        shipping_zone: str | None = None,
    ):
        # Server-calculated shipping overrides client-provided value
        if shipping_district:
            calc = calculate_shipping(
                self.db,
                customer_lat=0,
                customer_lng=0,
                customer_district=shipping_district,
                customer_zone=shipping_zone,
            )
            calculated = calc["cost"]
            subtotal = total_amount - shipping_cost
            if subtotal >= self.FREE_SHIPPING_MIN:
                calculated = 0
            shipping_cost = calculated
            total_amount = subtotal + shipping_cost + tax - discount

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
                unit_cost=None,
                quantity=item["quantity"],
            )
            self.db.add(order_item)

        self.db.commit()
        self.db.refresh(order)

        self._notify("New Order", f"Order #{order.order_number} placed by {contact_name} — Rs {total_amount:,.0f}", type="new_order", order_id=order.id)
        self._notify_admins({"type": "new_order", "order_id": order.id, "order_number": order.order_number, "customer_name": contact_name, "total": total_amount, "status": "pending"})

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
        order.accepted_at = datetime.now()
        self.db.commit()
        self.db.refresh(order)

        self._notify("Order Update", f"Your order #{order.order_number} has been accepted and is being processed.", user_id=order.user_id, type="order_status", order_id=order.id)
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
        order.rejected_at = datetime.now()
        self.db.commit()
        self.db.refresh(order)

        self._notify("Order Update", f"Your order #{order.order_number} has been rejected. Reason: {reason}", user_id=order.user_id, type="order_status", order_id=order.id)
        self._notify_user(order.user_id, {"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "rejected", "reason": reason})

        items = self.db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
        product_names = ", ".join(item.product.name for item in items if item.product)
        email_to = order.contact_email
        if email_to:
            try:
                email_service.send_order_status_email(
                    to_email=email_to,
                    subject=f"Order #{order.order_number} Rejected",
                    heading="Your Order Has Been Rejected",
                    body_lines=[
                        f"Order #{order.order_number} has been rejected.",
                        f"Product(s): {product_names}" if product_names else "",
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
        self._notify("Order Cancelled", f"Order #{order.order_number} cancelled by {by_label}. Reason: {reason}", type="order_status", order_id=order.id)
        self._notify("Order Cancelled", f"Your order #{order.order_number} has been cancelled. Reason: {reason}", user_id=order.user_id, type="order_status", order_id=order.id)
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
        if next_status == "accepted":
            order.accepted_at = datetime.now()
        elif next_status == "packed":
            order.packed_at = datetime.now()
        elif next_status == "on_delivery":
            order.on_delivery_at = datetime.now()
            items = self.db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
            from app.services.fifo_service import FifoAllocationService
            fifo = FifoAllocationService(self.db)
            for item in items:
                product = self.db.get(Product, item.product_id)
                if not product:
                    continue
                if product.stock_quantity < item.quantity:
                    raise HTTPException(status_code=400, detail=f"Not enough stock for product #{item.product_id}")

                allocations = fifo.allocate(
                    product_id=item.product_id,
                    variant_id=item.variant_id,
                    quantity=item.quantity,
                )
                total_cost = sum(a.unit_cost * a.quantity for a in allocations)
                avg_cost = round(total_cost / item.quantity, 2) if item.quantity > 0 else 0
                item.unit_cost = avg_cost

                product.stock_quantity = (product.stock_quantity or 0) - item.quantity
        elif next_status == "delivered":
            order.delivered_at = datetime.now()

        self.db.commit()
        self.db.refresh(order)

        status_labels = {"accepted": "Accepted", "packed": "Packed", "on_delivery": "On Delivery", "delivered": "Delivered"}
        label = status_labels.get(next_status, next_status)
        self._notify("Order Update", f"Your order #{order.order_number} is now: {label}", user_id=order.user_id, type="order_status", order_id=order.id)
        self._notify_user(order.user_id, {"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": next_status})

        if next_status in ("accepted", "delivered"):
            email_to = order.contact_email
            if email_to:
                try:
                    if next_status == "accepted":
                        email_service.send_order_status_email(
                            to_email=email_to,
                            subject=f"Order #{order.order_number} Accepted",
                            heading="Your Order Has Been Accepted!",
                            body_lines=[
                                f"Order #{order.order_number} has been accepted and is being processed.",
                                "We will update you as it progresses.",
                            ],
                        )
                    elif next_status == "delivered":
                        import json as _json
                        ship_addr = order.shipping_address
                        if isinstance(ship_addr, dict):
                            ship_addr_str = ship_addr.get("street", "")
                            if ship_addr.get("city"):
                                ship_addr_str += f", {ship_addr['city']}"
                            if ship_addr.get("state"):
                                ship_addr_str += f", {ship_addr['state']}"
                        else:
                            ship_addr_str = str(ship_addr or "")
                        items_data = []
                        for oi in order.items:
                            name = oi.product.name if oi.product else f"Product #{oi.product_id}"
                            items_data.append({
                                "name": name,
                                "quantity": oi.quantity,
                                "unit_price": float(oi.unit_price),
                                "total": float(oi.unit_price) * oi.quantity,
                            })
                        email_service.send_invoice_email(
                            to_email=email_to,
                            order_number=order.order_number,
                            contact_name=order.contact_name or "",
                            contact_phone=order.contact_phone or "",
                            shipping_address=ship_addr_str,
                            items=items_data,
                            subtotal=float(order.total_amount) - float(order.shipping_cost or 0) - float(order.tax or 0),
                            shipping_cost=float(order.shipping_cost or 0),
                            tax=float(order.tax or 0),
                            discount=float(order.discount or 0),
                            total=float(order.total_amount),
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
        order.refund_requested_at = datetime.now()
        self.db.commit()
        self.db.refresh(order)

        contact_name = order.contact_name or f"User #{order.user_id}"
        self._notify("Refund Requested", f"Refund requested for order #{order.order_number}. Reason: {reason}", type="refund_status", order_id=order.id)
        self._notify("Refund Update", f"Your refund request for order #{order.order_number} has been submitted.", user_id=order.user_id, type="refund_status", order_id=order.id)
        self._notify_admins({"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "refund_requested", "reason": reason, "description": description, "customer_name": contact_name})
        self._notify_user(order.user_id, {"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "refund_requested", "reason": reason})

        for admin_email in self._get_admin_emails():
            try:
                email_service.send_order_status_email(
                    to_email=admin_email,
                    subject=f"Refund Request for Order #{order.order_number}",
                    heading=f"User {contact_name} has asked for a refund",
                    body_lines=[
                        f"Order #{order.order_number} — Refund requested by {contact_name}.",
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
        order.refund_out_for_pickup_at = datetime.now()
        self.db.commit()
        self.db.refresh(order)

        self._notify("Refund Accepted", f"Refund for Order #{order.order_number} accepted — pickup initiated", type="refund_status", order_id=order.id)
        self._notify("Refund Update", f"Your refund for order #{order.order_number} has been accepted. Delivery boy will pick up the item.", user_id=order.user_id, type="refund_status", order_id=order.id)
        self._notify_admins({"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "refund_out_for_pickup"})
        self._notify_user(order.user_id, {"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "refund_out_for_pickup"})

        email_to = order.contact_email
        if email_to:
            try:
                email_service.send_order_status_email(
                    to_email=email_to,
                    subject=f"Refund — Delivery Pickup for Order #{order.order_number}",
                    heading="Delivery Boy Will Pick Up Your Item",
                    body_lines=[
                        f"Your refund request for order #{order.order_number} has been accepted.",
                        "A delivery boy will come to pick up the item. Please keep the product ready.",
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
        order.item_retrieved_from_customer_at = datetime.now()
        self.db.commit()
        self.db.refresh(order)

        self._notify("Item Retrieved", f"Item for Order #{order.order_number} retrieved from customer", type="refund_status", order_id=order.id)
        self._notify("Refund Update", f"The item for order #{order.order_number} has been picked up from you. Waiting for admin verification.", user_id=order.user_id, type="refund_status", order_id=order.id)
        self._notify_admins({"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "item_retrieved_from_customer"})
        self._notify_user(order.user_id, {"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "item_retrieved_from_customer"})
        return order

    def mark_item_retrieved_by_admin(self, order_id: int):
        order = self._get_order_or_404(order_id)
        if order.status != "item_retrieved_from_customer":
            raise HTTPException(status_code=400, detail=f"Cannot mark admin retrieval with status '{order.status}'")

        order.status = "item_retrieved_by_admin"
        order.item_retrieved_by_admin_at = datetime.now()
        self.db.commit()
        self.db.refresh(order)

        self._notify("Item Received", f"Item for Order #{order.order_number} received by admin", type="refund_status", order_id=order.id)
        self._notify("Refund Update", f"The returned item for order #{order.order_number} has been received by admin.", user_id=order.user_id, type="refund_status", order_id=order.id)
        self._notify_admins({"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "item_retrieved_by_admin"})
        self._notify_user(order.user_id, {"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "item_retrieved_by_admin"})
        return order

    def initiate_refund_payment(self, order_id: int, proof_image: str | None = None):
        order = self._get_order_or_404(order_id)
        if order.status != "item_retrieved_by_admin":
            raise HTTPException(status_code=400, detail=f"Cannot initiate refund payment with status '{order.status}'")

        order.status = "refund_on_the_way"
        order.refund_payment_proof = proof_image
        order.refund_on_the_way_at = datetime.now()
        self.db.commit()
        self.db.refresh(order)

        self._notify("Refund Payment Initiated", f"Refund payment for Order #{order.order_number} is on the way", type="refund_status", order_id=order.id)
        self._notify("Refund Update", f"Your refund for order #{order.order_number} is on the way!", user_id=order.user_id, type="refund_status", order_id=order.id)
        self._notify_admins({"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "refund_on_the_way"})
        self._notify_user(order.user_id, {"type": "order_status", "order_id": order.id, "order_number": order.order_number, "status": "refund_on_the_way"})

        email_to = order.contact_email
        if email_to:
            try:
                email_service.send_order_status_email(
                    to_email=email_to,
                    subject=f"Refund on the Way — Order #{order.order_number}",
                    heading="Refund Approved & Payment Sent",
                    body_lines=[
                        f"Your refund for order #{order.order_number} has been approved and the payment is on the way.",
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

        # Return stock to FIFO batches at original cost
        from app.services.fifo_service import FifoAllocationService
        fifo = FifoAllocationService(self.db)
        items = self.db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
        for item in items:
            product = self.db.get(Product, item.product_id)
            if product:
                cost = float(item.unit_cost) if item.unit_cost else 0
                fifo.return_stock(
                    product_id=item.product_id,
                    variant_id=item.variant_id,
                    quantity=item.quantity,
                    unit_cost=cost,
                )
                product.stock_quantity = (product.stock_quantity or 0) + item.quantity

        order.status = "refund_successful"
        order.refund_successful_at = datetime.now()
        if proof_image:
            order.refund_payment_proof = proof_image
        self.db.commit()
        self.db.refresh(order)

        self._notify("Refund Complete", f"Refund for Order #{order.order_number} completed successfully", type="refund_status", order_id=order.id)
        self._notify("Refund Update", f"Your refund for order #{order.order_number} has been completed!", user_id=order.user_id, type="refund_status", order_id=order.id)
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

    def get_admin_order(self, order_id: int):
        order = self._get_order_or_404(order_id)
        return _to_list_response(order)

    def get_order_by_number(self, order_number: str):
        order = self.db.query(Order).filter(Order.order_number == order_number).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return _to_list_response(order)


def _to_list_response(order: Order) -> OrderListResponse:
    ship_addr = None
    if order.shipping_address:
        ship_addr = {
            "street": order.shipping_address.street,
            "city": order.shipping_address.city,
            "state": order.shipping_address.state,
        }
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
                unit_cost=float(item.unit_cost) if item.unit_cost else None,
                name=item.product.name if item.product else None,
                size=item.variant.name if item.variant else None,
                variant_name=item.variant.name if item.variant else None,
            )
            for item in order.order_items
        ],
        contact_name=order.contact_name or "",
        contact_phone=order.contact_phone or "",
        contact_email=order.contact_email or "",
        payment_mode=order.payment_mode or "cod",
        shipping_cost=float(order.shipping_cost or 0),
        tax=float(order.tax or 0),
        discount=float(order.discount or 0),
        shipping_address=ship_addr,
        cancel_reason=order.cancel_reason,
        cancelled_by=order.cancelled_by,
        reject_reason=order.reject_reason,
        refund_reason=order.refund_reason,
        refund_description=order.refund_description,
        refund_proof_images=order.refund_proof_images,
        refund_payment_proof=order.refund_payment_proof,
        accepted_at=order.accepted_at,
        packed_at=order.packed_at,
        on_delivery_at=order.on_delivery_at,
        delivered_at=order.delivered_at,
        refund_requested_at=order.refund_requested_at,
        refund_out_for_pickup_at=order.refund_out_for_pickup_at,
        item_retrieved_from_customer_at=order.item_retrieved_from_customer_at,
        item_retrieved_by_admin_at=order.item_retrieved_by_admin_at,
        refund_on_the_way_at=order.refund_on_the_way_at,
        refund_successful_at=order.refund_successful_at,
    )
