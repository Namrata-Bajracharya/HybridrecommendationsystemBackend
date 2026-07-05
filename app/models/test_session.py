from sqlalchemy import String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.db.database import Base


class TestSession(Base):
    __tablename__ = "test_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    viewed_ids: Mapped[str] = mapped_column(Text, default="", server_default="")
    cart_ids: Mapped[str] = mapped_column(Text, default="", server_default="")
    wishlist_ids: Mapped[str] = mapped_column(Text, default="", server_default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
