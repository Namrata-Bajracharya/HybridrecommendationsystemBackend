from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime

from app.crud.review import ReviewCrud
from app.models.review import Review
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.user import User
from app.schema.review_schema import ReviewCreate, ReviewResponse, ReviewUpdate, ReviewReplyRequest
from app.schema.user_schema import UserPublic
from app.services.notification_service import NotificationService
from app.socketio_server import sio
from app.services import email_service
import asyncio


def _get_main_loop():
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.new_event_loop()


def _run_async(coro):
    loop = _get_main_loop()
    if loop.is_running():
        asyncio.run_coroutine_threadsafe(coro, loop)
    else:
        try:
            asyncio.ensure_future(coro)
        except RuntimeError:
            pass


def _get_admin_emails(db):
    return [
        u.email for u in db.query(User).filter(
            User.role == "admin", User.email.isnot(None)
        ).all()
        if u.email
    ]


class ReviewService:
    def __init__(self, db: Session):
        self.db = db
        self.crud = ReviewCrud(db=db)

    def _to_response(self, r: Review) -> ReviewResponse:
        return ReviewResponse(
            id=r.id,
            user_id=r.user_id,
            user_name=r.user.first_name or r.user.email or f"User #{r.user_id}",
            product_id=r.product_id,
            rating=r.rating,
            comment=r.comment,
            created_at=r.created_at,
            is_approved=r.is_approved,
            reply=r.reply,
            replied_at=r.replied_at,
        )

    def create_review(self, review: ReviewCreate, user_id: int) -> ReviewResponse:
        """Create a new review. Only customers who bought the product can review."""
        product_id = review.product_id

        # Check if user purchased this product
        has_purchased = self.db.query(Order).join(OrderItem).filter(
            Order.user_id == user_id,
            OrderItem.product_id == product_id,
            Order.status == "delivered",
        ).first() is not None

        if not has_purchased:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only review products you have purchased.",
            )

        db_review = self.crud.create_review(review=review, user_id=user_id)

        # Notify admins about the new review
        product_name = db_review.product.name if db_review.product else f"Product #{product_id}"
        user_name = db_review.user.first_name or db_review.user.email or f"User #{user_id}"

        try:
            # DB notification for admins
            notif = NotificationService(self.db)
            notif.create_notification(
                title="New Review",
                message=f"{user_name} reviewed {product_name}",
                type="new_review",
            )
            # Socket notification to admin room
            _run_async(sio.emit("message", {
                "type": "new_review",
                "review_id": db_review.id,
                "product_id": product_id,
                "product_name": product_name,
                "user_name": user_name,
                "rating": review.rating,
                "comment": review.comment,
            }, room="admins"))
            # Socket notification back to the reviewer so their page updates
            _run_async(sio.emit("message", {
                "type": "new_review",
                "review_id": db_review.id,
                "product_id": product_id,
                "product_name": product_name,
                "user_name": user_name,
                "rating": review.rating,
                "comment": review.comment,
            }, room=f"user:{user_id}"))
            # Email to admins
            for admin_email in _get_admin_emails(self.db):
                try:
                    email_service.send_order_status_email(
                        to_email=admin_email,
                        subject=f"New Review on {product_name}",
                        heading=f"{user_name} Reviewed {product_name}",
                        body_lines=[
                            f"{user_name} rated {product_name} {review.rating}/5.",
                            f"Comment: {review.comment or 'No comment'}" if review.comment else "",
                        ],
                    )
                except Exception:
                    pass
        except Exception:
            pass

        return self._to_response(db_review)

    def reply_to_review(self, review_id: int, user_id: int, payload: ReviewReplyRequest) -> ReviewResponse:
        """Admin replies to a review."""
        db_review = self.crud.get_review(review_id=review_id)
        if not db_review:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

        db_review.reply = payload.reply
        db_review.replied_at = datetime.now()
        self.db.commit()
        self.db.refresh(db_review)

        # Notify the customer who wrote the review
        try:
            product_name = db_review.product.name if db_review.product else f"Product #{db_review.product_id}"
            customer = self.db.get(User, db_review.user_id)
            customer_email = customer.email if customer else None

            # DB notification for the customer
            notif = NotificationService(self.db)
            notif.create_notification(
                title="Admin Replied to Your Review",
                message=f"Admin replied to your review on {product_name}",
                user_id=db_review.user_id,
                type="review_reply",
            )
            # Socket notification to the customer
            _run_async(sio.emit("message", {
                "type": "review_reply",
                "review_id": db_review.id,
                "product_id": db_review.product_id,
                "product_name": product_name,
                "reply": payload.reply,
            }, room=f"user:{db_review.user_id}"))
            # Email to the customer
            if customer_email:
                try:
                    email_service.send_order_status_email(
                        to_email=customer_email,
                        subject=f"Admin Replied to Your Review on {product_name}",
                        heading=f"Admin Replied to Your Review",
                        body_lines=[
                            f"Admin replied to your review on {product_name}:",
                            f'"{payload.reply}"',
                        ],
                    )
                except Exception:
                    pass
        except Exception:
            pass

        return self._to_response(db_review)

    def get_reviews_by_user(self, user_id: int) -> List[ReviewResponse]:
        reviews = self.crud.get_reviews_by_user(user_id=user_id)
        return [self._to_response(r) for r in reviews]

    def get_reviews_by_product(
        self, product_id: int, skip: int = 0, limit: int = 100
    ) -> List[ReviewResponse]:
        """Get all reviews for a specific product."""
        reviews = self.crud.get_reviews_by_product(
            product_id=product_id, skip=skip, limit=limit
        )
        return [self._to_response(r) for r in reviews]

    def get_review(self, review_id: int) -> ReviewResponse:
        """Get a specific review by ID."""
        review = self.crud.get_review(review_id=review_id)
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
            )
        return self._to_response(review)

    def update_review(
        self, review_id: int, review_update: ReviewUpdate, current_user: UserPublic
    ) -> ReviewResponse:
        """Update a review."""
        db_review = self.crud.get_review(review_id=review_id)
        if not db_review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
            )

        if db_review.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this review",
            )

        updated_review = self.crud.update_review(
            db_review=db_review, review_update=review_update
        )
        return self._to_response(updated_review)

    def delete_review(self, review_id: int, current_user: UserPublic) -> None:
        """Delete a review."""
        db_review = self.crud.get_review(review_id=review_id)
        if not db_review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
            )

        if db_review.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this review",
            )

        self.crud.delete_review(db_review=db_review)
