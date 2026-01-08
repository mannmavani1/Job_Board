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
    tag = Tag(
        name=data.name,
        description=data.description
    )

    session.add(tag)
    session.commit()
    session.refresh(tag)

    return tag

@router.get("", response_model=list[TagResponse])
def list_tags(
    session: Session = Depends(get_session)
):
    tags = session.exec(select(Tag)).all()
    return tags

@router.get("/{tag_id}", response_model=TagResponse)
def get_tag(
    tag_id: int,
    session: Session = Depends(get_session)
):
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
):
    tag = session.get(Tag, tag_id)
    if not tag:
        raise HTTPException(
            status_code=404,
            detail="Tag not found"
        )

    tag.name = data.name
    tag.description = data.description

    session.add(tag)
    session.commit()
    session.refresh(tag)

    return tag

@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    tag_id: int,
    session: Session = Depends(get_session),
):
    tag = session.get(Tag, tag_id)
    if not tag:
        raise HTTPException(
            status_code=404,
            detail="Tag not found"
        )

    session.delete(tag)
    session.commit()

    return {"detail": "Tag deleted successfully."}