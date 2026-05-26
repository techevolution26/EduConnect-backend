from pydantic import BaseModel


class WriterAnalyticsRead(BaseModel):
    total_content: int
    drafts: int
    pending: int
    published: int
    rejected: int
    followers: int
    likes_received: int
    comments_received: int
    bookmarks_received: int