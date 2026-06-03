# make ChildrenContentRead schema
from pydantic.v1 import BaseModel


class ChildrenContentRead(BaseModel):
    id: int
    title: str
    description: str
    age_group: str
    content: str
    model_config = {"from_attributes": True}
