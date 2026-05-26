from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.moderation import ModerationAction


class ModerationLogRead(BaseModel):
    id: str
    moderator_id: str
    content_id: Optional[str]
    action: ModerationAction
    note: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}