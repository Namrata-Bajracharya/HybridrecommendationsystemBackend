from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from dataclasses import dataclass
from fastapi import HTTPException, status

from app.models.stock_batch import StockBatch
from app.models.product import Product
from app.models.product_variant import ProductVariant


@dataclass
class Allocation:
    batch_id: int
    quantity: int
    unit_cost: float


class FifoAllocationService:
    def __init__(self, db: Session):
        self.db = db

    def get_available_quantity(self, product_id: int, variant_id: Optional[int] = None) -> int:
        batches = (
            self.db.query(StockBatch)
            .filter(
                StockBatch.product_id == product_id,
                StockBatch.variant_id == variant_id,
                StockBatch.quantity_remaining > 0,
            )
            .all()
        )
        return sum(b.quantity_remaining for b in batches)

    def allocate(self, product_id: int, quantity: int, variant_id: Optional[int] = None) -> List[Allocation]:
        if quantity <= 0:
            return []

        batches = (
            self.db.query(StockBatch)
            .filter(
                StockBatch.product_id == product_id,
                StockBatch.variant_id == variant_id,
                StockBatch.quantity_remaining > 0,
            )
            .order_by(StockBatch.created_at.asc())
            .all()
        )

        available = sum(b.quantity_remaining for b in batches)
        if available < quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Not enough stock for product #{product_id}. Available: {available}, requested: {quantity}",
            )

        allocations: List[Allocation] = []
        remaining = quantity

        for batch in batches:
            if remaining <= 0:
                break
            take = min(batch.quantity_remaining, remaining)
            batch.quantity_remaining -= take
            remaining -= take
            allocations.append(Allocation(
                batch_id=batch.id,
                quantity=take,
                unit_cost=batch.unit_cost,
            ))

        self.db.flush()
        return allocations

    def add_batch(
        self,
        product_id: int,
        quantity: int,
        unit_cost: float,
        variant_id: Optional[int] = None,
        purchase_order_item_id: Optional[int] = None,
    ) -> StockBatch:
        batch = StockBatch(
            product_id=product_id,
            variant_id=variant_id,
            purchase_order_item_id=purchase_order_item_id,
            quantity_remaining=quantity,
            unit_cost=unit_cost,
        )
        self.db.add(batch)
        self.db.flush()
        return batch

    def return_stock(self, product_id: int, quantity: int, unit_cost: float, variant_id: Optional[int] = None):
        batch = StockBatch(
            product_id=product_id,
            variant_id=variant_id,
            quantity_remaining=quantity,
            unit_cost=unit_cost,
        )
        self.db.add(batch)
        self.db.flush()
