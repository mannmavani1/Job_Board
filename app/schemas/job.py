# app/schemas/job.py

from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime


class JobCreateRequest(BaseModel):
    title: str
    description: str
    location: Optional[str] = None
    job_type: str
    experience_level: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    company_id: int


class JobUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    is_active: Optional[bool] = None


class JobResponse(BaseModel):
    id: int
    title: str
    description: str
    location: Optional[str]
    job_type: str
    experience_level: str
    salary_min: Optional[int]
    salary_max: Optional[int]
    company_id: int
    recruiter_id: int
    is_active: bool
    created_at: datetime
