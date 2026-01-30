from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select
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
    """
    Create a new job posting.

    **Permissions:**
    - Only users with the role 'recruiter' can create jobs.

    **Business Logic:**
    - The `recruiter_id` is automatically set to the currently logged-in user.
    - The job is set to `is_active=True` by default.
    - Timestamps (`created_at`, `updated_at`) are generated automatically.

    **Args:**
    - data (JobCreateRequest): The job details (title, description, salary, etc.).

    **Returns:**
    - JobResponse: The created job object.

    **Raises:**
    - 403 Forbidden: If the user is not a recruiter.
    """
    
    # Authorization Check
    if current_user.role != "recruiter":
        raise HTTPException(
            status_code=403,
            detail="Only recruiters can create jobs"
        )

    # Instantiate Job model
    job = Job(
        title=data.title,
        description=data.description,
        location=data.location,
        job_type=data.job_type,
        experience_level=data.experience_level,
        salary_min=data.salary_min,
        salary_max=data.salary_max,
        company_id=data.company_id,
        recruiter_id=current_user.id, # Link to current user
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    session.add(job)
    session.commit()
    session.refresh(job)

    return job


@router.get("", status_code=status.HTTP_200_OK)
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
    """
    Search and filter jobs with pagination.

    **Filters:**
    - `q`: Partial match on job title (case-insensitive).
    - `location`: Partial match on location.
    - `job_type`: Exact match (e.g., 'full_time', 'remote').
    - `experience_level`: Exact match (e.g., 'junior', 'senior').
    - `tag`: Filter by a specific tag name (e.g., 'Python').

    **Pagination:**
    - Uses `page` and `limit` to calculate the SQL `OFFSET` and `LIMIT`.

    **Returns:**
    - dict: A paginated response containing count, page info, and list of jobs.
    """
    
    # Start with base query: Only fetch active jobs
    query = select(Job).where(Job.is_active == True)

    # 🔍 Dynamic Filtering
    if q:
        query = query.where(Job.title.ilike(f"%{q}%"))

    if location:
        query = query.where(Job.location.ilike(f"%{location}%"))

    if job_type:
        query = query.where(Job.job_type == job_type)

    if experience_level:
        query = query.where(Job.experience_level == experience_level)

    # 🏷️ Tag filter: Requires joining Job -> JobTag -> Tag tables
    if tag:
        query = (
            query
            .join(JobTag)
            .join(Tag)
            .where(Tag.name == tag)
        )

    # 📄 Pagination Logic
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)

    jobs = session.exec(query).all()

    return {    
        "page": page,
        "limit": limit,
        "count": len(jobs),
        "results": jobs
    }


@router.get(
    "/{job_id}", 
    response_model=JobResponse,
    status_code=status.HTTP_200_OK
)
def get_job(
    job_id: int,
    session: Session = Depends(get_session)
):
    """
    Retrieve details of a specific job.

    **Constraint:**
    - Returns 404 if the job exists but `is_active` is False (Soft Deleted).

    **Args:**
    - job_id (int): The ID of the job.

    **Returns:**
    - JobResponse: The job details.
    """
    job = session.get(Job, job_id)

    # Check existence and active status
    if not job or not job.is_active:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@router.put(
    "/{job_id}", 
    response_model=JobResponse,
    status_code=status.HTTP_200_OK
)
def update_job(
    job_id: int,
    data: JobUpdateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Update job details.

    **Permissions:**
    - Only the recruiter who *created* the job (the owner) can update it.

    **Behavior:**
    - Performs a partial update (only fields sent in the request are updated).
    - Automatically updates the `updated_at` timestamp.

    **Raises:**
    - 404 Not Found: If job doesn't exist.
    - 403 Forbidden: If the current user is not the owner.
    """
    job = session.get(Job, job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Authorization Check: Ownership
    if job.recruiter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Dynamic Field Update
    # exclude_unset=True ensures we don't overwrite existing data with None unless explicitly sent
    for field, value in data.dict(exclude_unset=True).items():
        setattr(job, field, value)

    job.updated_at = datetime.utcnow()

    session.add(job)
    session.commit()
    session.refresh(job)

    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Soft delete a job.

    **Permissions:**
    - Only the recruiter who *created* the job can delete it.

    **Behavior:**
    - Does NOT remove the record from the database.
    - Sets `is_active` to `False`.

    **Returns:**
    - dict: Success message.
    """
    job = session.get(Job, job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Authorization Check: Ownership
    if job.recruiter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Soft Delete
    job.is_active = False
    session.add(job)
    session.commit()
    
    return {"detail": "Job deleted successfully."}


@router.get(
    "/{job_id}/applications",
    response_model=list[RecruiterApplicationResponse],
    status_code=status.HTTP_200_OK
)
def get_job_applications(
    job_id: int,
    session: Session = Depends(get_session)
):
    """
    Retrieve all applications for a specific job.

    **Permissions:**
    - Only recruiters can access this.
    - Only the recruiter who *posted* the job can view its applications.

    **Args:**
    - job_id (int): The ID of the job.

    **Returns:**
    - list[RecruiterApplicationResponse]: List of applications (includes applicant details).
    """
    
   
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    

    applications = session.exec(
        select(JobApplication)
        .where(JobApplication.job_id == job_id)
    ).all()

    return applications


@router.post(
    "/{job_id}/tags",
    status_code=status.HTTP_201_CREATED
)
def attach_tags_to_job(
    job_id: int,
    tag_ids: list[int],
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Attach existing tags to a job.

    **Permissions:**
    - Only the recruiter who owns the job can attach tags.

    **Validation:**
    - Verifies that all provided `tag_ids` actually exist in the database.
    - Prevents duplicates (if a tag is already attached, it skips it).

    **Args:**
    - job_id (int): ID of the job.
    - tag_ids (list[int]): List of Tag IDs to attach.
    """
    
    if current_user.role != "recruiter":
        raise HTTPException(status_code=403, detail="Only recruiters can attach tags")

    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.recruiter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Validate: Fetch all tags from DB that match the incoming IDs
    tags = session.exec(
        select(Tag).where(Tag.id.in_(tag_ids))
    ).all()

    # Integrity Check: Ensure we found as many tags as requested (deduplicating input)
    if len(tags) != len(set(tag_ids)):
        raise HTTPException(status_code=400, detail="One or more tags not found")

    # Attach logic: Loop through IDs and check if relation already exists
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
    """
    Remove a specific tag from a job.

    **Permissions:**
    - Only the recruiter who owns the job can remove tags.

    **Args:**
    - job_id (int): Job ID.
    - tag_id (int): Tag ID to remove.
    """
    
    if current_user.role != "recruiter":
        raise HTTPException(status_code=403, detail="Only recruiters can remove tags")

    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.recruiter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Find the relationship record
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
    """
    List all tags associated with a specific job.

    **Permissions:**
    - Public access.

    **Returns:**
    - list[Tag]: List of Tag objects.
    """
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Query: Join Tag and JobTag to find tags for this job_id
    tags = session.exec(
        select(Tag)
        .join(JobTag)
        .where(JobTag.job_id == job_id)
    ).all()

    return tags