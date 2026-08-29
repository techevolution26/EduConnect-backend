from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    user_id: str
    full_name: Optional[str] = None
    total_xp: int
    rank: int


class LeaderboardResponse(BaseModel):
    period: Literal["all_time", "month"]
    school_id: Optional[str] = None
    entries: list[LeaderboardEntry]


class MyXPRead(BaseModel):
    total_xp: int
    rank: Optional[int] = None
    school_rank: Optional[int] = None


class BadgeCreate(BaseModel):
    slug: str
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    xp_reward: int = 100
    condition: dict


class BadgeRead(BaseModel):
    id: str
    slug: str
    name: str
    description: Optional[str]
    icon: Optional[str]
    xp_reward: int

    model_config = {"from_attributes": True}


class UserBadgeRead(BaseModel):
    badge: BadgeRead
    awarded_at: datetime

    model_config = {"from_attributes": True}
