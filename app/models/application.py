# app/models/application.py

from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum


class ApplicationStatus(str, Enum):
    applied = "applied"
    shortlisted = "shortlisted"
    rejected = "rejected"
    hired = "hired"


class JobApplication(SQLModel, table=True):
    __tablename__ = "job_applications"

    id: int = Field(default=None, primary_key=True, index=True)

    job_id: int = Field(
        nullable=False,
        foreign_key="jobs.id",
        index=True
    )

    job_seeker_id: int = Field(
        nullable=False,
        foreign_key="users.id",
        index=True
    )

    resume_url: str = Field(nullable=False, max_length=500)

    cover_letter: str | None = Field(default=None)

    status: ApplicationStatus = Field(
        default=ApplicationStatus.applied,
        nullable=False,
        index=True
    )

    applied_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        # Prevent duplicate applications
        {"sqlite_autoincrement": True},
    )
