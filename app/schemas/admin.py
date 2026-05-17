from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


class AdminDashboardStats(BaseModel):
    total_users: int
    total_readers: int
    total_writers: int
    total_teachers: int
    total_students: int
    total_parents: int
    total_moderators: int
    total_admins: int

    total_content: int
    pending_content: int
    published_content: int
    rejected_content: int

    total_categories: int
    total_hubs: int
    total_partnerships: int
    active_partnerships: int


class AdminUserRead(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    username: Optional[str]
    role: UserRole
    avatar_url: Optional[str]
    bio: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AdminUserListResponse(BaseModel):
    items: list[AdminUserRead]
    total: int
    skip: int
    limit: int


class AdminUpdateUserRoleRequest(BaseModel):
    role: UserRole
    is_verified: Optional[bool] = None


class AdminUpdateUserStatusRequest(BaseModel):
    is_active: bool