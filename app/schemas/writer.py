from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from app.models.user import UserRole
from app.schemas.content import ContentRead


class WriterProfileRead(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    username: Optional[str]
    role: UserRole
    avatar_url: Optional[str]
    bio: Optional[str]
    is_verified: bool
    created_at: datetime

    followers_count: int = 0
    published_count: int = 0

    model_config = {"from_attributes": True}


class WriterContentResponse(BaseModel):
    writer: WriterProfileRead
    items: list[ContentRead]
    total: int