from pydantic import BaseModel, EmailStr
from uuid import UUID
from typing import Optional
from datetime import datetime


class CompanyCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None


class CompanyUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None


class CompanyResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    website: Optional[str]
    location: Optional[str]
    recruiter_id: int
    created_at: datetime

class AddRecruiterRequest(BaseModel):
    email: EmailStr
    password: Optional[str]= None
