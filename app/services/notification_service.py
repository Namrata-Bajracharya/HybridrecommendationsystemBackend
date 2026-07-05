from app.models.notification import Notification
from app.schema.admin_schema import NotificationCreate, NotificationResponse
from typing import Optional
from sqlalchemy.orm import Session


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def create_notification(
        self,
        title: str,
        message: str,
        user_id: Optional[int] = None,
        type: Optional[str] = None,
        order_id: Optional[int] = None,
    ) -> NotificationResponse:
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=type,
            order_id=order_id,
            read=False,
        )
        self.db.add(notif)
        self.db.commit()
        self.db.refresh(notif)
        return NotificationResponse.model_validate(notif)

    def list_notifications_for_user(self, user_id: int) -> list[NotificationResponse]:
        notifs = (
            self.db.query(Notification)
            .filter(
                (Notification.user_id == user_id) | (Notification.user_id.is_(None))
            )
            .order_by(Notification.created_at.desc())
            .all()
        )
        return [NotificationResponse.model_validate(n) for n in notifs]
