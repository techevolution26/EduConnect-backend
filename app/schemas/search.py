from pydantic import BaseModel

from app.schemas.category import CategoryRead
from app.schemas.children import ChildrenContentRead
from app.schemas.content import ContentRead
from app.schemas.education import EducationResourceRead
from app.schemas.hub import HubRead
from app.schemas.writer import WriterProfileRead


class GlobalSearchResponse(BaseModel):
    query: str
    content: list[ContentRead]
    writers: list[WriterProfileRead]
    hubs: list[HubRead]
    categories: list[CategoryRead]
    education_resources: list[EducationResourceRead]
    children_content: list[ChildrenContentRead]