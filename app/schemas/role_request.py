from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.role_request import RoleRequestStatus
from app.models.user import UserRole
from app.schemas.user import UserRead


class RoleUpgradeRequestCreate(BaseModel):
    requested_role: UserRole
    reason: str = Field(min_length=10, max_length=2000)


class RoleUpgradeRequestReview(BaseModel):
    admin_note: Optional[str] = Field(default=None, max_length=2000)


class RoleUpgradeRequestRead(BaseModel):
    id: str
    user_id: str
    requested_role: UserRole
    reason: str
    status: RoleRequestStatus
    admin_note: Optional[str]
    reviewed_by_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RoleUpgradeRequestDetailRead(RoleUpgradeRequestRead):
    user: Optional[UserRead] = None


class RoleUpgradeRequestListResponse(BaseModel):
    items: list[RoleUpgradeRequestDetailRead]
    total: int