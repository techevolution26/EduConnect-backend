from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedSchema


class HubCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str = Field(min_length=2, max_length=140)
    description: Optional[str] = None
    cover_image_url: Optional[str] = None


class HubUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    slug: Optional[str] = Field(default=None, min_length=2, max_length=140)
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    is_active: Optional[bool] = None


class HubRead(TimestampedSchema):
    name: str
    slug: str
    description: Optional[str]
    cover_image_url: Optional[str]
    is_active: bool