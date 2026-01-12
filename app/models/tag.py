from sqlmodel import SQLModel, Field
from typing import Optional


class Tag(SQLModel, table=True):
    """
    Database model representing a specific skill, technology, or category.

    **Usage:**
    - Used to categorize jobs (e.g., "Python", "Remote", "DevOps").
    - Tags are unique by name to prevent duplicates like "python" and "Python".

    **Relationships:**
    - Many-to-Many with Jobs (via JobTag link table).
    """
    __tablename__ = "tags"

    id: int = Field(default=None, primary_key=True, index=True)

    name: str = Field(
        nullable=False,
        unique=True,
        index=True,
        max_length=100,
        description="Unique name of the tag (e.g., 'FastAPI')."
    )

    description: Optional[str] = Field(
        default=None,
        description="Optional brief description of what this tag represents."
    )


class JobTag(SQLModel, table=True):
    """
    Link table (Association Model) for the Many-to-Many relationship 
    between Jobs and Tags.

    **Composite Primary Key:**
    - The combination of `job_id` and `tag_id` serves as the primary key.
    - This ensures a specific tag can only be attached to a specific job once.
    """
    __tablename__ = "job_tags"

    job_id: int = Field(
        foreign_key="jobs.id",
        primary_key=True,
        description="ID of the Job."
    )

    tag_id: int = Field(
        foreign_key="tags.id",
        primary_key=True,
        description="ID of the Tag."
    )