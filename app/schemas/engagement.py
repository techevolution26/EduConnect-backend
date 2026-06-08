from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserRead


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    parent_id: Optional[str] = None


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    content_id: str
    user_id: str
    parent_id: Optional[str] = None
    body: str
    is_hidden: bool
    created_at: datetime
    updated_at: datetime
    user: Optional[UserRead] = None
    likes_count: int = 0
    liked_by_me: bool = False


class EngagementStatus(BaseModel):
    liked: bool = False
    bookmarked: bool = False
    following: bool = False


class CountResponse(BaseModel):
    count: int