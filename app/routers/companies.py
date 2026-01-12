from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from datetime import datetime

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
    """
    Create a new company profile.

    **Permissions:**
    - Only users with the role 'recruiter' can create companies.

    **Business Logic:**
    - Verifies that a company with the same name does not already exist to prevent duplicates.
    - Associates the created company with the logged-in recruiter.

    **Args:**
    - data (CompanyCreateRequest): Name, description, website, and location.

    **Returns:**
    - CompanyResponse: The created company object.

    **Raises:**
    - 403 Forbidden: If the user is not a recruiter.
    - 400 Bad Request: If a company with the given name already exists.
    """
    
    # Authorization Check: Ensure user has the correct role
    if current_user.role != "recruiter":
        raise HTTPException(
            status_code=403,
            detail="Only recruiters can create companies"
        )
    
    # Validation: Check for duplicate company names
    if data.name:
        existing_company = session.exec(
            select(Company).where(Company.name == data.name)
        ).first()

        if existing_company:
            raise HTTPException(
                status_code=400,
                detail="Company with this name already exists"
            )

    # Creation: Instantiate the model
    # Note: recruiter_id is automatically pulled from the authenticated user
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


@router.get(
    "",
    response_model=list[CompanyResponse],
    status_code=status.HTTP_200_OK
)
def list_companies(
    session: Session = Depends(get_session)
):
    """
    Retrieve a list of all registered companies.

    **Permissions:**
    - Public access (no authentication required).

    **Returns:**
    - list[CompanyResponse]: A list of all company objects.
    """
    return session.exec(select(Company)).all()


@router.get(
    "/{company_id}",
    response_model=CompanyResponse,
    status_code=status.HTTP_200_OK
)
def get_company(
    company_id: int,
    session: Session = Depends(get_session)
):
    """
    Retrieve details for a specific company by ID.

    **Args:**
    - company_id (int): The unique identifier of the company.

    **Returns:**
    - CompanyResponse: The company object.

    **Raises:**
    - 404 Not Found: If the company ID does not exist.
    """
    company = session.get(Company, company_id)

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return company


@router.put(
    "/{company_id}",
    response_model=CompanyResponse,
    status_code=status.HTTP_200_OK
)
def update_company(
    company_id: int,
    data: CompanyUpdateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing company's details.

    **Permissions:**
    - Only the recruiter who created the company (the owner) can update it.

    **Args:**
    - company_id (int): ID of the company to update.
    - data (CompanyUpdateRequest): Fields to update (partial updates allowed).

    **Returns:**
    - CompanyResponse: The updated company object.

    **Raises:**
    - 404 Not Found: If the company does not exist.
    - 403 Forbidden: If the logged-in user is not the owner of the company.
    """
    
    # Check if company exists
    company = session.get(Company, company_id)

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Authorization Check: Ownership
    if company.recruiter_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to update this company"
        )

    # Partial Update: Only update fields that were actually sent in the request
    for field, value in data.dict(exclude_unset=True).items():
        setattr(company, field, value)

    # Update timestamp
    company.updated_at = datetime.utcnow()
    
    session.add(company)
    session.commit()
    session.refresh(company)

    return company


@router.delete("/{company_id}")
def delete_company(
    company_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a company profile.

    **Permissions:**
    - Only the recruiter who created the company (the owner) can delete it.

    **Args:**
    - company_id (int): ID of the company to delete.

    **Returns:**
    - dict: A success message.

    **Raises:**
    - 404 Not Found: If the company does not exist.
    - 403 Forbidden: If the logged-in user is not the owner.
    """
    
    # Check if company exists
    company = session.get(Company, company_id)

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Authorization Check: Ownership
    if company.recruiter_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to delete this company"
        )

    session.delete(company)
    session.commit()

    return {"detail": "Company deleted successfully"}