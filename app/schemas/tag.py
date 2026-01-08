from pydantic import BaseModel
from typing import Optional

class TagCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None 

class TagUpdateRequest(BaseModel):
    name: str
    description: Optional[str] = None

class TagResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None