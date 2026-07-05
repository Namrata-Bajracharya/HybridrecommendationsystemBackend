from sqlalchemy import Integer, ForeignKey, Numeric, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum as SQLEnum
from typing import List
from datetime import datetime
from app.db.database import Base


class Order(Base):
    """Order entity representing a customer's purchase and fulfillment state."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    shipping_address_id: Mapped[int] = mapped_column(
        ForeignKey("addresses.id", ondelete="RESTRICT"), nullable=True
    )
    billing_address_id: Mapped[int] = mapped_column(
        ForeignKey("addresses.id", ondelete="RESTRICT"), nullable=True
    )
    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        SQLEnum(
            "pending", "accepted", "rejected", "packed", "on_delivery",
            "delivered", "cancelled", "refund_requested",
            "refund_out_for_pickup", "item_retrieved_from_customer",
            "item_retrieved_by_admin", "refund_on_the_way",
            "refund_successful", "refunded",
            name="order_status"
        ),
        default="pending",
    )
    order_date: Mapped[datetime] = mapped_column(
        DateTime, default=func.current_timestamp()
    )
    accepted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    packed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    on_delivery_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    shipped_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    tx_ref: Mapped[str] = mapped_column(String(255), unique=True)
    payment_status: Mapped[str] = mapped_column(
        SQLEnum("pending", "success", "failed", name="payment_status"),
        default="pending",
    )
    contact_name: Mapped[str] = mapped_column(String(200), nullable=True)
    contact_phone: Mapped[str] = mapped_column(String(50), nullable=True)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=True)
    payment_mode: Mapped[str] = mapped_column(String(50), default="cod")
    shipping_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    tax: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    discount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    delivered_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    rejected_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    cancel_reason: Mapped[str] = mapped_column(String(500), nullable=True)
    cancelled_by: Mapped[str] = mapped_column(String(50), nullable=True)
    reject_reason: Mapped[str] = mapped_column(String(500), nullable=True)
    refund_reason: Mapped[str] = mapped_column(String(500), nullable=True)
    refund_description: Mapped[str] = mapped_column(String(1000), nullable=True)
    refund_proof_images: Mapped[str] = mapped_column(String(2000), nullable=True)
    refund_payment_proof: Mapped[str] = mapped_column(String(500), nullable=True)
    refund_requested_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    refund_out_for_pickup_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    item_retrieved_from_customer_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    item_retrieved_by_admin_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    refund_on_the_way_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    refund_successful_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="orders")
    shipping_address: Mapped["Address"] = relationship(
        "Address", foreign_keys=[shipping_address_id]
    )
    billing_address: Mapped["Address"] = relationship(
        "Address", foreign_keys=[billing_address_id]
    )
    order_items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment", back_populates="order", cascade="all, delete-orphan"
    )
