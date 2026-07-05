"""
Test Recommendation Route
Provides a testing page for the hybrid recommendation engine.
User can browse products, mark buy/cancel, and see live updates.
Works for both auth and non-auth users.
Supports anonymous session persistence for cross-device sync.
"""
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_optional_user, get_db
from app.schema.user_schema import UserPublic
from app.schema.product_schema import ProductResponse
from app.schema.common_schema import PaginatedResponse
from app.services.recommendation_service import RecommendationService
from app.services.product_service import ProductService
from app.dependencies import get_product_service_dep
from app.crud.test_session import TestSessionCrud
from app.socketio_server import sio
from app.core.logger import logger

router = APIRouter(tags=["Test Recommendation"], prefix="/testrecommendation")


class ActionRequest(BaseModel):
    product_id: str
    action: str  # "buy" | "cancel" | "normal" | "return" | "positive_review" | "negative_review" | "high_rating" | "low_rating"


class ActionResponse(BaseModel):
    status: str
    message: str


class TestRecommendationItem(BaseModel):
    item_id: str
    rank: int
    score: float
    reason: str
    reasons: List[str] = []


class TestRecommendationResponse(BaseModel):
    products: PaginatedResponse[ProductResponse]
    recommendations: List[TestRecommendationItem]
    actions: dict
    is_authenticated: bool = False
    session_id: str = ""
    viewed_ids: str = ""
    cart_ids: str = ""
    wishlist_ids: str = ""


def get_recommendation_service(db: Session = Depends(get_db)) -> RecommendationService:
    return RecommendationService(db=db)


rec_dep = Annotated[RecommendationService, Depends(get_recommendation_service)]
prod_dep = Annotated[ProductService, Depends(get_product_service_dep)]


def _resolve_ids(
    session_id: str | None,
    cart_ids: str,
    viewed_ids: str,
    wishlist_ids: str,
    db: Session,
) -> tuple[list[str], list[str], list[str]]:
    """Load/save test session state from/to the database.
    
    If session_id is provided, IDs are persisted so they survive across
    browsers and devices. Explicit query-param IDs always take precedence
    so the frontend can push deltas.
    """
    if not session_id:
        cart_list = [id.strip() for id in cart_ids.split(",") if id.strip()]
        viewed_list = [id.strip() for id in viewed_ids.split(",") if id.strip()]
        wish_list = [id.strip() for id in wishlist_ids.split(",") if id.strip()]
        return cart_list, viewed_list, wish_list

    crud = TestSessionCrud(db)
    existing = crud.get(session_id)

    # Use explicit params if provided, otherwise fall back to stored
    final_cart = cart_ids if cart_ids.strip() else (existing.cart_ids if existing else "")
    final_viewed = viewed_ids if viewed_ids.strip() else (existing.viewed_ids if existing else "")
    final_wish = wishlist_ids if wishlist_ids.strip() else (existing.wishlist_ids if existing else "")

    cart_list = [id.strip() for id in final_cart.split(",") if id.strip()]
    viewed_list = [id.strip() for id in final_viewed.split(",") if id.strip()]
    wish_list = [id.strip() for id in final_wish.split(",") if id.strip()]

    # Persist (merge explicit params into stored for next load)
    if cart_ids.strip() or viewed_ids.strip() or wishlist_ids.strip():
        crud.upsert(
            session_id=session_id,
            viewed_ids=",".join(viewed_list),
            cart_ids=",".join(cart_list),
            wishlist_ids=",".join(wish_list),
        )

    return cart_list, viewed_list, wish_list


@router.get("", response_model=TestRecommendationResponse)
async def get_test_recommendation(
    current_user: Annotated[Optional[UserPublic], Depends(get_optional_user)],
    product_service: prod_dep,
    rec_service: rec_dep,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    session_id: str = Query("", description="Anonymous session ID for cross-device persistence"),
    cart_ids: str = Query("", description="Comma-separated product IDs in cart"),
    viewed_ids: str = Query("", description="Comma-separated recently viewed product IDs"),
    wishlist_ids: str = Query("", description="Comma-separated wishlist product IDs"),
):
    """Get all products + recommendations.
    Pass session_id to persist view/cart/wishlist state across devices.
    Works for both auth (uses reviews/wishlist/actions) and non-auth (uses cart/viewed)."""
    user_id = str(current_user.id) if current_user else "anon"

    sid = session_id.strip() or None
    cart_list, viewed_list, wish_list = _resolve_ids(sid, cart_ids, viewed_ids, wishlist_ids, db)

    # Notify other clients in the same testrec session about the state change
    if sid:
        await sio.emit("message", {
            "type": "testrec_update",
            "viewed_ids": ",".join(viewed_list),
            "cart_ids": ",".join(cart_list),
            "wishlist_ids": ",".join(wish_list),
        }, room=f"testrec:{sid}")

    products = product_service.get_all_products(page=page, per_page=per_page)
    recommendations = rec_service.get_test_recommendations(
        user_id=user_id,
        top_k=10,
        cart_item_ids=cart_list,
        viewed_product_ids=viewed_list,
        wishlist_item_ids=wish_list,
    )

    actions = rec_service.get_user_actions(user_id) if current_user else {}

    return TestRecommendationResponse(
        products=products,
        recommendations=recommendations,
        actions=actions,
        is_authenticated=current_user is not None,
        session_id=sid or "",
        viewed_ids=",".join(viewed_list),
        cart_ids=",".join(cart_list),
        wishlist_ids=",".join(wish_list),
    )


VALID_ACTIONS = {"buy", "cancel", "normal", "return", "positive_review", "negative_review", "high_rating", "low_rating"}

@router.post("/action", response_model=ActionResponse)
async def record_action(
    current_user: Annotated[UserPublic, Depends(get_current_user)],
    rec_service: rec_dep,
    body: ActionRequest,
):
    """Record a buy/cancel/normal/return/review/rating action on a product (auth only)."""
    if body.action not in VALID_ACTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid action. Must be one of: {', '.join(VALID_ACTIONS)}")

    user_id = str(current_user.id)
    rec_service.record_action(user_id, body.product_id, body.action)
    logger.info(f"[TestRec] User {user_id} {body.action} on product {body.product_id}")

    # Broadcast to ALL test page visitors so collaborative recommendations update
    await sio.emit("message", {
        "type": "testrec_reload",
        "action": body.action,
        "product_id": body.product_id,
    }, room="testrec_all")

    return ActionResponse(status="ok", message=f"Action '{body.action}' recorded")


@router.get("/refresh", response_model=TestRecommendationResponse)
async def refresh_recommendations(
    current_user: Annotated[Optional[UserPublic], Depends(get_optional_user)],
    product_service: prod_dep,
    rec_service: rec_dep,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    session_id: str = Query("", description="Anonymous session ID for cross-device persistence"),
    cart_ids: str = Query("", description="Comma-separated product IDs in cart"),
    viewed_ids: str = Query("", description="Comma-separated recently viewed product IDs"),
    wishlist_ids: str = Query("", description="Comma-separated wishlist product IDs"),
):
    """Refresh recommendations after actions (no reload needed).
    Works for both auth and non-auth users."""
    user_id = str(current_user.id) if current_user else "anon"

    sid = session_id.strip() or None
    cart_list, viewed_list, wish_list = _resolve_ids(sid, cart_ids, viewed_ids, wishlist_ids, db)

    # Notify other clients in the same testrec session about the state change
    if sid:
        await sio.emit("message", {
            "type": "testrec_update",
            "viewed_ids": ",".join(viewed_list),
            "cart_ids": ",".join(cart_list),
            "wishlist_ids": ",".join(wish_list),
        }, room=f"testrec:{sid}")

    products = product_service.get_all_products(page=page, per_page=per_page)
    recommendations = rec_service.get_test_recommendations(
        user_id=user_id,
        top_k=10,
        cart_item_ids=cart_list,
        viewed_product_ids=viewed_list,
        wishlist_item_ids=wish_list,
    )
    actions = rec_service.get_user_actions(user_id) if current_user else {}

    return TestRecommendationResponse(
        products=products,
        recommendations=recommendations,
        actions=actions,
        is_authenticated=current_user is not None,
        session_id=sid or "",
        viewed_ids=",".join(viewed_list),
        cart_ids=",".join(cart_list),
        wishlist_ids=",".join(wish_list),
    )
