from typing import Optional

from pydantic import BaseModel

from app.models.education import ChildrenAgeGroup, CurriculumType, EducationResourceType
from app.schemas.common import TimestampedSchema


class EducationResourceCreate(BaseModel):
    content_id: str
    curriculum: CurriculumType
    grade_level: Optional[str] = None
    subject: Optional[str] = None
    resource_type: EducationResourceType
    download_url: Optional[str] = None


class EducationResourceRead(TimestampedSchema):
    content_id: str
    curriculum: CurriculumType
    grade_level: Optional[str]
    subject: Optional[str]
    resource_type: EducationResourceType
    download_url: Optional[str]


class ChildrenContentCreate(BaseModel):
    content_id: str
    age_group: ChildrenAgeGroup


class ChildrenContentRead(TimestampedSchema):
    content_id: str
    age_group: ChildrenAgeGroup