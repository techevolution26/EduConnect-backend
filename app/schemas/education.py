from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.education import (
    ChildrenAgeGroup,
    CurriculumType,
    EducationResourceType,
)
from app.schemas.content import ContentRead


class EducationResourceCreate(BaseModel):
    content_id: str
    curriculum: CurriculumType
    grade_level: Optional[str] = None
    subject: Optional[str] = None
    resource_type: EducationResourceType
    download_url: Optional[str] = None


class EducationResourceRead(BaseModel):
    id: str
    content_id: str
    curriculum: CurriculumType
    grade_level: Optional[str]
    subject: Optional[str]
    resource_type: EducationResourceType
    download_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EducationResourceDetailRead(EducationResourceRead):
    content: Optional[ContentRead] = None


class ChildrenContentCreate(BaseModel):
    content_id: str
    age_group: ChildrenAgeGroup


class ChildrenContentRead(BaseModel):
    id: str
    content_id: str
    age_group: ChildrenAgeGroup
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChildrenContentDetailRead(ChildrenContentRead):
    content: Optional[ContentRead] = None