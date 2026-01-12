from sqlmodel import SQLModel, Field
from datetime import datetime, timezone
from enum import Enum

def utc_now():
    """Helper to get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class ApplicationStatus(str, Enum):
    """
    Enum representing the lifecycle stages of a job application.
    """
    applied = "applied"         # Initial state
    shortlisted = "shortlisted" # Recruiter is interested
    rejected = "rejected"       # Application denied
    hired = "hired"             # Final successful state


class JobApplication(SQLModel, table=True):
    """
    Database model representing a User's application to a Job.

    **Relationships:**
    - Many-to-One with Job (one job has many applications).
    - Many-to-One with User (one user can apply to many jobs).

    **Constraints:**
    - A user cannot apply to the same job twice (enforced via logic/composite keys in DB usually, 
      but here handled in the router logic).
    """
    __tablename__ = "job_applications"

    id: int = Field(default=None, primary_key=True, index=True)

    job_id: int = Field(
        nullable=False,
        foreign_key="jobs.id",
        index=True,
        description="ID of the Job listing."
    )

    job_seeker_id: int = Field(
        nullable=False,
        foreign_key="users.id",
        index=True,
        description="ID of the User (Job Seeker) applying."
    )

    resume_url: str = Field(
        nullable=False, 
        max_length=500,
        description="URL to the applicant's resume (e.g., S3 or public link)."
    )

    cover_letter: str | None = Field(
        default=None,
        description="Optional cover letter text."
    )

    status: ApplicationStatus = Field(
        default=ApplicationStatus.applied,
        nullable=False,
        index=True,
        description="Current status of the application."
    )

    applied_at: datetime = Field(
        default_factory=utc_now,
        description="Timestamp when the application was created (UTC)."
    )

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )