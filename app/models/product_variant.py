from sqlalchemy import Integer, String, Float, ForeignKey, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional, Any
from app.db.database import Base


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    attributes: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0)
    sku: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    image_document_id: Mapped[Optional[str]] = mapped_column(ForeignKey("documents.id"), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    product: Mapped["Product"] = relationship("Product", back_populates="variants")
    image_document: Mapped[Optional["Document"]] = relationship("Document")
