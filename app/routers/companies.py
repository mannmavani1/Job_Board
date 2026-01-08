from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from datetime import datetime
from uuid import UUID

from app.database.session import get_session
from app.models.company import Company
from app.models.user import User
from app.dependencies.auth import get_current_user
from app.schemas.company import (
    CompanyCreateRequest,
    CompanyUpdateRequest,
    CompanyResponse
)

router = APIRouter(
    prefix="/companies",
    tags=["Companies"]
)



@router.post(
    "",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED
)
def create_company(
    data: CompanyCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "recruiter":
        raise HTTPException(
            status_code=403,
            detail="Only recruiters can create companies"
        )

    company = Company(
        name=data.name,
        description=data.description,
        website=data.website,
        location=data.location,
        recruiter_id=current_user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    session.add(company)
    session.commit()
    session.refresh(company)

    return company




@router.get("", response_model=list[CompanyResponse])
def list_companies(
    session: Session = Depends(get_session)
):
    return session.exec(select(Company)).all()



@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(
    company_id: int,
    session: Session = Depends(get_session)
):
    company = session.get(Company, company_id)

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return company


# =========================
# UPDATE COMPANY (Owner only)
# =========================

@router.put("/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: int,
    data: CompanyUpdateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    company = session.get(Company, company_id)

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if company.recruiter_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to update this company"
        )

    for field, value in data.dict(exclude_unset=True).items():
        setattr(company, field, value)

    company.updated_at = datetime.utcnow()
    session.add(company)
    session.commit()
    session.refresh(company)

    return company

@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(
    company_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    company = session.get(Company, company_id)

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if company.recruiter_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to delete this company"
        )

    session.delete(company)
    session.commit()
    return  {"detail": "Company deleted successfully"}