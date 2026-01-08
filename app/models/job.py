# app/models/job.py

from sqlmodel import SQLModel, Field
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum


class JobType(str, Enum):
    full_time = "full_time"
    part_time = "part_time"
    internship = "internship"
    contract = "contract"
    remote = "remote"


class ExperienceLevel(str, Enum):
    junior = "junior"
    mid = "mid"
    senior = "senior"
    intern = "intern"
    fresher = "fresher"


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: int = Field(default=None, primary_key=True, index=True)

    title: str = Field(nullable=False, index=True, max_length=255)

    description: str = Field(nullable=False)

    location: Optional[str] = Field(default=None, index=True, max_length=255)

    job_type: JobType = Field(nullable=False, index=True)

    experience_level: ExperienceLevel = Field(nullable=False, index=True)

    salary_min: Optional[int] = Field(default=None)
    salary_max: Optional[int] = Field(default=None)

    recruiter_id: int = Field(
        nullable=False,
        foreign_key="users.id",
        index=True
    )

    company_id: int = Field(
        nullable=False,
        foreign_key="companies.id",
        index=True
    )

    is_active: bool = Field(default=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"onupdate": datetime.utcnow}
    )