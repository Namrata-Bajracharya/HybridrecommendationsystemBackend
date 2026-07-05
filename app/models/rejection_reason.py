from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from app.db.database import Base


class RejectionReason(Base):
    __tablename__ = "rejection_reasons"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    reason: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
