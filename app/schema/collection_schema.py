from pydantic import BaseModel, Field
from datetime import datetime


class CreateCollection(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    emoji: str | None = None
    color: str | None = None
    occasion: str = Field(..., min_length=1, max_length=50)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Festival Edit",
                    "description": "Celebrate in style",
                    "emoji": "✨",
                    "color": "#f0ebe4",
                    "occasion": "festive",
                }
            ]
        }
    }


class CollectionPublic(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None
    emoji: str | None = None
    color: str | None = None
    occasion: str
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class UpdateCollection(BaseModel):
    name: str | None = None
    description: str | None = None
    emoji: str | None = None
    color: str | None = None
    occasion: str | None = None
    is_active: bool | None = None

    model_config = {"from_attributes": True}
