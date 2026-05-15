from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.user import UserRead


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    parent_id: Optional[str] = None


class CommentRead(BaseModel):
    id: str
    content_id: str
    user_id: str
    parent_id: Optional[str]
    body: str
    is_hidden: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CommentDetailRead(CommentRead):
    user: Optional[UserRead] = None


class EngagementStatus(BaseModel):
    liked: bool = False
    bookmarked: bool = False
    following: bool = False


class CountResponse(BaseModel):
    count: int