from sqlalchemy.orm import Session as DBSession
from sqlalchemy import select, delete
from datetime import datetime
from app.models.session import Session


class SessionCrud:
    def __init__(self, db: DBSession):
        self.db = db

    def create_session(self, user_id: int, refresh_token_hash: str, expires_at: datetime) -> Session:
        session = Session(
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_by_refresh_hash(self, hash: str) -> Session | None:
        stmt = select(Session).where(
            Session.refresh_token_hash == hash,
            Session.is_revoked == False,
        )
        return self.db.scalar(stmt)

    def revoke_session(self, session_id: int):
        session = self.db.get(Session, session_id)
        if session:
            session.is_revoked = True
            self.db.commit()

    def revoke_all_user_sessions(self, user_id: int):
        stmt = select(Session).where(
            Session.user_id == user_id,
            Session.is_revoked == False,
        )
        for s in self.db.scalars(stmt):
            s.is_revoked = True
        self.db.commit()

    def clean_expired(self):
        stmt = delete(Session).where(Session.expires_at < datetime.utcnow())
        self.db.execute(stmt)
        self.db.commit()
