from sqlalchemy.orm import Session
from app.models.document import Document
from uuid import uuid4
from app.core.logger import logger


class DocumentCrud:
    def __init__(self, db: Session):
        self.db = db

    def create_document(self, data: dict) -> Document:
        doc = Document(**data)
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def get_by_id(self, id: str) -> Document | None:
        return self.db.get(Document, id)

    def delete(self, id: str) -> bool:
        doc = self.db.get(Document, id)
        if not doc:
            return False
        self.db.delete(doc)
        self.db.commit()
        return True
