from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedSchema


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str = Field(min_length=2, max_length=140)
    description: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    slug: Optional[str] = Field(default=None, min_length=2, max_length=140)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class CategoryRead(TimestampedSchema):
    name: str
    slug: str
    description: Optional[str]
    is_active: bool