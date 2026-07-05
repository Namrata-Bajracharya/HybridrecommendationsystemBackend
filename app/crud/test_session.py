from sqlalchemy.orm import Session as DBSession
from sqlalchemy import select
from datetime import datetime
from app.models.test_session import TestSession


class TestSessionCrud:
    def __init__(self, db: DBSession):
        self.db = db

    def get(self, session_id: str) -> TestSession | None:
        return self.db.get(TestSession, session_id)

    def upsert(self, session_id: str, viewed_ids: str = "", cart_ids: str = "", wishlist_ids: str = "") -> TestSession:
        existing = self.get(session_id)
        if existing:
            existing.viewed_ids = viewed_ids
            existing.cart_ids = cart_ids
            existing.wishlist_ids = wishlist_ids
            existing.updated_at = datetime.utcnow()
        else:
            existing = TestSession(
                session_id=session_id,
                viewed_ids=viewed_ids,
                cart_ids=cart_ids,
                wishlist_ids=wishlist_ids,
            )
            self.db.add(existing)
        self.db.commit()
        self.db.refresh(existing)
        return existing
