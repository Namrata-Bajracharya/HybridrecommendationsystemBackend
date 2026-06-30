from pydantic import BaseModel, Field
from datetime import datetime


class DocumentPublic(BaseModel):
    id: str
    original_filename: str
    stored_filename: str
    relative_path: str
    absolute_path: str
    mime_type: str | None = None
    size: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
