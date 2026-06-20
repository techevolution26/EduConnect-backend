from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ReadSessionStart(BaseModel):
    content_id: str


class ReadSessionHeartbeat(BaseModel):
    active_seconds_delta: int = 0
    scroll_percent: int = 0
    tab_visible: bool = True


class ReadSessionFinish(BaseModel):
    active_seconds_delta: int = 0
    scroll_percent: int = 0
    tab_visible: bool = True


class ReadSessionRead(BaseModel):
    id: str
    content_id: str
    user_id: str
    started_at: datetime
    last_active_at: datetime
    ended_at: datetime | None
    active_seconds: int
    max_scroll_percent: int
    tab_visible: bool
    is_completed: bool
    is_qualified: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)