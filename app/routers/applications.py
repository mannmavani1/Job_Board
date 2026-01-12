from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from uuid import UUID
from datetime import datetime

from app.database.session import get_session
from app.dependencies.auth import get_current_user
from app.models.application import JobApplication
from app.models.job import Job
from app.models.user import User
from app.schemas.application import (
    ApplyJobRequest,
    JobApplicationResponse,
    UpdateApplicationRequest
)
from app.schemas.application import UpdateApplicationStatusRequest

router = APIRouter(
    prefix="/applications",
    tags=["Applications"]
)


@router.post(
    "/jobs/{job_id}/apply",
    response_model=JobApplicationResponse,
    status_code=status.HTTP_201_CREATED
)
def apply_to_job(
    job_id: int,
    data: ApplyJobRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Submit a new application for a specific job.

    **Permissions:**
    - Only users with the role 'job_seeker' can apply.

    **Business Logic:**
    - Verifies the job exists and is currently active.
    - Prevents users from applying to the same job more than once.
    - Records the timestamp of the application.

    **Args:**
    - job_id (int): The ID of the job to apply for.
    - data (ApplyJobRequest): Resume URL and optional cover letter.

    **Returns:**
    - JobApplication: The created application object.
    """
    
    # Authorization Check: Ensure user is a job seeker
    if current_user.role != "job_seeker":
        raise HTTPException(
            status_code=403,
            detail="Only job seekers can apply to jobs"
        )

    # Validation: Check if job exists and is active
    job = session.get(Job, job_id)
    if not job or not job.is_active:
        raise HTTPException(
            status_code=404,
            detail="Job not available"
        )

    # Validation: Check for duplicate applications
    existing_application = session.exec(
        select(JobApplication)
        .where(JobApplication.job_id == job_id)
        .where(JobApplication.job_seeker_id == current_user.id)
    ).first()

    if existing_application:
        raise HTTPException(
            status_code=400,
            detail="You have already applied to this job"
        )

    # Create the application record
    application = JobApplication(
        job_id=job_id,
        job_seeker_id=current_user.id,
        resume_url=data.resume_url,
        cover_letter=data.cover_letter,
        applied_at=datetime.utcnow()
    )

    session.add(application)
    session.commit()
    session.refresh(application)

    return application


@router.get(
    "/me",
    response_model=list[JobApplicationResponse],
    status_code=status.HTTP_200_OK
)
def my_applications(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve all applications submitted by the current logged-in user.

    **Permissions:**
    - Only users with the role 'job_seeker' can access this endpoint.

    **Returns:**
    - list[JobApplication]: A list of applications owned by the user.
    """
    
    # Authorization Check
    if current_user.role != "job_seeker":
        raise HTTPException(
            status_code=403,
            detail="Only job seekers can view applications"
        )

    # Query: Fetch all applications where the seeker ID matches the current user
    return session.exec(
        select(JobApplication)
        .where(JobApplication.job_seeker_id == current_user.id)
    ).all()


@router.put(
    "/{application_id}",
    response_model=JobApplicationResponse,
    status_code=status.HTTP_200_OK
)
def update_application(
    application_id: int,
    data: UpdateApplicationRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Update details of an existing application (e.g., Resume URL or Cover Letter).

    **Permissions:**
    - Only the job seeker who created the application can update it.

    **Constraints:**
    - Applications with the status 'hired' cannot be modified.

    **Args:**
    - application_id (int): ID of the application to update.
    - data (UpdateApplicationRequest): Fields to update.

    **Returns:**
    - JobApplication: The updated application object.
    """
    
    # Authorization Check: Role
    if current_user.role != "job_seeker":
        raise HTTPException(
            status_code=403,
            detail="Only job seekers can update applications"
        )

    # Retrieve application
    application = session.get(JobApplication, application_id)

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Authorization Check: Ownership
    if application.job_seeker_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to update this application"
        )

    # Validation: Prevent modification of finalized applications
    if application.status == "hired":
        raise HTTPException(
            status_code=400,
            detail="Cannot update a hired application"
        )

    # Update fields dynamically based on provided data
    for field, value in data.dict(exclude_unset=True).items():
        setattr(application, field, value)

    session.add(application)
    session.commit()
    session.refresh(application)

    return application


@router.delete(
    "/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def withdraw_application(
    application_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Withdraw (delete) a job application.

    **Permissions:**
    - Only the job seeker who created the application can withdraw it.

    **Constraints:**
    - Applications with the status 'hired' cannot be withdrawn.

    **Args:**
    - application_id (int): ID of the application to withdraw.

    **Returns:**
    - 204 No Content on success.
    """
    
    # Authorization Check: Role
    if current_user.role != "job_seeker":
        raise HTTPException(
            status_code=403,
            detail="Only job seekers can withdraw applications"
        )

    application = session.get(JobApplication, application_id)

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Authorization Check: Ownership
    if application.job_seeker_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to delete this application"
        )

    # Validation: Prevent withdrawal of finalized applications
    if application.status == "hired":
        raise HTTPException(
            status_code=400,
            detail="Cannot withdraw a hired application"
        )

    session.delete(application)
    session.commit()

    return {"detail": "Application withdrawn successfully"}


@router.put(
    "/{application_id}/status",
    response_model=JobApplicationResponse
)
def update_application_status(
    application_id: int,
    data: UpdateApplicationStatusRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Update the status of an application (e.g., Applied -> Shortlisted -> Hired).

    **Permissions:**
    - Only users with the role 'recruiter' can perform this action.
    - The recruiter MUST be the owner of the job associated with this application.

    **Constraints:**
    - Status cannot be changed if the applicant is already 'hired'.

    **Args:**
    - application_id (int): ID of the application to update.
    - data (UpdateApplicationStatusRequest): New status enum.

    **Returns:**
    - JobApplication: The updated application object.
    """
    
    # Authorization Check: Role
    if current_user.role != "recruiter":
        raise HTTPException(
            status_code=403,
            detail="Only recruiters can update application status"
        )

    # Retrieve Application and associated Job
    application = session.get(JobApplication, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    job = session.get(Job, application.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Authorization Check: Recruiter Ownership
    # Ensure the logged-in recruiter is the one who posted the job
    if job.recruiter_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to update this application"
        )

    # Validation: Prevent changing status of hired candidates
    if application.status == "hired":
        raise HTTPException(
            status_code=400,
            detail="Cannot update a hired application"
        )

    # Update status
    application.status = data.status

    session.add(application)
    session.commit()
    session.refresh(application)

    return application