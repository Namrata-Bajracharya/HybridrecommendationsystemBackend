from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ProductException
from app.crud.product import ProductCrud
from app.crud.cart_item import CartCrud
from app.models.cart import Cart
from app.schema.cart_schema import CartItemCreate, CartItemUpdate
from app.core.logger import logger


class CartService:
    def __init__(self, db: Session):
        self.db = db
        self.cart_crud = CartCrud(db=db)
        self.prod_crud = ProductCrud(db=db)

    def get_or_create_cart(self, user_id: Optional[int], session_id: Optional[str]):
        try:
            if user_id:
                cart = self.cart_crud.get_cart_by_user_id(user_id=user_id)
                if cart:
                    return cart
                cart = self.cart_crud.create_cart_by_user_id(user_id=user_id)
                return cart
            else:
                cart = self.cart_crud.get_cart_by_session_id(session_id=session_id)
                if cart:
                    return cart
                cart = self.cart_crud.create_cart_by_session_id(session_id=session_id)
                return cart
        except Exception as e:
            logger.info(f"exception: {e}")

    def _resolve_price(self, product, variant_id: int | None = None) -> float:
        if variant_id:
            variant = next((v for v in (product.variants or []) if v.id == variant_id), None)
            if variant and variant.price is not None:
                return variant.price
        return float(product.price)

    def _resolve_stock(self, product, variant_id: int | None = None) -> int:
        if variant_id:
            variant = next((v for v in (product.variants or []) if v.id == variant_id), None)
            if variant:
                return variant.stock_quantity
        return product.stock_quantity

    def add_item(self, cart: Cart, data: CartItemCreate):
        product = self.prod_crud.get_product_by_id(data.product_id)
        if not product:
            raise ProductException("product not found")
        stock = self._resolve_stock(product, data.variant_id)
        if stock < data.quantity:
            raise ProductException("Product out of stock")

        existing = self.cart_crud.get_cart_item_by_product(
            cart.id, product.id, data.variant_id
        )

        if existing:
            result = self.cart_crud.update_existing_cart_item(
                cart.id, product.id, data.variant_id, data.quantity
            )
            return result

        new_item = self.cart_crud.add_new_cart_item(
            cart_id=cart.id, product_id=product.id,
            quantity=data.quantity, variant_id=data.variant_id,
        )
        return new_item

    def update_item(self, cart: Cart, item_id: int, data: CartItemUpdate):
        item = self.cart_crud.update_item(cart_id=cart.id, item_id=item_id, data=data)
        if not item:
            raise HTTPException(
                status=status.HTTP_404_NOT_FOUND, detail="Item not found"
            )
        return item

    def remove_item(self, cart: Cart, item_id: int):
        item = self.cart_crud.remove_item(cart_id=cart.id, item_id=item_id)

        if not item:
            raise HTTPException(
                status=status.HTTP_404_NOT_FOUND, detail="Item not found"
            )
        return item

    def get_cart_details(self, cart: Cart):
        items = []
        subtotal = 0
        total_items = 0

        for item in cart.cart_items:
            product = item.product
            unit_price = self._resolve_price(product, item.variant_id)
            item_sub = unit_price * item.quantity

            items.append(
                {
                    "id": item.id,
                    "product_id": product.id,
                    "variant_id": item.variant_id,
                    "quantity": item.quantity,
                    "product_name": product.name,
                    "unit_price": unit_price,
                    "subtotal": item_sub,
                }
            )

            subtotal += item_sub
            total_items += item.quantity

        return {
            "id": cart.id,
            "items": items,
            "subtotal": subtotal,
            "total_items": total_items,
        }

    def merge_carts(self, user_id: int, session_id: str):
        user_cart = self.cart_crud.get_cart_by_user_id(user_id=user_id)
        anon_cart = self.cart_crud.get_cart_by_session_id(session_id=session_id)

        logger.info(f"info user cart: {user_cart}")
        logger.info(f"anon cart: {anon_cart}")

        if not anon_cart:
            return

        if not user_cart:
            self.cart_crud.update_anon_cart_to_user_cart(
                user_id=user_id, session_id=session_id
            )
            return

        for item in anon_cart.cart_items:
            existing = self.cart_crud.get_cart_item_by_product(
                user_cart.id, item.product_id, item.variant_id
            )

            if existing:
                existing.quantity += item.quantity
            else:
                item.cart_id = user_cart.id
        self.cart_crud.remove_anon_cart(session_id=session_id)
