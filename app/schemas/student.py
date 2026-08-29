from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.student import SchoolType


class SchoolRead(BaseModel):
    id: str
    name: str
    county: Optional[str]
    type: Optional[SchoolType]

    model_config = {"from_attributes": True}


class SchoolCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    county: Optional[str] = None
    type: Optional[SchoolType] = None


class StudentProfileRead(BaseModel):
    user_id: str
    school_id: Optional[str]
    grade_level: Optional[str]
    curriculum: Optional[str]
    verified: bool
    verified_at: Optional[datetime]

    model_config = {"from_attributes": True}


class StudentAffiliationUpdate(BaseModel):
    school_id: str
    grade_level: Optional[str] = Field(default=None, max_length=50)
    curriculum: Optional[str] = Field(default=None, max_length=30)


class StudentVerificationRequest(BaseModel):
    school_email: EmailStr


class StudentVerificationConfirm(BaseModel):
    code: str = Field(min_length=6, max_length=6)
