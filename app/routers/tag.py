from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database.session import get_session
from app.models.tag import Tag
from app.models.user import User
from app.dependencies.auth import get_current_user
from app.schemas.tag import (
    TagCreateRequest,
    TagUpdateRequest,
    TagResponse
)

router = APIRouter(
    prefix="/tags",
    tags=["Tags"]
)


@router.post(
    "",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED
)
def create_tag(
    data: TagCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new job tag.

    **Permissions:**
    - Any authenticated user can create a tag (Recruiter or Job Seeker).
    - This allows the ecosystem of tags to grow based on user needs.

    **Args:**
    - data (TagCreateRequest): The tag details (name, description).

    **Returns:**
    - TagResponse: The created tag object.
    """
    
    # Create the Tag model instance
    tag = Tag(
        name=data.name,
        description=data.description
    )

    # Persist to database
    session.add(tag)
    session.commit()
    session.refresh(tag)

    return tag


@router.get("", response_model=list[TagResponse])
def list_tags(
    session: Session = Depends(get_session)
):
    """
    Retrieve a list of all available job tags.

    **Permissions:**
    - Public access. Used for populating dropdowns or filter lists in the UI.

    **Returns:**
    - list[TagResponse]: A list of all tag objects.
    """
    
    # Query all tags from the database
    tags = session.exec(select(Tag)).all()
    return tags


@router.get("/{tag_id}", response_model=TagResponse)
def get_tag(
    tag_id: int,
    session: Session = Depends(get_session)
):
    """
    Retrieve a specific tag by its ID.

    **Args:**
    - tag_id (int): The unique identifier of the tag.

    **Returns:**
    - TagResponse: The requested tag.

    **Raises:**
    - 404 Not Found: If the tag ID does not exist.
    """
    
    tag = session.get(Tag, tag_id)
    
    if not tag:
        raise HTTPException(
            status_code=404,
            detail="Tag not found"
        )
    return tag


@router.put("/{tag_id}", response_model=TagResponse)
def update_tag(
    tag_id: int,
    data: TagUpdateRequest,
    session: Session = Depends(get_session),
    # Note: Authorization dependency could be added here if you want to restrict updates
):
    """
    Update an existing tag's details.

    **Business Logic:**
    - Updates the name and description of the tag.

    **Args:**
    - tag_id (int): ID of the tag to update.
    - data (TagUpdateRequest): New values for name and description.

    **Returns:**
    - TagResponse: The updated tag object.

    **Raises:**
    - 404 Not Found: If the tag does not exist.
    """
    
    # Check if tag exists
    tag = session.get(Tag, tag_id)
    if not tag:
        raise HTTPException(
            status_code=404,
            detail="Tag not found"
        )

    # Update fields
    tag.name = data.name
    tag.description = data.description

    # Save changes
    session.add(tag)
    session.commit()
    session.refresh(tag)

    return tag


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    tag_id: int,
    session: Session = Depends(get_session),
    # Note: Authorization dependency could be added here to restrict deletion
):
    """
    Delete a tag from the system.

    **Args:**
    - tag_id (int): ID of the tag to delete.

    **Returns:**
    - dict: Success message.

    **Raises:**
    - 404 Not Found: If the tag does not exist.
    """
    
    # Check if tag exists
    tag = session.get(Tag, tag_id)
    if not tag:
        raise HTTPException(
            status_code=404,
            detail="Tag not found"
        )

    # Delete the record
    session.delete(tag)
    session.commit()

    return {"detail": "Tag deleted successfully."}