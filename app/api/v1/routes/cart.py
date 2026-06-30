from typing import Annotated
from fastapi import APIRouter, Depends, Request

from fastapi.responses import JSONResponse
from app.dependencies import get_cart_service_dep, get_optional_user
from app.schema.user_schema import UserPublic
from app.services.cart_service import CartService
from app.schema.cart_schema import CartItemCreate, CartItemUpdate, CartResponse
from app.utils.session import generate_session_id
from app.core.logger import logger
from app.dependencies import get_recommendation_service_dep
from app.services.recommendation_service import RecommendationService
from datetime import datetime

router = APIRouter(tags=["Cart"])

cart_dependency = Annotated[CartService, Depends(get_cart_service_dep)]
user_dep = Annotated[UserPublic | None, Depends(get_optional_user)]

@router.get("/recommendations")
async def get_cart_recommendations(
    request: Request,
    current_user: user_dep,
    cart_service: cart_dependency,
    rec_service: Annotated[RecommendationService, Depends(get_recommendation_service_dep)],
):
    """Return recommendations based on current cart items."""
    # Resolve cart
    if current_user:
        session_id = request.cookies.get("session_id")
        cart_service.merge_carts(current_user.id, session_id)
        cart = cart_service.get_or_create_cart(user_id=current_user.id, session_id=None)
    else:
        session_id = request.cookies.get("session_id") or generate_session_id()
        cart = cart_service.get_or_create_cart(user_id=None, session_id=session_id)

    cart_details = cart_service.get_cart_details(cart=cart)
    item_ids = [str(i["product_id"]) for i in cart_details.get("items", [])]

    if not item_ids:
        return {
            "user_id": str(current_user.id) if current_user else None,
            "recommendation_type": "cart",
            "recommendations": [],
            "total_count": 0,
            "timestamp": datetime.utcnow().isoformat(),
        }

    recommendations = rec_service.get_cart_recommendations(
        user_id=str(current_user.id) if current_user else None,
        cart_items=item_ids,
        top_k=5,
    )

    return {
        "user_id": str(current_user.id) if current_user else None,
        "recommendation_type": "cart",
        "recommendations": recommendations,
        "total_count": len(recommendations),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("")
async def get_cart(
    request: Request, current_user: user_dep, cart_service: cart_dependency
):
    # Authenticated user
    if current_user:
        session_id = request.cookies.get("session_id")
        cart_service.merge_carts(current_user.id, session_id)

        cart = cart_service.get_or_create_cart(user_id=current_user.id, session_id=None)
        return cart_service.get_cart_details(cart=cart)

    # Anonymous user
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = generate_session_id()

    cart = cart_service.get_or_create_cart(user_id=None, session_id=session_id)

    response = JSONResponse(cart_service.get_cart_details(cart=cart))
    response.set_cookie("session_id", session_id, httponly=True, max_age=1296000)
    return response


@router.post("/items")
async def add_item(
    request: Request,
    data: CartItemCreate,
    current_user: user_dep,
    cart_service: cart_dependency,
):
    if current_user:
        cart = cart_service.get_or_create_cart(user_id=current_user.id, session_id=None)
    else:
        session_id = request.cookies.get("session_id") or generate_session_id()
        cart = cart_service.get_or_create_cart(user_id=None, session_id=session_id)

    item = cart_service.add_item(cart=cart, data=data)
    return {"message": "Item added", "item_id": item.id}


@router.put("/items/{item_id}")
async def update_item(
    request: Request,
    item_id: int,
    data: CartItemUpdate,
    current_user: user_dep,
    cart_service: cart_dependency,
):
    if current_user:
        cart = cart_service.get_or_create_cart(user_id=current_user.id, session_id=None)
        logger.info("cart with user: {cart}")
    else:
        session_id = request.cookies.get("session_id")
        logger.info(f"we are using session: {session_id}")
        cart = cart_service.get_or_create_cart(user_id=None, session_id=session_id)

    item = cart_service.update_item(cart, item_id, data)
    return {"message": "Item updated", "item_id": item.id}


@router.delete("/items/{item_id}")
async def remove_item(
    request: Request,
    item_id: int,
    current_user: user_dep,
    cart_service: cart_dependency,
):
    if current_user:
        cart = cart_service.get_or_create_cart(user_id=current_user.id, session_id=None)
    else:
        session_id = request.cookies.get("session_id")
        cart = cart_service.get_or_create_cart(user_id=None, session_id=session_id)

    cart_service.remove_item(cart, item_id)
    return {"message": "Item removed"}
