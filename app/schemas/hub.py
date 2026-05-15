from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    username: Optional[str] = Field(default=None, max_length=80)
    role: UserRole = UserRole.READER


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=160)
    username: Optional[str] = Field(default=None, max_length=80)
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class UserRead(BaseModel):
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

    model_config = {"from_attributes": True}

class HubRead(BaseModel):
    id: str
    name: str
    description: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}

class HubCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=2, max_length=100)
    description: Optional[str] = None


class HubUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    description: Optional[str] = None