from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampedSchema(BaseSchema):
    id: str
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    message: str