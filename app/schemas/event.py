from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.event import EventStatus, EventType, ParticipationStatus


class EventCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: Optional[str] = None
    type: EventType
    curriculum_tags: list[str] = Field(default_factory=list)
    student_only: bool = False
    school_id: Optional[str] = None
    requires_partnership: bool = False
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    max_participants: Optional[int] = Field(default=None, ge=1)
    metadata: dict = Field(default_factory=dict)
    cover_image_url: Optional[str] = None


class EventRead(BaseModel):
    id: str
    title: str
    slug: str
    description: Optional[str]
    type: EventType
    status: EventStatus
    host_id: str
    curriculum_tags: list[str]
    student_only: bool
    school_id: Optional[str]
    requires_partnership: bool
    starts_at: Optional[datetime]
    ends_at: Optional[datetime]
    max_participants: Optional[int]
    cover_image_url: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class EventDetailRead(EventRead):
    metadata: dict = Field(validation_alias="metadata_json", serialization_alias="metadata")

    model_config = {"from_attributes": True, "populate_by_name": True}


class EventListResponse(BaseModel):
    items: list[EventRead]
    total: int
    skip: int
    limit: int


class EventParticipantRead(BaseModel):
    id: str
    event_id: str
    user_id: str
    status: ParticipationStatus
    xp_awarded: int
    submission: Optional[dict]
    created_at: datetime

    model_config = {"from_attributes": True}


class EventSubmissionCreate(BaseModel):
    content_id: Optional[str] = None
    note: Optional[str] = Field(default=None, max_length=2000)
    url: Optional[str] = None
