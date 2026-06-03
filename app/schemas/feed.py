from pydantic import BaseModel

from app.schemas.content import ContentRead


class FeedResponse(BaseModel):
    items: list[ContentRead]
    total: int
    skip: int = 0
    limit: int = 20


class SearchResponse(BaseModel):
    query: str
    items: list[ContentRead]
    total: int