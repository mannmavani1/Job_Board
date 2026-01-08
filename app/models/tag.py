from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4


class Tag(SQLModel, table=True):
    __tablename__ = "tags"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)

    name: str = Field(
        nullable=False,
        unique=True,
        index=True,
        max_length=100
    )


class JobTag(SQLModel, table=True):
    __tablename__ = "job_tags"

    job_id: UUID = Field(
        foreign_key="jobs.id",
        primary_key=True
    )

    tag_id: UUID = Field(
        foreign_key="tags.id",
        primary_key=True
    )
