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
from app.models.job import Job

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
    if current_user.role != "job_seeker":
        raise HTTPException(
            status_code=403,
            detail="Only job seekers can apply to jobs"
        )

    job = session.get(Job, job_id)
    if not job or not job.is_active:
        raise HTTPException(
            status_code=404,
            detail="Job not available"
        )

    # Prevent duplicate applications
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
    if current_user.role != "job_seeker":
        raise HTTPException(
            status_code=403,
            detail="Only job seekers can view applications"
        )

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
    if current_user.role != "job_seeker":
        raise HTTPException(
            status_code=403,
            detail="Only job seekers can update applications"
        )

    application = session.get(JobApplication, application_id)

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    if application.job_seeker_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to update this application"
        )

    if application.status == "hired":
        raise HTTPException(
            status_code=400,
            detail="Cannot update a hired application"
        )

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
    if current_user.role != "job_seeker":
        raise HTTPException(
            status_code=403,
            detail="Only job seekers can withdraw applications"
        )

    application = session.get(JobApplication, application_id)

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    if application.job_seeker_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to delete this application"
        )

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
    # Recruiter only
    if current_user.role != "recruiter":
        raise HTTPException(
            status_code=403,
            detail="Only recruiters can update application status"
        )

    application = session.get(JobApplication, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    job = session.get(Job, application.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Ownership check
    if job.recruiter_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to update this application"
        )

    if application.status == "hired":
        raise HTTPException(
            status_code=400,
            detail="Cannot update a hired application"
        )

    application.status = data.status

    session.add(application)
    session.commit()
    session.refresh(application)

    return application
