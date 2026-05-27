from pydantic import BaseModel


class WriterRelationshipRead(BaseModel):
    following: bool
    is_self: bool