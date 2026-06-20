from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole
from app.schemas.content import ContentRead


class WriterAnalyticsRead(BaseModel):
    total_content: int = 0
    drafts: int = 0
    pending: int = 0
    published: int = 0
    rejected: int = 0
    followers: int = 0
    likes_received: int = 0
    comments_received: int = 0
    bookmarks_received: int = 0

    estimated_earnings_total: float = 0.0
    estimated_earnings_pending: float = 0.0
    estimated_monthly_earnings: float = 0.0
    estimated_partner_reads: int = 0
    qualified_reads: int = 0


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

    analytics: WriterAnalyticsRead = Field(default_factory=WriterAnalyticsRead)

    model_config = ConfigDict(from_attributes=True)


class WriterContentResponse(BaseModel):
    writer: WriterProfileRead
    items: list[ContentRead]
    total: int