from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone


def utc_now():
    """Helper to get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class Company(SQLModel, table=True):
    """
    Database model representing a Company profile.

    **Ownership:**
    - Each company is linked to a specific Recruiter via `recruiter_id`.
    - Only the creator (recruiter) can edit or delete their company profile.

    **Relationships:**
    - One-to-Many with Jobs (One company can have multiple job postings).
    - Many-to-Many with Recruiters (Implemented via `company_recruiter_links` table).
    """
    __tablename__ = "companies"

    id: int = Field(default=None, primary_key=True, index=True)

    name: str = Field(
        nullable=False,
        index=True,
        max_length=255,
        description="Name of the company (must be unique per recruiter/system logic)."
    )

    description: Optional[str] = Field(
        default=None,
        description="Detailed text about the company, culture, and mission."
    )

    website: Optional[str] = Field(
        default=None,
        max_length=255,
        description="External link to the company's official website."
    )

    location: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Headquarters or primary location."
    )

    recruiter_id: int = Field(
        nullable=False,
        foreign_key="users.id",
        index=True,
        description="Foreign Key linking to the Recruiter (User) who owns this profile."
    )

    created_at: datetime = Field(
        default_factory=utc_now,
        description="Timestamp of profile creation."
    )
    
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"onupdate": utc_now},
        description="Timestamp of the last update. Automatically updates on DB write."
    )

class CompanyRecruiterLink(SQLModel, table=True):
    """
    Link table (Association Model) for the Many-to-Many relationship 
    between Companies and Recruiters.

    **Composite Primary Key:**
    - The combination of `company_id` and `recruiter_id` serves as the primary key.
    - This ensures a specific recruiter can only be linked to a specific company once.
    """
    __tablename__ = "company_recruiter_links"

    company_id: int = Field(
        foreign_key="companies.id",
        primary_key=True,
        description="ID of the Company."
    )

    recruiter_id: int = Field(
        foreign_key="users.id",
        primary_key=True,
        description="ID of the Recruiter (User)."
    )