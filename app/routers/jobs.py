from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select
from uuid import UUID
from datetime import datetime

from app.database.session import get_session
from app.models.application import JobApplication
from app.models.job import Job
from app.models.tag import JobTag, Tag
from app.models.user import User
from app.dependencies.auth import get_current_user
from app.schemas.application import RecruiterApplicationResponse
from app.schemas.job import (
    JobCreateRequest,
    JobUpdateRequest,
    JobResponse
)

router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"]
)




@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED
)
def create_job(
    data: JobCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "recruiter":
        raise HTTPException(
            status_code=403,
            detail="Only recruiters can create jobs"
        )

    job = Job(
        title=data.title,
        description=data.description,
        location=data.location,
        job_type=data.job_type,
        experience_level=data.experience_level,
        salary_min=data.salary_min,
        salary_max=data.salary_max,
        company_id=data.company_id,
        recruiter_id=current_user.id,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    session.add(job)
    session.commit()
    session.refresh(job)

    return job


# =========================
# LIST JOBS (Public)
# =========================

@router.get("")
def search_jobs(
    q: str | None = Query(default=None, description="Search by job title"),
    location: str | None = None,
    job_type: str | None = None,
    experience_level: str | None = None,
    tag: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session)
):
    query = select(Job).where(Job.is_active == True)

    # 🔍 Search by title
    if q:
        query = query.where(Job.title.ilike(f"%{q}%"))

    # 📍 Location filter
    if location:
        query = query.where(Job.location.ilike(f"%{location}%"))

    # 💼 Job type
    if job_type:
        query = query.where(Job.job_type == job_type)

    # 📈 Experience level
    if experience_level:
        query = query.where(Job.experience_level == experience_level)

    # 🏷️ Tag filter (JOIN)
    if tag:
        query = (
            query
            .join(JobTag)
            .join(Tag)
            .where(Tag.name == tag)
        )

    # 📄 Pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)

    jobs = session.exec(query).all()

    return {    
        "page": page,
        "limit": limit,
        "count": len(jobs),
        "results": jobs
    }

# =========================
# GET JOB DETAILS
# =========================

@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: int,
    session: Session = Depends(get_session)
):
    job = session.get(Job, job_id)

    if not job or not job.is_active:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


# =========================
# UPDATE JOB (Owner only)
# =========================

@router.put("/{job_id}", response_model=JobResponse)
def update_job(
    job_id: int,
    data: JobUpdateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    job = session.get(Job, job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.recruiter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    for field, value in data.dict(exclude_unset=True).items():
        setattr(job, field, value)

    job.updated_at = datetime.utcnow()

    session.add(job)
    session.commit()
    session.refresh(job)

    return job


# =========================
# DELETE JOB (Owner only)
# =========================

@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    job = session.get(Job, job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.recruiter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    job.is_active = False
    session.add(job)
    session.commit()
    return {"detail": "Job deleted successfully."}

@router.get(
    "/{job_id}/applications",
    response_model=list[RecruiterApplicationResponse]
)
def get_job_applications(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    # Role check
    if current_user.role != "recruiter":
        raise HTTPException(
            status_code=403,
            detail="Only recruiters can view job applications"
        )

    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Ownership check
    if job.recruiter_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to view applications for this job"
        )

    applications = session.exec(
        select(JobApplication)
        .where(JobApplication.job_id == job_id)
    ).all()

    return applications

@router.post(
    "/{job_id}/tags",
    status_code=201
)
def attach_tags_to_job(
    job_id: int,
    tag_ids: list[int],
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "recruiter":
        raise HTTPException(status_code=403, detail="Only recruiters can attach tags")

    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.recruiter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Validate tags
    tags = session.exec(
        select(Tag).where(Tag.id.in_(tag_ids))
    ).all()

    if len(tags) != len(set(tag_ids)):
        raise HTTPException(status_code=400, detail="One or more tags not found")

    # Attach tags (ignore existing)
    for tag_id in tag_ids:
        exists = session.exec(
            select(JobTag)
            .where(JobTag.job_id == job_id)
            .where(JobTag.tag_id == tag_id)
        ).first()

        if not exists:
            session.add(JobTag(job_id=job_id, tag_id=tag_id))

    session.commit()

    return {"message": "Tags attached successfully"}

@router.delete(
    "/{job_id}/tags/{tag_id}",
    status_code=204
)
def remove_tag_from_job(
    job_id: int,
    tag_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "recruiter":
        raise HTTPException(status_code=403, detail="Only recruiters can remove tags")

    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.recruiter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    job_tag = session.exec(
        select(JobTag)
        .where(JobTag.job_id == job_id)
        .where(JobTag.tag_id == tag_id)
    ).first()

    if not job_tag:
        raise HTTPException(status_code=404, detail="Tag not attached to job")

    session.delete(job_tag)
    session.commit()

    return {"message": "Tag removed successfully"}

@router.get("/{job_id}/tags")
def list_job_tags(
    job_id: int,
    session: Session = Depends(get_session)
):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    tags = session.exec(
        select(Tag)
        .join(JobTag)
        .where(JobTag.job_id == job_id)
    ).all()

    return tags
