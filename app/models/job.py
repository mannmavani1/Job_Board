from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone
from enum import Enum


def utc_now():
    """Helper to get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class JobType(str, Enum):
    """
    Enumeration for the type of employment offered.
    """
    full_time = "full_time"
    part_time = "part_time"
    internship = "internship"
    contract = "contract"
    remote = "remote"


class ExperienceLevel(str, Enum):
    """
    Enumeration for the required experience level.
    """
    junior = "junior"       # 0-2 years
    mid = "mid"             # 2-5 years
    senior = "senior"       # 5+ years
    intern = "intern"       # Student/Trainee
    fresher = "fresher"     # Recent graduate


class Job(SQLModel, table=True):
    """
    Database model representing a Job Posting.

    **Relationships:**
    - Many-to-One with Company (A job belongs to one company).
    - Many-to-One with User (A job is posted by one Recruiter).
    - One-to-Many with JobApplication (A job has many applicants).
    - Many-to-Many with Tag (A job can have multiple skill tags).
    """
    __tablename__ = "jobs"

    id: int = Field(default=None, primary_key=True, index=True)

    title: str = Field(
        nullable=False, 
        index=True, 
        max_length=255,
        description="The job title (e.g., 'Senior Backend Engineer')."
    )

    description: str = Field(
        nullable=False,
        description="Full job description, requirements, and benefits."
    )

    location: Optional[str] = Field(
        default=None, 
        index=True, 
        max_length=255,
        description="Physical location or 'Remote'."
    )

    job_type: JobType = Field(
        nullable=False, 
        index=True,
        description="Type of employment (Full-time, Contract, etc.)."
    )

    experience_level: ExperienceLevel = Field(
        nullable=False, 
        index=True,
        description="Required seniority level."
    )

    salary_min: Optional[int] = Field(
        default=None,
        description="Minimum annual/monthly salary offer."
    )
    
    salary_max: Optional[int] = Field(
        default=None,
        description="Maximum annual/monthly salary offer."
    )

    recruiter_id: int = Field(
        nullable=False,
        foreign_key="users.id",
        index=True,
        description="ID of the Recruiter who posted this job."
    )

    company_id: int = Field(
        nullable=False,
        foreign_key="companies.id",
        index=True,
        description="ID of the Company this job is for."
    )

    is_active: bool = Field(
        default=True,
        description="If False, the job is 'Soft Deleted' or closed."
    )

    created_at: datetime = Field(
        default_factory=utc_now,
        description="Timestamp when the job was posted."
    )
    
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"onupdate": utc_now},
        description="Timestamp of the last edit."
    )