from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CommentAuthorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: Optional[str] = None
    full_name: Optional[str] = None


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    body: str
    created_at: datetime
    user: Optional[CommentAuthorRead] = None