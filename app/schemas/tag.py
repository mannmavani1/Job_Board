from pydantic import BaseModel


class TagCreateRequest(BaseModel):
    name: str


class TagUpdateRequest(BaseModel):
    name: str


class TagResponse(BaseModel):
    id: int
    name: str
