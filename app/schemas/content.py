from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from app.models.content import ContentStatus, ContentType, ContentVisibility
from app.schemas.category import CategoryRead
from app.schemas.hub import HubRead
from app.schemas.user import UserRead


class ContentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=220)
    slug: str = Field(min_length=3, max_length=260)
    excerpt: Optional[str] = Field(default=None, max_length=500)
    body: str = Field(min_length=20)

    content_type: ContentType
    visibility: ContentVisibility = ContentVisibility.PUBLIC
    is_premium: bool = False

    category_id: Optional[str] = None
    hub_id: Optional[str] = None
    cover_image_url: Optional[str] = None


class ContentUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=220)
    slug: Optional[str] = Field(default=None, min_length=3, max_length=260)
    excerpt: Optional[str] = Field(default=None, max_length=500)
    body: Optional[str] = Field(default=None, min_length=20)

    content_type: Optional[ContentType] = None
    visibility: Optional[ContentVisibility] = None
    is_premium: Optional[bool] = None

    category_id: Optional[str] = None
    hub_id: Optional[str] = None
    cover_image_url: Optional[str] = None


class ContentRead(BaseModel):
    id: str
    author_id: str
    category_id: Optional[str]
    hub_id: Optional[str]

    title: str
    slug: str
    excerpt: Optional[str]
    body: str
    cover_image_url: Optional[str]

    content_type: ContentType
    status: ContentStatus
    visibility: ContentVisibility
    is_premium: bool
    reading_time_minutes: int

    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContentDetailRead(ContentRead):
    author: UserRead
    category: Optional[CategoryRead]
    hub: Optional[HubRead]


class ContentRejectRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class ContentListResponse(BaseModel):
    items: list[ContentRead]
    total: int