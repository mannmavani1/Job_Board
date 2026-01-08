from sqlmodel import SQLModel, Field
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime


class Company(SQLModel, table=True):
    __tablename__ = "companies"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)

    name: str = Field(nullable=False, index=True, max_length=255)

    description: Optional[str] = Field(default=None)

    website: Optional[str] = Field(default=None, max_length=255)

    location: Optional[str] = Field(default=None, max_length=255)

    recruiter_id: UUID = Field(
        nullable=False,
        unique=True,
        foreign_key="users.id",
        index=True
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"onupdate": datetime.utcnow}
    )