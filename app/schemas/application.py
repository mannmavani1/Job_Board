from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.models.application import ApplicationStatus


class ApplyJobRequest(BaseModel):
    resume_url: str
    cover_letter: Optional[str] = None


class JobApplicationResponse(BaseModel):
    id: int
    job_id: int
    job_seeker_id: int
    resume_url: str
    cover_letter: Optional[str]
    status: ApplicationStatus
    applied_at: datetime

class UpdateApplicationRequest(BaseModel):
    resume_url: Optional[str] = None
    cover_letter: Optional[str] = None

class RecruiterApplicationResponse(BaseModel):
    id: int 
    job_id: int
    job_seeker_id: int
    resume_url: str
    cover_letter: str | None
    status: ApplicationStatus
    applied_at: datetime


class UpdateApplicationStatusRequest(BaseModel):
    status: ApplicationStatus
