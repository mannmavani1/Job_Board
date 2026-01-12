from sqlmodel import SQLModel, Field
from datetime import datetime, timezone
from enum import Enum


def utc_now():
    """Helper to get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class UserRole(str, Enum):
    """
    Enumeration defining the two main types of users in the system.
    """
    recruiter = "recruiter"     # Can create companies and post jobs
    job_seeker = "job_seeker"   # Can search for jobs and apply


class User(SQLModel, table=True):
    """
    Database model representing a registered User.

    **Security:**
    - Stores hashed passwords, never plain text.
    - Uses email as the unique identifier for login.

    **Relationships:**
    - One-to-Many with Company (A Recruiter can own companies).
    - One-to-Many with JobApplication (A Job Seeker can have many applications).
    """
    __tablename__ = "users"

    id: int = Field(default=None, primary_key=True, index=True)

    email: str = Field(
        nullable=False,
        unique=True,
        index=True,
        max_length=255,
        description="Unique email address used for login."
    )

    hashed_password: str = Field(
        nullable=False,
        description="Bcrypt hashed password string."
    )

    role: UserRole = Field(
        nullable=False,
        description="Role of the user (recruiter or job_seeker)."
    )

    is_active: bool = Field(
        default=True,
        description="If False, the user is banned or deactivated."
    )

    # Timestamps with Timezone-aware default
    created_at: datetime = Field(
        default_factory=utc_now,
        description="Timestamp when the user registered."
    )